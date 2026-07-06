#!/usr/bin/env python3
"""
启动 Python 后端服务的便捷脚本
"""

import os
import sys
import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser(description="启动 Trello Pomodoro 后端服务")
    parser.add_argument("--port", type=int, default=8765, help="服务端口")
    parser.add_argument("--data-dir", default=None, help="数据目录")
    args = parser.parse_args()
    
    # 获取项目根目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    python_dir = os.path.join(project_root, "python")
    
    # 检查 Python 环境
    try:
        result = subprocess.run(
            [sys.executable, "--version"],
            capture_output=True,
            text=True
        )
        print(f"✓ Python: {result.stdout.strip()}")
    except Exception as e:
        print(f"✗ 无法运行 Python: {e}")
        return 1
    
    # 检查依赖
    print("\n检查依赖...")
    try:
        import fastapi
        import uvicorn
        import pydantic
        print("✓ FastAPI 已安装")
        print("✓ Uvicorn 已安装")
        print("✓ Pydantic 已安装")
    except ImportError as e:
        print(f"✗ 缺少依赖: {e}")
        print("\n请安装依赖:")
        print(f"  cd {python_dir}")
        print("  pip install -r requirements.txt")
        return 1
    
    # 确保数据目录存在
    data_dir = args.data_dir or os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    print(f"\n✓ 数据目录: {data_dir}")
    
    # 启动服务
    print(f"\n启动服务 http://127.0.0.1:{args.port} ...")
    print("按 Ctrl+C 停止服务\n")
    
    try:
        # 切换到 python 目录
        os.chdir(python_dir)
        
        # 启动服务
        sys.path.insert(0, python_dir)
        
        from api.server import create_app
        import uvicorn
        
        app = create_app()
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=args.port,
            log_level="info"
        )
        
    except KeyboardInterrupt:
        print("\n\n服务已停止")
        return 0
    except Exception as e:
        print(f"\n✗ 启动失败: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
