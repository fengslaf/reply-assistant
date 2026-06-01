from typing import List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from .data_types import ConversationTurn


class WindowStrategy(Enum):
    FIXED_SIZE = "fixed_size"
    TIME_BASED = "time_based"
    TOKEN_LIMIT = "token_limit"
    SMART_TRIM = "smart_trim"


class ContextWindow:
    
    def __init__(
        self,
        strategy: WindowStrategy = WindowStrategy.FIXED_SIZE,
        max_turns: int = 10,
        max_time_minutes: Optional[int] = None,
        max_tokens: Optional[int] = None,
        importance_filter: Optional[Callable] = None
    ):
        self.strategy = strategy
        self.max_turns = max_turns
        self.max_time_minutes = max_time_minutes
        self.max_tokens = max_tokens
        self.importance_filter = importance_filter
    
    def apply(self, turns: List[ConversationTurn]) -> List[ConversationTurn]:
        if not turns:
            return []
        
        if self.strategy == WindowStrategy.FIXED_SIZE:
            return self._fixed_size_window(turns)
        elif self.strategy == WindowStrategy.TIME_BASED:
            return self._time_based_window(turns)
        elif self.strategy == WindowStrategy.TOKEN_LIMIT:
            return self._token_limit_window(turns)
        elif self.strategy == WindowStrategy.SMART_TRIM:
            return self._smart_trim_window(turns)
        else:
            return turns[-self.max_turns:]
    
    def _fixed_size_window(self, turns: List[ConversationTurn]) -> List[ConversationTurn]:
        return turns[-self.max_turns:]
    
    def _time_based_window(self, turns: List[ConversationTurn]) -> List[ConversationTurn]:
        if not self.max_time_minutes:
            return turns
        
        cutoff_time = datetime.now() - timedelta(minutes=self.max_time_minutes)
        return [t for t in turns if t.timestamp >= cutoff_time]
    
    def _token_limit_window(self, turns: List[ConversationTurn]) -> List[ConversationTurn]:
        if not self.max_tokens:
            return turns
        
        selected = []
        total_tokens = 0
        
        for turn in reversed(turns):
            turn_tokens = self._estimate_tokens(turn.content)
            if total_tokens + turn_tokens <= self.max_tokens:
                selected.insert(0, turn)
                total_tokens += turn_tokens
            else:
                break
        
        return selected
    
    def _smart_trim_window(self, turns: List[ConversationTurn]) -> List[ConversationTurn]:
        if self.importance_filter:
            important_turns = [t for t in turns if self.importance_filter(t)]
            if len(important_turns) <= self.max_turns:
                return important_turns
        
        recent_turns = turns[-self.max_turns:]
        
        if self.importance_filter:
            important_ids = {t.turn_id for t in important_turns}
            for t in recent_turns:
                if t.turn_id not in important_ids:
                    important_turns.append(t)
            return important_turns[-self.max_turns:]
        
        return recent_turns
    
    def _estimate_tokens(self, text: str) -> int:
        chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
        other_chars = len(text) - chinese_chars
        return chinese_chars + other_chars // 4
    
    def get_window_summary(self, turns: List[ConversationTurn]) -> dict:
        if not turns:
            return {'count': 0, 'roles': {}, 'time_range': None}
        
        roles = {}
        for t in turns:
            role_key = t.role.value
            roles[role_key] = roles.get(role_key, 0) + 1
        
        time_range = {
            'start': turns[0].timestamp.isoformat(),
            'end': turns[-1].timestamp.isoformat(),
        }
        
        return {
            'count': len(turns),
            'roles': roles,
            'time_range': time_range,
            'estimated_tokens': sum(self._estimate_tokens(t.content) for t in turns),
        }