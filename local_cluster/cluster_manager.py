from typing import List, Dict, Optional
from .keyword_extractor import KeywordExtractor
from .similarity_calculator import SimilarityCalculator, SimilarityMethod
from .cluster_engine import ClusterEngine, ClusterReport


class LocalClusterManager:
    
    def __init__(
        self,
        similarity_threshold: float = 0.3,
        min_cluster_size: int = 2,
        similarity_method: SimilarityMethod = SimilarityMethod.JACCARD
    ):
        self.cluster_engine = ClusterEngine(
            similarity_threshold=similarity_threshold,
            min_cluster_size=min_cluster_size,
            similarity_method=similarity_method
        )
        self.keyword_extractor = KeywordExtractor()
        self.similarity_calculator = SimilarityCalculator(
            method=similarity_method,
            keyword_extractor=self.keyword_extractor
        )
        
        self._last_report: Optional[ClusterReport] = None
    
    def cluster_samples(
        self,
        samples: List[str],
        method: str = "greedy"
    ) -> ClusterReport:
        self._last_report = self.cluster_engine.cluster_texts(samples, method=method)
        return self._last_report
    
    def cluster_by_keywords(
        self,
        samples: List[str],
        keywords: Optional[List[str]] = None
    ) -> Dict[str, List[str]]:
        if keywords is None:
            common_keywords = self.keyword_extractor.get_common_keywords(samples, min_count=2)
        else:
            common_keywords = keywords
        
        keyword_groups: Dict[str, List[str]] = {}
        
        for sample in samples:
            sample_keywords = self.keyword_extractor.extract(sample).keywords
            
            matched_keyword = None
            for kw in common_keywords:
                if kw in sample_keywords:
                    matched_keyword = kw
                    break
            
            if matched_keyword:
                if matched_keyword not in keyword_groups:
                    keyword_groups[matched_keyword] = []
                keyword_groups[matched_keyword].append(sample)
            else:
                if "其他" not in keyword_groups:
                    keyword_groups["其他"] = []
                keyword_groups["其他"].append(sample)
        
        return keyword_groups
    
    def find_similar_samples(
        self,
        query: str,
        samples: List[str],
        top_k: int = 5,
        threshold: float = 0.3
    ) -> List[Dict]:
        results = []
        
        for i, sample in enumerate(samples):
            sim_result = self.similarity_calculator.calculate(query, sample)
            
            if sim_result.similarity >= threshold:
                results.append({
                    'index': i,
                    'sample': sample,
                    'similarity': sim_result.similarity,
                    'common_keywords': sim_result.common_keywords,
                })
        
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
    
    def get_sample_keywords(self, sample: str) -> List[str]:
        return self.keyword_extractor.extract(sample).keywords
    
    def get_all_keywords(self, samples: List[str]) -> Dict:
        keyword_counter: Dict[str, int] = {}
        
        for sample in samples:
            keywords = self.keyword_extractor.extract(sample).keywords
            for kw in keywords:
                keyword_counter[kw] = keyword_counter.get(kw, 0) + 1
        
        sorted_keywords = sorted(
            keyword_counter.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return {
            'keywords': [kw for kw, count in sorted_keywords],
            'counts': dict(sorted_keywords),
            'total_unique': len(keyword_counter),
        }
    
    def get_last_report(self) -> Optional[ClusterReport]:
        return self._last_report
    
    def get_cluster_summary(self) -> Optional[str]:
        if self._last_report:
            return self.cluster_engine.get_cluster_summary(self._last_report)
        return None
    
    def analyze_duplicates(
        self,
        samples: List[str],
        duplicate_threshold: float = 0.8
    ) -> Dict:
        duplicates = []
        
        for i in range(len(samples)):
            for j in range(i + 1, len(samples)):
                sim = self.similarity_calculator.calculate(samples[i], samples[j])
                
                if sim.similarity >= duplicate_threshold:
                    duplicates.append({
                        'index_1': i,
                        'index_2': j,
                        'similarity': sim.similarity,
                        'sample_1': samples[i][:50],
                        'sample_2': samples[j][:50],
                    })
        
        return {
            'duplicate_pairs': duplicates,
            'duplicate_count': len(duplicates),
            'duplicate_ratio': len(duplicates) / (len(samples) * (len(samples) - 1) / 2) if len(samples) > 1 else 0,
        }
    
    def suggest_categories(
        self,
        samples: List[str],
        max_categories: int = 10
    ) -> List[Dict]:
        keywords_info = self.get_all_keywords(samples)
        
        categories = []
        for kw, count in sorted(keywords_info['counts'].items(), key=lambda x: x[1], reverse=True):
            if count >= 2:
                matching_samples = [s for s in samples if kw in self.get_sample_keywords(s)]
                categories.append({
                    'category': kw,
                    'count': count,
                    'sample_count': len(matching_samples),
                    'samples_preview': matching_samples[:3],
                })
            
            if len(categories) >= max_categories:
                break
        
        return categories