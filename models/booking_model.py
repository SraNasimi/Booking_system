import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from db.db import get_db_connection


class BookingModel:

    @staticmethod
    def add_booking(customer_id: int, provider_id: int, 
                   service_id: int, slot_id: int) -> Tuple[bool, str]:
        """
        افزودن رزرو جدید
        برگرداندن: (success, message)
        """
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                # بررسی تداخل رزرو
                c.execute("""
                    SELECT id FROM bookings
                    WHERE slot_id = ? AND status IN ('Pending', 'Confirmed')
                """, (slot_id,))
                if c.fetchone():
                    return False, "این بازه زمانی قبلاً رزرو شده است"
                
                # بررسی وضعیت اسلات و سرویس
                c.execute("""
                    SELECT ts.status, s.status FROM time_slots ts
                    JOIN services s ON ts.service_id = s.id
                    WHERE ts.id = ? AND s.id = ?
                """, (slot_id, service_id))
                chk = c.fetchone()
                if not chk:
                    return False, "سرویس یا بازه زمانی یافت نشد"
                if chk[0] != 'Active':
                    return False, "بازه زمانی فعال نیست"
                if chk[1] != 'Active':
                    return False, "سرویس فعال نیست"
                
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                c.execute("""
                    INSERT INTO bookings
                        (customer_id, provider_id, service_id, slot_id, created_at, status, payment_status)
                    VALUES (?, ?, ?, ?, ?, 'Pending', 'Unpaid')
                """, (customer_id, provider_id, service_id, slot_id, now))
                
                booking_id = c.lastrowid
                
                # اعلان برای ارائه‌دهنده (رزرو جدید)
                try:
                    from models.notification_model import NotificationModel
                    NotificationModel.add(
                        provider_id,
                        f"رزرو جدید #{booking_id} ثبت شد. لطفاً پس از پرداخت مشتری، آن را تأیید کنید.",
                        'booking_created'
                    )
                    NotificationModel.add(
                        customer_id,
                        f"رزرو #{booking_id} با موفقیت ثبت شد. لطفاً پرداخت را انجام دهید.",
                        'booking_created'
                    )
                except:
                    pass
                
                return True, str(booking_id)
                
        except Exception as e:
            print(f"Error in add_booking: {e}")
            return False, f"خطا در ثبت رزرو: {str(e)}"

    @staticmethod
    def get_booking_by_id(booking_id: int) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات یک رزرو"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT b.id, b.customer_id, b.provider_id, b.service_id, b.slot_id,
                        b.status, b.payment_status, b.created_at, b.paid_at,
                        ts.start_time, ts.end_time, s.title as service_title, s.price
                    FROM bookings b
                    JOIN time_slots ts ON b.slot_id = ts.id
                    JOIN services s ON b.service_id = s.id
                    WHERE b.id = ?
                """, (booking_id,))
                row = c.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error in get_booking_by_id: {e}")
            return None

    @staticmethod
    def get_all_bookings() -> List[Dict[str, Any]]:
        """دریافت همه رزروها (برای ادمین)"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT b.id, cu.username as customer_name, pu.username as provider_name, 
                           s.title as service_title, ts.start_time, b.status, b.payment_status,
                           b.service_id
                    FROM bookings b
                    JOIN users cu ON b.customer_id = cu.id
                    JOIN users pu ON b.provider_id = pu.id
                    JOIN services s ON b.service_id = s.id
                    JOIN time_slots ts ON b.slot_id = ts.id
                    ORDER BY b.created_at DESC
                """)
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_all_bookings: {e}")
            return []

    @staticmethod
    def update_booking_status(booking_id: int, new_status: str) -> bool:
        """تغییر وضعیت رزرو (برای ادمین)"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("UPDATE bookings SET status = ? WHERE id = ?", 
                         (new_status, booking_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error in update_booking_status: {e}")
            return False

    @staticmethod
    def get_provider_bookings(provider_id: int) -> List[Dict[str, Any]]:
        """دریافت رزروهای یک ارائه‌دهنده"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT b.id, u.username as customer_name, s.title as service_title, 
                           ts.start_time, ts.end_time, b.status, b.payment_status,
                           b.created_at, b.service_id
                    FROM bookings b
                    JOIN users u ON b.customer_id = u.id
                    JOIN services s ON b.service_id = s.id
                    JOIN time_slots ts ON b.slot_id = ts.id
                    WHERE b.provider_id = ?
                    ORDER BY b.created_at DESC
                """, (provider_id,))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_provider_bookings: {e}")
            return []

    @staticmethod
    def get_provider_bookings_count(provider_id: int) -> int:
        """تعداد رزروهای یک ارائه‌دهنده"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT COUNT(*) FROM bookings WHERE provider_id = ?", 
                         (provider_id,))
                row = c.fetchone()
                return row[0] if row else 0
        except Exception as e:
            print(f"Error in get_provider_bookings_count: {e}")
            return 0

    @staticmethod
    def get_bookings_status_count(provider_id: int) -> Dict[str, int]:
        """تعداد رزروها بر اساس وضعیت برای یک ارائه‌دهنده"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT status, COUNT(*) FROM bookings
                    WHERE provider_id = ? GROUP BY status
                """, (provider_id,))
                rows = c.fetchall()
                return {row[0]: row[1] for row in rows}
        except Exception as e:
            print(f"Error in get_bookings_status_count: {e}")
            return {}

    @staticmethod
    def confirm_booking(booking_id: int, provider_id: int) -> Tuple[bool, str]:
        """تأیید رزرو توسط ارائه‌دهنده (فقط در صورتی که پرداخت شده باشد)"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                # بررسی وضعیت پرداخت
                c.execute("""
                    SELECT payment_status, status, customer_id FROM bookings 
                    WHERE id = ? AND provider_id = ?
                """, (booking_id, provider_id))
                row = c.fetchone()
                
                if not row:
                    return False, "رزرو یافت نشد"
                
                if row['payment_status'] != 'Paid':
                    return False, "امکان تأیید رزرو قبل از پرداخت وجود ندارد. لطفاً ابتدا مشتری پرداخت را انجام دهد."
                
                if row['status'] != 'Pending':
                    return False, f"رزرو در وضعیت {row['status']} قابل تأیید نیست"
                
                customer_id = row['customer_id']
                
                c.execute("""
                    UPDATE bookings SET status = 'Confirmed' 
                    WHERE id = ? AND provider_id = ?
                """, (booking_id, provider_id))
                conn.commit()
                
                # اعلان برای مشتری
                try:
                    from models.notification_model import NotificationModel
                    NotificationModel.add(
                        customer_id,
                        f"✅ رزرو #{booking_id} توسط ارائه‌دهنده تأیید شد.",
                        'booking_confirmed'
                    )
                except:
                    pass
                
                return True, "رزرو با موفقیت تأیید شد"
        except Exception as e:
            print(f"Error in confirm_booking: {e}")
            return False, f"خطا در تأیید رزرو: {str(e)}"

    @staticmethod
    def reject_booking(booking_id: int, provider_id: int) -> Tuple[bool, str]:
        """رد رزرو توسط ارائه‌دهنده (فقط در صورتی که پرداخت شده باشد)"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                # بررسی وضعیت پرداخت
                c.execute("""
                    SELECT payment_status, status, customer_id FROM bookings 
                    WHERE id = ? AND provider_id = ?
                """, (booking_id, provider_id))
                row = c.fetchone()
                
                if not row:
                    return False, "رزرو یافت نشد"
                
                if row['payment_status'] != 'Paid':
                    return False, "امکان رد رزرو قبل از پرداخت وجود ندارد."
                
                if row['status'] != 'Pending':
                    return False, f"رزرو در وضعیت {row['status']} قابل رد نیست"
                
                customer_id = row['customer_id']
                
                c.execute("""
                    UPDATE bookings SET status = 'Rejected' 
                    WHERE id = ? AND provider_id = ?
                """, (booking_id, provider_id))
                conn.commit()
                
                # اعلان برای مشتری
                try:
                    from models.notification_model import NotificationModel
                    NotificationModel.add(
                        customer_id,
                        f"❌ رزرو #{booking_id} توسط ارائه‌دهنده رد شد.",
                        'booking_rejected'
                    )
                except:
                    pass
                
                return True, "رزرو با موفقیت رد شد"
        except Exception as e:
            print(f"Error in reject_booking: {e}")
            return False, f"خطا در رد رزرو: {str(e)}"

    @staticmethod
    def cancel_booking(booking_id: int, customer_id: int) -> Tuple[bool, str]:
        """
        لغو رزرو توسط مشتری
        بررسی قانون ۲ ساعت قبل از شروع
        برگرداندن: (success, message)
        """
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT ts.start_time, b.customer_id, b.provider_id, b.status, b.payment_status
                    FROM bookings b 
                    JOIN time_slots ts ON b.slot_id = ts.id
                    WHERE b.id = ?
                """, (booking_id,))
                row = c.fetchone()
                
                if not row:
                    return False, "رزرو یافت نشد"
                
                start_str, cust_id, prov_id, status, payment_status = row
                
                # بررسی دسترسی
                if customer_id != cust_id:
                    return False, "شما اجازه لغو این رزرو را ندارید"
                
                # بررسی وضعیت رزرو
                if status in ('Canceled', 'Rejected'):
                    return False, f"این رزرو قبلاً {status} شده است"
                
                if status == 'Confirmed':
                    return False, "رزرو تأیید شده قابل لغو نیست"
                
                # بررسی پرداخت
                if payment_status != 'Paid':
                    return False, "ابتدا باید پرداخت انجام شود سپس می‌توانید لغو کنید"
                
                # محاسبه زمان باقیمانده تا شروع
                start_time = datetime.strptime(start_str, '%Y-%m-%d %H:%M:%S')
                hours_until_start = (start_time - datetime.now()).total_seconds() / 3600
                
                # بررسی قانون ۲ ساعت
                if hours_until_start < 2:
                    remaining_seconds = (start_time - datetime.now()).total_seconds()
                    if remaining_seconds <= 0:
                        return False, "زمان شروع خدمت گذشته است و نمی‌توان رزرو را لغو کرد"
                    
                    hours = int(hours_until_start)
                    minutes = int((hours_until_start - hours) * 60)
                    
                    if hours > 0:
                        time_msg = f"{hours} ساعت و {minutes} دقیقه"
                    else:
                        time_msg = f"{minutes} دقیقه"
                    
                    return False, f"لغو رزرو فقط حداقل ۲ ساعت قبل از شروع امکان‌پذیر است.\nزمان باقیمانده: {time_msg}"
                
                # انجام لغو
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                c.execute("UPDATE bookings SET status = 'Canceled' WHERE id = ?", (booking_id,))
                conn.commit()
                
                # اعلان برای ارائه‌دهنده
                try:
                    from models.notification_model import NotificationModel
                    NotificationModel.add(
                        prov_id,
                        f"🚫 رزرو #{booking_id} توسط مشتری لغو شد.",
                        'booking_canceled'
                    )
                    NotificationModel.add(
                        customer_id,
                        f"رزرو #{booking_id} با موفقیت لغو شد.",
                        'booking_canceled'
                    )
                except:
                    pass
                
                return True, "رزرو با موفقیت لغو شد"
                
        except Exception as e:
            print(f"Error in cancel_booking: {e}")
            return False, f"خطا در لغو رزرو: {str(e)}"
            
    @staticmethod
    def pay_booking(booking_id: int) -> Tuple[bool, str]:
        """
        ثبت پرداخت برای رزرو - ثبت زمان پرداخت
        توجه: اعلان‌ها در کنترلر ارسال می‌شوند تا از تکرار جلوگیری شود
        """
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                # بررسی وضعیت فعلی رزرو
                c.execute("""
                    SELECT payment_status, status, customer_id, provider_id 
                    FROM bookings 
                    WHERE id = ?
                """, (booking_id,))
                row = c.fetchone()
                
                if not row:
                    return False, "رزرو یافت نشد"
                
                if row['payment_status'] == 'Paid':
                    return False, "این رزرو قبلاً پرداخت شده است"
                
                if row['status'] in ('Canceled', 'Rejected'):
                    return False, f"رزرو {row['status']} شده قابل پرداخت نیست"
                
                # ثبت زمان پرداخت
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                c.execute("""
                    UPDATE bookings 
                    SET payment_status = 'Paid', 
                        paid_at = ? 
                    WHERE id = ?
                """, (now, booking_id))
                conn.commit()
                
                return True, f"پرداخت با موفقیت ثبت شد. زمان پرداخت: {now}"
                
        except Exception as e:
            print(f"Error in pay_booking: {e}")
            return False, f"خطا در ثبت پرداخت: {str(e)}"
            
    @staticmethod
    def get_customer_bookings(customer_id: int) -> List[Dict[str, Any]]:
        """دریافت رزروهای یک مشتری"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT b.id, s.title as service_title, u.username as provider_name, 
                        ts.start_time, b.status, b.payment_status, b.paid_at,
                        b.created_at, b.service_id
                    FROM bookings b
                    JOIN services s ON b.service_id = s.id
                    JOIN users u ON b.provider_id = u.id
                    JOIN time_slots ts ON b.slot_id = ts.id
                    WHERE b.customer_id = ?
                    ORDER BY b.created_at DESC
                """, (customer_id,))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_customer_bookings: {e}")
            return []

    @staticmethod
    def get_bookings_by_slot(slot_id: int) -> List[Dict[str, Any]]:
        """دریافت رزروهای یک بازه زمانی خاص"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT id, status, payment_status, customer_id, provider_id
                    FROM bookings 
                    WHERE slot_id = ?
                    ORDER BY created_at DESC
                """, (slot_id,))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_bookings_by_slot: {e}")
            return []

    @staticmethod
    def can_cancel_booking(booking_id: int, customer_id: int) -> Tuple[bool, float, str]:
        """
        بررسی امکان لغو رزرو
        برگرداندن: (can_cancel, hours_remaining, message)
        """
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT julianday(ts.start_time) - julianday('now') as hours_diff,
                        b.customer_id, b.status, b.payment_status, ts.start_time
                    FROM bookings b 
                    JOIN time_slots ts ON b.slot_id = ts.id
                    WHERE b.id = ?
                """, (booking_id,))
                row = c.fetchone()
                
                if not row:
                    return False, 0, "رزرو یافت نشد"
                
                hours_remaining = row['hours_diff'] * 24 if row['hours_diff'] else 0
                cust_id = row['customer_id']
                status = row['status']
                payment_status = row['payment_status']
                
                # بررسی دسترسی
                if customer_id != cust_id:
                    return False, 0, "شما اجازه لغو این رزرو را ندارید"
                
                # بررسی وضعیت رزرو
                if status in ('Canceled', 'Rejected'):
                    return False, 0, f"این رزرو قبلاً {status} شده است"
                
                if status == 'Confirmed':
                    return False, 0, "رزرو تأیید شده قابل لغو نیست"
                
                # بررسی پرداخت
                if payment_status != 'Paid':
                    return False, 0, "ابتدا باید پرداخت انجام شود سپس می‌توانید لغو کنید"
                
                # بررسی زمان
                if hours_remaining < 2:
                    if hours_remaining <= 0:
                        return False, hours_remaining, "زمان شروع خدمت گذشته است و نمی‌توان رزرو را لغو کرد"
                    
                    hours = int(hours_remaining)
                    minutes = int((hours_remaining - hours) * 60)
                    if hours > 0:
                        time_msg = f"{hours} ساعت و {minutes} دقیقه"
                    else:
                        time_msg = f"{minutes} دقیقه"
                    return False, hours_remaining, f"لغو رزرو فقط تا ۲ ساعت قبل از شروع مجاز است.\nزمان باقیمانده: {time_msg}"
                
                # محاسبه زمان باقیمانده به صورت خوانا
                hours = int(hours_remaining)
                minutes = int((hours_remaining - hours) * 60)
                if hours > 0:
                    time_msg = f"{hours} ساعت و {minutes} دقیقه"
                else:
                    time_msg = f"{minutes} دقیقه"
                
                return True, hours_remaining, f"زمان باقیمانده تا شروع: {time_msg}"
                    
        except Exception as e:
            print(f"Error in can_cancel_booking: {e}")
            return False, 0, f"خطا در بررسی: {str(e)}"
            

    @staticmethod
    def get_booking_slot_time(booking_id: int) -> Optional[str]:
        """دریافت زمان شروع رزرو"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT ts.start_time
                    FROM bookings b 
                    JOIN time_slots ts ON b.slot_id = ts.id
                    WHERE b.id = ?
                """, (booking_id,))
                row = c.fetchone()
                return row[0] if row else None
        except Exception as e:
            print(f"Error in get_booking_slot_time: {e}")
            return None