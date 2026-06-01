from typing import List, Optional, Dict, Set
from datetime import datetime, timedelta
from .data_types import ConversationTurn, TurnRole


class ContextRetriever:
    
    def __init__(self):
        self.keywords_cache: Dict[str, Set[str]] = {}
    
    def retrieve_by_time_range(
        self,
        turns: List[ConversationTurn],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[ConversationTurn]:
        if not start_time and not end_time:
            return turns
        
        result = []
        for turn in turns:
            if start_time and turn.timestamp < start_time:
                continue
            if end_time and turn.timestamp > end_time:
                continue
            result.append(turn)
        
        return result
    
    def retrieve_by_keywords(
        self,
        turns: List[ConversationTurn],
        keywords: List[str],
        match_all: bool = False
    ) -> List[ConversationTurn]:
        if not keywords:
            return turns
        
        keyword_set = set(k.lower() for k in keywords)
        result = []
        
        for turn in turns:
            turn_keywords = self._extract_keywords(turn.content)
            
            if match_all:
                if keyword_set <= turn_keywords:
                    result.append(turn)
            else:
                if keyword_set & turn_keywords:
                    result.append(turn)
        
        return result
    
    def retrieve_by_role(
        self,
        turns: List[ConversationTurn],
        roles: List[TurnRole]
    ) -> List[ConversationTurn]:
        if not roles:
            return turns
        
        role_set = set(roles)
        return [t for t in turns if t.role in role_set]
    
    def retrieve_recent_n(
        self,
        turns: List[ConversationTurn],
        n: int,
        role_filter: Optional[TurnRole] = None
    ) -> List[ConversationTurn]:
        if role_filter:
            filtered = [t for t in turns if t.role == role_filter]
            return filtered[-n:]
        return turns[-n:]
    
    def search_content(
        self,
        turns: List[ConversationTurn],
        query: str,
        exact_match: bool = False
    ) -> List[ConversationTurn]:
        if not query:
            return turns
        
        query_lower = query.lower()
        result = []
        
        for turn in turns:
            content_lower = turn.content.lower()
            if exact_match:
                if query_lower in content_lower:
                    result.append(turn)
            else:
                query_keywords = self._extract_keywords(query)
                turn_keywords = self._extract_keywords(turn.content)
                if query_keywords & turn_keywords:
                    result.append(turn)
        
        return result
    
    def get_last_user_query(self, turns: List[ConversationTurn]) -> Optional[ConversationTurn]:
        for turn in reversed(turns):
            if turn.role == TurnRole.USER:
                return turn
        return None
    
    def get_last_assistant_reply(self, turns: List[ConversationTurn]) -> Optional[ConversationTurn]:
        for turn in reversed(turns):
            if turn.role == TurnRole.ASSISTANT:
                return turn
        return None
    
    def get_conversation_pairs(
        self,
        turns: List[ConversationTurn],
        limit: Optional[int] = None
    ) -> List[Dict]:
        pairs = []
        last_user = None
        
        for turn in turns:
            if turn.role == TurnRole.USER:
                last_user = turn
            elif turn.role == TurnRole.ASSISTANT and last_user:
                pairs.append({
                    'query': last_user,
                    'reply': turn,
                })
                last_user = None
        
        if limit:
            pairs = pairs[-limit:]
        
        return pairs
    
    def _extract_keywords(self, text: str) -> Set[str]:
        if text in self.keywords_cache:
            return self.keywords_cache[text]
        
        import re
        chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
        chinese_words = chinese_pattern.findall(text)
        
        english_pattern = re.compile(r'[a-zA-Z]+')
        english_words = english_pattern.findall(text)
        
        keywords = set()
        for word in chinese_words:
            if len(word) >= 2:
                keywords.add(word.lower())
        for word in english_words:
            if len(word) >= 3:
                keywords.add(word.lower())
        
        self.keywords_cache[text] = keywords
        return keywords
    
    def build_context_string(
        self,
        turns: List[ConversationTurn],
        format_template: Optional[str] = None
    ) -> str:
        if not turns:
            return ""
        
        if not format_template:
            format_template = "[{role}] {content}"
        
        lines = []
        for turn in turns:
            line = format_template.format(
                role=turn.role.value,
                content=turn.content,
                timestamp=turn.timestamp.strftime("%H:%M:%S")
            )
            lines.append(line)
        
        return "\n".join(lines)