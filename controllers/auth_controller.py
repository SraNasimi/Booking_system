# controllers/auth_controller.py
from models.user_model import UserModel
from db.db import hash_password


class AuthController:
    """کنترلر احراز هویت - مدیریت ورود و ثبت‌نام"""

    def login(self, username: str, password: str) -> dict:
        """
        احراز هویت کاربر
        برگرداندن: دیکشنری شامل success, role, user_id, message
        """
        if not username or not password:
            return {
                'success': False,
                'message': 'نام کاربری و رمز عبور الزامی هستند.'
            }

        user = UserModel.get_user_by_username(username)
        
        if not user:
            return {
                'success': False,
                'message': 'نام کاربری یا رمز عبور اشتباه است.'
            }
        
        # هش کردن رمز ورودی و مقایسه
        hashed_password = hash_password(password)
        
        if user.get('password') != hashed_password:
            return {
                'success': False,
                'message': 'نام کاربری یا رمز عبور اشتباه است.'
            }
        
        return {
            'success': True,
            'user_id': user.get('id'),
            'role': user.get('role'),
            'username': user.get('username'),
            'message': 'ورود با موفقیت انجام شد.'
        }

    def register(self, username: str, password: str, password_confirm: str, role: str) -> dict:
        """
        ثبت‌نام کاربر جدید
        برگرداندن: دیکشنری شامل success, message
        """
        # اعتبارسنجی ورودی‌ها
        if not username or not password:
            return {
                'success': False,
                'message': 'نام کاربری و رمز عبور الزامی هستند.'
            }
        
        if len(password) < 4:
            return {
                'success': False,
                'message': 'رمز عبور باید حداقل ۴ کاراکتر باشد.'
            }
        
        if password != password_confirm:
            return {
                'success': False,
                'message': 'رمز عبور و تکرار آن مطابقت ندارند.'
            }
        
        # بررسی نقش معتبر
        valid_roles = ['Provider', 'Customer']
        if role not in valid_roles:
            return {
                'success': False,
                'message': f'نقش نامعتبر. نقش‌های مجاز: {valid_roles}'
            }
        
        # هش کردن رمز عبور
        hashed_password = hash_password(password)
        
        # افزودن کاربر
        success = UserModel.add_user(username, hashed_password, role)
        
        if success:
            return {
                'success': True,
                'message': 'ثبت‌نام با موفقیت انجام شد. اکنون می‌توانید وارد شوید.'
            }
        else:
            return {
                'success': False,
                'message': 'این نام کاربری قبلاً ثبت شده است.'
            }