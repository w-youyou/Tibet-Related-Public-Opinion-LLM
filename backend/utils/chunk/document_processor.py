import os
import json
import shutil
import logging
import tempfile
import traceback
from django.conf import settings

# 导入分块器相关依赖
from utils.chunk.QAspilter import run as qa_run
from utils.chunk.LawSpilter import LawSpilter
from utils.chunk.optimized_semantic_spilter import split_text_to_chunks, split_docx_to_chunks, split_pdf_to_chunks
from utils.chunk.PolicyAnnouncementSpilter import PolicyAnnouncementSpilter
from utils.chunk.TableSpilter import TableSpilter
from utils.chunk.MultimodalSpilter import MultimodalSpilter
from utils.chunk.BasicSpilter import BasicSpilter

import uuid
from chunker_api.models import KnowledgeBase

logger = logging.getLogger(__name__)

# 尝试导入多模态编码器
try:
    from utils.chunk.MultimodalEncoder import MultimodalEncoder
    from utils.chunk.LocalEmbeddingEncoder import LocalEmbeddingEncoder

    ENCODER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"编码器导入失败: {e}")
    ENCODER_AVAILABLE = False
    logger.warning("MultimodalEncoder 未导入，编码功能将不可用")

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


def process_qa_chunker(file_path, file_name):
    """处理问答分块器"""
    try:
        # 创建临时输出文件
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.jsonl') as output_file:
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
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        chunk_size = 1000  # 处理窗口大小，固定值

        if file_ext == '.pdf':
            chunks = split_pdf_to_chunks(file_path, min_chars=min_chars, max_chars=max_chars, window_size=window_size,
                                         smoothing_width=smoothing_width, chunk_size=chunk_size)
        elif file_ext == '.docx':
            chunks = split_docx_to_chunks(file_path, min_chars=min_chars, max_chars=max_chars, window_size=window_size,
                                          smoothing_width=smoothing_width, chunk_size=chunk_size)
        elif file_ext == '.doc':
            # 对于.doc文件，先读取内容再分块
            text_content = read_doc_file(file_path)
            chunks = split_text_to_chunks(text_content, min_chars=min_chars, max_chars=max_chars,
                                          window_size=window_size, smoothing_width=smoothing_width,
                                          chunk_size=chunk_size)
        else:
            chunks = split_text_to_chunks(open(file_path, 'r', encoding='utf-8').read(), min_chars=min_chars,
                                          max_chars=max_chars, window_size=window_size, smoothing_width=smoothing_width,
                                          chunk_size=chunk_size)

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
                'avg_chunk_size': sum(len(c['content']) for c in result_chunks) // len(
                    result_chunks) if result_chunks else 0
            }
        }

    except Exception as e:
        raise Exception(f"语义分块器处理失败: {str(e)}")


def process_policy_chunker(file_path, file_name):
    """处理政策公告分块器"""
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


def process_text_embedding(chunks, chunker_type, file_name, knowledge_base_id=None, request=None, version_id=None):
    """
    处理纯文本数据的向量化（统一使用多模态编码器）

    Args:
        chunks: 分块列表
        chunker_type: 分块器类型
        file_name: 文件名
        knowledge_base_id: 知识库ID（可选）
        request: Django请求对象（可选）
        version_id: 文档版本ID（可选，用于版本管理）

    Returns:
        编码统计信息字典
    """
    if not ENCODER_AVAILABLE:
        logger.warning("MultimodalEncoder 不可用，跳过文本向量化")
        return None

    try:
        from django.conf import settings

        # 检查是否配置了API Key
        api_key = getattr(settings, 'DASHSCOPE_API_KEY', None)
        print(api_key)
        if not api_key:
            logger.warning("未配置 DASHSCOPE_API_KEY，跳过文本向量化")
            return None

        # 获取知识库信息（如果提供）
        knowledge_base = None
        collection_name = getattr(settings, 'MULTIMODAL_COLLECTION_NAME', 'multimodal_documents')
        if knowledge_base_id:
            try:
                knowledge_base = KnowledgeBase.objects.get(id=knowledge_base_id)
                collection_name = knowledge_base.collection_name
            except KnowledgeBase.DoesNotExist:
                logger.warning(f"知识库 {knowledge_base_id} 不存在，使用默认集合")

        # 获取本地嵌入模型路径
        local_model_path = getattr(settings, 'LOCAL_EMBEDDING_MODEL', 'G:\\models\\bge-large-zh')
        
        # 统一使用本地文本编码器
        encoder = LocalEmbeddingEncoder(
            model_path=local_model_path,
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
                        'file_name': file_name,
                        **({'version_id': version_id} if version_id else {})
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
            'model': getattr(encoder, 'model', getattr(encoder, 'model_path', 'unknown')),
            'knowledge_base_id': str(knowledge_base.id) if knowledge_base else None
        }
        logger.info(f"成功编码并存储了 {len(chunks_for_encoding)} 个文本分块到 Chroma (集合: {collection_name})")

        return encoding_stats

    except Exception as e:
        logger.error(f"文本向量化失败: {e}")
        # Fallback: Insert chunks into ChromaDB without embeddings so they can still be previewed
        try:
            if hasattr(encoder, 'chroma_client') and encoder.chroma_client:
                client = encoder.chroma_client
            else:
                import chromadb
                from chromadb.config import Settings as ChromaSettings
                client = chromadb.PersistentClient(
                    path=getattr(settings, 'CHROMA_DB_PATH', './chroma_db'),
                    settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True)
                )
            collection = client.get_or_create_collection(collection_name)
            
            ids = [str(c['id']) for c in chunks_for_encoding]
            documents = [c['content'] for c in chunks_for_encoding]
            metadatas = [c['metadata'] for c in chunks_for_encoding]
            
            collection.add(ids=ids, documents=documents, metadatas=metadatas)
            logger.info(f"Fallback: 成功将 {len(chunks_for_encoding)} 个无向量文本分块存入 Chroma (集合: {collection_name})")
        except Exception as fallback_e:
            logger.error(f"Fallback 存储也失败: {fallback_e}")
            
        return {
            'encoded': False,
            'error': str(e)
        }


def process_multimodal_chunker(file_path, file_name, enable_encoding: bool = False, request=None,
                               knowledge_base_id=None, text_chunk_size=1000, text_chunk_overlap=200, min_chars=400,
                               max_chars=800, window_size=4, version_id=None):
    """
    处理多模态分块器

    Args:
        file_path: 文件路径
        file_name: 文件名
        enable_encoding: 是否启用多模态编码并存储到Chroma
        request: Django请求对象（用于获取服务器URL）
        knowledge_base_id: 知识库ID（可选）
        version_id: 文档版本ID（可选，用于版本管理）
    """
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
        if knowledge_base_id:
            try:
                knowledge_base = KnowledgeBase.objects.get(id=knowledge_base_id)
                collection_name = knowledge_base.collection_name
            except KnowledgeBase.DoesNotExist:
                logger.warning(f"知识库 {knowledge_base_id} 不存在，使用默认集合")

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
            pdf_screenshot_pages=True,  # 启用PDF页面截图模式
            pdf_screenshot_dpi=150,  # 设置截图DPI
            docx_screenshot_pages=True  # 启用Word页面截图模式
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
                'metadata': {
                    **chunk.metadata.copy(), 
                    'file_name': file_name,
                    **({'version_id': version_id} if version_id else {})
                }
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
        if enable_encoding and ENCODER_AVAILABLE:
            try:
                # 检查是否配置了API Key
                api_key = getattr(settings, 'DASHSCOPE_API_KEY', None)
                if not api_key:
                    logger.warning("未配置 DASHSCOPE_API_KEY，跳过编码步骤")
                else:
                    # 获取本地嵌入模型路径
                    local_model_path = getattr(settings, 'LOCAL_EMBEDDING_MODEL', 'G:\\models\\bge-large-zh')
                    
                    # 初始化本地编码器
                    encoder = LocalEmbeddingEncoder(
                        model_path=local_model_path,
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
                    logger.info(
                        f"成功编码并存储了 {len(chunks_for_encoding)} 个分块到 Chroma (集合: {collection_name})")

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
