import os
import shutil
import uuid
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

from models.booking_model import BookingModel
from models.service_model import ServiceModel
from models.stats_model import StatsModel
from models.user_model import UserModel
from db.db import hash_password


class PasswordChangeResult(Enum):
    """نتیجه تغییر رمز عبور"""
    OK = 'ok'
    EMPTY = 'empty'
    MISMATCH = 'mismatch'
    WRONG_PASSWORD = 'wrong'


class ProviderController:
    """کنترلر پنل ارائه‌دهنده - مدیریت منطق کسب و کار"""

    def __init__(self, view, provider_id: int, return_to_login_callback):
        self.view = view
        self.provider_id = provider_id
        self.return_to_login_callback = return_to_login_callback

    def _add_notification(self, message: str, notification_type: str = 'info'):
        """افزودن اعلان برای ارائه‌دهنده"""
        try:
            from models.notification_model import NotificationModel
            NotificationModel.add(self.provider_id, message, notification_type)
        except Exception as e:
            print(f"Error adding notification: {e}")

    # ==================== پروفایل ====================

    def get_profile_info(self) -> Dict[str, Any]:
        """دریافت اطلاعات پروفایل ارائه‌دهنده"""
        user = UserModel.get_user_by_id(self.provider_id)
        if not user:
            return {}
        
        return {
            'id': user.get('id'),
            'username': user.get('username', ''),
            'name': user.get('name', ''),
            'bio': user.get('bio', ''),
            'specialty': user.get('specialty', ''),
            'photo_path': user.get('profile_image', '')
        }

    def update_profile(self, name: str = None, specialty: str = None, 
                       bio: str = None, phone: str = None, 
                       address: str = None, photo_path: str = None) -> bool:
        """به‌روزرسانی اطلاعات پروفایل"""
        try:
            # به‌روزرسانی اطلاعات پایه
            if name is not None or bio is not None or specialty is not None:
                UserModel.update_profile_info(self.provider_id, name=name, bio=bio, specialty=specialty)
            
            # به‌روزرسانی اطلاعات تماس
            if phone is not None or address is not None:
                UserModel.update_contact_info(self.provider_id, phone=phone, address=address)
            
            # به‌روزرسانی تصویر پروفایل
            if photo_path and os.path.exists(photo_path):
                save_dir = os.path.join('assets', 'profile_pics')
                os.makedirs(save_dir, exist_ok=True)
                ext = os.path.splitext(photo_path)[1]
                fname = f"provider_{self.provider_id}_{uuid.uuid4().hex[:8]}{ext}"
                dest = os.path.join(save_dir, fname)
                shutil.copy(photo_path, dest)
                UserModel.update_profile_image(self.provider_id, dest)
            
            # اعلان برای ارائه‌دهنده
            self._add_notification("پروفایل شما با موفقیت به‌روزرسانی شد.", 'profile')
            
            return True
        except Exception as e:
            print(f"update_profile error: {e}")
            return False

    def get_contact_info(self) -> Dict[str, str]:
        """دریافت اطلاعات تماس ارائه‌دهنده"""
        user = UserModel.get_user_by_id(self.provider_id)
        if not user:
            return {'phone': '', 'address': ''}
        
        return {
            'phone': user.get('phone', ''),
            'address': user.get('address', '')
        }

    def change_password(self, current_pass: str, new_pass: str, 
                        confirm_pass: str) -> PasswordChangeResult:
        """تغییر رمز عبور"""
        if not all([current_pass, new_pass, confirm_pass]):
            return PasswordChangeResult.EMPTY
        
        if new_pass != confirm_pass:
            return PasswordChangeResult.MISMATCH
        
        user = UserModel.get_user_by_id(self.provider_id)
        if not user:
            return PasswordChangeResult.WRONG_PASSWORD
        
        # هش کردن رمز فعلی و مقایسه
        hashed_current = hash_password(current_pass)
        if user.get('password') != hashed_current:
            return PasswordChangeResult.WRONG_PASSWORD
        
        # ذخیره رمز جدید هش شده
        hashed_new = hash_password(new_pass)
        UserModel.update_password(self.provider_id, hashed_new)
        
        # اعلان برای ارائه‌دهنده
        self._add_notification("رمز عبور شما با موفقیت تغییر کرد.", 'security')
        
        return PasswordChangeResult.OK

    # ==================== دسته‌بندی‌ها ====================

    def get_categories(self) -> List[Dict[str, Any]]:
        """دریافت لیست دسته‌بندی‌ها"""
        return ServiceModel.get_all_categories()
        
    def add_category(self, name: str) -> Optional[int]:
        """افزودن دسته‌بندی جدید"""
        if not name or not name.strip():
            return None
        return ServiceModel.add_category(name.strip())

    # ==================== سرویس‌ها ====================

    def get_my_services(self) -> List[Dict[str, Any]]:
        """دریافت لیست سرویس‌های ارائه‌دهنده"""
        return ServiceModel.get_provider_services(self.provider_id)

    def add_service(self, title: str, description: str, price: float, 
                    image: str = None, category_id: int = None, status: str = 'Active') -> bool:
        """افزودن سرویس جدید (بدون مدت زمان)"""
        try:
            # اعتبارسنجی
            if not title or not title.strip():
                print("add_service error: عنوان سرویس الزامی است")
                return False
            
            if not price or float(price) <= 0:
                print("add_service error: قیمت نامعتبر")
                return False
            
            result = ServiceModel.add_service(
                provider_id=self.provider_id,
                title=title.strip(),
                description=description.strip() if description else '',
                price=float(price),
                image=image,
                category_id=category_id,
                status=status
            )
            
            if result:
                # اعلان برای ارائه‌دهنده
                self._add_notification(f"سرویس جدید '{title}' با موفقیت اضافه شد.", 'service_management')
            
            return result
        except Exception as e:
            print(f"add_service error: {e}")
            return False

    def edit_service(self, service_id: int, title: str, description: str, 
                    price: float, image: str = None, 
                    category_id: int = None, status: str = None) -> bool:
        """ویرایش سرویس (بدون مدت زمان)"""
        try:
            # اعتبارسنجی
            if not title or not title.strip():
                return False
            if price and float(price) <= 0:
                return False
            
            result = ServiceModel.update_service(
                service_id=service_id,
                provider_id=self.provider_id,
                title=title.strip(),
                description=description.strip() if description else '',
                price=float(price),
                image=image,
                category_id=category_id,
                status=status
            )
            
            if result:
                # اعلان برای ارائه‌دهنده
                self._add_notification(f"سرویس '{title}' با موفقیت ویرایش شد.", 'service_management')
            
            return result
        except Exception as e:
            print(f"edit_service error: {e}")
            return False

    def delete_service(self, service_id: int) -> Tuple[bool, str]:
        """حذف سرویس - بررسی رزروهای تأیید شده"""
        try:
            # دریافت نام سرویس برای اعلان
            services = self.get_my_services()
            service_title = next((s.get('title', 'نامشخص') for s in services if s.get('id') == service_id), 'نامشخص')
            
            result = ServiceModel.delete_service(service_id, self.provider_id)
            
            if result[0]:
                # اعلان برای ارائه‌دهنده
                self._add_notification(f"سرویس '{service_title}' با موفقیت حذف شد.", 'service_management')
            
            return result
        except Exception as e:
            print(f"delete_service error: {e}")
            return False, f"خطا در حذف سرویس: {str(e)}"
            

    def toggle_service_status(self, service_id: int) -> Tuple[bool, str]:
        """تغییر وضعیت فعال/غیرفعال سرویس"""
        try:
            # دریافت نام سرویس برای اعلان
            services = self.get_my_services()
            service_title = next((s.get('title', 'نامشخص') for s in services if s.get('id') == service_id), 'نامشخص')
            
            result = ServiceModel.toggle_service_status(service_id, self.provider_id)
            
            if result[0]:
                # دریافت وضعیت جدید
                updated_services = self.get_my_services()
                new_status = next((s.get('status', '') for s in updated_services if s.get('id') == service_id), '')
                status_text = 'فعال' if new_status == 'Active' else 'غیرفعال'
                # اعلان برای ارائه‌دهنده
                self._add_notification(f"وضعیت سرویس '{service_title}' به {status_text} تغییر کرد.", 'service_management')
            
            return result
        except Exception as e:
            print(f"toggle_service_status error: {e}")
            return False, f"خطا در تغییر وضعیت: {str(e)}"
            

    # ==================== بازه‌های زمانی (اسلات‌ها) ====================

    def get_slots(self, service_id: int) -> List[Dict[str, Any]]:
        """دریافت بازه‌های زمانی یک سرویس"""
        return ServiceModel.get_time_slots_by_service(service_id)

    def add_slot_for_service(self, service_id: int, start_datetime: str, 
                            end_datetime: str) -> bool:
        """افزودن بازه زمانی جدید با اعتبارسنجی زمان"""
        from datetime import datetime
        
        # اعتبارسنجی تاریخ و ساعت
        if not self._validate_datetime(start_datetime) or not self._validate_datetime(end_datetime):
            return False
        
        # بررسی اینکه زمان شروع از الان بزرگتر باشد
        start_dt = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        
        if start_dt <= now:
            print("add_slot_for_service error: زمان شروع باید بعد از زمان فعلی باشد")
            return False
        
        if start_datetime >= end_datetime:
            return False
        
        result = ServiceModel.add_time_slot(service_id, start_datetime, end_datetime)
        
        if result:
            # اعلان برای ارائه‌دهنده
            self._add_notification(f"بازه زمانی جدید ({start_datetime[:16]} تا {end_datetime[:16]}) اضافه شد.", 'slot_management')
        
        return result

    def update_slot(self, slot_id: int, service_id: int, 
                    new_start: str, new_end: str) -> Tuple[bool, str]:
        """ویرایش بازه زمانی"""
        if not self._validate_datetime(new_start) or not self._validate_datetime(new_end):
            return False, "فرمت تاریخ و ساعت نامعتبر است."
        
        if new_start >= new_end:
            return False, "زمان پایان باید بعد از زمان شروع باشد."
        
        result = ServiceModel.update_time_slot(slot_id, service_id, new_start, new_end)
        
        if result[0]:
            # اعلان برای ارائه‌دهنده
            self._add_notification(f"بازه زمانی با موفقیت ویرایش شد ({new_start[:16]} تا {new_end[:16]}).", 'slot_management')
        
        return result

    def delete_slot(self, slot_id: int, service_id: int = None) -> Tuple[bool, str]:
        """حذف بازه زمانی"""
        result = ServiceModel.delete_time_slot(slot_id, service_id)
        
        if result[0]:
            # اعلان برای ارائه‌دهنده
            self._add_notification(f"بازه زمانی با موفقیت حذف شد.", 'slot_management')
        
        return result
        
    def toggle_slot_status(self, slot_id: int, service_id: int) -> Tuple[bool, str]:
        """تغییر وضعیت فعال/غیرفعال بازه زمانی"""
        try:
            result = ServiceModel.toggle_slot_status(slot_id, service_id)
            
            if result[0]:
                # اعلان برای ارائه‌دهنده
                self._add_notification(f"وضعیت بازه زمانی با موفقیت تغییر کرد.", 'slot_management')
            
            return result
        except Exception as e:
            print(f"toggle_slot_status error: {e}")
            return False, f"خطا در تغییر وضعیت: {str(e)}"
            

    # ==================== رزروها ====================

    def get_my_bookings(self) -> List[Dict[str, Any]]:
        """دریافت رزروهای ارائه‌دهنده"""
        return BookingModel.get_provider_bookings(self.provider_id)

    def confirm_booking(self, booking_id: int) -> Tuple[bool, str]:
        """تأیید رزرو"""
        result = BookingModel.confirm_booking(booking_id, self.provider_id)
        
        if result[0]:
            # اعلان برای ارائه‌دهنده
            self._add_notification(f"رزرو #{booking_id} با موفقیت تأیید شد.", 'booking_confirmed')
        
        return result
        
    def reject_booking(self, booking_id: int) -> Tuple[bool, str]:
        """رد رزرو"""
        result = BookingModel.reject_booking(booking_id, self.provider_id)
        
        if result[0]:
            # اعلان برای ارائه‌دهنده
            self._add_notification(f"رزرو #{booking_id} رد شد.", 'booking_rejected')
        
        return result
        
    def pay_booking(self, booking_id: int) -> Tuple[bool, str]:
        """ثبت پرداخت برای رزرو"""
        result = BookingModel.pay_booking(booking_id)
        
        if result[0]:
            # اعلان برای ارائه‌دهنده
            self._add_notification(f"پرداخت رزرو #{booking_id} توسط مشتری انجام شد.", 'payment_success')
        
        return result

    # ==================== نظرات (Reviews) ====================

    def get_my_reviews(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        دریافت نظرات مربوط به سرویس‌های من
        برگرداندن: لیست دیکشنری‌های شامل اطلاعات نظرات
        """
        try:
            from models.review_model import ReviewModel
            return ReviewModel.get_provider_all_reviews(self.provider_id, limit, offset)
        except Exception as e:
            print(f"get_my_reviews error: {e}")
            return []

    def get_my_reviews_count(self) -> int:
        """
        تعداد کل نظرات من
        برگرداندن: عدد تعداد نظرات
        """
        try:
            from models.review_model import ReviewModel
            return ReviewModel.get_provider_reviews_count(self.provider_id)
        except Exception as e:
            print(f"get_my_reviews_count error: {e}")
            return 0

    def get_my_reviews_summary(self) -> Dict[str, Any]:
        """
        خلاصه نظرات من (میانگین امتیاز، توزیع امتیازات)
        برگرداندن: دیکشنری شامل آمار کامل
        """
        try:
            from models.review_model import ReviewModel
            return ReviewModel.get_provider_reviews_summary(self.provider_id)
        except Exception as e:
            print(f"get_my_reviews_summary error: {e}")
            return {
                'total_reviews': 0,
                'avg_rating': 0,
                'rating_5': 0, 'rating_4': 0, 'rating_3': 0, 'rating_2': 0, 'rating_1': 0
            }

    # ==================== داشبورد ====================

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """دریافت آمار داشبورد"""
        try:
            stats = StatsModel.get_provider_stats(self.provider_id)
            return {
                'total': stats.get('total_bookings', 0),
                'status_counts': stats.get('status_counts', {}),
                'income': stats.get('income', 0),
                'services': stats.get('services', 0),
                'confirmed': stats.get('confirmed_bookings', 0),
            }
        except Exception as e:
            print(f"get_dashboard_stats error: {e}")
            return {
                'total': 0, 
                'status_counts': {}, 
                'income': 0, 
                'services': 0, 
                'confirmed': 0
            }

    #گزارشات
    def generate_services_report(self) -> Optional[str]:
        """تولید گزارش PDF سرویس‌ها برای ارائه‌دهنده"""
        try:
            from reports.pdf_generator import generate_provider_services_report
            
            info = self.get_profile_info()
            username = info.get('username', 'Provider') if info else 'Provider'
            services = self.get_my_services()
            
            if not services:
                print("No services to generate report")
                return None
            
            slots_map = {}
            for svc in services:
                slots_map[svc['id']] = self.get_slots(svc['id'])
            
            path = generate_provider_services_report(username, services, slots_map)
            
            if path:
                self._add_notification("گزارش سرویس‌ها با موفقیت تولید شد.", 'report')
            
            return path
        except ImportError as e:
            print(f"Error importing pdf_generator: {e}")
            return None
        except Exception as e:
            print(f"Error generating services report: {e}")
            return None

    # ==================== متدهای کمکی ====================

    def _validate_datetime(self, dt_str: str) -> bool:
        """اعتبارسنجی فرمت datetime"""
        try:
            from datetime import datetime
            datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
            return True
        except ValueError:
            return False

    # ==================== خروج ====================

    def logout(self):
        """خروج از پنل ارائه‌دهنده"""
        if self.return_to_login_callback:
            self.return_to_login_callback()