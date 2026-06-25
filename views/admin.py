import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from typing import Dict, Any, List, Optional
from enum import Enum

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from controllers.admin_controller import PasswordChangeResult

ROLE_COLORS = {'Admin': '#e74c3c', 'Provider': '#2980b9', 'Customer': '#27ae60'}
STATUS_BG = {'Pending': '#fff3cd', 'Confirmed': '#d4edda', 'Rejected': '#f8d7da', 'Canceled': '#e2e3e5'}


class AdminView:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.root.title("پنل مدیریت سیستم")
        self.root.geometry("1050x720")
        self.root.minsize(900, 600)
        self._service_search_after = None
        self._review_search_after = None
        
        # برای تایمر اعلان‌ها
        self.notification_update_id = None
        self.admin_unread_count = 0

        self._topbar()
        self._notebook()
        self._tab_users()
        self._tab_bookings()
        self._tab_services()
        self._tab_reviews()
        self._tab_notifications()
        self._tab_dashboard()
        self._tab_profile()
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab)
        self.load_users()
        self.load_stats()
        self.load_notifications()
        
        # شروع تایمر برای به‌روزرسانی خودکار اعلان‌ها
        self.schedule_notification_update()

    def _topbar(self):
        bar = tk.Frame(self.root, bg='#2c3e50', height=46)
        bar.pack(fill='x')
        bar.pack_propagate(False)
        tk.Label(bar, text='⚙  پنل مدیریت', bg='#2c3e50', fg='white',
                 font=('Tahoma', 13, 'bold')).pack(side='left', padx=14)
        tk.Button(bar, text='خروج', command=self._logout,
                  bg='#e74c3c', fg='white', font=('Tahoma', 10, 'bold'),
                  relief='flat', padx=12, pady=2).pack(side='right', padx=10, pady=8)

    def _notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=6, pady=4)
        self.tab_users = ttk.Frame(self.notebook)
        self.tab_bookings = ttk.Frame(self.notebook)
        self.tab_services = ttk.Frame(self.notebook)
        self.tab_reviews = ttk.Frame(self.notebook)
        self.tab_notifications = ttk.Frame(self.notebook)
        self.tab_dash = ttk.Frame(self.notebook)
        self.tab_profile = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tab_users, text='  👤  کاربران  ')
        self.notebook.add(self.tab_bookings, text='  📋  رزروها  ')
        self.notebook.add(self.tab_services, text='  🛠  خدمات  ')
        self.notebook.add(self.tab_reviews, text='  ⭐  نظرات  ')
        self.notebook.add(self.tab_notifications, text='  🔔  اعلان‌ها  ')
        self.notebook.add(self.tab_dash, text='  📊  داشبورد  ')
        self.notebook.add(self.tab_profile, text='  🔑  پروفایل  ')

    def _on_tab(self, event):
        txt = self.notebook.tab(self.notebook.select(), 'text').strip()
        if 'کاربران' in txt:
            if hasattr(self, 'role_filter_var'):
                self.role_filter_var.set('همه')
            self.load_users()
        elif 'رزروها' in txt:
            self.load_bookings()
        elif 'خدمات' in txt:
            self.load_services()
        elif 'نظرات' in txt:
            self.load_reviews()
        elif 'اعلان' in txt:
            self.load_notifications()
        elif 'داشبورد' in txt:
            self.load_stats()

    def _logout(self):
        # لغو تایمر
        if self.notification_update_id:
            self.root.after_cancel(self.notification_update_id)
        if messagebox.askyesno("خروج", "از پنل مدیریت خارج می‌شوید؟"):
            self.root.destroy()
            self.controller.return_to_login()

    # ==================== تایمر برای به‌روزرسانی خودکار اعلان‌ها ====================
    
    def schedule_notification_update(self):
        """برنامه‌ریزی برای به‌روزرسانی خودکار اعلان‌ها (هر 10 ثانیه)"""
        self.notification_update_id = self.root.after(10000, self.check_notifications)

    def check_notifications(self):
        """بررسی اعلان‌های جدید و به‌روزرسانی"""
        if not self.controller or not self.controller._admin_user_id:
            self.schedule_notification_update()
            return
        
        try:
            from models.notification_model import NotificationModel
            old_count = self.admin_unread_count
            
            new_count = NotificationModel.get_unread_count(self.controller._admin_user_id)
            
            if new_count != old_count:
                self.admin_unread_count = new_count
                self.update_unread_badge()
                self.load_notifications()
                if new_count > old_count:
                    self.admin_unread_badge.config(text=str(new_count))
        except Exception as e:
            print(f"Error checking notifications: {e}")
        
        self.schedule_notification_update()

    # ==================== تب اعلان‌ها ====================
    
   # در views/admin.py، متد _tab_notifications را اصلاح کنید:

    def _tab_notifications(self):
        """راه‌اندازی تب اعلان‌ها برای ادمین"""
        f = self.tab_notifications
        
        header_frame = tk.Frame(f)
        header_frame.pack(fill='x', padx=10, pady=10)
        
        self.admin_unread_label = tk.Label(header_frame, text="🔔 اعلان‌ها", font=('Tahoma', 12, 'bold'))
        self.admin_unread_label.pack(side='left')
        
        self.admin_unread_badge = tk.Label(header_frame, text="0", bg='red', fg='white', 
                                            font=('Tahoma', 9, 'bold'), padx=5, pady=2)
        self.admin_unread_badge.pack(side='left', padx=10)
        
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
        self.admin_notifications_tree = ttk.Treeview(f, columns=cols, show="headings", height=18)
        
        for col, w in zip(cols, [50, 500, 150, 100]):
            self.admin_notifications_tree.heading(col, text=col)
            self.admin_notifications_tree.column(col, width=w, anchor="center")
        
        self.admin_notifications_tree.tag_configure('unread', background='#fff3cd')
        self.admin_notifications_tree.tag_configure('read', background='#ffffff')
        
        sb = ttk.Scrollbar(f, orient='vertical', command=self.admin_notifications_tree.yview)
        self.admin_notifications_tree.configure(yscrollcommand=sb.set)
        self.admin_notifications_tree.pack(side='left', fill="both", expand=True, padx=10, pady=5)
        sb.pack(side='left', fill='y', pady=5)
        
        self.admin_notifications_tree.bind('<Double-1>', self._mark_notification_read)
        self.admin_notifications_tree.bind('<Button-3>', self._show_delete_menu)  # کلیک راست

    def _show_delete_menu(self, event):
        """نمایش منوی حذف با کلیک راست"""
        item = self.admin_notifications_tree.identify_row(event.y)
        if not item:
            return
        
        self.admin_notifications_tree.selection_set(item)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="🗑 حذف این اعلان", command=self._delete_selected_notification)
        menu.post(event.x_root, event.y_root)

    def _delete_selected_notification(self):
        """حذف اعلان انتخاب شده"""
        sel = self.admin_notifications_tree.selection()
        if not sel:
            return
        
        values = self.admin_notifications_tree.item(sel[0])['values']
        notif_id = values[0]
        
        if messagebox.askyesno("حذف اعلان", "آیا از حذف این اعلان اطمینان دارید؟"):
            from models.notification_model import NotificationModel
            success, message = NotificationModel.delete_notification(notif_id, self.controller._admin_user_id)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_notifications()
            else:
                messagebox.showerror("خطا", message)

    def delete_read_notifications(self):
        """حذف اعلان‌های خوانده شده"""
        if messagebox.askyesno("حذف", "آیا از حذف همه اعلان‌های خوانده شده اطمینان دارید؟"):
            from models.notification_model import NotificationModel
            success, message = NotificationModel.delete_read_notifications(self.controller._admin_user_id)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_notifications()
            else:
                messagebox.showerror("خطا", message)

    def delete_all_notifications(self):
        """حذف همه اعلان‌ها"""
        if messagebox.askyesno("حذف", "آیا از حذف همه اعلان‌ها اطمینان دارید؟ این عمل قابل بازگشت نیست."):
            from models.notification_model import NotificationModel
            success, message = NotificationModel.delete_all_notifications(self.controller._admin_user_id)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_notifications()
            else:
                messagebox.showerror("خطا", message)
                
    def load_notifications(self):
        """بارگذاری اعلان‌های ادمین"""
        if not self.controller or not self.controller._admin_user_id:
            return
        
        for r in self.admin_notifications_tree.get_children():
            self.admin_notifications_tree.delete(r)
        
        from models.notification_model import NotificationModel
        notifications = NotificationModel.get_user_notifications(self.controller._admin_user_id, limit=100)
        
        icon_map = {
            'user_management': '👤', 'booking_management': '📋', 'service_management': '🛠️',
            'review_management': '⭐', 'security': '🔒', 'report': '📄',
            'admin_action': '⚙️', 'review_deleted': '⚠️', 'payment_success': '💰'
        }
        
        for notif in notifications:
            notif_id = notif.get('id')
            message = notif.get('message', '')
            created_at = notif.get('created_at', '')[:16]
            is_read = notif.get('is_read', False)
            notif_type = notif.get('type', 'info')
            
            icon = icon_map.get(notif_type, '🔔')
            display_message = f"{icon} {message}"
            status = "✓ خوانده شده" if is_read else "🔴 جدید"
            tag = 'read' if is_read else 'unread'
            
            self.admin_notifications_tree.insert("", "end", values=(
                notif_id, display_message, created_at, status
            ), tags=(tag,))
        
        self.update_unread_badge()

    def update_unread_badge(self):
        """به‌روزرسانی تعداد اعلان‌های خوانده نشده ادمین"""
        if not self.controller or not self.controller._admin_user_id:
            return
        
        from models.notification_model import NotificationModel
        count = NotificationModel.get_unread_count(self.controller._admin_user_id)
        self.admin_unread_count = count
        self.admin_unread_badge.config(text=str(count) if count > 0 else "0")
        
        if count > 0:
            self.notebook.tab(self.tab_notifications, text=f'  🔔  اعلان‌ها ({count})  ')
        else:
            self.notebook.tab(self.tab_notifications, text='  🔔  اعلان‌ها  ')

    def _mark_notification_read(self, event):
        """علامت‌گذاری اعلان به عنوان خوانده شده با دابل کلیک"""
        sel = self.admin_notifications_tree.selection()
        if not sel:
            return
        
        values = self.admin_notifications_tree.item(sel[0])['values']
        notif_id = values[0]
        
        from models.notification_model import NotificationModel
        if NotificationModel.mark_as_read(notif_id, self.controller._admin_user_id):
            self.admin_notifications_tree.item(sel[0], values=(
                values[0], values[1], values[2], "✓ خوانده شده"
            ), tags=('read',))
            self.update_unread_badge()

    def mark_all_notifications_read(self):
        """علامت‌گذاری همه اعلان‌ها به عنوان خوانده شده"""
        from models.notification_model import NotificationModel
        if NotificationModel.mark_all_as_read(self.controller._admin_user_id):
            for item in self.admin_notifications_tree.get_children():
                values = self.admin_notifications_tree.item(item)['values']
                self.admin_notifications_tree.item(item, values=(
                    values[0], values[1], values[2], "✓ خوانده شده"
                ), tags=('read',))
            self.update_unread_badge()
            messagebox.showinfo("موفق", "همه اعلان‌ها به عنوان خوانده شده علامت‌گذاری شدند.")

    # ==================== تب کاربران ====================
    
    def _tab_users(self):
        f = self.tab_users
        
        tb = tk.Frame(f, bg='#ecf0f1', pady=5)
        tb.pack(fill='x')
        tk.Label(tb, text='مدیریت کاربران', font=('Tahoma', 11, 'bold'), 
                 bg='#ecf0f1').pack(side='left', padx=10)
        
        for txt, clr, cmd in [
            ('+ افزودن', '#2ecc71', self._show_add_user_form),
            ('✏ تغییر نقش', '#3498db', self._change_role),
            ('🗑 حذف', '#e74c3c', self._delete_user),
        ]:
            tk.Button(tb, text=txt, command=cmd, bg=clr, fg='white', 
                      relief='flat', padx=8).pack(side='right', padx=4)
        
        filter_frame = tk.Frame(f, bg='#ecf0f1', pady=5)
        filter_frame.pack(fill='x', padx=8, pady=(5, 0))
        
        tk.Label(filter_frame, text="فیلتر بر اساس نقش:", bg='#ecf0f1', 
                 font=('Tahoma', 10)).pack(side='left', padx=5)
        
        self.role_filter_var = tk.StringVar(value='همه')
        role_filter_combo = ttk.Combobox(filter_frame, textvariable=self.role_filter_var,
                                          values=['همه', 'Admin', 'Provider', 'Customer'],
                                          state='readonly', width=15)
        role_filter_combo.pack(side='left', padx=5)
        role_filter_combo.bind('<<ComboboxSelected>>', lambda e: self.load_users())
        
        cols = ('ID', 'نام کاربری', 'نقش', 'تاریخ ثبت')
        self.users_tree = ttk.Treeview(f, columns=cols, show='headings', height=20)
        for role, clr in ROLE_COLORS.items():
            self.users_tree.tag_configure(role, foreground=clr)
        for col, w in zip(cols, [50, 220, 110, 170]):
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=w, anchor='center')
        
        sb = ttk.Scrollbar(f, orient='vertical', command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=sb.set)
        self.users_tree.pack(side='left', fill='both', expand=True, padx=(8, 0), pady=6)
        sb.pack(side='left', fill='y', pady=6)

    def load_users(self):
        for r in self.users_tree.get_children():
            self.users_tree.delete(r)
        
        all_users = self.controller.get_all_users()
        selected_role = self.role_filter_var.get() if hasattr(self, 'role_filter_var') else 'همه'
        
        if selected_role != 'همه':
            filtered_users = [u for u in all_users if u.get('role') == selected_role]
        else:
            filtered_users = all_users
        
        for u in filtered_users:
            role = u.get('role', '')
            values = (u.get('id'), u.get('username'), role, u.get('created_at'))
            self.users_tree.insert('', 'end', values=values, tags=(role,))
        
        count = len(filtered_users)
        self.notebook.tab(self.tab_users, text=f'  👤  کاربران ({count})  ')

    def _show_add_user_form(self):
        win = tk.Toplevel(self.root)
        win.title("افزودن کاربر جدید")
        win.geometry("320x270")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        tk.Label(win, text="نام کاربری:").pack(pady=(12, 0))
        e_user = tk.Entry(win, width=30)
        e_user.pack(pady=4)
        
        tk.Label(win, text="رمز عبور:").pack()
        e_pass = tk.Entry(win, width=30, show='*')
        e_pass.pack(pady=4)
        
        tk.Label(win, text="تکرار رمز:").pack()
        e_pass_confirm = tk.Entry(win, width=30, show='*')
        e_pass_confirm.pack(pady=4)
        
        tk.Label(win, text="نقش:").pack()
        role_var = tk.StringVar(value='Customer')
        role_combo = ttk.Combobox(win, textvariable=role_var, 
                                   values=['Admin', 'Provider', 'Customer'],
                                   state='readonly', width=27)
        role_combo.pack(pady=4)

        def save():
            username = e_user.get().strip()
            password = e_pass.get().strip()
            password_confirm = e_pass_confirm.get().strip()
            role = role_var.get()
            
            if not username or not password:
                messagebox.showerror("خطا", "نام کاربری و رمز عبور الزامی‌اند.", parent=win)
                return
            
            if password != password_confirm:
                messagebox.showerror("خطا", "رمز عبور و تکرار آن مطابقت ندارند.", parent=win)
                return
            
            success, message = self.controller.add_user(username, password, role)
            if success:
                messagebox.showinfo("موفق", message, parent=win)
                win.destroy()
                self.load_users()
            else:
                messagebox.showerror("خطا", message, parent=win)

        tk.Button(win, text="ذخیره", command=save, 
                  bg="#2ecc71", fg="white", width=14).pack(pady=14)

    def _change_role(self):
        sel = self.users_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک کاربر انتخاب کنید.")
            return
        
        vals = self.users_tree.item(sel[0])['values']
        uid, cur_role = vals[0], vals[2]
        
        win = tk.Toplevel(self.root)
        win.title("تغییر نقش")
        win.geometry("260x190")
        win.resizable(False, False)
        win.grab_set()
        
        tk.Label(win, text=f"کاربر: {vals[1]}", font=('Tahoma', 11, 'bold')).pack(pady=10)
        tk.Label(win, text="نقش جدید:").pack()
        rv = tk.StringVar(value=cur_role)
        
        for r in ['Admin', 'Provider', 'Customer']:
            tk.Radiobutton(win, text=r, variable=rv, value=r).pack()
        
        def apply():
            success, message = self.controller.update_user_role(uid, rv.get())
            if success:
                messagebox.showinfo("موفق", message)
                win.destroy()
                self.load_users()
            else:
                messagebox.showerror("خطا", message, parent=win)
        
        tk.Button(win, text="اعمال", command=apply, 
                  bg='#3498db', fg='white', width=12).pack(pady=10)

    def _delete_user(self):
        sel = self.users_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک کاربر انتخاب کنید")
            return
        
        vals = self.users_tree.item(sel[0])['values']
        user_id = vals[0]
        username = vals[1]
        role = vals[2]
        
        if role == 'Provider':
            warning_msg = f"کاربر «{username}» یک ارائه‌دهنده است.\n\nاگر این کاربر دارای رزرو فعال یا سرویس فعال باشد، امکان حذف وجود ندارد.\n\nآیا از حذف این کاربر اطمینان دارید؟"
        elif role == 'Customer':
            warning_msg = f"کاربر «{username}» یک مشتری است.\n\nاگر این کاربر دارای رزرو فعال باشد، امکان حذف وجود ندارد.\n\nآیا از حذف این کاربر اطمینان دارید؟"
        else:
            warning_msg = f"کاربر «{username}» حذف شود؟"
        
        if messagebox.askyesno("حذف کاربر", warning_msg):
            success, message = self.controller.delete_user(user_id)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_users()
            else:
                messagebox.showerror("خطا", message)
                
    # ==================== تب رزروها ====================
    
    def _tab_bookings(self):
        f = self.tab_bookings
        tb = tk.Frame(f, bg='#ecf0f1', pady=5)
        tb.pack(fill='x')
        tk.Label(tb, text='مدیریت رزروها', font=('Tahoma', 11, 'bold'), 
                 bg='#ecf0f1').pack(side='left', padx=10)
        
        for txt, clr, cmd in [
            ('✅ تأیید', '#27ae60', self._force_approve_booking),
            ('❌ رد', '#c0392b', self._force_reject_booking),
            ('🚫 لغو', '#7f8c8d', self._force_cancel_booking),
        ]:
            tk.Button(tb, text=txt, command=cmd, bg=clr, fg='white', 
                      relief='flat', padx=8).pack(side='right', padx=4)

        ff = tk.Frame(f)
        ff.pack(fill='x', padx=8, pady=(4, 0))
        tk.Label(ff, text='فیلتر:').pack(side='left')
        self._bf = tk.StringVar(value='همه')
        cb = ttk.Combobox(ff, textvariable=self._bf, 
                          values=['همه', 'Pending', 'Confirmed', 'Rejected', 'Canceled'],
                          state='readonly', width=13)
        cb.pack(side='left', padx=6)
        cb.bind('<<ComboboxSelected>>', lambda e: self.load_bookings())

        cols = ('ID', 'مشتری', 'ارائه‌دهنده', 'خدمت', 'زمان', 'وضعیت', 'پرداخت')
        self.bookings_tree = ttk.Treeview(f, columns=cols, show='headings', height=20)
        for s, bg in STATUS_BG.items():
            self.bookings_tree.tag_configure(s, background=bg)
        for col, w in zip(cols, [45, 120, 120, 160, 145, 90, 80]):
            self.bookings_tree.heading(col, text=col)
            self.bookings_tree.column(col, width=w, anchor='center')
        
        sb = ttk.Scrollbar(f, orient='vertical', command=self.bookings_tree.yview)
        self.bookings_tree.configure(yscrollcommand=sb.set)
        self.bookings_tree.pack(side='left', fill='both', expand=True, padx=(8, 0), pady=6)
        sb.pack(side='left', fill='y', pady=6)

    def load_bookings(self):
        for r in self.bookings_tree.get_children():
            self.bookings_tree.delete(r)
        filt = self._bf.get()
        for b in self.controller.get_all_bookings():
            status = b.get('status', '')
            if filt != 'همه' and status != filt:
                continue
            values = (
                b.get('id'),
                b.get('customer_name'),
                b.get('provider_name'),
                b.get('service_title'),
                b.get('start_time'),
                status,
                b.get('payment_status')
            )
            self.bookings_tree.insert('', 'end', values=values, tags=(status,))

    def get_selected_booking_id(self):
        sel = self.bookings_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک رزرو انتخاب کنید")
            return None
        return self.bookings_tree.item(sel[0])['values'][0]

    def _force_approve_booking(self):
        bid = self.get_selected_booking_id()
        if not bid:
            return
        
        from models.booking_model import BookingModel
        booking = BookingModel.get_booking_by_id(bid)
        
        if not booking:
            messagebox.showerror("خطا", "رزرو یافت نشد.")
            return
        
        if booking.get('payment_status') != 'Paid':
            messagebox.showerror("خطا", "امکان تأیید رزرو قبل از پرداخت وجود ندارد.\nمشتری ابتدا باید پرداخت را انجام دهد.")
            return
        
        if messagebox.askyesno("تأیید اجباری", f"رزرو #{bid} تأیید شود؟"):
            success, message = self.controller.force_approve_booking(bid)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_bookings()
            else:
                messagebox.showerror("خطا", message)

    def _force_reject_booking(self):
        bid = self.get_selected_booking_id()
        if not bid:
            return
        
        from models.booking_model import BookingModel
        booking = BookingModel.get_booking_by_id(bid)
        
        if not booking:
            messagebox.showerror("خطا", "رزرو یافت نشد.")
            return
        
        if booking.get('payment_status') != 'Paid':
            messagebox.showerror("خطا", "امکان رد رزرو قبل از پرداخت وجود ندارد.")
            return
        
        if messagebox.askyesno("رد اجباری", f"رزرو #{bid} رد شود؟"):
            success, message = self.controller.force_reject_booking(bid)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_bookings()
            else:
                messagebox.showerror("خطا", message)
                
    def _force_cancel_booking(self):
        bid = self.get_selected_booking_id()
        if not bid:
            return
        if messagebox.askyesno("لغو اجباری", f"رزرو #{bid} لغو شود؟"):
            success, message = self.controller.force_cancel_booking(bid)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_bookings()
            else:
                messagebox.showerror("خطا", message)

    # ==================== تب خدمات ====================
    
    def _tab_services(self):
        f = self.tab_services
        
        tb = tk.Frame(f, bg='#ecf0f1', pady=5)
        tb.pack(fill='x')
        tk.Label(tb, text='مدیریت خدمات', font=('Tahoma', 11, 'bold'), 
                bg='#ecf0f1').pack(side='left', padx=10)
        
        tk.Button(tb, text='🔄 فعال/غیرفعال', command=self._toggle_svc,
                bg='#e67e22', fg='white', relief='flat', padx=8).pack(side='right', padx=4)
        tk.Button(tb, text='🗑 حذف', command=self._delete_svc,
                bg='#e74c3c', fg='white', relief='flat', padx=8).pack(side='right', padx=4)
        
        filter_frame = tk.Frame(f, bg='#ecf0f1', pady=5)
        filter_frame.pack(fill='x', padx=8, pady=(5, 0))
        
        tk.Label(filter_frame, text="وضعیت:", bg='#ecf0f1', 
                font=('Tahoma', 10)).pack(side='left', padx=5)
        
        self.service_status_filter = tk.StringVar(value='همه')
        status_combo = ttk.Combobox(filter_frame, textvariable=self.service_status_filter,
                                    values=['همه', 'Active', 'Inactive'],
                                    state='readonly', width=10)
        status_combo.pack(side='left', padx=5)
        status_combo.bind('<<ComboboxSelected>>', lambda e: self.load_services())
        
        tk.Label(filter_frame, text="جست و جو:", bg='#ecf0f1', 
                font=('Tahoma', 10)).pack(side='left', padx=15)
        
        self.service_search_var = tk.StringVar()
        search_entry = tk.Entry(filter_frame, textvariable=self.service_search_var, width=20)
        search_entry.pack(side='left', padx=5)
        search_entry.bind('<KeyRelease>', lambda e: self.load_services())

        cols = ('ID', 'ارائه‌دهنده', 'عنوان', 'قیمت', 'وضعیت', 'تعداد رزرو')
        self.services_tree = ttk.Treeview(f, columns=cols, show='headings', height=20)
        self.services_tree.tag_configure('Active', background='#eafaf1')
        self.services_tree.tag_configure('Inactive', background='#fdecea')
        for col, w in zip(cols, [45, 130, 200, 110, 80, 90]):
            self.services_tree.heading(col, text=col)
            self.services_tree.column(col, width=w, anchor='center')
        
        sb = ttk.Scrollbar(f, orient='vertical', command=self.services_tree.yview)
        self.services_tree.configure(yscrollcommand=sb.set)
        self.services_tree.pack(side='left', fill='both', expand=True, padx=(8, 0), pady=6)
        sb.pack(side='left', fill='y', pady=6)
        
    def load_services(self):
        if not self.controller:
            return
        
        if hasattr(self, '_service_search_after') and self._service_search_after:
            self.root.after_cancel(self._service_search_after)
        
        self._service_search_after = self.root.after(300, self._do_load_services)

    def _do_load_services(self):
        if not self.controller:
            return
        
        for r in self.services_tree.get_children():
            self.services_tree.delete(r)
        
        all_services = self.controller.get_all_services()
        
        status_filter = self.service_status_filter.get() if hasattr(self, 'service_status_filter') else 'همه'
        search_text = self.service_search_var.get().strip().lower() if hasattr(self, 'service_search_var') else ''
        
        filtered_services = []
        for s in all_services:
            if status_filter != 'همه' and s.get('status') != status_filter:
                continue
            if search_text:
                provider_name = s.get('provider_name', '').lower()
                title = s.get('title', '').lower()
                if search_text not in provider_name and search_text not in title:
                    continue
            filtered_services.append(s)
        
        for s in filtered_services:
            status = s.get('status', '')
            tag = status if status in ('Active', 'Inactive') else ''
            status_text = 'فعال' if status == 'Active' else 'غیرفعال' if status == 'Inactive' else status
            values = (
                s.get('id'),
                s.get('provider_name'),
                s.get('title'),
                f"{s.get('price', 0):,} تومان",
                status_text,
                s.get('booking_count', 0)
            )
            self.services_tree.insert('', 'end', values=values, tags=(tag,))
        
        count = len(filtered_services)
        self.notebook.tab(self.tab_services, text=f'  🛠  خدمات ({count})  ')

    def _toggle_svc(self):
        sel = self.services_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یکی از خدمات را انتخاب کنید")
            return
        sid = self.services_tree.item(sel[0])['values'][0]
        success, message = self.controller.toggle_service_status(sid)
        if success:
            self.load_services()
            messagebox.showinfo("موفق", message)
        else:
            messagebox.showerror("خطا", message)

    def _delete_svc(self):
        sel = self.services_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یکی از خدمات را انتخاب کنید")
            return
        vals = self.services_tree.item(sel[0])['values']
        service_id = vals[0]
        service_title = vals[2]
        
        from models.booking_model import BookingModel
        all_bookings = self.controller.get_all_bookings()
        confirmed_bookings = [b for b in all_bookings if b.get('status') == 'Confirmed' and b.get('service_id') == service_id]
        
        if confirmed_bookings:
            messagebox.showerror("خطا", 
                f"امکان حذف سرویس «{service_title}» وجود ندارد.\n"
                f"این سرویس دارای {len(confirmed_bookings)} رزرو تأیید شده است.\n"
                "لطفاً ابتدا رزروهای مربوطه را لغو کنید.")
            return
        
        if messagebox.askyesno("حذف", f"آیا از حذف سرویس «{service_title}» و تمام بازه‌های زمانی آن اطمینان دارید؟"):
            success, message = self.controller.delete_service(service_id)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_services()
            else:
                messagebox.showerror("خطا", message)
                
    # ==================== تب نظرات ====================
    
    def _tab_reviews(self):
        f = self.tab_reviews

        filter_frame = tk.Frame(f, bg='#ecf0f1', pady=8)
        filter_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(filter_frame, text="فیلتر امتیاز:", bg='#ecf0f1', 
                 font=('Tahoma', 10)).pack(side='left', padx=5)

        self.admin_rating_filter = tk.StringVar(value='همه')
        rating_combo = ttk.Combobox(filter_frame, textvariable=self.admin_rating_filter,
                                     values=['همه', '5', '4', '3', '2', '1'],
                                     state='readonly', width=10)
        rating_combo.pack(side='left', padx=5)
        rating_combo.bind('<<ComboboxSelected>>', lambda e: self.load_reviews())

        tk.Label(filter_frame, text="نام ارائه‌دهنده:", bg='#ecf0f1', 
                 font=('Tahoma', 10)).pack(side='left', padx=15)

        self.admin_provider_filter = tk.StringVar()
        provider_entry = tk.Entry(filter_frame, textvariable=self.admin_provider_filter, width=20)
        provider_entry.pack(side='left', padx=5)
        provider_entry.bind('<KeyRelease>', lambda e: self.load_reviews())

        tk.Label(filter_frame, text="جستجو:", bg='#ecf0f1', 
                 font=('Tahoma', 10)).pack(side='left', padx=15)

        self.admin_search_var = tk.StringVar()
        search_entry = tk.Entry(filter_frame, textvariable=self.admin_search_var, width=20)
        search_entry.pack(side='left', padx=5)
        search_entry.bind('<KeyRelease>', lambda e: self.load_reviews())

        btn_frame = tk.Frame(f, bg='#ecf0f1', pady=5)
        btn_frame.pack(fill='x', padx=10)
        tk.Button(btn_frame, text="🗑 حذف نظر", command=self._delete_review,
                  bg='#e74c3c', fg='white', relief='flat', padx=10).pack(side='right', padx=4)

        cols = ('ID', 'مشتری', 'ارائه‌دهنده', 'سرویس', 'امتیاز', 'نظر', 'تاریخ ثبت')
        self.admin_reviews_tree = ttk.Treeview(f, columns=cols, show='headings', height=20)
        
        self.admin_reviews_tree.tag_configure('rating_5', background='#d5f5e3')
        self.admin_reviews_tree.tag_configure('rating_4', background='#d4efdf')
        self.admin_reviews_tree.tag_configure('rating_3', background='#fdebd0')
        self.admin_reviews_tree.tag_configure('rating_2', background='#fadbd8')
        self.admin_reviews_tree.tag_configure('rating_1', background='#f5b7b1')

        for col, w in zip(cols, [50, 120, 120, 180, 70, 350, 130]):
            self.admin_reviews_tree.heading(col, text=col)
            self.admin_reviews_tree.column(col, width=w, anchor='center')

        sb = ttk.Scrollbar(f, orient='vertical', command=self.admin_reviews_tree.yview)
        self.admin_reviews_tree.configure(yscrollcommand=sb.set)
        self.admin_reviews_tree.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=6)
        sb.pack(side='left', fill='y', pady=6)

    def load_reviews(self):
        if not self.controller:
            return
        
        if hasattr(self, '_review_search_after') and self._review_search_after:
            self.root.after_cancel(self._review_search_after)
        
        self._review_search_after = self.root.after(300, self._do_load_reviews)

    def _do_load_reviews(self):
        if not self.controller:
            return

        for r in self.admin_reviews_tree.get_children():
            self.admin_reviews_tree.delete(r)

        rating_filter = self.admin_rating_filter.get() if hasattr(self, 'admin_rating_filter') else 'همه'
        provider_filter = self.admin_provider_filter.get().strip() if hasattr(self, 'admin_provider_filter') else ''
        search_text = self.admin_search_var.get().strip().lower() if hasattr(self, 'admin_search_var') else ''

        rating_val = None if rating_filter == 'همه' else int(rating_filter)
        
        all_reviews = self.controller.get_all_reviews(limit=500, rating_filter=rating_val, 
                                                    provider_filter=provider_filter)

        filtered_reviews = []
        for r in all_reviews:
            if search_text:
                customer = r.get('customer_name', '').lower()
                provider = r.get('provider_name', '').lower()
                service = r.get('service_title', '').lower()
                comment = r.get('comment', '').lower()
                if search_text not in customer and search_text not in provider and \
                search_text not in service and search_text not in comment:
                    continue
            filtered_reviews.append(r)

        for r in filtered_reviews:
            rating = r.get('rating', 0)
            tag = f'rating_{rating}'
            
            self.admin_reviews_tree.insert('', 'end', values=(
                r.get('id'),
                r.get('customer_name'),
                r.get('provider_name'),
                r.get('service_title'),
                f"{rating}",
                r.get('comment', '—'),
                r.get('created_at', '—')[:16]
            ), tags=(tag,))

        count = len(filtered_reviews)
        self.notebook.tab(self.tab_reviews, text=f'  ⭐  نظرات ({count})  ')

    def _delete_review(self):
        sel = self.admin_reviews_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک نظر را انتخاب کنید.")
            return
        
        review_id = self.admin_reviews_tree.item(sel[0])['values'][0]
        
        if messagebox.askyesno("حذف نظر", "آیا از حذف این نظر اطمینان دارید؟"):
            success, message = self.controller.delete_review(review_id)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_reviews()
            else:
                messagebox.showerror("خطا", message)
                
    # ==================== تب داشبورد ====================
    
    def _tab_dashboard(self):
        f = self.tab_dash
        canvas = tk.Canvas(f)
        sb = ttk.Scrollbar(f, orient='vertical', command=canvas.yview)
        self._sf = ttk.Frame(canvas)
        self._sf.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=self._sf, anchor='nw')
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

        card_frame = ttk.LabelFrame(self._sf, text='  آمار کلی  ', padding=10)
        card_frame.pack(fill='x', padx=12, pady=10)
        inner = tk.Frame(card_frame)
        inner.pack()

        card_defs = [
            ('👥 کل کاربران', 'total_users', '#3498db'),
            ('📋 کل رزروها', 'total_bookings', '#9b59b6'),
            ('✅ تأیید شده', 'confirmed_bookings', '#27ae60'),
            ('📅 رزرو امروز', 'daily_bookings', '#e67e22'),
            ('📆 رزرو هفته', 'weekly_bookings', '#2980b9'),
            ('🛠 سرویس فعال', 'active_services', '#16a085'),
            ('🛠 سرویس غیرفعال', 'inactive_services', '#95a5a6'),
            ('💰 درآمد کل', 'total_income', '#f39c12'),
            ('📈 درآمد هفته', 'weekly_income', '#8e44ad'),
        ]
        self._cards = {}
        for i, (lbl, key, clr) in enumerate(card_defs):
            cell = tk.Frame(inner, bg=clr, width=145, height=72, relief='flat')
            cell.grid(row=i // 3, column=i % 3, padx=8, pady=8)
            cell.pack_propagate(False)
            tk.Label(cell, text=lbl, bg=clr, fg='white', font=('Tahoma', 9)).pack(pady=(8, 2))
            lv = tk.Label(cell, text='...', bg=clr, fg='white', font=('Tahoma', 13, 'bold'))
            lv.pack()
            self._cards[key] = lv

        role_frm = ttk.LabelFrame(self._sf, text='  تفکیک نقش کاربران  ', padding=10)
        role_frm.pack(fill='x', padx=12, pady=6)
        self._role_lbs = {}
        for role, clr in ROLE_COLORS.items():
            r = tk.Frame(role_frm)
            r.pack(fill='x', pady=2)
            tk.Label(r, text=f"{role}:", width=16, anchor='w', 
                     font=('Tahoma', 10)).pack(side='left')
            lb = tk.Label(r, text='...', font=('Tahoma', 10, 'bold'), fg=clr)
            lb.pack(side='left')
            self._role_lbs[role] = lb

        top_frm = ttk.LabelFrame(self._sf, text=' سرویسهای پرطرفدار  ', padding=10)
        top_frm.pack(fill='x', padx=12, pady=6)
        self._top_list = tk.Listbox(top_frm, height=5, font=('Tahoma', 10))
        self._top_list.pack(fill='x')

        pdf_btn_frm = tk.Frame(self._sf)
        pdf_btn_frm.pack(fill='x', padx=12, pady=4)
        tk.Button(pdf_btn_frm, text='📄 دریافت گزارش PDF آمار',
                  command=self._generate_pdf_report,
                  bg='#e74c3c', fg='white', font=('Tahoma', 10, 'bold'),
                  padx=16, pady=6).pack(side='left')

        chart_frm = ttk.LabelFrame(self._sf, text='  رزروهای ۷ روز اخیر  ', padding=10)
        chart_frm.pack(fill='both', expand=True, padx=12, pady=10)
        self._fig, self._ax = plt.subplots(figsize=(7, 3), dpi=88)
        self._fig.patch.set_facecolor('#f8f9fa')
        self._chart_cv = FigureCanvasTkAgg(self._fig, master=chart_frm)
        self._chart_cv.get_tk_widget().pack(fill='both', expand=True)

    def load_stats(self):
        stats = self.controller.get_admin_stats()
        for key, lb in self._cards.items():
            v = stats.get(key, 0)
            lb.config(text=f"{int(v):,}" if isinstance(v, (int, float)) else str(v))
        
        roles = stats.get('users_by_role', {})
        for role, lb in self._role_lbs.items():
            lb.config(text=str(roles.get(role, 0)))
        
        self._top_list.delete(0, tk.END)
        tops = self.controller.get_top_services()
        for i, s in enumerate(tops, 1):
            if isinstance(s, dict):
                title = s.get('title', '')
                count = s.get('booking_count', 0)
            else:
                title = s[0] if len(s) > 0 else ''
                count = s[1] if len(s) > 1 else 0
            self._top_list.insert(tk.END, f"  {i}.  {title}  —  {count} رزرو")
        if not tops:
            self._top_list.insert(tk.END, "  داده‌ای یافت نشد")
        
        self._ax.clear()
        daily = stats.get('daily_chart_data', [])
        if daily:
            labels = [d[0] for d in daily]
            vals = [d[1] for d in daily]
            self._ax.fill_between(labels, vals, alpha=0.18, color='#3498db')
            self._ax.plot(labels, vals, marker='o', color='#2980b9', linewidth=2, markersize=6)
            for x, y in zip(labels, vals):
                self._ax.annotate(str(y), (x, y), textcoords='offset points', 
                                  xytext=(0, 5), ha='center', fontsize=8)
            self._ax.set_facecolor('#f8f9fa')
            self._ax.set_ylabel('تعداد')
            self._ax.tick_params(axis='x', rotation=30, labelsize=8)
            self._fig.tight_layout()
        self._chart_cv.draw()

    def _generate_pdf_report(self):
        if not self.controller:
            return
        try:
            path = self.controller.generate_stats_report()
            if path:
                messagebox.showinfo("موفق", f"گزارش PDF با موفقیت ساخته شد.\n\nمسیر:\n{path}")
            else:
                messagebox.showerror("خطا", "خطا در تولید گزارش PDF")
        except Exception as e:
            messagebox.showerror("خطا", f"خطا در ساخت PDF:\n{e}")

    # ==================== تب پروفایل ====================
    
    def _tab_profile(self):
        f = self.tab_profile
        outer = tk.Frame(f)
        outer.pack(expand=True)

        frm = ttk.LabelFrame(outer, text="  🔑  تغییر رمز عبور مدیر  ", padding=20)
        frm.pack(padx=40, pady=60)

        tk.Label(frm, text="رمز عبور فعلی:", font=('Tahoma', 10), 
                 width=20, anchor='w').grid(row=0, column=0, pady=8)
        self._adm_cur = ttk.Entry(frm, show='*', width=28)
        self._adm_cur.grid(row=0, column=1, pady=8, padx=8)

        tk.Label(frm, text="رمز عبور جدید:", font=('Tahoma', 10), 
                 width=20, anchor='w').grid(row=1, column=0, pady=8)
        self._adm_new = ttk.Entry(frm, show='*', width=28)
        self._adm_new.grid(row=1, column=1, pady=8, padx=8)

        tk.Label(frm, text="تکرار رمز جدید:", font=('Tahoma', 10), 
                 width=20, anchor='w').grid(row=2, column=0, pady=8)
        self._adm_confirm = ttk.Entry(frm, show='*', width=28)
        self._adm_confirm.grid(row=2, column=1, pady=8, padx=8)

        tk.Button(frm, text="تغییر رمز عبور", command=self._change_admin_password,
                  bg='#2ecc71', fg='white', font=('Tahoma', 10, 'bold'),
                  width=20, pady=6).grid(row=3, column=0, columnspan=2, pady=20)

    def _change_admin_password(self):
        cur = self._adm_cur.get()
        new = self._adm_new.get()
        confirm = self._adm_confirm.get()
        
        if not cur or not new or not confirm:
            messagebox.showwarning("خطا", "تمام فیلدها الزامی‌اند")
            return
        if new != confirm:
            messagebox.showerror("خطا", "رمز جدید و تکرار آن مطابقت ندارند")
            return
        
        result = self.controller.change_admin_password(cur, new)
        
        if result == PasswordChangeResult.OK:
            messagebox.showinfo("موفق", "رمز عبور با موفقیت تغییر کرد")
            self._adm_cur.delete(0, 'end')
            self._adm_new.delete(0, 'end')
            self._adm_confirm.delete(0, 'end')
        elif result == PasswordChangeResult.EMPTY:
            messagebox.showwarning("خطا", "تمام فیلدها الزامی‌اند")
        elif result == PasswordChangeResult.WRONG_PASSWORD:
            messagebox.showerror("خطا", "رمز عبور فعلی اشتباه است")