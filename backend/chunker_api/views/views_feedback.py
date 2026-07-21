import json
import traceback
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from chunker_api.models import ChatMessage, Document, DocumentVersion, Feedback, FeedbackDocument, FeedbackChunk, FeedbackProcessLog, AdminUser

# ----- 用户端接口 -----

@csrf_exempt
def submit_feedback(request):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': '未登录'}, status=401)
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '不支持的请求方法'}, status=405)
    
    try:
        data = json.loads(request.body)
        message_id = data.get('message_id')
        feedback_type = data.get('feedback_type')
        feedback_comment = data.get('feedback_comment', '')
        
        if not message_id or not feedback_type:
            return JsonResponse({'success': False, 'error': '参数不完整'}, status=400)
            
        try:
            message = ChatMessage.objects.get(id=message_id, session__user=request.user)
        except ChatMessage.DoesNotExist:
            return JsonResponse({'success': False, 'error': '未找到相关消息'}, status=404)
            
        question_msg = ChatMessage.objects.filter(session=message.session, role='user', created_at__lt=message.created_at).last()
        question_text = question_msg.content if question_msg else "未知问题"
        
        feedback = Feedback.objects.create(
            message=message,
            session=message.session,
            question=question_text,
            answer=message.content,
            feedback_type=feedback_type,
            feedback_comment=feedback_comment
        )
        
        sources = message.sources or []
        retrieval_hits = message.retrieval_hits or []
        citations = message.citations or []

        seen_docs = set()
        
        # 兼容 citations
        for doc_data in citations:
            doc_name = doc_data.get('title') or doc_data.get('file_name')
            ver_id = doc_data.get('version_id')
            if doc_name and doc_name not in seen_docs:
                seen_docs.add(doc_name)
                doc = Document.objects.filter(name=doc_name).first()
                if doc:
                    ver = DocumentVersion.objects.filter(id=ver_id).first() if ver_id else None
                    FeedbackDocument.objects.create(
                        feedback=feedback,
                        document=doc,
                        document_version=ver
                    )
                    
        # 兜底 sources
        if not seen_docs:
            for s in sources:
                doc_name = s.get('file_name')
                if doc_name and doc_name not in seen_docs:
                    seen_docs.add(doc_name)
                    doc = Document.objects.filter(name=doc_name).first()
                    if doc:
                        FeedbackDocument.objects.create(feedback=feedback, document=doc)
                        
        if retrieval_hits:
            for rank, chunk_data in enumerate(retrieval_hits):
                FeedbackChunk.objects.create(
                    feedback=feedback,
                    chunk_id=chunk_data.get('chunk_id', ''),
                    content=chunk_data.get('content', ''),
                    score=chunk_data.get('score', 0.0),
                    rank=rank
                )
        else:
            for rank, s in enumerate(sources):
                FeedbackChunk.objects.create(
                    feedback=feedback,
                    chunk_id=s.get('chunk_id', ''),
                    content=s.get('content', ''),
                    score=s.get('score_fused') or s.get('score_ce') or 0.0,
                    rank=rank
                )
            
        return JsonResponse({'success': True, 'feedback_id': feedback.id})
    except Exception as e:
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def get_feedback_types(request):
    types = [{'value': k, 'label': v} for k, v in Feedback.TYPE_CHOICES]
    return JsonResponse({'success': True, 'data': types})

# ----- 后台端接口 -----

def _check_admin(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None, JsonResponse({'success': False, 'error': '未提供 Token 或格式错误'}, status=401)
    token = auth_header.split(' ')[1]
    
    from utils.auth import verify_admin_token
    payload = verify_admin_token(token, 'access')
    if not payload:
        return None, JsonResponse({'success': False, 'error': 'Token 无效或已过期'}, status=401)
    admin_id = payload.get('admin_id')
    try:
        admin_user = AdminUser.objects.get(id=admin_id)
        return admin_user, None
    except AdminUser.DoesNotExist:
        return None, JsonResponse({'success': False, 'error': '管理员不存在'}, status=401)

@csrf_exempt
def admin_feedback_list(request):
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '只支持 GET 请求'}, status=405)
    
    admin, err = _check_admin(request)
    if err: return err
    
    status = request.GET.get('status')
    feedback_type = request.GET.get('type')
    keyword = request.GET.get('keyword')
    time_range = request.GET.get('time_range')
    
    qs = Feedback.objects.all()
    
    from django.utils import timezone
    import datetime
    if time_range == '7d':
        qs = qs.filter(created_at__gte=timezone.now() - datetime.timedelta(days=7))
    elif time_range == '30d':
        qs = qs.filter(created_at__gte=timezone.now() - datetime.timedelta(days=30))
        
    if status:
        qs = qs.filter(status=status)
    if feedback_type:
        qs = qs.filter(feedback_type=feedback_type)
    if keyword:
        qs = qs.filter(Q(question__icontains=keyword) | Q(answer__icontains=keyword) | Q(feedback_comment__icontains=keyword))
        
    data = []
    for fb in qs:
        data.append({
            'id': fb.id,
            'question': fb.question[:100],
            'type_value': fb.feedback_type,
            'type_label': fb.get_feedback_type_display(),
            'status': fb.status,
            'status_label': fb.get_status_display(),
            'created_at': fb.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'handler': fb.handler.username if fb.handler else None
        })
        
    return JsonResponse({'success': True, 'data': data})

@csrf_exempt
def admin_feedback_detail(request, feedback_id):
    if request.method != 'GET':
        return JsonResponse({'success': False, 'error': '只支持 GET 请求'}, status=405)
        
    admin, err = _check_admin(request)
    if err: return err
    
    try:
        fb = Feedback.objects.get(id=feedback_id)
    except Feedback.DoesNotExist:
        return JsonResponse({'success': False, 'error': '反馈不存在'}, status=404)
        
    docs = []
    for fd in fb.feedback_documents.all():
        docs.append({
            'id': fd.document.id,
            'name': fd.document.name,
            'version': fd.document_version.version_number if fd.document_version else None,
            'status': fd.document.status,
            'collection_name': fd.document.knowledge_base.collection_name
        })
        
    chunks = []
    for fc in fb.feedback_chunks.all():
        chunks.append({
            'chunk_id': fc.chunk_id,
            'content': fc.content,
            'score': fc.score,
            'rank': fc.rank
        })
        
    logs = []
    for log in fb.process_logs.all():
        logs.append({
            'operator': log.operator.username if log.operator else '系统',
            'action': log.get_action_display(),
            'remark': log.remark,
            'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    data = {
        'id': fb.id,
        'question': fb.question,
        'answer': fb.answer,
        'type_label': fb.get_feedback_type_display(),
        'comment': fb.feedback_comment,
        'status': fb.status,
        'status_label': fb.get_status_display(),
        'created_at': fb.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'documents': docs,
        'chunks': chunks,
        'logs': logs,
        'collection_name': fb.session.knowledge_base.collection_name if fb.session and fb.session.knowledge_base else ''
    }
    
    return JsonResponse({'success': True, 'data': data})

@csrf_exempt
def admin_feedback_ignore(request, feedback_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '只支持 POST 请求'}, status=405)
        
    admin, err = _check_admin(request)
    if err: return err
    
    try:
        data = json.loads(request.body)
        remark = data.get('remark', '')
        
        fb = Feedback.objects.get(id=feedback_id)
        fb.status = 'IGNORED'
        fb.handler = admin
        fb.save()
        
        FeedbackProcessLog.objects.create(
            feedback=fb,
            operator=admin,
            action='IGNORED',
            remark=remark
        )
        return JsonResponse({'success': True})
    except Feedback.DoesNotExist:
        return JsonResponse({'success': False, 'error': '反馈不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
def admin_feedback_offline_document(request, feedback_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '只支持 POST 请求'}, status=405)
        
    admin, err = _check_admin(request)
    if err: return err
    
    try:
        data = json.loads(request.body)
        document_id = data.get('document_id')
        remark = data.get('remark', '')
        
        fb = Feedback.objects.get(id=feedback_id)
        from chunker_api.models import Document
        doc = Document.objects.get(id=document_id)
        
        doc.status = 'inactive'
        doc.save(update_fields=['status', 'updated_at'])
        
        from chunker_api.chroma_sync import set_document_chunks_active_status
        collection_name = doc.knowledge_base.collection_name
        set_document_chunks_active_status(collection_name, doc.name, is_active=False)
        
        fb.status = 'RESOLVED'
        fb.handler = admin
        fb.save()
        
        from chunker_api.models import FeedbackProcessLog
        FeedbackProcessLog.objects.create(
            feedback=fb,
            operator=admin,
            action='DOCUMENT_OFFLINE',
            remark=f"下架文档 {doc.name}" + (f" - 备注: {remark}" if remark else "")
        )
        return JsonResponse({'success': True})
    except Feedback.DoesNotExist:
        return JsonResponse({'success': False, 'error': '反馈不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@csrf_exempt
def admin_feedback_update_chunk(request, feedback_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': '只支持 POST 请求'}, status=405)
        
    admin, err = _check_admin(request)
    if err: return err
    
    try:
        data = json.loads(request.body)
        chunk_id = data.get('chunk_id')
        new_content = data.get('new_content')
        collection_name = data.get('collection_name')
        remark = data.get('remark', '')
        
        if not chunk_id or not new_content or not collection_name:
            return JsonResponse({'success': False, 'error': '参数不完整'}, status=400)
            
        chunk_id = str(chunk_id) # 修复 ChromaDB Expected ID to be str 的报错
        fb = Feedback.objects.get(id=feedback_id)
        doc = fb.feedback_documents.first().document if fb.feedback_documents.exists() else None
        doc_version_id_str = str(fb.feedback_documents.first().document_version.id) if fb.feedback_documents.exists() and fb.feedback_documents.first().document_version else None
        # 如果获取不到具体反馈时的版本，或者为了确保前台显示一致，最好默认取当前文档的 current 版本
        current_ver = doc.versions.filter(status='current').first() if doc else None
        current_ver_id_str = str(current_ver.id) if current_ver else None
        
        # 优先使用当前生效版本来更新，防止更新到了历史废弃版本导致界面不同步
        target_version_id = current_ver_id_str or doc_version_id_str
        doc_name = doc.name if doc else None
        doc_id_str = str(doc.id) if doc else "未知"
        
        from django.conf import settings
        from utils.chunk.LocalEmbeddingEncoder import LocalEmbeddingEncoder
        local_model_path = getattr(settings, 'LOCAL_EMBEDDING_MODEL', 'G:\\models\\bge-large-zh')
        encoder = LocalEmbeddingEncoder(model_path=local_model_path)
        new_emb = encoder.encode([new_content])[0]['embedding']
        
        from chunker_api.chroma_sync import get_chroma_store, clear_bm25_cache
        store = get_chroma_store(collection_name)
        
        # 尝试通过传来的 chunk_id 定位真实主键
        real_chunk_id = chunk_id
        existing = store._collection.get(ids=[real_chunk_id], include=["metadatas"])
        
        if not existing or not existing.get("ids"):
            # 如果没找到，说明前台传的是切片序号（metadata 中的 chunk_id），需要全表扫描匹配出真实 UUID 主键
            all_docs = store._collection.get(include=["metadatas"])
            found_id = None
            for tid, meta in zip(all_docs.get("ids", []), all_docs.get("metadatas", [])):
                if meta:
                    m_file = meta.get("file_name") or meta.get("source") or meta.get("source_file")
                    m_cid = str(meta.get("chunk_id", ""))
                    m_vid = str(meta.get("version_id", ""))
                    
                    if m_file == doc_name and m_cid == chunk_id:
                        # 确保精确命中当前激活的版本！防止更新到了过期的历史版本中导致文档管理界面依然显示旧数据
                        if target_version_id and m_vid != target_version_id:
                            continue
                        found_id = tid
                        break
            if found_id:
                real_chunk_id = found_id
                existing = store._collection.get(ids=[real_chunk_id], include=["metadatas"])
            else:
                return JsonResponse({'success': False, 'error': '向量库底层匹配失败，该切片可能已被废弃或被其他流程覆盖'}, status=404)

        metadatas = existing.get("metadatas")
        if metadatas and len(metadatas) > 0:
            meta = metadatas[0]
            if 'text' in meta:
                meta['text'] = new_content
            store._collection.update(ids=[real_chunk_id], embeddings=[new_emb], documents=[new_content], metadatas=[meta])
        else:
            store._collection.update(ids=[real_chunk_id], embeddings=[new_emb], documents=[new_content])
            
        clear_bm25_cache(collection_name)
        
        fb.status = 'RESOLVED'
        fb.handler = admin
        fb.save()
        
        # 同步更新该反馈下对应的 FeedbackChunk 实体，保证详情页界面刷新后可见最新文本
        from chunker_api.models import FeedbackChunk
        FeedbackChunk.objects.filter(feedback=fb, chunk_id=chunk_id).update(content=new_content)
        
        from chunker_api.models import FeedbackProcessLog, OperationLog
        FeedbackProcessLog.objects.create(
            feedback=fb,
            operator=admin,
            action='CHUNK_UPDATED',
            remark=f"更新了 Chunk {real_chunk_id}" + (f" - 备注: {remark}" if remark else "")
        )
        
        OperationLog.objects.create(
            admin_user=admin,
            action='EDIT_CHUNK',
            details=f"在问题反馈处理中热修复了分块内容 (文档ID: {doc_id_str} | Chunk ID: {real_chunk_id} | 反馈工单: {fb.id})" + (f" - 备注: {remark}" if remark else "")
        )
        
        return JsonResponse({'success': True})
    except Feedback.DoesNotExist:
        return JsonResponse({'success': False, 'error': '反馈不存在'}, status=404)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)}, status=500)
