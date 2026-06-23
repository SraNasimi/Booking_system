# models/review_model.py
from typing import List, Dict, Any, Optional, Tuple
from db.db import get_db_connection
from datetime import datetime


class ReviewModel:
    """مدل مدیریت امتیازات و نظرات"""

    @staticmethod
    def add_review(booking_id: int, customer_id: int, provider_id: int,
                   service_id: int, rating: int, comment: str = '') -> Tuple[bool, str]:
        """
        افزودن امتیاز جدید برای یک رزرو
        برگرداندن: (success, message)
        """
        if rating < 1 or rating > 5:
            return False, "امتیاز باید بین 1 تا 5 باشد."

        try:
            with get_db_connection() as conn:
                c = conn.cursor()

                # بررسی اینکه آیا قبلاً برای این رزرو امتیاز ثبت شده است
                c.execute("""
                    SELECT id FROM reviews 
                    WHERE booking_id = ? AND customer_id = ?
                """, (booking_id, customer_id))
                
                if c.fetchone():
                    return False, "شما قبلاً برای این رزرو امتیاز ثبت کرده‌اید."

                # بررسی وضعیت رزرو
                c.execute("""
                    SELECT status, payment_status 
                    FROM bookings 
                    WHERE id = ? AND customer_id = ?
                """, (booking_id, customer_id))
                
                booking = c.fetchone()
                if not booking:
                    return False, "رزرو مورد نظر یافت نشد."

                if booking['status'] != 'Confirmed':
                    return False, "امکان امتیازدهی فقط برای رزروهای تأیید شده وجود دارد."

                if booking['payment_status'] != 'Paid':
                    return False, "امکان امتیازدهی فقط برای رزروهای پرداخت شده وجود دارد."

                # ثبت امتیاز
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                c.execute("""
                    INSERT INTO reviews (booking_id, customer_id, provider_id, service_id, 
                                        rating, comment, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (booking_id, customer_id, provider_id, service_id, rating, comment, now))

                # به‌روزرسانی میانگین امتیاز سرویس
                c.execute("""
                    UPDATE services 
                    SET avg_rating = (
                        SELECT COALESCE(ROUND(AVG(rating), 1), 0) FROM reviews WHERE service_id = ?
                    ),
                    review_count = (
                        SELECT COUNT(*) FROM reviews WHERE service_id = ?
                    )
                    WHERE id = ?
                """, (service_id, service_id, service_id))

                # ========== اعلان برای ارائه‌دهنده (غیرفعال شده) ==========
                # try:
                #     from models.notification_model import NotificationModel
                #     rating_text = {1: 'خیلی ضعیف', 2: 'ضعیف', 3: 'متوسط', 4: 'خوب', 5: 'عالی'}
                #     NotificationModel.add(
                #         provider_id,
                #         f"⭐ مشتری به سرویس شما امتیاز {rating} ستاره ({rating_text.get(rating, '')}) داد.\nنظر: {comment if comment else 'نظری ثبت نشده'}",
                #         'review_received'
                #     )
                # except Exception as e:
                #     print(f"Error sending notification to provider: {e}")

                return True, "امتیاز شما با موفقیت ثبت شد. ممنون از بازخورد شما!"

        except Exception as e:
            print(f"Error in add_review: {e}")
            return False, f"خطا در ثبت امتیاز: {str(e)}"
            
    # ========== بقیه متدها بدون تغییر ==========
    
    @staticmethod
    def get_service_reviews(service_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT r.id, r.rating, r.comment, r.created_at,
                           u.username as customer_name
                    FROM reviews r
                    JOIN users u ON r.customer_id = u.id
                    WHERE r.service_id = ?
                    ORDER BY r.created_at DESC
                    LIMIT ?
                """, (service_id, limit))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_service_reviews: {e}")
            return []

    @staticmethod
    def get_provider_reviews(provider_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT r.id, r.rating, r.comment, r.created_at,
                           u.username as customer_name,
                           s.title as service_title
                    FROM reviews r
                    JOIN users u ON r.customer_id = u.id
                    JOIN services s ON r.service_id = s.id
                    WHERE r.provider_id = ?
                    ORDER BY r.created_at DESC
                    LIMIT ?
                """, (provider_id, limit))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_provider_reviews: {e}")
            return []

    @staticmethod
    def get_provider_all_reviews(provider_id: int, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT r.id, r.rating, r.comment, r.created_at,
                           u.username as customer_name,
                           s.title as service_title,
                           s.id as service_id,
                           ts.start_time as booking_time
                    FROM reviews r
                    JOIN users u ON r.customer_id = u.id
                    JOIN services s ON r.service_id = s.id
                    JOIN bookings b ON r.booking_id = b.id
                    JOIN time_slots ts ON b.slot_id = ts.id
                    WHERE r.provider_id = ?
                    ORDER BY r.created_at DESC
                    LIMIT ? OFFSET ?
                """, (provider_id, limit, offset))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_provider_all_reviews: {e}")
            return []

    @staticmethod
    def get_provider_reviews_count(provider_id: int) -> int:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT COUNT(*) as count
                    FROM reviews
                    WHERE provider_id = ?
                """, (provider_id,))
                row = c.fetchone()
                return row['count'] if row else 0
        except Exception as e:
            print(f"Error in get_provider_reviews_count: {e}")
            return 0

    @staticmethod
    def get_provider_reviews_summary(provider_id: int) -> Dict[str, Any]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT 
                        COUNT(*) as total_reviews,
                        COALESCE(AVG(rating), 0) as avg_rating,
                        SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) as rating_5,
                        SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) as rating_4,
                        SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) as rating_3,
                        SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) as rating_2,
                        SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as rating_1
                    FROM reviews
                    WHERE provider_id = ?
                """, (provider_id,))
                row = c.fetchone()
                if row:
                    result = dict(row)
                    result['avg_rating'] = round(result['avg_rating'], 1)
                    return result
                return {
                    'total_reviews': 0,
                    'avg_rating': 0,
                    'rating_5': 0, 'rating_4': 0, 'rating_3': 0, 'rating_2': 0, 'rating_1': 0
                }
        except Exception as e:
            print(f"Error in get_provider_reviews_summary: {e}")
            return {}

    @staticmethod
    def get_all_reviews_for_admin(limit: int = 100, offset: int = 0, 
                                   rating_filter: int = None, 
                                   provider_filter: str = None) -> List[Dict[str, Any]]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                query = """
                    SELECT r.id, r.rating, r.comment, r.created_at,
                           cu.username as customer_name,
                           pu.username as provider_name,
                           s.title as service_title,
                           s.id as service_id,
                           ts.start_time as booking_time
                    FROM reviews r
                    JOIN users cu ON r.customer_id = cu.id
                    JOIN users pu ON r.provider_id = pu.id
                    JOIN services s ON r.service_id = s.id
                    JOIN bookings b ON r.booking_id = b.id
                    JOIN time_slots ts ON b.slot_id = ts.id
                    WHERE 1=1
                """
                params = []
                
                if rating_filter:
                    query += " AND r.rating = ?"
                    params.append(rating_filter)
                
                if provider_filter:
                    query += " AND pu.username LIKE ?"
                    params.append(f'%{provider_filter}%')
                
                query += " ORDER BY r.created_at DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                c.execute(query, params)
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_all_reviews_for_admin: {e}")
            return []

    @staticmethod
    def get_all_reviews_count_for_admin(rating_filter: int = None, 
                                         provider_filter: str = None) -> int:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                query = """
                    SELECT COUNT(*) as count
                    FROM reviews r
                    JOIN users pu ON r.provider_id = pu.id
                    WHERE 1=1
                """
                params = []
                
                if rating_filter:
                    query += " AND r.rating = ?"
                    params.append(rating_filter)
                
                if provider_filter:
                    query += " AND pu.username LIKE ?"
                    params.append(f'%{provider_filter}%')
                
                c.execute(query, params)
                row = c.fetchone()
                return row['count'] if row else 0
        except Exception as e:
            print(f"Error in get_all_reviews_count_for_admin: {e}")
            return 0

    @staticmethod
    def delete_review_by_admin(review_id: int) -> Tuple[bool, str]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                c.execute("""
                    SELECT service_id, rating, customer_id, provider_id, comment
                    FROM reviews 
                    WHERE id = ?
                """, (review_id,))
                review = c.fetchone()
                
                if not review:
                    return False, "نظر یافت نشد."
                
                service_id = review['service_id']
                c.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
                
                c.execute("""
                    UPDATE services 
                    SET avg_rating = (
                        SELECT COALESCE(ROUND(AVG(rating), 1), 0) FROM reviews WHERE service_id = ?
                    ),
                    review_count = (
                        SELECT COUNT(*) FROM reviews WHERE service_id = ?
                    )
                    WHERE id = ?
                """, (service_id, service_id, service_id))
                
                # ========== اعلان‌ها (غیرفعال شده) ==========
                # try:
                #     from models.notification_model import NotificationModel
                #     rating_text = {1: 'خیلی ضعیف', 2: 'ضعیف', 3: 'متوسط', 4: 'خوب', 5: 'عالی'}
                #     NotificationModel.add(
                #         customer_id,
                #         f"⚠️ نظر شما با امتیاز {rating} ستاره ({rating_text.get(rating, '')}) برای سرویس توسط ادمین حذف شد.\nنظر: {comment if comment else 'نظری ثبت نشده'}",
                #         'review_deleted'
                #     )
                # except Exception as e:
                #     print(f"Error sending notification to customer: {e}")
                
                return True, "نظر با موفقیت حذف شد."
                
        except Exception as e:
            print(f"Error in delete_review_by_admin: {e}")
            return False, f"خطا در حذف نظر: {str(e)}"

    @staticmethod
    def get_service_rating_stats(service_id: int) -> Dict[str, Any]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT 
                        COUNT(*) as total_reviews,
                        COALESCE(AVG(rating), 0) as avg_rating,
                        SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) as rating_5,
                        SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) as rating_4,
                        SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) as rating_3,
                        SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) as rating_2,
                        SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as rating_1
                    FROM reviews
                    WHERE service_id = ?
                """, (service_id,))
                row = c.fetchone()
                if row:
                    result = dict(row)
                    result['avg_rating'] = round(result['avg_rating'], 1)
                    return result
                return {
                    'total_reviews': 0,
                    'avg_rating': 0,
                    'rating_5': 0, 'rating_4': 0, 'rating_3': 0, 'rating_2': 0, 'rating_1': 0
                }
        except Exception as e:
            print(f"Error in get_service_rating_stats: {e}")
            return {}

    @staticmethod
    def has_user_reviewed_booking(booking_id: int, customer_id: int) -> bool:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT id FROM reviews 
                    WHERE booking_id = ? AND customer_id = ?
                """, (booking_id, customer_id))
                return c.fetchone() is not None
        except Exception as e:
            print(f"Error in has_user_reviewed_booking: {e}")
            return False

    @staticmethod
    def get_customer_review_for_booking(booking_id: int, customer_id: int) -> Optional[Dict[str, Any]]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT rating, comment, created_at
                    FROM reviews 
                    WHERE booking_id = ? AND customer_id = ?
                """, (booking_id, customer_id))
                row = c.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error in get_customer_review_for_booking: {e}")
            return None

    @staticmethod
    def get_customer_all_reviews(customer_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT r.id, r.rating, r.comment, r.created_at,
                           s.title as service_title,
                           u.username as provider_name
                    FROM reviews r
                    JOIN services s ON r.service_id = s.id
                    JOIN users u ON r.provider_id = u.id
                    WHERE r.customer_id = ?
                    ORDER BY r.created_at DESC
                    LIMIT ?
                """, (customer_id, limit))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_customer_all_reviews: {e}")
            return []

    @staticmethod
    def get_provider_rating_stats(provider_id: int) -> Dict[str, Any]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT 
                        COUNT(*) as total_reviews,
                        COALESCE(AVG(rating), 0) as avg_rating,
                        SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) as rating_5,
                        SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) as rating_4,
                        SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) as rating_3,
                        SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) as rating_2,
                        SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as rating_1
                    FROM reviews
                    WHERE provider_id = ?
                """, (provider_id,))
                row = c.fetchone()
                if row:
                    result = dict(row)
                    result['avg_rating'] = round(result['avg_rating'], 1)
                    return result
                return {
                    'total_reviews': 0,
                    'avg_rating': 0,
                    'rating_5': 0, 'rating_4': 0, 'rating_3': 0, 'rating_2': 0, 'rating_1': 0
                }
        except Exception as e:
            print(f"Error in get_provider_rating_stats: {e}")
            return {}

    @staticmethod
    def delete_review(review_id: int, customer_id: int) -> Tuple[bool, str]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                c.execute("""
                    SELECT service_id FROM reviews 
                    WHERE id = ? AND customer_id = ?
                """, (review_id, customer_id))
                
                row = c.fetchone()
                if not row:
                    return False, "امتیاز مورد نظر یافت نشد یا شما دسترسی حذف آن را ندارید."
                
                service_id = row['service_id']
                c.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
                
                c.execute("""
                    UPDATE services 
                    SET avg_rating = (
                        SELECT COALESCE(ROUND(AVG(rating), 1), 0) FROM reviews WHERE service_id = ?
                    ),
                    review_count = (
                        SELECT COUNT(*) FROM reviews WHERE service_id = ?
                    )
                    WHERE id = ?
                """, (service_id, service_id, service_id))
                
                return True, "امتیاز با موفقیت حذف شد."
                
        except Exception as e:
            print(f"Error in delete_review: {e}")
            return False, f"خطا در حذف امتیاز: {str(e)}"