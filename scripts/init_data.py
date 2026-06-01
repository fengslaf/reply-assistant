#!/usr/bin/env python3
"""数据初始化脚本"""

import json
import shutil
from pathlib import Path
from datetime import datetime


def init_data(data_dir: str = None):
    """初始化本地数据
    
    Args:
        data_dir: 数据目录（可选，默认自动检测）
    """
    # 确定数据目录
    if data_dir:
        data_path = Path(data_dir)
    else:
        data_path = Path(__file__).parent.parent / 'data'
    
    # 创建数据目录
    data_path.mkdir(parents=True, exist_ok=True)
    
    # 初始化配置文件
    config_path = data_path / 'config.json'
    if not config_path.exists():
        config_example = Path(__file__).parent.parent / 'data' / 'config.example.json'
        if config_example.exists():
            shutil.copy(config_example, config_path)
            
            # 更新创建时间
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            config['created_at'] = datetime.now().isoformat()
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            print(f"✓ 配置文件已创建: {config_path}")
        else:
            print(f"⚠ 配置模板不存在，请手动创建")
    
    # 初始化预览模式数据
    local_data_path = data_path / 'local_data.json'
    if not local_data_path.exists():
        local_data_example = Path(__file__).parent.parent / 'data' / 'local_data.example.json'
        if local_data_example.exists():
            shutil.copy(local_data_example, local_data_path)
            
            # 更新创建时间
            with open(local_data_path, 'r', encoding='utf-8') as f:
                local_data = json.load(f)
            local_data['config']['last_updated'] = datetime.now().isoformat()
            with open(local_data_path, 'w', encoding='utf-8') as f:
                json.dump(local_data, f, ensure_ascii=False, indent=2)
            
            print(f"✓ 预览数据已创建: {local_data_path}")
    
    # 创建必要目录
    exports_dir = data_path / 'exports'
    exports_dir.mkdir(exist_ok=True)
    print(f"✓ 导出目录已创建: {exports_dir}")
    
    backups_dir = data_path / 'backups'
    backups_dir.mkdir(exist_ok=True)
    print(f"✓ 备份目录已创建: {backups_dir}")
    
    logs_dir = data_path / 'logs'
    logs_dir.mkdir(exist_ok=True)
    print(f"✓ 日志目录已创建: {logs_dir}")
    
    chroma_dir = data_path / 'chroma'
    chroma_dir.mkdir(exist_ok=True)
    print(f"✓ 向量库目录已创建: {chroma_dir}")
    
    print("\n" + "=" * 60)
    print("数据初始化完成！")
    print("=" * 60)
    print(f"\n数据目录: {data_path}")
    print("\n下一步:")
    print("  1. 运行: python scripts/start_local.py")
    print("  2. 或使用GUI: python start_gui.py")
    print("=" * 60)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='初始化本地数据')
    parser.add_argument('--data-dir', help='数据目录')
    args = parser.parse_args()
    init_data(args.data_dir)