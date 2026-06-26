# notification_server.py - اصلاح شده با پورت 8766
import asyncio
import json
import websockets
from datetime import datetime
import sqlite3
import os
from typing import Dict

# مسیر دیتابیس
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'booking.db')

# ذخیره ارتباطات فعال کاربران
connected_clients: Dict[int, websockets.WebSocketServerProtocol] = {}


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def save_notification(user_id: int, message: str, notification_type: str) -> int:
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO notifications (user_id, message, type, is_read, created_at)
                VALUES (?, ?, ?, 0, ?)
            """, (user_id, message, notification_type, now))
            conn.commit()
            return c.lastrowid
    except Exception as e:
        print(f"Error saving notification: {e}")
        return None


async def send_notification_to_user(user_id: int, message: str, notification_type: str):
    notification_id = save_notification(user_id, message, notification_type)
    
    if user_id in connected_clients:
        try:
            notification_data = {
                'type': 'notification',
                'id': notification_id,
                'notification_type': notification_type,
                'message': message,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            await connected_clients[user_id].send(json.dumps(notification_data))
            print(f"Notification sent to user {user_id}: {message}")
        except Exception as e:
            print(f"Error sending notification: {e}")


async def send_unread_notifications(websocket, user_id: int):
    try:
        with get_db_connection() as conn:
            c = conn.cursor()
            c.execute("""
                SELECT id, message, type, created_at
                FROM notifications
                WHERE user_id = ? AND is_read = 0
                ORDER BY created_at DESC
                LIMIT 50
            """, (user_id,))
            
            notifications = c.fetchall()
            
            for notif in notifications:
                notification_data = {
                    'type': 'notification',
                    'id': notif['id'],
                    'notification_type': notif['type'],
                    'message': notif['message'],
                    'created_at': notif['created_at']
                }
                await websocket.send(json.dumps(notification_data))
                print(f"Sent unread notification {notif['id']} to user {user_id}")
    except Exception as e:
        print(f"Error sending unread notifications: {e}")


async def handler(websocket, path):
    user_id = None
    
    try:
        message = await websocket.recv()
        data = json.loads(message)
        
        if data.get('type') == 'auth':
            user_id = data.get('user_id')
            if user_id:
                connected_clients[user_id] = websocket
                print(f"✅ User {user_id} connected")
                await send_unread_notifications(websocket, user_id)
                
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        if data.get('type') == 'ping':
                            await websocket.send(json.dumps({'type': 'pong'}))
                    except:
                        pass
                    
    except websockets.exceptions.ConnectionClosed:
        print(f"User {user_id} disconnected")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if user_id and user_id in connected_clients:
            del connected_clients[user_id]
            print(f"❌ User {user_id} disconnected")


async def start_websocket_server():
    """راه‌اندازی سرور WebSocket"""
    # استفاده از پورت 8766 و localhost
    try:
        async with websockets.serve(handler, "127.0.0.1", 8766):
            print("=" * 50)
            print("🚀 WebSocket Server started successfully!")
            print(f"📡 Server running on: ws://127.0.0.1:8766")
            print("💡 Waiting for client connections...")
            print("=" * 50)
            await asyncio.Future()
    except OSError as e:
        print(f"❌ Port 8766 is busy. Trying port 8767...")
        try:
            async with websockets.serve(handler, "127.0.0.1", 8767):
                print("=" * 50)
                print("🚀 WebSocket Server started successfully!")
                print(f"📡 Server running on: ws://127.0.0.1:8767")
                print("💡 Waiting for client connections...")
                print("=" * 50)
                await asyncio.Future()
        except Exception as e2:
            print(f"❌ Failed to start server: {e2}")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")


if __name__ == "__main__":
    print("🔧 Initializing WebSocket Notification Server...")
    print(f"📁 Database path: {DB_PATH}")
    
    if not os.path.exists(DB_PATH):
        print("⚠️ Database not found! Run main.py first to create database.")
    else:
        print("✅ Database found!")
    
    asyncio.run(start_websocket_server())