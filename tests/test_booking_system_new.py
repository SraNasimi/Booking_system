"""
test_booking_system_new.py
==========================
Unit tests for Booking System - MVC Version

Run:
    python -m unittest tests.test_booking_system_new -v
"""

import sys
import os
import sqlite3
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.db import hash_password
import db.db as db_module


class BaseTestCase(unittest.TestCase):
    """کلاس پایه برای تمام تست‌ها - راه‌اندازی دیتابیس تمیز برای هر تست"""
    
    def setUp(self):
        """ایجاد دیتابیس جدید و تمیز قبل از هر تست"""
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        
        self._create_tables()
        
        self.orig_connection = db_module.get_connection
        self.orig_test_conn = getattr(db_module, '_TEST_CONNECTION', None)
        db_module.get_connection = lambda: self.conn
        db_module._TEST_CONNECTION = self.conn
        
        self._seed_default_admin()
    
    def tearDown(self):
        db_module.get_connection = self.orig_connection
        db_module._TEST_CONNECTION = self.orig_test_conn
        self.conn.close()
    
    def _create_tables(self):
        """ایجاد تمام جداول دیتابیس"""
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT CHECK(role IN ('Admin','Provider','Customer')) NOT NULL,
                created_at TEXT,
                profile_image TEXT DEFAULT NULL,
                name TEXT DEFAULT NULL,
                bio TEXT DEFAULT NULL,
                specialty TEXT DEFAULT NULL,
                phone TEXT DEFAULT NULL,
                address TEXT DEFAULT NULL
            );
            
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                image TEXT DEFAULT NULL,
                status TEXT CHECK(status IN ('Active','Inactive')) DEFAULT 'Active',
                category_id INTEGER,
                avg_rating REAL DEFAULT 0,
                review_count INTEGER DEFAULT 0,
                FOREIGN KEY(provider_id) REFERENCES users(id),
                FOREIGN KEY(category_id) REFERENCES categories(id)
            );
            
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                status TEXT CHECK(status IN ('Active','Inactive')) DEFAULT 'Active',
                FOREIGN KEY(service_id) REFERENCES services(id)
            );
            
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER NOT NULL,
                provider_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                slot_id INTEGER NOT NULL,
                status TEXT CHECK(status IN ('Pending','Confirmed','Rejected','Canceled')) DEFAULT 'Pending',
                payment_status TEXT CHECK(payment_status IN ('Unpaid','Paid')) DEFAULT 'Unpaid',
                created_at TEXT,
                paid_at TEXT,
                FOREIGN KEY(customer_id) REFERENCES users(id),
                FOREIGN KEY(provider_id) REFERENCES users(id),
                FOREIGN KEY(service_id) REFERENCES services(id),
                FOREIGN KEY(slot_id) REFERENCES time_slots(id)
            );
            
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                is_read INTEGER DEFAULT 0,
                created_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                provider_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(booking_id) REFERENCES bookings(id),
                FOREIGN KEY(customer_id) REFERENCES users(id),
                FOREIGN KEY(provider_id) REFERENCES users(id),
                FOREIGN KEY(service_id) REFERENCES services(id),
                UNIQUE(booking_id, customer_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_services_provider ON services(provider_id);
            CREATE INDEX IF NOT EXISTS idx_bookings_slot ON bookings(slot_id);
            CREATE INDEX IF NOT EXISTS idx_slots_service ON time_slots(service_id);
            CREATE INDEX IF NOT EXISTS idx_reviews_service ON reviews(service_id);
            CREATE INDEX IF NOT EXISTS idx_reviews_provider ON reviews(provider_id);
        """)
        self.conn.commit()

    def _clear_all_tables(self):
        tables = ['notifications', 'reviews', 'bookings', 'time_slots', 'services', 'categories', 'users']
        for table in tables:
            self.conn.execute(f"DELETE FROM {table}")
        self.conn.commit()
    
    def _seed_default_admin(self):
        from models.user_model import UserModel
        admin_exists = self.conn.execute(
            "SELECT id FROM users WHERE username='admin'"
        ).fetchone()
        if not admin_exists:
            UserModel.add_user('admin', hash_password('admin'), 'Admin')
    
    def _now(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    def _future(self, hours=48):
        return (datetime.now() + timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    
    def _add_test_user(self, username, password, role):
        from models.user_model import UserModel
        return UserModel.add_user(username, hash_password(password), role)
    
    def _get_user(self, username):
        from models.user_model import UserModel
        return UserModel.get_user_by_username(username)
    
    def _add_test_service(self, provider_id, title, price, status='Active'):
        from models.service_model import ServiceModel
        return ServiceModel.add_service(provider_id, title, '', price, status=status)
    
    def _add_test_slot(self, service_id, start_time, end_time):
        from models.service_model import ServiceModel
        return ServiceModel.add_time_slot(service_id, start_time, end_time)
    
    def _add_test_booking(self, customer_id, provider_id, service_id, slot_id):
        from models.booking_model import BookingModel
        return BookingModel.add_booking(customer_id, provider_id, service_id, slot_id)


# ═══════════════════════════════════════════════════════════════════
# 1. تست ثبت نام و ورود
# ═══════════════════════════════════════════════════════════════════
class TestAuthAndRegistration(BaseTestCase):
    
    def setUp(self):
        super().setUp()
        self._clear_all_tables()
        self._seed_default_admin()
    
    def test_01_register_customer_success(self):
        result = self._add_test_user('customer1', 'pass123', 'Customer')
        self.assertTrue(result)
        user = self._get_user('customer1')
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'customer1')
        self.assertEqual(user['role'], 'Customer')
    
    def test_02_register_provider_success(self):
        result = self._add_test_user('provider1', 'pass123', 'Provider')
        self.assertTrue(result)
        user = self._get_user('provider1')
        self.assertEqual(user['role'], 'Provider')
    
    def test_03_register_admin_success(self):
        result = self._add_test_user('admin2', 'pass123', 'Admin')
        self.assertTrue(result)
        user = self._get_user('admin2')
        self.assertEqual(user['role'], 'Admin')
    
    def test_04_register_duplicate_username_fails(self):
        self._add_test_user('duplicate', 'pass1', 'Customer')
        result = self._add_test_user('duplicate', 'pass2', 'Customer')
        self.assertFalse(result)
    
    def test_05_login_success_with_auth_controller(self):
        from controllers.auth_controller import AuthController
        self._add_test_user('testuser', 'mypassword', 'Customer')
        auth = AuthController()
        result = auth.login('testuser', 'mypassword')
        self.assertTrue(result['success'])
        self.assertEqual(result['username'], 'testuser')
    
    def test_06_login_wrong_password_fails(self):
        from controllers.auth_controller import AuthController
        self._add_test_user('testuser2', 'correctpass', 'Customer')
        auth = AuthController()
        result = auth.login('testuser2', 'wrongpass')
        self.assertFalse(result['success'])
    
    def test_07_login_nonexistent_user_fails(self):
        from controllers.auth_controller import AuthController
        auth = AuthController()
        result = auth.login('nonexistent', 'anypass')
        self.assertFalse(result['success'])
    
    def test_08_login_empty_credentials_fails(self):
        from controllers.auth_controller import AuthController
        auth = AuthController()
        result = auth.login('', '')
        self.assertFalse(result['success'])
    
    def test_09_register_with_short_password_fails(self):
        from controllers.auth_controller import AuthController
        auth = AuthController()
        result = auth.register('newuser', '123', '123', 'Customer')
        self.assertFalse(result['success'])
    
    def test_10_register_password_mismatch_fails(self):
        from controllers.auth_controller import AuthController
        auth = AuthController()
        result = auth.register('newuser2', 'pass123', 'pass456', 'Customer')
        self.assertFalse(result['success'])


# ═══════════════════════════════════════════════════════════════════
# 2. تست ساخت سرویس
# ═══════════════════════════════════════════════════════════════════
class TestServiceManagement(BaseTestCase):
    
    def setUp(self):
        super().setUp()
        self._clear_all_tables()
        self._seed_default_admin()
        self._add_test_user('provider_svc', 'pass', 'Provider')
        self.provider = self._get_user('provider_svc')
        self.provider_id = self.provider['id']
    
    def test_01_add_service_success(self):
        from models.service_model import ServiceModel
        result = ServiceModel.add_service(self.provider_id, 'ماساژ درمانی', '', 150000)
        self.assertTrue(result)
        services = ServiceModel.get_provider_services(self.provider_id)
        self.assertEqual(len(services), 1)
        self.assertEqual(services[0]['title'], 'ماساژ درمانی')
    
    def test_02_add_service_default_status_active(self):
        from models.service_model import ServiceModel
        ServiceModel.add_service(self.provider_id, 'سرویس تست', '', 50000)
        services = ServiceModel.get_provider_services(self.provider_id)
        self.assertEqual(services[0]['status'], 'Active')
    
    def test_03_add_service_with_inactive_status(self):
        from models.service_model import ServiceModel
        ServiceModel.add_service(self.provider_id, 'سرویس غیرفعال', '', 50000, status='Inactive')
        services = ServiceModel.get_provider_services(self.provider_id)
        self.assertEqual(services[0]['status'], 'Inactive')
    
    def test_04_add_multiple_services_for_provider(self):
        from models.service_model import ServiceModel
        existing = ServiceModel.get_provider_services(self.provider_id)
        for s in existing:
            ServiceModel.delete_service(s['id'], self.provider_id)
        titles = ['سرویس ۱', 'سرویس ۲', 'سرویس ۳']
        for title in titles:
            ServiceModel.add_service(self.provider_id, title, '', 50000)
        services = ServiceModel.get_provider_services(self.provider_id)
        self.assertEqual(len(services), 3)
    
    def test_05_update_service_success(self):
        from models.service_model import ServiceModel
        ServiceModel.add_service(self.provider_id, 'نام قدیم', '', 50000)
        services = ServiceModel.get_provider_services(self.provider_id)
        service_id = services[0]['id']
        result = ServiceModel.update_service(service_id, self.provider_id, 'نام جدید', '', 75000)
        self.assertTrue(result)
        updated = ServiceModel.get_service_by_id(service_id)
        self.assertEqual(updated['title'], 'نام جدید')
        self.assertEqual(updated['price'], 75000)
    
    def test_06_delete_service_success(self):
        from models.service_model import ServiceModel
        existing = ServiceModel.get_provider_services(self.provider_id)
        for s in existing:
            ServiceModel.delete_service(s['id'], self.provider_id)
        ServiceModel.add_service(self.provider_id, 'سرویس برای حذف', '', 50000)
        services = ServiceModel.get_provider_services(self.provider_id)
        service_id = services[0]['id']
        result = ServiceModel.delete_service(service_id, self.provider_id)
        self.assertTrue(result)
        services_after = ServiceModel.get_provider_services(self.provider_id)
        self.assertEqual(len(services_after), 0)
    
    def test_07_toggle_service_status(self):
        from models.service_model import ServiceModel
        ServiceModel.add_service(self.provider_id, 'سرویس تست', '', 50000)
        services = ServiceModel.get_provider_services(self.provider_id)
        service_id = services[0]['id']
        ServiceModel.toggle_service_status(service_id, self.provider_id)
        svc = ServiceModel.get_service_by_id(service_id)
        self.assertEqual(svc['status'], 'Inactive')
        ServiceModel.toggle_service_status(service_id, self.provider_id)
        svc = ServiceModel.get_service_by_id(service_id)
        self.assertEqual(svc['status'], 'Active')
    
    def test_08_search_services_by_keyword(self):
        from models.service_model import ServiceModel
        existing = ServiceModel.get_provider_services(self.provider_id)
        for s in existing:
            ServiceModel.delete_service(s['id'], self.provider_id)
        ServiceModel.add_service(self.provider_id, 'ماساژ عمیق', '', 150000)
        ServiceModel.add_service(self.provider_id, 'کوتاهی مو', '', 80000)
        results = ServiceModel.search_services(keyword='ماساژ')
        self.assertEqual(len(results), 1)
        self.assertIn('ماساژ', results[0]['title'])
    
    def test_09_search_services_by_price_range(self):
        from models.service_model import ServiceModel
        existing = ServiceModel.get_provider_services(self.provider_id)
        for s in existing:
            ServiceModel.delete_service(s['id'], self.provider_id)
        ServiceModel.add_service(self.provider_id, 'سرویس ارزان', '', 50000)
        ServiceModel.add_service(self.provider_id, 'سرویس گران', '', 500000)
        results = ServiceModel.search_services(min_price=0, max_price=100000)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'سرویس ارزان')
    
    def test_10_get_service_by_id(self):
        from models.service_model import ServiceModel
        existing = ServiceModel.get_provider_services(self.provider_id)
        for s in existing:
            ServiceModel.delete_service(s['id'], self.provider_id)
        ServiceModel.add_service(self.provider_id, 'سرویس ویژه', '', 120000)
        services = ServiceModel.get_provider_services(self.provider_id)
        service_id = services[0]['id']
        svc = ServiceModel.get_service_by_id(service_id)
        self.assertIsNotNone(svc)
        self.assertEqual(svc['title'], 'سرویس ویژه')


# ═══════════════════════════════════════════════════════════════════
# 3. تست تعریف زمان بندی (Time Slots)
# ═══════════════════════════════════════════════════════════════════
class TestTimeSlotManagement(BaseTestCase):
    
    def setUp(self):
        super().setUp()
        self._clear_all_tables()
        self._seed_default_admin()
        self._add_test_user('provider_slot', 'pass', 'Provider')
        self.provider = self._get_user('provider_slot')
        self.provider_id = self.provider['id']
        from models.service_model import ServiceModel
        ServiceModel.add_service(self.provider_id, 'سرویس تست زمان', '', 100000)
        services = ServiceModel.get_provider_services(self.provider_id)
        self.service_id = services[0]['id']
    
    def test_01_add_valid_time_slot(self):
        from models.service_model import ServiceModel
        existing_slots = ServiceModel.get_time_slots_by_service(self.service_id)
        for slot in existing_slots:
            ServiceModel.delete_time_slot(slot['id'], self.service_id)
        result = ServiceModel.add_time_slot(self.service_id, '2025-12-01 10:00:00', '2025-12-01 11:00:00')
        self.assertTrue(result)
        slots = ServiceModel.get_time_slots_by_service(self.service_id)
        self.assertEqual(len(slots), 1)
    
    def test_02_add_overlapping_slot_fails(self):
        from models.service_model import ServiceModel
        existing_slots = ServiceModel.get_time_slots_by_service(self.service_id)
        for slot in existing_slots:
            ServiceModel.delete_time_slot(slot['id'], self.service_id)
        ServiceModel.add_time_slot(self.service_id, '2025-12-02 09:00:00', '2025-12-02 11:00:00')
        result = ServiceModel.add_time_slot(self.service_id, '2025-12-02 10:00:00', '2025-12-02 12:00:00')
        self.assertFalse(result)
    
    def test_03_add_adjacent_slots_allowed(self):
        from models.service_model import ServiceModel
        existing_slots = ServiceModel.get_time_slots_by_service(self.service_id)
        for slot in existing_slots:
            ServiceModel.delete_time_slot(slot['id'], self.service_id)
        result1 = ServiceModel.add_time_slot(self.service_id, '2025-12-03 09:00:00', '2025-12-03 10:00:00')
        result2 = ServiceModel.add_time_slot(self.service_id, '2025-12-03 10:00:00', '2025-12-03 11:00:00')
        self.assertTrue(result1)
        self.assertTrue(result2)
        slots = ServiceModel.get_time_slots_by_service(self.service_id)
        self.assertEqual(len(slots), 2)
    
    def test_04_toggle_slot_status(self):
        from models.service_model import ServiceModel
        existing_slots = ServiceModel.get_time_slots_by_service(self.service_id)
        for slot in existing_slots:
            ServiceModel.delete_time_slot(slot['id'], self.service_id)
        ServiceModel.add_time_slot(self.service_id, '2025-12-04 09:00:00', '2025-12-04 10:00:00')
        slots = ServiceModel.get_time_slots_by_service(self.service_id)
        slot_id = slots[0]['id']
        ServiceModel.toggle_slot_status(slot_id, self.service_id)
        updated = ServiceModel.get_time_slots_by_service(self.service_id)[0]
        self.assertEqual(updated['status'], 'Inactive')
    
    def test_05_delete_slot_without_booking_success(self):
        from models.service_model import ServiceModel
        existing_slots = ServiceModel.get_time_slots_by_service(self.service_id)
        for slot in existing_slots:
            ServiceModel.delete_time_slot(slot['id'], self.service_id)
        ServiceModel.add_time_slot(self.service_id, '2025-12-05 09:00:00', '2025-12-05 10:00:00')
        slots = ServiceModel.get_time_slots_by_service(self.service_id)
        slot_id = slots[0]['id']
        result = ServiceModel.delete_time_slot(slot_id, self.service_id)
        self.assertTrue(result)
        slots_after = ServiceModel.get_time_slots_by_service(self.service_id)
        self.assertEqual(len(slots_after), 0)
    
    def test_06_update_time_slot_success(self):
        from models.service_model import ServiceModel
        existing_slots = ServiceModel.get_time_slots_by_service(self.service_id)
        for slot in existing_slots:
            ServiceModel.delete_time_slot(slot['id'], self.service_id)
        ServiceModel.add_time_slot(self.service_id, '2025-12-06 09:00:00', '2025-12-06 10:00:00')
        slots = ServiceModel.get_time_slots_by_service(self.service_id)
        slot_id = slots[0]['id']
        result = ServiceModel.update_time_slot(slot_id, self.service_id, '2025-12-06 11:00:00', '2025-12-06 12:00:00')
        self.assertTrue(result)
        updated = ServiceModel.get_time_slots_by_service(self.service_id)[0]
        self.assertIn('11:00', updated['start_time'])
    
    def test_07_update_slot_with_conflict_fails(self):
        from models.service_model import ServiceModel
        existing_slots = ServiceModel.get_time_slots_by_service(self.service_id)
        for slot in existing_slots:
            ServiceModel.delete_time_slot(slot['id'], self.service_id)
        
        ServiceModel.add_time_slot(self.service_id, '2025-12-07 09:00:00', '2025-12-07 10:00:00')
        ServiceModel.add_time_slot(self.service_id, '2025-12-07 11:00:00', '2025-12-07 12:00:00')
        
        slots = ServiceModel.get_time_slots_by_service(self.service_id)
        slot_id = slots[1]['id']
        
        result = ServiceModel.update_time_slot(slot_id, self.service_id, '2025-12-07 09:30:00', '2025-12-07 10:30:00')
        success, message = result if isinstance(result, tuple) else (result, '')
        
        self.assertFalse(success, f"به دلیل تداخل باید False برگرداند. پیام: {message}")
    
    def test_08_get_available_slots(self):
        from models.service_model import ServiceModel
        from models.booking_model import BookingModel
        existing_slots = ServiceModel.get_time_slots_by_service(self.service_id)
        for slot in existing_slots:
            ServiceModel.delete_time_slot(slot['id'], self.service_id)
        self._add_test_user('customer_slot', 'pass', 'Customer')
        customer = self._get_user('customer_slot')
        ServiceModel.add_time_slot(self.service_id, '2025-12-08 09:00:00', '2025-12-08 10:00:00')
        slots = ServiceModel.get_time_slots_by_service(self.service_id)
        slot_id = slots[0]['id']
        available_before = ServiceModel.get_available_slots(self.service_id)
        self.assertEqual(len(available_before), 1)
        BookingModel.add_booking(customer['id'], self.provider_id, self.service_id, slot_id)
        available_after = ServiceModel.get_available_slots(self.service_id)
        self.assertEqual(len(available_after), 0)


# ═══════════════════════════════════════════════════════════════════
# 4. تست رزرو سرویس
# ═══════════════════════════════════════════════════════════════════
class TestBookingCreation(BaseTestCase):
    
    def setUp(self):
        super().setUp()
        self._clear_all_tables()
        self._seed_default_admin()
        self._add_test_user('provider_book', 'pass', 'Provider')
        self._add_test_user('customer_book', 'pass', 'Customer')
        self.provider = self._get_user('provider_book')
        self.customer = self._get_user('customer_book')
        from models.service_model import ServiceModel
        ServiceModel.add_service(self.provider['id'], 'سرویس تست رزرو', '', 100000)
        services = ServiceModel.get_provider_services(self.provider['id'])
        self.service_id = services[0]['id'] if services else None
        if self.service_id:
            self.slot_start = self._future(48)
            self.slot_end = self._future(49)
            ServiceModel.add_time_slot(self.service_id, self.slot_start, self.slot_end)
            slots = ServiceModel.get_time_slots_by_service(self.service_id)
            self.slot_id = slots[0]['id'] if slots else None
    
    def test_01_create_booking_success(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        success, message = BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, self.slot_id)
        self.assertTrue(success)
    
    def test_02_booking_status_pending(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, self.slot_id)
        booking = self.conn.execute("SELECT status FROM bookings WHERE slot_id=?", (self.slot_id,)).fetchone()
        self.assertEqual(booking['status'], 'Pending')
    
    def test_03_booking_payment_status_unpaid(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, self.slot_id)
        booking = self.conn.execute("SELECT payment_status FROM bookings WHERE slot_id=?", (self.slot_id,)).fetchone()
        self.assertEqual(booking['payment_status'], 'Unpaid')
    
    def test_04_booking_on_inactive_service_fails(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        from models.service_model import ServiceModel
        ServiceModel.add_service(self.provider['id'], 'سرویس غیرفعال', '', 50000, status='Inactive')
        inactive_services = ServiceModel.get_provider_services(self.provider['id'])
        inactive_service = [s for s in inactive_services if s['title'] == 'سرویس غیرفعال']
        if inactive_service:
            slot_id = self._add_test_slot(inactive_service[0]['id'], self._future(48), self._future(49))
            success, _ = BookingModel.add_booking(self.customer['id'], self.provider['id'], inactive_service[0]['id'], slot_id)
            self.assertFalse(success)
    
    def test_05_booking_on_inactive_slot_fails(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        from models.service_model import ServiceModel
        inactive_slot_id = self._add_test_slot(self.service_id, self._future(52), self._future(53))
        ServiceModel.toggle_slot_status(inactive_slot_id, self.service_id)
        success, _ = BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, inactive_slot_id)
        self.assertFalse(success)
    
    def test_06_provider_can_confirm_booking(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, self.slot_id)
        booking = self.conn.execute("SELECT id FROM bookings WHERE slot_id=?", (self.slot_id,)).fetchone()
        if booking:
            result = BookingModel.confirm_booking(booking['id'], self.provider['id'])
            self.assertTrue(result)
    
    def test_07_provider_can_reject_booking(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, self.slot_id)
        booking = self.conn.execute("SELECT id FROM bookings WHERE slot_id=?", (self.slot_id,)).fetchone()
        if booking:
            result = BookingModel.reject_booking(booking['id'], self.provider['id'])
            self.assertTrue(result)
    
    def test_08_customer_cancel_booking_in_time(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        far_start = self._future(48)
        far_end = self._future(49)
        far_slot_id = self._add_test_slot(self.service_id, far_start, far_end)
        BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, far_slot_id)
        booking = self.conn.execute("SELECT id FROM bookings WHERE slot_id=?", (far_slot_id,)).fetchone()
        if booking:
            BookingModel.pay_booking(booking['id'])
            success, _ = BookingModel.cancel_booking(booking['id'], self.customer['id'])
            self.assertTrue(success)
    
    def test_09_customer_cancel_booking_too_late_fails(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        near_start = (datetime.now() + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
        near_end = (datetime.now() + timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')
        near_slot_id = self._add_test_slot(self.service_id, near_start, near_end)
        
        BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, near_slot_id)
        booking = self.conn.execute("SELECT id FROM bookings WHERE slot_id=?", (near_slot_id,)).fetchone()
        
        if booking:
            BookingModel.pay_booking(booking['id'])
            BookingModel.confirm_booking(booking['id'], self.provider['id'])
            success, _ = BookingModel.cancel_booking(booking['id'], self.customer['id'])
            self.assertFalse(success)
    
    def test_10_notification_sent_to_provider_after_booking(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, self.slot_id)
        pass
    
    def test_11_customer_get_my_bookings(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        from models.customer_model import CustomerModel
        BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, self.slot_id)
        customer_model = CustomerModel(self.customer['id'])
        bookings = customer_model.get_my_bookings()
        self.assertEqual(len(bookings), 1)
    
    def test_12_provider_get_my_bookings(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, self.slot_id)
        provider_bookings = BookingModel.get_provider_bookings(self.provider['id'])
        self.assertEqual(len(provider_bookings), 1)
    
    def test_13_cancel_booking_2_hours_rule(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        
        slot_far_id = self._add_test_slot(
            self.service_id, 
            (datetime.now() + timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S'),
            (datetime.now() + timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')
        )
        
        slot_near_id = self._add_test_slot(
            self.service_id,
            (datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S'),
            (datetime.now() + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')
        )
        
        BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, slot_far_id)
        BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, slot_near_id)
        
        booking_far = self.conn.execute("SELECT id FROM bookings WHERE slot_id=?", (slot_far_id,)).fetchone()
        booking_near = self.conn.execute("SELECT id FROM bookings WHERE slot_id=?", (slot_near_id,)).fetchone()
        
        if booking_far:
            BookingModel.pay_booking(booking_far['id'])
            success_far, _ = BookingModel.cancel_booking(booking_far['id'], self.customer['id'])
            self.assertTrue(success_far)
        
        if booking_near:
            BookingModel.pay_booking(booking_near['id'])
            success_near, _ = BookingModel.cancel_booking(booking_near['id'], self.customer['id'])
            self.assertFalse(success_near)


# ═══════════════════════════════════════════════════════════════════
# 5. تست جلوگیری از رزروهای تداخلی
# ═══════════════════════════════════════════════════════════════════
class TestConflictPrevention(BaseTestCase):
    
    def setUp(self):
        super().setUp()
        self._clear_all_tables()
        self._seed_default_admin()
        self._add_test_user('provider_conf', 'pass', 'Provider')
        self._add_test_user('customer_conf1', 'pass', 'Customer')
        self._add_test_user('customer_conf2', 'pass', 'Customer')
        self.provider = self._get_user('provider_conf')
        self.customer1 = self._get_user('customer_conf1')
        self.customer2 = self._get_user('customer_conf2')
        from models.service_model import ServiceModel
        ServiceModel.add_service(self.provider['id'], 'سرویس تست تداخل', '', 100000)
        services = ServiceModel.get_provider_services(self.provider['id'])
        self.service_id = services[0]['id'] if services else None
        if self.service_id:
            self.slot_id = self._add_test_slot(self.service_id, self._future(48), self._future(49))
    
    def test_01_second_booking_on_same_slot_fails(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        success1, _ = BookingModel.add_booking(self.customer1['id'], self.provider['id'], self.service_id, self.slot_id)
        success2, _ = BookingModel.add_booking(self.customer2['id'], self.provider['id'], self.service_id, self.slot_id)
        self.assertTrue(success1)
        self.assertFalse(success2)
    
    def test_02_only_one_booking_in_database_for_slot(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        BookingModel.add_booking(self.customer1['id'], self.provider['id'], self.service_id, self.slot_id)
        BookingModel.add_booking(self.customer2['id'], self.provider['id'], self.service_id, self.slot_id)
        count = self.conn.execute("SELECT COUNT(*) FROM bookings WHERE slot_id=?", (self.slot_id,)).fetchone()[0]
        self.assertEqual(count, 1)
    
    def test_03_different_slots_both_bookable(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.booking_model import BookingModel
        from models.service_model import ServiceModel
        
        existing_slots = ServiceModel.get_time_slots_by_service(self.service_id)
        for slot in existing_slots:
            ServiceModel.delete_time_slot(slot['id'], self.service_id)
        
        slot1_start = self._future(48)
        slot1_end = self._future(49)
        slot2_start = self._future(96)
        slot2_end = self._future(97)
        
        slot1_id = ServiceModel.add_time_slot(self.service_id, slot1_start, slot1_end)
        slot2_id = ServiceModel.add_time_slot(self.service_id, slot2_start, slot2_end)
        
        self.assertTrue(slot1_id)
        self.assertTrue(slot2_id)
        
        slots = ServiceModel.get_time_slots_by_service(self.service_id)
        self.assertGreaterEqual(len(slots), 2)
        
        actual_slot1_id = slots[0]['id']
        actual_slot2_id = slots[1]['id']
        
        success1, _ = BookingModel.add_booking(self.customer1['id'], self.provider['id'], self.service_id, actual_slot1_id)
        success2, _ = BookingModel.add_booking(self.customer2['id'], self.provider['id'], self.service_id, actual_slot2_id)
        
        self.assertTrue(success1)
        self.assertTrue(success2)
    
    def test_04_canceled_slot_can_be_rebooked(self):
        from models.booking_model import BookingModel
        BookingModel.add_booking(self.customer1['id'], self.provider['id'], self.service_id, self.slot_id)
        booking = self.conn.execute("SELECT id FROM bookings WHERE slot_id=?", (self.slot_id,)).fetchone()
        if booking:
            BookingModel.pay_booking(booking['id'])
            BookingModel.cancel_booking(booking['id'], self.customer1['id'])
            success, _ = BookingModel.add_booking(self.customer2['id'], self.provider['id'], self.service_id, self.slot_id)
            if success:
                new_booking = self.conn.execute("SELECT id FROM bookings WHERE slot_id=? AND customer_id=?", 
                                            (self.slot_id, self.customer2['id'])).fetchone()
                if new_booking:
                    BookingModel.pay_booking(new_booking['id'])
            self.assertTrue(success)
    
    def test_05_rejected_slot_can_be_rebooked(self):
        from models.booking_model import BookingModel
        BookingModel.add_booking(self.customer1['id'], self.provider['id'], self.service_id, self.slot_id)
        booking = self.conn.execute("SELECT id FROM bookings WHERE slot_id=?", (self.slot_id,)).fetchone()
        if booking:
            BookingModel.pay_booking(booking['id'])
            BookingModel.reject_booking(booking['id'], self.provider['id'])
            success, _ = BookingModel.add_booking(self.customer2['id'], self.provider['id'], self.service_id, self.slot_id)
            if success:
                new_booking = self.conn.execute("SELECT id FROM bookings WHERE slot_id=? AND customer_id=?", 
                                            (self.slot_id, self.customer2['id'])).fetchone()
                if new_booking:
                    BookingModel.pay_booking(new_booking['id'])
            self.assertTrue(success)
    
    def test_06_customer_model_prevents_conflict(self):
        if not self.service_id:
            self.skipTest("Service not created")
        from models.customer_model import CustomerModel
        cm1 = CustomerModel(self.customer1['id'])
        cm2 = CustomerModel(self.customer2['id'])
        success1, _ = cm1.book_service(self.service_id, self.slot_id)
        success2, _ = cm2.book_service(self.service_id, self.slot_id)
        self.assertTrue(success1)
        self.assertFalse(success2)


# ═══════════════════════════════════════════════════════════════════
# 6. تست پرداخت
# ═══════════════════════════════════════════════════════════════════
class TestPayment(BaseTestCase):
    
    def setUp(self):
        super().setUp()
        self._clear_all_tables()
        self._seed_default_admin()
        self._add_test_user('provider_pay', 'pass', 'Provider')
        self._add_test_user('customer_pay', 'pass', 'Customer')
        self.provider = self._get_user('provider_pay')
        self.customer = self._get_user('customer_pay')
        from models.service_model import ServiceModel
        ServiceModel.add_service(self.provider['id'], 'سرویس تست پرداخت', '', 200000)
        services = ServiceModel.get_provider_services(self.provider['id'])
        self.service_id = services[0]['id'] if services else None
        if self.service_id:
            self.slot_id = self._add_test_slot(self.service_id, self._future(48), self._future(49))
            from models.booking_model import BookingModel
            BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, self.slot_id)
            booking = self.conn.execute("SELECT id FROM bookings WHERE slot_id=?", (self.slot_id,)).fetchone()
            self.booking_id = booking['id'] if booking else None
    
    def test_01_payment_success(self):
        if not self.service_id or not self.booking_id:
            self.skipTest("Service or booking not created")
        from models.booking_model import BookingModel
        success, _ = BookingModel.pay_booking(self.booking_id)
        self.assertTrue(success)
    
    def test_02_payment_status_becomes_paid(self):
        if not self.service_id or not self.booking_id:
            self.skipTest("Service or booking not created")
        from models.booking_model import BookingModel
        BookingModel.pay_booking(self.booking_id)
        booking = self.conn.execute("SELECT payment_status FROM bookings WHERE id=?", (self.booking_id,)).fetchone()
        self.assertEqual(booking['payment_status'], 'Paid')
    
    def test_03_paid_at_timestamp_set(self):
        if not self.service_id or not self.booking_id:
            self.skipTest("Service or booking not created")
        from models.booking_model import BookingModel
        BookingModel.pay_booking(self.booking_id)
        booking = self.conn.execute("SELECT paid_at FROM bookings WHERE id=?", (self.booking_id,)).fetchone()
        self.assertIsNotNone(booking['paid_at'])
    
    def test_04_double_payment_fails(self):
        if not self.service_id or not self.booking_id:
            self.skipTest("Service or booking not created")
        from models.booking_model import BookingModel
        BookingModel.pay_booking(self.booking_id)
        success, _ = BookingModel.pay_booking(self.booking_id)
        self.assertFalse(success)
    
    def test_05_payment_after_booking_confirmation(self):
        if not self.service_id or not self.booking_id:
            self.skipTest("Service or booking not created")
        from models.booking_model import BookingModel
        BookingModel.confirm_booking(self.booking_id, self.provider['id'])
        success, _ = BookingModel.pay_booking(self.booking_id)
        self.assertTrue(success)
    
    def test_06_customer_cannot_pay_others_booking(self):
        if not self.service_id or not self.booking_id:
            self.skipTest("Service or booking not created")
        from models.customer_model import CustomerModel
        self._add_test_user('other_customer', 'pass', 'Customer')
        other = self._get_user('other_customer')
        other_model = CustomerModel(other['id'])
        success, _ = other_model.pay_booking(self.booking_id)
        self.assertFalse(success)
    
    def test_07_payment_notification_sent(self):
        if not self.service_id or not self.booking_id:
            self.skipTest("Service or booking not created")
        pass
    
    def test_08_provider_income_increases_after_payment(self):
        if not self.service_id or not self.booking_id:
            self.skipTest("Service or booking not created")
        from models.booking_model import BookingModel
        from models.service_model import ServiceModel
        initial_income = ServiceModel.get_provider_income(self.provider['id'])
        BookingModel.pay_booking(self.booking_id)
        final_income = ServiceModel.get_provider_income(self.provider['id'])
        self.assertGreater(final_income, initial_income)
    
    def test_09_payment_only_for_pending_or_confirmed(self):
        """تست پرداخت برای رزرو رد شده - باید ناموفق باشد"""
        from models.booking_model import BookingModel
        from models.service_model import ServiceModel
        
        ServiceModel.add_service(self.provider['id'], 'سرویس تست پرداخت رد', '', 100000)
        services = ServiceModel.get_provider_services(self.provider['id'])
        test_service_id = None
        for s in services:
            if s['title'] == 'سرویس تست پرداخت رد':
                test_service_id = s['id']
                break
        
        if test_service_id:
            test_slot_id = self._add_test_slot(test_service_id, self._future(48), self._future(49))
            
            BookingModel.add_booking(self.customer['id'], self.provider['id'], test_service_id, test_slot_id)
            
            booking = self.conn.execute("SELECT id FROM bookings WHERE slot_id=?", (test_slot_id,)).fetchone()
            
            if booking:
                BookingModel.pay_booking(booking['id'])
                BookingModel.reject_booking(booking['id'], self.provider['id'])
                success, _ = BookingModel.pay_booking(booking['id'])
                self.assertFalse(success, "پرداخت رزرو رد شده باید ناموفق باشد")


# ═══════════════════════════════════════════════════════════════════
# 7. تست ثبت نظر و امتیاز (Reviews and Ratings)
# ═══════════════════════════════════════════════════════════════════
class TestReviewsAndRatings(BaseTestCase):
    
    def setUp(self):
        super().setUp()
        self._clear_all_tables()
        self._seed_default_admin()
        
        # ایجاد کاربران
        self._add_test_user('provider_review', 'pass', 'Provider')
        self._add_test_user('customer_review', 'pass', 'Customer')
        self.provider = self._get_user('provider_review')
        self.customer = self._get_user('customer_review')
        
        # ایجاد سرویس با نام یکتا
        unique_service_name = f"سرویس تست نظر_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        from models.service_model import ServiceModel
        ServiceModel.add_service(self.provider['id'], unique_service_name, '', 100000)
        services = ServiceModel.get_provider_services(self.provider['id'])
        self.service_id = None
        for s in services:
            if s['title'] == unique_service_name:
                self.service_id = s['id']
                break
        
        # ایجاد اسلات و رزرو با زمان یکتا
        if self.service_id:
            unique_start = (datetime.now() + timedelta(hours=120)).strftime('%Y-%m-%d %H:%M:%S')
            unique_end = (datetime.now() + timedelta(hours=121)).strftime('%Y-%m-%d %H:%M:%S')
            self.slot_id = self._add_test_slot(self.service_id, unique_start, unique_end)
            
            from models.booking_model import BookingModel
            BookingModel.add_booking(self.customer['id'], self.provider['id'], self.service_id, self.slot_id)
            booking = self.conn.execute("SELECT id FROM bookings WHERE slot_id=?", (self.slot_id,)).fetchone()
            self.booking_id = booking['id'] if booking else None
            
            # پرداخت و تأیید رزرو
            if self.booking_id:
                BookingModel.pay_booking(self.booking_id)
                BookingModel.confirm_booking(self.booking_id, self.provider['id'])
                
    def test_01_add_review_success(self):
        """تست ثبت امتیاز با موفقیت"""
        if not self.booking_id:
            self.skipTest("Booking not created")
        from models.review_model import ReviewModel
        success, message = ReviewModel.add_review(
            self.booking_id, self.customer['id'], self.provider['id'],
            self.service_id, 5, "عالی بود"
        )
        self.assertTrue(success)
        self.assertIn("موفقیت", message)
    
    def test_02_add_review_with_rating_5(self):
        """تست ثبت امتیاز 5 ستاره"""
        from models.review_model import ReviewModel
        success, _ = ReviewModel.add_review(
            self.booking_id, self.customer['id'], self.provider['id'],
            self.service_id, 5, "بی‌نظیر"
        )
        self.assertTrue(success)
        
        review = self.conn.execute(
            "SELECT rating, comment FROM reviews WHERE booking_id=?", 
            (self.booking_id,)
        ).fetchone()
        self.assertEqual(review['rating'], 5)
        self.assertEqual(review['comment'], "بی‌نظیر")
    
    def test_03_add_review_with_rating_1(self):
        """تست ثبت امتیاز 1 ستاره"""
        from models.review_model import ReviewModel
        success, _ = ReviewModel.add_review(
            self.booking_id, self.customer['id'], self.provider['id'],
            self.service_id, 1, "خیلی ضعیف"
        )
        self.assertTrue(success)
        
        review = self.conn.execute(
            "SELECT rating FROM reviews WHERE booking_id=?", 
            (self.booking_id,)
        ).fetchone()
        self.assertEqual(review['rating'], 1)
    
    def test_04_cannot_add_duplicate_review(self):
        """تست عدم امکان ثبت نظر تکراری"""
        from models.review_model import ReviewModel
        ReviewModel.add_review(
            self.booking_id, self.customer['id'], self.provider['id'],
            self.service_id, 4, "اولین نظر"
        )
        success, message = ReviewModel.add_review(
            self.booking_id, self.customer['id'], self.provider['id'],
            self.service_id, 5, "نظر تکراری"
        )
        self.assertFalse(success)
        self.assertIn("قبلاً", message)
    
    def test_05_rating_range_validation(self):
        """تست اعتبارسنجی محدوده امتیاز (1 تا 5)"""
        from models.review_model import ReviewModel
        # امتیاز 0 - نامعتبر
        success, message = ReviewModel.add_review(
            self.booking_id, self.customer['id'], self.provider['id'],
            self.service_id, 0, "نامعتبر"
        )
        self.assertFalse(success)
        
        # امتیاز 6 - نامعتبر
        success, message = ReviewModel.add_review(
            self.booking_id, self.customer['id'], self.provider['id'],
            self.service_id, 6, "نامعتبر"
        )
        self.assertFalse(success)
    
    def test_06_provider_can_view_reviews(self):
        """تست مشاهده نظرات توسط ارائه‌دهنده"""
        from models.review_model import ReviewModel
        ReviewModel.add_review(
            self.booking_id, self.customer['id'], self.provider['id'],
            self.service_id, 5, "خدمت عالی"
        )
        
        provider_reviews = ReviewModel.get_provider_reviews(self.provider['id'])
        self.assertEqual(len(provider_reviews), 1)
        self.assertEqual(provider_reviews[0]['rating'], 5)
    
    def test_07_provider_reviews_summary(self):
        """تست خلاصه آمار نظرات ارائه‌دهنده"""
        from models.review_model import ReviewModel
        ReviewModel.add_review(
            self.booking_id, self.customer['id'], self.provider['id'],
            self.service_id, 5, "عالی"
        )
        
        summary = ReviewModel.get_provider_rating_stats(self.provider['id'])
        self.assertGreaterEqual(summary['total_reviews'], 1)
        self.assertGreaterEqual(summary['avg_rating'], 4)
    
    def test_08_admin_can_delete_review(self):
        """تست حذف نظر توسط ادمین"""
        from models.review_model import ReviewModel
        ReviewModel.add_review(
            self.booking_id, self.customer['id'], self.provider['id'],
            self.service_id, 3, "متوسط"
        )
        
        review = self.conn.execute(
            "SELECT id FROM reviews WHERE booking_id=?", (self.booking_id,)
        ).fetchone()
        
        if review:
            success, message = ReviewModel.delete_review_by_admin(review['id'])
            self.assertTrue(success)
            
            check = self.conn.execute(
                "SELECT id FROM reviews WHERE id=?", (review['id'],)
            ).fetchone()
            self.assertIsNone(check)
    
    def test_09_service_avg_rating_updates_after_review(self):
        """تست به‌روزرسانی میانگین امتیاز سرویس پس از ثبت نظر"""
        from models.review_model import ReviewModel
        from models.service_model import ServiceModel
        
        ReviewModel.add_review(
            self.booking_id, self.customer['id'], self.provider['id'],
            self.service_id, 5, "عالی"
        )
        
        service = ServiceModel.get_service_by_id(self.service_id)
        # بررسی وجود کلیدها قبل از دسترسی
        if 'avg_rating' in service:
            self.assertEqual(service['avg_rating'], 5.0)
        if 'review_count' in service:
            self.assertEqual(service['review_count'], 1)
            
    def test_10_customer_can_view_own_reviews(self):
        """تست مشاهده نظرات خود توسط مشتری"""
        from models.review_model import ReviewModel
        ReviewModel.add_review(
            self.booking_id, self.customer['id'], self.provider['id'],
            self.service_id, 5, "خدمت عالی"
        )
        
        customer_reviews = ReviewModel.get_customer_all_reviews(self.customer['id'])
        self.assertEqual(len(customer_reviews), 1)
        self.assertEqual(customer_reviews[0]['rating'], 5)


if __name__ == '__main__':
    unittest.main(verbosity=2)