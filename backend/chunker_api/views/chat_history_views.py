import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import logging
from ..models import KnowledgeBase, ChatSession

# 导入分块器和编码器
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

logger = logging.getLogger(__name__)


# ==================== 聊天记录相关API ====================

@csrf_exempt
@require_http_methods(["POST"])
def create_chat_session(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': '请先登录'}, status=401)
    try:
        data = json.loads(request.body)
        title = (data.get('title') or '').strip()
        knowledge_base_id = data.get('knowledge_base_id')
        kb = None
        if knowledge_base_id:
            try:
                kb = KnowledgeBase.objects.get(id=knowledge_base_id)
            except KnowledgeBase.DoesNotExist:
                return JsonResponse({'success': False, 'error': '知识库不存在或无权限访问'}, status=404)
        if not title:
            title = '新对话'
        session = ChatSession.objects.create(user=request.user, title=title, knowledge_base=kb)
        return JsonResponse({'success': True, 'session': {
            'id': str(session.id),
            'title': session.title,
            'knowledge_base_id': str(kb.id) if kb else None,
            'created_at': session.created_at.isoformat(),
            'updated_at': session.updated_at.isoformat(),
        }})
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        return JsonResponse({'success': False, 'error': f'创建会话失败: {e}'}, status=500)


@require_http_methods(["GET"])
def list_chat_sessions(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': '请先登录'}, status=401)
    sessions = ChatSession.objects.filter(user=request.user).order_by('-updated_at')
    data = [{
        'id': str(s.id),
        'title': s.title,
        'knowledge_base_id': str(s.knowledge_base.id) if s.knowledge_base else None,
        'created_at': s.created_at.isoformat(),
        'updated_at': s.updated_at.isoformat(),
    } for s in sessions]
    return JsonResponse({'success': True, 'sessions': data, 'total': len(data)})


@require_http_methods(["GET"])
def list_chat_messages(request, session_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': '请先登录'}, status=401)
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': '会话不存在或无权限访问'}, status=404)
    messages = session.messages.all().order_by('created_at')
    data = [{
        'id': m.id,
        'role': m.role,
        'content': m.content,
        'sources': m.sources,
        'images': m.images,
        'refusal': m.refusal,
        'suggested_next_questions': m.suggested_next_questions,
        'created_at': m.created_at.isoformat(),
    } for m in messages]
    return JsonResponse({'success': True, 'messages': data})


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_chat_session(request, session_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': '请先登录'}, status=401)
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
        session.delete()
        return JsonResponse({'success': True, 'message': '会话已删除'})
    except ChatSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': '会话不存在或无权限访问'}, status=404)
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        return JsonResponse({'success': False, 'error': f'删除会话失败: {e}'}, status=500)

@csrf_exempt
@require_http_methods(["POST", "PATCH"])
def rename_chat_session(request, session_id):
    """重命名聊天会话"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': '请先登录'}, status=401)
    try:
        session = ChatSession.objects.get(id=session_id, user=request.user)
    except ChatSession.DoesNotExist:
        return JsonResponse({'success': False, 'error': '会话不存在或无权限访问'}, status=404)
    try:
        data = json.loads(request.body or '{}')
        title = (data.get('title') or '').strip()
        if not title:
            return JsonResponse({'success': False, 'error': '标题不能为空'}, status=400)
        # 简单清洗并限制长度
        title = title.replace('\n', ' ').replace('\r', ' ').strip()[:50]
        session.title = title
        session.save(update_fields=['title', 'updated_at'])
        return JsonResponse({'success': True, 'session': {
            'id': str(session.id),
            'title': session.title,
            'knowledge_base_id': str(session.knowledge_base.id) if session.knowledge_base else None,
            'created_at': session.created_at.isoformat(),
            'updated_at': session.updated_at.isoformat(),
        }})
    except Exception as e:
        logger.error(f"重命名会话失败: {e}")
        return JsonResponse({'success': False, 'error': f'重命名失败: {e}'}, status=500)
