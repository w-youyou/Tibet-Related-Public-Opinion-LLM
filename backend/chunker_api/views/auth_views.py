import json
import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from utils.Tools.excel_validator import EnterpriseUserValidator
from ..models import User

logger = logging.getLogger(__name__)


# 导入doc文件处理库
try:
    from docx import Document as DocxDocument
    import win32com.client
    DOC_SUPPORT = True
except ImportError:
    DOC_SUPPORT = False

def generate_jsonl_content(chunks):
    """生成JSONL格式的内容"""
    jsonl_lines = []
    for chunk in chunks:
        jsonl_lines.append(json.dumps(chunk, ensure_ascii=False))
    return '\n'.join(jsonl_lines)

def read_doc_file(file_path: str) -> str:
    """读取.doc文件内容"""
    if not DOC_SUPPORT:
        raise Exception("缺少.doc文件处理依赖，请安装pywin32: pip install pywin32")
    
    try:
        import pythoncom
        
        # 初始化COM组件
        pythoncom.CoInitialize()
        
        # 使用win32com.client读取.doc文件
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        
        # 按段落读取，保持段落结构
        doc = word.Documents.Open(file_path)
        paragraphs = []
        for paragraph in doc.Paragraphs:
            text = paragraph.Range.Text.strip()
            if text:  # 只添加非空段落
                paragraphs.append(text)
        
        doc.Close()
        word.Quit()
        
        # 用换行符连接段落
        return '\n'.join(paragraphs)
    except Exception as e:
        raise Exception(f"读取.doc文件失败: {str(e)}")
    finally:
        try:
            if 'word' in locals():
                word.Quit()
            # 清理COM组件
            pythoncom.CoUninitialize()
        except:
            pass


# ==================== 用户认证相关API ====================

@csrf_exempt
@require_http_methods(["POST"])
def register(request):
    """用户注册（支持个人用户和企业用户）"""
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            return JsonResponse({'success': False, 'error': '无效的请求格式，需要一个JSON对象。'}, status=400)
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        email = data.get('email', '').strip()
        age = data.get('age')
        gender = data.get('gender', '').strip()
        user_type = data.get('user_type', 'personal').strip()  # 新增：用户类型
        employee_id = data.get('employee_id', '').strip()  # 新增：工号

        # 验证必填字段 用户名 密码  年龄
        if not username or not password or not age:
            return JsonResponse({
                'success': False,
                'error': '用户名、密码、年龄为必填项'
            }, status=400)

        # 企业用户特殊验证
        if user_type == 'enterprise':
            if not employee_id:
                return JsonResponse({
                    'success': False,
                    'error': '企业用户必须提供工号'
                }, status=400)

            # 验证企业用户信息
            validator = EnterpriseUserValidator()
            validation_result = validator.validate_enterprise_user(
                name=username,
                employee_id=employee_id
            )

            if not validation_result['valid']:
                return JsonResponse({
                    'success': False,
                    'error': validation_result['message']
                }, status=400)

            # 验证通过，可以使用 validation_result['user_info'] 获取更多信息
            logger.info(f"企业用户验证通过: {username} ({employee_id})")

        # 个人用户需要邮箱
        if user_type == 'personal' and not email:
            return JsonResponse({
                'success': False,
                'error': '个人用户邮箱为必填项'
            }, status=400)

        # 检查用户名是否已存在
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                'success': False,
                'error': '用户名已存在'
            }, status=400)

        # 检查邮箱是否已存在（如果提供）
        if email and User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'error': '邮箱已被注册'
            }, status=400)

        # 检查工号是否已被注册（企业用户）
        if user_type == 'enterprise' and User.objects.filter(employee_id=employee_id).exists():
            return JsonResponse({
                'success': False,
                'error': '该工号已被注册'
            }, status=400)

        # 创建用户
        user = User.objects.create_user(
            username=username,
            email=email if email else f"{employee_id}@company.com",  # 企业用户默认邮箱
            password=password,
            user_type=user_type,
            employee_id=employee_id if user_type == 'enterprise' else None,
            age=age if age else None,
            gender=gender if gender in ['M', 'F', 'O'] else None
        )

        # 自动登录
        login(request, user)

        # -----------------------------
        # 新增：注册时初始化 UserPersona
        # -----------------------------
        from ..models import UserPersona
        from utils.Tools.get_age_group import get_age_group
        age_group = get_age_group(age)
        role = 'enterprise' if user_type == 'enterprise' else 'local'
        UserPersona.objects.create(
            user=user,
            age_group=age_group,
            role=role
        )

        return JsonResponse({
            'success': True,
            'message': '注册成功',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'user_type': user.user_type,
                'employee_id': user.employee_id,
                'age': user.age,
                'gender': user.gender,
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"注册失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': f'注册失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def user_login(request):
    """用户登录"""
    try:
        data = json.loads(request.body)
        if not isinstance(data, dict):
            return JsonResponse({'success': False, 'error': '无效的请求格式，需要一个JSON对象。'}, status=400)
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return JsonResponse({
                'success': False,
                'error': '用户名和密码不能为空'
            }, status=400)
        
        # 认证用户
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            return JsonResponse({
                'success': True,
                'message': '登录成功',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'user_type': user.user_type,
                    'employee_id': user.employee_id,
                    'age': user.age,
                    'gender': user.gender,
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'error': '用户名或密码错误'
            }, status=401)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"登录失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'登录失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def user_logout(request):
    """用户登出（CSRF豁免，便于前后端分离场景）"""
    try:
        logout(request)
        # 同时清理会话ID Cookie（可选，Django logout 已处理）
        resp = JsonResponse({'success': True, 'message': '登出成功'})
        resp.delete_cookie(settings.SESSION_COOKIE_NAME)
        return resp
    except Exception as e:
        logger.error(f"登出失败: {e}")
        return JsonResponse({'success': False, 'error': '登出失败'}, status=500)


@csrf_exempt
@login_required
@require_http_methods(["POST", "PATCH"])
def update_user_profile(request):
    """更新当前登录用户的个人信息"""
    try:
        user = request.user
        data = json.loads(request.body)

        # 允许更新的字段
        if 'email' in data:
            new_email = data['email'].strip()
            if new_email and new_email != user.email:
                # 检查新邮箱是否已被其他用户注册
                if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
                    return JsonResponse({
                        'success': False,
                        'error': '该邮箱已被其他用户注册'
                    }, status=400)
                user.email = new_email

        if 'age' in data:
            user.age = data['age']

        if 'gender' in data:
            gender = data['gender'].strip()
            if gender in ['M', 'F', 'O']:
                user.gender = gender

        # 保存更改
        user.save()

        return JsonResponse({
            'success': True,
            'message': '用户信息更新成功',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'user_type': user.user_type,
                'employee_id': user.employee_id,
                'age': user.age,
                'gender': user.gender,
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'更新失败: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_current_user(request):
    """获取当前登录用户信息"""
    if request.user.is_authenticated:
        return JsonResponse({
            'success': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'user_type': request.user.user_type,
                'employee_id': request.user.employee_id,
                'age': request.user.age,
                'gender': request.user.gender,
            }
        })
    else:
        return JsonResponse({
            'success': False,
            'error': '未登录'
        }, status=401)

