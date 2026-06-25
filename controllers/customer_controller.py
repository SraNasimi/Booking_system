import os
import shutil
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from models.customer_model import CustomerModel
from models.user_model import UserModel
from db.db import hash_password


class PasswordChangeResult(Enum):
    """نتیجه تغییر رمز عبور"""
    OK = 'ok'
    EMPTY = 'empty'
    MISMATCH = 'mismatch'
    WRONG_PASSWORD = 'wrong'


class ProfilePictureResult(Enum):
    """نتیجه به‌روزرسانی تصویر پروفایل"""
    SUCCESS = 'success'
    NO_FILE = 'no_file'
    FILE_NOT_FOUND = 'file_not_found'
    ERROR = 'error'


class CustomerController:
    """کنترلر پنل مشتری - مدیریت منطق کسب و کار"""

    def __init__(self, view, user_id: int, return_to_login_callback):
        self.view = view
        self.user_id = user_id
        self.return_to_login_callback = return_to_login_callback
        self.model = CustomerModel(user_id)
        
        # اگر View در سازنده کنترلر را دریافت کرده باشد، نیازی به set_controller نیست
        if view and hasattr(view, 'set_controller'):
            self.view.set_controller(self)

    def _add_notification(self, message: str, notification_type: str = 'info'):
        """افزودن اعلان برای مشتری"""
        try:
            from models.notification_model import NotificationModel
            NotificationModel.add(self.user_id, message, notification_type)
        except Exception as e:
            print(f"Error adding notification: {e}")

    # ==================== خروج ====================

    def logout(self) -> bool:
        """خروج از پنل مشتری - برگرداندن True اگر موفق باشد"""
        try:
            if self.view and hasattr(self.view, 'root'):
                if self.view.root.winfo_exists():
                    self.view.root.destroy()
            return True
        except Exception as e:
            print(f"logout error: {e}")
            return False
        finally:
            if self.return_to_login_callback:
                self.return_to_login_callback()

    # ==================== پروفایل ====================

    def get_user_details(self) -> Dict[str, Any]:
        """دریافت اطلاعات کاربر"""
        return self.model.get_user_details()

    def change_password(self, current_pass: str, new_pass: str, 
                        confirm_pass: str) -> PasswordChangeResult:
        """تغییر رمز عبور - برگرداندن نتیجه"""
        if not all([current_pass, new_pass, confirm_pass]):
            return PasswordChangeResult.EMPTY
        
        if new_pass != confirm_pass:
            return PasswordChangeResult.MISMATCH
        
        # اعتبارسنجی طول رمز
        if len(new_pass) < 4:
            return PasswordChangeResult.EMPTY
        
        user = UserModel.get_user_by_id(self.user_id)
        if not user:
            return PasswordChangeResult.WRONG_PASSWORD
        
        # هش کردن رمز فعلی و مقایسه
        hashed_current = hash_password(current_pass)
        if user.get('password') != hashed_current:
            return PasswordChangeResult.WRONG_PASSWORD
        
        # ذخیره رمز جدید هش شده
        hashed_new = hash_password(new_pass)
        UserModel.update_password(self.user_id, hashed_new)
        
        # اعلان برای مشتری
        self._add_notification("رمز عبور شما با موفقیت تغییر کرد.", 'security')
        
        return PasswordChangeResult.OK

    def update_profile_picture(self, image_path: str) -> Tuple[ProfilePictureResult, str]:
        """
        به‌روزرسانی تصویر پروفایل
        برگرداندن: (نتیجه, پیام)
        """
        try:
            if not image_path:
                return ProfilePictureResult.NO_FILE, "تصویری انتخاب نشده است."
            
            if not os.path.exists(image_path):
                return ProfilePictureResult.FILE_NOT_FOUND, "فایل تصویر یافت نشد."
            
            save_dir = os.path.join('assets', 'profile_pics')
            os.makedirs(save_dir, exist_ok=True)
            
            ext = os.path.splitext(image_path)[1]
            fname = f"user_{self.user_id}_{self._generate_filename()}{ext}"
            dest = os.path.join(save_dir, fname)
            shutil.copy(image_path, dest)
            
            # ذخیره مسیر نسبی
            relative_path = dest.replace('\\', '/')
            UserModel.update_profile_image(self.user_id, relative_path)
            
            # اعلان برای مشتری
            self._add_notification("تصویر پروفایل شما با موفقیت به‌روزرسانی شد.", 'profile')
            
            return ProfilePictureResult.SUCCESS, "تصویر پروفایل با موفقیت بروزرسانی شد."
            
        except Exception as e:
            print(f"update_profile_picture error: {e}")
            return ProfilePictureResult.ERROR, f"خطا در ذخیره تصویر: {str(e)}"

    def _generate_filename(self) -> str:
        """تولید نام فایل یکتا"""
        import uuid
        return uuid.uuid4().hex[:8]

    # ==================== سرویس‌ها ====================

    def search_services(self, keyword: str = '', category: str = '', 
                       provider: str = '', min_price: float = 0, 
                       max_price: float = 10_000_000, 
                       active_only: bool = True) -> List[Dict[str, Any]]:
        """جستجوی سرویس‌ها"""
        return self.model.search_services(keyword, category, provider, 
                                          min_price, max_price, active_only)

    def get_service_details(self, service_id: int) -> Optional[Dict[str, Any]]:
        """دریافت جزئیات یک سرویس"""
        return self.model.get_service_details(service_id)

    def get_available_slots(self, service_id: int) -> List[Dict[str, Any]]:
        """دریافت بازه‌های زمانی available یک سرویس"""
        return self.model.get_available_slots(service_id)

    # ==================== رزروها ====================

    def book_service(self, service_id: int, slot_id: int) -> Tuple[bool, str]:
        """
        رزرو سرویس
        برگرداندن: (success, message)
        """
        # اعتبارسنجی اولیه
        if not service_id or not slot_id:
            return False, "اطلاعات سرویس یا بازه زمانی نامعتبر است."
        
        result = self.model.book_service(service_id, slot_id)
        
        if result[0]:
            # اعلان برای مشتری
            self._add_notification(f"رزرو شما با موفقیت ثبت شد. لطفاً پرداخت را انجام دهید.", 'booking_created')
        
        return result

    def get_my_bookings(self) -> List[Dict[str, Any]]:
        """دریافت لیست رزروهای من"""
        return self.model.get_my_bookings()

    def cancel_booking(self, booking_id: int) -> Tuple[bool, str]:
        """
        لغو رزرو
        برگرداندن: (success, message)
        """
        if not booking_id:
            return False, "شناسه رزرو نامعتبر است."
        
        result = self.model.cancel_booking(booking_id)
        
        if result[0]:
            # اعلان برای مشتری
            self._add_notification(f"رزرو #{booking_id} با موفقیت لغو شد.", 'booking_canceled')
        
        return result

    def get_remaining_cancel_time(self, booking_id: int) -> Optional[float]:
        """
        دریافت ساعت باقی‌مانده برای لغو رزرو
        برگرداندن: ساعت باقی‌مانده یا None اگر قابل لغو نباشد
        """
        return self.model.get_remaining_cancel_time(booking_id)

    def pay_booking(self, booking_id: int) -> Tuple[bool, str]:
        """
        پرداخت برای رزرو
        برگرداندن: (success, message)
        """
        if not booking_id:
            return False, "شناسه رزرو نامعتبر است."
        
        result = self.model.pay_booking(booking_id)
        
        if result[0]:
            # اعلان برای مشتری (فقط یک بار)
            self._add_notification(f"پرداخت رزرو #{booking_id} با موفقیت انجام شد.", 'payment_success')
            
            # همچنین به ارائه‌دهنده هم اعلان بفرست
            try:
                from models.booking_model import BookingModel
                booking = BookingModel.get_booking_by_id(booking_id)
                if booking and booking.get('provider_id'):
                    from models.notification_model import NotificationModel
                    NotificationModel.add(
                        booking['provider_id'],
                        f"پرداخت رزرو #{booking_id} توسط مشتری انجام شد. لطفاً تأیید کنید.",
                        'payment_success'
                    )
            except:
                pass
        
        return result

    # ==================== متدهای کمکی ====================

    def can_cancel_booking(self, booking_id: int) -> Tuple[bool, float, str]:
        """
        بررسی امکان لغو رزرو (۲ ساعت قبل از شروع)
        برگرداندن: (can_cancel, hours_remaining, message)
        """
        from models.booking_model import BookingModel
        return BookingModel.can_cancel_booking(booking_id, self.user_id)

    # ==================== امتیازدهی (Reviews) ====================

    def can_review_booking(self, booking_id: int) -> Tuple[bool, str]:
        """
        بررسی امکان امتیازدهی برای یک رزرو
        برگرداندن: (can_review, message)
        """
        if not booking_id:
            return False, "شناسه رزرو نامعتبر است."
        
        return self.model.can_review_booking(booking_id)

    def add_review(self, booking_id: int, rating: int, comment: str = '') -> Tuple[bool, str]:
        """
        ثبت امتیاز برای یک رزرو
        برگرداندن: (success, message)
        """
        if not booking_id:
            return False, "شناسه رزرو نامعتبر است."
        
        if rating < 1 or rating > 5:
            return False, "امتیاز باید بین 1 تا 5 باشد."
        
        result = self.model.add_review(booking_id, rating, comment)
        
        if result[0]:
            # اعلان برای مشتری
            rating_text = {1: 'خیلی ضعیف', 2: 'ضعیف', 3: 'متوسط', 4: 'خوب', 5: 'عالی'}
            self._add_notification(f"امتیاز {rating} ستاره ({rating_text.get(rating, '')}) برای سرویس ثبت شد. ممنون از بازخورد شما!", 'review')
        
        return result

    def get_review_status_for_booking(self, booking_id: int) -> Dict[str, Any]:
        """
        دریافت وضعیت امتیاز برای یک رزرو
        برگرداندن: {'has_reviewed': bool, 'rating': int, 'comment': str, 'created_at': str}
        """
        if not booking_id:
            return {'has_reviewed': False}
        
        return self.model.get_review_status_for_booking(booking_id)

    def get_my_reviews(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        دریافت همه امتیازهای ثبت شده توسط این مشتری
        برگرداندن: لیست دیکشنری‌های شامل اطلاعات امتیازها
        """
        return self.model.get_my_reviews(limit)

    # ==================== گزارشات PDF ====================

    def generate_bookings_report(self) -> Optional[str]:
        """تولید گزارش PDF رزروهای مشتری"""
        try:
            from reports.pdf_generator import generate_customer_bookings_report
            
            details = self.get_user_details()
            username = details.get('username', 'Customer') if details else 'Customer'
            bookings = self.get_my_bookings()
            
            if not bookings:
                print("No bookings to generate report")
                return None
            
            path = generate_customer_bookings_report(username, bookings)
            
            if path:
                self._add_notification("گزارش رزروهای شما با موفقیت تولید شد.", 'report')
            
            return path
        except ImportError as e:
            print(f"Error importing pdf_generator: {e}")
            return None
        except Exception as e:
            print(f"Error generating bookings report: {e}")
            return None

    def generate_receipt(self, booking_id: int) -> Optional[str]:
        """تولید فاکتور PDF برای یک رزرو خاص"""
        try:
            from reports.pdf_generator import generate_payment_receipt
            
            details = self.get_user_details()
            username = details.get('username', 'Customer') if details else 'Customer'
            
            # دریافت اطلاعات رزرو
            booking_info = self.model.get_booking_info_for_receipt(booking_id)
            if not booking_info:
                print(f"No booking info found for id: {booking_id}")
                return None
            
            path = generate_payment_receipt(username, booking_info)
            
            if path:
                self._add_notification(f"فاکتور پرداخت رزرو #{booking_id} با موفقیت تولید شد.", 'receipt')
            
            return path
        except ImportError as e:
            print(f"Error importing pdf_generator: {e}")
            return None
        except Exception as e:
            print(f"Error generating receipt: {e}")
            return None