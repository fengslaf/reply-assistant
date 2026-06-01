from typing import List, Dict, Set, Optional
from dataclasses import dataclass
import re
from collections import Counter


@dataclass
class KeywordResult:
    text_id: str
    keywords: List[str]
    keyword_scores: Dict[str, float]
    keyword_positions: Dict[str, List[int]]


class KeywordExtractor:
    
    DEFAULT_STOPWORDS = {
        '的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个',
        '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好',
        '自己', '这', '那', '什么', '他', '她', '它', '们', '这个', '那个', '怎么',
        '可以', '吗', '啊', '吧', '呢', '哦', '嗯', '哈', '呀', '哎', '喂', '谢',
        '您好', '你好', '谢谢', '请问', '感谢', '麻烦', '打扰', '不好意思', '对不起',
    }
    
    def __init__(
        self,
        stopwords: Optional[Set[str]] = None,
        min_keyword_length: int = 2,
        max_keywords: int = 10,
        use_jieba: bool = True
    ):
        self.stopwords = stopwords or self.DEFAULT_STOPWORDS
        self.min_keyword_length = min_keyword_length
        self.max_keywords = max_keywords
        self.use_jieba = use_jieba
        self._jieba_available = self._check_jieba()
    
    def _check_jieba(self) -> bool:
        if not self.use_jieba:
            return False
        try:
            import jieba
            return True
        except ImportError:
            return False
    
    def extract(self, text: str, text_id: Optional[str] = None) -> KeywordResult:
        text_id = text_id or f"text_{hash(text)}"
        
        if self._jieba_available:
            keywords, scores = self._extract_with_jieba(text)
        else:
            keywords, scores = self._extract_with_regex(text)
        
        positions = self._find_positions(text, keywords)
        
        return KeywordResult(
            text_id=text_id,
            keywords=keywords[:self.max_keywords],
            keyword_scores=scores,
            keyword_positions=positions,
        )
    
    def batch_extract(self, texts: List[str], text_ids: Optional[List[str]] = None) -> List[KeywordResult]:
        results = []
        for i, text in enumerate(texts):
            text_id = text_ids[i] if text_ids and i < len(text_ids) else f"text_{i}"
            results.append(self.extract(text, text_id))
        return results
    
    def _extract_with_jieba(self, text: str) -> tuple:
        import jieba
        import jieba.analyse
        
        keywords_with_weights = jieba.analyse.extract_tags(
            text,
            topK=self.max_keywords * 2,
            withWeight=True
        )
        
        keywords = []
        scores = {}
        for word, weight in keywords_with_weights:
            if word not in self.stopwords and len(word) >= self.min_keyword_length:
                keywords.append(word)
                scores[word] = weight
        
        return keywords, scores
    
    def _extract_with_regex(self, text: str) -> tuple:
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]{2,}')
        chinese_words = chinese_pattern.findall(text)
        
        english_pattern = re.compile(r'[a-zA-Z]{3,}')
        english_words = english_pattern.findall(text)
        
        all_words = chinese_words + [w.lower() for w in english_words]
        
        word_freq = Counter(all_words)
        
        keywords = []
        scores = {}
        
        for word, freq in word_freq.most_common(self.max_keywords * 2):
            if word not in self.stopwords:
                keywords.append(word)
                scores[word] = freq / len(all_words) if all_words else 0
        
        return keywords, scores
    
    def _find_positions(self, text: str, keywords: List[str]) -> Dict[str, List[int]]:
        positions = {}
        for keyword in keywords:
            pos = []
            start = 0
            while True:
                idx = text.find(keyword, start)
                if idx == -1:
                    break
                pos.append(idx)
                start = idx + 1
            positions[keyword] = pos
        return positions
    
    def get_keyword_set(self, texts: List[str]) -> Set[str]:
        all_keywords = set()
        for text in texts:
            result = self.extract(text)
            all_keywords.update(result.keywords)
        return all_keywords
    
    def get_common_keywords(self, texts: List[str], min_count: int = 2) -> List[str]:
        keyword_counter = Counter()
        for text in texts:
            result = self.extract(text)
            keyword_counter.update(result.keywords)
        
        return [kw for kw, count in keyword_counter.most_common() if count >= min_count]