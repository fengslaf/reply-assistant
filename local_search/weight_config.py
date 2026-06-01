"""权重配置管理 - 用户自定义权重配置保存和加载"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

from .data_types import WeightConfig


class WeightConfigManager:
    """权重配置管理器"""
    
    DEFAULT_CONFIG = WeightConfig(
        vector=0.4,
        keyword=0.3,
        scene=0.15,
        quality=0.15
    )
    
    def __init__(self, config_path: str = None):
        """初始化
        
        Args:
            config_path: 配置文件路径（默认为data/weights.json）
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            self.config_path = Path(__file__).parent.parent / 'data' / 'weights.json'
        
        self._ensure_config_dir()
    
    def _ensure_config_dir(self):
        """确保配置目录存在"""
        config_dir = self.config_path.parent
        if not config_dir.exists():
            config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self) -> WeightConfig:
        """加载权重配置
        
        Returns:
            WeightConfig对象
        """
        if not self.config_path.exists():
            return self.DEFAULT_CONFIG
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            weights = data.get('weights', {})
            
            return WeightConfig(
                vector=weights.get('vector', 0.4),
                keyword=weights.get('keyword', 0.3),
                scene=weights.get('scene', 0.15),
                quality=weights.get('quality', 0.15),
                user_id=data.get('user_id'),
                updated_at=datetime.fromisoformat(data.get('updated_at')) if data.get('updated_at') else datetime.now()
            )
        except Exception:
            return self.DEFAULT_CONFIG
    
    def save_config(self, config: WeightConfig):
        """保存权重配置
        
        Args:
            config: WeightConfig对象
        """
        if not config.validate():
            raise ValueError("权重总和必须为1")
        
        data = {
            'weights': config.to_dict(),
            'user_id': config.user_id,
            'updated_at': datetime.now().isoformat()
        }
        
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def update_weight(self, weight_type: str, value: float) -> WeightConfig:
        """更新单个权重
        
        Args:
            weight_type: 权重类型（vector/keyword/scene/quality）
            value: 权重值
            
        Returns:
            更新后的WeightConfig对象
        """
        current_config = self.load_config()
        
        weight_dict = current_config.to_dict()
        
        if weight_type not in weight_dict:
            raise ValueError(f"无效的权重类型: {weight_type}")
        
        if not (0 <= value <= 1):
            raise ValueError(f"权重值必须在0-1之间: {value}")
        
        weight_dict[weight_type] = value
        
        total = sum(weight_dict.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"权重总和必须为1，当前总和: {total}")
        
        new_config = WeightConfig.from_dict(weight_dict)
        
        self.save_config(new_config)
        
        return new_config
    
    def reset_to_default(self) -> WeightConfig:
        """重置为默认权重
        
        Returns:
            默认WeightConfig对象
        """
        self.save_config(self.DEFAULT_CONFIG)
        return self.DEFAULT_CONFIG
    
    def get_available_weight_types(self) -> list:
        """获取可用的权重类型"""
        return ['vector', 'keyword', 'scene', 'quality']
    
    def get_weight_description(self, weight_type: str) -> str:
        """获取权重描述
        
        Args:
            weight_type: 权重类型
            
        Returns:
            权重描述
        """
        descriptions = {
            'vector': '向量检索权重 - 控制语义相似度的影响',
            'keyword': '关键词匹配权重 - 控制关键词匹配的影响',
            'scene': '场景权重 - 控制场景匹配的加成',
            'quality': '质量权重 - 控制样本质量分数的影响'
        }
        
        return descriptions.get(weight_type, '未知权重类型')