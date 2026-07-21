"""
RAGPipeline — 混合检索问答流程编排。

将 QuestionRouter、RetrievalEngine、AnswerBuilder 三个子模块串联，
实现与 RAGService.smart_answer_hybrid() 完全相同的 RAG v1 输出协议。

这是一个纯重构，不改动任何行为。
"""

import logging
import os
import time
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional

from django.conf import settings

from . import retrieval_engine
from .question_router import QuestionRouter
from .answer_builder import AnswerBuilder
from ..llm_service import get_llm_service

logger = logging.getLogger(__name__)


class RAGPipeline:
    """混合检索 + 画像模板回答流程编排器。

    提取自 RAGService.smart_answer_hybrid()，使用 QuestionRouter、
    RetrievalEngine、AnswerBuilder 三个子模块替代原始的内部方法调用。
    输出协议与原始方法完全相同。
    """

    def __init__(
        self,
        api_key: str,
        model_name: str = "qwen3.7-max",
        encoder_model: str = "tongyi-embedding-vision-plus",
        chroma_db_path: str = "./chroma_db",
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.encoder_model = encoder_model
        self.chroma_db_path = chroma_db_path

        # LLM 实例
        self.llm = get_llm_service(api_key=api_key, model_name=model_name)

        # 子模块
        self.router = QuestionRouter()
        self.retriever = retrieval_engine.RetrievalEngine(
            api_key=api_key,
            encoder_model=encoder_model,
            chroma_db_path=chroma_db_path,
        )
        self.builder = AnswerBuilder(llm=self.llm)

        # 编码器延迟加载（用于图片检索）
        self._encoder = None

    # ========================================================================
    # 兼容性属性 — 向后兼容 RELEVANCE_THRESHOLD / CE_RELEVANCE_THRESHOLD
    # ========================================================================

    @property
    def RELEVANCE_THRESHOLD(self) -> float:
        return self.retriever.RELEVANCE_THRESHOLD

    @property
    def CE_RELEVANCE_THRESHOLD(self) -> float:
        return self.retriever.CE_RELEVANCE_THRESHOLD

    # ========================================================================
    # encoder 属性（延迟加载 MultimodalEncoder）
    # ========================================================================

    @property
    def encoder(self):
        """延迟加载编码器（用于图片检索）"""
        if self._encoder is None:
            try:
                from ..views.Spilter.MultimodalEncoder import MultimodalEncoder
                self._encoder = MultimodalEncoder(
                    api_key=self.api_key,
                    model=self.encoder_model,
                    chroma_db_path=self.chroma_db_path,
                )
            except ImportError:
                logger.error("MultimodalEncoder 不可用")
                raise ImportError("MultimodalEncoder is not available")
        return self._encoder

    # ========================================================================
    # _retrieve_images — 从 smart_answer_hybrid 提取的图片检索逻辑
    # ========================================================================

    def _retrieve_images(
        self,
        question: str,
        collection_names: List[str],
        chosen_docs: list,
        quality: Dict[str, Any],
        top_k: int,
        timings: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """基于相关文本的来源文件补充图片。

        Args:
            question: 用户问题
            collection_names: 知识库集合名列表
            chosen_docs: 已排序的检索文档列表
            quality: 检索质量评估结果
            top_k: 最大返回数量
            timings: 耗时统计字典（会被原地修改）

        Returns:
            图片结果列表
        """

        def _mark(key: str, t_start: float):
            timings[key] = round((time.perf_counter() - t_start) * 1000, 2)

        image_results: List[Dict[str, Any]] = []
        source_files = list({
            d.metadata.get('file_name')
            for d in chosen_docs
            if d.metadata.get('file_name')
        })

        if not source_files or quality["level"] == "none":
            return image_results

        t_img_total = time.perf_counter()
        for name in collection_names:
            try:
                t_one = time.perf_counter()
                self.encoder.set_collection(name)
                _mark(f"image_set_collection[{name}]", t_one)

                final_where = {
                    "$and": [
                        {"file_name": {"$in": source_files}},
                        {"modality_type": "image"},
                    ]
                }
                t_one = time.perf_counter()
                imgs = self.encoder.query(
                    query_text=question,
                    n_results=min(3, top_k),
                    where=final_where,
                ) or []
                _mark(f"image_query[{name}]", t_one)

                image_results.extend(imgs)
            except Exception as e:
                logger.error(f"图片检索集合 '{name}' 失败: {e}")
                continue

        t_one = time.perf_counter()
        image_results.sort(key=lambda x: x.get('distance', float('inf')))
        image_results = image_results[:min(3, top_k)]
        _mark("image_sort_and_truncate", t_one)
        _mark("image_retrieve_total", t_img_total)

        return image_results

    # ========================================================================
    # build_prompt — 构建多模态提示词（qa_views 使用）
    # ========================================================================

    def build_prompt(
        self,
        question: str,
        text_contexts: List[Dict[str, Any]],
        image_contexts: List[Dict[str, Any]] = None,
        system_prompt: str = None,
        strategy_text: str = None,
    ):
        """构建提示词（从原 RAGService.build_prompt 迁移）

        Args:
            question: 用户问题
            text_contexts: 文本上下文列表
            image_contexts: 图片上下文列表
            system_prompt: 系统提示词（可选）

        Returns:
            (system_prompt, user_prompt) 元组
        """
        if image_contexts is None:
            image_contexts = []

        if system_prompt is None:
            system_prompt = (
                "你是一个专业的问答助手。请根据提供的参考资料回答用户的问题。\n"
                "确保答案准确、详细。如果参考资料中没有相关信息，请明确告知用户。\n"
            )
            if strategy_text:
                system_prompt += f"\n{strategy_text}\n"

        context_parts = []
        if text_contexts:
            for i, ctx in enumerate(text_contexts):
                content = ctx.get('content', ctx.get('document', ''))
                context_parts.append(f"【参考资料{i+1}】\n{content}")

        if image_contexts:
            image_info_parts = []
            for i, img in enumerate(image_contexts):
                metadata = img.get('metadata', {})
                file_name = metadata.get('file_name', '未知')
                image_info_parts.append(f"- 图片{i+1}: {file_name}")

            if image_info_parts:
                context_parts.append("【相关图片】\n" + "\n".join(image_info_parts))

        if context_parts:
            context_text = "\n\n".join(context_parts)
            user_prompt = f"""参考资料：
{context_text}

用户问题：{question}

请根据参考资料提供准确、详细的回答。"""
        else:
            user_prompt = f"用户问题：{question}"

        return system_prompt, user_prompt

    # ========================================================================
    # run() — 忠实地从 smart_answer_hybrid() 提取而来
    # ========================================================================

    def run(
        self,
        question: str,
        collection_names: List[str],
        *,
        history: Optional[List[Dict[str, str]]] = None,
        age: Optional[int] = None,
        is_employee: Optional[bool] = None,
        frequency: Optional[str] = None,
        is_strict: bool = False,
        top_k: int = 10,
        debug: bool = False,
    ) -> Dict[str, Any]:
        """混合检索 + 画像模板回答（RAG v1 输出协议）。

        RAG v1（方案1）：
        - citations: 文档级静态元数据（title/dept/pub_date/url/effective_status/region 等）
        - retrieval_hits: chunk 级动态命中信息（chunk_id/section_path/score/rank 等）
        - evidence_spans: 证据片段（先做 v1：取命中 chunk 的摘要片段或前 N 字）
        - refusal: 硬规则拒答（NO_EVIDENCE/LOW_SCORE/OUT_OF_SCOPE）
        - retrieval_stats: 检索统计
        """
        # ====== 性能打点（用于定位“慢”在哪）======
        t0_total = time.perf_counter()
        timings: Dict[str, float] = {}

        def _mark(key: str, t_start: float):
            timings[key] = round((time.perf_counter() - t_start) * 1000, 2)

        # RAG v1 输出骨架
        trace_id = uuid.uuid4().hex
        citations: List[Dict[str, Any]] = []
        retrieval_hits: List[Dict[str, Any]] = []
        evidence_spans: List[Dict[str, Any]] = []
        refusal: Optional[Dict[str, Any]] = None

        # 惰性导入混合检索依赖
        retrieval_engine._ensure_hybrid_imports()
        if not retrieval_engine.HYBRID_AVAILABLE:
            raise RuntimeError("混合检索能力未就绪，请检查依赖与本地模型路径")
        imports = retrieval_engine._hybrid_imports
        categorize_user_profile = imports['categorize_user_profile']
        get_judge_prompt = imports['get_judge_prompt']
        get_rag_template = imports['get_rag_template']
        get_direct_template = imports['get_direct_template']
        get_refusal_response = imports['get_refusal_response']
        Document = imports['Document']
        if not collection_names:
            user_type = 'employee' if is_employee else 'public'
            profile = categorize_user_profile(age=age, user_type=user_type, frequency=frequency)
            refusal = {
                "is_refused": True,
                "reason": "OUT_OF_SCOPE",
                "max_ce": 0.0,
                "max_fused": 0.0,
                "threshold_ce": self.CE_RELEVANCE_THRESHOLD,
                "threshold_rrf": self.RELEVANCE_THRESHOLD,
                "suggested_next_questions": [],
            }
            retrieval_stats = {
                "timings_ms": {**timings},
                "docs_retrieved": 0,
                "thresholds": {
                    "rrf": self.RELEVANCE_THRESHOLD,
                    "ce": self.CE_RELEVANCE_THRESHOLD,
                },
            }
            return {
                "trace_id": trace_id,
                "answer": get_refusal_response(profile, reason="OUT_OF_SCOPE"),
                "citations": [],
                "retrieval_hits": [],
                "evidence_spans": [],
                "retrieval_stats": retrieval_stats,
                "refusal": refusal,
                "docs": [],
                "images": [],
                "used_template": "refusal",
            }

        # 聚合知识库描述（这里简化为集合名）
        t_judge = time.perf_counter()
        kb_desc = ", ".join(collection_names)
        need_kb = self.router.needs_knowledge_base(question, kb_desc)
        _mark("judge_need_kb", t_judge)

        # 用户画像
        user_type = 'employee' if is_employee else 'public'
        profile = categorize_user_profile(age=age, user_type=user_type, frequency=frequency)
        history_ctx = self.builder.format_history(history)

        chosen_docs: List[Document] = []
        context_str = ""
        used_template = "direct"

        debug_info: Dict[str, Any] = {}
        if not is_strict and not need_kb:
            retrieval_stats = {
                "timings_ms": {**timings},
                "docs_retrieved": 0,
                "thresholds": {
                    "rrf": self.RELEVANCE_THRESHOLD,
                    "ce": self.CE_RELEVANCE_THRESHOLD,
                },
            }

            template = get_direct_template(profile)
            user_prompt = template.format(question=question)
            answer = self.llm.generate_answer(user_prompt, system_prompt="你是一个涉藏舆情研究知识问答助手")

            if debug:
                debug_info = {
                    "need_kb": need_kb,
                    "is_strict": is_strict,
                    "collections": collection_names,
                    "docs_retrieved": 0,
                    "rrf_threshold": self.RELEVANCE_THRESHOLD,
                    "ce_threshold": self.CE_RELEVANCE_THRESHOLD,
                    "used_template": used_template,
                    "is_out_of_scope_direct_question": self.router.is_out_of_scope(question),
                }

            resp = {
                "trace_id": trace_id,
                "answer": answer,
                "citations": [],
                "retrieval_hits": [],
                "evidence_spans": [],
                "retrieval_stats": retrieval_stats,
                "refusal": refusal,
                "docs": [],
                "images": [],
                "used_template": used_template,
            }
            if debug:
                resp["debug"] = debug_info
            return resp

        # 需要走检索
        t_retrieve_all = time.perf_counter()
        for name in collection_names:
            try:
                t_one = time.perf_counter()
                retriever = self.retriever.get_retriever(name, top_k)
                _mark(f"hybrid_get_retriever[{name}]", t_one)

                t_one = time.perf_counter()
                docs = retriever.invoke(question)
                _mark(f"hybrid_invoke[{name}]", t_one)

                if docs:
                    chosen_docs.extend(docs)
            except Exception as e:
                # 若遇到旧版 schema 报错，自动切换到最近重建目录后重试一次
                if self.retriever._is_legacy_chroma_schema_error(e):
                    fallback = self.retriever._resolve_fallback_chroma_path()
                    if fallback and os.path.abspath(fallback) != os.path.abspath(self.retriever.chroma_db_path):
                        logger.warning(f"集合 {name} 命中旧 schema，切换 Chroma 路径重试: {fallback}")
                        self.retriever.chroma_db_path = fallback
                        self.retriever._retriever_cache = {}
                        try:
                            t_one = time.perf_counter()
                            retriever = self.retriever.get_retriever(name, top_k)
                            _mark(f"hybrid_get_retriever_retry[{name}]", t_one)

                            t_one = time.perf_counter()
                            docs = retriever.invoke(question)
                            _mark(f"hybrid_invoke_retry[{name}]", t_one)

                            if docs:
                                chosen_docs.extend(docs)
                            continue
                        except Exception as retry_e:
                            logger.error(f"集合 {name} 重试检索失败: {retry_e}")
                            continue
                logger.error(f"集合 {name} 检索失败: {e}")
                continue
        _mark("hybrid_retrieve_total", t_retrieve_all)

        # 选前 top_k（跨知识库重排后截断）
        def _rank_key(d: Document) -> tuple:
            meta = d.metadata or {}
            ce_raw = meta.get("_s_ce")
            ce_norm = retrieval_engine._safe_float(meta.get("_s_ce_norm"), 0.0)
            ce_score = retrieval_engine._safe_float(ce_raw, float("-inf")) if ce_raw is not None else float("-inf")
            primary = ce_score if ce_raw is not None else ce_norm
            fused = retrieval_engine._safe_float(meta.get("_s_fused", meta.get("_rrf_score", 0.0)), 0.0)
            mmr = retrieval_engine._safe_float(meta.get("_mmr_score", 0.0), 0.0)
            return (primary, fused, mmr, ce_norm)

        t_sort = time.perf_counter()
        chosen_docs.sort(key=_rank_key, reverse=True)
        chosen_docs = chosen_docs[:top_k]
        _mark("rank_and_truncate", t_sort)

        print(f"[RAG][HYBRID] docs_after_retrieve={len(chosen_docs)}")
        for rank, d in enumerate(chosen_docs, 1):
            meta = d.metadata or {}
            file_name = meta.get("file_name") or meta.get("source") or meta.get("source_file") or "unknown"
            print(
                f"[RAG][HYBRID][DOC] #{rank} file={file_name} chunk={meta.get('chunk_id')} "
                f"rrf={meta.get('_rrf_score')} ce={meta.get('_s_ce')} ce_norm={meta.get('_s_ce_norm')} mmr={meta.get('_mmr_score')}"
            )

        quality = self.retriever.evaluate_quality(chosen_docs)
        print(
            f"[RAG][QUALITY] level={quality['level']} max_ce={quality['max_ce']:.6f} "
            f"max_fused={quality['max_fused']:.6f} ce_threshold={self.CE_RELEVANCE_THRESHOLD} "
            f"rrf_threshold={self.RELEVANCE_THRESHOLD}"
        )
        if debug:
            debug_info = {
                "need_kb": need_kb,
                "is_strict": is_strict,
                "collections": collection_names,
                "docs_retrieved": len(chosen_docs),
                "max_rrf": quality["max_fused"],
                "max_ce": quality["max_ce"],
                "rrf_threshold": self.RELEVANCE_THRESHOLD,
                "ce_threshold": self.CE_RELEVANCE_THRESHOLD,
                "retrieval_quality": quality["level"],
                "is_relevant": quality["level"] == "relevant",
            }

        # 基于相关文本的来源文件补充图片
        image_results = self._retrieve_images(
            question=question,
            collection_names=collection_names,
            chosen_docs=chosen_docs,
            quality=quality,
            top_k=top_k,
            timings=timings,
        )

        # 生成阶段
        if quality["level"] == "relevant":
            t_ctx = time.perf_counter()
            context_str = self.retriever.format_docs(chosen_docs)
            _mark("format_text_context", t_ctx)

            template = get_rag_template(profile)
            used_template = "rag"
            user_prompt = template.format(context=context_str, question=question, history_context=history_ctx)

            t_llm = time.perf_counter()
            answer = self.llm.generate_answer(user_prompt, system_prompt="你是一个专业的涉藏舆情研究知识助手")
            _mark("llm_generate_answer", t_llm)
        else:
            refusal = {
                "is_refused": True,
                "reason": "LOW_SCORE",
                "max_ce": quality["max_ce"],
                "max_fused": quality["max_fused"],
                "threshold_ce": self.CE_RELEVANCE_THRESHOLD,
                "threshold_rrf": self.RELEVANCE_THRESHOLD,
                "suggested_next_questions": [],
            }
            used_template = "refusal"
            answer = get_refusal_response(profile, reason="LOW_SCORE")
            print(
                f"[RAG][REFUSAL] reason=LOW_SCORE profile_age={profile.get('age')} "
                f"max_ce={quality['max_ce']:.6f} "
                f"max_fused={quality['max_fused']:.6f}"
            )

        if (refusal or {}).get("is_refused"):
            docs_payload = []
            images_payload = []
        else:
            docs_payload = [
                {
                    "content": d.page_content,
                    "metadata": {**d.metadata, "modality_type": "text"},
                } for d in chosen_docs
            ]
            images_payload = [
                {
                    "content": "",
                    "metadata": {**(r.get("metadata") or {}), "modality_type": "image"},
                    "url": (r.get("metadata") or {}).get("image_url")
                            or (r.get("metadata") or {}).get("full_image_url")
                            or "",
                    "distance": r.get("distance", 0),
                }
                for r in image_results
            ]

        retrieval_stats = {
            "timings_ms": {**timings},
            "docs_retrieved": len(chosen_docs),
            "thresholds": {
                "rrf": self.RELEVANCE_THRESHOLD,
                "ce": self.CE_RELEVANCE_THRESHOLD,
            },
            "quality": quality,
        }

        _mark("total", t0_total)
        retrieval_stats["timings_ms"] = {**timings}

        # 强制打印（不依赖 Django logging 配置），便于你直接在控制台看到耗时
        try:
            print(
                f"[RAG][TIMING] total_ms={timings.get('total')} used_template={used_template} "
                f"docs={len(chosen_docs)} images={len(image_results)} detail={timings}"
            )
        except Exception:
            pass

        # 同时写入 logger（如果你的 handler/level 允许，也会落盘）
        try:
            logger.info(
                "[RAG][TIMING] total_ms=%s used_template=%s docs=%s images=%s detail=%s",
                timings.get("total"),
                used_template,
                len(chosen_docs),
                len(image_results),
                timings,
            )
        except Exception:
            pass

        return {
            "trace_id": trace_id,
            "answer": answer,
            "citations": citations,
            "retrieval_hits": retrieval_hits,
            "evidence_spans": evidence_spans,
            "retrieval_stats": retrieval_stats,
            "refusal": refusal,
            "docs": docs_payload + images_payload,  # 供 sources/模板使用
            "images": images_payload,               # 供前端直接展示
            "used_template": used_template,
            **({"debug": {**debug_info, "used_template": used_template, "timings_ms": timings}} if debug else {}),
        }
