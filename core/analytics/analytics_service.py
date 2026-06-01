#!/usr/bin/env python3
"""高级统计服务（闭源 - 仅接口）

此模块包含商业付费功能的实现。
公开版仅保留接口定义，实现细节不公开。
"""

from typing import Dict, List, Optional

from .usage_tracker import UsageTracker
from .adoption_analyzer import AdoptionAnalyzer
from .efficiency_report import EfficiencyReporter
from .scene_analyzer import SceneAnalyzer


class AnalyticsService:
    """高级统计服务（接口定义）
    
    整合使用追踪、采纳率分析、效率报告、场景分析。
    
    注意：完整实现请使用私有版。
    """
    
    def __init__(self, sample_repo=None, data_path: str = None):
        self.tracker = UsageTracker(data_path=data_path)
        self.adoption_analyzer = AdoptionAnalyzer(self.tracker)
        self.efficiency_reporter = EfficiencyReporter(self.tracker)
        self.scene_analyzer = SceneAnalyzer(sample_repo, self.tracker) if sample_repo else None
    
    def track_search(self, user_id: str, query: str, 
                     results: List[Dict], latency_ms: int = None):
        """追踪检索"""
        pass
    
    def track_generation(self, user_id: str, query: str,
                         candidates: List[Dict], model_used: str = None,
                         latency_ms: int = None):
        """追踪生成"""
        pass
    
    def track_adoption(self, user_id: str, candidate_id: str,
                       candidate_content: str, query: str):
        """追踪采纳"""
        pass
    
    def get_adoption_rate(self, user_id: str = None,
                          period_days: int = 30) -> Dict:
        """获取采纳率"""
        return self.adoption_analyzer.calculate_adoption_rate(user_id, period_days)
    
    def get_efficiency_report(self, user_id: str = None,
                              period_days: int = 30) -> Dict:
        """获取效率报告"""
        return self.efficiency_reporter.generate_efficiency_report(user_id, period_days)
    
    def get_scene_analysis(self, user_id: str = None,
                           period_days: int = 30) -> Dict:
        """获取场景分析"""
        if self.scene_analyzer:
            return self.scene_analyzer.analyze_scene_effectiveness(user_id, period_days)
        return {}
