#!/usr/bin/env python3
"""
Django服务器启动脚本
"""

import os
import sys
import subprocess


def start_server():
    """启动 Django 服务器"""
    print("启动 Django 服务器...")
    try:
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        manage_py = os.path.join(backend_dir, "manage.py")
        subprocess.run([
            sys.executable, manage_py, "runserver", "0.0.0.0:8000"
        ], cwd=backend_dir)
    except KeyboardInterrupt:
        print("\n服务器已停止")
    except Exception as e:
        print(f"启动服务器失败: {e}")


def main():
    print("Django API 服务")
    print("=" * 40)
    print("按 Ctrl+C 停止服务器")
    print("=" * 40)
    start_server()


if __name__ == "__main__":
    main()
