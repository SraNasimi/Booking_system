import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from tkinter import ttk, messagebox
from models.user_model import UserModel
from controllers.auth_controller import AuthController
from controllers.admin_controller import AdminController
from views.admin import AdminView
from controllers.provider_controller import ProviderController
from views.provider import ProviderView
from controllers.customer_controller import CustomerController
from views.customer import CustomerView
from db.db import init_db


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("سیستم رزرو خدمات")
        self.root.geometry("420x310")
        self.root.resizable(False, False)
        self.current_window = None
        self.auth_controller = AuthController()
        self.setup_login_ui()
        self.root.mainloop()

    def setup_login_ui(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.title("سیستم رزرو خدمات")
        self.root.geometry("420x310")
        self.root.deiconify()

        tk.Label(self.root, text="ورود به سیستم", font=("Tahoma", 16, "bold")).pack(pady=20)
        tk.Label(self.root, text="نام کاربری:", font=("Tahoma", 10)).pack()
        entry_user = tk.Entry(self.root, width=30)
        entry_user.pack(pady=5)
        tk.Label(self.root, text="رمز عبور:", font=("Tahoma", 10)).pack()
        entry_pass = tk.Entry(self.root, width=30, show="*")
        entry_pass.pack(pady=5)

        def login():
            username = entry_user.get().strip()
            password = entry_pass.get().strip()
            
            if not username or not password:
                messagebox.showwarning("خطا", "لطفاً نام کاربری و رمز را وارد کنید")
                return
            
            result = self.auth_controller.login(username, password)
            
            if result['success']:
                role = result['role']
                user_id = result['user_id']

                def return_to_login():
                    if self.current_window and self.current_window.winfo_exists():
                        self.current_window.destroy()
                    self.setup_login_ui()

                self.root.withdraw()

                if role == "Admin":
                    self.current_window = tk.Toplevel(self.root)
                    controller = AdminController(self.current_window, return_to_login)
                    controller.set_admin_id(user_id)         
                    view = AdminView(self.current_window, controller)
                    controller.view = view

                elif role == "Provider":
                    self.current_window = tk.Toplevel(self.root)
                    controller = ProviderController(None, user_id, return_to_login)
                    view = ProviderView(self.current_window, controller)
                    controller.view = view

                elif role == "Customer":
                    self.current_window = tk.Toplevel(self.root)
                    controller = CustomerController(None, user_id, return_to_login)
                    view = CustomerView(self.current_window, controller)
                    controller.view = view

                else:
                    messagebox.showerror("خطا", "نقش نامعتبر")
                    self.root.deiconify()
            else:
                messagebox.showerror("خطا", result['message'])

        self.root.bind('<Return>', lambda e: login())
        tk.Button(self.root, text="ورود", command=login,
                  bg="#4CAF50", fg="white", font=("Tahoma", 11), width=20).pack(pady=14)

        def open_register():
            reg = tk.Toplevel(self.root)
            reg.title("ثبت‌ نام")
            reg.geometry("350x300")
            reg.resizable(False, False)
            reg.grab_set()
            
            tk.Label(reg, text="فرم ثبت‌نام", font=("Tahoma", 14, "bold")).pack(pady=10)
            tk.Label(reg, text="نام کاربری:", font=("Tahoma", 10)).pack(anchor="w", padx=20)
            eu = tk.Entry(reg, width=30)
            eu.pack(pady=4)
            tk.Label(reg, text="رمز عبور:", font=("Tahoma", 10)).pack(anchor="w", padx=20)
            ep = tk.Entry(reg, width=30, show="*")
            ep.pack(pady=4)
            tk.Label(reg, text="تکرار رمز:", font=("Tahoma", 10)).pack(anchor="w", padx=20)
            ep_confirm = tk.Entry(reg, width=30, show="*")
            ep_confirm.pack(pady=4)
            tk.Label(reg, text="نقش:", font=("Tahoma", 10)).pack(anchor="w", padx=20)
            rv = tk.StringVar()
            cb = ttk.Combobox(reg, textvariable=rv, state="readonly", width=27)
            cb['values'] = ('Customer', 'Provider')
            cb.pack(pady=4)
            cb.current(0)

            def submit():
                username = eu.get().strip()
                password = ep.get().strip()
                password_confirm = ep_confirm.get().strip()
                role = rv.get()
                
                result = self.auth_controller.register(username, password, password_confirm, role)
                
                if result['success']:
                    messagebox.showinfo("موفق", result['message'], parent=reg)
                    reg.destroy()
                else:
                    messagebox.showerror("خطا", result['message'], parent=reg)

            tk.Button(reg, text="ثبت‌ نام", command=submit,
                      bg="#2196F3", fg="white", font=("Tahoma", 11), width=15).pack(pady=12)

        tk.Button(self.root, text="ثبت‌ نام", command=open_register,
                  bg="#2196F3", fg="white", font=("Tahoma", 9)).pack()


if __name__ == "__main__":
    init_db()
    App()