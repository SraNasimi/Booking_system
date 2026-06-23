from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from db.db import get_db_connection, get_connection
from models.service_model import ServiceModel


class CustomerModel:
    """مدل مشتری - دسترسی به دیتابیس برای عملیات مشتری"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id

    # ==================== پروفایل ====================
    
    def get_user_details(self) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات کاربر"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT id, username, profile_image, name, specialty, bio, phone, address
                    FROM users WHERE id = ?
                """, (self.user_id,))
                row = c.fetchone()
                if row:
                    return dict(row)
                return None
        except Exception as e:
            print(f"get_user_details error: {e}")
            return None

    # ==================== سرویس‌ها ====================
    
    def search_services(self, keyword: str = '', category: str = '', 
                        provider: str = '', min_price: float = 0, 
                        max_price: float = 10_000_000, 
                        active_only: bool = True) -> List[Dict[str, Any]]:
        """جستجوی سرویس‌ها"""
        return ServiceModel.search_services(keyword, category, provider, 
                                            min_price, max_price, active_only)

    def get_service_details(self, service_id: int) -> Optional[Dict[str, Any]]:
        """دریافت جزئیات یک سرویس"""
        return ServiceModel.get_service_by_id(service_id)

    def get_available_slots(self, service_id: int) -> List[Dict[str, Any]]:
        """دریافت بازه‌های زمانی آزاد یک سرویس"""
        return ServiceModel.get_available_slots(service_id)

    # ==================== رزروها ====================
    
    def book_service(self, service_id: int, slot_id: int) -> Tuple[bool, str]:
        """
        ثبت رزرو جدید
        برگرداندن: (success, message)
        """
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                # بررسی وجود اسلات و فعال بودن آن
                c.execute("""
                    SELECT service_id, status FROM time_slots 
                    WHERE id = ? AND service_id = ? AND status = 'Active'
                """, (slot_id, service_id))
                slot = c.fetchone()
                if not slot:
                    return False, "بازه زمانی انتخاب شده معتبر نیست یا غیرفعال شده است."
                
                # جلوگیری از رزرو تداخلی
                c.execute("""
                    SELECT id FROM bookings 
                    WHERE slot_id = ? AND status IN ('Pending', 'Confirmed')
                """, (slot_id,))
                if c.fetchone():
                    return False, "این بازه زمانی قبلاً رزرو شده است."
                
                # دریافت اطلاعات سرویس
                c.execute("""
                    SELECT provider_id, status FROM services WHERE id = ?
                """, (service_id,))
                service = c.fetchone()
                if not service:
                    return False, "سرویس مورد نظر یافت نشد."
                if service['status'] != 'Active':
                    return False, "این سرویس در حال حاضر فعال نیست."
                
                provider_id = service['provider_id']
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                c.execute("""
                    INSERT INTO bookings 
                        (customer_id, provider_id, service_id, slot_id, status, payment_status, created_at)
                    VALUES (?, ?, ?, ?, 'Pending', 'Unpaid', ?)
                """, (self.user_id, provider_id, service_id, slot_id, now))
                
                # پیام با توضیح اینکه باید پرداخت کنید
                return True, "رزرو با موفقیت ثبت شد. توجه: برای تأیید نهایی رزرو، لطفاً پرداخت را انجام دهید. تا زمان پرداخت، رزرو در وضعیت انتظار باقی می‌ماند."
                
        except Exception as e:
            print(f"book_service error: {e}")
            return False, f"خطا در ثبت رزرو: {str(e)}"

    def get_my_bookings(self) -> List[Dict[str, Any]]:
        """دریافت لیست رزروهای کاربر"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT b.id, s.title as service_title, 
                        COALESCE(u.username, 'نامشخص') as provider_name,
                        ts.start_time, b.status, b.payment_status,
                        b.created_at, b.paid_at
                    FROM bookings b
                    JOIN services s ON b.service_id = s.id
                    LEFT JOIN users u ON b.provider_id = u.id
                    JOIN time_slots ts ON b.slot_id = ts.id
                    WHERE b.customer_id = ?
                    ORDER BY b.created_at DESC
                """, (self.user_id,))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"get_my_bookings error: {e}")
            return []

    def get_booking_by_id(self, booking_id: int) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات یک رزرو خاص"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT b.id, b.customer_id, b.provider_id, b.service_id, b.slot_id,
                           b.status, b.payment_status, b.created_at, b.paid_at,
                           ts.start_time, ts.end_time, s.title as service_title
                    FROM bookings b
                    JOIN time_slots ts ON b.slot_id = ts.id
                    JOIN services s ON b.service_id = s.id
                    WHERE b.id = ? AND b.customer_id = ?
                """, (booking_id, self.user_id))
                row = c.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"get_booking_by_id error: {e}")
            return None

    def get_booking_start_time(self, booking_id: int) -> Optional[str]:
        """دریافت زمان شروع رزرو"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT ts.start_time
                    FROM bookings b
                    JOIN time_slots ts ON b.slot_id = ts.id
                    WHERE b.id = ? AND b.customer_id = ?
                """, (booking_id, self.user_id))
                row = c.fetchone()
                return row['start_time'] if row else None
        except Exception as e:
            print(f"get_booking_start_time error: {e}")
            return None

    def get_remaining_cancel_time(self, booking_id: int) -> Optional[float]:
        """
        دریافت ساعت باقی‌مانده برای لغو رزرو (بر اساس قانون ۲ ساعت)
        برگرداندن: ساعت باقی‌مانده تا شروع سرویس، یا None اگر قابل محاسبه نباشد
        """
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT julianday(ts.start_time) - julianday('now') as hours_left,
                           b.status, b.payment_status
                    FROM bookings b
                    JOIN time_slots ts ON b.slot_id = ts.id
                    WHERE b.id = ? AND b.customer_id = ?
                """, (booking_id, self.user_id))
                row = c.fetchone()
                
                if not row:
                    return None
                
                hours_left = row['hours_left'] * 24 if row['hours_left'] else 0
                
                # اگر رزرو قبلاً لغو یا رد شده باشد
                if row['status'] in ('Canceled', 'Rejected', 'Confirmed'):
                    return None
                
                # اگر پرداخت نشده باشد
                if row['payment_status'] != 'Paid':
                    return None
                
                return hours_left
                
        except Exception as e:
            print(f"get_remaining_cancel_time error: {e}")
            return None

    def cancel_booking(self, booking_id: int) -> Tuple[bool, str]:
        """
        لغو رزرو (بررسی قانون ۲ ساعت - با احتساب زمان شروع)
        برگرداندن: (success, message)
        """
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                # بررسی وجود رزرو و اطلاعات آن
                c.execute("""
                    SELECT b.status, b.payment_status, b.provider_id, ts.start_time
                    FROM bookings b
                    JOIN time_slots ts ON b.slot_id = ts.id
                    WHERE b.id = ? AND b.customer_id = ?
                """, (booking_id, self.user_id))
                booking = c.fetchone()
                
                if not booking:
                    return False, "رزرو مورد نظر یافت نشد."
                
                if booking['status'] in ('Canceled', 'Rejected'):
                    return False, f"این رزرو قبلاً {booking['status']} شده است."
                
                if booking['status'] == 'Confirmed':
                    return False, "رزرو تأیید شده قابل لغو نیست."
                
                if booking['payment_status'] != 'Paid':
                    return False, "ابتدا باید پرداخت انجام شود سپس می‌توانید لغو کنید."
                
                # بررسی قانون ۲ ساعت
                start_time = datetime.strptime(booking['start_time'], '%Y-%m-%d %H:%M:%S')
                hours_until_start = (start_time - datetime.now()).total_seconds() / 3600
                
                if hours_until_start < 2:
                    return False, f"تنها تا ۲ ساعت قبل از شروع سرویس امکان لغو وجود دارد. زمان باقیمانده: {hours_until_start:.1f} ساعت"
                
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                c.execute("UPDATE bookings SET status = 'Canceled' WHERE id = ?", (booking_id,))
                
                # ثبت نوتیفیکیشن برای ارائه‌دهنده
                c.execute("""
                    INSERT INTO notifications (user_id, message, created_at) 
                    VALUES (?, ?, ?)
                """, (booking['provider_id'], f"رزرو #{booking_id} توسط مشتری لغو شد.", now))
                
                return True, "رزرو با موفقیت لغو شد."
                
        except Exception as e:
            print(f"cancel_booking error: {e}")
            return False, f"خطا در لغو رزرو: {str(e)}"

    def update_booking_status(self, booking_id: int, new_status: str) -> Tuple[bool, str]:
        """به‌روزرسانی وضعیت رزرو"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE bookings SET status = ? 
                    WHERE id = ? AND customer_id = ?
                """, (new_status, booking_id, self.user_id))
                return True, f"وضعیت رزرو به {new_status} تغییر کرد."
        except Exception as e:
            print(f"update_booking_status error: {e}")
            return False, f"خطا در به‌روزرسانی: {str(e)}"

    def pay_booking(self, booking_id: int) -> Tuple[bool, str]:
        """ثبت پرداخت برای رزرو"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                c.execute("""
                    SELECT payment_status, status, provider_id FROM bookings 
                    WHERE id = ? AND customer_id = ?
                """, (booking_id, self.user_id))
                row = c.fetchone()
                
                if not row:
                    return False, "رزرو مورد نظر یافت نشد."
                
                if row['payment_status'] == 'Paid':
                    return False, "این رزرو قبلاً پرداخت شده است."
                
                if row['status'] in ('Canceled', 'Rejected'):
                    return False, f"رزرو {row['status']} شده قابل پرداخت نیست."
                
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                c.execute("""
                    UPDATE bookings 
                    SET payment_status = 'Paid', paid_at = ? 
                    WHERE id = ?
                """, (now, booking_id))
                
                # ثبت نوتیفیکیشن برای مشتری
                c.execute("""
                    INSERT INTO notifications (user_id, message, created_at) 
                    VALUES (?, ?, ?)
                """, (self.user_id, f"پرداخت رزرو #{booking_id} با موفقیت انجام شد.", now))
                
                # ثبت نوتیفیکیشن برای ارائه‌دهنده
                c.execute("""
                    INSERT INTO notifications (user_id, message, created_at) 
                    VALUES (?, ?, ?)
                """, (row['provider_id'], f"پرداخت رزرو #{booking_id} توسط مشتری انجام شد. لطفاً تأیید کنید.", now))
                
                return True, "پرداخت با موفقیت انجام شد."
                
        except Exception as e:
            print(f"pay_booking error: {e}")
            return False, f"خطا در پرداخت: {str(e)}"

    def get_booking_payment_status(self, booking_id: int) -> Optional[str]:
        """دریافت وضعیت پرداخت رزرو"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT payment_status FROM bookings 
                    WHERE id = ? AND customer_id = ?
                """, (booking_id, self.user_id))
                row = c.fetchone()
                return row['payment_status'] if row else None
        except Exception as e:
            print(f"get_booking_payment_status error: {e}")
            return None

    def can_cancel_booking(self, booking_id: int) -> Tuple[bool, float]:
        """
        بررسی امکان لغو رزرو (با قانون ۲ ساعت)
        برگرداندن: (can_cancel, hours_remaining)
        """
        remaining = self.get_remaining_cancel_time(booking_id)
        if remaining is None:
            return False, 0
        return remaining >= 2, remaining

    def get_booking_info_for_receipt(self, booking_id: int) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات رزرو برای فاکتور"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT b.id as booking_id, 
                        s.title as service_title, 
                        COALESCE(u.username, 'نامشخص') as provider_name,
                        ts.start_time, 
                        s.price, 
                        b.paid_at, 
                        b.status
                    FROM bookings b
                    JOIN services s ON b.service_id = s.id
                    LEFT JOIN users u ON b.provider_id = u.id
                    JOIN time_slots ts ON b.slot_id = ts.id
                    WHERE b.id = ? AND b.customer_id = ? AND b.payment_status = 'Paid'
                """, (booking_id, self.user_id))
                row = c.fetchone()
                if row:
                    result = dict(row)
                    # اطمینان از وجود provider_name
                    if not result.get('provider_name') or result.get('provider_name') == '':
                        result['provider_name'] = 'نامشخص'
                    return result
                return None
        except Exception as e:
            print(f"get_booking_info_for_receipt error: {e}")
            return None

    # ==================== امتیازدهی (Reviews) ====================

    def can_review_booking(self, booking_id: int) -> Tuple[bool, str]:
        """
        بررسی امکان امتیازدهی برای یک رزرو
        برگرداندن: (can_review, message)
        """
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                # بررسی وجود رزرو و وضعیت آن
                c.execute("""
                    SELECT status, payment_status 
                    FROM bookings 
                    WHERE id = ? AND customer_id = ?
                """, (booking_id, self.user_id))
                
                booking = c.fetchone()
                if not booking:
                    return False, "رزرو مورد نظر یافت نشد."
                
                if booking['status'] != 'Confirmed':
                    return False, "امکان امتیازدهی فقط برای رزروهای تأیید شده وجود دارد."
                
                if booking['payment_status'] != 'Paid':
                    return False, "امکان امتیازدهی فقط برای رزروهای پرداخت شده وجود دارد."
                
                # بررسی اینکه قبلاً امتیاز ثبت نشده باشد
                from models.review_model import ReviewModel
                if ReviewModel.has_user_reviewed_booking(booking_id, self.user_id):
                    return False, "شما قبلاً برای این رزرو امتیاز ثبت کرده‌اید."
                
                return True, "می‌توانید امتیاز خود را ثبت کنید."
                
        except Exception as e:
            print(f"can_review_booking error: {e}")
            return False, f"خطا در بررسی: {str(e)}"

    def add_review(self, booking_id: int, rating: int, comment: str = '') -> Tuple[bool, str]:
        """
        ثبت امتیاز برای یک رزرو
        برگرداندن: (success, message)
        """
        try:
            # دریافت اطلاعات رزرو
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT provider_id, service_id, status, payment_status
                    FROM bookings 
                    WHERE id = ? AND customer_id = ?
                """, (booking_id, self.user_id))
                
                booking = c.fetchone()
                if not booking:
                    return False, "رزرو مورد نظر یافت نشد."
                
                if booking['status'] != 'Confirmed':
                    return False, "امکان امتیازدهی فقط برای رزروهای تأیید شده وجود دارد."
                
                if booking['payment_status'] != 'Paid':
                    return False, "امکان امتیازدهی فقط برای رزروهای پرداخت شده وجود دارد."
                
                provider_id = booking['provider_id']
                service_id = booking['service_id']
            
            # ثبت امتیاز
            from models.review_model import ReviewModel
            return ReviewModel.add_review(
                booking_id=booking_id,
                customer_id=self.user_id,
                provider_id=provider_id,
                service_id=service_id,
                rating=rating,
                comment=comment
            )
            
        except Exception as e:
            print(f"add_review error: {e}")
            return False, f"خطا در ثبت امتیاز: {str(e)}"

    def get_review_status_for_booking(self, booking_id: int) -> Dict[str, Any]:
        """
        دریافت وضعیت امتیاز برای یک رزرو
        برگرداندن: {'has_reviewed': bool, 'rating': int, 'comment': str, 'created_at': str}
        """
        from models.review_model import ReviewModel
        
        has_reviewed = ReviewModel.has_user_reviewed_booking(booking_id, self.user_id)
        result = {'has_reviewed': has_reviewed}
        
        if has_reviewed:
            review = ReviewModel.get_customer_review_for_booking(booking_id, self.user_id)
            if review:
                result['rating'] = review.get('rating')
                result['comment'] = review.get('comment', '')
                result['created_at'] = review.get('created_at')
        
        return result

    def get_my_reviews(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        دریافت همه امتیازهای ثبت شده توسط این مشتری
        برگرداندن: لیست دیکشنری‌های شامل اطلاعات امتیازها
        """
        from models.review_model import ReviewModel
        return ReviewModel.get_customer_all_reviews(self.user_id, limit)