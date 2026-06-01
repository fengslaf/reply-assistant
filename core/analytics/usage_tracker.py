#!/usr/bin/env python3
"""使用追踪器（闭源 - 仅接口）

此模块包含商业付费功能的实现。
公开版仅保留接口定义，实现细节不公开。
"""

from typing import Dict, List, Optional


class UsageTracker:
    """使用追踪器（接口定义）
    
    记录用户每次使用系统行为的详细数据，
    用于后续分析用户使用习惯和效率。
    
    注意：完整实现请使用私有版。
    """
    
    def __init__(self, data_path: str = None):
        self.data_path = data_path
        self.logs = {
            'searches': [],
            'generations': [],
            'adoptions': [],
            'sessions': [],
            'summary': {
                'total_searches': 0,
                'total_generations': 0,
                'total_adoptions': 0,
                'total_saved_chars': 0,
                'total_saved_time': 0,
            }
        }
    
    def track_search(self, user_id: str, query: str, 
                     results: List[Dict], latency_ms: int = None):
        """追踪检索行为"""
        pass
    
    def track_generation(self, user_id: str, query: str,
                         candidates: List[Dict], model_used: str = None,
                         latency_ms: int = None):
        """追踪生成行为"""
        pass
    
    def track_adoption(self, user_id: str, candidate_id: str,
                       candidate_content: str, query: str):
        """追踪采纳行为"""
        pass
    
    def track_session(self, user_id: str, duration_minutes: int,
                      actions_count: int):
        """追踪使用会话"""
        pass
    
    def get_summary(self, user_id: str = None, 
                    period_days: int = 30) -> Dict:
        """获取使用摘要"""
        return self.logs['summary']
    
    def get_search_logs(self, user_id: str = None,
                        limit: int = 100) -> List[Dict]:
        """获取检索日志"""
        return []
    
    def get_generation_logs(self, user_id: str = None,
                            limit: int = 100) -> List[Dict]:
        """获取生成日志"""
        return []
    
    def get_adoption_logs(self, user_id: str = None,
                          limit: int = 100) -> List[Dict]:
        """获取采纳日志"""
        return []
    
    def clear_logs(self, user_id: str = None):
        """清除日志"""
        pass
