import os
import shutil
import logging
from django.conf import settings
from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_core.documents import Document as LangchainDocument
from chunker_api.models import Document, DocumentVersion

logger = logging.getLogger(__name__)

# 尝试导入多模态编码器依赖
try:
    from utils.chunk.MultimodalEncoder import MultimodalEncoder
    ENCODER_AVAILABLE = True
except ImportError:
    ENCODER_AVAILABLE = False

from utils.chunk.document_processor import (
    process_qa_chunker, process_law_chunker, process_basic_chunker,
    process_semantic_chunker, process_policy_chunker, process_table_chunker,
    process_multimodal_chunker, process_text_embedding
)

def get_chroma_store(collection_name, chroma_db_path=None):
    """
    获取 ChromaDB 存储对象
    """
    if chroma_db_path is None:
        chroma_db_path = getattr(settings, 'CHROMA_DB_PATH', './chroma_db')
        
    try:
        from chunker_api.rag_service import TongyiEmbeddings
        api_key = getattr(settings, 'DASHSCOPE_API_KEY', '')
        embeddings = TongyiEmbeddings(api_key=api_key)
    except Exception as e:
        logger.warning(f"无法初始化通义向量化引擎，降级为 None: {e}")
        embeddings = None
        
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=chroma_db_path,
        client_settings=ChromaSettings(
            is_persistent=True,
            anonymized_telemetry=False,
            allow_reset=True
        )
    )

def clear_bm25_cache(collection_name, chroma_db_path=None):
    """
    彻底清空 BM25 的本地索引文件以强推下一次查询重新构建，并清空 RAG 内存缓存
    """
    if chroma_db_path is None:
        chroma_db_path = getattr(settings, 'CHROMA_DB_PATH', './chroma_db')
        
    bm25_dir = os.path.join(chroma_db_path, 'bm25', collection_name)
    if os.path.exists(bm25_dir):
        try:
            shutil.rmtree(bm25_dir)
            logger.info(f"SUCCESS: 已清空 {collection_name} 的 BM25 索引缓存目录")
        except Exception as e:
            logger.error(f"清空 BM25 索引目录失败: {e}")
            
    # 同步清理内存中缓存的 RAGPipeline 和 RetrievalEngine 实例
    try:
        from chunker_api.rag.rag_factory import invalidate_rag_service
        invalidate_rag_service()
        logger.info(f"SUCCESS: 已清空 RAG 内存缓存，将在下次请求时重建 Retriever")
    except Exception as e:
        logger.error(f"清空 RAG 内存缓存失败: {e}")

def delete_document_chunks(collection_name, file_name, chroma_db_path=None):
    """
    从指定 Chroma 集合中彻底删除对应文件名的所有分块，并清理 BM25 缓存
    """
    try:
        store = get_chroma_store(collection_name, chroma_db_path)
        all_docs = store._collection.get(include=["metadatas"])
        
        # 兼容多种元数据命名规范
        delete_ids = []
        for i, meta in zip(all_docs.get("ids", []) or [], all_docs.get("metadatas", []) or []):
            if meta:
                meta_file = meta.get("file_name") or meta.get("source") or meta.get("source_file")
                if meta_file == file_name:
                    delete_ids.append(i)
                    
        if delete_ids:
            store._collection.delete(ids=delete_ids)
            logger.info(f"SUCCESS: 已从 Chroma 集合 {collection_name} 中删除 {len(delete_ids)} 个属于 {file_name} 的分块")
        else:
            logger.info(f"INFO: Chroma 集合 {collection_name} 中未找到属于 {file_name} 的分块")
            
        # 清理 BM25 缓存，确保下次问答时重新加载 Chroma 最新数据重建倒排索引
        clear_bm25_cache(collection_name, chroma_db_path)
        return len(delete_ids)
    except Exception as e:
        logger.error(f"从 Chroma 中删除文档 {file_name} 失败: {e}")
        return 0

def set_document_chunks_active_status(collection_name, file_name, is_active: bool, chroma_db_path=None):
    """
    修改指定文档的所有分块的 is_active 状态（逻辑删除/恢复）
    """
    try:
        store = get_chroma_store(collection_name, chroma_db_path)
        all_docs = store._collection.get(include=["metadatas"])
        
        update_ids = []
        update_metadatas = []
        for i, meta in zip(all_docs.get("ids", []) or [], all_docs.get("metadatas", []) or []):
            if meta:
                meta_file = meta.get("file_name") or meta.get("source") or meta.get("source_file")
                if meta_file == file_name:
                    update_ids.append(i)
                    meta['is_active'] = is_active
                    update_metadatas.append(meta)
                    
        if update_ids:
            store._collection.update(ids=update_ids, metadatas=update_metadatas)
            logger.info(f"SUCCESS: 已将 Chroma 集合 {collection_name} 中 {len(update_ids)} 个属于 {file_name} 的分块状态置为 is_active={is_active}")
        else:
            logger.info(f"INFO: Chroma 集合 {collection_name} 中未找到属于 {file_name} 的分块，无法更新状态")
            
        # 清理 BM25 缓存以重新构建倒排索引
        clear_bm25_cache(collection_name, chroma_db_path)
        return len(update_ids)
    except Exception as e:
        logger.error(f"修改文档 {file_name} 的分块状态失败: {e}")
        return 0

def set_version_active_status(collection_name, file_name, active_version_id: str, chroma_db_path=None):
    """
    文档版本切换：遍历指定文档的所有分块，仅激活属于指定 version_id 的分块，其他设为禁用
    实现零延迟秒级回滚
    """
    try:
        store = get_chroma_store(collection_name, chroma_db_path)
        all_docs = store._collection.get(include=["metadatas"])
        
        update_ids = []
        update_metadatas = []
        for i, meta in zip(all_docs.get("ids", []) or [], all_docs.get("metadatas", []) or []):
            if meta:
                meta_file = meta.get("file_name") or meta.get("source") or meta.get("source_file")
                if meta_file == file_name:
                    chunk_version_id = str(meta.get("version_id", ""))
                    # 只有属于目标版本的 chunk 才设为 True
                    is_active = (chunk_version_id == str(active_version_id))
                    
                    # 避免不必要的更新（如果状态已经正确）
                    if meta.get('is_active') != is_active:
                        update_ids.append(i)
                        meta['is_active'] = is_active
                        update_metadatas.append(meta)
                    
        if update_ids:
            store._collection.update(ids=update_ids, metadatas=update_metadatas)
            logger.info(f"SUCCESS: 已瞬间切换 {file_name} 的 active 版本至 {active_version_id} (更新了 {len(update_ids)} 个分块状态)")
        else:
            logger.info(f"INFO: {file_name} 状态已经是最新，无需切换")
            
        clear_bm25_cache(collection_name, chroma_db_path)
        return len(update_ids)
    except Exception as e:
        logger.error(f"版本状态切换失败: {e}")
        return 0


def index_document_version(collection_name, document_version, request=None):
    """
    解析并对文档的某一物理版本进行分块与向量化，写入 ChromaDB 并计算分块数
    """
    file_path = document_version.file_path
    file_name = document_version.document.name
    chunker_type = document_version.chunker_type
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"物理文档文件不存在: {file_path}")
        
    logger.info(f"开始解析文档版本 {file_name} v{document_version.version_number}，采用分块策略: {chunker_type}")
    
    # 不再在此处粗暴清理旧版本数据，以便保留历史版本实现 O(1) 切换
    # delete_document_chunks(collection_name, file_name)
    
    # 2. 根据分块器解析物理文件
    result = None
    if chunker_type == 'by_length':
        result = process_basic_chunker(file_path, file_name, 'by_length', 1000, 200)
    elif chunker_type == 'by_punctuation':
        result = process_basic_chunker(file_path, file_name, 'by_punctuation', 1000, 200)
    elif chunker_type == 'recursive':
        result = process_basic_chunker(file_path, file_name, 'recursive', 1000, 200)
    elif chunker_type == 'by_page':
        result = process_basic_chunker(file_path, file_name, 'by_page')
    elif chunker_type == 'qa':
        result = process_qa_chunker(file_path, file_name)
    elif chunker_type == 'law':
        result = process_law_chunker(file_path, file_name)
    elif chunker_type == 'semantic':
        result = process_semantic_chunker(file_path, file_name, 400, 800, 4)
    elif chunker_type == 'policy':
        result = process_policy_chunker(file_path, file_name)
    elif chunker_type == 'table':
        result = process_table_chunker(file_path, file_name)
    elif chunker_type == 'multimodal':
        result = process_multimodal_chunker(
            file_path, file_name, 
            enable_encoding=True, 
            request=request,
            knowledge_base_id=str(document_version.document.knowledge_base.id),
            version_id=str(document_version.id)
        )
    else:
        raise ValueError(f"不支持的分块器类型: {chunker_type}")
        
    if not result or 'chunks' not in result:
        raise RuntimeError("分块解析未生成有效分块数据")
        
    chunks = result['chunks']
    
    # 3. 如果是非多模态分块器，统一进行文本向量化
    embedding_stats = None
    if chunker_type != 'multimodal':
        # 手动注入知识库 ID 以便于 process_text_embedding 正确选定 Chroma Collection
        embedding_stats = process_text_embedding(
            chunks=chunks,
            chunker_type=chunker_type,
            file_name=file_name,
            knowledge_base_id=str(document_version.document.knowledge_base.id),
            request=request,
            version_id=str(document_version.id)
        )
        
    # 4. 更新数据库中对应的版本记录分块统计
    document_version.chunk_count = len(chunks)
    if chunker_type == 'multimodal' and 'statistics' in result:
        enc_stats = result['statistics'].get('encoding', {}) or {}
        document_version.embedding_count = enc_stats.get('total_encoded', len(chunks))
    elif embedding_stats and embedding_stats.get('encoded'):
        document_version.embedding_count = embedding_stats.get('total_encoded', len(chunks))
    else:
        document_version.embedding_count = len(chunks)
        
    document_version.save(update_fields=['chunk_count', 'embedding_count'])
    
    # 5. 清理 BM25 缓存以在下次搜索触发时重新生成包含此新文件在内的索引
    clear_bm25_cache(collection_name)
    logger.info(f"SUCCESS: 文档 {file_name} v{document_version.version_number} 索引构建完成。分块数: {document_version.chunk_count}, 向量数: {document_version.embedding_count}")
    
    return chunks
