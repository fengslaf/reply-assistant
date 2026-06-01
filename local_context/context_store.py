import json
import os
from typing import List, Optional, Dict
from datetime import datetime
from .data_types import ConversationTurn, TurnRole, SessionInfo


class ContextStore:
    
    def __init__(self, storage_path: Optional[str] = None):
        self.storage_path = storage_path
        self.sessions: Dict[str, SessionInfo] = {}
        self.turns: Dict[str, List[ConversationTurn]] = {}
        self.current_session_id: Optional[str] = None
        
        if storage_path and os.path.exists(storage_path):
            self._load_from_file()
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        if session_id is None:
            session_id = datetime.now().strftime("session_%Y%m%d_%H%M%S_%f")
        
        self.sessions[session_id] = SessionInfo(session_id=session_id)
        self.turns[session_id] = []
        self.current_session_id = session_id
        return session_id
    
    def add_turn(
        self,
        role: TurnRole,
        content: str,
        session_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> ConversationTurn:
        sid = session_id or self.current_session_id
        if not sid:
            sid = self.create_session()
        
        turn_id = f"{sid}_turn_{len(self.turns[sid]) + 1}"
        turn = ConversationTurn(
            turn_id=turn_id,
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        self.turns[sid].append(turn)
        self.sessions[sid].turn_count = len(self.turns[sid])
        
        self._save_to_file()
        return turn
    
    def get_turns(self, session_id: Optional[str] = None) -> List[ConversationTurn]:
        sid = session_id or self.current_session_id
        if not sid:
            return []
        return self.turns.get(sid, [])
    
    def get_all_sessions(self) -> List[SessionInfo]:
        return list(self.sessions.values())
    
    def end_session(self, session_id: Optional[str] = None):
        sid = session_id or self.current_session_id
        if sid and sid in self.sessions:
            self.sessions[sid].end_time = datetime.now()
            self._save_to_file()
    
    def clear_session(self, session_id: Optional[str] = None):
        sid = session_id or self.current_session_id
        if sid:
            self.turns[sid] = []
            if sid in self.sessions:
                self.sessions[sid].turn_count = 0
    
    def _save_to_file(self):
        if not self.storage_path:
            return
        
        data = {
            'sessions': {sid: s.to_dict() for sid, s in self.sessions.items()},
            'turns': {sid: [t.to_dict() for t in turns] for sid, turns in self.turns.items()},
            'current_session_id': self.current_session_id,
        }
        
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _load_from_file(self):
        if not self.storage_path or not os.path.exists(self.storage_path):
            return
        
        with open(self.storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.sessions = {
            sid: SessionInfo.from_dict(s) for sid, s in data.get('sessions', {}).items()
        }
        self.turns = {
            sid: [ConversationTurn.from_dict(t) for t in turns]
            for sid, turns in data.get('turns', {}).items()
        }
        self.current_session_id = data.get('current_session_id')