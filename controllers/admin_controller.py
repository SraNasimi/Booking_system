import tkinter as tk
from tkinter import messagebox
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from db.db import init_db, hash_password
from models.user_model import UserModel
from models.stats_model import StatsModel
from models.booking_model import BookingModel
from models.service_model import ServiceModel

VALID_ROLES = ['Admin', 'Provider', 'Customer']


class PasswordChangeResult(Enum):
    """نتیجه تغییر رمز عبور"""
    OK = 'ok'
    EMPTY = 'empty'
    WRONG_PASSWORD = 'wrong'


class AdminController:
    """کنترلر پنل ادمین - مدیریت منطق کسب و کار"""

    def __init__(self, root, return_to_login_callback=None):
        self.root = root
        self.view = None
        self._admin_user_id = None   
        self.return_to_login_callback = return_to_login_callback
        # حذف init_db() - فقط در main.py یکبار اجرا شود

    def set_admin_id(self, user_id: int):
        """تنظیم ID ادمین"""
        self._admin_user_id = user_id

    def _add_notification(self, message: str, notification_type: str = 'admin_action'):
        """افزودن اعلان برای ادمین"""
        try:
            from models.notification_model import NotificationModel
            NotificationModel.add(self._admin_user_id, message, notification_type)
        except Exception as e:
            print(f"Error adding notification: {e}")

    # ==================== کاربران ====================

    def get_all_users(self) -> List[Dict[str, Any]]:
        """دریافت لیست همه کاربران"""
        return UserModel.get_all_users()

    def update_user_role(self, user_id: int, new_role: str) -> Tuple[bool, str]:
        """به‌روزرسانی نقش کاربر - برگرداندن (success, message)"""
        if user_id == self._admin_user_id:
            return False, "نمی‌توانید نقش خودتان را تغییر دهید."
        
        if new_role not in VALID_ROLES:
            return False, f"نقش نامعتبر: {new_role}"
        
        try:
            # دریافت نام کاربر برای اعلان
            user = UserModel.get_user_by_id(user_id)
            username = user.get('username', 'نامشخص') if user else 'نامشخص'
            
            UserModel.update_role(user_id, new_role)
            
            # اعلان برای ادمین
            self._add_notification(f"نقش کاربر '{username}' به {new_role} تغییر کرد.", 'user_management')
            
            return True, "نقش کاربر با موفقیت تغییر کرد."
        except Exception as e:
            return False, f"خطا در تغییر نقش: {str(e)}"

    def delete_user(self, user_id: int) -> Tuple[bool, str]:
        """حذف کاربر - فقط در صورتی که رزرو فعال یا سرویس فعال نداشته باشد"""
        try:
            from models.booking_model import BookingModel
            from models.service_model import ServiceModel
            
            # بررسی وجود رزروهای فعال برای کاربر (اگر ارائه‌دهنده است)
            user = UserModel.get_user_by_id(user_id)
            if not user:
                return False, "کاربر یافت نشد"
            
            if user_id == self._admin_user_id:
                return False, "نمی‌توانید خودتان را حذف کنید."
            
            role = user.get('role')
            username = user.get('username', 'نامشخص')
            
            # اگر کاربر ارائه‌دهنده است، بررسی رزروهای فعال
            if role == 'Provider':
                # بررسی رزروهای فعال (Pending, Confirmed)
                provider_bookings = BookingModel.get_provider_bookings(user_id)
                active_bookings = [b for b in provider_bookings if b.get('status') in ('Pending', 'Confirmed')]
                
                if active_bookings:
                    return False, f"این ارائه‌دهنده دارای {len(active_bookings)} رزرو فعال است و قابل حذف نمی‌باشد.\nلطفاً ابتدا رزروهای مربوطه را لغو کنید."
                
                # بررسی سرویس‌های فعال
                provider_services = ServiceModel.get_provider_services(user_id)
                active_services = [s for s in provider_services if s.get('status') == 'Active']
                
                if active_services:
                    return False, f"این ارائه‌دهنده دارای {len(active_services)} سرویس فعال است و قابل حذف نمی‌باشد.\nلطفاً ابتدا سرویس‌ها را غیرفعال کنید."
            
            # اگر کاربر مشتری است، بررسی رزروهای فعال
            elif role == 'Customer':
                from models.booking_model import BookingModel
                customer_bookings = BookingModel.get_customer_bookings(user_id)
                active_bookings = [b for b in customer_bookings if b.get('status') in ('Pending', 'Confirmed')]
                
                if active_bookings:
                    return False, f"این مشتری دارای {len(active_bookings)} رزرو فعال است و قابل حذف نمی‌باشد.\nلطفاً ابتدا رزروهای مربوطه را لغو کنید."
            
            # حذف کاربر
            UserModel.delete_user(user_id)
            
            # اعلان برای ادمین
            self._add_notification(f"کاربر '{username}' با نقش {role} حذف شد.", 'user_management')
            
            return True, "کاربر با موفقیت حذف شد."
            
        except Exception as e:
            print(f"delete_user error: {e}")
            return False, f"خطا در حذف کاربر: {str(e)}"

    def add_user(self, username: str, password: str, role: str) -> Tuple[bool, str]:
        """افزودن کاربر جدید - برگرداندن (success, message)"""
        if not username or not password:
            return False, "نام کاربری و رمز عبور الزامی هستند."
        
        if role not in VALID_ROLES:
            return False, f"نقش نامعتبر: {role}"
        
        if len(password) < 4:
            return False, "رمز عبور باید حداقل ۴ کاراکتر باشد."
        
        try:
            hashed_password = hash_password(password)
            UserModel.add_user(username, hashed_password, role)
            
            # اعلان برای ادمین
            self._add_notification(f"کاربر جدید '{username}' با نقش {role} اضافه شد.", 'user_management')
            
            return True, "کاربر با موفقیت اضافه شد."
        except Exception as e:
            return False, f"خطا در افزودن کاربر: {str(e)}"

    # ==================== رمز عبور ادمین ====================

    def change_admin_password(self, current_pass: str, new_pass: str) -> PasswordChangeResult:
        """تغییر رمز عبور ادمین"""
        if not all([current_pass, new_pass]):
            return PasswordChangeResult.EMPTY
        
        if len(new_pass) < 4:
            return PasswordChangeResult.EMPTY
        
        user = UserModel.get_user_by_id(self._admin_user_id)
        if not user:
            return PasswordChangeResult.WRONG_PASSWORD
        
        hashed_current = hash_password(current_pass)
        if user.get('password') != hashed_current:
            return PasswordChangeResult.WRONG_PASSWORD
        
        hashed_new = hash_password(new_pass)
        UserModel.update_password(self._admin_user_id, hashed_new)
        
        # اعلان برای ادمین
        self._add_notification("رمز عبور شما با موفقیت تغییر کرد.", 'security')
        
        return PasswordChangeResult.OK

    # ==================== رزروها ====================

    def get_all_bookings(self) -> List[Dict[str, Any]]:
        """دریافت لیست همه رزروها"""
        return BookingModel.get_all_bookings()

    def force_approve_booking(self, booking_id: int) -> Tuple[bool, str]:
        """تأیید اجباری رزرو توسط ادمین (فقط در صورتی که پرداخت شده باشد)"""
        try:
            from models.booking_model import BookingModel
            # بررسی وضعیت پرداخت
            booking = BookingModel.get_booking_by_id(booking_id)
            if not booking:
                return False, "رزرو یافت نشد"
            
            if booking.get('payment_status') != 'Paid':
                return False, "امکان تأیید رزرو قبل از پرداخت وجود ندارد."
            
            success = BookingModel.update_booking_status(booking_id, 'Confirmed')
            if success:
                # اعلان برای ادمین
                self._add_notification(f"رزرو #{booking_id} توسط ادمین تأیید شد.", 'booking_management')
                return True, f"رزرو #{booking_id} تأیید شد."
            return False, f"تأیید رزرو #{booking_id} ناموفق بود."
        except Exception as e:
            return False, f"خطا: {str(e)}"

    def force_reject_booking(self, booking_id: int) -> Tuple[bool, str]:
        """رد اجباری رزرو توسط ادمین (فقط در صورتی که پرداخت شده باشد)"""
        try:
            from models.booking_model import BookingModel
            # بررسی وضعیت پرداخت
            booking = BookingModel.get_booking_by_id(booking_id)
            if not booking:
                return False, "رزرو یافت نشد"
            
            if booking.get('payment_status') != 'Paid':
                return False, "امکان رد رزرو قبل از پرداخت وجود ندارد."
            
            success = BookingModel.update_booking_status(booking_id, 'Rejected')
            if success:
                # اعلان برای ادمین
                self._add_notification(f"رزرو #{booking_id} توسط ادمین رد شد.", 'booking_management')
                return True, f"رزرو #{booking_id} رد شد."
            return False, f"رد رزرو #{booking_id} ناموفق بود."
        except Exception as e:
            return False, f"خطا: {str(e)}"

    def force_cancel_booking(self, booking_id: int) -> Tuple[bool, str]:
        """لغو اجباری رزرو توسط ادمین (فقط در صورتی که تأیید نشده باشد)"""
        try:
            from models.booking_model import BookingModel
            # بررسی وضعیت رزرو
            booking = BookingModel.get_booking_by_id(booking_id)
            if not booking:
                return False, "رزرو یافت نشد"
            
            if booking.get('status') == 'Confirmed':
                return False, "رزرو تأیید شده قابل لغو اجباری نیست."
            
            success = BookingModel.update_booking_status(booking_id, 'Canceled')
            if success:
                # اعلان برای ادمین
                self._add_notification(f"رزرو #{booking_id} توسط ادمین لغو شد.", 'booking_management')
                return True, f"رزرو #{booking_id} لغو شد."
            return False, f"لغو رزرو #{booking_id} ناموفق بود."
        except Exception as e:
            return False, f"خطا: {str(e)}"

    # ==================== سرویس‌ها ====================

    def get_all_services(self) -> List[Dict[str, Any]]:
        """دریافت لیست همه سرویس‌ها (برای ادمین)"""
        return ServiceModel.get_all_services_for_admin()

    def toggle_service_status(self, service_id: int) -> Tuple[bool, str]:
        """تغییر وضعیت فعال/غیرفعال سرویس"""
        try:
            # دریافت اطلاعات سرویس برای اعلان
            service = ServiceModel.get_service_by_id(service_id)
            service_title = service.get('title', 'نامشخص') if service else 'نامشخص'
            
            success = ServiceModel.admin_toggle_service(service_id)
            if success:
                # دریافت وضعیت جدید
                updated_service = ServiceModel.get_service_by_id(service_id)
                new_status = 'فعال' if updated_service.get('status') == 'Active' else 'غیرفعال' if updated_service else ''
                # اعلان برای ادمین
                self._add_notification(f"وضعیت سرویس '{service_title}' به {new_status} تغییر کرد.", 'service_management')
                return True, "وضعیت سرویس تغییر کرد."
            return False, "تغییر وضعیت سرویس ناموفق بود."
        except Exception as e:
            return False, f"خطا: {str(e)}"

    def delete_service(self, service_id: int) -> Tuple[bool, str]:
        """حذف سرویس توسط ادمین - بررسی رزروهای تأیید شده"""
        try:
            # دریافت اطلاعات سرویس برای اعلان
            service = ServiceModel.get_service_by_id(service_id)
            service_title = service.get('title', 'نامشخص') if service else 'نامشخص'
            
            result = ServiceModel.admin_delete_service(service_id)
            success, message = result if isinstance(result, tuple) else (result, message if 'message' in locals() else '')
            
            if success:
                # اعلان برای ادمین
                self._add_notification(f"سرویس '{service_title}' حذف شد.", 'service_management')
            
            return result
        except Exception as e:
            print(f"delete_service error: {e}")
            return False, f"خطا در حذف سرویس: {str(e)}"
            

    # ==================== نظرات (Reviews) ====================

    def get_all_reviews(self, limit: int = 500, offset: int = 0,
                        rating_filter: int = None, 
                        provider_filter: str = None) -> List[Dict[str, Any]]:
        """
        دریافت همه نظرات برای ادمین با فیلترهای مختلف
        برگرداندن: لیست دیکشنری‌های شامل اطلاعات نظرات
        """
        try:
            from models.review_model import ReviewModel
            return ReviewModel.get_all_reviews_for_admin(limit, offset, rating_filter, provider_filter)
        except Exception as e:
            print(f"get_all_reviews error: {e}")
            return []

    def get_all_reviews_count(self, rating_filter: int = None, 
                               provider_filter: str = None) -> int:
        """
        تعداد کل نظرات برای ادمین با فیلترها
        برگرداندن: عدد تعداد نظرات
        """
        try:
            from models.review_model import ReviewModel
            return ReviewModel.get_all_reviews_count_for_admin(rating_filter, provider_filter)
        except Exception as e:
            print(f"get_all_reviews_count error: {e}")
            return 0

    def delete_review(self, review_id: int) -> Tuple[bool, str]:
        """
        حذف نظر توسط ادمین
        برگرداندن: (success, message)
        """
        try:
            from models.review_model import ReviewModel
            result = ReviewModel.delete_review_by_admin(review_id)
            
            if result[0]:
                # اعلان برای ادمین
                self._add_notification(f"نظر #{review_id} توسط ادمین حذف شد.", 'review_management')
            
            return result
        except Exception as e:
            print(f"delete_review error: {e}")
            return False, f"خطا در حذف نظر: {str(e)}"

    # ==================== آمار ====================

    def get_admin_stats(self) -> Dict[str, Any]:
        """دریافت آمار کامل برای داشبورد ادمین"""
        return StatsModel.get_admin_stats()

    def get_top_services(self, limit: int = 5) -> List[Dict[str, Any]]:
        """دریافت محبوب‌ترین سرویس‌ها"""
        return StatsModel.get_top_services(limit)

    # ==================== خروج ====================

    def return_to_login(self):
        """بازگشت به صفحه لاگین"""
        if self.return_to_login_callback:
            self.return_to_login_callback()

    # ==================== گزارشات PDF ====================

    def generate_stats_report(self) -> Optional[str]:
        """تولید گزارش PDF آمار برای ادمین"""
        try:
            from reports.pdf_generator import generate_admin_stats_report
            
            stats = self.get_admin_stats()
            bookings = self.get_all_bookings()
            top_services = self.get_top_services()
            
            path = generate_admin_stats_report(stats, bookings, top_services)
            
            if path:
                self._add_notification("گزارش آماری PDF با موفقیت تولید شد.", 'report')
            
            return path
        except ImportError as e:
            print(f"Error importing pdf_generator: {e}")
            return None
        except Exception as e:
            print(f"Error generating stats report: {e}")
            return None