"""本地检索引擎主类 - V2.03集成智能增强"""

import hashlib
import json
import time
from pathlib import Path
from typing import List, Dict, Optional

from .data_types import SearchContext, SearchResult, WeightConfig
from .retrievers import ExactRetriever, KeywordRetriever, VectorRetriever, HybridRetriever
from .score_calculator import ScoreCalculator
from .weight_config import WeightConfigManager
from .source_marker import SourceMarker
from .embedding_service import LocalEmbeddingService
from .chroma_repo import LocalChromaRepo

try:
    from local_intelligence import IntelligenceManager
    HAS_INTELLIGENCE = True
except ImportError:
    HAS_INTELLIGENCE = False


class LocalSearchEngine:
    """本地检索引擎 - V2.03
    
    新增：
    - 意图识别前置过滤
    - 实体抽取辅助匹配
    - 向量检索启用（moka-ai/m3e-small + Chroma）
    """
    
    def __init__(self, data_path: str = None, 
                 embedding_service=None, 
                 chroma_repo=None,
                 weight_config_path: str = None,
                 enable_intelligence: bool = True):
        """初始化
        
        Args:
            data_path: 样本数据路径（local_data.json）
            embedding_service: Embedding生成服务（可选，默认创建）
            chroma_repo: Chroma向量库（可选，默认创建）
            weight_config_path: 权重配置路径（可选）
            enable_intelligence: 是否启用智能增强（默认True）
        """
        self.data_path = Path(data_path) if data_path else self._get_default_data_path()
        
        self.embedding_service = embedding_service or LocalEmbeddingService()
        self.chroma_repo = chroma_repo or LocalChromaRepo()
        
        self.samples = self._load_samples()
        
        self.weight_config_manager = WeightConfigManager(weight_config_path)
        self.weight_config = self.weight_config_manager.load_config()
        
        self.score_calculator = ScoreCalculator(self.weight_config)
        self.source_marker = SourceMarker()
        
        self.enable_intelligence = enable_intelligence and HAS_INTELLIGENCE
        self.intelligence_manager = IntelligenceManager() if self.enable_intelligence else None
        
        self.retrievers = {
            'exact': ExactRetriever(),
            'keyword': KeywordRetriever(),
            'vector': VectorRetriever(self.embedding_service, self.chroma_repo),
            'hybrid': HybridRetriever(self.embedding_service, self.chroma_repo)
        }
        
        self._sync_to_vector_store()
    
    def _get_default_data_path(self) -> Path:
        """获取默认数据路径"""
        return Path(__file__).parent.parent / 'data' / 'local_data.json'
    
    def _load_samples(self) -> List[Dict]:
        """加载样本数据"""
        if not self.data_path.exists():
            return []
        
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return data.get('samples', [])
        except Exception:
            return []
    
    def _sync_to_vector_store(self):
        """同步样本到向量库"""
        if not self.embedding_service.is_available():
            return
        
        if not self.chroma_repo.is_available():
            return
        
        self.chroma_repo.sync_from_local_data(
            self.samples,
            self.embedding_service,
            data_signature=self._get_data_signature(),
        )

    def _get_data_signature(self) -> str:
        """Return a lightweight signature for detecting source data changes."""
        try:
            if self.data_path.exists():
                stat = self.data_path.stat()
                return f"{self.data_path}|{stat.st_mtime_ns}|{len(self.samples)}"
        except Exception:
            pass
        return f"{self.data_path}|missing|{len(self.samples)}"

    def _build_sample_id(self, sample: Dict) -> str:
        created_at = str(sample.get('created_at') or '').strip()
        if created_at:
            source = f"created_at::{created_at}"
        else:
            source = json.dumps({
                'parent_message': sample.get('parent_message', ''),
                'replies': sample.get('replies', []),
                'scene_tag': sample.get('scene_tag', ''),
                'stage_tag': sample.get('stage_tag', ''),
                'keywords': sample.get('keywords', []),
            }, ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(source.encode('utf-8')).hexdigest()
    
    def reload_samples(self):
        """重新加载样本数据"""
        self.samples = self._load_samples()
        self._sync_to_vector_store()
    
    def update_weights(self, weight_config: WeightConfig):
        """更新权重配置
        
        Args:
            weight_config: 新的权重配置
        """
        self.weight_config_manager.save_config(weight_config)
        self.weight_config = weight_config
        self.score_calculator.update_weights(weight_config)
    
    def search(self, context: SearchContext) -> List[SearchResult]:
        """执行检索 - V2.03增强版
        
        Args:
            context: 搜索上下文
            
        Returns:
            SearchResult列表
        """
        start_time = time.time()
        
        analysis = None
        filtered_samples = self.samples
        
        if self.enable_intelligence and self.intelligence_manager:
            analysis = self.intelligence_manager.analyze(context.query)
            
            intent = analysis.intent_result.intent if hasattr(analysis, 'intent_result') else 'unknown'
            if intent and intent != 'unknown':
                filtered_samples = self._filter_by_intent(intent)
                context.intent = intent
                
                if context.scene_hint is None:
                    scene_hint_map = {
                        'price': '价格',
                        'course': '课程',
                        'teacher': '老师',
                        'schedule': '时间',
                        'location': '地址',
                        'enroll': '报名',
                        'refund': '退费',
                        'contact': '电话',
                    }
                    context.scene_hint = scene_hint_map.get(intent)
            
            if hasattr(analysis, 'entity_result') and analysis.entity_result.entities:
                entity_dict = {k: [e.value for e in v] for k, v in analysis.entity_result.entities.items()}
                context.entities = entity_dict
        
        if context.mode not in self.retrievers:
            raise ValueError(f"无效的检索模式: {context.mode}")
        
        retriever = self.retrievers[context.mode]
        
        results = retriever.retrieve(context, filtered_samples)
        
        quality_scores = self._get_quality_scores()
        results = self.score_calculator.apply_quality_weight(results, quality_scores)
        
        if context.scene_hint:
            results = self.score_calculator.apply_scene_weight(results, context.scene_hint)
        
        results = self.score_calculator.calculate_final_scores(results)
        
        for result in results:
            intelligence_info = {}
            if analysis:
                intelligence_info['意图'] = analysis.intent_result.intent if hasattr(analysis, 'intent_result') else 'unknown'
                intelligence_info['置信度'] = f"{analysis.intent_result.confidence:.2f}" if hasattr(analysis, 'intent_result') else '0.00'
            
            result = self.source_marker.mark(result, intelligence_info)
        
        total_latency = int((time.time() - start_time) * 1000)
        for result in results:
            result.total_latency_ms = total_latency
        
        return results[:context.top_k]
    
    def _filter_by_intent(self, intent: str) -> List[Dict]:
        """根据意图过滤样本
        
        Args:
            intent: 意图类型
            
        Returns:
            过滤后的样本列表
        """
        intent_scene_map = {
            'price': ['问价格', '价格', '费用'],
            'course': ['问课程', '课程', '内容'],
            'teacher': ['问师资', '老师', '师资'],
            'schedule': ['问时间', '时间', '课时'],
            'location': ['问地址', '地址', '位置'],
            'enroll': ['报名', '怎么报'],
            'refund': ['退费', '退款'],
            'contact': ['联系方式', '电话']
        }
        
        scene_tags = intent_scene_map.get(intent, [])
        
        if not scene_tags:
            return self.samples
        
        filtered = []
        for idx, sample in enumerate(self.samples):
            scene_tag = sample.get('scene_tag', '')
            if scene_tag in scene_tags:
                sample_copy = dict(sample)
                sample_copy['_sample_index'] = idx
                filtered.append(sample_copy)
        
        return filtered if filtered else self.samples
    
    def _get_quality_scores(self) -> Dict[str, float]:
        """获取样本质量分数"""
        quality_scores = {}
        
        for idx, sample in enumerate(self.samples):
            quality = sample.get('quality_score', 1.0)
            quality_scores[str(idx)] = quality
        
        return quality_scores
    
    def get_available_modes(self) -> List[str]:
        """获取可用的检索模式"""
        return ['exact', 'keyword', 'vector', 'hybrid']
    
    def get_mode_description(self, mode: str) -> str:
        """获取检索模式描述"""
        descriptions = {
            'exact': '精确匹配 - 完全匹配或包含匹配',
            'keyword': '关键词匹配 - 基于关键词词库匹配',
            'vector': '向量检索 - 基于语义相似度匹配（m3e-small）',
            'hybrid': '混合检索 - 整合精确+向量+关键词'
        }
        
        return descriptions.get(mode, '未知模式')
    
    def get_sample_count(self) -> int:
        """获取样本数量"""
        return len(self.samples)
    
    def add_sample(self, sample: Dict):
        """添加样本
        
        Args:
            sample: 样本数据
        """
        self.samples.append(sample)
        
        self._save_samples()
        
        if self.embedding_service.is_available() and self.chroma_repo.is_available():
            parent_message = sample.get('parent_message', '')
            embedding = self.embedding_service.embed(parent_message)
            
            if embedding:
                sample_id = self._build_sample_id(sample)
                metadata = {
                    'scene_tag': sample.get('scene_tag', ''),
                    'stage_tag': sample.get('stage_tag', ''),
                    'quality_score': sample.get('quality_score', 1.0),
                    'advisor_reply': sample.get('replies', [''])[0][:200] if sample.get('replies') else ''
                }
                
                self.chroma_repo.add_sample(
                    sample_id=sample_id,
                    parent_message=parent_message,
                    embedding=embedding,
                    metadata=metadata
                )
    
    def _save_samples(self):
        """保存样本数据"""
        data = {
            'samples': self.samples,
            'config': {
                'last_updated': time.strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_stats(self) -> Dict:
        """获取检索引擎统计信息"""
        return {
            'sample_count': len(self.samples),
            'vector_sample_count': self.chroma_repo.get_count() if self.chroma_repo else 0,
            'vector_available': self.embedding_service and self.embedding_service.is_available(),
            'chroma_available': self.chroma_repo and self.chroma_repo.is_available(),
            'intelligence_enabled': self.enable_intelligence,
            'weight_config': self.weight_config.to_dict(),
            'data_path': str(self.data_path),
            'embedding_model': self.embedding_service.get_model_info() if self.embedding_service else None
        }
    
    def analyze_query(self, query: str) -> Dict:
        """分析用户问题（智能增强）
        
        Args:
            query: 用户问题
            
        Returns:
            分析结果（意图、实体、质量评分等）
        """
        if not self.enable_intelligence or not self.intelligence_manager:
            return {
                'intent': 'unknown',
                'confidence': 0,
                'entities': {},
                'intelligence_enabled': False
            }
        
        result = self.intelligence_manager.analyze(query)
        
        entities = {}
        if hasattr(result, 'entity_result') and result.entity_result.entities:
            entities = {k: [e.value for e in v] for k, v in result.entity_result.entities.items()}
        
        return {
            'intent': result.intent_result.intent if hasattr(result, 'intent_result') else 'unknown',
            'confidence': result.intent_result.confidence if hasattr(result, 'intent_result') else 0,
            'entities': entities,
            'matched_keywords': result.intent_result.matched_keywords if hasattr(result, 'intent_result') else [],
            'intelligence_enabled': True
        }
