"""便捷启动脚本。从项目任意目录运行均可。"""
import os
import sys
from pathlib import Path

# 确保 backend 目录在 sys.path 中
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from rerank_service.app import app

port = int(os.getenv("RERANK_SERVICE_PORT", "5001"))
host = os.getenv("RERANK_SERVICE_HOST", "127.0.0.1")

print(f"Qwen3-Rerank 微服务启动于 http://{host}:{port}")
app.run(host=host, port=port, debug=False)
