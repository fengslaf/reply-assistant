"""来源标注 - 标注检索结果的来源类型"""

from typing import Dict, Optional
from .data_types import SearchResult, SOURCE_TYPE_LABELS


class SourceMarker:
    """来源标注器"""
    
    SOURCE_TYPE_PRIORITY = {
        'local_exact': 1,
        'local_vector': 2,
        'local_keyword': 3,
        'ai_user_key_deepseek': 4,
        'ai_user_key_zhipu': 5,
        'ai_user_key_wenxin': 6,
        'ai_user_key_openai': 7,
        'ai_platform': 8
    }
    
    def __init__(self):
        """初始化"""
        pass
    
    def mark(self, result: SearchResult, additional_info: Dict = None) -> SearchResult:
        """标注来源
        
        Args:
            result: SearchResult对象
            additional_info: 附加信息
            
        Returns:
            标注后的SearchResult对象
        """
        if additional_info:
            detail_parts = [result.source_detail]
            
            for key, value in additional_info.items():
                detail_parts.append(f'{key}={value}')
            
            result.source_detail = ', '.join(detail_parts)
        
        return result
    
    def mark_with_model_info(self, result: SearchResult, model_name: str) -> SearchResult:
        """标注模型信息（用于AI生成结果）
        
        Args:
            result: SearchResult对象
            model_name: 模型名称
            
        Returns:
            标注后的SearchResult对象
        """
        result.generation_model = model_name
        
        return result
    
    def mark_with_latency(self, result: SearchResult, latency_ms: int) -> SearchResult:
        """标注延迟信息
        
        Args:
            result: SearchResult对象
            latency_ms: 延迟毫秒数
            
        Returns:
            标注后的SearchResult对象
        """
        result.retrieval_latency_ms = latency_ms
        
        if not result.total_latency_ms:
            result.total_latency_ms = latency_ms
        
        return result
    
    def get_source_label(self, source_type: str) -> str:
        """获取来源标签（中文）
        
        Args:
            source_type: 来源类型
            
        Returns:
            中文标签
        """
        return SOURCE_TYPE_LABELS.get(source_type, '未知来源')
    
    def get_source_priority(self, source_type: str) -> int:
        """获取来源优先级
        
        Args:
            source_type: 来源类型
            
        Returns:
            优先级（数字越小优先级越高）
        """
        return self.SOURCE_TYPE_PRIORITY.get(source_type, 99)
    
    def sort_by_source_priority(self, results: list) -> list:
        """按来源优先级排序
        
        Args:
            results: SearchResult列表
            
        Returns:
            排序后的列表
        """
        return sorted(results, key=lambda r: self.get_source_priority(r.source_type))
    
    def format_source_detail(self, result: SearchResult) -> str:
        """格式化来源详情（用于GUI显示）
        
        Args:
            result: SearchResult对象
            
        Returns:
            格式化的来源详情
        """
        label = self.get_source_label(result.source_type)
        
        detail = result.source_detail
        
        return f'【{label}】{detail}'
    
    def is_high_confidence(self, result: SearchResult, threshold: float = 0.8) -> bool:
        """是否为高置信度结果
        
        Args:
            result: SearchResult对象
            threshold: 置信度阈值
            
        Returns:
            是否高置信度
        """
        return result.confidence >= threshold
    
    def get_source_icon(self, source_type: str) -> Optional[str]:
        """获取来源图标（用于GUI）
        
        Args:
            source_type: 来源类型
            
        Returns:
            图标名称或路径
        """
        icon_map = {
            'local_exact': '[EXACT]',
            'local_vector': '[VEC]',
            'local_keyword': '[KEY]',
            'ai_user_key_deepseek': '[AI-DS]',
            'ai_user_key_zhipu': '[AI-ZP]',
            'ai_user_key_wenxin': '[AI-WX]',
            'ai_user_key_openai': '[AI-OA]',
            'ai_platform': '[PLATFORM]'
        }
        
        return icon_map.get(source_type, '❓')
    
    def get_source_color(self, source_type: str) -> str:
        """获取来源颜色（用于GUI）
        
        Args:
            source_type: 来源类型
            
        Returns:
            颜色代码
        """
        color_map = {
            'local_exact': '#4CAF50',
            'local_vector': '#2196F3',
            'local_keyword': '#FF9800',
            'ai_user_key_deepseek': '#9C27B0',
            'ai_user_key_zhipu': '#9C27B0',
            'ai_user_key_wenxin': '#9C27B0',
            'ai_user_key_openai': '#9C27B0',
            'ai_platform': '#E91E63'
        }
        
        return color_map.get(source_type, '#757575')