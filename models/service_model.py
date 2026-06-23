import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from db.db import get_db_connection


class ServiceModel:

    # ==================== دسته‌بندی‌ها ====================
    
    @staticmethod
    def get_all_categories() -> List[Tuple[int, str]]:
        """دریافت همه دسته‌بندی‌ها"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT id, name FROM categories ORDER BY name")
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_all_categories: {e}")
            return []

    @staticmethod
    def add_category(name: str) -> Optional[int]:
        """افزودن دسته‌بندی جدید - برگرداندن ID دسته‌بندی"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                try:
                    c.execute("INSERT INTO categories (name) VALUES (?)", (name,))
                    return c.lastrowid
                except sqlite3.IntegrityError:
                    # دسته‌بندی قبلاً وجود دارد
                    c.execute("SELECT id FROM categories WHERE name=?", (name,))
                    row = c.fetchone()
                    return row[0] if row else None
        except Exception as e:
            print(f"Error in add_category: {e}")
            return None

    @staticmethod
    def get_category_by_id(category_id: int) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات یک دسته‌بندی"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("SELECT id, name FROM categories WHERE id = ?", (category_id,))
                row = c.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error in get_category_by_id: {e}")
            return None

    # ==================== سرویس‌ها (بدون duration) ====================

    @staticmethod
    def get_provider_services(provider_id: int) -> List[Dict[str, Any]]:
        """دریافت همه سرویس‌های یک ارائه‌دهنده (بدون مدت زمان)"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT s.id, s.title, s.price, s.status,
                           COALESCE(cat.name, 'بدون دسته‌بندی') as category,
                           s.description, s.image, s.category_id
                    FROM services s
                    LEFT JOIN categories cat ON s.category_id = cat.id
                    WHERE s.provider_id = ?
                    ORDER BY s.title
                """, (provider_id,))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_provider_services: {e}")
            return []

    @staticmethod
    def get_service_by_id(service_id: int) -> Optional[Dict[str, Any]]:
        """دریافت اطلاعات یک سرویس با ID (بدون مدت زمان)"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT s.id, s.provider_id, s.title, s.description,
                           s.price, s.status, u.username, s.image,
                           COALESCE(cat.name, '') as category, 
                           COALESCE(s.category_id, 0) as category_id
                    FROM services s
                    JOIN users u ON s.provider_id = u.id
                    LEFT JOIN categories cat ON s.category_id = cat.id
                    WHERE s.id = ?
                """, (service_id,))
                row = c.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error in get_service_by_id: {e}")
            return None

    @staticmethod
    def add_service(provider_id: int, title: str, description: str, 
                    price: float, image: str = None, 
                    category_id: int = None, status: str = 'Active') -> bool:
        """افزودن سرویس جدید (بدون مدت زمان) - برگرداندن True در صورت موفقیت"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO services
                        (provider_id, title, description, price, image, category_id, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (provider_id, title, description, float(price),
                      image, category_id, status))
            return True
        except Exception as e:
            print(f"Error in add_service: {e}")
            return False

    @staticmethod
    def update_service(service_id: int, provider_id: int, title: str, 
                      description: str, price: float, 
                      image: str = None, category_id: int = None, 
                      status: str = None) -> bool:
        """به‌روزرسانی سرویس (بدون مدت زمان) - برگرداندن True در صورت موفقیت"""
        try:
            fields = ["title = ?", "description = ?", "price = ?"]
            values = [title, description, float(price)]
            
            if image is not None:
                fields.append("image = ?")
                values.append(image)
            if category_id is not None:
                fields.append("category_id = ?")
                values.append(category_id)
            if status is not None:
                fields.append("status = ?")
                values.append(status)
            
            values.extend([service_id, provider_id])
            
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute(f"""
                    UPDATE services 
                    SET {', '.join(fields)} 
                    WHERE id = ? AND provider_id = ?
                """, values)
            return True
        except Exception as e:
            print(f"Error in update_service: {e}")
            return False

    @staticmethod
    def delete_service(service_id: int, provider_id: int) -> Tuple[bool, str]:
        """حذف سرویس - فقط در صورتی که رزرو تأیید شده نداشته باشد"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                # بررسی وجود رزروهای تأیید شده برای این سرویس
                c.execute("""
                    SELECT COUNT(*) FROM bookings b
                    JOIN services s ON b.service_id = s.id
                    WHERE s.id = ? AND b.status = 'Confirmed'
                """, (service_id,))
                confirmed_count = c.fetchone()[0]
                
                if confirmed_count > 0:
                    return False, "این سرویس دارای رزروهای تأیید شده است و قابل حذف نمی‌باشد."
                
                # حذف بازه‌های زمانی
                c.execute("DELETE FROM time_slots WHERE service_id = ?", (service_id,))
                
                # حذف سرویس
                c.execute("DELETE FROM services WHERE id = ? AND provider_id = ?", 
                        (service_id, provider_id))
                
                if c.rowcount == 0:
                    return False, "سرویس یافت نشد یا شما دسترسی حذف آن را ندارید."
                
                return True, "سرویس با موفقیت حذف شد."
                
        except Exception as e:
            print(f"Error in delete_service: {e}")
            return False, f"خطا در حذف سرویس: {str(e)}"
            

    @staticmethod
    def toggle_service_status(service_id: int, provider_id: int) -> Tuple[bool, str]:
        """تغییر وضعیت فعال/غیرفعال سرویس"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                # بررسی وجود رزرو فعال
                c.execute("""
                    SELECT COUNT(*) FROM bookings b
                    JOIN services s ON b.service_id = s.id
                    WHERE s.id = ? AND b.status IN ('Pending', 'Confirmed')
                """, (service_id,))
                if c.fetchone()[0] > 0:
                    return False, "این سرویس دارای رزرو فعال است و نمی‌توان وضعیت آن را تغییر داد."
                
                c.execute("""
                    UPDATE services
                    SET status = CASE WHEN status = 'Active' THEN 'Inactive' ELSE 'Active' END
                    WHERE id = ? AND provider_id = ?
                """, (service_id, provider_id))
                
                if c.rowcount == 0:
                    return False, "سرویس یافت نشد."
                
                # دریافت وضعیت جدید برای نمایش پیام مناسب
                c.execute("SELECT status FROM services WHERE id = ?", (service_id,))
                row = c.fetchone()
                new_status_text = 'غیرفعال' if row['status'] == 'Inactive' else 'فعال'
                
                return True, f"وضعیت سرویس با موفقیت به {new_status_text} تغییر کرد."
                
        except Exception as e:
            print(f"Error in toggle_service_status: {e}")
            return False, f"خطا در تغییر وضعیت سرویس: {str(e)}"
            

    # ==================== بازه‌های زمانی (اسلات‌ها) ====================

    @staticmethod
    def check_slot_overlap(service_id: int, start_time: str, end_time: str, 
                           exclude_slot_id: int = None) -> bool:
        """
        بررسی تداخل زمانی
        برگرداندن True اگر تداخل وجود دارد
        """
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                query = """
                    SELECT id FROM time_slots
                    WHERE service_id = ? AND status = 'Active'
                      AND (start_time < ? AND end_time > ?)
                """
                params = [service_id, end_time, start_time]
                
                if exclude_slot_id is not None:
                    query += " AND id != ?"
                    params.append(exclude_slot_id)
                
                c.execute(query, params)
                return c.fetchone() is not None
        except Exception as e:
            print(f"Error in check_slot_overlap: {e}")
            return True  # در صورت خطا، فرض می‌کنیم تداخل دارد

    @staticmethod
    def add_time_slot(service_id: int, start_time: str, end_time: str) -> bool:
        """افزودن بازه زمانی جدید - برگرداندن True در صورت موفقیت"""
        try:
            # بررسی تداخل زمانی
            if ServiceModel.check_slot_overlap(service_id, start_time, end_time):
                return False
            
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO time_slots (service_id, start_time, end_time, status)
                    VALUES (?, ?, ?, 'Active')
                """, (service_id, start_time, end_time))
            return True
        except Exception as e:
            print(f"Error in add_time_slot: {e}")
            return False

    @staticmethod
    def update_time_slot(slot_id: int, service_id: int, new_start: str, new_end: str) -> Tuple[bool, str]:
        """ویرایش بازه زمانی - فقط در صورتی که رزرو فعال نداشته باشد"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                # بررسی وجود رزرو فعال برای این اسلات
                c.execute("""
                    SELECT id FROM bookings 
                    WHERE slot_id = ? AND status IN ('Pending', 'Confirmed')
                """, (slot_id,))
                if c.fetchone():
                    return False, "این بازه زمانی دارای رزرو فعال است و قابل ویرایش نمی‌باشد."
                
                # بررسی تداخل با بازه‌های دیگر (به جز خودش)
                if ServiceModel.check_slot_overlap(service_id, new_start, new_end, slot_id):
                    return False, "این بازه زمانی با بازه دیگر تداخل دارد."
                
                c.execute("""
                    UPDATE time_slots 
                    SET start_time = ?, end_time = ? 
                    WHERE id = ? AND service_id = ?
                """, (new_start, new_end, slot_id, service_id))
                
                if c.rowcount == 0:
                    return False, "بازه زمانی یافت نشد."
                
                return True, "بازه زمانی با موفقیت ویرایش شد."
                
        except Exception as e:
            print(f"Error in update_time_slot: {e}")
            return False, f"خطا در ویرایش بازه زمانی: {str(e)}"
            

    @staticmethod
    def get_time_slots_by_service(service_id: int) -> List[Dict[str, Any]]:
        """دریافت همه بازه‌های زمانی یک سرویس"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT id, start_time, end_time, status
                    FROM time_slots 
                    WHERE service_id = ? 
                    ORDER BY start_time
                """, (service_id,))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_time_slots_by_service: {e}")
            return []

    @staticmethod
    def get_available_slots(service_id: int) -> List[Dict[str, Any]]:
        """دریافت بازه‌های زمانی available (رزرو نشده و فعال)"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT ts.id, ts.start_time, ts.end_time
                    FROM time_slots ts
                    LEFT JOIN bookings b ON ts.id = b.slot_id 
                        AND b.status IN ('Pending', 'Confirmed')
                    WHERE ts.service_id = ? AND ts.status = 'Active' AND b.id IS NULL
                    ORDER BY ts.start_time
                """, (service_id,))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_available_slots: {e}")
            return []

    @staticmethod
    def toggle_slot_status(slot_id: int, service_id: int) -> Tuple[bool, str]:
        """تغییر وضعیت فعال/غیرفعال بازه زمانی - فقط در صورتی که رزرو فعال نداشته باشد"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                # بررسی وجود رزرو فعال
                c.execute("""
                    SELECT id FROM bookings 
                    WHERE slot_id = ? AND status IN ('Pending', 'Confirmed')
                """, (slot_id,))
                if c.fetchone():
                    return False, "این بازه زمانی دارای رزرو فعال است و نمی‌توان وضعیت آن را تغییر داد."
                
                c.execute("""
                    UPDATE time_slots
                    SET status = CASE WHEN status = 'Active' THEN 'Inactive' ELSE 'Active' END
                    WHERE id = ? AND service_id = ?
                """, (slot_id, service_id))
                
                if c.rowcount == 0:
                    return False, "بازه زمانی یافت نشد."
                
                return True, "وضعیت بازه زمانی با موفقیت تغییر کرد."
                
        except Exception as e:
            print(f"Error in toggle_slot_status: {e}")
            return False, f"خطا در تغییر وضعیت بازه زمانی: {str(e)}"
            

    @staticmethod
    def delete_time_slot(slot_id: int, service_id: int = None) -> Tuple[bool, str]:
        """
        حذف بازه زمانی - فقط در صورتی که رزرو فعال نداشته باشد
        """
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                # بررسی وجود رزرو فعال
                c.execute("""
                    SELECT id FROM bookings 
                    WHERE slot_id = ? AND status IN ('Pending', 'Confirmed')
                """, (slot_id,))
                if c.fetchone():
                    return False, "این بازه زمانی دارای رزرو فعال است و قابل حذف نمی‌باشد."
                
                if service_id:
                    c.execute("DELETE FROM time_slots WHERE id = ? AND service_id = ?", 
                            (slot_id, service_id))
                else:
                    c.execute("DELETE FROM time_slots WHERE id = ?", (slot_id,))
                
                if c.rowcount == 0:
                    return False, "بازه زمانی یافت نشد."
                
                return True, "بازه زمانی با موفقیت حذف شد."
                
        except Exception as e:
            print(f"Error in delete_time_slot: {e}")
            return False, f"خطا در حذف بازه زمانی: {str(e)}"
            

    # ==================== جستجو و گزارش ====================

    @staticmethod
    def search_services(keyword: str = '', category: str = '', provider: str = '', 
                       min_price: float = 0, max_price: float = 10_000_000, 
                       active_only: bool = True) -> List[Dict[str, Any]]:
        """جستجوی سرویس‌ها با فیلترهای مختلف (بدون مدت زمان)"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                query = """
                    SELECT s.id, s.title, COALESCE(cat.name, '') as category, 
                           u.username as provider_name, s.price, s.status
                    FROM services s
                    JOIN users u ON s.provider_id = u.id
                    LEFT JOIN categories cat ON s.category_id = cat.id
                    WHERE s.title LIKE ? AND s.price BETWEEN ? AND ?
                """
                params = [f'%{keyword}%', min_price, max_price]
                
                if category:
                    query += " AND cat.name LIKE ?"
                    params.append(f'%{category}%')
                if provider:
                    query += " AND u.username LIKE ?"
                    params.append(f'%{provider}%')
                if active_only:
                    query += " AND s.status = 'Active'"
                
                query += " ORDER BY s.title"
                
                c.execute(query, params)
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in search_services: {e}")
            return []

    @staticmethod
    def get_provider_income(provider_id: int) -> float:
        """محاسبه درآمد یک ارائه‌دهنده از رزروهای پرداخت شده"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT COALESCE(SUM(s.price), 0)
                    FROM bookings b 
                    JOIN services s ON b.service_id = s.id
                    WHERE s.provider_id = ? AND b.payment_status = 'Paid'
                """, (provider_id,))
                row = c.fetchone()
                return row[0] if row else 0.0
        except Exception as e:
            print(f"Error in get_provider_income: {e}")
            return 0.0

    # ==================== متدهای مدیریتی برای ادمین ====================

    @staticmethod
    def get_all_services_for_admin() -> List[Dict[str, Any]]:
        """دریافت همه سرویس‌ها برای ادمین (همراه با تعداد رزروها) - بدون مدت زمان"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT s.id, u.username as provider_name, s.title, s.price, 
                           s.status, COUNT(b.id) as booking_count
                    FROM services s
                    JOIN users u ON s.provider_id = u.id
                    LEFT JOIN bookings b ON s.id = b.service_id
                    GROUP BY s.id 
                    ORDER BY u.username, s.title
                """)
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_all_services_for_admin: {e}")
            return []

    @staticmethod
    def admin_toggle_service(service_id: int) -> Tuple[bool, str]:
        """تغییر وضعیت سرویس توسط ادمین"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                # بررسی وجود رزرو فعال
                c.execute("""
                    SELECT COUNT(*) FROM bookings b
                    JOIN services s ON b.service_id = s.id
                    WHERE s.id = ? AND b.status IN ('Pending', 'Confirmed')
                """, (service_id,))
                if c.fetchone()[0] > 0:
                    return False, "این سرویس دارای رزرو فعال است و نمی‌توان وضعیت آن را تغییر داد."
                
                c.execute("""
                    UPDATE services
                    SET status = CASE WHEN status = 'Active' THEN 'Inactive' ELSE 'Active' END
                    WHERE id = ?
                """, (service_id,))
                
                if c.rowcount == 0:
                    return False, "سرویس یافت نشد."
                
                # دریافت وضعیت جدید برای نمایش پیام مناسب
                c.execute("SELECT status FROM services WHERE id = ?", (service_id,))
                row = c.fetchone()
                new_status_text = 'غیرفعال' if row['status'] == 'Inactive' else 'فعال'
                
                return True, f"وضعیت سرویس با موفقیت به {new_status_text} تغییر کرد."
                
        except Exception as e:
            print(f"Error in admin_toggle_service: {e}")
            return False, f"خطا در تغییر وضعیت سرویس: {str(e)}"
            

    @staticmethod
    def admin_delete_service(service_id: int) -> Tuple[bool, str]:
        """حذف سرویس توسط ادمین - فقط در صورتی که رزرو تأیید شده نداشته باشد"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                # بررسی وجود رزروهای تأیید شده برای این سرویس
                c.execute("""
                    SELECT COUNT(*) FROM bookings b
                    JOIN services s ON b.service_id = s.id
                    WHERE s.id = ? AND b.status = 'Confirmed'
                """, (service_id,))
                confirmed_count = c.fetchone()[0]
                
                if confirmed_count > 0:
                    return False, "این سرویس دارای رزروهای تأیید شده است و قابل حذف نمی‌باشد."
                
                # حذف بازه‌های زمانی
                c.execute("DELETE FROM time_slots WHERE service_id = ?", (service_id,))
                
                # حذف سرویس
                c.execute("DELETE FROM services WHERE id = ?", (service_id,))
                
                if c.rowcount == 0:
                    return False, "سرویس یافت نشد."
                
                return True, "سرویس با موفقیت حذف شد."
                
        except Exception as e:
            print(f"Error in admin_delete_service: {e}")
            return False, f"خطا در حذف سرویس: {str(e)}"