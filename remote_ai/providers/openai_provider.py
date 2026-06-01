"""OpenAI提供商"""

import time
import requests
from typing import List

from .base_provider import BaseAIProvider


class OpenAIProvider(BaseAIProvider):
    """OpenAI提供商"""
    
    PROVIDER_NAME = 'OpenAI'
    SOURCE_TYPE = 'ai_user_key_openai'
    
    def get_default_base_url(self) -> str:
        return 'https://api.openai.com/v1'
    
    def get_default_model(self) -> str:
        return 'gpt-3.5-turbo'
    
    def generate(self, query: str, context_samples: List[str] = None) -> 'SearchResult':
        """生成回复"""
        start_time = time.time()
        
        prompt = self._build_prompt(query, context_samples)
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model_name,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'temperature': 0.7,
            'max_tokens': 500
        }
        
        try:
            response = requests.post(
                f'{self.api_base}/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                return self._create_result(content, 0.85, latency_ms, context_samples)
            else:
                return self._create_result(f'OpenAI API错误: {response.status_code}', 0.0, latency_ms)
        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            return self._create_result(f'OpenAI调用失败: {str(e)}', 0.0, latency_ms)