"""各个Retriever实现 - 精确/向量/关键词检索"""

import time
import re
import uuid
from typing import List, Dict, Optional
from pathlib import Path

from .data_types import SearchContext, SearchResult


class BaseRetriever:
    """检索器基类"""
    
    def retrieve(self, context: SearchContext, samples: List[Dict]) -> List[SearchResult]:
        """检索方法（子类实现）"""
        raise NotImplementedError
    
    def _normalize_text(self, text: str) -> str:
        """文本归一化"""
        if not text:
            return ""
        
        text = text.strip()
        text = re.sub(r'[^\w\s\u4e00-\u9fff]', '', text)
        text = text.lower()
        
        return text
    
    def _extract_keywords(self, text: str) -> set:
        """提取关键词（简单实现）"""
        normalized = self._normalize_text(text)
        words = normalized.split()
        
        keywords = set()
        for word in words:
            if len(word) >= 2:
                keywords.add(word)
        
        return keywords
    
    def _calc_text_overlap(self, text1: str, text2: str) -> float:
        """计算文本重叠度"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        return intersection / union if union > 0 else 0.0


class ExactRetriever(BaseRetriever):
    """精确匹配检索器"""
    
    def retrieve(self, context: SearchContext, samples: List[Dict]) -> List[SearchResult]:
        """精确匹配检索
        
        Args:
            context: 搜索上下文
            samples: 样本数据列表
            
        Returns:
            SearchResult列表
        """
        start_time = time.time()
        
        query_normalized = self._normalize_text(context.query)
        
        results = []
        
        for idx, sample in enumerate(samples):
            parent_message = sample.get('parent_message', '')
            sample_idx = sample.get('_sample_index', idx)
            parent_normalized = self._normalize_text(parent_message)
            
            if not parent_normalized:
                continue
            
            match_type = None
            confidence = 0.0
            
            if query_normalized == parent_normalized:
                match_type = 'exact'
                confidence = 0.95
            elif query_normalized and parent_normalized:
                if query_normalized in parent_normalized:
                    match_type = 'contains_query'
                    confidence = 0.85
                elif parent_normalized in query_normalized:
                    match_type = 'contains_parent'
                    confidence = 0.80
            
            if match_type:
                for reply_idx, reply in enumerate(sample.get('replies', [])):
                    result = SearchResult(
                        reply_id=f'local_exact_{sample_idx}_{reply_idx}_{uuid.uuid4().hex[:6]}',
                        content=reply,
                        confidence=confidence,
                        source_type='local_exact',
                        source_detail=f'精确匹配(匹配类型={match_type}, 样本ID={sample_idx})',
                        matched_sample_id=str(sample_idx),
                        matched_parent_message=parent_message,
                        retrieval_latency_ms=int((time.time() - start_time) * 1000)
                    )
                    results.append(result)
        
        latency_ms = int((time.time() - start_time) * 1000)
        for r in results:
            r.total_latency_ms = latency_ms
        
        return results[:context.top_k]


class KeywordRetriever(BaseRetriever):
    """关键词匹配检索器"""
    
    def retrieve(self, context: SearchContext, samples: List[Dict]) -> List[SearchResult]:
        """关键词匹配检索
        
        Args:
            context: 搜索上下文
            samples: 样本数据列表
            
        Returns:
            SearchResult列表
        """
        start_time = time.time()
        
        query_keywords = self._extract_keywords(context.query)
        
        results = []
        
        for idx, sample in enumerate(samples):
            parent_message = sample.get('parent_message', '')
            sample_idx = sample.get('_sample_index', idx)
            sample_keywords = set(sample.get('keywords', []))
            
            intersection = len(query_keywords & sample_keywords)
            
            if intersection > 0:
                union = len(query_keywords | sample_keywords)
                jaccard_score = intersection / union
                
                overlap_score = self._calc_text_overlap(
                    self._normalize_text(context.query),
                    self._normalize_text(parent_message)
                )
                
                confidence = jaccard_score * 0.7 + overlap_score * 0.3
                
                if sample.get('scene_tag') and context.scene_hint:
                    if sample['scene_tag'] == context.scene_hint:
                        confidence += 0.15
                
                confidence = min(confidence, 1.0)
                
                for reply_idx, reply in enumerate(sample.get('replies', [])):
                    result = SearchResult(
                        reply_id=f'local_keyword_{sample_idx}_{reply_idx}_{uuid.uuid4().hex[:6]}',
                        content=reply,
                        confidence=confidence,
                        source_type='local_keyword',
                        source_detail=f'关键词匹配(关键词交集={intersection}, Jaccard={jaccard_score:.2f}, 样本ID={sample_idx})',
                        matched_sample_id=str(sample_idx),
                        matched_parent_message=parent_message,
                        retrieval_latency_ms=int((time.time() - start_time) * 1000)
                    )
                    results.append(result)
        
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        latency_ms = int((time.time() - start_time) * 1000)
        for r in results:
            r.total_latency_ms = latency_ms
        
        return results[:context.top_k]


class VectorRetriever(BaseRetriever):
    """向量检索器"""
    
    def __init__(self, embedding_service=None, chroma_repo=None):
        """初始化
        
        Args:
            embedding_service: Embedding生成服务（可选）
            chroma_repo: Chroma向量库（可选）
        """
        self.embedding_service = embedding_service
        self.chroma_repo = chroma_repo
    
    def retrieve(self, context: SearchContext, samples: List[Dict]) -> List[SearchResult]:
        """向量检索
        
        Args:
            context: 搜索上下文
            samples: 样本数据列表（备用，当向量库不可用时）
            
        Returns:
            SearchResult列表
        """
        start_time = time.time()
        
        if not self.embedding_service or not self.embedding_service.is_available():
            return self._fallback_retrieve(context, samples, start_time)
        
        if not self.chroma_repo:
            return self._fallback_retrieve(context, samples, start_time)
        
        query_embedding = self.embedding_service.embed(context.query)
        
        if not query_embedding:
            return self._fallback_retrieve(context, samples, start_time)
        
        user_id = 'default_user'
        
        similar_items = self.chroma_repo.search_similar(
            user_id=user_id,
            query_embedding=query_embedding,
            top_k=context.top_k
        )
        
        results = []
        
        for item in similar_items:
            sample_id = item.get('sample_id', '')
            parent_message = item.get('parent_message', '')
            distance = item.get('distance', 0)
            metadata = item.get('metadata', {})
            
            similarity = 1 - distance
            confidence = min(max(similarity, 0), 1)
            
            advisor_reply = metadata.get('advisor_reply', '')
            
            if advisor_reply:
                result = SearchResult(
                    reply_id=f'local_vector_{sample_id}_{uuid.uuid4().hex[:6]}',
                    content=advisor_reply,
                    confidence=confidence,
                    source_type='local_vector',
                    source_detail=f'向量检索(moka-ai/m3e-small, 相似度={similarity:.2f}, 样本ID={sample_id})',
                    matched_sample_id=sample_id,
                    matched_parent_message=parent_message,
                    retrieval_latency_ms=int((time.time() - start_time) * 1000)
                )
                results.append(result)
        
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        latency_ms = int((time.time() - start_time) * 1000)
        for r in results:
            r.total_latency_ms = latency_ms
        
        return results[:context.top_k]
    
    def _fallback_retrieve(self, context: SearchContext, samples: List[Dict], start_time: float) -> List[SearchResult]:
        """降级检索（当向量库不可用时，使用文本重叠度）"""
        
        results = []
        
        for idx, sample in enumerate(samples):
            parent_message = sample.get('parent_message', '')
            sample_idx = sample.get('_sample_index', idx)
            
            overlap = self._calc_text_overlap(
                self._normalize_text(context.query),
                self._normalize_text(parent_message)
            )
            
            if overlap > 0.2:
                confidence = overlap
                
                for reply_idx, reply in enumerate(sample.get('replies', [])):
                    result = SearchResult(
                        reply_id=f'local_vector_fallback_{sample_idx}_{reply_idx}_{uuid.uuid4().hex[:6]}',
                        content=reply,
                        confidence=confidence,
                        source_type='local_vector',
                        source_detail=f'向量检索降级(文本重叠={overlap:.2f}, 样本ID={sample_idx})',
                        matched_sample_id=str(sample_idx),
                        matched_parent_message=parent_message,
                        retrieval_latency_ms=int((time.time() - start_time) * 1000)
                    )
                    results.append(result)
        
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        latency_ms = int((time.time() - start_time) * 1000)
        for r in results:
            r.total_latency_ms = latency_ms
        
        return results[:context.top_k]


class HybridRetriever(BaseRetriever):
    """混合检索器（整合精确+向量+关键词）"""
    
    def __init__(self, embedding_service=None, chroma_repo=None):
        """初始化
        
        Args:
            embedding_service: Embedding生成服务（可选）
            chroma_repo: Chroma向量库（可选）
        """
        self.exact_retriever = ExactRetriever()
        self.vector_retriever = VectorRetriever(embedding_service, chroma_repo)
        self.keyword_retriever = KeywordRetriever()
    
    def retrieve(self, context: SearchContext, samples: List[Dict]) -> List[SearchResult]:
        """混合检索
        
        Args:
            context: 搜索上下文
            samples: 样本数据列表
            
        Returns:
            SearchResult列表
        """
        start_time = time.time()
        
        exact_results = self.exact_retriever.retrieve(context, samples)
        
        if exact_results and any(r.confidence >= 0.95 for r in exact_results):
            return exact_results
        
        vector_results = self.vector_retriever.retrieve(context, samples)
        keyword_results = self.keyword_retriever.retrieve(context, samples)
        
        all_results = []
        seen_ids = set()
        
        for r in exact_results:
            if r.matched_sample_id not in seen_ids:
                seen_ids.add(r.matched_sample_id)
                all_results.append(r)
        
        for r in vector_results:
            if r.matched_sample_id not in seen_ids:
                seen_ids.add(r.matched_sample_id)
                all_results.append(r)
        
        for r in keyword_results:
            if r.matched_sample_id not in seen_ids:
                seen_ids.add(r.matched_sample_id)
                all_results.append(r)
        
        all_results.sort(key=lambda x: x.confidence, reverse=True)
        
        latency_ms = int((time.time() - start_time) * 1000)
        for r in all_results:
            r.total_latency_ms = latency_ms
        
        return all_results[:context.top_k]
