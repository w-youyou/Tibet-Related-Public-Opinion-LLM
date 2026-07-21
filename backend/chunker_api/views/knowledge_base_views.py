import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import logging
from ..models import KnowledgeBase

# 导入分块器和编码器
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

logger = logging.getLogger(__name__)

# ==================== 知识库管理相关API ====================

@csrf_exempt
@require_http_methods(["POST"])
def create_knowledge_base(request):
    """创建知识库"""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': '请先登录'
        }, status=401)
    
    try:
        data = json.loads(request.body)
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        
        if not name:
            return JsonResponse({
                'success': False,
                'error': '知识库名称不能为空'
            }, status=400)
        
        # 创建知识库
        kb = KnowledgeBase.objects.create(
            user=request.user,
            name=name,
            description=description if description else None
        )
        
        return JsonResponse({
            'success': True,
            'message': '知识库创建成功',
            'knowledge_base': {
                'id': str(kb.id),
                'name': kb.name,
                'description': kb.description,
                'collection_name': kb.collection_name,
                'created_at': kb.created_at.isoformat(),
            }
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"创建知识库失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'创建知识库失败: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def list_knowledge_bases(request):
    """获取用户的知识库列表"""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': '请先登录'
        }, status=401)
    
    try:
        # 参考 cgrag_api -v3，返回所有激活状态的知识库供用户选择
        knowledge_bases = KnowledgeBase.objects.filter(status='active')
        
        kb_list = [{
            'id': str(kb.id),
            'name': kb.name,
            'description': kb.description,
            'collection_name': kb.collection_name,
            'created_at': kb.created_at.isoformat(),
            'updated_at': kb.updated_at.isoformat(),
        } for kb in knowledge_bases]
        
        return JsonResponse({
            'success': True,
            'knowledge_bases': kb_list,
            'total': len(kb_list)
        })
    
    except Exception as e:
        logger.error(f"获取知识库列表失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'获取知识库列表失败: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_knowledge_base(request, kb_id):
    """获取知识库详情"""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': '请先登录'
        }, status=401)
    
    try:
        kb = KnowledgeBase.objects.get(id=kb_id, user=request.user)
        
        return JsonResponse({
            'success': True,
            'knowledge_base': {
                'id': str(kb.id),
                'name': kb.name,
                'description': kb.description,
                'collection_name': kb.collection_name,
                'created_at': kb.created_at.isoformat(),
                'updated_at': kb.updated_at.isoformat(),
            }
        })
    
    except KnowledgeBase.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '知识库不存在或无权限访问'
        }, status=404)
    except Exception as e:
        logger.error(f"获取知识库详情失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'获取知识库详情失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_knowledge_base(request, kb_id):
    """删除知识库"""
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': '请先登录'
        }, status=401)
    
    try:
        kb = KnowledgeBase.objects.get(id=kb_id, user=request.user)
        collection_name = kb.collection_name
        kb.delete()
        
        # TODO: 可选 - 删除Chroma中的集合数据
        # 这里可以添加删除Chroma集合的逻辑
        
        return JsonResponse({
            'success': True,
            'message': '知识库删除成功',
            'deleted_collection': collection_name
        })
    
    except KnowledgeBase.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': '知识库不存在或无权限访问'
        }, status=404)
    except Exception as e:
        logger.error(f"删除知识库失败: {e}")
        return JsonResponse({
            'success': False,
            'error': f'删除知识库失败: {str(e)}'
        }, status=500)
