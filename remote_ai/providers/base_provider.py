"""AI提供商基类"""

import time
import uuid
from typing import Dict, List, Optional
from abc import ABC, abstractmethod

from local_search.data_types import SearchResult


class BaseAIProvider(ABC):
    """AI提供商基类"""
    
    PROVIDER_NAME = 'unknown'
    SOURCE_TYPE = 'ai_user_key_unknown'
    
    def __init__(self, api_key: str, api_base: str = None):
        """初始化
        
        Args:
            api_key: API密钥
            api_base: API基础URL（可选）
        """
        self.api_key = api_key
        self.api_base = api_base or self.get_default_base_url()
        self.model_name = self.get_default_model()
    
    @abstractmethod
    def get_default_base_url(self) -> str:
        """获取默认API基础URL"""
        pass
    
    @abstractmethod
    def get_default_model(self) -> str:
        """获取默认模型名称"""
        pass
    
    @abstractmethod
    def generate(self, query: str, context_samples: List[str] = None) -> SearchResult:
        """生成回复
        
        Args:
            query: 用户问题
            context_samples: 参考样本（可选）
            
        Returns:
            SearchResult对象
        """
        pass
    
    def _build_prompt(self, query: str, context_samples: List[str] = None) -> str:
        """构建提示
        
        Args:
            query: 用户问题
            context_samples: 参考样本
            
        Returns:
            构建好的提示
        """
        prompt = f"用户问题: {query}\n\n"
        
        if context_samples:
            prompt += "参考回复:\n"
            for i, sample in enumerate(context_samples[:3]):
                prompt += f"{i+1}. {sample}\n"
            prompt += "\n请基于以上参考，生成一个合适的回复:\n"
        else:
            prompt += "请生成一个合适的回复:\n"
        
        return prompt
    
    def _create_result(self, content: str, confidence: float, 
                       latency_ms: int, reference_samples: List[str] = None) -> SearchResult:
        """创建SearchResult对象
        
        Args:
            content: 生成的回复内容
            confidence: 置信度
            latency_ms: 延迟毫秒数
            reference_samples: 参考样本
            
        Returns:
            SearchResult对象
        """
        return SearchResult(
            reply_id=f'{self.SOURCE_TYPE}_{uuid.uuid4().hex[:8]}',
            content=content,
            confidence=confidence,
            source_type=self.SOURCE_TYPE,
            source_detail=f'{self.PROVIDER_NAME}生成(模型={self.model_name}, 延迟={latency_ms}ms)',
            generation_model=self.model_name,
            generation_latency_ms=latency_ms,
            reference_samples=reference_samples or [],
            total_latency_ms=latency_ms
        )
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return bool(self.api_key)
    
    def get_provider_info(self) -> Dict:
        """获取提供商信息"""
        return {
            'name': self.PROVIDER_NAME,
            'source_type': self.SOURCE_TYPE,
            'model': self.model_name,
            'api_base': self.api_base
        }