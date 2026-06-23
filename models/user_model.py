import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
from db.db import get_db_connection, hash_password


class UserModel:

    @staticmethod
    def add_user(username: str, password: str, role: str) -> bool:
        """افزودن کاربر جدید - رمز باید قبلاً هش شده باشد"""
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute(
                    'INSERT INTO users (username, password, role, created_at) VALUES (?, ?, ?, ?)',
                    (username, password, role, now)
                )
            return True
        except sqlite3.IntegrityError:
            return False  # username تکراری
        except Exception as e:
            print(f"Error in add_user: {e}")
            return False

    @staticmethod
    def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
        """احراز هویت کاربر - برگرداندن دیکشنری از اطلاعات کاربر"""
        try:
            hashed_password = hash_password(password)
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute(
                    'SELECT id, username, role FROM users WHERE username = ? AND password = ?',
                    (username, hashed_password)
                )
                row = c.fetchone()
                if row:
                    return dict(row)
            return None
        except Exception as e:
            print(f"Error in authenticate: {e}")
            return None

    @staticmethod
    def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('SELECT * FROM users WHERE username = ?', (username,))
                row = c.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error in get_user_by_username: {e}")
            return None

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('SELECT * FROM users WHERE id = ?', (user_id,))
                row = c.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Error in get_user_by_id: {e}")
            return None

    @staticmethod
    def get_all_users() -> List[Dict[str, Any]]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('SELECT id, username, role, created_at FROM users ORDER BY role, username')
                rows = c.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error in get_all_users: {e}")
            return []

    @staticmethod
    def update_role(user_id: int, new_role: str) -> bool:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
            return True
        except Exception as e:
            print(f"Error in update_role: {e}")
            return False

    @staticmethod
    def delete_user(user_id: int) -> bool:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('DELETE FROM users WHERE id = ?', (user_id,))
            return True
        except Exception as e:
            print(f"Error in delete_user: {e}")
            return False

    @staticmethod
    def update_password(user_id: int, new_password: str) -> bool:
        """new_password باید قبلاً هش شده باشد"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('UPDATE users SET password = ? WHERE id = ?', (new_password, user_id))
            return True
        except Exception as e:
            print(f"Error in update_password: {e}")
            return False

    @staticmethod
    def update_profile_image(user_id: int, image_path: str) -> bool:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('UPDATE users SET profile_image = ? WHERE id = ?', (image_path, user_id))
            return True
        except Exception as e:
            print(f"Error in update_profile_image: {e}")
            return False

    @staticmethod
    def update_profile_info(user_id: int, name: str = None, bio: str = None, 
                           specialty: str = None) -> bool:
        """به‌روزرسانی اطلاعات پروفایل - برگرداندن True در صورت موفقیت"""
        try:
            fields = []
            values = []
            
            if name is not None:
                fields.append('name = ?')
                values.append(name)
            if bio is not None:
                fields.append('bio = ?')
                values.append(bio)
            if specialty is not None:
                fields.append('specialty = ?')
                values.append(specialty)
            
            if not fields:
                return True  # هیچ چیزی برای به‌روزرسانی نیست
            
            values.append(user_id)
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
            return True
        except Exception as e:
            print(f"Error in update_profile_info: {e}")
            return False

    @staticmethod
    def update_contact_info(user_id: int, phone: str = None, address: str = None) -> bool:
        """به‌روزرسانی اطلاعات تماس"""
        try:
            fields = []
            values = []
            
            if phone is not None:
                fields.append('phone = ?')
                values.append(phone)
            if address is not None:
                fields.append('address = ?')
                values.append(address)
            
            if not fields:
                return True
            
            values.append(user_id)
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
            return True
        except Exception as e:
            print(f"Error in update_contact_info: {e}")
            return False

    @staticmethod
    def get_users_by_role_stats() -> Dict[str, int]:
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute('SELECT role, COUNT(*) FROM users GROUP BY role')
                data = c.fetchall()
                return {row['role']: row[1] for row in data}
        except Exception as e:
            print(f"Error in get_users_by_role_stats: {e}")
            return {}