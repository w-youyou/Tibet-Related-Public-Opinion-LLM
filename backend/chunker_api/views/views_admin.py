import os
import json
import uuid
import datetime
import logging
import shutil
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Sum, Count

from chunker_api.models import User, AdminUser, KnowledgeBase, Document, DocumentVersion, OperationLog
from utils.auth import generate_admin_tokens, verify_admin_token, admin_jwt_required
from chunker_api.chroma_sync import delete_document_chunks, index_document_version, get_chroma_store, set_document_chunks_active_status, set_version_active_status

logger = logging.getLogger(__name__)

def log_activity(admin_user, action, details):
    """记录管理员操作审计日志"""
    OperationLog.objects.create(
        admin_user=admin_user,
        action=action,
        details=details
    )

# ==================== 1. 管理员认证相关 API ====================

@csrf_exempt
@require_http_methods(["POST"])
def admin_login(request):
    """管理员登录"""
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return JsonResponse({'success': False, 'error': '用户名和密码不能为空'}, status=400)
            
        try:
            admin_user = AdminUser.objects.get(username=username, is_active=True)
        except AdminUser.DoesNotExist:
            return JsonResponse({'success': False, 'error': '用户名或密码错误'}, status=401)
            
        if not check_password(password, admin_user.password):
            return JsonResponse({'success': False, 'error': '用户名或密码错误'}, status=401)
            
        # 签发 JWT 双 Token
        tokens = generate_admin_tokens(admin_user)
        
        # 记录登录日志
        log_activity(admin_user, "LOGIN", f"管理员 {username} 成功登录管理后台")
        
        return JsonResponse({'success': True, 'data': tokens})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON数据'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def admin_token_refresh(request):
    """刷新管理员 Access Token"""
    try:
        data = json.loads(request.body)
        refresh_token = data.get('refresh_token', '').strip()
        
        if not refresh_token:
            return JsonResponse({'success': False, 'error': '未提供 Refresh Token'}, status=400)
            
        payload = verify_admin_token(refresh_token, 'refresh')
        if not payload:
            return JsonResponse({'success': False, 'error': 'Refresh Token 无效或已过期，请重新登录'}, status=401)
            
        try:
            admin_user = AdminUser.objects.get(id=payload['admin_id'], is_active=True)
        except AdminUser.DoesNotExist:
            return JsonResponse({'success': False, 'error': '管理员账号不存在或已被禁用'}, status=401)
            
        tokens = generate_admin_tokens(admin_user)
        return JsonResponse({'success': True, 'data': tokens})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON数据'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'服务器内部错误: {str(e)}'}, status=500)

@csrf_exempt
@admin_jwt_required()
@require_http_methods(["POST"])
def admin_logout(request):
    """管理员登出"""
    log_activity(request.admin_user, "LOGOUT", f"管理员 {request.admin_user.username} 成功注销退出")
    return JsonResponse({'success': True, 'message': '注销成功'})

# ==================== 2. 看板与大屏 API ====================

@admin_jwt_required()
@require_http_methods(["GET"])
def dashboard_stats(request):
    """获取 Dashboard 统计指标数据"""
    try:
        kb_count = KnowledgeBase.objects.count()
        doc_count = Document.objects.exclude(status='deleted').count()
        
        # 计算激活状态下的分块与向量总数 (仅统计当前主版本的 active 文档)
        stats = DocumentVersion.objects.filter(
            status='current',
            document__status='active'
        ).aggregate(
            total_chunks=Sum('chunk_count'),
            total_embeddings=Sum('embedding_count')
        )
        
        chunk_total = stats['total_chunks'] or 0
        embedding_total = stats['total_embeddings'] or 0
        
        # 最近上传文件 (最近5个版本物理文件)
        recent_versions = DocumentVersion.objects.select_related('document', 'document__knowledge_base').order_by('-uploaded_at')[:5]
        recent_files = [{
            'id': str(rv.id),
            'document_id': str(rv.document.id),
            'name': rv.document.name,
            'kb_name': rv.document.knowledge_base.name,
            'version': f"v{rv.version_number}",
            'uploaded_at': rv.uploaded_at.isoformat(),
            'size': rv.file_size,
            'status': rv.document.status
        } for rv in recent_versions]
        
        # 最近操作日志
        recent_logs = OperationLog.objects.select_related('admin_user').order_by('-created_at')[:10]
        op_logs = [{
            'id': log.id,
            'admin_username': log.admin_user.username if log.admin_user else '系统',
            'action': log.action,
            'details': log.details,
            'created_at': log.created_at.isoformat()
        } for log in recent_logs]
        
        return JsonResponse({
            'success': True,
            'data': {
                'kb_total': kb_count,
                'doc_total': doc_count,
                'chunk_total': chunk_total,
                'embedding_total': embedding_total,
                'recent_files': recent_files,
                'operation_logs': op_logs
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'获取看板统计失败: {str(e)}'}, status=500)

# ==================== 3. 知识库管理 API ====================

@csrf_exempt
@admin_jwt_required()
@require_http_methods(["GET", "POST"])
def admin_kb_list_create(request):
    """获取知识库列表 / 新增知识库"""
    if request.method == "GET":
        try:
            # 聚合查询每个知识库的文档数、Chunks数
            kbs = KnowledgeBase.objects.annotate(
                doc_count=Count('documents', distinct=True)
            ).order_by('-created_at')
            
            kb_list = []
            for kb in kbs:
                # 统计该知识库内所有 active 文档当前主版本的 chunks 数之和
                chunk_sum = DocumentVersion.objects.filter(
                    document__knowledge_base=kb,
                    document__status='active',
                    status='current'
                ).aggregate(total=Sum('chunk_count'))['total'] or 0
                
                kb_list.append({
                    'id': str(kb.id),
                    'name': kb.name,
                    'description': kb.description,
                    'collection_name': kb.collection_name,
                    'doc_count': kb.doc_count,
                    'chunk_count': chunk_sum,
                    'status': getattr(kb, 'status', 'active'),
                    'created_at': kb.created_at.isoformat(),
                })
                
            return JsonResponse({'success': True, 'data': kb_list})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'获取知识库列表失败: {str(e)}'}, status=500)
            
    elif request.method == "POST":
        # 权限校验：仅超级管理员可创建知识库
        if request.admin_user.role != 'SUPER_ADMIN':
            return JsonResponse({'success': False, 'error': '只有超级管理员有权创建新的知识库'}, status=403)
            
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            description = data.get('description', '').strip()
            
            if not name:
                return JsonResponse({'success': False, 'error': '知识库名称不能为空'}, status=400)
                
            # 获取或创建一个默认前台普通用户关联（因为现有模型外键绑定到普通 User）
            default_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
            if not default_user:
                # 兜底：如果系统没任何用户，自动新建一个初始化用户
                import secrets
                default_user = User.objects.create_user(username="kb_owner", password=secrets.token_urlsafe(16), email="owner@company.com")
                
            kb = KnowledgeBase.objects.create(
                user=default_user,
                name=name,
                description=description
            )
            
            # 预热初始化 ChromaDB 集合
            get_chroma_store(kb.collection_name)
            
            log_activity(request.admin_user, "CREATE_KB", f"创建了知识库 '{name}'，关联集合: {kb.collection_name}")
            
            return JsonResponse({
                'success': True,
                'data': {
                    'id': str(kb.id),
                    'name': kb.name,
                    'description': kb.description,
                    'collection_name': kb.collection_name,
                    'created_at': kb.created_at.isoformat()
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': '无效的JSON数据'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'创建知识库失败: {str(e)}'}, status=500)

@csrf_exempt
@admin_jwt_required()
@require_http_methods(["PATCH", "DELETE"])
def admin_kb_detail(request, kb_id):
    """修改知识库 / 删除知识库"""
    try:
        kb = KnowledgeBase.objects.get(id=kb_id)
    except KnowledgeBase.DoesNotExist:
        return JsonResponse({'success': False, 'error': '目标知识库不存在'}, status=404)
        
    if request.method == "PATCH":
        try:
            data = json.loads(request.body)
            name = data.get('name', '')
            if type(name) is str:
                name = name.strip()
            description = data.get('description')
            if type(description) is str:
                description = description.strip()
            status = data.get('status')
            
            if name:
                kb.name = name
            if description is not None:
                kb.description = description
            if status in ['active', 'inactive']:
                kb.status = status
                
            kb.save()
            
            if status == 'inactive':
                log_activity(request.admin_user, "DISABLE_KB", f"禁用了知识库 '{kb.name}'")
            elif status == 'active':
                log_activity(request.admin_user, "ENABLE_KB", f"启用了知识库 '{kb.name}'")
            else:
                log_activity(request.admin_user, "UPDATE_KB", f"更新了知识库 '{kb.name}' 的配置信息")
            
            return JsonResponse({
                'success': True,
                'data': {
                    'id': str(kb.id),
                    'name': kb.name,
                    'description': kb.description,
                    'status': getattr(kb, 'status', 'active')
                }
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': '无效的JSON数据'}, status=400)
            
    elif request.method == "DELETE":
        # 权限校验：仅超级管理员可删除知识库
        if request.admin_user.role != 'SUPER_ADMIN':
            return JsonResponse({'success': False, 'error': '只有超级管理员有权删除知识库'}, status=403)
            
        try:
            kb_name = kb.name
            collection_name = kb.collection_name
            
            # 1. 物理删除 ChromaDB 里的集合
            try:
                store = get_chroma_store(collection_name)
                store._collection.delete()
                # 删除物理 Chroma 文件夹及 BM25 索引文件夹
                shutil_chroma = os.path.join(getattr(settings, 'CHROMA_DB_PATH', './chroma_db'), collection_name)
                if os.path.exists(shutil_chroma):
                    shutil.rmtree(shutil_chroma)
                shutil_bm25 = os.path.join(getattr(settings, 'CHROMA_DB_PATH', './chroma_db'), 'bm25', collection_name)
                if os.path.exists(shutil_bm25):
                    shutil.rmtree(shutil_bm25)
            except Exception as e:
                logger.error(f"清理知识库底层 Chroma/BM25 数据发生异常: {e}")
                
            # 2. 级联删除 SQL 数据库实体
            kb.delete()
            log_activity(request.admin_user, "DELETE_KB", f"删除了知识库 '{kb_name}'，同步清理了底层向量数据与文件记录")
            
            return JsonResponse({'success': True, 'message': f"知识库 '{kb_name}' 已成功安全注销删除"})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'删除知识库失败: {str(e)}'}, status=500)

# ==================== 4. 文档生命周期管理 API ====================

@admin_jwt_required()
@require_http_methods(["GET"])
def admin_document_list(request):
    """获取文档列表 (支持模糊搜索、状态过滤、知识库过滤)"""
    try:
        kb_id = request.GET.get('knowledge_base_id')
        status = request.GET.get('status')
        search_query = request.GET.get('search')
        
        query = Document.objects.exclude(status='deleted').select_related('knowledge_base')
        
        if kb_id:
            query = query.filter(knowledge_base_id=kb_id)
        if status:
            query = query.filter(status=status)
        if search_query:
            query = query.filter(name__icontains=search_query)
            
        doc_list = []
        for doc in query:
            # 获取当前主版本
            current_ver = doc.versions.filter(status='current').first()
            doc_list.append({
                'id': str(doc.id),
                'name': doc.name,
                'kb_id': str(doc.knowledge_base.id),
                'kb_name': doc.knowledge_base.name,
                'status': doc.status,
                'created_at': doc.created_at.isoformat(),
                'version': f"v{current_ver.version_number}" if current_ver else '无版本',
                'size': current_ver.file_size if current_ver else 0,
                'chunk_count': current_ver.chunk_count if current_ver else 0,
                'embedding_count': current_ver.embedding_count if current_ver else 0,
                'chunker_type': current_ver.chunker_type if current_ver else 'semantic'
            })
            
        return JsonResponse({'success': True, 'data': doc_list})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'获取文档列表失败: {str(e)}'}, status=500)

@csrf_exempt
@admin_jwt_required()
@require_http_methods(["POST"])
def admin_document_upload(request):
    """上传全新文档 (保存文件 -> 注册记录 -> 触发切片与向量化)"""
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'error': '未包含上传文件'}, status=400)
            
        file = request.FILES['file']
        kb_id = request.POST.get('knowledge_base_id')
        chunker_type = request.POST.get('chunker_type', 'semantic')
        
        if not kb_id:
            return JsonResponse({'success': False, 'error': '请指定目标知识库'}, status=400)
            
        try:
            kb = KnowledgeBase.objects.get(id=kb_id)
        except KnowledgeBase.DoesNotExist:
            return JsonResponse({'success': False, 'error': '选定的知识库不存在'}, status=400)
            
        # 检查逻辑文档是否已重名存在
        existing_doc = Document.objects.filter(knowledge_base=kb, name=file.name).first()
        if existing_doc:
            if existing_doc.status == 'deleted':
                # 如果是已删除状态，代表软删除，我们可以直接恢复它
                existing_doc.status = 'active'
                existing_doc.save()
                doc = existing_doc
            else:
                return JsonResponse({'success': False, 'error': f'文件名 {file.name} 已存在。如需更新内容，请在详情页上传新版本。'}, status=400)
        else:
            # 新建逻辑文档
            doc = Document.objects.create(
                knowledge_base=kb,
                name=file.name,
                status='active'
            )
            
        # 保存物理文件到 media/admin_docs 目录下
        media_dir = os.path.join(settings.MEDIA_ROOT, 'admin_docs')
        os.makedirs(media_dir, exist_ok=True)
        file_ext = os.path.splitext(file.name)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}{file_ext}"
        file_path = os.path.join(media_dir, unique_filename)
        
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
                
        # 注册 Version 1 为当前激活主版本
        version = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            file_path=file_path,
            file_size=file.size,
            chunker_type=chunker_type,
            status='current',
            uploaded_by_admin=request.admin_user
        )
        
        # 触发底层同步切片与向量化导入
        try:
            index_document_version(kb.collection_name, version, request=request)
        except Exception as embed_error:
            # 底层向量化发生报错，软清理逻辑记录并提示
            version.delete()
            if not doc.versions.exists():
                doc.delete()
            if os.path.exists(file_path):
                os.unlink(file_path)
            return JsonResponse({'success': False, 'error': f'解析与嵌入向量库失败: {str(embed_error)}'}, status=500)
            
        log_activity(request.admin_user, "UPLOAD_DOC", f"向知识库 '{kb.name}' 上传并激活了全新文档 '{file.name}' v1")
        
        return JsonResponse({
            'success': True,
            'message': '文档上传并向量化索引成功',
            'data': {
                'document_id': str(doc.id),
                'name': doc.name,
                'version_number': 1,
                'chunk_count': version.chunk_count,
                'embedding_count': version.embedding_count
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'文档上传处理失败: {str(e)}'}, status=500)

@csrf_exempt
@admin_jwt_required()
@require_http_methods(["PATCH"])
def admin_document_status(request, doc_id):
    """修改文档状态 (启用、禁用、彻底删除)"""
    try:
        doc = Document.objects.get(id=doc_id)
    except Document.DoesNotExist:
        return JsonResponse({'success': False, 'error': '目标逻辑文档不存在'}, status=404)
        
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status not in ['active', 'inactive', 'deleted']:
            return JsonResponse({'success': False, 'error': '无效的状态值'}, status=400)
            
        collection_name = doc.knowledge_base.collection_name
        
        if new_status == 'inactive':
            doc.status = 'inactive'
            doc.save()
            logger.info(f"Updated document {doc.id} status to inactive in database.")
            # 动态隐藏 ChromaDB 中的 Chunks 索引
            set_document_chunks_active_status(collection_name, doc.name, False)
            log_activity(request.admin_user, "DISABLE_DOC", f"禁用了文档 '{doc.name}'，已下架其在向量库中的所有分块")
            
        elif new_status == 'active':
            doc.status = 'active'
            doc.save()
            logger.info(f"Updated document {doc.id} status to active in database.")
            # 仅恢复状态，不重新向量化
            set_document_chunks_active_status(collection_name, doc.name, True)
            log_activity(request.admin_user, "ENABLE_DOC", f"恢复启用了文档 '{doc.name}'，重新将其主版本向量化入库")
            
        elif new_status == 'deleted':
            doc.status = 'deleted'
            doc.save()
            logger.info(f"Updated document {doc.id} status to deleted in database.")
            # 从 ChromaDB 逻辑删除（下架隐藏），而不是彻底物理擦除
            set_document_chunks_active_status(collection_name, doc.name, False)
            log_activity(request.admin_user, "DELETE_DOC", f"软删除了文档 '{doc.name}'，从底层隐藏了其向量分块")
            
        return JsonResponse({
            'success': True,
            'message': f"文档已成功切换为 '{doc.get_status_display()}'",
            'data': {'id': str(doc.id), 'status': doc.status}
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON数据'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'修改文档状态失败: {str(e)}'}, status=500)

@admin_jwt_required()
@require_http_methods(["GET"])
def admin_document_detail(request, doc_id):
    """获取文档详情 (含 Chunks 预览与版本线)"""
    try:
        doc = Document.objects.select_related('knowledge_base').get(id=doc_id)
    except Document.DoesNotExist:
        return JsonResponse({'success': False, 'error': '目标文档不存在'}, status=404)
        
    try:
        # 1. 组装基本信息
        current_ver = doc.versions.filter(status='current').first()
        basic_info = {
            'id': str(doc.id),
            'name': doc.name,
            'status': doc.status,
            'kb_id': str(doc.knowledge_base.id),
            'kb_name': doc.knowledge_base.name,
            'created_at': doc.created_at.isoformat(),
            'current_version': current_ver.version_number if current_ver else None,
            'chunker_type': current_ver.chunker_type if current_ver else 'semantic',
            'file_size': current_ver.file_size if current_ver else 0,
            'chunk_count': current_ver.chunk_count if current_ver else 0,
            'embedding_count': current_ver.embedding_count if current_ver else 0,
        }
        
        # 2. 从 ChromaDB 拉取切片分块
        chunks_preview = []
        if doc.status == 'active':
            try:
                # 构建版本映射 ID -> version_number
                version_map = {str(v.id): v.version_number for v in doc.versions.all()}
                current_ver_id = str(current_ver.id) if current_ver else None

                store = get_chroma_store(doc.knowledge_base.collection_name)
                show_all = request.GET.get('show_all_chunks') == 'true'
                all_docs = store._collection.get(include=["documents", "metadatas"])
                count = 0
                for true_id, doc_text, meta in zip(all_docs.get("ids", []) or [], all_docs.get("documents", []) or [], all_docs.get("metadatas", []) or []):
                    if meta:
                        meta_file = meta.get("file_name") or meta.get("source") or meta.get("source_file")
                        if meta_file == doc.name:
                            vid = meta.get('version_id')
                            # 判断是否属于当前激活的最新版本
                            # 如果既没有 version_id 也没有 current_ver_id，则也当作当前版本（兼容旧数据）
                            if vid and current_ver_id:
                                is_current_version = (vid == current_ver_id)
                            else:
                                is_current_version = (meta.get('is_active') is True)
                                
                            if show_all or is_current_version:
                                ver_number_str = f"v{version_map[vid]}" if vid in version_map else "未知"
                                chunks_preview.append({
                                    'chunk_id': true_id,  # 使用真实的 ChromaDB 主键，确保热修复能定位到记录
                                    'content': doc_text[:300] + ('...' if len(doc_text) > 300 else ''),
                                    'length': len(doc_text),
                                    'is_active': is_current_version,
                                    'version_number': ver_number_str
                                })
                                count += 1
                            if count >= 100: # 限制看板返回量防止数据包过载
                                break
            except Exception as e:
                logger.warning(f"获取文档底层切块预览失败: {e}")
                
        # 3. 组装版本历史时间轴数据
        versions = doc.versions.all().order_by('-version_number')
        version_list = [{
            'id': str(v.id),
            'version_number': v.version_number,
            'file_size': v.file_size,
            'chunk_count': v.chunk_count,
            'embedding_count': v.embedding_count,
            'chunker_type': v.chunker_type,
            'status': v.status,
            'uploaded_at': v.uploaded_at.isoformat(),
            'uploaded_by': v.uploaded_by_admin.username if v.uploaded_by_admin else (v.uploaded_by_user.username if v.uploaded_by_user else '系统'),
            'remark': v.remark
        } for v in versions]
        # 4. 获取与该文档相关的操作日志
        from chunker_api.models import OperationLog
        logs = OperationLog.objects.filter(details__icontains=str(doc.id)).select_related('admin_user').order_by('-created_at')[:50]
        log_list = [{
            'id': l.id,
            'operator': l.admin_user.username if l.admin_user else '系统',
            'action': l.action,
            'details': l.details,
            'created_at': l.created_at.isoformat()
        } for l in logs]
        
        return JsonResponse({
            'success': True,
            'data': {
                'basic': basic_info,
                'chunks': chunks_preview,
                'versions': version_list,
                'logs': log_list
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'获取文档详情失败: {str(e)}'}, status=500)

@csrf_exempt
@admin_jwt_required()
@require_http_methods(["POST"])
def admin_document_update_chunk(request, doc_id):
    """管理员主动热修复文档切块"""
    try:
        data = json.loads(request.body)
        chunk_id = data.get('chunk_id')
        new_content = data.get('new_content')
        remark = data.get('remark', '')
        
        if not chunk_id or not new_content:
            return JsonResponse({'success': False, 'error': '参数不完整'}, status=400)
            
        chunk_id = str(chunk_id)
        doc = Document.objects.select_related('knowledge_base').get(id=doc_id)
        collection_name = doc.knowledge_base.collection_name
        
        from django.conf import settings
        from utils.chunk.LocalEmbeddingEncoder import LocalEmbeddingEncoder
        local_model_path = getattr(settings, 'LOCAL_EMBEDDING_MODEL', 'G:\\models\\bge-large-zh')
        encoder = LocalEmbeddingEncoder(model_path=local_model_path)
        new_emb = encoder.encode([new_content])[0]['embedding']
        
        from chunker_api.chroma_sync import get_chroma_store, clear_bm25_cache
        store = get_chroma_store(collection_name)
        existing = store._collection.get(ids=[chunk_id], include=["metadatas"])
        metadatas = existing.get("metadatas")
        if metadatas and len(metadatas) > 0:
            meta = metadatas[0]
            if 'text' in meta:
                meta['text'] = new_content
            store._collection.update(ids=[chunk_id], embeddings=[new_emb], documents=[new_content], metadatas=[meta])
        else:
            store._collection.update(ids=[chunk_id], embeddings=[new_emb], documents=[new_content])
            
        clear_bm25_cache(collection_name)
        
        OperationLog.objects.create(
            admin_user=request.admin_user,
            action='EDIT_CHUNK',
            details=f"在文档管理中热修复了分块内容 (文档ID: {doc_id} | Chunk ID: {chunk_id})" + (f" - 备注: {remark}" if remark else "")
        )
        
        return JsonResponse({'success': True})
    except Document.DoesNotExist:
        return JsonResponse({'success': False, 'error': '文档不存在'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ==================== 5. 文档版本管理 API ====================

@csrf_exempt
@admin_jwt_required()
@require_http_methods(["POST"])
def admin_version_upload(request):
    """为指定文档上传更新版本 (物理版本自增 -> 置为 current -> 重写向量库)"""
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'error': '未包含更新文件'}, status=400)
            
        file = request.FILES['file']
        doc_id = request.POST.get('document_id')
        chunker_type = request.POST.get('chunker_type')
        remark = request.POST.get('remark', '')
        
        if not doc_id:
            return JsonResponse({'success': False, 'error': '请指定目标逻辑文档'}, status=400)
            
        try:
            doc = Document.objects.select_related('knowledge_base').get(id=doc_id)
        except Document.DoesNotExist:
            return JsonResponse({'success': False, 'error': '关联的逻辑文档不存在'}, status=404)
            
        # 检查上传的新版本文件名是否与原逻辑文档一致 (允许后缀不同，但推荐主干一致)
        # 这里为了保持 Chroma 清洗的一致性，使用原有逻辑文档的 name 作为元数据，物理文件名可使用新物理路径
        
        # 算定新的版本号
        latest_ver = doc.versions.order_by('-version_number').first()
        new_version_number = (latest_ver.version_number + 1) if latest_ver else 1
        
        # 保存物理文件
        media_dir = os.path.join(settings.MEDIA_ROOT, 'admin_docs')
        os.makedirs(media_dir, exist_ok=True)
        file_ext = os.path.splitext(file.name)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}_v{new_version_number}{file_ext}"
        file_path = os.path.join(media_dir, unique_filename)
        
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
                
        # 创建新版本记录并置为 current，原 current 全部失效置为 historical
        doc.versions.update(status='historical')
        
        version = DocumentVersion.objects.create(
            document=doc,
            version_number=new_version_number,
            file_path=file_path,
            file_size=file.size,
            chunker_type=chunker_type or (latest_ver.chunker_type if latest_ver else 'semantic'),
            status='current',
            uploaded_by_admin=request.admin_user,
            remark=remark
        )
        
        # 如果当前文档没被禁用，同步清空 Chroma 中旧 Chunks 并编码导入新 Chunks
        chunks_data = []
        if doc.status == 'active':
            try:
                chunks_data = index_document_version(doc.knowledge_base.collection_name, version, request=request)
                # 重要：新版本向量入库后，默认都为 True，需调用此接口将所有旧版本设为 False，保证检索干净
                set_version_active_status(doc.knowledge_base.collection_name, doc.name, version.id)
            except Exception as e:
                # 容错：导入失败则进行回滚
                version.delete()
                if latest_ver:
                    latest_ver.status = 'current'
                    latest_ver.save()
                if os.path.exists(file_path):
                    os.unlink(file_path)
                return JsonResponse({'success': False, 'error': f'新版本向量化入库失败，已自动回滚到上一个正常版本: {str(e)}'}, status=500)
                
        log_activity(request.admin_user, "UPLOAD_VERSION", f"为文档 '{doc.name}' 升级并激活了新版本 v{new_version_number}")
        
        return JsonResponse({
            'success': True,
            'message': f"文档版本成功升级至 v{new_version_number}",
            'data': {
                'id': str(version.id),
                'version_number': new_version_number,
                'chunk_count': version.chunk_count,
                'embedding_count': version.embedding_count,
                'chunks': chunks_data,
                'chunker_type': version.chunker_type
            }
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'上传新版本发生错误: {str(e)}'}, status=500)

@csrf_exempt
@admin_jwt_required()
@require_http_methods(["POST"])
def admin_version_switch(request):
    """切换或回退文档主版本 (SQL修改状态 -> 清洗Chroma旧数据 -> 加载新版本Chroma数据)"""
    try:
        data = json.loads(request.body)
        version_id = data.get('version_id')
        remark = data.get('remark', '')
        
        if not version_id:
            return JsonResponse({'success': False, 'error': '未提供版本ID'}, status=400)
            
        try:
            target_version = DocumentVersion.objects.select_related('document', 'document__knowledge_base').get(id=version_id)
        except DocumentVersion.DoesNotExist:
            return JsonResponse({'success': False, 'error': '指定的文档版本记录不存在'}, status=404)
            
        doc = target_version.document
        collection_name = doc.knowledge_base.collection_name
        
        if target_version.status == 'current':
            return JsonResponse({'success': True, 'message': '目标版本已经是当前主版本，无需切换'})
            
        # 1. SQL 状态更新：旧 current 全体退居 historical，新目标升格 current
        doc.versions.filter(status='current').update(status='historical')
        target_version.status = 'current'
        if remark:
            target_version.remark = remark
        target_version.save(update_fields=['status', 'remark'])
        
        # 2. 如果文档逻辑状态是“已启用”，则动态更新底层向量库索引
        if doc.status == 'active':
            try:
                # 瞬间状态切换，不再删除重做！(O(1) 复杂度)
                set_version_active_status(collection_name, doc.name, target_version.id)
            except Exception as e:
                return JsonResponse({'success': False, 'error': f'切换成功，但向量索引更新失败，请在列表尝试手动点击禁用再启用重试: {str(e)}'}, status=500)
                
        log_activity(request.admin_user, "ROLLBACK_VER", f"将文档 '{doc.name}' 的当前运行版本回滚/切换为了历史版本 v{target_version.version_number}")
        
        return JsonResponse({
            'success': True,
            'message': f"已成功将运行版本切换至 v{target_version.version_number}",
            'data': {
                'document_id': str(doc.id),
                'active_version': target_version.version_number,
                'chunk_count': target_version.chunk_count
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON数据'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'版本切换处理失败: {str(e)}'}, status=500)

# ==================== 6. 系统日志与操作审计 API ====================

@admin_jwt_required()
@require_http_methods(["GET"])
def admin_operation_logs(request):
    """查看管理员操作审计日志"""
    try:
        action_filter = request.GET.get('action')
        admin_filter = request.GET.get('username')
        
        query = OperationLog.objects.select_related('admin_user')
        if action_filter:
            query = query.filter(action=action_filter)
        if admin_filter:
            query = query.filter(admin_user__username=admin_filter)
            
        logs = query.order_by('-created_at')[:100] # 最多回显 100 条
        
        data = [{
            'id': log.id,
            'admin_username': log.admin_user.username if log.admin_user else '系统',
            'action': log.action,
            'details': log.details,
            'created_at': log.created_at.isoformat()
        } for log in logs]
        
        return JsonResponse({'success': True, 'data': data})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'获取审计日志失败: {str(e)}'}, status=500)

# ==================== 6. 管理员账号管理 API ====================
from django.contrib.auth.hashers import make_password, check_password

@csrf_exempt
@admin_jwt_required()
@require_http_methods(["POST"])
def admin_add_account(request):
    """添加新管理员账号 (仅SUPER_ADMIN可用)"""
    if request.admin_user.role != 'SUPER_ADMIN':
        return JsonResponse({'success': False, 'error': '权限不足，只有超级管理员可添加新账号'}, status=403)
        
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '')
        email = data.get('email', '').strip()
        role = data.get('role', 'KB_ADMIN').strip()
        
        if not username or not password or not email:
            return JsonResponse({'success': False, 'error': '用户名、密码和邮箱均不能为空'}, status=400)
            
        if AdminUser.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'error': '该用户名已存在'}, status=400)
            
        if AdminUser.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'error': '该邮箱已被注册'}, status=400)
            
        new_admin = AdminUser.objects.create(
            username=username,
            password=make_password(password),
            email=email,
            role=role,
            is_active=True
        )
        
        log_activity(request.admin_user, 'CREATE_ADMIN', f'创建了新管理员账号: {username} (角色: {role})')
        return JsonResponse({'success': True, 'message': '管理员账号创建成功', 'data': {'username': username, 'role': role}})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'创建账号失败: {str(e)}'}, status=500)

@csrf_exempt
@admin_jwt_required()
@require_http_methods(["POST"])
def admin_change_password(request):
    """管理员自主修改密码"""
    try:
        data = json.loads(request.body)
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        
        if not old_password or not new_password:
            return JsonResponse({'success': False, 'error': '旧密码和新密码不能为空'}, status=400)
            
        if not check_password(old_password, request.admin_user.password):
            return JsonResponse({'success': False, 'error': '旧密码不正确'}, status=400)
            
        request.admin_user.password = make_password(new_password)
        request.admin_user.save(update_fields=['password', 'updated_at'])
        
        log_activity(request.admin_user, 'CHANGE_PASSWORD', f'修改了自己的登录密码')
        return JsonResponse({'success': True, 'message': '密码修改成功，请重新登录'})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': f'密码修改失败: {str(e)}'}, status=500)
