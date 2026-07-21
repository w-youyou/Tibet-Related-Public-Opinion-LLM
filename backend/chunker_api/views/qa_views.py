import os
import json
import tempfile
import shutil
import base64
import uuid
import time
from urllib.parse import urlparse
from django.http import JsonResponse, HttpResponse, Http404, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
import logging
from ..models import KnowledgeBase, ChatSession, ChatMessage
from utils.chunk.LocalEmbeddingEncoder import LocalEmbeddingEncoder
# 调用 RAGService（进程内缓存，避免每次请求重复加载 reranker / bm25 / chroma 等导致极慢）
from ..rag_service import RAGService
from ..flow import extract_and_render_flow
try:
    from utils.Tools.persona import record_user_activity
    from utils.promt.prompt import build_answer_strategy, format_strategy_text
except ImportError:
    pass


logger = logging.getLogger(__name__)

# 多轮对话历史最大轮数（每轮 = 用户 + 助手各一条）
_MAX_HISTORY_TURNS = 10


def _load_history_from_db(session_id, user):
    """从数据库加载会话历史消息，转换为 [{role, content}] 格式。"""
    if not session_id:
        return []
    try:
        session = ChatSession.objects.get(id=session_id, user=user)
    except ChatSession.DoesNotExist:
        logger.warning(f"会话 {session_id} 不存在或无权限")
        return []
    messages = ChatMessage.objects.filter(session=session).order_by('created_at')
    # 取最近 N 轮，截断过长历史避免 prompt 超限
    max_msgs = _MAX_HISTORY_TURNS * 2
    recent = messages[max_msgs * -1:] if messages.count() > max_msgs else messages
    return [{'role': m.role, 'content': m.content} for m in recent]

# Spilter / MultimodalEncoder / docx 等重型模块均在各 process_* 函数中惰性导入，
# 避免非分块请求（health、auth、chat、qa）触发不必要的 langchain/chromadb 加载。

def _import_multimodal_encoder():
    """惰性导入 MultimodalEncoder。"""
    from .Spilter.MultimodalEncoder import MultimodalEncoder
    return MultimodalEncoder

def generate_jsonl_content(chunks):
    """生成JSONL格式的内容"""
    jsonl_lines = []
    for chunk in chunks:
        jsonl_lines.append(json.dumps(chunk, ensure_ascii=False))
    return '\n'.join(jsonl_lines)


def _is_flow_extract_enabled(raw: str) -> bool:
    return str(raw or 'false').strip().lower() in {'1', 'true', 'yes', 'on'}


def _build_flow_matter_record(matter: dict, fallback_source_file: str = '') -> dict:
    flow_graph = matter.get('flow_graph') or {}
    render = matter.get('render') or {}
    steps = flow_graph.get('steps') or []

    step_lines = []
    for idx, step in enumerate(steps, 1):
        text = (step.get('action') or step.get('raw_text') or '').strip()
        if text:
            step_lines.append(f"{idx}. {text}")

    steps_text = '\n'.join(step_lines)
    matter_title = matter.get('matter_title') or flow_graph.get('title') or '未命名事项'
    summary_text = f"事项：{matter_title}，共{len(step_lines)}步。"

    return {
        'matter_title': matter_title,
        'matter_index': int(matter.get('matter_index') or 0),
        'steps_text': steps_text,
        'summary_text': summary_text,
        'svg_url': render.get('svg_url') or '',
        'png_url': render.get('png_url') or '',
        'source_file': flow_graph.get('source_file') or fallback_source_file,
        'text': f"{summary_text}\n\n{steps_text}".strip(),
    }


def _extract_sources_and_flows(docs: list) -> tuple[list, list]:
    sources = []
    flow_references = []
    for d in docs or []:
        md = d.get('metadata') or {}
        if md.get('doc_type') == 'flow_matter':
            flow_references.append({
                'matter_title': md.get('matter_title') or '未命名事项',
                'summary': md.get('summary_text') or (d.get('content') or '')[:120],
                'svg_url': md.get('svg_url') or '',
                'png_url': md.get('png_url') or '',
            })
            continue

        sources.append({
            'content': d.get('content', ''),
            'file_name': md.get('file_name') or md.get('source') or md.get('source_file') or '未知',
            'chunk_id': md.get('chunk_id') or '',
            'score_fused': md.get('_s_fused') or md.get('_rrf_score'),
            'score_ce': md.get('_s_ce_norm'),
        })

    return sources, flow_references


def _is_flow_question(question: str) -> bool:
    q = (question or '').strip()
    keys = ['流程', '步骤', '办理', '怎么办', '如何办', '材料', '时限', '窗口']
    return any(k in q for k in keys)


def _coerce_optional_int(value):
    if value in (None, ''):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolve_profile_age(request, data: dict):
    """登录用户资料优先；缺失时再使用请求体中的年龄。"""
    raw_age = getattr(request.user, 'age', None)
    if raw_age in (None, ''):
        raw_age = data.get('age')
    return _coerce_optional_int(raw_age)


def _resolve_profile_is_employee(request, data: dict):
    raw = data.get('is_employee', None)
    if raw is not None:
        if isinstance(raw, bool):
            return raw
        return str(raw).strip().lower() in {'1', 'true', 'yes', 'on'}
    return getattr(request.user, 'user_type', None) == 'enterprise'


def read_doc_file(file_path: str) -> str:
    """读取.doc文件内容"""
    try:
        import win32com.client
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

@csrf_exempt
@require_http_methods(["POST"])
def chunk_document(request):
    """
    文档分块API接口
    
    请求参数:
    - file: 上传的文件
    - chunker_type: 分块器类型 (qa, law, semantic, policy, table)
    - chunker_params: 分块器参数 (可选)
    """
    try:
        # 调试信息
        logger.info(f"请求方法: {request.method}")
        logger.info(f"请求头: {dict(request.headers)}")
        logger.info(f"FILES keys: {list(request.FILES.keys())}")
        logger.info(f"POST keys: {list(request.POST.keys())}")
        
        # 获取上传的文件
        if 'file' not in request.FILES:
            logger.error("没有找到文件字段")
            return JsonResponse({'error': '没有上传文件'}, status=400)
        
        file = request.FILES['file']
        chunker_type = request.POST.get('chunker_type', 'semantic')
        enable_flow_extract = _is_flow_extract_enabled(request.POST.get('enable_flow_extract', 'false'))
        flow_extract = {
            'enabled': enable_flow_extract,
            'success': False,
            'matter_count': 0,
            'message': '未开启流程提取' if not enable_flow_extract else '流程提取尚未执行'
        }
        
        logger.info(f"文件名称: {file.name}, 文件大小: {file.size}, 分块器类型: {chunker_type}, enable_flow_extract: {enable_flow_extract}")
        
        # 验证文件类型（multimodal支持更多格式）
        allowed_extensions = ['.txt', '.pdf', '.docx', '.doc', '.xlsx', '.xls']
        if chunker_type == 'multimodal':
            # 多模态分块器支持更多格式
            allowed_extensions.extend(['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.mp4', '.avi', '.mov'])
        
        file_ext = os.path.splitext(file.name)[1].lower()
        if file_ext not in allowed_extensions:
            return JsonResponse({
                'error': f'不支持的文件类型: {file_ext}',
                'supported_types': allowed_extensions
            }, status=400)
        
        # 保存临时文件到项目本地目录
        tmp_dir = getattr(settings, 'TMP_DIR', os.path.join(settings.BASE_DIR, 'tmp'))
        os.makedirs(tmp_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext, dir=tmp_dir) as temp_file:
            for chunk in file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name
        
        try:
            # 获取知识库ID（如果提供）
            knowledge_base_id = request.POST.get('knowledge_base_id', None)
            
            # 根据分块器类型处理文档
            if chunker_type == 'by_length':
                chunk_size = int(request.POST.get('chunk_size', 1000))
                chunk_overlap = int(request.POST.get('chunk_overlap', 200))
                result = process_basic_chunker(temp_file_path, file.name, 'by_length', chunk_size, chunk_overlap)
            elif chunker_type == 'by_punctuation':
                chunk_size = int(request.POST.get('chunk_size', 1000))
                chunk_overlap = int(request.POST.get('chunk_overlap', 200))
                result = process_basic_chunker(temp_file_path, file.name, 'by_punctuation', chunk_size, chunk_overlap)
            elif chunker_type == 'recursive':
                chunk_size = int(request.POST.get('chunk_size', 1000))
                chunk_overlap = int(request.POST.get('chunk_overlap', 200))
                result = process_basic_chunker(temp_file_path, file.name, 'recursive', chunk_size, chunk_overlap)
            elif chunker_type == 'by_page':
                result = process_basic_chunker(temp_file_path, file.name, 'by_page')
            elif chunker_type == 'qa':
                result = process_qa_chunker(temp_file_path, file.name)
            elif chunker_type == 'law':
                result = process_law_chunker(temp_file_path, file.name)
            elif chunker_type == 'semantic':
                # 获取语义分块器参数
                min_chars = int(request.POST.get('min_chars', 400))
                max_chars = int(request.POST.get('max_chars', 800))
                window_size = int(request.POST.get('window_size', 4))
                result = process_semantic_chunker(temp_file_path, file.name, min_chars, max_chars, window_size)
            elif chunker_type == 'policy':
                result = process_policy_chunker(temp_file_path, file.name)
            elif chunker_type == 'table':
                result = process_table_chunker(temp_file_path, file.name)
            elif chunker_type == 'multimodal':
                # 获取多模态分块器参数
                text_chunk_size = int(request.POST.get('text_chunk_size', 1000))
                text_chunk_overlap = int(request.POST.get('text_chunk_overlap', 200))
                min_chars = int(request.POST.get('min_chars', 400))
                max_chars = int(request.POST.get('max_chars', 800))
                window_size = int(request.POST.get('window_size', 4))
                # 默认启用编码
                result = process_multimodal_chunker(
                    temp_file_path, 
                    file.name, 
                    enable_encoding=True, 
                    request=request,
                    knowledge_base_id=knowledge_base_id,
                    text_chunk_size=text_chunk_size,
                    text_chunk_overlap=text_chunk_overlap,
                    min_chars=min_chars,
                    max_chars=max_chars,
                    window_size=window_size
                )
            else:
                return JsonResponse({'error': f'不支持的分块器类型: {chunker_type}'}, status=400)
            
            # 对纯文本数据进行向量化（多模态数据已在process_multimodal_chunker中处理）
            if chunker_type != 'multimodal' and chunker_type in ['by_length', 'by_punctuation', 'recursive', 'by_page', 'semantic', 'qa', 'law', 'policy', 'table']:
                try:
                    # 默认启用向量化存储
                    encoding_stats = process_text_embedding(
                        chunks=result['chunks'],
                        chunker_type=chunker_type,
                        file_name=file.name,
                        knowledge_base_id=knowledge_base_id,
                        request=request
                    )
                    if encoding_stats:
                        result['statistics']['encoding'] = encoding_stats
                except Exception as e:
                    logger.warning(f"文本向量化失败: {e}")
                    # 向量化失败不影响分块结果返回
            
            # 开启时执行流程提取（失败不影响主链路）
            if enable_flow_extract:
                if file_ext in ['.pdf', '.docx', '.txt']:
                    try:
                        flow_result = extract_and_render_flow(
                            file_path=temp_file_path,
                            title=os.path.splitext(file.name)[0],
                            use_agent=True,
                            request=request,
                        )
                        matters = flow_result.get('matters') or []
                        flow_matter_chunks = []

                        if matters:
                            for i, matter in enumerate(matters, 1):
                                m = _build_flow_matter_record(matter, fallback_source_file=file.name)
                                flow_matter_chunks.append({
                                    'id': 1000000 + i,
                                    'content': m['text'],
                                    'modality_type': 'text',
                                    'metadata': {
                                        'file_name': file.name,
                                        'source_file': m['source_file'] or file.name,
                                        'doc_type': 'flow_matter',
                                        'matter_title': m['matter_title'],
                                        'matter_index': m['matter_index'] or i,
                                        'steps_text': m['steps_text'],
                                        'summary_text': m['summary_text'],
                                        'svg_url': m['svg_url'],
                                        'png_url': m['png_url'],
                                    }
                                })

                            # 写入同知识库集合，作为可检索流程事项
                            process_text_embedding(
                                chunks=flow_matter_chunks,
                                chunker_type='flow_matter',
                                file_name=file.name,
                                knowledge_base_id=knowledge_base_id,
                                request=request
                            )

                        flow_extract = {
                            'enabled': True,
                            'success': True,
                            'matter_count': len(flow_matter_chunks),
                            'message': '流程提取完成' if flow_matter_chunks else '未提取到流程事项'
                        }
                    except Exception as flow_err:
                        logger.warning(f"流程提取失败（不阻断上传）: {flow_err}")
                        flow_extract = {
                            'enabled': True,
                            'success': False,
                            'matter_count': 0,
                            'message': f'流程提取失败: {flow_err}'
                        }
                else:
                    flow_extract = {
                        'enabled': True,
                        'success': False,
                        'matter_count': 0,
                        'message': '仅支持 pdf/docx/txt 进行流程提取'
                    }

            # 生成JSONL格式的结果
            jsonl_content = generate_jsonl_content(result['chunks'])
            
            return JsonResponse({
                'success': True,
                'chunker_type': chunker_type,
                'file_name': file.name,
                'chunks': result['chunks'],
                'jsonl_content': jsonl_content,
                'flow_extract': flow_extract,
                'metadata': result.get('metadata', {}),
                'statistics': result.get('statistics', {})
            })
            
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                
    except Exception as e:
        logger.error(f"分块处理失败: {str(e)}")
        return JsonResponse({'error': f'处理失败: {str(e)}'}, status=500)


# ==================== 多模态问答相关API ====================

@csrf_exempt
@require_http_methods(["POST"])
def hybrid_qa_stream(request):
    """混合检索问答（SSE 流式输出，仅回答阶段流式）。

    SSE 事件：
    - meta: 先返回 session_id/sources/images/metadata
    - token: 逐段输出回答文本
    - done: 结束
    - error: 出错

    说明：
    - 检索不流式：仍然同步执行检索与画像模板选择
    - 回答流式：调用 QwenLLM.stream_answer / stream_answer_multimodal
    """

    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': '请先登录'}, status=401)

    def sse_pack(event: str, payload) -> str:
        return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

    try:
        data = json.loads(request.body or '{}')
        question = (data.get('question') or '').strip()
        top_k = int(data.get('top_k', 5))
        if _is_flow_question(question):
            top_k = max(top_k, 12)
        if _is_flow_question(question):
            top_k = max(top_k, 12)
        is_strict = bool(data.get('is_strict', False))
        debug = bool(data.get('debug', False))
        age = _resolve_profile_age(request, data)
        is_employee = _resolve_profile_is_employee(request, data)
        frequency = data.get('frequency')
        history = data.get('history') or []
        session_id = data.get('session_id')
        # ✅ 前端未传 history 时，从数据库自动回读会话历史
        if session_id and not history:
            history = _load_history_from_db(session_id, request.user)
        kb_ids = data.get('knowledge_base_id')

        if not question:
            return JsonResponse({'success': False, 'error': '问题不能为空'}, status=400)

        api_key = getattr(settings, 'DASHSCOPE_API_KEY', None)
        if not api_key:
            return JsonResponse({'success': False, 'error': '未配置 DASHSCOPE_API_KEY'}, status=500)

        # 解析知识库集合
        collection_names = []
        kb_instance = None
        if isinstance(kb_ids, list):
            kb_id_list = kb_ids
        elif isinstance(kb_ids, str) and kb_ids:
            kb_id_list = [kb_ids]
        else:
            kb_id_list = []

        if kb_id_list:
            for kid in kb_id_list:
                try:
                    kb = KnowledgeBase.objects.get(id=kid, user=request.user)
                    collection_names.append(kb.collection_name)
                    if not kb_instance:
                        kb_instance = kb
                except KnowledgeBase.DoesNotExist:
                    return JsonResponse({'success': False, 'error': f'知识库不存在或无权限访问: {kid}'}, status=404)
        else:
            user_kbs = KnowledgeBase.objects.filter(user=request.user)
            collection_names = [kb.collection_name for kb in user_kbs]
            if not collection_names:
                return JsonResponse({'success': False, 'error': '您还没有创建任何知识库'}, status=400)

        # 会话
        is_new_session = False
        if session_id:
            try:
                chat_session = ChatSession.objects.get(id=session_id, user=request.user)
                if chat_session.title == '新对话' and not chat_session.messages.exists():
                    is_new_session = True
            except ChatSession.DoesNotExist:
                return JsonResponse({'success': False, 'error': '会话不存在或无权限访问'}, status=404)
        else:
            title = question[:20] + ('...' if len(question) > 20 else '')
            chat_session = ChatSession.objects.create(user=request.user, title=title, knowledge_base=kb_instance)
            is_new_session = True

        # 保存用户消息
        ChatMessage.objects.create(session=chat_session, role='user', content=question)

        # 获取 RAGPipeline 单例（统一工厂）
        from ..rag import get_rag_service
        chroma_path = getattr(settings, 'CHROMA_DB_PATH', './chroma_db')
        rag = get_rag_service(api_key=api_key, model_name="qwen3-omni-flash", chroma_db_path=chroma_path)

        # 同步检索（run 内部会产出 docs/images 以及 RAG v1 所需字段）
        result = rag.run(
            question=question,
            collection_names=collection_names,
            history=history,
            age=age,
            is_employee=is_employee,
            frequency=frequency,
            is_strict=is_strict,
            top_k=top_k,
            debug=debug,
        )

        # 注意：当前 run 内部已经生成了 answer（非流式）。
        # 为保证”只流式输出回答”且不重复消耗模型，推荐下一步把 run 拆分为：
        # - retrieve_only（只检索/组 prompt）
        # - stream_generate（只流式生成）
        # 这里先采用最小侵入方案：仍然用 result 的 docs/images 重新构建 prompt 并流式生成（会多一次 LLM 调用）。

        docs = result.get('docs', []) or []
        images = result.get('images', []) or []

        sources, flow_references = _extract_sources_and_flows(docs)

        # 构建 prompt（复用 rag_service 里的 build_prompt）
        # text_contexts: 只用文本 docs
        text_contexts = []
        for d in docs:
            md = d.get('metadata') or {}
            if md.get('modality_type', 'text') == 'text':
                text_contexts.append({'content': d.get('content', ''), 'metadata': md, 'distance': d.get('distance', 0)})

        image_contexts = []
        for img in images:
            md = img.get('metadata') or {}
            image_contexts.append({'metadata': md, 'distance': img.get('distance', 0)})


        # --- 新增：构造画像驱动回答策略 ---
        strategy_text = None
        try:
            record_user_activity(request.user)
            persona = getattr(request.user, 'persona', None)
            role = persona.role if persona else 'external'
            age_group = persona.age_group if persona else 'youth'
            freq = persona.frequency if persona else 'normal'
            strategy = build_answer_strategy(role=role, age_group=age_group, frequency=freq)
            strategy_text = format_strategy_text(strategy)
        except Exception as e:
            logger.error(f"构建画像策略失败: {e}")

        sys_prompt, user_prompt = rag.build_prompt(
            question=question,
            text_contexts=text_contexts,
            image_contexts=image_contexts,
            system_prompt=None,
            strategy_text=strategy_text
        )

        def _to_data_url_from_local_image(md: dict, fallback_url: str | None) -> str | None:
            """将本地图片转换为 data URL（base64），用于发送给云端多模态模型。

            优先使用 metadata.image_path；其次尝试根据 image_url/full_image_url 推断本地路径。
            """
            # 1) 直接用 image_path
            image_path = md.get('image_path')
            if image_path and os.path.exists(image_path):
                try:
                    ext = os.path.splitext(image_path)[1].lower()
                    mime = {
                        '.png': 'image/png',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.webp': 'image/webp',
                        '.bmp': 'image/bmp',
                        '.gif': 'image/gif',
                    }.get(ext, 'image/png')
                    with open(image_path, 'rb') as f:
                        b64 = base64.b64encode(f.read()).decode('utf-8')
                    return f"data:{mime};base64,{b64}"
                except Exception as e:
                    logger.warning(f"图片转base64失败(image_path): {e}")

            # 2) 尝试用 image_url 推断本地路径：/api/media/<relpath>
            rel = md.get('image_url')
            if not rel and fallback_url:
                try:
                    rel = urlparse(fallback_url).path
                except Exception:
                    rel = None
            if rel and isinstance(rel, str) and rel.startswith('/api/media/'):
                rel_path = rel[len('/api/media/'):]
                try:
                    local_path = os.path.join(getattr(settings, 'EXTRACTED_IMAGES_DIR'), rel_path)
                    local_path = os.path.normpath(local_path)
                    if os.path.exists(local_path):
                        ext = os.path.splitext(local_path)[1].lower()
                        mime = {
                            '.png': 'image/png',
                            '.jpg': 'image/jpeg',
                            '.jpeg': 'image/jpeg',
                            '.webp': 'image/webp',
                            '.bmp': 'image/bmp',
                            '.gif': 'image/gif',
                        }.get(ext, 'image/png')
                        with open(local_path, 'rb') as f:
                            b64 = base64.b64encode(f.read()).decode('utf-8')
                        return f"data:{mime};base64,{b64}"
                except Exception as e:
                    logger.warning(f"图片转base64失败(image_url推断): {e}")

            return None

        image_urls: list[str] = []
        for img in images:
            md = img.get('metadata') or {}
            url = md.get('full_image_url') or md.get('image_url') or img.get('url')
            data_url = _to_data_url_from_local_image(md, url)
            if data_url:
                image_urls.append(data_url)
            # 若转 base64 失败：不加入图片，避免 400 直接失败（仍可走纯文本回答）

        def event_stream():
            trace_id = uuid.uuid4().hex
            refusal_obj = result.get('refusal') or {}
            refusal_payload = (
                {**refusal_obj, 'reply_text': result.get('answer', '')}
                if refusal_obj.get('is_refused')
                else (result.get('refusal', None))
            )

            # 先发 meta（RAG v1 协议：citations=文档静态信息，retrieval_hits=chunk级动态信息）
            yield sse_pack('meta', {
                'success': True,
                'session_id': str(chat_session.id),
                'trace_id': trace_id,
                'answer': '',
                'citations': result.get('citations', []) or [],
                'retrieval_hits': result.get('retrieval_hits', []) or [],
                'evidence_spans': result.get('evidence_spans', []) or [],
                'retrieval_stats': result.get('retrieval_stats', {}) or {},
                'refusal': refusal_payload,

                # 兼容旧字段：保持现有前端不崩
                'sources': sources,
                'images': images,
                'flow_references': flow_references,
                'metadata': {
                    'collections': collection_names,
                    'used_template': result.get('used_template'),
                    'top_k': top_k,
                    'strict': is_strict,
                    **({'debug': result.get('debug')} if debug else {}),
                }
            })

            full_answer_parts = []
            try:
                # 拒答：不生成正文，不发送 token
                if (result.get('refusal') or {}).get('is_refused'):
                    final_answer = result.get('answer', '')
                elif result.get('used_template') == 'direct':
                    # 普通直答已在 run 中按 get_direct_template 生成，避免空上下文二次生成。
                    final_answer = result.get('answer', '')
                    if final_answer:
                        yield sse_pack('token', {'delta': final_answer})
                else:
                    if image_urls:
                        for token in rag.llm.stream_answer_multimodal(text=user_prompt, image_urls=image_urls, system_prompt=sys_prompt):
                            full_answer_parts.append(token)
                            yield sse_pack('token', {'delta': token})
                    else:
                        for token in rag.llm.stream_answer(prompt=user_prompt, system_prompt=sys_prompt):
                            full_answer_parts.append(token)
                            yield sse_pack('token', {'delta': token})

                    # 非拒答时，拼接最终答案
                    final_answer = ''.join(full_answer_parts).strip()

                # 生成引导式追问（拒答/空答案时不生成）
                suggested_next_questions = []
                is_refused = (result.get('refusal') or {}).get('is_refused')
                if not is_refused and final_answer.strip():
                    try:
                        source_files = list(set(
                            (d.get('metadata') or {}).get('file_name', '')
                            for d in docs
                            if (d.get('metadata') or {}).get('modality_type', 'text') == 'text'
                        ))
                        sources_summary = '、'.join(source_files[:5]) if source_files else ''
                        suggested_next_questions = rag.builder.generate_suggested_next_questions(
                            question=question,
                            answer=final_answer,
                            sources_summary=sources_summary,
                            is_refused=False,
                        )
                    except Exception:
                        pass

                # 保存助手消息（RAG v1 协议字段落库）
                assistant_msg = ChatMessage.objects.create(
                    session=chat_session,
                    role='assistant',
                    content=final_answer,
                    sources=sources or None,
                    images=images or None,
                    trace_id=trace_id,
                    citations=result.get('citations', None),
                    retrieval_hits=result.get('retrieval_hits', None),
                    evidence_spans=result.get('evidence_spans', None),
                    retrieval_stats=result.get('retrieval_stats', None),
                    refusal=result.get('refusal', None),
                    suggested_next_questions=suggested_next_questions or None,
                )

                # 新会话生成标题（可选）
                try:
                    if (
                        not (result.get('refusal') or {}).get('is_refused')
                        and is_new_session
                    ):
                        new_title = rag.builder.generate_title(question, final_answer, api_key)
                        if new_title:
                            chat_session.title = new_title[:50]
                            chat_session.save(update_fields=['title', 'updated_at'])
                except Exception:
                    pass

                yield sse_pack('done', {'ok': True, 'message_id': assistant_msg.id, 'flow_references': flow_references, 'suggested_next_questions': suggested_next_questions})
            except Exception as e:
                yield sse_pack('error', {'ok': False, 'error': str(e)})

        resp = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp

    except Exception as e:
        logger.error(f"hybrid_qa_stream failed: {e}")
        return JsonResponse({'success': False, 'error': f'问答失败: {e}'}, status=500)


def process_qa_chunker(file_path, file_name):
    """处理问答分块器"""
    from .Spilter.QAspilter import run as qa_run
    try:
        # 创建临时输出文件
        tmp_dir = getattr(settings, 'TMP_DIR', os.path.join(settings.BASE_DIR, 'tmp'))
        os.makedirs(tmp_dir, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl', dir=tmp_dir) as output_file:
            output_path = output_file.name
        
        # 运行QA分块器
        result_code = qa_run(
            input_path=file_path,
            output_path=output_path,
            preserve_line_breaks=True
        )
        
        if result_code != 0:
            raise Exception("QA分块器处理失败")
        
        # 读取结果
        chunks = []
        with open(output_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    chunk_data = json.loads(line.strip())
                    chunks.append({
                        'id': chunk_data['id'],
                        'content': chunk_data['content'],
                        'metadata': chunk_data['metadata']
                    })
        
        # 清理临时文件
        os.unlink(output_path)
        
        return {
            'chunks': chunks,
            'statistics': {
                'total_chunks': len(chunks),
                'chunker_name': '问答分块器'
            }
        }
        
    except Exception as e:
        raise Exception(f"QA分块器处理失败: {str(e)}")


def process_law_chunker(file_path, file_name):
    """处理法律法规分块器"""
    from .Spilter.LawSpilter import LawSpilter
    try:
        splitter = LawSpilter()
        
        # 读取文档
        if file_path.endswith('.pdf'):
            text_content = splitter.read_pdf(file_path)
        elif file_path.endswith('.docx'):
            text_content = splitter.read_docx(file_path)
        elif file_path.endswith('.doc'):
            text_content = read_doc_file(file_path)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
        
        if not text_content:
            raise Exception("无法读取文档内容")
        
        # 执行分块
        chunks_data = splitter.split_text(text_content, file_name, file_path)
        
        # 转换为API格式
        chunks = []
        for i, chunk in enumerate(chunks_data):
            chunks.append({
                'id': i + 1,
                'content': chunk.content,
                'metadata': chunk.metadata
            })
        
        # 获取统计信息
        stats = splitter.get_chunk_statistics(chunks_data)
        
        return {
            'chunks': chunks,
            'statistics': {
                'total_chunks': len(chunks),
                'chunker_name': '法律法规分块器',
                'articles_count': stats.get('articles_count', 0),
                'chapters': stats.get('chapters', {})
            }
        }
        
    except Exception as e:
        raise Exception(f"法律法规分块器处理失败: {str(e)}")


def process_basic_chunker(file_path, file_name, method, chunk_size=1000, chunk_overlap=200):
    """处理基础分块器"""
    from .Spilter.BasicSpilter import BasicSpilter
    try:
        splitter = BasicSpilter()
        chunks_data = splitter.split_file(file_path, method, chunk_size, chunk_overlap)
        
        # 转换为API格式
        chunks = []
        for chunk in chunks_data:
            chunks.append({
                'id': chunk.id,
                'content': chunk.content,
                'metadata': chunk.metadata
            })
        
        return {
            'chunks': chunks,
            'statistics': {
                'total_chunks': len(chunks),
                'chunker_name': f'基础分块器-{method}',
                'chunk_method': method,
                'chunk_size': chunk_size,
                'chunk_overlap': chunk_overlap
            }
        }
    
    except Exception as e:
        raise Exception(f"基础分块器处理失败: {str(e)}")


def process_semantic_chunker(file_path, file_name, min_chars=400, max_chars=800, window_size=4, smoothing_width=2):
    """处理语义分块器"""
    from .Spilter.optimized_semantic_spilter import split_text_to_chunks, split_docx_to_chunks, split_pdf_to_chunks
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        chunk_size = 1000  # 处理窗口大小，固定值
        
        if file_ext == '.pdf':
            chunks = split_pdf_to_chunks(file_path, min_chars=min_chars, max_chars=max_chars, window_size=window_size, smoothing_width=smoothing_width, chunk_size=chunk_size)
        elif file_ext == '.docx':
            chunks = split_docx_to_chunks(file_path, min_chars=min_chars, max_chars=max_chars, window_size=window_size, smoothing_width=smoothing_width, chunk_size=chunk_size)
        elif file_ext == '.doc':
            # 对于.doc文件，先读取内容再分块
            text_content = read_doc_file(file_path)
            chunks = split_text_to_chunks(text_content, min_chars=min_chars, max_chars=max_chars, window_size=window_size, smoothing_width=smoothing_width, chunk_size=chunk_size)
        else:
            chunks = split_text_to_chunks(open(file_path, 'r', encoding='utf-8').read(), min_chars=min_chars, max_chars=max_chars, window_size=window_size, smoothing_width=smoothing_width, chunk_size=chunk_size)
        
        # 转换为API格式
        result_chunks = []
        for i, chunk_content in enumerate(chunks):
            result_chunks.append({
                'id': i + 1,
                'content': chunk_content,
                'metadata': {
                    'chunk_size': len(chunk_content),
                    'source_file': file_name,
                    'file_name': file_name,
                    'chunker': 'semantic'
                }
            })
        
        return {
            'chunks': result_chunks,
            'statistics': {
                'total_chunks': len(result_chunks),
                'chunker_name': '语义分块器',
                'avg_chunk_size': sum(len(c['content']) for c in result_chunks) // len(result_chunks) if result_chunks else 0
            }
        }
        
    except Exception as e:
        raise Exception(f"语义分块器处理失败: {str(e)}")


def process_policy_chunker(file_path, file_name):
    """处理政策公告分块器"""
    from .Spilter.PolicyAnnouncementSpilter import PolicyAnnouncementSpilter
    try:
        splitter = PolicyAnnouncementSpilter()
        
        # 读取文档
        if file_path.endswith('.pdf'):
            text_content, tables_info = splitter.read_pdf(file_path)
        elif file_path.endswith('.docx'):
            text_content, tables_info = splitter.read_docx(file_path)
        elif file_path.endswith('.doc'):
            text_content = read_doc_file(file_path)
            tables_info = []  # .doc文件暂不支持表格提取
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                text_content = f.read()
            tables_info = []
        
        if not text_content:
            raise Exception("无法读取文档内容")
        
        # 执行分块
        chunks_data = splitter.split_text(text_content, tables_info, file_path)
        
        # 转换为API格式
        chunks = []
        for i, chunk in enumerate(chunks_data):
            chunks.append({
                'id': i + 1,
                'content': chunk.content,
                'metadata': chunk.metadata
            })
        
        return {
            'chunks': chunks,
            'statistics': {
                'total_chunks': len(chunks),
                'chunker_name': '政策公告分块器',
                'tables_count': len(tables_info)
            }
        }
        
    except Exception as e:
        raise Exception(f"政策公告分块器处理失败: {str(e)}")


def process_table_chunker(file_path, file_name):
    """处理表格分块器"""
    from .Spilter.TableSpilter import TableSpilter
    try:
        splitter = TableSpilter(rows_per_chunk=30)
        
        # 读取表格
        tables = splitter.read_any(file_path)
        
        if not tables:
            raise Exception("未找到表格数据")
        
        # 处理所有表格
        all_chunks = []
        for table_name, rows in tables:
            chunks = splitter.split_table_rows(
                rows, 
                file_name=file_name, 
                table_name=table_name,
                file_path=file_path
            )
            all_chunks.extend(chunks)
        
        # 转换为API格式
        result_chunks = []
        for i, chunk in enumerate(all_chunks):
            # 将表格数据转换为记录格式
            records = splitter.rows_to_records(chunk.content)
            result_chunks.append({
                'id': i + 1,
                'content': json.dumps(records, ensure_ascii=False),
                'metadata': chunk.metadata
            })
        
        return {
            'chunks': result_chunks,
            'statistics': {
                'total_chunks': len(result_chunks),
                'chunker_name': '表格分块器',
                'tables_count': len(tables)
            }
        }
        
    except Exception as e:
        raise Exception(f"表格分块器处理失败: {str(e)}")


def process_text_embedding(chunks, chunker_type, file_name, knowledge_base_id=None, request=None):
    """
    处理纯文本数据的向量化（统一使用多模态编码器）
    
    Args:
        chunks: 分块列表
        chunker_type: 分块器类型
        file_name: 文件名
        knowledge_base_id: 知识库ID（可选）
        request: Django请求对象（可选）
    
    Returns:
        编码统计信息字典
    """
    try:
        from django.conf import settings
        
        # 使用本地嵌入模型，不需要 API Key
        # 获取知识库信息（如果提供）
        knowledge_base = None
        collection_name = getattr(settings, 'MULTIMODAL_COLLECTION_NAME', 'multimodal_documents')
        if knowledge_base_id and request and request.user.is_authenticated:
            try:
                knowledge_base = KnowledgeBase.objects.get(id=knowledge_base_id, user=request.user)
                collection_name = knowledge_base.collection_name
            except KnowledgeBase.DoesNotExist:
                logger.warning(f"知识库 {knowledge_base_id} 不存在或无权限访问，使用默认集合")
        
        # 使用本地文本编码器（bge-large-zh, 1024维）
        encoder = LocalEmbeddingEncoder(
            model_path=getattr(settings, 'LOCAL_EMBEDDING_MODEL', str(settings.BASE_DIR / 'models' / 'bge-large-zh')),
            chroma_db_path=getattr(settings, 'CHROMA_DB_PATH', './chroma_db'),
            collection_name=collection_name
        )
        
        # 准备分块数据（只处理文本内容）
        chunks_for_encoding = []
        for chunk in chunks:
            content = chunk.get('content', '')
            if content and isinstance(content, str):
                chunks_for_encoding.append({
                    'id': chunk.get('id', len(chunks_for_encoding)),
                    'content': content,
                    'modality_type': 'text',
                    'metadata': {
                        **chunk.get('metadata', {}),
                        'chunker_type': chunker_type,
                        'file_name': file_name
                    }
                })
        
        if not chunks_for_encoding:
            logger.warning("没有可编码的文本内容")
            return None
        
        # 批量编码并存储
        batch_size = getattr(settings, 'ENCODING_BATCH_SIZE', 10)
        encoder.process_and_store(
            chunks=chunks_for_encoding,
            batch_size=batch_size,
            metadatas=None
        )
        
        encoding_stats = {
            'encoded': True,
            'total_encoded': len(chunks_for_encoding),
            'collection_name': encoder.collection_name,
            'model': getattr(encoder, 'model_path', 'unknown'),
            'knowledge_base_id': str(knowledge_base.id) if knowledge_base else None
        }
        logger.info(f"成功编码并存储了 {len(chunks_for_encoding)} 个文本分块到 Chroma (集合: {collection_name})")
        
        return encoding_stats
        
    except Exception as e:
        logger.error(f"文本向量化失败: {e}")
        return {
            'encoded': False,
            'error': str(e)
        }


def process_multimodal_chunker(file_path, file_name, enable_encoding: bool = False, request=None, knowledge_base_id=None, text_chunk_size=1000, text_chunk_overlap=200, min_chars=400, max_chars=800, window_size=4):
    """
    处理多模态分块器
    
    Args:
        file_path: 文件路径
        file_name: 文件名
        enable_encoding: 是否启用多模态编码并存储到Chroma
        request: Django请求对象（用于获取服务器URL）
        knowledge_base_id: 知识库ID（可选）
    """
    from .Spilter.MultimodalSpilter import MultimodalSpilter

    splitter = None
    saved_images = []  # 保存移动到media目录的图片路径
    encoder = None

    try:
        from django.conf import settings
        import uuid
        
        # 创建保存图片的目录
        file_id = str(uuid.uuid4())[:8]
        images_save_dir = os.path.join(settings.EXTRACTED_IMAGES_DIR, file_id)
        os.makedirs(images_save_dir, exist_ok=True)
        
        # 获取知识库信息（如果提供）
        knowledge_base = None
        collection_name = getattr(settings, 'MULTIMODAL_COLLECTION_NAME', 'multimodal_documents')
        if knowledge_base_id and request and request.user.is_authenticated:
            try:
                knowledge_base = KnowledgeBase.objects.get(id=knowledge_base_id, user=request.user)
                collection_name = knowledge_base.collection_name
            except KnowledgeBase.DoesNotExist:
                logger.warning(f"知识库 {knowledge_base_id} 不存在或无权限访问，使用默认集合")
        
        splitter = MultimodalSpilter(
            text_chunk_size=text_chunk_size,
            text_chunk_overlap=text_chunk_overlap,
            extract_images=True,
            use_semantic_splitter=True,
            min_chars=min_chars,
            max_chars=max_chars,
            window_size=window_size,
            smoothing_width=1,
            chunk_size=1000,  # 处理窗口大小，固定值
            pdf_screenshot_pages=True,   # 启用PDF页面截图模式
            pdf_screenshot_dpi=150,      # 设置截图DPI
            docx_screenshot_pages=True   # 启用Word页面截图模式
        )
        
        # 执行分块
        chunks_data = splitter.split_file(file_path)
        
        # 获取服务器基础URL（用于构建完整的图片URL）
        if request:
            base_url = f"{request.scheme}://{request.get_host()}"
        else:
            # 默认使用localhost:8000
            base_url = "http://localhost:8000"
        
        # 转换为API格式，处理图片路径
        chunks = []
        chunks_for_encoding = []  # 用于编码的chunks（包含完整URL或Base64）
        
        for chunk in chunks_data:
            chunk_dict = {
                'id': chunk.id,
                'content': chunk.content,
                'modality_type': chunk.modality_type,
                'metadata': {**chunk.metadata.copy(), 'file_name': file_name}
            }
            
            # 如果是图片，将临时文件移动到可访问的目录
            if chunk.modality_type == 'image':
                image_path = chunk.metadata.get('image_path')
                if image_path and os.path.exists(image_path):
                    try:
                        # 复制图片到media目录
                        image_filename = os.path.basename(image_path)
                        saved_image_path = os.path.join(images_save_dir, image_filename)
                        shutil.copy2(image_path, saved_image_path)
                        
                        # 生成访问URL（相对于EXTRACTED_IMAGES_DIR）
                        relative_path = os.path.relpath(saved_image_path, settings.EXTRACTED_IMAGES_DIR)
                        image_url = f"/api/media/{relative_path.replace(os.sep, '/')}"
                        full_image_url = f"{base_url}{image_url}"
                        
                        # 更新content和metadata
                        chunk_dict['content'] = image_url  # 前端显示用相对URL
                        chunk_dict['metadata']['image_url'] = image_url
                        chunk_dict['metadata']['full_image_url'] = full_image_url  # 编码用完整URL
                        chunk_dict['metadata']['image_path'] = saved_image_path
                        chunk_dict['metadata']['file_id'] = file_id
                        
                        saved_images.append(saved_image_path)
                        
                        # 准备编码用的chunk（使用Base64以避免外网无法访问本地URL）
                        encoding_chunk = chunk_dict.copy()
                        try:
                            base64_image_for_encoding = splitter.image_to_base64(saved_image_path)
                            encoding_chunk['content'] = base64_image_for_encoding
                        except Exception:
                            # 兜底：仍然使用完整URL
                            encoding_chunk['content'] = full_image_url
                        chunks_for_encoding.append(encoding_chunk)
                        
                    except Exception as e:
                        logger.warning(f"无法保存图片 {image_path}: {e}")
                        # 如果保存失败，尝试转换为base64作为备选
                        try:
                            base64_image = splitter.image_to_base64(image_path)
                            chunk_dict['content'] = base64_image
                            chunk_dict['metadata']['is_base64'] = True
                            
                            # 编码用的chunk也使用base64
                            encoding_chunk = chunk_dict.copy()
                            chunks_for_encoding.append(encoding_chunk)
                        except:
                            pass
                else:
                    # 如果没有图片路径，直接使用content（可能是base64）
                    chunks_for_encoding.append(chunk_dict)
            else:
                # 文本块，直接添加
                chunks_for_encoding.append(chunk_dict)
            
            chunks.append(chunk_dict)
        
        # 如果启用编码，使用多模态编码器进行嵌入
        encoding_stats = {}
        if enable_encoding:
            try:
                MultimodalEncoder = _import_multimodal_encoder()
            except ImportError:
                logger.warning("MultimodalEncoder 不可用，跳过编码步骤")
                MultimodalEncoder = None
            if MultimodalEncoder:
                # 检查是否配置了API Key
                api_key = getattr(settings, 'DASHSCOPE_API_KEY', None)
                if not api_key:
                    logger.warning("未配置 DASHSCOPE_API_KEY，跳过编码步骤")
                else:
                    try:
                        # 初始化编码器（使用知识库的集合名称）
                        encoder = MultimodalEncoder(
                            api_key=api_key,
                            model="tongyi-embedding-vision-plus",
                            chroma_db_path=getattr(settings, 'CHROMA_DB_PATH', './chroma_db'),
                            collection_name=collection_name
                        )

                        # 批量编码并存储
                        batch_size = getattr(settings, 'ENCODING_BATCH_SIZE', 10)
                        encoder.process_and_store(
                            chunks=chunks_for_encoding,
                            batch_size=batch_size,
                            metadatas=None
                        )

                        encoding_stats = {
                            'encoded': True,
                            'total_encoded': len(chunks_for_encoding),
                            'collection_name': encoder.collection_name,
                            'knowledge_base_id': str(knowledge_base.id) if knowledge_base else None
                        }
                        logger.info(f"成功编码并存储了 {len(chunks_for_encoding)} 个分块到 Chroma (集合: {collection_name})")
                    except Exception as e:
                        logger.error(f"多模态编码失败: {e}")
                        encoding_stats = {
                            'encoded': False,
                            'error': str(e)
                        }
        
        # 统计信息
        modality_stats = {}
        for chunk in chunks_data:
            mod_type = chunk.modality_type
            modality_stats[mod_type] = modality_stats.get(mod_type, 0) + 1
        
        result = {
            'chunks': chunks,
            'statistics': {
                'total_chunks': len(chunks),
                'chunker_name': '多模态分块器',
                'modality_distribution': modality_stats,
                'file_id': file_id,  # 用于标识这次处理的文件，便于后续清理
                'encoding': encoding_stats
            }
        }
        
        return result
        
    except Exception as e:
        raise Exception(f"多模态分块器处理失败: {str(e)}")
    finally:
        # 清理临时图片文件（但不清理已保存到media的）
        if splitter:
            try:
                splitter.cleanup_temp_images()
            except:
                pass


@csrf_exempt
@require_http_methods(["POST"]) 
def hybrid_qa(request):
    """
    混合检索融合 + 用户画像 的问答接口
    请求参数:
    - question: 文本问题
    - knowledge_base_id: 单个或多个知识库ID（字符串或字符串数组）
    - session_id: 会话ID（可选）
    - top_k: 返回文档数量（默认5）
    - is_strict: 是否严格仅基于知识库回答（默认False）
    - age, is_employee, frequency: 用户画像
    - history: 对话历史 [{role, content}]（可选）
    """
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'error': '请先登录'}, status=401)
    try:
        data = json.loads(request.body or '{}')
        question = (data.get('question') or '').strip()
        top_k = int(data.get('top_k', 5))
        is_strict = bool(data.get('is_strict', False))
        debug = bool(data.get('debug', False))
        age = _resolve_profile_age(request, data)
        is_employee = _resolve_profile_is_employee(request, data)
        frequency = data.get('frequency')
        history = data.get('history') or []
        session_id = data.get('session_id')
        # ✅ 前端未传 history 时，从数据库自动回读会话历史
        if session_id and not history:
            history = _load_history_from_db(session_id, request.user)
        kb_ids = data.get('knowledge_base_id')

        if not question:
            return JsonResponse({'success': False, 'error': '问题不能为空'}, status=400)

        # API Key
        api_key = getattr(settings, 'DASHSCOPE_API_KEY', None)
        if not api_key:
            return JsonResponse({'success': False, 'error': '未配置 DASHSCOPE_API_KEY'}, status=500)

        # 解析知识库集合
        collection_names = []
        kb_instance = None
        if isinstance(kb_ids, list):
            kb_id_list = kb_ids
        elif isinstance(kb_ids, str) and kb_ids:
            kb_id_list = [kb_ids]
        else:
            kb_id_list = []

        if kb_id_list:
            for kid in kb_id_list:
                try:
                    kb = KnowledgeBase.objects.get(id=kid)
                    collection_names.append(kb.collection_name)
                    if not kb_instance:
                        kb_instance = kb
                except KnowledgeBase.DoesNotExist:
                    return JsonResponse({'success': False, 'error': f'知识库不存在或无权限访问: {kid}'}, status=404)
        else:
            # 默认使用当前用户全部知识库
            user_kbs = KnowledgeBase.objects.filter(status='active')
            collection_names = [kb.collection_name for kb in user_kbs]
            if not collection_names:
                return JsonResponse({'success': False, 'error': '您还没有创建任何知识库'}, status=400)

        # 会话
        is_new_session = False
        if session_id:
            try:
                chat_session = ChatSession.objects.get(id=session_id, user=request.user)
                if chat_session.title == '新对话' and not chat_session.messages.exists():
                    is_new_session = True
            except ChatSession.DoesNotExist:
                return JsonResponse({'success': False, 'error': '会话不存在或无权限访问'}, status=404)
        else:
            title = question[:20] + ('...' if len(question) > 20 else '')
            chat_session = ChatSession.objects.create(user=request.user, title=title, knowledge_base=kb_instance)
            is_new_session = True

        # 保存用户消息
        ChatMessage.objects.create(session=chat_session, role='user', content=question)


        # 获取 RAGPipeline 单例（统一工厂）
        from ..rag import get_rag_service
        chroma_path = getattr(settings, 'CHROMA_DB_PATH', './chroma_db')
        rag = get_rag_service(api_key=api_key, model_name="qwen3-omni-flash", chroma_db_path=chroma_path)
        result = rag.run(
            question=question,
            collection_names=collection_names,
            history=history,
            age=age,
            is_employee=is_employee,
            frequency=frequency,
            is_strict=is_strict,
            top_k=top_k,
            debug=debug,
        )

        assistant_answer = result.get('answer', '')
        # 保存助手消息（附带来源）
        sources = []
        flow_references = []
        for d in result.get('docs', []):
            md = d.get('metadata') or {}
            if md.get('doc_type') == 'flow_matter':
                flow_references.append({
                    'matter_title': md.get('matter_title') or '未命名事项',
                    'summary': md.get('summary_text') or (d.get('content') or '')[:120],
                    'svg_url': md.get('svg_url') or '',
                    'png_url': md.get('png_url') or '',
                })
                continue

            sources.append({
                'content': d.get('content', ''),
                'file_name': md.get('file_name') or md.get('source') or md.get('source_file') or '未知',
                'chunk_id': md.get('chunk_id') or '',
                'score_fused': md.get('_s_fused') or md.get('_rrf_score'),
                'score_ce': md.get('_s_ce_norm'),
            })

        images = result.get('images', [])

        # 生成引导式追问
        suggested_next_questions = []
        is_refused = (result.get('refusal') or {}).get('is_refused')
        if not is_refused and assistant_answer.strip():
            try:
                source_files = list(set(
                    (d.get('metadata') or {}).get('file_name', '')
                    for d in result.get('docs', [])
                    if (d.get('metadata') or {}).get('modality_type', 'text') == 'text'
                ))
                sources_summary = '、'.join(source_files[:5]) if source_files else ''
                suggested_next_questions = rag.builder.generate_suggested_next_questions(
                    question=question,
                    answer=assistant_answer,
                    sources_summary=sources_summary,
                    is_refused=False,
                )
            except Exception:
                pass

        assistant_msg = ChatMessage.objects.create(
            session=chat_session,
            role='assistant',
            content=assistant_answer,
            sources=sources or None,
            images=images or None,
            trace_id=result.get('trace_id', None),
            citations=result.get('citations', None),
            retrieval_hits=result.get('retrieval_hits', None),
            evidence_spans=result.get('evidence_spans', None),
            retrieval_stats=result.get('retrieval_stats', None),
            refusal=result.get('refusal', None),
            suggested_next_questions=suggested_next_questions or None,
        )

        # 新建会话则生成标题
        try:
            if is_new_session:
                new_title = rag.builder.generate_title(question, assistant_answer, api_key)
                if new_title:
                    chat_session.title = new_title[:50]
                    chat_session.save(update_fields=['title', 'updated_at'])
        except Exception:
            pass

        return JsonResponse({
            'success': True,
            'answer': assistant_answer,
            'sources': sources,
            'images': images,
            'flow_references': flow_references,
            'session_id': str(chat_session.id),
            'message_id': assistant_msg.id,
            'suggested_next_questions': suggested_next_questions,
            'metadata': {
                'collections': collection_names,
                'used_template': result.get('used_template'),
                'top_k': top_k,
                'strict': is_strict,
                **({'debug': result.get('debug')} if debug else {}),
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': '无效的JSON数据'}, status=400)
    except Exception as e:
        logger.error(f"混合检索问答失败: {e}")
        return JsonResponse({'success': False, 'error': f'问答失败: {e}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def multimodal_qa(request):
    """
    多模态问答API接口
    
    请求参数:
    - question: 用户问题（文本）
    - knowledge_base_id: 知识库ID（可选，如果不提供则查询用户的所有知识库）
    - session_id: 会话ID（可选，如未提供则自动创建）
    - top_k: 返回的检索结果数量（默认5）
    - include_images: 是否在结果中包含图片（默认True）
    """
    if not request.user.is_authenticated:
        return JsonResponse({
            'success': False,
            'error': '请先登录'
        }, status=401)
    
    try:
        data = json.loads(request.body)
        question = data.get('question', '').strip()
        knowledge_base_id = data.get('knowledge_base_id', None)
        session_id = data.get('session_id')
        top_k = int(data.get('top_k', 5))
        include_images = data.get('include_images', True)
        
        if not question:
            return JsonResponse({
                'success': False,
                'error': '问题不能为空'
            }, status=400)
        
        # 检查是否配置了API Key
        api_key = getattr(settings, 'DASHSCOPE_API_KEY', None)
        if not api_key:
            return JsonResponse({
                'success': False,
                'error': '未配置 DASHSCOPE_API_KEY'
            }, status=500)
        
        # 获取要查询的集合名称列表，并解析kb实例
        collection_names = []
        kb_instance = None
        if knowledge_base_id:
            try:
                kb_instance = KnowledgeBase.objects.get(id=knowledge_base_id)
                collection_names = [kb_instance.collection_name]
            except KnowledgeBase.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': '知识库不存在或无权限访问'
                }, status=404)
        else:
            user_knowledge_bases = KnowledgeBase.objects.filter(status='active')
            collection_names = [kb.collection_name for kb in user_knowledge_bases]
            if not collection_names:
                return JsonResponse({
                    'success': False,
                    'error': '您还没有创建任何知识库，请先创建知识库并上传文档'
                }, status=400)
        
        # 如果没有提供session，自动创建会话（标题取首句）
        chat_session = None
        is_new_session = False
        if session_id:
            try:
                chat_session = ChatSession.objects.get(id=session_id, user=request.user)
                if chat_session.title == '新对话' and not chat_session.messages.exists():
                    is_new_session = True
            except ChatSession.DoesNotExist:
                return JsonResponse({'success': False, 'error': '会话不存在或无权限访问'}, status=404)
        else:
            title = question[:20] + ('...' if len(question) > 20 else '')
            chat_session = ChatSession.objects.create(
                user=request.user,
                title=title,
                knowledge_base=kb_instance
            )
            is_new_session = True
        
        # 保存用户消息
        ChatMessage.objects.create(
            session=chat_session,
            role='user',
            content=question
        )
        
        # 初始化RAG服务并生成答案
        rag_service = RAGService(
            api_key=api_key,
            model_name="qwen3-omni-flash",
            chroma_db_path=getattr(settings, 'CHROMA_DB_PATH', './chroma_db')
        )
        result = rag_service.answer_question(
            question=question,
            collection_names=collection_names,
            top_k=top_k,
            include_images=include_images
        )
        
        # 处理图片URL（转换为完整URL）
        base_url = f"{request.scheme}://{request.get_host()}"
        for img in result.get('images', []):
            if img['url'] and not img['url'].startswith('http'):
                img['url'] = f"{base_url}{img['url']}"
        
        # 保存助手消息（携带sources和images）
        assistant_answer = result.get('answer', '')
        ChatMessage.objects.create(
            session=chat_session,
            role='assistant',
            content=assistant_answer,
            sources=result.get('sources', None),
            images=result.get('images', None)
        )

        # 新对话首次问答后，自动生成并更新会话标题（仅当是新建会话且标题仍为默认占位）
        try:
            if is_new_session:
                rag_for_title = RAGService(
                    api_key=api_key,
                    model_name="qwen3-omni-flash",
                    chroma_db_path=getattr(settings, 'CHROMA_DB_PATH', './chroma_db')
                )
                new_title = rag_for_title.generate_title(question, assistant_answer)
                if new_title and new_title.strip():
                    chat_session.title = new_title.strip()
                    chat_session.save(update_fields=['title', 'updated_at'])
        except Exception as e:
            logger.warning(f"自动生成标题失败: {e}")
        
        return JsonResponse({
            'success': True,
            'answer': result['answer'],
            'sources': result['sources'],
            'images': result['images'],
            'session_id': str(chat_session.id),
            'metadata': {
                **result['metadata'],
                'knowledge_base_id': knowledge_base_id if knowledge_base_id else 'all',
            }
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': '无效的JSON数据'
        }, status=400)
    except Exception as e:
        logger.error(f"多模态问答失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return JsonResponse({
            'success': False,
            'error': f'问答失败: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_chunker_info(request):
    """获取分块器信息"""
    chunkers_info = {
        # 基础切分方式
        'by_length': {
            'name': '按长度切分',
            'description': '按固定字符长度切分文本，简单快速',
            'supported_formats': ['.txt', '.pdf', '.docx'],
            'features': ['固定长度', '可设置重叠', '处理快速'],
            'category': 'basic',
            'params': {
                'chunk_size': {'type': 'number', 'default': 1000, 'min': 100, 'max': 5000, 'label': '块大小（字符）'},
                'chunk_overlap': {'type': 'number', 'default': 200, 'min': 0, 'max': 500, 'label': '重叠大小（字符）'}
            }
        },
        'by_punctuation': {
            'name': '按标点符号切分',
            'description': '在标点符号处切分，保持句子完整性',
            'supported_formats': ['.txt', '.pdf', '.docx'],
            'features': ['句子完整', '标点识别', '上下文保留'],
            'category': 'basic',
            'params': {
                'chunk_size': {'type': 'number', 'default': 1000, 'min': 100, 'max': 5000, 'label': '目标块大小（字符）'},
                'chunk_overlap': {'type': 'number', 'default': 200, 'min': 0, 'max': 500, 'label': '重叠大小（字符）'}
            }
        },
        'recursive': {
            'name': '智能递归切分',
            'description': '按分隔符优先级递归切分，智能选择最佳分割点',
            'supported_formats': ['.txt', '.pdf', '.docx'],
            'features': ['递归切分', '智能分隔', '结构保持'],
            'category': 'basic',
            'params': {
                'chunk_size': {'type': 'number', 'default': 1000, 'min': 100, 'max': 5000, 'label': '目标块大小（字符）'},
                'chunk_overlap': {'type': 'number', 'default': 200, 'min': 0, 'max': 500, 'label': '重叠大小（字符）'}
            }
        },
        'by_page': {
            'name': '按页切分',
            'description': '按文档页面切分，保留页面结构',
            'supported_formats': ['.pdf', '.docx'],
            'features': ['页面保持', '结构完整', '简单直观'],
            'category': 'basic',
            'params': {}
        },
        # 进阶切分方式
        'semantic': {
            'name': '语义分块器',
            'description': '基于语义相似度的智能分块',
            'supported_formats': ['.txt', '.pdf', '.docx'],
            'features': ['语义分析', '智能边界', '上下文保持'],
            'category': 'advanced',
            'params': {
                'min_chars': {'type': 'number', 'default': 400, 'min': 100, 'max': 2000, 'label': '最小字符数'},
                'max_chars': {'type': 'number', 'default': 800, 'min': 200, 'max': 3000, 'label': '最大字符数'},
                'window_size': {'type': 'number', 'default': 4, 'min': 2, 'max': 10, 'label': '窗口大小'}
            }
        },
        'multimodal': {
            'name': '多模态分块器',
            'description': '支持文本、图片、视频等多种模态的分块处理',
            'supported_formats': ['.txt', '.pdf', '.docx', '.jpg', '.png', '.jpeg', '.gif', '.mp4', '.avi', '.mov'],
            'features': ['多模态支持', '图片提取', '视频处理', '文本分块'],
            'category': 'advanced',
            'params': {
                'text_chunk_size': {'type': 'number', 'default': 1000, 'min': 500, 'max': 3000, 'label': '文本块大小'},
                'text_chunk_overlap': {'type': 'number', 'default': 200, 'min': 0, 'max': 500, 'label': '文本块重叠'},
                'min_chars': {'type': 'number', 'default': 400, 'min': 100, 'max': 2000, 'label': '最小字符数'},
                'max_chars': {'type': 'number', 'default': 800, 'min': 200, 'max': 3000, 'label': '最大字符数'},
                'window_size': {'type': 'number', 'default': 4, 'min': 2, 'max': 10, 'label': '窗口大小'}
            }
        },
        # 专用切分方式
        'qa': {
            'name': '问答分块器',
            'description': '专门处理问答类文档，提取Q/A对',
            'supported_formats': ['.txt', '.pdf', '.docx'],
            'features': ['Q/A提取', '语义保持', '重叠处理'],
            'category': 'specialized'
        },
        'law': {
            'name': '法律法规分块器',
            'description': '按"条"进行分块，适用于法律法规文档',
            'supported_formats': ['.txt', '.pdf', '.docx'],
            'features': ['条文识别', '章节保持', '元数据提取'],
            'category': 'specialized'
        },
        'policy': {
            'name': '政策公告分块器',
            'description': '基于一级标题分块，适用于政策公告',
            'supported_formats': ['.txt', '.pdf', '.docx'],
            'features': ['标题识别', '表格处理', '时间提取'],
            'category': 'specialized'
        },
        'table': {
            'name': '表格分块器',
            'description': '专门处理表格数据，按行分块',
            'supported_formats': ['.pdf', '.docx', '.xlsx', '.xls'],
            'features': ['表头保持', '行分块', '数据清洗'],
            'category': 'specialized'
        }
    }
    
    return JsonResponse({
        'success': True,
        'chunkers': chunkers_info
    })


@require_http_methods(["GET"])
def health_check(request):
    """健康检查接口"""
    return JsonResponse({
        'status': 'healthy',
        'message': '分块器API服务正常运行'
    })


@require_http_methods(["GET"])
def serve_extracted_image(request, file_path):
    """提供提取的图片文件访问"""
    try:
        from django.conf import settings
        
        # 构建完整路径
        full_path = os.path.join(settings.EXTRACTED_IMAGES_DIR, file_path)
        
        # 安全检查：确保路径在允许的目录内
        full_path = os.path.normpath(full_path)
        allowed_dir = os.path.normpath(settings.EXTRACTED_IMAGES_DIR)
        if not full_path.startswith(allowed_dir):
            raise Http404("文件路径不安全")
        
        if not os.path.exists(full_path):
            raise Http404("图片文件不存在")
        
        # 读取文件
        with open(full_path, 'rb') as f:
            image_data = f.read()
        
        # 确定Content-Type
        ext = os.path.splitext(full_path)[1].lower()
        content_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp',
            '.webp': 'image/webp'
        }
        content_type = content_types.get(ext, 'image/jpeg')
        
        response = HttpResponse(image_data, content_type=content_type)
        response['Cache-Control'] = 'public, max-age=3600'  # 缓存1小时
        return response
        
    except Http404:
        raise
    except Exception as e:
        logger.error(f"提供图片文件失败: {e}")
        raise Http404("无法提供图片文件")

