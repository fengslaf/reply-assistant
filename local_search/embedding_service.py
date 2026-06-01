"""本地Embedding服务 - 支持 m3e-small 中文模型"""

import os
from typing import List, Optional
from pathlib import Path

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False

M3E_SMALL_MODEL = 'moka-ai/m3e-small'
M3E_SMALL_MODEL_PATH = Path(__file__).parent.parent.parent / 'models' / 'm3e-small'
ALL_MINILM_MODEL = 'all-MiniLM-L6-v2'
ALLOW_REMOTE_EMBEDDING_DOWNLOAD = os.environ.get("ALLOW_REMOTE_EMBEDDING_DOWNLOAD", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


class LocalEmbeddingService:
    """本地Embedding生成服务 - V2.03
    
    支持模型：
    - moka-ai/m3e-small（中文优化，推荐）
    - all-MiniLM-L6-v2（英文通用，备选）
    """
    
    def __init__(self, model_name: str = None, model_path: str = None):
        """初始化
        
        Args:
            model_name: 模型名称（moka-ai/m3e-small/all-MiniLM-L6-v2）
            model_path: 模型本地路径（可选，优先使用本地模型）
        """
        self.model_name = model_name or M3E_SMALL_MODEL
        self.model_path = model_path
        self.model = None
        self.dimension = 512
        
        if not HAS_SENTENCE_TRANSFORMERS:
            return
        
        self._load_model()
    
    def _load_model(self):
        """加载模型"""
        if not HAS_SENTENCE_TRANSFORMERS:
            return
        
        try:
            if self.model_path and Path(self.model_path).exists():
                self.model = SentenceTransformer(self.model_path)
            elif M3E_SMALL_MODEL_PATH.exists():
                self.model = SentenceTransformer(str(M3E_SMALL_MODEL_PATH))
            elif not ALLOW_REMOTE_EMBEDDING_DOWNLOAD:
                self.model = None
                return
            else:
                self.model = SentenceTransformer(self.model_name)
            
            if hasattr(self.model, "get_embedding_dimension"):
                self.dimension = self.model.get_embedding_dimension()
            else:
                self.dimension = self.model.get_sentence_embedding_dimension()
        except Exception as e:
            print(f"[LocalEmbeddingService] 模型加载失败: {e}")
            self.model = None
    
    def embed(self, text: str) -> Optional[List[float]]:
        """生成文本embedding
        
        Args:
            text: 输入文本
            
        Returns:
            embedding向量（512维），失败返回None
        """
        if not self.model:
            return None
        
        if not text or not text.strip():
            return None
        
        try:
            embedding = self.model.encode(text, normalize_embeddings=True)
            if hasattr(embedding, "tolist"):
                return embedding.tolist()
            if isinstance(embedding, list):
                return embedding
            return list(embedding)
        except Exception as e:
            print(f"[LocalEmbeddingService] Embedding生成失败: {e}")
            return None
    
    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """批量生成embedding
        
        Args:
            texts: 文本列表
            
        Returns:
            embedding向量列表
        """
        if not self.model:
            return [None] * len(texts)
        
        valid_texts = [t if t and t.strip() else "" for t in texts]
        
        try:
            embeddings = self.model.encode(valid_texts, normalize_embeddings=True)
            if hasattr(embeddings, "tolist"):
                embeddings = embeddings.tolist()
            
            for i, t in enumerate(valid_texts):
                if not t:
                    embeddings[i] = None
            
            return embeddings
        except Exception as e:
            print(f"[LocalEmbeddingService] 批量Embedding生成失败: {e}")
            return [None] * len(texts)
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """计算余弦相似度
        
        Args:
            embedding1: 向量1
            embedding2: 向量2
            
        Returns:
            相似度（0-1）
        """
        if not embedding1 or not embedding2:
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        norm1 = sum(a ** 2 for a in embedding1) ** 0.5
        norm2 = sum(b ** 2 for b in embedding2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def get_dimension(self) -> int:
        """获取embedding维度"""
        return self.dimension
    
    def is_available(self) -> bool:
        """检查服务是否可用"""
        return self.model is not None
    
    def get_model_info(self) -> dict:
        """获取模型信息"""
        return {
            'model_name': self.model_name,
            'dimension': self.dimension,
            'available': self.is_available(),
            'has_sentence_transformers': HAS_SENTENCE_TRANSFORMERS,
            'allow_remote_download': ALLOW_REMOTE_EMBEDDING_DOWNLOAD,
        }


def get_embedding_service(model_name: str = None) -> LocalEmbeddingService:
    """获取Embedding服务实例
    
    Args:
        model_name: 模型名称（默认m3e-small）
        
    Returns:
        LocalEmbeddingService实例
    """
    return LocalEmbeddingService(model_name=model_name)
