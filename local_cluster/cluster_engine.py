from typing import List, Dict, Optional
from dataclasses import dataclass, field
import json
from .keyword_extractor import KeywordExtractor
from .similarity_calculator import SimilarityCalculator, SimilarityMethod


@dataclass
class ClusterResult:
    cluster_id: str
    texts: List[str]
    text_ids: List[str]
    keywords: List[str]
    centroid_keywords: List[str]
    member_count: int
    intra_similarity: float


@dataclass
class ClusterReport:
    clusters: List[ClusterResult]
    total_texts: int
    total_clusters: int
    method: str
    threshold: float
    statistics: Dict = field(default_factory=dict)


class ClusterEngine:
    
    def __init__(
        self,
        similarity_threshold: float = 0.3,
        min_cluster_size: int = 2,
        similarity_method: SimilarityMethod = SimilarityMethod.JACCARD
    ):
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self.similarity_method = similarity_method
        self.keyword_extractor = KeywordExtractor()
        self.similarity_calculator = SimilarityCalculator(
            method=similarity_method,
            keyword_extractor=self.keyword_extractor
        )
    
    def cluster_texts(
        self,
        texts: List[str],
        text_ids: Optional[List[str]] = None,
        method: str = "greedy"
    ) -> ClusterReport:
        ids = text_ids or [f"text_{i}" for i in range(len(texts))]
        
        if method == "greedy":
            clusters = self._greedy_clustering(texts, ids)
        elif method == "hierarchical":
            clusters = self._hierarchical_clustering(texts, ids)
        elif method == "keyword_group":
            clusters = self._keyword_grouping(texts, ids)
        else:
            clusters = self._greedy_clustering(texts, ids)
        
        total_intra_sim = sum(c.intra_similarity for c in clusters if c.member_count > 1)
        avg_intra_sim = total_intra_sim / len(clusters) if clusters else 0
        
        statistics = {
            'avg_cluster_size': sum(c.member_count for c in clusters) / len(clusters) if clusters else 0,
            'avg_intra_similarity': avg_intra_sim,
            'max_cluster_size': max(c.member_count for c in clusters) if clusters else 0,
            'min_cluster_size': min(c.member_count for c in clusters) if clusters else 0,
            'singleton_count': sum(1 for c in clusters if c.member_count == 1),
        }
        
        return ClusterReport(
            clusters=clusters,
            total_texts=len(texts),
            total_clusters=len(clusters),
            method=method,
            threshold=self.similarity_threshold,
            statistics=statistics,
        )
    
    def _greedy_clustering(self, texts: List[str], ids: List[str]) -> List[ClusterResult]:
        clusters: List[ClusterResult] = []
        assigned = set()
        
        sim_matrix = self.similarity_calculator.build_similarity_matrix(texts, ids)
        
        for i, id1 in enumerate(ids):
            if id1 in assigned:
                continue
            
            cluster_texts = [texts[i]]
            cluster_ids = [id1]
            cluster_keywords = self.keyword_extractor.extract(texts[i]).keywords
            
            assigned.add(id1)
            
            for j, id2 in enumerate(ids):
                if id2 in assigned:
                    continue
                
                if sim_matrix[id1][id2] >= self.similarity_threshold:
                    cluster_texts.append(texts[j])
                    cluster_ids.append(id2)
                    assigned.add(id2)
                    
                    kw2 = self.keyword_extractor.extract(texts[j]).keywords
                    cluster_keywords.extend(kw2)
            
            from collections import Counter
            keyword_counter = Counter(cluster_keywords)
            centroid_keywords = [k for k, _ in keyword_counter.most_common(5)]
            
            intra_sim = 0.0
            if len(cluster_ids) > 1:
                total_sim = 0
                count = 0
                for a in cluster_ids:
                    for b in cluster_ids:
                        if a != b:
                            total_sim += sim_matrix[a][b]
                            count += 1
                intra_sim = total_sim / count if count > 0 else 0
            
            clusters.append(ClusterResult(
                cluster_id=f"cluster_{len(clusters)}",
                texts=cluster_texts,
                text_ids=cluster_ids,
                keywords=list(set(cluster_keywords)),
                centroid_keywords=centroid_keywords,
                member_count=len(cluster_texts),
                intra_similarity=intra_sim,
            ))
        
        return [c for c in clusters if c.member_count >= self.min_cluster_size or c.member_count == 1]
    
    def _hierarchical_clustering(self, texts: List[str], ids: List[str]) -> List[ClusterResult]:
        sim_matrix = self.similarity_calculator.build_similarity_matrix(texts, ids)
        
        clusters = [[id] for id in ids]
        
        while len(clusters) > 1:
            best_merge = None
            best_sim = -1
            
            for i in range(len(clusters)):
                for j in range(i + 1, len(clusters)):
                    avg_sim = self._avg_cluster_similarity(
                        clusters[i], clusters[j], sim_matrix
                    )
                    
                    if avg_sim >= self.similarity_threshold and avg_sim > best_sim:
                        best_sim = avg_sim
                        best_merge = (i, j)
            
            if best_merge is None:
                break
            
            i, j = best_merge
            clusters[i] = clusters[i] + clusters[j]
            clusters.pop(j)
        
        results = []
        for i, cluster_ids in enumerate(clusters):
            cluster_texts = [texts[ids.index(id)] for id in cluster_ids]
            
            all_keywords = []
            for text in cluster_texts:
                all_keywords.extend(self.keyword_extractor.extract(text).keywords)
            
            from collections import Counter
            keyword_counter = Counter(all_keywords)
            centroid_keywords = [k for k, _ in keyword_counter.most_common(5)]
            
            intra_sim = 0.0
            if len(cluster_ids) > 1:
                intra_sim = self._avg_cluster_similarity(
                    cluster_ids, cluster_ids, sim_matrix
                )
            
            results.append(ClusterResult(
                cluster_id=f"cluster_{i}",
                texts=cluster_texts,
                text_ids=cluster_ids,
                keywords=list(set(all_keywords)),
                centroid_keywords=centroid_keywords,
                member_count=len(cluster_texts),
                intra_similarity=intra_sim,
            ))
        
        return results
    
    def _keyword_grouping(self, texts: List[str], ids: List[str]) -> List[ClusterResult]:
        keyword_to_texts: Dict[str, List[int]] = {}
        
        for i, text in enumerate(texts):
            kw_result = self.keyword_extractor.extract(text)
            for kw in kw_result.keywords:
                if kw not in keyword_to_texts:
                    keyword_to_texts[kw] = []
                keyword_to_texts[kw].append(i)
        
        clusters = []
        assigned = set()
        
        sorted_keywords = sorted(
            keyword_to_texts.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )
        
        for keyword, indices in sorted_keywords:
            if len(indices) < self.min_cluster_size:
                continue
            
            cluster_indices = [i for i in indices if i not in assigned]
            
            if len(cluster_indices) < self.min_cluster_size:
                continue
            
            cluster_texts = [texts[i] for i in cluster_indices]
            cluster_ids = [ids[i] for i in cluster_indices]
            
            for i in cluster_indices:
                assigned.add(i)
            
            all_keywords = []
            for text in cluster_texts:
                all_keywords.extend(self.keyword_extractor.extract(text).keywords)
            
            from collections import Counter
            keyword_counter = Counter(all_keywords)
            centroid_keywords = [k for k, _ in keyword_counter.most_common(5)]
            
            sim_matrix = self.similarity_calculator.build_similarity_matrix(cluster_texts, cluster_ids)
            intra_sim = 0.0
            if len(cluster_ids) > 1:
                total_sim = 0
                count = 0
                for a in cluster_ids:
                    for b in cluster_ids:
                        if a != b:
                            total_sim += sim_matrix[a][b]
                            count += 1
                intra_sim = total_sim / count if count > 0 else 0
            
            clusters.append(ClusterResult(
                cluster_id=f"cluster_{keyword}",
                texts=cluster_texts,
                text_ids=cluster_ids,
                keywords=list(set(all_keywords)),
                centroid_keywords=centroid_keywords,
                member_count=len(cluster_texts),
                intra_similarity=intra_sim,
            ))
        
        for i, id in enumerate(ids):
            if i not in assigned:
                clusters.append(ClusterResult(
                    cluster_id=f"singleton_{id}",
                    texts=[texts[i]],
                    text_ids=[id],
                    keywords=self.keyword_extractor.extract(texts[i]).keywords,
                    centroid_keywords=self.keyword_extractor.extract(texts[i]).keywords[:5],
                    member_count=1,
                    intra_similarity=0.0,
                ))
        
        return clusters
    
    def _avg_cluster_similarity(
        self,
        cluster1: List[str],
        cluster2: List[str],
        sim_matrix: Dict[str, Dict[str, float]]
    ) -> float:
        if not cluster1 or not cluster2:
            return 0.0
        
        total = 0
        count = 0
        
        for id1 in cluster1:
            for id2 in cluster2:
                if id1 != id2:
                    total += sim_matrix[id1][id2]
                    count += 1
        
        return total / count if count > 0 else 0.0
    
    def get_cluster_summary(self, report: ClusterReport) -> str:
        lines = []
        lines.append(f"聚类总数: {report.total_clusters}")
        lines.append(f"文本总数: {report.total_texts}")
        lines.append(f"方法: {report.method}")
        lines.append(f"阈值: {report.threshold}")
        lines.append("")
        
        for cluster in report.clusters:
            lines.append(f"【{cluster.cluster_id}】")
            lines.append(f"  成员数: {cluster.member_count}")
            lines.append(f"  关键词: {', '.join(cluster.centroid_keywords)}")
            lines.append(f"  内部相似度: {cluster.intra_similarity:.3f}")
            for i, text in enumerate(cluster.texts[:3]):
                preview = text[:50] + "..." if len(text) > 50 else text
                lines.append(f"    - {preview}")
            lines.append("")
        
        return "\n".join(lines)