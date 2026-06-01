"""用户自带Key AI引擎"""

import time
import uuid
from typing import List, Dict, Optional

from local_search.data_types import SearchResult
from .providers import get_provider, get_available_providers


class UserKeyAIEngine:
    """用户自带Key AI引擎 - 支持多提供商"""
    
    def __init__(self):
        """初始化"""
        self.providers: Dict[str, any] = {}
        self.default_provider = 'deepseek'
    
    def configure_provider(self, provider_name: str, api_key: str, 
                           api_base: str = None, model: str = None):
        """配置提供商
        
        Args:
            provider_name: 提供商名称（deepseek/zhipu/wenxin/openai）
            api_key: API密钥
            api_base: API基础URL（可选）
            model: 模型名称（可选）
        """
        provider = get_provider(provider_name, api_key, api_base)
        
        if model:
            provider.model_name = model
        
        self.providers[provider_name] = provider
    
    def set_default_provider(self, provider_name: str):
        """设置默认提供商
        
        Args:
            provider_name: 提供商名称
        """
        if provider_name not in self.providers:
            raise ValueError(f'未配置的提供商: {provider_name}')
        
        self.default_provider = provider_name
    
    def generate(self, query: str, provider_name: str = None,
                 context_samples: List[str] = None) -> SearchResult:
        """生成回复
        
        Args:
            query: 用户问题
            provider_name: 提供商名称（可选，默认使用default_provider）
            context_samples: 参考样本
            
        Returns:
            SearchResult对象
        """
        provider_name = provider_name or self.default_provider
        
        if provider_name not in self.providers:
            return SearchResult(
                reply_id=f'ai_user_key_error_{uuid.uuid4().hex[:8]}',
                content=f'未配置提供商: {provider_name}',
                confidence=0.0,
                source_type='ai_user_key_error',
                source_detail='配置错误',
                total_latency_ms=0
            )
        
        provider = self.providers[provider_name]
        
        return provider.generate(query, context_samples)
    
    def is_provider_available(self, provider_name: str) -> bool:
        """检查提供商是否可用
        
        Args:
            provider_name: 提供商名称
            
        Returns:
            是否可用
        """
        if provider_name not in self.providers:
            return False
        
        return self.providers[provider_name].is_available()
    
    def get_available_providers(self) -> List[str]:
        """获取已配置的可用提供商"""
        available = []
        
        for name, provider in self.providers.items():
            if provider.is_available():
                available.append(name)
        
        return available
    
    def get_all_supported_providers(self) -> List[str]:
        """获取所有支持的提供商"""
        return get_available_providers()
    
    def clear_provider(self, provider_name: str):
        """清除提供商配置
        
        Args:
            provider_name: 提供商名称
        """
        if provider_name in self.providers:
            del self.providers[provider_name]
    
    def clear_all_providers(self):
        """清除所有提供商配置"""
        self.providers.clear()
    
    def get_config_summary(self) -> Dict:
        """获取配置摘要"""
        summary = {
            'default_provider': self.default_provider,
            'configured_providers': []
        }
        
        for name, provider in self.providers.items():
            summary['configured_providers'].append({
                'name': name,
                'model': provider.model_name,
                'available': provider.is_available()
            })
        
        return summary