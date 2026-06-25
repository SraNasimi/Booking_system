import sqlite3
import os
import hashlib
from contextlib import contextmanager
from datetime import datetime
import time

# مسیر دیتابیس
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'booking.db')

# متغیر global برای اتصال تست (in-memory)
_TEST_CONNECTION = None


def set_test_connection(conn):
    """تنظیم اتصال دیتابیس برای تست (in-memory)"""
    global _TEST_CONNECTION
    _TEST_CONNECTION = conn


def hash_password(password: str) -> str:
    """هش کردن رمز عبور با SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def get_db_path():
    """بازگرداندن مسیر دیتابیس"""
    return DB_PATH


@contextmanager
def get_db_connection():
    """مدیریت خودکار اتصال دیتابیس با rollback در صورت خطا"""
    global _TEST_CONNECTION
    
    # اگر در حالت تست هستیم، از اتصال in-memory استفاده کن
    if _TEST_CONNECTION:
        yield _TEST_CONNECTION
    else:
        # افزایش timeout و فعال کردن WAL mode برای کاهش قفل
        conn = sqlite3.connect(DB_PATH, timeout=20)
        conn.row_factory = sqlite3.Row
        # فعال کردن WAL mode برای بهبود همزمانی
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def get_connection():
    """برای سازگاری با کدهای قدیمی - استفاده از context manager توصیه می‌شود"""
    global _TEST_CONNECTION
    if _TEST_CONNECTION:
        return _TEST_CONNECTION
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()

        # جدول users
        c.execute('''
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
            )
        ''')

        # اضافه کردن ستون‌های جدید در صورت نیاز (فقط یکبار)
        existing_columns = [col[1] for col in c.execute("PRAGMA table_info(users)")]
        for col, defn in [
            ('profile_image', 'TEXT DEFAULT NULL'),
            ('name', 'TEXT DEFAULT NULL'),
            ('bio', 'TEXT DEFAULT NULL'),
            ('specialty', 'TEXT DEFAULT NULL'),
            ('phone', 'TEXT DEFAULT NULL'),
            ('address', 'TEXT DEFAULT NULL'),
        ]:
            if col not in existing_columns:
                c.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")

        # جدول categories
        c.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')

        # ========== جدول services ==========
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='services'")
        table_exists = c.fetchone()
        
        if table_exists:
            c.execute("PRAGMA table_info(services)")
            columns = [col[1] for col in c.fetchall()]
            
            # اضافه کردن ستون‌های avg_rating و review_count در صورت نیاز
            if 'avg_rating' not in columns:
                c.execute("ALTER TABLE services ADD COLUMN avg_rating REAL DEFAULT 0")
            if 'review_count' not in columns:
                c.execute("ALTER TABLE services ADD COLUMN review_count INTEGER DEFAULT 0")
            
            if 'duration' in columns:
                c.execute("SELECT * FROM services")
                services_data = c.fetchall()
                c.execute("DROP TABLE services")
                
                c.execute('''
                    CREATE TABLE services (
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
                        FOREIGN KEY(provider_id) REFERENCES users(id) ON DELETE RESTRICT,
                        FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL
                    )
                ''')
                
                for row in services_data:
                    row_dict = {desc[0]: row[i] for i, desc in enumerate(c.description) if hasattr(c, 'description')}
                    c.execute('''
                        INSERT INTO services (id, provider_id, title, description, price, image, status, category_id, avg_rating, review_count)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        row_dict.get('id'), row_dict.get('provider_id'), row_dict.get('title'),
                        row_dict.get('description', ''), row_dict.get('price', 0),
                        row_dict.get('image'), row_dict.get('status', 'Active'), row_dict.get('category_id'),
                        row_dict.get('avg_rating', 0), row_dict.get('review_count', 0)
                    ))
        else:
            c.execute('''
                CREATE TABLE services (
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
                    FOREIGN KEY(provider_id) REFERENCES users(id) ON DELETE RESTRICT,
                    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL
                )
            ''')
        
        c.execute('CREATE INDEX IF NOT EXISTS idx_services_provider ON services(provider_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_services_status ON services(status)')

        # جدول time_slots
        c.execute('''
            CREATE TABLE IF NOT EXISTS time_slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                status TEXT CHECK(status IN ('Active','Inactive')) DEFAULT 'Active',
                FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE
            )
        ''')
        
        c.execute('CREATE INDEX IF NOT EXISTS idx_slots_service ON time_slots(service_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_slots_time ON time_slots(start_time, end_time)')

        # جدول bookings با ON DELETE RESTRICT
        c.execute('''
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
                FOREIGN KEY(customer_id) REFERENCES users(id) ON DELETE RESTRICT,
                FOREIGN KEY(provider_id) REFERENCES users(id) ON DELETE RESTRICT,
                FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE RESTRICT,
                FOREIGN KEY(slot_id) REFERENCES time_slots(id) ON DELETE RESTRICT
            )
        ''')
        
        c.execute('CREATE INDEX IF NOT EXISTS idx_bookings_customer ON bookings(customer_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_bookings_provider ON bookings(provider_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status)')

        # ========== جدول notifications با ستون type ==========
        c.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                is_read INTEGER DEFAULT 0,
                created_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')
        
        c.execute('CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type)')

        # ========== جدول reviews (امتیازات و نظرات) ==========
        c.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL,
                customer_id INTEGER NOT NULL,
                provider_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                comment TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
                FOREIGN KEY(customer_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(provider_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(service_id) REFERENCES services(id) ON DELETE CASCADE,
                UNIQUE(booking_id, customer_id)
            )
        ''')
        
        c.execute('CREATE INDEX IF NOT EXISTS idx_reviews_service ON reviews(service_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_reviews_provider ON reviews(provider_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_reviews_customer ON reviews(customer_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_reviews_booking ON reviews(booking_id)')

        # ایجاد ادمین پیش‌فرض با رمز هش شده
        admin_password = hash_password('admin')
        c.execute("SELECT id FROM users WHERE username='admin'")
        if not c.fetchone():
            c.execute(
                "INSERT INTO users (username, password, role, created_at) VALUES (?,?,?,?)",
                ('admin', admin_password, 'Admin', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )