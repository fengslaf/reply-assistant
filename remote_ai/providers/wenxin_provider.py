"""文心一言提供商"""

import time
import requests
import json
from typing import List

from .base_provider import BaseAIProvider


class WenxinProvider(BaseAIProvider):
    """文心一言提供商"""
    
    PROVIDER_NAME = '文心一言'
    SOURCE_TYPE = 'ai_user_key_wenxin'
    
    def get_default_base_url(self) -> str:
        return 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat'
    
    def get_default_model(self) -> str:
        return 'eb-instant'
    
    def generate(self, query: str, context_samples: List[str] = None) -> 'SearchResult':
        """生成回复"""
        start_time = time.time()
        
        prompt = self._build_prompt(query, context_samples)
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        payload = {
            'messages': [
                {'role': 'user', 'content': prompt}
            ]
        }
        
        try:
            response = requests.post(
                f'{self.api_base}/{self.model_name}?access_token={self.api_key}',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('result', '')
                return self._create_result(content, 0.85, latency_ms, context_samples)
            else:
                return self._create_result(f'文心API错误: {response.status_code}', 0.0, latency_ms)
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return self._create_result(f'文心调用失败: {str(e)}', 0.0, latency_ms)