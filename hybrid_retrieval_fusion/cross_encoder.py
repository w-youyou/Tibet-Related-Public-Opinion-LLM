# -*- coding: utf-8 -*-
from __future__ import annotations

import logging
import os
from typing import List

import requests

logger = logging.getLogger(__name__)


class RemoteCrossEncoderWrapper:
    """通过 HTTP 调用 Qwen3-Rerank 微服务进行重排序。

    使用前需先启动 rerank_service 微服务（后端独立进程或本机服务）。
    """

    def __init__(
        self,
        service_url: str = "http://127.0.0.1:5001/rerank",
        batch_size: int = 64,
        device: str | None = None,
    ):
        self.service_url = service_url
        self.batch_size = batch_size

    def score(self, query: str, passages: List[str]) -> List[float]:
        if not passages:
            return []

        try:
            resp = requests.post(
                self.service_url,
                json={"query": query, "passages": passages},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise RuntimeError(f"Rerank service error: {data['error']}")
            return [float(s) for s in data.get("scores", [])]
        except requests.RequestException as e:
            logger.error("RemoteCrossEncoder 调用失败: %s", e)
            raise


class CrossEncoderWrapper:
    """基于 sentence-transformers 的 CrossEncoder（默认 BAAI/bge-reranker-large）。

    - 默认优先使用 GPU（cuda），若不可用则回退 CPU
    - 支持通过环境变量强制指定设备：
        - RERANKER_DEVICE=cuda | cpu | auto（默认 auto）
    - 初始化会打印一次关键信息，便于确认是否真的在用 GPU、以及加载的是哪个文件
    """

    def __init__(
        self,
        model_path: str = "BAAI/bge-reranker-large",
        batch_size: int = 16,
        device: str | None = None,
    ):
        from sentence_transformers import CrossEncoder
        import torch

        self.batch_size = batch_size

        env_device = (os.getenv("RERANKER_DEVICE") or "auto").strip().lower()
        if device is None:
            device = env_device

        if device in ("auto", ""):
            resolved = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            resolved = device
            if resolved == "cuda" and not torch.cuda.is_available():
                print("[RERANKER] RERANKER_DEVICE=cuda 但当前 torch.cuda 不可用，回退到 cpu")
                resolved = "cpu"

        self.device = resolved

        # 打印一次信息（初始化阶段）
        try:
            pid = os.getpid()
            file_path = os.path.abspath(__file__)
            torch_ver = getattr(torch, "__version__", "unknown")
            cuda_ok = bool(torch.cuda.is_available())
            cuda_cnt = int(torch.cuda.device_count()) if cuda_ok else 0
            cuda_name = ""
            if cuda_ok and cuda_cnt > 0:
                try:
                    cuda_name = torch.cuda.get_device_name(0)
                except Exception:
                    cuda_name = "cuda"

            print(
                f"[RERANKER][INIT] pid={pid} file={file_path} torch={torch_ver} "
                f"cuda_available={cuda_ok} cuda_count={cuda_cnt} device={self.device} "
                f"gpu0={cuda_name} batch_size={self.batch_size} model={model_path}"
            )
        except Exception:
            pass

        # 兼容不同版本的初始化方式
        try:
            self.model = CrossEncoder(model_path, device=self.device)
        except Exception:
            try:
                self.model = CrossEncoder(model_name_or_path=model_path, device=self.device)
            except Exception:
                self.model = CrossEncoder(model_name=model_path, device=self.device)

    def score(self, query: str, passages: List[str]) -> List[float]:
        if not passages:
            return []
        pairs = [(query, p) for p in passages]
        scores = self.model.predict(pairs, batch_size=self.batch_size)
        return [float(s) for s in scores]
