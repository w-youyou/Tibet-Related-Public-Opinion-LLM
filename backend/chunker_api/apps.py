import os
import logging
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class ChunkerApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chunker_api'

    def ready(self):
        # 仅在主进程中执行预热，避免 autoreload 模式下重复执行
        # `RUN_MAIN` 是 Django runserver 的标准环境变量
        if os.environ.get('RUN_MAIN') != 'true':
            return

        # 通过环境变量控制是否启用预热
        warmup_enabled = os.getenv('RAG_WARMUP_ENABLED', 'false').lower() in ('true', '1', 'yes')
        if not warmup_enabled:
            logger.info("[WARMUP] RAG_WARMUP_ENABLED 未开启，跳过 RAG 服务预热。")
            return

        logger.info("[WARMUP] RAG 服务预热已启动...")
        try:
            # 读取必要的配置
            api_key = getattr(settings, 'DASHSCOPE_API_KEY', None)
            chroma_path = getattr(settings, 'CHROMA_DB_PATH', './chroma_db')

            if not api_key:
                logger.warning("[WARMUP] 缺少 DASHSCOPE_API_KEY，无法预热 RAG 服务。")
                return

            # 通过 get_rag_service() 创建/获取 RAGPipeline 单例
            from .rag import get_rag_service
            logger.info("[WARMUP] 正在创建 RAGPipeline 实例...")
            get_rag_service(api_key=api_key, chroma_db_path=chroma_path)
            logger.info("[WARMUP] RAGPipeline 实例已创建。")

            # 可选：如果需要，可以在这里预加载 BM25/Chroma 索引
            # rag_instance = get_rag_service(api_key=api_key, chroma_db_path=chroma_path)
            # rag_instance._get_hybrid_retriever('your_default_collection_name', top_k=5)

            logger.info("[WARMUP] RAG 服务预热完成。")

        except Exception as e:
            logger.error(f"[WARMUP] RAG 服务预热失败: {e}", exc_info=True)
