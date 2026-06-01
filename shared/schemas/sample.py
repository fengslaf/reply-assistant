#!/usr/bin/env python3
"""
快捷回复助手 - 样本数据结构定义
对应文档: 08_API接口契约.md 附录
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from shared.constants.enums import (
    SceneTag, StageTag, SampleStatus, SourceType,
    SCENE_TAGS, STAGE_TAGS, SAMPLE_STATUSES, SOURCE_TYPES
)


# ===== Sample（样本）=====
class Sample(BaseModel):
    """样本数据结构"""
    
    sample_id: str = Field(..., description="样本唯一标识")
    user_id: str = Field(..., description="顾问唯一标识")
    parent_message: str = Field(..., description="家长问题")
    advisor_reply: str = Field(..., description="顾问回复")
    
    scene_tag: Optional[str] = Field(None, description="场景标签")
    stage_tag: Optional[str] = Field(None, description="阶段标签")
    note: Optional[str] = Field(None, description="顾问备注")
    quality_score: int = Field(default=1, ge=1, le=3, description="质量分数 1-3")
    
    source_type: str = Field(..., description="来源类型")
    status: str = Field(default="draft", description="样本状态")
    
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    last_used_at: Optional[datetime] = Field(None, description="最近使用时间")
    
    def validate_tags(self):
        """验证标签是否合法"""
        if self.scene_tag and self.scene_tag not in SCENE_TAGS:
            raise ValueError(f"非法场景标签: {self.scene_tag}")
        if self.stage_tag and self.stage_tag not in STAGE_TAGS:
            raise ValueError(f"非法阶段标签: {self.stage_tag}")
        if self.status not in SAMPLE_STATUSES:
            raise ValueError(f"非法样本状态: {self.status}")
        if self.source_type not in SOURCE_TYPES:
            raise ValueError(f"非法来源类型: {self.source_type}")


class SampleCreate(BaseModel):
    """创建样本请求"""
    user_id: str
    parent_message: str
    advisor_reply: str
    scene_tag: Optional[str] = None
    stage_tag: Optional[str] = None
    note: Optional[str] = None
    quality_score: int = 1
    source_type: str
    auto_activate: bool = False


class SampleUpdate(BaseModel):
    """更新样本请求"""
    scene_tag: Optional[str] = None
    stage_tag: Optional[str] = None
    note: Optional[str] = None
    quality_score: Optional[int] = None


class SampleListResponse(BaseModel):
    """样本列表响应"""
    total: int
    page: int
    limit: int
    items: List[Sample]


# ===== ReplyCandidate（候选回复）=====
class ReplyCandidate(BaseModel):
    """候选回复数据结构"""
    
    reply_id: str = Field(..., description="唯一标识")
    content: str = Field(..., description="回复内容")
    style_tag: str = Field(..., description="风格标签")
    reference_samples: List[str] = Field(default_factory=list, description="引用的样本ID")
    confidence: float = Field(..., ge=0, le=1, description="置信度")


class GenerateReplyRequest(BaseModel):
    """生成候选回复请求"""
    query: str
    scene_hint: Optional[str] = None
    stage_hint: Optional[str] = None
    style_preference: Optional[str] = None


class GenerateReplyResponse(BaseModel):
    """生成候选回复响应"""
    query: str
    candidates: List[ReplyCandidate]
    model_used: str
    latency_ms: int


# ===== SearchResult（检索结果）=====
class SearchResult(BaseModel):
    """检索结果"""
    
    sample_id: str
    parent_message: str
    advisor_reply: str
    scene_tag: Optional[str]
    stage_tag: Optional[str]
    note: Optional[str]
    quality_score: int
    similarity: float  # 相似度分数 0-1


class SearchRequest(BaseModel):
    """检索请求"""
    query: str
    top_k: int = 5
    scene_filter: Optional[str] = None
    stage_filter: Optional[str] = None


class SearchResponse(BaseModel):
    """检索响应"""
    query: str
    total: int
    results: List[SearchResult]


# ===== ForwardCandidate（合并转发候选）=====
class ForwardCandidate(BaseModel):
    """合并转发解析候选"""
    
    temp_id: str
    sender: str
    time: str
    content: str
    role_guess: str  # parent | advisor | unknown


class ParseForwardResponse(BaseModel):
    """解析合并转发响应"""
    parsed_count: int
    candidates: List[ForwardCandidate]
    needs_confirmation: bool


class ConfirmRolesRequest(BaseModel):
    """确认角色映射请求"""
    openid: str
    temp_ids: List[str]
    role_mapping: dict  # {temp_id: "parent" | "advisor"}