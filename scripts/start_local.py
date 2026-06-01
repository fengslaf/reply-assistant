#!/usr/bin/env python3
"""启动本地版本脚本"""

import sys
from pathlib import Path

# 添加项目路径
_root = Path(__file__).parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from server.app.local.app import LocalApp


def main():
    """启动本地应用"""
    import argparse
    
    parser = argparse.ArgumentParser(description='快捷回复助手（本地版）')
    parser.add_argument('--data-dir', help='数据目录')
    parser.add_argument('--mode', choices=['gui', 'cli'], default='gui', help='运行模式')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("快捷回复助手 - 本地版（无需账号）")
    print("=" * 60)
    print("\n功能特点:")
    print("  ✓ 完整核心功能可用")
    print("  ✓ 数据本地存储，完全掌控")
    print("  ✓ 智能匹配检索")
    print("  ✓ 基础候选生成")
    print("  ✓ 无限制使用")
    print("\n升级云端服务可解锁:")
    print("  • 高级统计分析")
    print("  • 多端数据同步")
    print("  • 团队共享库")
    print("  • 云端数据备份")
    print("=" * 60 + "\n")
    
    app = LocalApp(data_dir=args.data_dir)
    
    if args.mode == 'gui':
        app.start_gui()
    else:
        app.start_cli()


if __name__ == '__main__':
    main()