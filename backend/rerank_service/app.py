"""
Qwen3-Rerank 微服务

独立运行的 Flask 服务，将百炼 DashScope 重排序 API 封装为本地 HTTP 接口。
启动: python start.py 或 flask run -p 5001
"""

import os
import sys
import logging
from pathlib import Path

from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

# 从项目根目录 .env 加载 API Key
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
DASHSCOPE_RERANK_URL = "https://dashscope.aliyuncs.com/compatible-api/v1/reranks"
RERANK_MODEL = os.getenv("RERANK_MODEL_NAME", "qwen3-rerank")

logging.basicConfig(level=logging.INFO, format="[RERANK-SERVICE] %(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "model": RERANK_MODEL})


@app.route("/rerank", methods=["POST"])
def rerank():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "请求体不能为空"}), 400

    query = data.get("query", "").strip()
    passages = data.get("passages", [])
    if not query:
        return jsonify({"error": "缺少 query 参数"}), 400
    if not passages:
        return jsonify({"scores": []})

    if not DASHSCOPE_API_KEY:
        return jsonify({"error": "未配置 DASHSCOPE_API_KEY，请检查 .env 文件"}), 500

    # 批量调用（Qwen3-rerank 单次最多 100 条，安全起见 64 条一批）
    batch_size = 64
    all_scores = []

    for i in range(0, len(passages), batch_size):
        batch = passages[i:i + batch_size]
        try:
            headers = {
                "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
                "Content-Type": "application/json",
            }
            body = {
                "model": RERANK_MODEL,
                "query": query,
                "documents": batch,
            }
            logger.info("调用 DashScope Rerank API: query=%.60s... docs=%d", query, len(batch))
            resp = requests.post(DASHSCOPE_RERANK_URL, json=body, headers=headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()

            # 按 index 排列分数
            batch_scores = [0.0] * len(batch)
            for item in result.get("results", []):
                idx = item.get("index", 0)
                score = item.get("relevance_score", 0.0)
                if 0 <= idx < len(batch):
                    batch_scores[idx] = float(score)

            all_scores.extend(batch_scores)
        except requests.RequestException as e:
            logger.error("DashScope API 调用失败: %s", e)
            return jsonify({"error": f"重排序服务调用失败: {str(e)}"}), 502

    return jsonify({"scores": all_scores})


if __name__ == "__main__":
    port = int(os.getenv("RERANK_SERVICE_PORT", "5001"))
    host = os.getenv("RERANK_SERVICE_HOST", "127.0.0.1")
    logger.info("Qwen3-Rerank 微服务启动于 http://%s:%d", host, port)
    app.run(host=host, port=port, debug=False)
