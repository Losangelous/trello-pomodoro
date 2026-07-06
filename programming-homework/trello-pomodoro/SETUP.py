#!/usr/bin/env python3
"""Trello Pomodoro 安装脚本"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    try:
        print("Trello Pomodoro 安装程序")
        print("=" * 30)
        
        # 安装 Python 依赖（含 FastAPI、uvicorn 后端与 flet GUI）
        print("\n[1/3] 正在安装依赖...")
        print("      （requirements.txt：后端 + Flet 图形界面）")
        req_file = Path(__file__).parent / "python" / "requirements.txt"
        
        if not req_file.exists():
            print(f"错误: 找不到 {req_file}")
            input("\n按 Enter 退出...")
            return
        
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
            text=True,
        )
        
        if result.returncode != 0:
            print("安装失败，请检查上方 pip 消息。")
            input("\n按 Enter 退出...")
            return
        
        print("✓ 依赖安装完成")
        
        # 验证 GUI 所需模块 flet（避免仅执行 start.bat 却未安装成功）
        print("\n[2/3] 验证 Flet (GUI)...")
        try:
            import flet  # noqa: F401
            print("✓ flet 模块可正常导入")
        except ImportError as e:
            print(f"错误: flet 无法导入 — {e}")
            print("请确认 pip 安装时无错误，或手动执行：")
            print(f'  {sys.executable} -m pip install -r "{req_file}"')
            input("\n按 Enter 退出...")
            return
        
        # 创建启动脚本
        print("\n[3/3] 创建启动文件...")
        project_root = Path(__file__).parent
        start_bat = project_root / "start.bat"
        
        bat_content = '''@echo off
cd /d "{python_dir}"
python gui.py
pause
'''.format(python_dir=project_root / "python")
        
        with open(start_bat, 'w', encoding='utf-8') as f:
            f.write(bat_content)
        
        print(f"✓ 创建启动文件: {start_bat}")
        
        print("\n" + "=" * 30)
        print("安装完成！")
        print("请运行 start.bat 启动程序")
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    
    input("\n按 Enter 退出...")

if __name__ == "__main__":
    main()
