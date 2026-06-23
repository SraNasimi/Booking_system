from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
from db.db import get_db_connection


class StatsModel:

    @staticmethod
    def get_admin_stats() -> Dict[str, Any]:
        """دریافت آمار کامل برای ادمین"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                stats = {}
                
                today = datetime.now()
                today_str = today.strftime('%Y-%m-%d')
                week_ago = (today - timedelta(days=7)).strftime('%Y-%m-%d')
                
                # آمار کاربران
                c.execute("SELECT COUNT(*) as count FROM users")
                row = c.fetchone()
                stats['total_users'] = row['count'] if row else 0
                
                c.execute("SELECT role, COUNT(*) FROM users GROUP BY role")
                stats['users_by_role'] = {row[0]: row[1] for row in c.fetchall()}
                
                # آمار سرویس‌ها
                c.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status='Active' THEN 1 ELSE 0 END) as active,
                        SUM(CASE WHEN status='Inactive' THEN 1 ELSE 0 END) as inactive
                    FROM services
                """)
                row = c.fetchone()
                stats['total_services'] = row[0] if row else 0
                stats['active_services'] = row[1] if row else 0
                stats['inactive_services'] = row[2] if row else 0
                
                # آمار رزروها (با یک کوئری)
                c.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN status='Confirmed' THEN 1 ELSE 0 END) as confirmed,
                        SUM(CASE WHEN DATE(created_at)=? THEN 1 ELSE 0 END) as daily,
                        SUM(CASE WHEN DATE(created_at)>=? THEN 1 ELSE 0 END) as weekly
                    FROM bookings
                """, (today_str, week_ago))
                row = c.fetchone()
                stats['total_bookings'] = row[0] if row else 0
                stats['confirmed_bookings'] = row[1] if row else 0
                stats['daily_bookings'] = row[2] if row else 0
                stats['weekly_bookings'] = row[3] if row else 0
                
                # آمار درآمد (با یک کوئری)
                c.execute("""
                    SELECT 
                        COALESCE(SUM(s.price), 0) as total,
                        COALESCE(SUM(CASE WHEN DATE(b.created_at)=? THEN s.price ELSE 0 END), 0) as daily,
                        COALESCE(SUM(CASE WHEN DATE(b.created_at)>=? THEN s.price ELSE 0 END), 0) as weekly
                    FROM bookings b
                    JOIN services s ON b.service_id = s.id
                    WHERE b.payment_status = 'Paid'
                """, (today_str, week_ago))
                row = c.fetchone()
                stats['total_income'] = row[0] if row else 0
                stats['daily_income'] = row[1] if row else 0
                stats['weekly_income'] = row[2] if row else 0
                
                # آمار ۷ روز گذشته برای نمودار (یک کوئری)
                c.execute("""
                    SELECT DATE(created_at) as date, COUNT(*) as count
                    FROM bookings 
                    WHERE DATE(created_at) >= DATE('now', '-6 days')
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """)
                daily_data = {row[0][5:]: row[1] for row in c.fetchall()}  # day[5:] = "MM-DD"
                
                # تکمیل روزهای خالی
                daily_chart = []
                for i in range(6, -1, -1):
                    day = (today - timedelta(days=i)).strftime('%m-%d')
                    daily_chart.append((day, daily_data.get(day, 0)))
                stats['daily_chart_data'] = daily_chart
                
                return stats
                
        except Exception as e:
            print(f"Error in get_admin_stats: {e}")
            return {
                'total_users': 0,
                'users_by_role': {},
                'total_services': 0,
                'active_services': 0,
                'inactive_services': 0,
                'total_bookings': 0,
                'confirmed_bookings': 0,
                'daily_bookings': 0,
                'weekly_bookings': 0,
                'total_income': 0,
                'daily_income': 0,
                'weekly_income': 0,
                'daily_chart_data': []
            }

    @staticmethod
    def get_top_services(limit: int = 5) -> List[Dict[str, Any]]:
        """دریافت محبوب‌ترین سرویس‌ها"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT s.title, COUNT(b.id) as booking_count, COALESCE(SUM(s.price), 0) as revenue
                    FROM bookings b 
                    JOIN services s ON b.service_id = s.id
                    WHERE b.status = 'Confirmed' AND b.payment_status = 'Paid'
                    GROUP BY s.id 
                    ORDER BY booking_count DESC 
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_top_services: {e}")
            return []

    @staticmethod
    def get_provider_stats(provider_id: int) -> Dict[str, Any]:
        """دریافت آمار یک ارائه‌دهنده"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                
                # یک کوئری برای چند آمار
                c.execute("""
                    SELECT 
                        (SELECT COUNT(*) FROM services WHERE provider_id = ?) as services,
                        (SELECT COUNT(*) FROM bookings WHERE provider_id = ?) as total_bookings,
                        (SELECT COUNT(*) FROM bookings WHERE provider_id = ? AND status = 'Confirmed') as confirmed_bookings,
                        (SELECT COALESCE(SUM(s.price), 0) FROM bookings b 
                         JOIN services s ON b.service_id = s.id
                         WHERE b.provider_id = ? AND b.payment_status = 'Paid') as income
                """, (provider_id, provider_id, provider_id, provider_id))
                row = c.fetchone()
                
                # آمار بر اساس وضعیت
                c.execute("""
                    SELECT status, COUNT(*) 
                    FROM bookings 
                    WHERE provider_id = ? 
                    GROUP BY status
                """, (provider_id,))
                status_counts = {row['status']: row[1] for row in c.fetchall()}                
                return {
                    'services': row[0] if row else 0,
                    'total_bookings': row[1] if row else 0,
                    'confirmed_bookings': row[2] if row else 0,
                    'income': row[3] if row else 0,
                    'status_counts': status_counts
                }
                
        except Exception as e:
            print(f"Error in get_provider_stats: {e}")
            return {
                'services': 0,
                'total_bookings': 0,
                'confirmed_bookings': 0,
                'income': 0,
                'status_counts': {}
            }

    @staticmethod
    def get_provider_weekly_stats(provider_id: int) -> List[Dict[str, Any]]:
        """دریافت آمار هفتگی یک ارائه‌دهنده (تعداد و درآمد روزانه)"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("""
                    SELECT 
                        DATE(b.created_at) as date,
                        COUNT(*) as booking_count,
                        COALESCE(SUM(s.price), 0) as daily_income
                    FROM bookings b
                    JOIN services s ON b.service_id = s.id
                    WHERE b.provider_id = ? 
                        AND DATE(b.created_at) >= DATE('now', '-6 days')
                        AND b.payment_status = 'Paid'
                    GROUP BY DATE(b.created_at)
                    ORDER BY date DESC
                """, (provider_id,))
                return [dict(row) for row in c.fetchall()]
        except Exception as e:
            print(f"Error in get_provider_weekly_stats: {e}")
            return []