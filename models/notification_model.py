# models/notification_model.py
from typing import List, Dict, Any, Optional, Tuple  # اضافه کردن Tuple
from db.db import get_db_connection
from datetime import datetime
import sqlite3
import time


class NotificationModel:
    """مدل مدیریت اعلان‌ها"""
    
    @staticmethod
    def _ensure_columns():
        """اطمینان از وجود ستون‌های مورد نیاز"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("PRAGMA table_info(notifications)")
                columns = [col[1] for col in c.fetchall()]
                
                if 'type' not in columns:
                    c.execute("ALTER TABLE notifications ADD COLUMN type TEXT DEFAULT 'info'")
                if 'is_read' not in columns:
                    c.execute("ALTER TABLE notifications ADD COLUMN is_read INTEGER DEFAULT 0")
                conn.commit()
        except Exception as e:
            print(f"Error ensuring columns: {e}")
    
    @staticmethod
    def add(user_id: int, message: str, notification_type: str = 'info') -> Optional[int]:
        """افزودن اعلان جدید - با مدیریت خطای قفل دیتابیس"""
        try:
            NotificationModel._ensure_columns()
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # تلاش مجدد در صورت قفل بودن دیتابیس (حداکثر 3 بار)
            for attempt in range(3):
                try:
                    with get_db_connection() as conn:
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO notifications (user_id, message, type, is_read, created_at)
                            VALUES (?, ?, ?, 0, ?)
                        """, (user_id, message, notification_type, now))
                        conn.commit()
                        return c.lastrowid
                except sqlite3.OperationalError as e:
                    if "locked" in str(e) and attempt < 2:
                        time.sleep(0.1)
                        continue
                    else:
                        raise
            return None
        except Exception as e:
            print(f"Error adding notification (continuing): {e}")
            return None
    
    @staticmethod
    def get_user_notifications(user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """دریافت لیست اعلان‌های کاربر"""
        try:
            NotificationModel._ensure_columns()
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT id, message, type, is_read, created_at
                    FROM notifications
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (user_id, limit))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error getting user notifications: {e}")
            return []
    
    @staticmethod
    def get_unread_count(user_id: int) -> int:
        """دریافت تعداد اعلان‌های خوانده نشده"""
        try:
            NotificationModel._ensure_columns()
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT COUNT(*) as count
                    FROM notifications
                    WHERE user_id = ? AND is_read = 0
                """, (user_id,))
                row = c.fetchone()
                return row['count'] if row else 0
        except Exception as e:
            print(f"Error getting unread count: {e}")
            return 0
    
    @staticmethod
    def mark_as_read(notification_id: int, user_id: int) -> bool:
        """علامت‌گذاری اعلان به عنوان خوانده شده"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE notifications SET is_read = 1
                    WHERE id = ? AND user_id = ?
                """, (notification_id, user_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error marking notification as read: {e}")
            return False
    
    @staticmethod
    def mark_all_as_read(user_id: int) -> bool:
        """علامت‌گذاری همه اعلان‌ها به عنوان خوانده شده"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    UPDATE notifications SET is_read = 1
                    WHERE user_id = ? AND is_read = 0
                """, (user_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error marking all notifications as read: {e}")
            return False
    
    # ==================== متدهای حذف ====================
    
    @staticmethod
    def delete_notification(notification_id: int, user_id: int) -> Tuple[bool, str]:
        """حذف یک اعلان توسط کاربر"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                # بررسی مالکیت اعلان
                c.execute("SELECT user_id FROM notifications WHERE id = ?", (notification_id,))
                row = c.fetchone()
                
                if not row:
                    return False, "اعلان یافت نشد."
                
                if row['user_id'] != user_id:
                    return False, "شما اجازه حذف این اعلان را ندارید."
                
                c.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
                conn.commit()
                return True, "اعلان با موفقیت حذف شد."
        except Exception as e:
            print(f"Error deleting notification: {e}")
            return False, f"خطا در حذف اعلان: {str(e)}"
    
    @staticmethod
    def delete_all_notifications(user_id: int) -> Tuple[bool, str]:
        """حذف همه اعلان‌های یک کاربر"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
                conn.commit()
                return True, "همه اعلان‌ها با موفقیت حذف شدند."
        except Exception as e:
            print(f"Error deleting all notifications: {e}")
            return False, f"خطا در حذف اعلان‌ها: {str(e)}"
    
    @staticmethod
    def delete_read_notifications(user_id: int) -> Tuple[bool, str]:
        """حذف اعلان‌های خوانده شده"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("DELETE FROM notifications WHERE user_id = ? AND is_read = 1", (user_id,))
                conn.commit()
                return True, "اعلان‌های خوانده شده با موفقیت حذف شدند."
        except Exception as e:
            print(f"Error deleting read notifications: {e}")
            return False, f"خطا در حذف اعلان‌ها: {str(e)}"
    
    # ==================== متدهای کمکی برای ایجاد اعلان ====================
    
    @staticmethod
    def add_booking_created(customer_id: int, provider_id: int, booking_id: int) -> bool:
        NotificationModel.add(provider_id, f"رزرو جدید #{booking_id} ثبت شد. لطفاً بررسی کنید.", 'booking_created')
        NotificationModel.add(customer_id, f"رزرو #{booking_id} ثبت شد. برای تأیید، پرداخت را انجام دهید.", 'booking_created')
        return True
    
    @staticmethod
    def add_booking_confirmed(customer_id: int, provider_id: int, booking_id: int) -> bool:
        NotificationModel.add(customer_id, f"✅ رزرو #{booking_id} تأیید شد.", 'booking_confirmed')
        return True
    
    @staticmethod
    def add_booking_rejected(customer_id: int, provider_id: int, booking_id: int) -> bool:
        NotificationModel.add(customer_id, f"❌ رزرو #{booking_id} رد شد.", 'booking_rejected')
        return True
    
    @staticmethod
    def add_booking_canceled(customer_id: int, provider_id: int, booking_id: int) -> bool:
        NotificationModel.add(provider_id, f"🚫 رزرو #{booking_id} توسط مشتری لغو شد.", 'booking_canceled')
        NotificationModel.add(customer_id, f"رزرو #{booking_id} لغو شد.", 'booking_canceled')
        return True
    
    @staticmethod
    def add_payment_success(customer_id: int, provider_id: int, booking_id: int, amount: float) -> bool:
        NotificationModel.add(provider_id, f"💰 پرداخت {amount:,.0f} تومان برای رزرو #{booking_id}", 'payment_success')
        NotificationModel.add(customer_id, f"💰 پرداخت {amount:,.0f} تومان برای رزرو #{booking_id} موفق بود.", 'payment_success')
        return True