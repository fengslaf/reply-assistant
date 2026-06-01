from typing import List, Optional, Dict
from datetime import datetime
from .context_store import ContextStore
from .context_window import ContextWindow, WindowStrategy
from .context_retriever import ContextRetriever
from .data_types import ConversationTurn, TurnRole


class LocalContextManager:
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        window_strategy: WindowStrategy = WindowStrategy.FIXED_SIZE,
        max_turns: int = 10
    ):
        self.store = ContextStore(storage_path)
        self.window = ContextWindow(strategy=window_strategy, max_turns=max_turns)
        self.retriever = ContextRetriever()
    
    def start_session(self, session_id: Optional[str] = None) -> str:
        return self.store.create_session(session_id)
    
    def add_user_message(self, content: str, metadata: Optional[Dict] = None) -> ConversationTurn:
        return self.store.add_turn(TurnRole.USER, content, metadata=metadata)
    
    def add_assistant_reply(self, content: str, metadata: Optional[Dict] = None) -> ConversationTurn:
        return self.store.add_turn(TurnRole.ASSISTANT, content, metadata=metadata)
    
    def add_system_message(self, content: str) -> ConversationTurn:
        return self.store.add_turn(TurnRole.SYSTEM, content)
    
    def get_current_context(self, apply_window: bool = True) -> List[ConversationTurn]:
        turns = self.store.get_turns()
        if apply_window:
            turns = self.window.apply(turns)
        return turns
    
    def get_full_history(self) -> List[ConversationTurn]:
        return self.store.get_turns()
    
    def search_by_keywords(self, keywords: List[str]) -> List[ConversationTurn]:
        turns = self.store.get_turns()
        return self.retriever.retrieve_by_keywords(turns, keywords)
    
    def search_by_time(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[ConversationTurn]:
        turns = self.store.get_turns()
        return self.retriever.retrieve_by_time_range(turns, start_time, end_time)
    
    def get_last_user_query(self) -> Optional[ConversationTurn]:
        turns = self.store.get_turns()
        return self.retriever.get_last_user_query(turns)
    
    def get_last_assistant_reply(self) -> Optional[ConversationTurn]:
        turns = self.store.get_turns()
        return self.retriever.get_last_assistant_reply(turns)
    
    def get_conversation_pairs(self, limit: Optional[int] = None) -> List[Dict]:
        turns = self.store.get_turns()
        return self.retriever.get_conversation_pairs(turns, limit)
    
    def build_prompt_context(
        self,
        max_turns: Optional[int] = None,
        format_template: Optional[str] = None
    ) -> str:
        turns = self.get_current_context(apply_window=True)
        if max_turns:
            turns = turns[-max_turns:]
        return self.retriever.build_context_string(turns, format_template)
    
    def end_session(self):
        self.store.end_session()
    
    def clear_current_session(self):
        self.store.clear_session()
    
    def get_session_summary(self) -> Dict:
        turns = self.store.get_turns()
        windowed = self.window.apply(turns)
        return self.window.get_window_summary(windowed)
    
    def switch_strategy(
        self,
        strategy: WindowStrategy,
        max_turns: Optional[int] = None,
        max_time_minutes: Optional[int] = None
    ):
        self.window = ContextWindow(
            strategy=strategy,
            max_turns=max_turns or self.window.max_turns,
            max_time_minutes=max_time_minutes
        )