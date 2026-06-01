"""AI提供商模块"""

from .base_provider import BaseAIProvider
from .deepseek_provider import DeepSeekProvider
from .zhipu_provider import ZhipuProvider
from .wenxin_provider import WenxinProvider
from .openai_provider import OpenAIProvider

PROVIDER_REGISTRY = {
    'deepseek': DeepSeekProvider,
    'zhipu': ZhipuProvider,
    'wenxin': WenxinProvider,
    'openai': OpenAIProvider
}

def get_provider(provider_name: str, api_key: str, api_base: str = None) -> BaseAIProvider:
    """获取提供商实例
    
    Args:
        provider_name: 提供商名称
        api_key: API密钥
        api_base: API基础URL
        
    Returns:
        提供商实例
    """
    if provider_name not in PROVIDER_REGISTRY:
        raise ValueError(f'未知提供商: {provider_name}')
    
    return PROVIDER_REGISTRY[provider_name](api_key, api_base)

def get_available_providers() -> list:
    """获取可用的提供商列表"""
    return list(PROVIDER_REGISTRY.keys())

__all__ = [
    'BaseAIProvider',
    'DeepSeekProvider',
    'ZhipuProvider',
    'WenxinProvider',
    'OpenAIProvider',
    'PROVIDER_REGISTRY',
    'get_provider',
    'get_available_providers'
]