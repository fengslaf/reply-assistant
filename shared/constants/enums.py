#!/usr/bin/env python3
"""
快捷回复助手 - 枚举常量定义
对应文档: 09_枚举规范.md
"""

from enum import Enum
from typing import List, Dict


# ===== scene_tag（场景标签）=====
class SceneTag(Enum):
    """场景标签 - 8个"""
    ASK_PRICE = "问价格"            # 家长主动询问费用
    NEED_THINK = "回去考虑"         # 家长表示需要考虑
    TRIAL_HESITATE = "试听后犹豫"   # 试听后犹豫不决
    LOW_INTEREST = "孩子兴趣一般"   # 孩子反馈兴趣不高
    READ_NO_REPLY = "已读不回"      # 家长已读不回复
    WAKE_SILENCE = "沉默唤醒"       # 长时间沉默后唤醒
    BOOK_TRIAL = "约试听"           # 尝试预约试听
    BOOK_FOLLOW = "约复聊"         # 尝试约定后续沟通


SCENE_TAGS: List[str] = [e.value for e in SceneTag]


# ===== stage_tag（阶段标签）=====
class StageTag(Enum):
    """阶段标签 - 5个"""
    NEW_INQUIRY = "新咨询"          # 第一次接触
    PRICE_STAGE = "问价阶段"        # 进入价格讨论
    BEFORE_TRIAL = "试听前"         # 尚未试听
    AFTER_TRIAL = "试听后"          # 已完成试听
    WAKE_UP_STAGE = "沉默后再唤醒"  # 重新接触


STAGE_TAGS: List[str] = [e.value for e in StageTag]


# ===== status（样本状态）=====
class SampleStatus(Enum):
    """样本状态 - 4个"""
    DRAFT = "draft"        # 待审核
    REVIEWED = "reviewed"  # 已审核
    ACTIVE = "active"      # 已激活
    ARCHIVED = "archived"  # 已归档


SAMPLE_STATUSES: List[str] = [e.value for e in SampleStatus]


# ===== source_type（来源类型）=====
class SourceType(Enum):
    """来源类型 - 5个"""
    PC_INSTANT = "pc_instant_save"    # PC即时收藏
    PC_MANUAL = "pc_manual_patch"     # PC手动批量
    WECHAT_FORWARD = "wechat_forward" # 公众号转发
    BOT_COMMAND = "bot_command"       # 公众号指令
    ADMIN_MANUAL = "admin_manual"     # 后台手动


SOURCE_TYPES: List[str] = [e.value for e in SourceType]


# ===== quality_score（质量分数）=====
QUALITY_SCORES: List[int] = [1, 2, 3]

QUALITY_SCORE_DESC: Dict[int, str] = {
    1: "普通样本 - 基础可用",
    2: "较好样本 - 推荐优先复用",
    3: "优秀样本 - 高频复用典型范例"
}


# ===== msg_type（消息类型）=====
class MsgType(Enum):
    """消息类型"""
    TEXT = "text"      # 普通文本
    FORWARD = "forward" # 合并转发


# ===== role_guess（角色猜测）=====
class RoleGuess(Enum):
    """角色猜测"""
    PARENT = "parent"   # 家长/客户
    ADVISOR = "advisor" # 顾问/咨询师
    UNKNOWN = "unknown" # 未知


# ===== provider（模型提供商）=====
class LLMProvider(Enum):
    """大模型提供商"""
    DEEPSEEK = "deepseek"
    OPENAI = "openai"
    OTHER = "other"


# ===== 错误码 =====
class ErrorCode(Enum):
    """错误码定义"""
    SUCCESS = 0
    PARAM_MISSING = 1001
    PARAM_FORMAT_ERROR = 1002
    USER_NOT_FOUND = 2001
    SAMPLE_NOT_FOUND = 2002
    SEARCH_FAILED = 3001
    LLM_FAILED = 3002
    PERMISSION_DENIED = 4001
    INTERNAL_ERROR = 5001


ERROR_MESSAGES: Dict[int, str] = {
    0: "成功",
    1001: "参数缺失",
    1002: "参数格式错误",
    2001: "用户不存在",
    2002: "样本不存在",
    3001: "检索失败",
    3002: "模型调用失败",
    4001: "权限不足",
    5001: "服务器内部错误"
}


# ===== 枚举导出 =====
def get_all_enums() -> Dict[str, List]:
    """获取所有枚举定义 (对应 GET /api/v1/enums/all)"""
    return {
        "scene_tags": SCENE_TAGS,
        "stage_tags": STAGE_TAGS,
        "statuses": SAMPLE_STATUSES,
        "source_types": SOURCE_TYPES,
        "quality_scores": QUALITY_SCORES
    }