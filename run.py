#!/usr/bin/env python3
"""一键启动脚本 - 快速启动快捷回复助手

自动处理:
1. 检查Python环境
2. 检查依赖
3. 设置环境变量
4. 启动应用

使用: python run.py 或 直接双击运行
"""

import os
import sys
import warnings
from pathlib import Path

# 静默第三方库的弃用警告（jieba 使用了已弃用的 pkg_resources）
warnings.filterwarnings("ignore", message=".*pkg_resources.*deprecated.*")

PROJECT_ROOT = Path(__file__).parent


def setup_env():
    """设置环境变量"""
    os.environ['DATABASE_PATH'] = str(PROJECT_ROOT / 'data' / 'guest_data.db')
    os.environ['VECTOR_STORE_PATH'] = str(PROJECT_ROOT / 'data' / 'guest_chroma')


def check_dependencies():
    """检查依赖"""
    required = []
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"缺少依赖: {', '.join(missing)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    return True


def main():
    """启动应用"""
    print("快捷回复助手 - 启动...")
    
    setup_env()
    
    sys.path.insert(0, str(PROJECT_ROOT))
    
    if not check_dependencies():
        sys.exit(1)
    
    import start_gui
    start_gui.main()


if __name__ == '__main__':
    main()