#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Trello Pomodoro - Python 后端服务入口
启动 HTTP API 服务器，供 C++ Qt 客户端调用
"""

import os
import sys
import argparse

# Windows: 设置 UTF-8 编码
if os.name == 'nt':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    # 强制设置 stdout/stderr 编码
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加当前目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description="Trello Pomodoro Backend Server")
    parser.add_argument("--host", default="127.0.0.1", help="服务器监听地址 (默认: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="服务器端口 (默认: 8765)")
    parser.add_argument("--data-dir", default=None, help="数据存储目录 (默认: ../data)")
    parser.add_argument("--reload", action="store_true", help="开发模式自动重载")
    
    args = parser.parse_args()
    
    # 设置数据目录
    if args.data_dir:
        os.environ["TRELLO_DATA_DIR"] = args.data_dir
    
    print(f"启动 Trello Pomodoro 后端服务...")
    print(f"地址: http://{args.host}:{args.port}")
    
    # 导入并启动服务
    from api.server import create_app
    import uvicorn
    
    app = create_app()
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        reload=args.reload
    )

if __name__ == "__main__":
    main()
