import jwt
import datetime
from functools import wraps
from django.conf import settings
from django.http import JsonResponse
from chunker_api.models import AdminUser

JWT_SECRET_KEY = getattr(settings, 'SECRET_KEY', 'default_secret_key_for_jwt')

def generate_admin_tokens(admin_user):
    """
    为管理员生成 Access Token 和 Refresh Token
    """
    now = datetime.datetime.utcnow()
    
    # Access Token (有效期 2 小时)
    access_payload = {
        'admin_id': str(admin_user.id),
        'username': admin_user.username,
        'role': admin_user.role,
        'token_type': 'access',
        'exp': now + datetime.timedelta(hours=2),
        'iat': now
    }
    access_token = jwt.encode(access_payload, JWT_SECRET_KEY, algorithm='HS256')
    
    # Refresh Token (有效期 7 天)
    refresh_payload = {
        'admin_id': str(admin_user.id),
        'token_type': 'refresh',
        'exp': now + datetime.timedelta(days=7),
        'iat': now
    }
    refresh_token = jwt.encode(refresh_payload, JWT_SECRET_KEY, algorithm='HS256')
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_in': 7200,
        'role': admin_user.role,
        'username': admin_user.username,
        'email': admin_user.email
    }

def verify_admin_token(token, expected_type='access'):
    """
    验证 Token 并返回 payload
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=['HS256'])
        if payload.get('token_type') != expected_type:
            return None
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None

def admin_jwt_required(allowed_roles=None):
    """
    管理员 JWT 身份验证装饰器
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return JsonResponse({'success': False, 'error': '未提供认证Token，请先登录'}, status=401)
            
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return JsonResponse({'success': False, 'error': '认证Token格式错误，应为 Bearer <Token>'}, status=401)
                
            payload = verify_admin_token(token, 'access')
            if not payload:
                return JsonResponse({'success': False, 'error': 'Token无效或已过期，请重新登录'}, status=401)
            
            try:
                admin_user = AdminUser.objects.get(id=payload['admin_id'], is_active=True)
            except AdminUser.DoesNotExist:
                return JsonResponse({'success': False, 'error': '管理员账号不存在或已被禁用'}, status=401)
            
            # 角色权限控制
            if allowed_roles:
                roles_list = [allowed_roles] if isinstance(allowed_roles, str) else allowed_roles
                if admin_user.role not in roles_list:
                    return JsonResponse({'success': False, 'error': '权限不足，禁止访问该接口'}, status=403)
            
            request.admin_user = admin_user
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
