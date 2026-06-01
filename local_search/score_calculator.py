"""权重融合计算器 - 根据用户自定义权重计算综合得分"""

from typing import Dict, List
from .data_types import SearchResult, WeightConfig


class ScoreCalculator:
    """权重融合计算器"""
    
    def __init__(self, weight_config: WeightConfig = None):
        """初始化
        
        Args:
            weight_config: 权重配置（用户自定义）
        """
        self.weight_config = weight_config or WeightConfig()
    
    def calculate_final_scores(self, results: List[SearchResult]) -> List[SearchResult]:
        """计算最终综合得分
        
        Args:
            results: SearchResult列表
            
        Returns:
            计算后的SearchResult列表（按综合得分排序）
        """
        for result in results:
            base_score = result.confidence
            
            source_type_weights = {
                'local_exact': 1.0,
                'local_vector': self.weight_config.vector,
                'local_keyword': self.weight_config.keyword
            }
            
            source_weight = source_type_weights.get(result.source_type, 0.5)
            
            result.confidence = base_score * source_weight
        
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        return results
    
    def apply_quality_weight(self, results: List[SearchResult], 
                             quality_scores: Dict[str, float]) -> List[SearchResult]:
        """应用质量权重
        
        Args:
            results: SearchResult列表
            quality_scores: 样本ID -> 质量分数映射
            
        Returns:
            计算后的SearchResult列表
        """
        for result in results:
            if result.matched_sample_id:
                quality = quality_scores.get(result.matched_sample_id, 1.0)
                
                base_confidence = result.confidence
                quality_contribution = quality * self.weight_config.quality
                
                result.confidence = base_confidence + quality_contribution * (1 - base_confidence)
        
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        return results
    
    def apply_scene_weight(self, results: List[SearchResult],
                          scene_hint: str) -> List[SearchResult]:
        """应用场景权重
        
        Args:
            results: SearchResult列表
            scene_hint: 场景提示
            
        Returns:
            计算后的SearchResult列表
        """
        if not scene_hint:
            return results
        
        for result in results:
            if result.matched_parent_message:
                parent_lower = result.matched_parent_message.lower()
                scene_lower = scene_hint.lower()
                
                if scene_lower in parent_lower:
                    scene_boost = self.weight_config.scene
                    result.confidence = min(result.confidence + scene_boost, 1.0)
        
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        return results
    
    def get_weights_dict(self) -> Dict[str, float]:
        """获取当前权重配置"""
        return self.weight_config.to_dict()
    
    def update_weights(self, weight_config: WeightConfig):
        """更新权重配置
        
        Args:
            weight_config: 新的权重配置
        """
        if weight_config.validate():
            self.weight_config = weight_config
        else:
            raise ValueError("权重总和必须为1")