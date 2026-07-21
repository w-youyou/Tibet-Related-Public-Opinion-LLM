import os
import django
import sys

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from chunker_api.models import AdminUser
from django.contrib.auth.hashers import make_password

def create_default_admin():
    username = "admin"
    password = os.getenv('ADMIN_INIT_PASSWORD')
    if not password:
        import secrets
        password = secrets.token_urlsafe(16)
        print(f" 环境变量 ADMIN_INIT_PASSWORD 未设置，已自动生成随机密码。")
    
    if AdminUser.objects.filter(username=username).exists():
        print(f"管理员账号 '{username}' 已存在。")
        return
        
    AdminUser.objects.create(
        username=username,
        password=make_password(password),
        email='admin@example.com',
        role='SUPER_ADMIN',
        is_active=True
    )
    print(f"✅ 管理员账号创建成功！\n用户名: {username}\n初始密码: {password}\n请登录后及时修改密码。")

if __name__ == '__main__':
    create_default_admin()
