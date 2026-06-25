import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from typing import Dict, Any, List, Optional
import os
import threading
import json
from datetime import datetime

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import websockets
    import asyncio
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

from controllers.customer_controller import PasswordChangeResult, ProfilePictureResult


class CustomerView:
    def __init__(self, root, controller=None):
        self.root = root
        self.controller = controller
        self.root.title("پنل مشتری")
        self.root.geometry("1050x720")
        self.selected_image_path = None
        self._search_after = None
        self._booking_search_after = None
        
        # WebSocket related
        self.websocket = None
        self.ws_thread = None
        self.unread_count = 0
        self.ws_running = False
        self.notification_update_id = None  # برای تایمر

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True)

        self.search_frame = ttk.Frame(self.notebook)
        self.my_bookings_frame = ttk.Frame(self.notebook)
        self.notification_frame = ttk.Frame(self.notebook)
        self.account_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.search_frame, text="  🔍  جستجو و رزرو")
        self.notebook.add(self.my_bookings_frame, text="  📋  رزروهای من  ")
        self.notebook.add(self.notification_frame, text="  🔔  اعلان‌ها  ")
        self.notebook.add(self.account_frame, text="  👤  ویرایش حساب  ")

        self._init_search_tab()
        self._init_bookings_tab()
        self._init_notification_tab()
        self._init_account_tab()

        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab)

        bottom = tk.Frame(root)
        bottom.pack(side="bottom", fill="x", pady=4)
        tk.Button(bottom, text="خروج", command=self.logout,
                  fg="white", bg="#e74c3c", padx=14).pack(side="right", padx=10)
        
        # شروع تایمر برای به‌روزرسانی خودکار اعلان‌ها
        self.schedule_notification_update()

    def set_controller(self, controller):
        self.controller = controller
        self.load_services()
        self.load_bookings()
        self.load_user_details()
        self.load_notifications()
        self._connect_websocket()

    def _on_tab(self, event):
        txt = self.notebook.tab(self.notebook.select(), 'text').strip()
        if 'جستجو' in txt:
            self.load_services()
        elif 'رزرو' in txt:
            self.load_bookings()
        elif 'اعلان' in txt:
            self.load_notifications()
        elif 'حساب' in txt or 'ویرایش' in txt:
            self.load_user_details()

    def logout(self):
        self.ws_running = False
        # لغو تایمر
        if self.notification_update_id:
            self.root.after_cancel(self.notification_update_id)
        if messagebox.askyesno("خروج", "از پنل مشتری خارج می‌شوید؟"):
            if self.controller:
                self.controller.logout()
            else:
                try: 
                    self.root.destroy()
                except: 
                    pass

    # ==================== تایمر برای به‌روزرسانی خودکار اعلان‌ها ====================
    
    def schedule_notification_update(self):
        """برنامه‌ریزی برای به‌روزرسانی خودکار اعلان‌ها (هر 10 ثانیه)"""
        self.notification_update_id = self.root.after(10000, self.check_notifications)

    def check_notifications(self):
        """بررسی اعلان‌های جدید و به‌روزرسانی"""
        if not self.controller:
            self.schedule_notification_update()
            return
        
        try:
            from models.notification_model import NotificationModel
            old_count = self.unread_count
            
            # دریافت تعداد جدید اعلان‌های خوانده نشده
            new_count = NotificationModel.get_unread_count(self.controller.user_id)
            
            # اگر تعداد تغییر کرد
            if new_count != old_count:
                self.unread_count = new_count
                self.update_unread_badge()
                
                # به‌روزرسانی جدول اعلان‌ها
                self.load_notifications()
                
                # اگر اعلان جدیدی آمده
                if new_count > old_count:
                    # به‌روزرسانی آیکون
                    self.unread_badge.config(text=str(new_count))
        except Exception as e:
            print(f"Error checking notifications: {e}")
        
        # دوباره برنامه‌ریزی کن
        self.schedule_notification_update()

    # ==================== تب اعلان‌ها (Notifications) ====================
    
    # در views/customer.py، متد _init_notification_tab را اصلاح کنید:

    def _init_notification_tab(self):
        """راه‌اندازی تب اعلان‌ها"""
        f = self.notification_frame
        
        # هدر با تعداد اعلان‌های خوانده نشده
        header_frame = tk.Frame(f)
        header_frame.pack(fill='x', padx=10, pady=10)
        
        self.unread_label = tk.Label(header_frame, text="🔔 اعلان‌ها", font=('Tahoma', 12, 'bold'))
        self.unread_label.pack(side='left')
        
        self.unread_badge = tk.Label(header_frame, text="0", bg='red', fg='white', 
                                    font=('Tahoma', 9, 'bold'), padx=5, pady=2)
        self.unread_badge.pack(side='left', padx=10)
        
        # دکمه‌های عملیاتی
        btn_frame = tk.Frame(header_frame)
        btn_frame.pack(side='right')
        
        tk.Button(btn_frame, text="✓ علامت‌گذاری همه به عنوان خوانده شده",
                command=self.mark_all_notifications_read,
                bg='#3498db', fg='white', padx=8, pady=2).pack(side='left', padx=2)
        
        tk.Button(btn_frame, text="🗑 حذف خوانده شده‌ها",
                command=self.delete_read_notifications,
                bg='#e67e22', fg='white', padx=8, pady=2).pack(side='left', padx=2)
        
        tk.Button(btn_frame, text="🗑 حذف همه",
                command=self.delete_all_notifications,
                bg='#e74c3c', fg='white', padx=8, pady=2).pack(side='left', padx=2)
        
        # جدول اعلان‌ها
        cols = ("ID", "پیام", "تاریخ", "وضعیت")
        self.notifications_tree = ttk.Treeview(f, columns=cols, show="headings", height=18)
        
        for col, w in zip(cols, [50, 500, 150, 100]):
            self.notifications_tree.heading(col, text=col)
            self.notifications_tree.column(col, width=w, anchor="center")
        
        self.notifications_tree.tag_configure('unread', background='#fff3cd')
        self.notifications_tree.tag_configure('read', background='#ffffff')
        
        sb = ttk.Scrollbar(f, orient='vertical', command=self.notifications_tree.yview)
        self.notifications_tree.configure(yscrollcommand=sb.set)
        self.notifications_tree.pack(side='left', fill="both", expand=True, padx=10, pady=5)
        sb.pack(side='left', fill='y', pady=5)
        
        # کلیک راست برای منوی حذف
        self.notifications_tree.bind('<Double-1>', self._mark_notification_read)
        self.notifications_tree.bind('<Button-3>', self._show_delete_menu)  # کلیک راست

    def _show_delete_menu(self, event):
        """نمایش منوی حذف با کلیک راست"""
        item = self.notifications_tree.identify_row(event.y)
        if not item:
            return
        
        self.notifications_tree.selection_set(item)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="🗑 حذف این اعلان", command=self._delete_selected_notification)
        menu.post(event.x_root, event.y_root)

    def _delete_selected_notification(self):
        """حذف اعلان انتخاب شده"""
        sel = self.notifications_tree.selection()
        if not sel:
            return
        
        values = self.notifications_tree.item(sel[0])['values']
        notif_id = values[0]
        
        if messagebox.askyesno("حذف اعلان", "آیا از حذف این اعلان اطمینان دارید؟"):
            from models.notification_model import NotificationModel
            success, message = NotificationModel.delete_notification(notif_id, self.controller.user_id)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_notifications()
            else:
                messagebox.showerror("خطا", message)

    def delete_read_notifications(self):
        """حذف اعلان‌های خوانده شده"""
        if messagebox.askyesno("حذف", "آیا از حذف همه اعلان‌های خوانده شده اطمینان دارید؟"):
            from models.notification_model import NotificationModel
            success, message = NotificationModel.delete_read_notifications(self.controller.user_id)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_notifications()
            else:
                messagebox.showerror("خطا", message)

    def delete_all_notifications(self):
        """حذف همه اعلان‌ها"""
        if messagebox.askyesno("حذف", "آیا از حذف همه اعلان‌ها اطمینان دارید؟ این عمل قابل بازگشت نیست."):
            from models.notification_model import NotificationModel
            success, message = NotificationModel.delete_all_notifications(self.controller.user_id)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_notifications()
            else:
                messagebox.showerror("خطا", message)
                
    def _connect_websocket(self):
        """اتصال به WebSocket server برای دریافت اعلان‌های لحظه‌ای"""
        if not WEBSOCKET_AVAILABLE or not self.controller:
            return
        
        if not self.controller.user_id:
            return
        
        self.ws_running = True
        
        def run_websocket():
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._websocket_handler())
        
        self.ws_thread = threading.Thread(target=run_websocket, daemon=True)
        self.ws_thread.start()
    
    async def _websocket_handler(self):
        """مدیریت اتصال WebSocket"""
        try:
            uri = "ws://localhost:8765"
            async with websockets.connect(uri) as websocket:
                self.websocket = websocket
                
                # احراز هویت با ارسال user_id
                await websocket.send(json.dumps({
                    'type': 'auth',
                    'user_id': self.controller.user_id
                }))
                
                # گوش دادن به پیام‌ها
                while self.ws_running:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1)
                        data = json.loads(message)
                        if data.get('type') == 'notification':
                            # اضافه کردن اعلان جدید به جدول
                            self.root.after(0, lambda: self._add_notification_to_table(data))
                            self.root.after(0, self.update_unread_badge)
                    except asyncio.TimeoutError:
                        continue
        except Exception as e:
            print(f"WebSocket error: {e}")
    
    def _add_notification_to_table(self, notification):
        """اضافه کردن اعلان جدید به جدول"""
        notification_id = notification.get('id', 'جدید')
        message = notification.get('message', '')
        created_at = notification.get('created_at', '')
        notification_type = notification.get('notification_type', 'info')
        
        # نمایش آیکون مناسب بر اساس نوع اعلان
        icon_map = {
            'booking_created': '📅',
            'booking_confirmed': '✅',
            'booking_rejected': '❌',
            'booking_canceled': '🚫',
            'payment_success': '💰',
            'profile': '👤',
            'security': '🔒',
            'report': '📄',
            'receipt': '🧾',
            'review': '⭐',
            'review_received': '⭐',  # جدید
            'review_deleted': '⚠️'  
        }
        icon = icon_map.get(notification_type, '🔔')
        
        self.notifications_tree.insert("", 0, values=(
            notification_id,
            f"{icon} {message}",
            created_at,
            "🔴 جدید"
        ), tags=('unread',))
        
        # نمایش پیام popup
        messagebox.showinfo("اعلان جدید", message)
    
    def load_notifications(self):
        """بارگذاری اعلان‌های قبلی کاربر"""
        if not self.controller:
            return
        
        for r in self.notifications_tree.get_children():
            self.notifications_tree.delete(r)
        
        from models.notification_model import NotificationModel
        notifications = NotificationModel.get_user_notifications(self.controller.user_id, limit=100)
        
        for notif in notifications:
            notif_id = notif.get('id')
            message = notif.get('message', '')
            created_at = notif.get('created_at', '')[:16]
            is_read = notif.get('is_read', False)
            notif_type = notif.get('type', 'info')
            
            icon_map = {
                'booking_created': '📅',
                'booking_confirmed': '✅',
                'booking_rejected': '❌',
                'booking_canceled': '🚫',
                'payment_success': '💰',
                'profile': '👤',
                'security': '🔒',
                'report': '📄',
                'receipt': '🧾',
                'review': '⭐'
            }
            icon = icon_map.get(notif_type, '🔔')
            
            status = "✓ خوانده شده" if is_read else "🔴 جدید"
            tag = 'read' if is_read else 'unread'
            
            self.notifications_tree.insert("", "end", values=(
                notif_id, f"{icon} {message}", created_at, status
            ), tags=(tag,))
        
        self.update_unread_badge()
    
    def update_unread_badge(self):
        """به‌روزرسانی تعداد اعلان‌های خوانده نشده"""
        if not self.controller:
            return
        
        from models.notification_model import NotificationModel
        count = NotificationModel.get_unread_count(self.controller.user_id)
        self.unread_count = count
        self.unread_badge.config(text=str(count) if count > 0 else "0")
        
        # به‌روزرسانی عنوان تب
        if count > 0:
            self.notebook.tab(self.notification_frame, text=f"  🔔  اعلان‌ها ({count})  ")
        else:
            self.notebook.tab(self.notification_frame, text="  🔔  اعلان‌ها  ")
    
    def _mark_notification_read(self, event):
        """علامت‌گذاری اعلان به عنوان خوانده شده با دابل کلیک"""
        sel = self.notifications_tree.selection()
        if not sel:
            return
        
        values = self.notifications_tree.item(sel[0])['values']
        notif_id = values[0]
        
        if notif_id == "جدید":
            return
        
        from models.notification_model import NotificationModel
        if NotificationModel.mark_as_read(notif_id, self.controller.user_id):
            # به‌روزرسانی نمایش
            self.notifications_tree.item(sel[0], values=(
                values[0], values[1], values[2], "✓ خوانده شده"
            ), tags=('read',))
            self.update_unread_badge()
    
    def mark_all_notifications_read(self):
        """علامت‌گذاری همه اعلان‌ها به عنوان خوانده شده"""
        from models.notification_model import NotificationModel
        if NotificationModel.mark_all_as_read(self.controller.user_id):
            # به‌روزرسانی جدول
            for item in self.notifications_tree.get_children():
                values = self.notifications_tree.item(item)['values']
                self.notifications_tree.item(item, values=(
                    values[0], values[1], values[2], "✓ خوانده شده"
                ), tags=('read',))
            self.update_unread_badge()
            messagebox.showinfo("موفق", "همه اعلان‌ها به عنوان خوانده شده علامت‌گذاری شدند.")

    # ═══════════════════════════════════════════════════════════════════
    # تب جستجو و رزرو
    # ═══════════════════════════════════════════════════════════════════
    
    def _init_search_tab(self):
        f = self.search_frame

        tk.Label(f, text="جستجوی خدمات:", font=("Tahoma", 12, "bold")).pack(pady=8)

        ff = tk.Frame(f)
        ff.pack(pady=4)

        row1 = tk.Frame(ff)
        row1.pack(pady=2)
        
        tk.Label(row1, text="نام سرویس:").pack(side="left", padx=4)
        self.entry_keyword = tk.Entry(row1, width=14)
        self.entry_keyword.pack(side="left", padx=4)
        self.entry_keyword.bind('<KeyRelease>', lambda e: self.load_services())
        
        tk.Label(row1, text="دسته‌بندی:").pack(side="left", padx=4)
        self.entry_category = tk.Entry(row1, width=14)
        self.entry_category.pack(side="left", padx=4)
        self.entry_category.bind('<KeyRelease>', lambda e: self.load_services())
        
        tk.Label(row1, text="ارائه‌دهنده:").pack(side="left", padx=4)
        self.entry_provider = tk.Entry(row1, width=14)
        self.entry_provider.pack(side="left", padx=4)
        self.entry_provider.bind('<KeyRelease>', lambda e: self.load_services())

        row2 = tk.Frame(ff)
        row2.pack(pady=2)
        
        tk.Label(row2, text="قیمت (تومان):").pack(side="left", padx=4)
        self.entry_min_price = tk.Entry(row2, width=8)
        self.entry_min_price.insert(0, "0")
        self.entry_min_price.pack(side="left")
        self.entry_min_price.bind('<KeyRelease>', lambda e: self.load_services())
        
        tk.Label(row2, text="تا").pack(side="left", padx=2)
        self.entry_max_price = tk.Entry(row2, width=8)
        self.entry_max_price.insert(0, "10000000")
        self.entry_max_price.pack(side="left", padx=4)
        self.entry_max_price.bind('<KeyRelease>', lambda e: self.load_services())

        cols = ("ID", "نام", "دسته‌بندی", "ارائه‌دهنده", "قیمت", "وضعیت")
        self.services_tree = ttk.Treeview(f, columns=cols, show="headings", height=10)
        for col, w in zip(cols, [45, 180, 110, 120, 100, 80]):
            self.services_tree.heading(col, text=col)
            self.services_tree.column(col, width=w, anchor="center")
        
        sb = ttk.Scrollbar(f, orient='vertical', command=self.services_tree.yview)
        self.services_tree.configure(yscrollcommand=sb.set)
        self.services_tree.pack(side='left', fill="both", expand=True, padx=(8, 0), pady=4)
        sb.pack(side='left', fill='y', pady=4)

        btn = tk.Frame(f)
        btn.pack(pady=6)
        tk.Button(btn, text="📅 رزرو", command=self.book_service,
                  bg='#27ae60', fg='white', padx=10).pack(side="left", padx=6)

    def load_services(self):
        if not self.controller:
            return
        
        if hasattr(self, '_search_after') and self._search_after:
            self.root.after_cancel(self._search_after)
        
        self._search_after = self.root.after(300, self._do_search)

    def _do_search(self):
        if not self.controller:
            return
        
        for r in self.services_tree.get_children():
            self.services_tree.delete(r)
        
        keyword = self.entry_keyword.get().strip()
        category = self.entry_category.get().strip()
        provider = self.entry_provider.get().strip()
        
        try:
            min_p = float(self.entry_min_price.get() or 0)
            max_p = float(self.entry_max_price.get() or 10000000)
        except ValueError:
            min_p = 0
            max_p = 10000000
        
        services = self.controller.search_services(
            keyword=keyword, category=category,
            provider=provider, min_price=min_p, max_price=max_p
        )
        
        if not services:
            self.services_tree.insert("", "end", values=("—", "هیچ خدماتی یافت نشد", "", "", "", ""))
            return
        
        for s in services:
            self.services_tree.insert("", "end", values=(
                s.get('id'),
                s.get('title'),
                s.get('category', "—"),
                s.get('provider_name'),
                f"{s.get('price', 0):,} تومان",
                s.get('status')
            ))

    def show_slots(self):
        if not self.controller:
            return
        sel = self.services_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک خدمت را انتخاب کنید.")
            return
        
        sid = self.services_tree.item(sel[0])["values"][0]
        if sid == "—":
            return
        
        svc_name = self.services_tree.item(sel[0])["values"][1]
        slots = self.controller.get_available_slots(sid)

        win = tk.Toplevel(self.root)
        win.title(f"بازه‌های آزاد — {svc_name}")
        win.geometry("600x380")
        win.grab_set()

        tk.Label(win, text=f"بازه‌های زمانی آزاد: {svc_name}",
                font=("Tahoma", 11, "bold")).pack(pady=10)

        cols = ("ID", "شروع", "پایان", "مدت")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=10)
        for col, w in zip(cols, [50, 200, 200, 80]):
            tree.heading(col, text=col)
            tree.column(col, width=w, anchor="center")
        tree.pack(fill="both", expand=True, padx=12, pady=6)

        if slots:
            for sl in slots:
                start_time = sl.get('start_time', '')
                end_time = sl.get('end_time', '')
                duration = ''
                if start_time and end_time:
                    try:
                        start = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
                        end = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
                        minutes = int((end - start).total_seconds() / 60)
                        duration = f"{minutes} دقیقه"
                    except:
                        duration = '—'
                
                tree.insert("", "end", values=(
                    sl.get('id'), 
                    start_time, 
                    end_time,
                    duration
                ))
        else:
            tree.insert("", "end", values=("—", "هیچ بازه آزادی وجود ندارد", "", ""))

        def reserve():
            s = tree.selection()
            if not s:
                messagebox.showwarning("هشدار", "یک بازه انتخاب کنید.", parent=win)
                return
            slot_id = tree.item(s[0])["values"][0]
            if slot_id == "—":
                return
            
            if messagebox.askyesno("تأیید رزرو", "آیا از رزرو این بازه اطمینان دارید؟", parent=win):
                success, message = self.controller.book_service(sid, slot_id)
                if success:
                    messagebox.showinfo("موفق", 
                        "✅ رزرو با موفقیت ثبت شد!\n\n"
                        "⚠️ نکته مهم: برای تأیید نهایی رزرو، لطفاً پرداخت را انجام دهید.\n"
                        "تا زمان پرداخت، رزرو شما در وضعیت انتظار باقی می‌ماند و تأیید نخواهد شد.\n\n"
                        "✅ پس از پرداخت، ارائه‌دهنده می‌تواند رزرو شما را تأیید کند.", 
                        parent=win)
                    win.destroy()
                    self.load_services()
                    self.load_bookings()
                else:
                    messagebox.showerror("خطا", f"رزرو ناموفق بود: {message}", parent=win)

        tk.Button(win, text="📅 رزرو این بازه", command=reserve,
                bg='#27ae60', fg='white', padx=14, pady=6).pack(pady=10)
                
    def book_service(self):
        self.show_slots()

    # ═══════════════════════════════════════════════════════════════════
    # تب رزروهای من
    # ═══════════════════════════════════════════════════════════════════
    
    def _init_bookings_tab(self):
        f = self.my_bookings_frame
        
        tk.Label(f, text="رزروهای من:", font=("Tahoma", 12, "bold")).pack(pady=8)

        btn_frame = tk.Frame(f)
        btn_frame.pack(fill='x', padx=8, pady=5)
        
        buttons = [
            ("📄 گزارش PDF رزروها", self._pdf_bookings_report, '#e74c3c'),
            ("🧾 فاکتور پرداخت", self._pdf_receipt, '#16a085'),
            ("🚫 لغو رزرو", self.cancel_booking, '#e74c3c'),
            ("💳 پرداخت", self.pay_booking, '#8e44ad'),
            ("⭐ امتیازدهی", self.rate_booking, '#f39c12'),
        ]
        
        for text, cmd, color in buttons:
            tk.Button(btn_frame, text=text, command=cmd, bg=color, fg='white', 
                      padx=10, pady=4).pack(side="left", padx=4)

        filter_frame = tk.Frame(f, bg='#ecf0f1', pady=5)
        filter_frame.pack(fill='x', padx=8, pady=(5, 0))
        
        tk.Label(filter_frame, text="وضعیت:", bg='#ecf0f1', 
                 font=('Tahoma', 10)).pack(side='left', padx=5)
        
        self.booking_status_filter = tk.StringVar(value='همه')
        status_combo = ttk.Combobox(filter_frame, textvariable=self.booking_status_filter,
                                     values=['همه', 'Pending', 'Confirmed', 'Rejected', 'Canceled'],
                                     state='readonly', width=12)
        status_combo.pack(side='left', padx=5)
        status_combo.bind('<<ComboboxSelected>>', lambda e: self.load_bookings())
        
        tk.Label(filter_frame, text="پرداخت:", bg='#ecf0f1', 
                 font=('Tahoma', 10)).pack(side='left', padx=15)
        
        self.booking_payment_filter = tk.StringVar(value='همه')
        payment_combo = ttk.Combobox(filter_frame, textvariable=self.booking_payment_filter,
                                      values=['همه', 'Paid', 'Unpaid'],
                                      state='readonly', width=10)
        payment_combo.pack(side='left', padx=5)
        payment_combo.bind('<<ComboboxSelected>>', lambda e: self.load_bookings())
        
        tk.Label(filter_frame, text="جستجو:", bg='#ecf0f1', 
                 font=('Tahoma', 10)).pack(side='left', padx=15)
        
        self.booking_search_var = tk.StringVar()
        search_entry = tk.Entry(filter_frame, textvariable=self.booking_search_var, width=20)
        search_entry.pack(side='left', padx=5)
        search_entry.bind('<KeyRelease>', lambda e: self.load_bookings())
        
        cols = ("ID", "خدمت", "ارائه‌دهنده", "زمان شروع", "وضعیت", "پرداخت", "زمان پرداخت", "امتیاز")
        self.bookings_tree = ttk.Treeview(f, columns=cols, show="headings", height=14)
        STATUS_BG = {'Pending': '#fff3cd', 'Confirmed': '#d4edda',
                     'Rejected': '#f8d7da', 'Canceled': '#e2e3e5'}
        for s, bg in STATUS_BG.items():
            self.bookings_tree.tag_configure(s, background=bg)
        
        col_widths = [45, 180, 130, 150, 90, 80, 130, 80]
        for col, w in zip(cols, col_widths):
            self.bookings_tree.heading(col, text=col)
            self.bookings_tree.column(col, width=w, anchor="center")
        
        sb = ttk.Scrollbar(f, orient='vertical', command=self.bookings_tree.yview)
        self.bookings_tree.configure(yscrollcommand=sb.set)
        self.bookings_tree.pack(side='left', fill="both", expand=True, padx=(8, 0), pady=4)
        sb.pack(side='left', fill='y', pady=4)

    def load_bookings(self):
        if not self.controller:
            return
        
        if hasattr(self, '_booking_search_after') and self._booking_search_after:
            self.root.after_cancel(self._booking_search_after)
        
        self._booking_search_after = self.root.after(300, self._do_load_bookings)

    def _do_load_bookings(self):
        if not self.controller:
            return
        
        for r in self.bookings_tree.get_children():
            self.bookings_tree.delete(r)
        
        all_bookings = self.controller.get_my_bookings()
        
        status_filter = self.booking_status_filter.get() if hasattr(self, 'booking_status_filter') else 'همه'
        payment_filter = self.booking_payment_filter.get() if hasattr(self, 'booking_payment_filter') else 'همه'
        search_text = self.booking_search_var.get().strip().lower() if hasattr(self, 'booking_search_var') else ''
        
        filtered_bookings = []
        for b in all_bookings:
            if status_filter != 'همه' and b.get('status') != status_filter:
                continue
            if payment_filter != 'همه' and b.get('payment_status') != payment_filter:
                continue
            if search_text:
                service = b.get('service_title', '').lower()
                provider = b.get('provider_name', '').lower()
                if search_text not in service and search_text not in provider:
                    continue
            filtered_bookings.append(b)
        
        for b in filtered_bookings:
            status = b.get('status', '')
            paid_at = b.get('paid_at', '')
            if paid_at:
                paid_at = paid_at[:16]
            else:
                paid_at = '—'
            
            review_status = self.controller.get_review_status_for_booking(b.get('id'))
            if review_status.get('has_reviewed'):
                rating = review_status.get('rating', 0)
                rating_display = f"{rating}"
            else:
                rating_display = "—"
            
            self.bookings_tree.insert("", "end", values=(
                b.get('id'),
                b.get('service_title'),
                b.get('provider_name'),
                b.get('start_time'),
                status,
                b.get('payment_status'),
                paid_at,
                rating_display
            ), tags=(status,))
        
        count = len(filtered_bookings)
        self.notebook.tab(self.my_bookings_frame, text=f'  📋  رزروهای من ({count})  ')

    def cancel_booking(self):
        if not self.controller:
            return
        sel = self.bookings_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک رزرو را انتخاب کنید.")
            return
        
        bid = self.bookings_tree.item(sel[0])["values"][0]
        if bid == "—":
            return
        
        can_cancel, hours_remaining, message = self.controller.can_cancel_booking(bid)
        
        if not can_cancel:
            messagebox.showerror("خطا", message)
            return
        
        start_time = self.bookings_tree.item(sel[0])["values"][3]
        response = messagebox.askyesno("تأیید لغو",
            f"آیا از لغو این رزرو اطمینان دارید؟\n\n"
            f"📅 سرویس: {self.bookings_tree.item(sel[0])['values'][1]}\n"
            f"📅 زمان شروع: {start_time}\n"
            f"⏰ {message}\n\n"
            f"⚠️ توجه: پس از لغو، مبلغ به کیف پول شما برگشت داده می‌شود.")
        
        if response:
            success, msg = self.controller.cancel_booking(bid)
            if success:
                messagebox.showinfo("موفق", msg)
                self.load_bookings()
            else:
                messagebox.showerror("خطا", msg)

    def pay_booking(self):
        if not self.controller:
            return
        sel = self.bookings_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک رزرو را انتخاب کنید.")
            return
        
        vals = self.bookings_tree.item(sel[0])["values"]
        bid = vals[0]
        payment_status = vals[5]
        
        if bid == "—":
            return
        if payment_status == "Paid":
            messagebox.showinfo("اطلاع", "این رزرو قبلاً پرداخت شده.")
            return
        
        from models.booking_model import BookingModel
        booking = BookingModel.get_booking_by_id(bid)
        
        if messagebox.askyesno("تأیید پرداخت", 
            f"آیا از پرداخت مبلغ این رزرو اطمینان دارید؟\n\n"
            f"📅 سرویس: {self.bookings_tree.item(sel[0])['values'][1]}\n"
            f"📅 زمان شروع: {self.bookings_tree.item(sel[0])['values'][3]}\n\n"
            f"💰 مبلغ قابل پرداخت: {booking.get('price') if booking else 'نامشخص'} تومان\n\n"
            f"✅ پس از پرداخت، رزرو شما برای تأیید به ارائه‌دهنده ارسال می‌شود."):
            
            success, message = self.controller.pay_booking(bid)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_bookings()
            else:
                messagebox.showerror("خطا", f"پرداخت ناموفق بود: {message}")

    # ═══════════════════════════════════════════════════════════════════
    # امتیازدهی
    # ═══════════════════════════════════════════════════════════════════
    
    def rate_booking(self):
        if not self.controller:
            return
        
        sel = self.bookings_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک رزرو را انتخاب کنید.")
            return
        
        vals = self.bookings_tree.item(sel[0])["values"]
        booking_id = vals[0]
        status = vals[4]
        payment_status = vals[5]
        service_title = vals[1]
        start_time = vals[3]
        
        if status != 'Confirmed':
            messagebox.showwarning("هشدار", 
                "امکان امتیازدهی فقط برای رزروهای تأیید شده وجود دارد.\n"
                f"وضعیت فعلی: {status}")
            return
        
        if payment_status != 'Paid':
            messagebox.showwarning("هشدار", 
                "امکان امتیازدهی فقط برای رزروهای پرداخت شده وجود دارد.\n"
                "لطفاً ابتدا پرداخت را انجام دهید.")
            return
        
        can_review, message = self.controller.can_review_booking(booking_id)
        if not can_review:
            review_status = self.controller.get_review_status_for_booking(booking_id)
            if review_status.get('has_reviewed'):
                rating = review_status.get('rating', 0)
                comment = review_status.get('comment', '')
                created_at = review_status.get('created_at', '')
                messagebox.showinfo("امتیاز قبلی", 
                    f"شما قبلاً برای این رزرو امتیاز ثبت کرده‌اید.\n\n"
                    f"⭐ امتیاز: {rating} از 5\n"
                    f"💬 نظر: {comment if comment else 'نظری ثبت نشده'}\n"
                    f"📅 تاریخ ثبت: {created_at}")
            else:
                messagebox.showwarning("هشدار", message)
            return
        
        self._show_review_form(booking_id, service_title, start_time)

    def _show_review_form(self, booking_id: int, service_title: str, start_time: str):
        win = tk.Toplevel(self.root)
        win.title("ثبت امتیاز و نظر")
        win.geometry("450x480")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="ثبت امتیاز برای سرویس", 
                font=('Tahoma', 14, 'bold')).pack(pady=10)
        
        tk.Label(win, text=f"📅 سرویس: {service_title}", 
                font=('Tahoma', 10)).pack(pady=2)
        tk.Label(win, text=f"⏰ زمان شروع: {start_time}", 
                font=('Tahoma', 10)).pack(pady=2)
        
        tk.Frame(win, height=2, bg='#ccc').pack(fill='x', padx=20, pady=10)

        tk.Label(win, text="امتیاز شما (1 تا 5):", 
                font=('Tahoma', 11, 'bold')).pack(pady=(10, 5))
        
        rating_frame = tk.Frame(win)
        rating_frame.pack(pady=5)
        
        self.rating_var = tk.IntVar(value=5)
        
        for i in range(1, 6):
            rb = tk.Radiobutton(rating_frame, text=f"⭐ {i}", 
                                variable=self.rating_var, value=i,
                                font=('Tahoma', 11))
            rb.pack(side='left', padx=8)
        
        rating_labels_frame = tk.Frame(win)
        rating_labels_frame.pack(pady=5)
        
        rating_labels = [
            (1, "خیلی ضعیف"),
            (2, "ضعیف"),
            (3, "متوسط"),
            (4, "خوب"),
            (5, "عالی")
        ]
        
        for i, label in rating_labels:
            color = '#e74c3c' if i <= 2 else '#f39c12' if i == 3 else '#27ae60'
            tk.Label(rating_labels_frame, text=f"{i}⭐: {label}", 
                    font=('Tahoma', 8), fg=color).pack(side='left', padx=5)

        tk.Label(win, text="نظر شما (اختیاری):", 
                font=('Tahoma', 11, 'bold')).pack(pady=(15, 5))
        
        self.comment_text = tk.Text(win, width=50, height=5, 
                                    font=('Tahoma', 10), wrap='word')
        self.comment_text.pack(padx=20, pady=5)
        
        tk.Label(win, text="نظر شما به ارائه‌دهنده کمک می‌کند تا خدمات بهتری ارائه دهد.", 
                font=('Tahoma', 8), fg='gray').pack()

        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=20)
        
        submit_btn = tk.Button(btn_frame, text="✅ ثبت امتیاز", 
                            command=lambda: self._submit_review(win, booking_id),
                            bg='#27ae60', fg='white', font=('Tahoma', 10, 'bold'),
                            padx=20, pady=5)
        submit_btn.pack(side='left', padx=10)
        
        cancel_btn = tk.Button(btn_frame, text="❌ انصراف", 
                            command=win.destroy,
                            bg='#95a5a6', fg='white', font=('Tahoma', 10),
                            padx=20, pady=5)
        cancel_btn.pack(side='left', padx=10)

    def _submit_review(self, window, booking_id: int):
        rating = self.rating_var.get()
        comment = self.comment_text.get("1.0", tk.END).strip()
        
        success, message = self.controller.add_review(booking_id, rating, comment)
        
        if success:
            messagebox.showinfo("موفق", message, parent=window)
            window.destroy()
            self.load_bookings()
        else:
            messagebox.showerror("خطا", message, parent=window)
            
    # ═══════════════════════════════════════════════════════════════════
    # PDF Reports
    # ═══════════════════════════════════════════════════════════════════
    
    def _pdf_bookings_report(self):
        if not self.controller:
            return
        try:
            path = self.controller.generate_bookings_report()
            if path:
                messagebox.showinfo("موفق", f"گزارش PDF ساخته شد.\n\nمسیر:\n{path}")
            else:
                messagebox.showerror("خطا", "خطا در تولید گزارش PDF")
        except Exception as e:
            messagebox.showerror("خطا", f"خطا: {str(e)}")

    def _pdf_receipt(self):
        if not self.controller:
            return
        sel = self.bookings_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک رزرو را انتخاب کنید.")
            return
        
        vals = self.bookings_tree.item(sel[0])["values"]
        bid = vals[0]
        
        if bid == "—":
            return
        if vals[5] != "Paid":
            messagebox.showwarning("هشدار", "فقط رزروهای پرداخت‌شده فاکتور دارند.")
            return
        
        try:
            path = self.controller.generate_receipt(bid)
            if path:
                messagebox.showinfo("موفق", f"فاکتور PDF ساخته شد.\n\nمسیر:\n{path}")
            else:
                messagebox.showerror("خطا", "خطا در تولید فاکتور")
        except Exception as e:
            messagebox.showerror("خطا", f"خطا: {str(e)}")

    # ═══════════════════════════════════════════════════════════════════
    # تب ویرایش حساب
    # ═══════════════════════════════════════════════════════════════════
    
    def _init_account_tab(self):
        f = self.account_frame

        pic_frm = ttk.LabelFrame(f, text="تصویر پروفایل", padding=10)
        pic_frm.pack(fill="x", padx=24, pady=12)
        self.profile_label = tk.Label(pic_frm, text="تصویری انتخاب نشده",
                                      bg="#ecf0f1", width=20, height=10)
        self.profile_label.pack(side="left", padx=10)
        btn_pic = ttk.Frame(pic_frm)
        btn_pic.pack(side="left", padx=16)
        ttk.Button(btn_pic, text="انتخاب تصویر", command=self._select_pic).pack(pady=4)
        ttk.Button(btn_pic, text="ذخیره تصویر", command=self._save_pic).pack(pady=4)

        pass_frm = ttk.LabelFrame(f, text="تغییر رمز عبور", padding=12)
        pass_frm.pack(fill="x", padx=24, pady=12)
        
        for i, (lbl, attr, show) in enumerate([
            ("رمز عبور فعلی:", "_cur_pass", "*"),
            ("رمز عبور جدید:", "_new_pass", "*"),
            ("تکرار رمز جدید:", "_confirm_pass", "*"),
        ]):
            tk.Label(pass_frm, text=lbl, width=18, anchor='w',
                     font=('Tahoma', 10)).grid(row=i, column=0, pady=6, sticky='w')
            e = ttk.Entry(pass_frm, show=show, width=28)
            e.grid(row=i, column=1, pady=6, padx=8)
            setattr(self, attr, e)
        ttk.Button(pass_frm, text="تغییر رمز عبور",
                   command=self._change_pass).grid(row=3, column=1, pady=12, sticky='e')

    def _select_pic(self):
        fp = filedialog.askopenfilename(
            title="انتخاب تصویر",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg")])
        if fp:
            self.selected_image_path = fp
            if PIL_AVAILABLE:
                try:
                    img = Image.open(fp).resize((200, 200), Image.Resampling.LANCZOS)
                    ph = ImageTk.PhotoImage(img)
                    self.profile_label.config(image=ph, text="")
                    self.profile_label.image = ph
                    self.profile_label.config(width=200, height=200)
                except Exception as e:
                    print(f"pic preview error: {e}")
    
    def _get_profile_image_path(self):
        if not self.controller:
            return None
        
        details = self.controller.get_user_details()
        if not details:
            return None
        
        photo = details.get('profile_image', '')
        if not photo:
            return None
        
        if os.path.exists(photo):
            return photo
        
        filename = os.path.basename(photo)
        if filename:
            alt_path = os.path.join('assets', 'profile_pics', filename)
            if os.path.exists(alt_path):
                return alt_path
        
        return None

    def load_user_details(self):
        if not self.controller:
            return
        
        image_path = self._get_profile_image_path()
        
        if image_path and PIL_AVAILABLE:
            try:
                img = Image.open(image_path).resize((200, 200), Image.Resampling.LANCZOS)
                ph = ImageTk.PhotoImage(img)
                self.profile_label.config(image=ph, text="")
                self.profile_label.image = ph
                self.profile_label.config(width=200, height=200)
            except Exception as e:
                print(f"Error loading profile image: {e}")
                self.profile_label.config(image='', text='خطا در بارگذاری تصویر')
        else:
            self.profile_label.config(image='', text='بدون تصویر')

    def _save_pic(self):
        if not self.controller or not self.selected_image_path:
            messagebox.showwarning("خطا", "ابتدا یک تصویر انتخاب کنید.")
            return
        
        result, message = self.controller.update_profile_picture(self.selected_image_path)
        
        if result == ProfilePictureResult.SUCCESS:
            messagebox.showinfo("موفق", message)
            self.load_user_details()
        elif result == ProfilePictureResult.NO_FILE:
            messagebox.showwarning("خطا", message)
        elif result == ProfilePictureResult.FILE_NOT_FOUND:
            messagebox.showerror("خطا", message)
        else:
            messagebox.showerror("خطا", message)

    def _change_pass(self):
        if not self.controller:
            return
        
        result = self.controller.change_password(
            self._cur_pass.get(),
            self._new_pass.get(),
            self._confirm_pass.get()
        )
        
        if result == PasswordChangeResult.OK:
            messagebox.showinfo("موفق", "رمز عبور با موفقیت تغییر کرد.")
        elif result == PasswordChangeResult.EMPTY:
            messagebox.showwarning("خطا", "تمام فیلدهای رمز عبور الزامی‌اند.")
        elif result == PasswordChangeResult.MISMATCH:
            messagebox.showerror("خطا", "رمز جدید و تکرار آن مطابقت ندارند.")
        elif result == PasswordChangeResult.WRONG_PASSWORD:
            messagebox.showerror("خطا", "رمز عبور فعلی اشتباه است.")
        
        self._cur_pass.delete(0, 'end')
        self._new_pass.delete(0, 'end')
        self._confirm_pass.delete(0, 'end')