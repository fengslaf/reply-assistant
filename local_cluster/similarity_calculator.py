from typing import List, Dict, Set, Optional
from dataclasses import dataclass
from enum import Enum
import math
from collections import Counter


class SimilarityMethod(Enum):
    JACCARD = "jaccard"
    COSINE = "cosine"
    DICE = "dice"
    OVERLAP = "overlap"
    TF_IDF = "tfidf"


@dataclass
class SimilarityResult:
    text_id_1: str
    text_id_2: str
    similarity: float
    method: SimilarityMethod
    common_keywords: List[str]
    details: Dict


class SimilarityCalculator:
    
    def __init__(
        self,
        method: SimilarityMethod = SimilarityMethod.JACCARD,
        keyword_extractor: Optional['KeywordExtractor'] = None
    ):
        self.method = method
        self.keyword_extractor = keyword_extractor
        
        if keyword_extractor is None:
            from .keyword_extractor import KeywordExtractor
            self.keyword_extractor = KeywordExtractor()
    
    def calculate(
        self,
        text1: str,
        text2: str,
        text_id_1: Optional[str] = None,
        text_id_2: Optional[str] = None,
        method: Optional[SimilarityMethod] = None
    ) -> SimilarityResult:
        use_method = method or self.method
        
        kw1 = self.keyword_extractor.extract(text1, text_id_1)
        kw2 = self.keyword_extractor.extract(text2, text_id_2)
        
        set1 = set(kw1.keywords)
        set2 = set(kw2.keywords)
        
        if use_method == SimilarityMethod.JACCARD:
            similarity = self._jaccard(set1, set2)
        elif use_method == SimilarityMethod.COSINE:
            similarity = self._cosine(kw1.keyword_scores, kw2.keyword_scores)
        elif use_method == SimilarityMethod.DICE:
            similarity = self._dice(set1, set2)
        elif use_method == SimilarityMethod.OVERLAP:
            similarity = self._overlap(set1, set2)
        elif use_method == SimilarityMethod.TF_IDF:
            similarity = self._tfidf_cosine(kw1.keywords, kw2.keywords)
        else:
            similarity = self._jaccard(set1, set2)
        
        common = list(set1 & set2)
        
        return SimilarityResult(
            text_id_1=kw1.text_id,
            text_id_2=kw2.text_id,
            similarity=similarity,
            method=use_method,
            common_keywords=common,
            details={
                'keywords_1': kw1.keywords,
                'keywords_2': kw2.keywords,
                'intersection_size': len(common),
                'union_size': len(set1 | set2),
            }
        )
    
    def batch_calculate(
        self,
        texts: List[str],
        text_ids: Optional[List[str]] = None,
        threshold: float = 0.0
    ) -> List[SimilarityResult]:
        results = []
        
        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                id1 = text_ids[i] if text_ids else f"text_{i}"
                id2 = text_ids[j] if text_ids else f"text_{j}"
                
                sim = self.calculate(texts[i], texts[j], id1, id2)
                
                if sim.similarity >= threshold:
                    results.append(sim)
        
        return sorted(results, key=lambda x: x.similarity, reverse=True)
    
    def build_similarity_matrix(
        self,
        texts: List[str],
        text_ids: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, float]]:
        ids = text_ids or [f"text_{i}" for i in range(len(texts))]
        
        matrix = {}
        for i, id1 in enumerate(ids):
            matrix[id1] = {}
            for j, id2 in enumerate(ids):
                if i == j:
                    matrix[id1][id2] = 1.0
                else:
                    sim = self.calculate(texts[i], texts[j], id1, id2)
                    matrix[id1][id2] = sim.similarity
        
        return matrix
    
    def _jaccard(self, set1: Set[str], set2: Set[str]) -> float:
        if not set1 and not set2:
            return 1.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0
    
    def _cosine(self, scores1: Dict[str, float], scores2: Dict[str, float]) -> float:
        if not scores1 or not scores2:
            return 0.0
        
        common_keys = set(scores1.keys()) & set(scores2.keys())
        
        if not common_keys:
            return 0.0
        
        dot_product = sum(scores1[k] * scores2[k] for k in common_keys)
        
        norm1 = math.sqrt(sum(v ** 2 for v in scores1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in scores2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _dice(self, set1: Set[str], set2: Set[str]) -> float:
        if not set1 and not set2:
            return 1.0
        
        intersection = len(set1 & set2)
        total = len(set1) + len(set2)
        
        return 2 * intersection / total if total > 0 else 0.0
    
    def _overlap(self, set1: Set[str], set2: Set[str]) -> float:
        if not set1 and not set2:
            return 1.0
        
        intersection = len(set1 & set2)
        min_size = min(len(set1), len(set2))
        
        return intersection / min_size if min_size > 0 else 0.0
    
    def _tfidf_cosine(self, keywords1: List[str], keywords2: List[str]) -> float:
        if not keywords1 or not keywords2:
            return 0.0
        
        counter1 = Counter(keywords1)
        counter2 = Counter(keywords2)
        
        all_keys = set(counter1.keys()) | set(counter2.keys())
        
        vec1 = [counter1.get(k, 0) for k in all_keys]
        vec2 = [counter2.get(k, 0) for k in all_keys]
        
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a ** 2 for a in vec1))
        norm2 = math.sqrt(sum(b ** 2 for b in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot / (norm1 * norm2)