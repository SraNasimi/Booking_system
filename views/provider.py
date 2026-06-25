import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import calendar
from datetime import datetime, date, timedelta

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from controllers.provider_controller import PasswordChangeResult


class ProviderView:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.root.title("پنل ارائه‌دهنده")
        self.root.geometry("1050x720")
        self._service_search_after = None
        self._booking_search_after = None
        self._review_search_after = None
        
        # برای تایمر اعلان‌ها
        self.notification_update_id = None
        self.provider_unread_count = 0

        # نوار بالا
        topbar = tk.Frame(self.root, bg='#2c3e50', height=44)
        topbar.pack(fill='x')
        topbar.pack_propagate(False)
        tk.Label(topbar, text='🛠  پنل ارائه‌دهنده', bg='#2c3e50', fg='white',
                 font=('Tahoma', 13, 'bold')).pack(side='left', padx=14)
        tk.Button(topbar, text='🚪 خروج', command=self.logout,
                  bg='#e74c3c', fg='white', font=('Tahoma', 10, 'bold'),
                  relief='flat', padx=12, pady=2).pack(side='right', padx=10, pady=6)

        # تب‌ها
        nb = ttk.Notebook(root)
        nb.pack(fill='both', expand=True, padx=4, pady=4)
        self.notebook = nb

        self.tab_dash = ttk.Frame(nb)
        self.tab_svc = ttk.Frame(nb)
        self.tab_slots = ttk.Frame(nb)
        self.tab_book = ttk.Frame(nb)
        self.tab_reviews = ttk.Frame(nb)
        self.tab_notifications = ttk.Frame(nb)
        self.tab_profile = ttk.Frame(nb)

        nb.add(self.tab_dash, text='  📊  داشبورد  ')
        nb.add(self.tab_svc, text='  🗂  سرویس‌ها  ')
        nb.add(self.tab_slots, text='  🕐  بازه‌های زمانی  ')
        nb.add(self.tab_book, text='  📋  رزروها  ')
        nb.add(self.tab_reviews, text='  ⭐  نظرات  ')
        nb.add(self.tab_notifications, text='  🔔  اعلان‌ها  ')
        nb.add(self.tab_profile, text='  👤  پروفایل  ')

        # ساخت تب‌ها
        self._setup_dashboard()
        self._setup_services()
        self._setup_slots()
        self._setup_bookings()
        self._setup_reviews()
        self._setup_notifications()
        self._setup_profile()

        nb.bind("<<NotebookTabChanged>>", self._on_tab)

        if self.controller is not None:
            self.root.after(100, self._initial_load)
        
        # شروع تایمر برای به‌روزرسانی خودکار اعلان‌ها
        self.schedule_notification_update()

    def _initial_load(self):
        self.load_services()
        self.load_bookings()
        self.load_dashboard_data()
        self.load_profile_info()
        self.load_reviews()
        self.load_notifications()

    def _on_tab(self, event):
        txt = self.notebook.tab(self.notebook.select(), 'text').strip()
        if not self.controller:
            return
        if 'داشبورد' in txt:
            self.load_dashboard_data()
        elif 'سرویس' in txt:
            self.load_services()
        elif 'بازه' in txt:
            self._refresh_slots_tab()
        elif 'رزرو' in txt:
            self.load_bookings()
        elif 'نظرات' in txt:
            self.load_reviews()
        elif 'اعلان' in txt:
            self.load_notifications()
        elif 'پروفایل' in txt:
            self.load_profile_info()

    def logout(self):
        if self.notification_update_id:
            self.root.after_cancel(self.notification_update_id)
        if messagebox.askyesno("خروج", "از پنل ارائه‌دهنده خارج می‌شوید؟"):
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
        if not self.controller or not self.controller.provider_id:
            self.schedule_notification_update()
            return
        
        try:
            from models.notification_model import NotificationModel
            old_count = self.provider_unread_count
            
            new_count = NotificationModel.get_unread_count(self.controller.provider_id)
            
            if new_count != old_count:
                self.provider_unread_count = new_count
                self.update_unread_badge()
                self.load_notifications()
                if new_count > old_count:
                    self.provider_unread_badge.config(text=str(new_count))
        except Exception as e:
            print(f"Error checking notifications: {e}")
        
        self.schedule_notification_update()

    # ==================== تب اعلان‌ها ====================
    
    # در views/provider.py، متد _setup_notifications را اصلاح کنید:

    def _setup_notifications(self):
        """راه‌اندازی تب اعلان‌ها برای ارائه‌دهنده"""
        f = self.tab_notifications
        
        header_frame = tk.Frame(f)
        header_frame.pack(fill='x', padx=10, pady=10)
        
        self.provider_unread_label = tk.Label(header_frame, text="🔔 اعلان‌ها", font=('Tahoma', 12, 'bold'))
        self.provider_unread_label.pack(side='left')
        
        self.provider_unread_badge = tk.Label(header_frame, text="0", bg='red', fg='white', 
                                            font=('Tahoma', 9, 'bold'), padx=5, pady=2)
        self.provider_unread_badge.pack(side='left', padx=10)
        
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
        self.provider_notifications_tree = ttk.Treeview(f, columns=cols, show="headings", height=16)
        
        for col, w in zip(cols, [50, 500, 150, 100]):
            self.provider_notifications_tree.heading(col, text=col)
            self.provider_notifications_tree.column(col, width=w, anchor="center")
        
        self.provider_notifications_tree.tag_configure('unread', background='#fff3cd')
        self.provider_notifications_tree.tag_configure('read', background='#ffffff')
        
        sb = ttk.Scrollbar(f, orient='vertical', command=self.provider_notifications_tree.yview)
        self.provider_notifications_tree.configure(yscrollcommand=sb.set)
        self.provider_notifications_tree.pack(side='left', fill="both", expand=True, padx=10, pady=5)
        sb.pack(side='left', fill='y', pady=5)
        
        self.provider_notifications_tree.bind('<Double-1>', self._mark_notification_read)
        self.provider_notifications_tree.bind('<Button-3>', self._show_delete_menu)  # کلیک راست

    def _show_delete_menu(self, event):
        """نمایش منوی حذف با کلیک راست"""
        item = self.provider_notifications_tree.identify_row(event.y)
        if not item:
            return
        
        self.provider_notifications_tree.selection_set(item)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="🗑 حذف این اعلان", command=self._delete_selected_notification)
        menu.post(event.x_root, event.y_root)

    def _delete_selected_notification(self):
        """حذف اعلان انتخاب شده"""
        sel = self.provider_notifications_tree.selection()
        if not sel:
            return
        
        values = self.provider_notifications_tree.item(sel[0])['values']
        notif_id = values[0]
        
        if messagebox.askyesno("حذف اعلان", "آیا از حذف این اعلان اطمینان دارید؟"):
            from models.notification_model import NotificationModel
            success, message = NotificationModel.delete_notification(notif_id, self.controller.provider_id)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_notifications()
            else:
                messagebox.showerror("خطا", message)

    def delete_read_notifications(self):
        """حذف اعلان‌های خوانده شده"""
        if messagebox.askyesno("حذف", "آیا از حذف همه اعلان‌های خوانده شده اطمینان دارید؟"):
            from models.notification_model import NotificationModel
            success, message = NotificationModel.delete_read_notifications(self.controller.provider_id)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_notifications()
            else:
                messagebox.showerror("خطا", message)

    def delete_all_notifications(self):
        """حذف همه اعلان‌ها"""
        if messagebox.askyesno("حذف", "آیا از حذف همه اعلان‌ها اطمینان دارید؟ این عمل قابل بازگشت نیست."):
            from models.notification_model import NotificationModel
            success, message = NotificationModel.delete_all_notifications(self.controller.provider_id)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_notifications()
            else:
                messagebox.showerror("خطا", message)
                
    def load_notifications(self):
        if not self.controller or not self.controller.provider_id:
            return
        
        for r in self.provider_notifications_tree.get_children():
            self.provider_notifications_tree.delete(r)
        
        from models.notification_model import NotificationModel
        notifications = NotificationModel.get_user_notifications(self.controller.provider_id, limit=100)
        
        icon_map = {
            'booking_created': '📅', 'booking_confirmed': '✅', 'booking_rejected': '❌',
            'booking_canceled': '🚫', 'payment_success': '💰', 'profile': '👤',
            'security': '🔒', 'report': '📄', 'service_management': '🛠️',
            'slot_management': '🕐', 'review_received': '⭐', 'review_deleted': '⚠️',
            'admin_action': '⚙️'
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
            
            self.provider_notifications_tree.insert("", "end", values=(
                notif_id, display_message, created_at, status
            ), tags=(tag,))
        
        self.update_unread_badge()

    def update_unread_badge(self):
        if not self.controller or not self.controller.provider_id:
            return
        
        from models.notification_model import NotificationModel
        count = NotificationModel.get_unread_count(self.controller.provider_id)
        self.provider_unread_count = count
        self.provider_unread_badge.config(text=str(count) if count > 0 else "0")
        
        if count > 0:
            self.notebook.tab(self.tab_notifications, text=f'  🔔  اعلان‌ها ({count})  ')
        else:
            self.notebook.tab(self.tab_notifications, text='  🔔  اعلان‌ها  ')

    def _mark_notification_read(self, event):
        sel = self.provider_notifications_tree.selection()
        if not sel:
            return
        
        values = self.provider_notifications_tree.item(sel[0])['values']
        notif_id = values[0]
        
        from models.notification_model import NotificationModel
        if NotificationModel.mark_as_read(notif_id, self.controller.provider_id):
            self.provider_notifications_tree.item(sel[0], values=(
                values[0], values[1], values[2], "✓ خوانده شده"
            ), tags=('read',))
            self.update_unread_badge()

    def mark_all_notifications_read(self):
        from models.notification_model import NotificationModel
        if NotificationModel.mark_all_as_read(self.controller.provider_id):
            for item in self.provider_notifications_tree.get_children():
                values = self.provider_notifications_tree.item(item)['values']
                self.provider_notifications_tree.item(item, values=(
                    values[0], values[1], values[2], "✓ خوانده شده"
                ), tags=('read',))
            self.update_unread_badge()
            messagebox.showinfo("موفق", "همه اعلان‌ها به عنوان خوانده شده علامت‌گذاری شدند.")

    # ==================== نظرات ====================
    
    def _setup_reviews(self):
        f = self.tab_reviews

        summary_frame = tk.LabelFrame(f, text="📊 خلاصه نظرات", padx=10, pady=8, font=('Tahoma', 10, 'bold'))
        summary_frame.pack(fill='x', padx=10, pady=8)

        self.summary_labels = {}
        summary_inner = tk.Frame(summary_frame)
        summary_inner.pack()

        stats = [
            ('total_reviews', '📝 تعداد نظرات', '#3498db'),
            ('avg_rating', '⭐ میانگین امتیاز', '#f39c12'),
            ('rating_5', '5 ستاره', '#27ae60'),
            ('rating_4', '4 ستاره', '#2ecc71'),
            ('rating_3', '3 ستاره', '#f1c40f'),
            ('rating_2', '2 ستاره', '#e67e22'),
            ('rating_1', '1 ستاره', '#e74c3c'),
        ]

        for i, (key, label, color) in enumerate(stats):
            card = tk.Frame(summary_inner, bg=color, width=130, height=65, relief='flat')
            card.grid(row=i // 4, column=i % 4, padx=6, pady=6)
            card.pack_propagate(False)
            tk.Label(card, text=label, bg=color, fg='white', font=('Tahoma', 9)).pack(pady=(5, 2))
            value_lbl = tk.Label(card, text='...', bg=color, fg='white', font=('Tahoma', 14, 'bold'))
            value_lbl.pack()
            self.summary_labels[key] = value_lbl

        filter_frame = tk.Frame(f, bg='#ecf0f1', pady=5)
        filter_frame.pack(fill='x', padx=10, pady=(0, 8))

        tk.Label(filter_frame, text="جستجو در نظرات:", bg='#ecf0f1', 
                 font=('Tahoma', 10)).pack(side='left', padx=5)

        self.review_search_var = tk.StringVar()
        search_entry = tk.Entry(filter_frame, textvariable=self.review_search_var, width=25)
        search_entry.pack(side='left', padx=5)
        search_entry.bind('<KeyRelease>', lambda e: self.load_reviews())

        tk.Label(filter_frame, text="فیلتر امتیاز:", bg='#ecf0f1', 
                 font=('Tahoma', 10)).pack(side='left', padx=15)

        self.rating_filter_var = tk.StringVar(value='همه')
        rating_combo = ttk.Combobox(filter_frame, textvariable=self.rating_filter_var,
                                     values=['همه', '5', '4', '3', '2', '1'],
                                     state='readonly', width=10)
        rating_combo.pack(side='left', padx=5)
        rating_combo.bind('<<ComboboxSelected>>', lambda e: self.load_reviews())

        cols = ('ID', 'مشتری', 'سرویس', 'امتیاز', 'نظر', 'تاریخ ثبت')
        self.reviews_tree = ttk.Treeview(f, columns=cols, show='headings', height=16)
        
        self.reviews_tree.tag_configure('rating_5', background='#d5f5e3')
        self.reviews_tree.tag_configure('rating_4', background='#d4efdf')
        self.reviews_tree.tag_configure('rating_3', background='#fdebd0')
        self.reviews_tree.tag_configure('rating_2', background='#fadbd8')
        self.reviews_tree.tag_configure('rating_1', background='#f5b7b1')

        for col, w in zip(cols, [50, 130, 200, 70, 400, 150]):
            self.reviews_tree.heading(col, text=col)
            self.reviews_tree.column(col, width=w, anchor='center')

        sb = ttk.Scrollbar(f, orient='vertical', command=self.reviews_tree.yview)
        self.reviews_tree.configure(yscrollcommand=sb.set)
        self.reviews_tree.pack(side='left', fill='both', expand=True, padx=(10, 0), pady=6)
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

        for r in self.reviews_tree.get_children():
            self.reviews_tree.delete(r)

        try:
            summary = self.controller.get_my_reviews_summary()
            for key, lbl in self.summary_labels.items():
                value = summary.get(key, 0)
                if key == 'avg_rating':
                    lbl.config(text=f"{value:.1f}")
                else:
                    lbl.config(text=str(value))
        except Exception as e:
            print(f"Error loading reviews summary: {e}")

        all_reviews = self.controller.get_my_reviews(limit=200)
        
        search_text = self.review_search_var.get().strip().lower() if hasattr(self, 'review_search_var') else ''
        rating_filter = self.rating_filter_var.get() if hasattr(self, 'rating_filter_var') else 'همه'

        filtered_reviews = []
        for r in all_reviews:
            if rating_filter != 'همه' and str(r.get('rating')) != rating_filter:
                continue
            if search_text:
                customer = r.get('customer_name', '').lower()
                comment = r.get('comment', '').lower()
                service = r.get('service_title', '').lower()
                if search_text not in customer and search_text not in comment and search_text not in service:
                    continue
            filtered_reviews.append(r)

        for r in filtered_reviews:
            rating = r.get('rating', 0)
            tag = f'rating_{rating}'
            
            self.reviews_tree.insert('', 'end', values=(
                r.get('id'),
                r.get('customer_name'),
                r.get('service_title'),
                f"{rating}",
                r.get('comment', '—'),
                r.get('created_at', '—')[:16]
            ), tags=(tag,))

        count = len(filtered_reviews)
        self.notebook.tab(self.tab_reviews, text=f'  ⭐  نظرات ({count})  ')
        
    # ==================== PDF Reports ====================
    
    def _pdf_services_report(self):
        if not self.controller:
            return
        try:
            path = self.controller.generate_services_report()
            if path:
                messagebox.showinfo("موفق", f"گزارش PDF ساخته شد.\n\nمسیر:\n{path}")
            else:
                messagebox.showerror("خطا", "خطا در تولید گزارش PDF یا سرویسی برای گزارش وجود ندارد")
        except Exception as e:
            messagebox.showerror("خطا", f"خطا: {str(e)}")
    
    def _pdf_bookings_report(self):
        if not self.controller:
            return
        try:
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
                    customer = b.get('customer_name', '').lower()
                    service = b.get('service_title', '').lower()
                    if search_text not in customer and search_text not in service:
                        continue
                filtered_bookings.append(b)
            
            if not filtered_bookings:
                messagebox.showwarning("اطلاع", "هیچ رزروی با فیلترهای انتخاب شده وجود ندارد.")
                return
            
            from reports.pdf_generator import generate_provider_bookings_report
            info = self.controller.get_profile_info()
            username = info.get('username', 'Provider') if info else 'Provider'
            
            path = generate_provider_bookings_report(username, filtered_bookings)
            if path:
                messagebox.showinfo("موفق", f"گزارش PDF ساخته شد.\n\nمسیر:\n{path}")
            else:
                messagebox.showerror("خطا", "خطا در تولید گزارش PDF")
        except ImportError:
            messagebox.showerror("خطا", "ماژول گزارش PDF یافت نشد.")
        except Exception as e:
            messagebox.showerror("خطا", f"خطا: {str(e)}")
            
    # ==================== داشبورد ====================
    def _setup_dashboard(self):
        p = self.tab_dash
        canvas = tk.Canvas(p)
        sb = ttk.Scrollbar(p, orient='vertical', command=canvas.yview)
        sf = ttk.Frame(canvas)
        sf.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=sf, anchor='nw')
        canvas.configure(yscrollcommand=sb.set)

        kf = ttk.LabelFrame(sf, text='  آمار کلی  ', padding=14)
        kf.pack(fill='x', padx=16, pady=14)
        self.lbl_services = tk.Label(kf, text='سرویس‌ها: ...', font=('Tahoma', 11))
        self.lbl_total_bookings = tk.Label(kf, text='کل رزروها: ...', font=('Tahoma', 11))
        self.lbl_income = tk.Label(kf, text='درآمد: ... تومان', font=('Tahoma', 11, 'bold'), fg='green')
        for lbl in [self.lbl_services, self.lbl_total_bookings, self.lbl_income]:
            lbl.pack(anchor='w', pady=3)

        self.status_frame = tk.LabelFrame(sf, text='تفکیک وضعیت رزروها', padx=10, pady=6)
        self.status_frame.pack(fill='x', padx=16, pady=6)
        self.status_inner = tk.Frame(self.status_frame)
        self.status_inner.pack(fill='x')

        chart_frm = ttk.LabelFrame(sf, text='  نمودار آماری  ', padding=10)
        chart_frm.pack(fill='both', expand=True, padx=16, pady=10)
        self.chart_frame = tk.Frame(chart_frm)
        self.chart_frame.pack(fill='both', expand=True)

        canvas.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')

    def load_dashboard_data(self):
        if not self.controller:
            return
        stats = self.controller.get_dashboard_stats()
        self.lbl_services.config(text=f"سرویس‌ها: {stats.get('services', 0)}")
        self.lbl_total_bookings.config(text=f"کل رزروها: {stats.get('total', 0)}")
        self.lbl_income.config(text=f"درآمد: {stats.get('income', 0):,} تومان")
        for w in self.status_inner.winfo_children():
            w.destroy()
        for st, cnt in stats.get('status_counts', {}).items():
            tk.Label(self.status_inner, text=f"  {st}: {cnt} مورد",
                     font=('Tahoma', 10)).pack(anchor='w')
        self._draw_chart(stats.get('status_counts', {}))

    def _draw_chart(self, status_counts):
        for w in self.chart_frame.winfo_children():
            w.destroy()
        if not status_counts:
            tk.Label(self.chart_frame, text="داده‌ای موجود نیست.").pack(expand=True)
            return
        try:
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.bar(list(status_counts.keys()), list(status_counts.values()),
                   color=['#3498db', '#27ae60', '#e74c3c', '#95a5a6'][:len(status_counts)])
            ax.set_title("تفکیک رزروها")
            ax.set_ylabel("تعداد")
            fig.tight_layout()
            cv = FigureCanvasTkAgg(fig, master=self.chart_frame)
            cv.draw()
            cv.get_tk_widget().pack(fill='both', expand=True)
        except Exception as e:
            print(f"chart error: {e}")

    # ==================== سرویس‌ها ====================
    def _setup_services(self):
        p = self.tab_svc

        tb = tk.Frame(p, bg='#ecf0f1', pady=6)
        tb.pack(fill='x')
        tk.Label(tb, text='مدیریت سرویس‌ها', font=('Tahoma', 11, 'bold'),
                 bg='#ecf0f1').pack(side='left', padx=10)

        for txt, clr, cmd in [
            ('+ افزودن', '#2ecc71', self._add_service_win),
            ('✏ ویرایش', '#3498db', self._edit_service_win),
            ('🗑 حذف', '#e74c3c', self._delete_service),
            ('🔄 فعال/غیرفعال', '#e67e22', self._toggle_service),
            ('📄 گزارش PDF', '#8e44ad', self._pdf_services_report),
        ]:
            tk.Button(tb, text=txt, command=cmd, bg=clr, fg='white',
                      relief='flat', padx=8).pack(side='right', padx=4)

        filter_frame = tk.Frame(p, bg='#ecf0f1', pady=5)
        filter_frame.pack(fill='x', padx=8, pady=(5, 0))
        
        tk.Label(filter_frame, text="وضعیت:", bg='#ecf0f1', 
                 font=('Tahoma', 10)).pack(side='left', padx=5)
        
        self.service_status_filter = tk.StringVar(value='همه')
        status_combo = ttk.Combobox(filter_frame, textvariable=self.service_status_filter,
                                     values=['همه', 'Active', 'Inactive'],
                                     state='readonly', width=10)
        status_combo.pack(side='left', padx=5)
        status_combo.bind('<<ComboboxSelected>>', lambda e: self.load_services())
        
        tk.Label(filter_frame, text="جستجو:", bg='#ecf0f1', 
                 font=('Tahoma', 10)).pack(side='left', padx=15)
        
        self.service_search_var = tk.StringVar()
        search_entry = tk.Entry(filter_frame, textvariable=self.service_search_var, width=20)
        search_entry.pack(side='left', padx=5)
        search_entry.bind('<KeyRelease>', lambda e: self.load_services())
        
        cols = ('ID', 'عنوان', 'قیمت', 'وضعیت', 'دسته‌بندی')
        self.service_tree = ttk.Treeview(p, columns=cols, show='headings', height=18)
        self.service_tree.tag_configure('Active', background='#eafaf1')
        self.service_tree.tag_configure('Inactive', background='#fdecea')
        for col, w in zip(cols, [45, 220, 110, 90, 140]):
            self.service_tree.heading(col, text=col)
            self.service_tree.column(col, width=w, anchor='center')
        
        sb = ttk.Scrollbar(p, orient='vertical', command=self.service_tree.yview)
        self.service_tree.configure(yscrollcommand=sb.set)
        self.service_tree.pack(side='left', fill='both', expand=True, padx=(8, 0), pady=6)
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
        for r in self.service_tree.get_children():
            self.service_tree.delete(r)
        
        all_services = self.controller.get_my_services()
        status_filter = self.service_status_filter.get() if hasattr(self, 'service_status_filter') else 'همه'
        search_text = self.service_search_var.get().strip().lower() if hasattr(self, 'service_search_var') else ''
        
        filtered_services = []
        for s in all_services:
            if status_filter != 'همه' and s.get('status') != status_filter:
                continue
            if search_text:
                title = s.get('title', '').lower()
                category = s.get('category', '').lower()
                if search_text not in title and search_text not in category:
                    continue
            filtered_services.append(s)
        
        for s in filtered_services:
            status = s.get('status', '')
            tag = status if status in ('Active', 'Inactive') else ''
            status_text = 'فعال' if status == 'Active' else 'غیرفعال'
            values = (
                s.get('id'),
                s.get('title'),
                f"{s.get('price', 0):,} تومان",
                status_text,
                s.get('category', 'بدون دسته‌بندی')
            )
            self.service_tree.insert('', 'end', values=values, tags=(tag,))
        
        count = len(filtered_services)
        self.notebook.tab(self.tab_svc, text=f'  🗂  سرویس‌ها ({count})  ')

    def _add_service_win(self):
        self._service_form_win(edit_mode=False)

    def _edit_service_win(self):
        sel = self.service_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک سرویس انتخاب کنید.")
            return
        vals = self.service_tree.item(sel[0])['values']
        svc = self.controller.get_my_services()
        row = next((s for s in svc if s.get('id') == vals[0]), None)
        self._service_form_win(edit_mode=True, existing=row)

    def _service_form_win(self, edit_mode=False, existing=None):
        from tkinter import simpledialog

        win = tk.Toplevel(self.root)
        win.title("ویرایش سرویس" if edit_mode else "افزودن سرویس جدید")
        win.geometry("420x420")
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="عنوان سرویس:", font=('Tahoma', 10)).pack(anchor='w', padx=20, pady=(12, 0))
        e_title = tk.Entry(win, width=42)
        e_title.pack(padx=20)

        tk.Label(win, text="توضیحات:", font=('Tahoma', 10)).pack(anchor='w', padx=20, pady=(8, 0))
        e_desc = tk.Text(win, width=42, height=3)
        e_desc.pack(padx=20)

        row1 = tk.Frame(win)
        row1.pack(fill='x', padx=20, pady=(8, 0))
        tk.Label(row1, text="قیمت (تومان):", font=('Tahoma', 10)).pack(side='left')
        e_price = tk.Entry(row1, width=12)
        e_price.pack(side='left', padx=8)

        row2 = tk.Frame(win)
        row2.pack(fill='x', padx=20, pady=(8, 0))
        tk.Label(row2, text="دسته‌بندی:", font=('Tahoma', 10)).pack(side='left')
        cats = self.controller.get_categories()
        cat_names = [c['name'] for c in cats] if cats else []
        cat_var = tk.StringVar(value=cat_names[0] if cat_names else '')
        cat_cb = ttk.Combobox(row2, textvariable=cat_var, values=cat_names + ['+ دسته جدید...'],
                            state='readonly', width=18)
        cat_cb.pack(side='left', padx=8)

        def on_cat_change(e):
            if cat_var.get() == '+ دسته جدید...':
                new_cat = simpledialog.askstring("دسته جدید", "نام دسته‌بندی جدید:")
                if new_cat:
                    self.controller.add_category(new_cat.strip())
                    cats2 = self.controller.get_categories()
                    names2 = [c['name'] for c in cats2] if cats2 else []
                    cat_cb['values'] = names2 + ['+ دسته جدید...']
                    cat_var.set(new_cat.strip())

        cat_cb.bind('<<ComboboxSelected>>', on_cat_change)

        row3 = tk.Frame(win)
        row3.pack(fill='x', padx=20, pady=(8, 0))
        tk.Label(row3, text="وضعیت:", font=('Tahoma', 10)).pack(side='left')
        status_var = tk.StringVar(value='Active')
        ttk.Radiobutton(row3, text='فعال (Active)', variable=status_var, value='Active').pack(side='left', padx=8)
        ttk.Radiobutton(row3, text='غیرفعال (Inactive)', variable=status_var, value='Inactive').pack(side='left')

        if edit_mode and existing:
            e_title.insert(0, existing.get('title', ''))
            e_price.insert(0, str(existing.get('price', '')))
            status_var.set(existing.get('status', 'Active'))
            cat_label = existing.get('category', '')
            if cat_label in cat_names:
                cat_var.set(cat_label)

        def get_cat_id():
            name = cat_var.get()
            if name == '+ دسته جدید...' or not name:
                return None
            for cat in self.controller.get_categories():
                if cat['name'] == name:
                    return cat['id']
            return None

        def save():
            title = e_title.get().strip()
            desc = e_desc.get("1.0", tk.END).strip()
            price = e_price.get().strip()
            status = status_var.get()

            if not title or not price:
                messagebox.showerror("خطا", "عنوان و قیمت الزامی‌اند.", parent=win)
                return
            try:
                price_f = float(price)
            except ValueError:
                messagebox.showerror("خطا", "قیمت باید عدد باشد.", parent=win)
                return

            cid = get_cat_id()
            if edit_mode and existing:
                ok = self.controller.edit_service(
                    existing.get('id'), title, desc, price_f,
                    category_id=cid, status=status
                )
            else:
                ok = self.controller.add_service(
                    title, desc, price_f,
                    category_id=cid, status=status
                )

            if ok:
                messagebox.showinfo("موفق", "سرویس ویرایش شد." if edit_mode else "سرویس اضافه شد.", parent=win)
                win.destroy()
                self.load_services()
                self._refresh_slots_tab()
            else:
                messagebox.showerror("خطا", "خطا در ذخیره.", parent=win)

        tk.Button(win, text="ذخیره", command=save,
                bg='#27ae60', fg='white', width=16, font=('Tahoma', 10)).pack(pady=18)

    def _delete_service(self):
        sel = self.service_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک سرویس انتخاب کنید.")
            return
        vals = self.service_tree.item(sel[0])['values']
        service_id = vals[0]
        service_title = vals[1]
        
        from models.booking_model import BookingModel
        bookings = BookingModel.get_provider_bookings(self.controller.provider_id)
        confirmed_bookings = [b for b in bookings if b.get('status') == 'Confirmed' and b.get('service_id') == service_id]
        
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
                self._refresh_slots_tab()
            else:
                messagebox.showerror("خطا", message)

    def _toggle_service(self):
        sel = self.service_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک سرویس انتخاب کنید.")
            return
        sid = self.service_tree.item(sel[0])['values'][0]
        self.controller.toggle_service_status(sid)
        self.load_services()

    # ==================== بازه‌های زمانی ====================
    def _setup_slots(self):
        from datetime import date

        p = self.tab_slots

        top = tk.Frame(p, bg='#ecf0f1', pady=6)
        top.pack(fill='x')
        tk.Label(top, text='سرویس:', bg='#ecf0f1', font=('Tahoma', 10)).pack(side='left', padx=10)
        self._slot_svc_var = tk.StringVar()
        self._slot_svc_cb = ttk.Combobox(top, textvariable=self._slot_svc_var,
                                        state='readonly', width=32)
        self._slot_svc_cb.pack(side='left', padx=6)
        self._slot_svc_cb.bind('<<ComboboxSelected>>', lambda e: self._load_slots())

        self._svc_status_lbl = tk.Label(top, text='', font=('Tahoma', 10), bg='#ecf0f1')
        self._svc_status_lbl.pack(side='left', padx=10)
        tk.Button(top, text='🔄 فعال/غیرفعال سرویس',
                command=self._toggle_selected_svc,
                bg='#e67e22', fg='white', relief='flat', padx=8).pack(side='left', padx=4)

        cols = ('ID', 'شروع', 'پایان', 'مدت (دقیقه)', 'وضعیت')
        self.slots_tree = ttk.Treeview(p, columns=cols, show='headings', height=11)
        self.slots_tree.tag_configure('Active', background='#eafaf1')
        self.slots_tree.tag_configure('Inactive', background='#fdecea')
        for col, w in zip(cols, [55, 180, 180, 80, 80]):
            self.slots_tree.heading(col, text=col)
            self.slots_tree.column(col, width=w, anchor='center')
        sb_s = ttk.Scrollbar(p, orient='vertical', command=self.slots_tree.yview)
        self.slots_tree.configure(yscrollcommand=sb_s.set)
        self.slots_tree.pack(side='left', fill='both', expand=True, padx=(8, 0), pady=4)
        sb_s.pack(side='left', fill='y', pady=4)

        form_outer = tk.Frame(p)
        form_outer.pack(fill='x', padx=8, pady=4)

        form = tk.LabelFrame(form_outer, text="افزودن / ویرایش بازه", padx=10, pady=8)
        form.pack(fill='x')

        date_frame = tk.LabelFrame(form, text="انتخاب تاریخ", padx=10, pady=5)
        date_frame.pack(fill='x', pady=4)
        
        self._slot_date_var = tk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        
        top_date_frame = tk.Frame(date_frame)
        top_date_frame.pack(fill='x', pady=2)
        tk.Label(top_date_frame, text="تاریخ انتخاب شده:", width=15, anchor='w').pack(side='left')
        date_label = tk.Entry(top_date_frame, textvariable=self._slot_date_var, width=12, 
                              state='readonly', relief='sunken', bg='#f0f0f0')
        date_label.pack(side='left', padx=5)
        
        cal_frame = tk.Frame(date_frame, bg='#f0f0f0', relief='sunken', bd=1)
        cal_frame.pack(fill='x', pady=5)
        
        self._cal_year = tk.IntVar(value=date.today().year)
        self._cal_month = tk.IntVar(value=date.today().month)
        
        cal_header = tk.Frame(cal_frame, bg='#2c3e50')
        cal_header.pack(fill='x')
        tk.Button(cal_header, text='◀', command=self._cal_prev_month,
                  bg='#2c3e50', fg='white', relief='flat', width=3).pack(side='left')
        self._cal_title = tk.Label(cal_header, text='', bg='#2c3e50', fg='white',
                                    font=('Tahoma', 10, 'bold'), width=18)
        self._cal_title.pack(side='left', expand=True)
        tk.Button(cal_header, text='▶', command=self._cal_next_month,
                  bg='#2c3e50', fg='white', relief='flat', width=3).pack(side='right')
        
        days_frame = tk.Frame(cal_frame, bg='#ecf0f1')
        days_frame.pack(fill='x')
        for d in ['شن', 'یک', 'دو', 'سه', 'چه', 'پن', 'جم']:
            tk.Label(days_frame, text=d, width=4, bg='#ecf0f1', font=('Tahoma', 8, 'bold')).pack(side='left')
        
        self._cal_grid = tk.Frame(cal_frame, bg='white')
        self._cal_grid.pack(fill='x')
        
        self._cal_update()

        r2 = tk.Frame(form)
        r2.pack(fill='x', pady=4)
        tk.Label(r2, text="شروع:", width=10, anchor='w').pack(side='left')
        self._start_h = tk.Spinbox(r2, from_=0, to=23, width=3, format='%02.0f')
        self._start_h.pack(side='left')
        tk.Label(r2, text=":").pack(side='left')
        self._start_m = tk.Spinbox(r2, from_=0, to=59, width=3, format='%02.0f')
        self._start_m.pack(side='left')

        r3 = tk.Frame(form)
        r3.pack(fill='x', pady=4)
        tk.Label(r3, text="پایان:", width=10, anchor='w').pack(side='left')
        self._end_h = tk.Spinbox(r3, from_=0, to=23, width=3, format='%02.0f')
        self._end_h.pack(side='left')
        tk.Label(r3, text=":").pack(side='left')
        self._end_m = tk.Spinbox(r3, from_=0, to=59, width=3, format='%02.0f')
        self._end_m.pack(side='left')

        btn_f = tk.Frame(form)
        btn_f.pack(pady=6)
        tk.Button(btn_f, text='➕ افزودن بازه', command=self._add_slot,
                bg='#2ecc71', fg='white', padx=10).pack(side='left', padx=6)
        tk.Button(btn_f, text='✏ ذخیره ویرایش', command=self._save_edit_slot,
                bg='#3498db', fg='white', padx=10).pack(side='left', padx=6)
        tk.Button(btn_f, text='🔄 فعال/غیرفعال', command=self._toggle_slot,
                bg='#e67e22', fg='white', padx=10).pack(side='left', padx=6)
        tk.Button(btn_f, text='🗑 حذف بازه', command=self._delete_slot,
                bg='#e74c3c', fg='white', padx=10).pack(side='left', padx=6)

        self.slots_tree.bind('<<TreeviewSelect>>', self._on_slot_select)

    def _cal_update(self):
        for w in self._cal_grid.winfo_children():
            w.destroy()
        
        year = self._cal_year.get()
        month = self._cal_month.get()
        
        self._cal_title.config(text=f"{year} / {month:02d}")
        
        cal = calendar.monthcalendar(year, month)
        today = date.today()
        
        for week in cal:
            row = tk.Frame(self._cal_grid, bg='white')
            row.pack()
            for day in week:
                if day == 0:
                    tk.Label(row, width=4, text='', bg='white').pack(side='left')
                else:
                    d = date(year, month, day)
                    is_today = (d == today)
                    is_past = (d < today)
                    
                    if is_past:
                        btn = tk.Button(row, text=str(day), width=4,
                                       relief='flat',
                                       bg='#cccccc', fg='#999999',
                                       font=('Tahoma', 9), state='disabled')
                    else:
                        btn_bg = '#3498db' if is_today else 'white'
                        btn_fg = 'white' if is_today else 'black'
                        btn = tk.Button(row, text=str(day), width=4,
                                       relief='flat',
                                       bg=btn_bg, fg=btn_fg,
                                       font=('Tahoma', 9),
                                       command=lambda dt=d: self._cal_select_date(dt))
                    btn.pack(side='left', padx=1, pady=1)

    def _cal_prev_month(self):
        if self._cal_month.get() == 1:
            self._cal_year.set(self._cal_year.get() - 1)
            self._cal_month.set(12)
        else:
            self._cal_month.set(self._cal_month.get() - 1)
        self._cal_update()

    def _cal_next_month(self):
        if self._cal_month.get() == 12:
            self._cal_year.set(self._cal_year.get() + 1)
            self._cal_month.set(1)
        else:
            self._cal_month.set(self._cal_month.get() + 1)
        self._cal_update()

    def _cal_select_date(self, selected_date):
        self._slot_date_var.set(selected_date.strftime('%Y-%m-%d'))

    def _get_selected_svc_id(self):
        idx = self._slot_svc_cb.current()
        if idx < 0:
            return None
        svcs = self.controller.get_my_services()
        if idx >= len(svcs):
            return None
        return svcs[idx].get('id')

    def _toggle_selected_svc(self):
        sid = self._get_selected_svc_id()
        if sid is None:
            messagebox.showwarning("هشدار", "یک سرویس انتخاب کنید.")
            return
        self.controller.toggle_service_status(sid)
        self.load_services()
        self._refresh_slots_tab()

    def _refresh_slots_tab(self):
        if not self.controller:
            return
        svcs = self.controller.get_my_services()
        names = [f"{s.get('id')} — {s.get('title')} ({s.get('status')})" for s in svcs]
        self._slot_svc_cb['values'] = names
        if names:
            cur = self._slot_svc_cb.current()
            if cur < 0 or cur >= len(names):
                self._slot_svc_cb.current(0)
            self._load_slots()
        else:
            for r in self.slots_tree.get_children():
                self.slots_tree.delete(r)
            self._svc_status_lbl.config(text='')

    def _load_slots(self):
        if not self.controller:
            return
        sid = self._get_selected_svc_id()
        if sid is None:
            return

        svcs = self.controller.get_my_services()
        idx = self._slot_svc_cb.current()
        if 0 <= idx < len(svcs):
            st = svcs[idx].get('status', '')
            self._svc_status_lbl.config(
                text=f"وضعیت: {st}",
                fg='green' if st == 'Active' else 'red'
            )

        for r in self.slots_tree.get_children():
            self.slots_tree.delete(r)

        for sl in self.controller.get_slots(sid):
            tag = sl.get('status', '')
            
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
            
            values = (sl.get('id'), start_time, end_time, duration, tag)
            self.slots_tree.insert('', 'end', values=values, tags=(tag,))

    def _on_slot_select(self, event):
        sel = self.slots_tree.selection()
        if not sel:
            return
        vals = self.slots_tree.item(sel[0])['values']
        try:
            start_dt = vals[1]
            end_dt = vals[2]
            d_part = start_dt[:10]
            s_time = start_dt[11:16]
            e_time = end_dt[11:16]
            self._slot_date_var.set(d_part)
            self._start_h.delete(0, tk.END)
            self._start_h.insert(0, s_time[:2])
            self._start_m.delete(0, tk.END)
            self._start_m.insert(0, s_time[3:])
            self._end_h.delete(0, tk.END)
            self._end_h.insert(0, e_time[:2])
            self._end_m.delete(0, tk.END)
            self._end_m.insert(0, e_time[3:])
            
            try:
                y, m, d = map(int, d_part.split('-'))
                self._cal_year.set(y)
                self._cal_month.set(m)
                self._cal_update()
            except:
                pass
        except Exception:
            pass

    def _add_slot(self):
        sid = self._get_selected_svc_id()
        if sid is None:
            messagebox.showwarning("هشدار", "ابتدا یک سرویس انتخاب کنید.")
            return

        d = self._slot_date_var.get()
        start = f"{int(self._start_h.get()):02d}:{int(self._start_m.get()):02d}"
        end = f"{int(self._end_h.get()):02d}:{int(self._end_m.get()):02d}"

        if not d:
            messagebox.showerror("خطا", "تاریخ را انتخاب کنید.")
            return

        try:
            selected_date = datetime.strptime(d, '%Y-%m-%d').date()
            today = date.today()
            
            if selected_date < today:
                messagebox.showerror("خطا", "امکان تعریف بازه زمانی برای تاریخ‌های گذشته وجود ندارد.")
                return
            
            start_dt_str = f"{d} {start}:00"
            end_dt_str = f"{d} {end}:00"
            
            start_dt = datetime.strptime(start_dt_str, '%Y-%m-%d %H:%M:%S')
            end_dt = datetime.strptime(end_dt_str, '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            
            if start_dt <= now:
                messagebox.showerror("خطا", 
                    f"امکان تعریف بازه زمانی برای زمان گذشته وجود ندارد.\n"
                    f"زمان شروع باید بعد از زمان فعلی ({now.strftime('%H:%M:%S')}) باشد.")
                return
            
            if end_dt <= start_dt:
                messagebox.showerror("خطا", "ساعت پایان باید بعد از ساعت شروع باشد.")
                return
                
        except ValueError as e:
            messagebox.showerror("خطا", f"فرمت تاریخ/ساعت نامعتبر است: {e}")
            return

        if self.controller.add_slot_for_service(sid, start_dt_str, end_dt_str):
            messagebox.showinfo("موفق", "بازه اضافه شد.")
            self._load_slots()
        else:
            messagebox.showerror("خطا", "تداخل زمانی وجود دارد یا خطا رخ داد.")
            
    def _save_edit_slot(self):
        sel = self.slots_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک بازه را انتخاب کنید.")
            return

        slot_id = self.slots_tree.item(sel[0])['values'][0]
        sid = self._get_selected_svc_id()
        if sid is None:
            return

        d = self._slot_date_var.get()
        start = f"{int(self._start_h.get()):02d}:{int(self._start_m.get()):02d}"
        end = f"{int(self._end_h.get()):02d}:{int(self._end_m.get()):02d}"

        if not d:
            messagebox.showerror("خطا", "تاریخ را انتخاب کنید.")
            return

        try:
            selected_date = datetime.strptime(d, '%Y-%m-%d').date()
            today = date.today()
            
            if selected_date < today:
                messagebox.showerror("خطا", "امکان تعریف بازه زمانی برای تاریخ‌های گذشته وجود ندارد.")
                return
            
            start_dt_str = f"{d} {start}:00"
            end_dt_str = f"{d} {end}:00"
            
            start_dt = datetime.strptime(start_dt_str, '%Y-%m-%d %H:%M:%S')
            end_dt = datetime.strptime(end_dt_str, '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            
            if start_dt <= now:
                messagebox.showerror("خطا", 
                    f"امکان تعریف بازه زمانی برای زمان گذشته وجود ندارد.\n"
                    f"زمان شروع باید بعد از زمان فعلی ({now.strftime('%H:%M:%S')}) باشد.")
                return
            
            if end_dt <= start_dt:
                messagebox.showerror("خطا", "ساعت پایان باید بعد از ساعت شروع باشد.")
                return
                
        except ValueError as e:
            messagebox.showerror("خطا", f"فرمت تاریخ/ساعت نامعتبر است: {e}")
            return

        from models.booking_model import BookingModel
        bookings = BookingModel.get_bookings_by_slot(slot_id)
        active_bookings = [b for b in bookings if b.get('status') in ('Pending', 'Confirmed')]
        
        if active_bookings:
            messagebox.showerror("خطا", 
                f"این بازه زمانی دارای {len(active_bookings)} رزرو فعال است و قابل ویرایش نمی‌باشد.\n"
                "لطفاً ابتدا رزروهای مربوطه را لغو کنید.")
            return

        success, message = self.controller.update_slot(slot_id, sid, start_dt_str, end_dt_str)
        if success:
            messagebox.showinfo("موفق", message)
            self._load_slots()
        else:
            messagebox.showerror("خطا", message)

    def _toggle_slot(self):
        sel = self.slots_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک بازه انتخاب کنید.")
            return
        slot_id = self.slots_tree.item(sel[0])['values'][0]
        sid = self._get_selected_svc_id()
        if sid is None:
            return
        
        from models.booking_model import BookingModel
        bookings = BookingModel.get_bookings_by_slot(slot_id)
        active_bookings = [b for b in bookings if b.get('status') in ('Pending', 'Confirmed')]
        
        if active_bookings:
            messagebox.showerror("خطا", 
                f"این بازه زمانی دارای {len(active_bookings)} رزرو فعال است و نمی‌توان وضعیت آن را تغییر داد.")
            return
        
        success, message = self.controller.toggle_slot_status(slot_id, sid)
        if success:
            messagebox.showinfo("موفق", message)
            self._load_slots()
        else:
            messagebox.showerror("خطا", message)

    def _delete_slot(self):
        sel = self.slots_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "یک بازه انتخاب کنید.")
            return
        slot_id = self.slots_tree.item(sel[0])['values'][0]
        sid = self._get_selected_svc_id()
        
        from models.booking_model import BookingModel
        bookings = BookingModel.get_bookings_by_slot(slot_id)
        active_bookings = [b for b in bookings if b.get('status') in ('Pending', 'Confirmed')]
        
        if active_bookings:
            messagebox.showerror("خطا", 
                f"این بازه زمانی دارای {len(active_bookings)} رزرو فعال است و قابل حذف نمی‌باشد.")
            return
        
        if messagebox.askyesno("حذف", "این بازه حذف شود؟"):
            success, message = self.controller.delete_slot(slot_id, sid)
            if success:
                messagebox.showinfo("موفق", message)
                self._load_slots()
            else:
                messagebox.showerror("خطا", message)
                
    # ==================== رزروها ====================
    def _setup_bookings(self):
        p = self.tab_book
        
        tb = tk.Frame(p, bg='#ecf0f1', pady=6)
        tb.pack(fill='x')
        tk.Label(tb, text='رزروهای دریافتی', font=('Tahoma', 11, 'bold'),
                 bg='#ecf0f1').pack(side='left', padx=10)
        
        tk.Button(tb, text='📄 گزارش PDF رزروها', command=self._pdf_bookings_report,
                  bg='#8e44ad', fg='white', relief='flat', padx=8).pack(side='right', padx=4)
        
        for txt, clr, cmd in [
            ('✅ تأیید', '#27ae60', self._confirm_booking),
            ('❌ رد', '#e74c3c', self._reject_booking)
        ]:
            tk.Button(tb, text=txt, command=cmd, bg=clr, fg='white',
                      relief='flat', padx=8).pack(side='right', padx=4)
        
        filter_frame = tk.Frame(p, bg='#ecf0f1', pady=5)
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
        
        cols = ('ID', 'مشتری', 'سرویس', 'شروع', 'پایان', 'وضعیت', 'پرداخت')
        self.bookings_tree = ttk.Treeview(p, columns=cols, show='headings', height=16)
        STATUS_BG = {'Pending': '#fff3cd', 'Confirmed': '#d4edda',
                     'Rejected': '#f8d7da', 'Canceled': '#e2e3e5'}
        for s, bg in STATUS_BG.items():
            self.bookings_tree.tag_configure(s, background=bg)
        for col, w in zip(cols, [45, 120, 160, 130, 130, 90, 80]):
            self.bookings_tree.heading(col, text=col)
            self.bookings_tree.column(col, width=w, anchor='center')
        
        sb2 = ttk.Scrollbar(p, orient='vertical', command=self.bookings_tree.yview)
        self.bookings_tree.configure(yscrollcommand=sb2.set)
        self.bookings_tree.pack(side='left', fill='both', expand=True, padx=(8, 0), pady=6)
        sb2.pack(side='left', fill='y', pady=6)

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
                customer = b.get('customer_name', '').lower()
                service = b.get('service_title', '').lower()
                if search_text not in customer and search_text not in service:
                    continue
            filtered_bookings.append(b)
        
        for b in filtered_bookings:
            status = b.get('status', '')
            values = (
                b.get('id'),
                b.get('customer_name'),
                b.get('service_title'),
                b.get('start_time'),
                b.get('end_time'),
                status,
                b.get('payment_status')
            )
            self.bookings_tree.insert('', 'end', values=values, tags=(status,))
        
        count = len(filtered_bookings)
        self.notebook.tab(self.tab_book, text=f'  📋  رزروها ({count})  ')

    def _confirm_booking(self):
        sel = self.bookings_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "رزرو انتخاب کنید.")
            return
        bid = self.bookings_tree.item(sel[0])['values'][0]
        
        from models.booking_model import BookingModel
        booking = BookingModel.get_booking_by_id(bid)
        
        if not booking:
            messagebox.showerror("خطا", "رزرو یافت نشد.")
            return
        
        if booking.get('payment_status') != 'Paid':
            messagebox.showerror("خطا", "امکان تأیید رزرو قبل از پرداخت وجود ندارد.\nمشتری ابتدا باید پرداخت را انجام دهد.")
            return
        
        if messagebox.askyesno("تأیید رزرو", f"رزرو #{bid} تأیید شود؟"):
            success, message = self.controller.confirm_booking(bid)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_bookings()
                self.load_dashboard_data()
            else:
                messagebox.showerror("خطا", message)

    def _reject_booking(self):
        sel = self.bookings_tree.selection()
        if not sel:
            messagebox.showwarning("هشدار", "رزرو انتخاب کنید.")
            return
        bid = self.bookings_tree.item(sel[0])['values'][0]
        
        from models.booking_model import BookingModel
        booking = BookingModel.get_booking_by_id(bid)
        
        if not booking:
            messagebox.showerror("خطا", "رزرو یافت نشد.")
            return
        
        if booking.get('payment_status') != 'Paid':
            messagebox.showerror("خطا", "امکان رد رزرو قبل از پرداخت وجود ندارد.")
            return
        
        if messagebox.askyesno("رد رزرو", f"رزرو #{bid} رد شود؟"):
            success, message = self.controller.reject_booking(bid)
            if success:
                messagebox.showinfo("موفق", message)
                self.load_bookings()
                self.load_dashboard_data()
            else:
                messagebox.showerror("خطا", message)
                
    # ==================== پروفایل ====================
    def _setup_profile(self):
        p = self.tab_profile
        
        main_frame = tk.Frame(p)
        main_frame.pack(expand=True)
        
        pass_frame = ttk.LabelFrame(main_frame, text="  🔑  تغییر رمز عبور  ", padding=20)
        pass_frame.pack(padx=40, pady=60)

        cur_frame = tk.Frame(pass_frame)
        cur_frame.pack(fill='x', pady=8)
        tk.Label(cur_frame, text="رمز عبور فعلی:", width=18, anchor='w',
                 font=('Tahoma', 10)).pack(side='left')
        self._p_cur = tk.Entry(cur_frame, show='*', width=28, font=('Tahoma', 10))
        self._p_cur.pack(side='left', padx=8)

        new_frame = tk.Frame(pass_frame)
        new_frame.pack(fill='x', pady=8)
        tk.Label(new_frame, text="رمز عبور جدید:", width=18, anchor='w',
                 font=('Tahoma', 10)).pack(side='left')
        self._p_new = tk.Entry(new_frame, show='*', width=28, font=('Tahoma', 10))
        self._p_new.pack(side='left', padx=8)

        confirm_frame = tk.Frame(pass_frame)
        confirm_frame.pack(fill='x', pady=8)
        tk.Label(confirm_frame, text="تکرار رمز جدید:", width=18, anchor='w',
                 font=('Tahoma', 10)).pack(side='left')
        self._p_confirm = tk.Entry(confirm_frame, show='*', width=28, font=('Tahoma', 10))
        self._p_confirm.pack(side='left', padx=8)

        tk.Button(pass_frame, text="تغییر رمز عبور", command=self._change_password,
                  bg='#8e44ad', fg='white', font=('Tahoma', 10, 'bold'),
                  width=20, pady=6).pack(pady=20)

    def load_profile_info(self):
        pass

    def _change_password(self):
        if not self.controller:
            return

        result = self.controller.change_password(
            self._p_cur.get(),
            self._p_new.get(),
            self._p_confirm.get()
        )

        if result == PasswordChangeResult.OK:
            messagebox.showinfo("موفق", "رمز عبور با موفقیت تغییر کرد.")
            self._p_cur.delete(0, 'end')
            self._p_new.delete(0, 'end')
            self._p_confirm.delete(0, 'end')
        elif result == PasswordChangeResult.EMPTY:
            messagebox.showwarning("خطا", "تمام فیلدها الزامی‌اند.")
        elif result == PasswordChangeResult.MISMATCH:
            messagebox.showerror("خطا", "رمز جدید و تکرار آن مطابقت ندارند.")
        elif result == PasswordChangeResult.WRONG_PASSWORD:
            messagebox.showerror("خطا", "رمز عبور فعلی اشتباه است.")