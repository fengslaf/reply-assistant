"""GUI显示辅助模块 - 来源标注可视化"""

from typing import Dict, List

from local_search.data_types import SearchResult, SOURCE_TYPE_LABELS, INFERENCE_MODE_LABELS
from local_search.source_marker import SourceMarker


class GUIDisplayHelper:
    """GUI显示辅助"""
    
    def __init__(self):
        """初始化"""
        self.source_marker = SourceMarker()
    
    def format_result_for_display(self, result: SearchResult) -> Dict:
        """格式化结果用于GUI显示
        
        Args:
            result: SearchResult对象
            
        Returns:
            GUI显示格式
        """
        icon = self.source_marker.get_source_icon(result.source_type)
        color = self.source_marker.get_source_color(result.source_type)
        label = self.source_marker.get_source_label(result.source_type)
        
        confidence_percent = int(result.confidence * 100)
        
        confidence_label = self._get_confidence_label(result.confidence)
        
        latency_info = self._format_latency(result)
        
        return {
            'icon': icon,
            'color': color,
            'source_label': label,
            'content': result.content,
            'confidence': result.confidence,
            'confidence_percent': confidence_percent,
            'confidence_label': confidence_label,
            'source_detail': result.source_detail,
            'matched_parent': result.matched_parent_message,
            'latency': latency_info,
            'reply_id': result.reply_id,
            'is_local': result.is_local(),
            'is_ai': result.is_ai_generated()
        }
    
    def _get_confidence_label(self, confidence: float) -> str:
        """获取置信度标签"""
        if confidence >= 0.9:
            return '高置信'
        elif confidence >= 0.7:
            return '中置信'
        elif confidence >= 0.5:
            return '低置信'
        else:
            return '不确定'
    
    def _format_latency(self, result: SearchResult) -> str:
        """格式化延迟信息"""
        if result.total_latency_ms:
            if result.generation_latency_ms:
                return f'检索{result.retrieval_latency_ms}ms + 生成{result.generation_latency_ms}ms = 总计{result.total_latency_ms}ms'
            else:
                return f'检索耗时{result.total_latency_ms}ms'
        else:
            return '未知'
    
    def format_results_list(self, results: List[SearchResult]) -> List[Dict]:
        """格式化结果列表
        
        Args:
            results: SearchResult列表
            
        Returns:
            GUI显示格式列表
        """
        formatted = []
        
        for result in results:
            formatted.append(self.format_result_for_display(result))
        
        return formatted
    
    def get_source_type_options(self) -> List[Dict]:
        """获取来源类型选项（用于GUI下拉）"""
        options = []
        
        for source_type, label in SOURCE_TYPE_LABELS.items():
            options.append({
                'value': source_type,
                'label': label,
                'icon': self.source_marker.get_source_icon(source_type),
                'color': self.source_marker.get_source_color(source_type)
            })
        
        return options
    
    def get_inference_mode_options(self) -> List[Dict]:
        """获取推理模式选项（用于GUI下拉）"""
        options = []
        
        for mode, label in INFERENCE_MODE_LABELS.items():
            options.append({
                'value': mode,
                'label': label
            })
        
        return options
    
    def format_confidence_bar(self, confidence: float) -> Dict:
        """格式化置信度进度条
        
        Args:
            confidence: 置信度
            
        Returns:
            进度条配置
        """
        percent = int(confidence * 100)
        
        color = '#4CAF50' if confidence >= 0.7 else '#FF9800' if confidence >= 0.5 else '#F44336'
        
        return {
            'percent': percent,
            'color': color,
            'width': f'{percent}%'
        }
    
    def highlight_source_type(self, source_type: str) -> str:
        """高亮来源类型显示
        
        Args:
            source_type: 来源类型
            
        Returns:
            高亮文本（带颜色标记）
        """
        icon = self.source_marker.get_source_icon(source_type)
        label = self.source_marker.get_source_label(source_type)
        
        return f'{icon} {label}'