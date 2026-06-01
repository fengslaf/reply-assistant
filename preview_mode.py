#!/usr/bin/env python3
"""预览模式 - 本地离线运行，不连接服务器

功能：
1. 本地数据匹配：精确匹配返回已保存的回复
2. 近似匹配：基于关键词/文本相似度返回相近回复
3. 支持导入对话数据到本地存储
4. 本地AI处理（预留，需配置API Key）

数据存储结构（local_data.json）：
{
    "samples": [
        {
            "parent_message": "价格有点高",
            "replies": ["回复1", "回复2", "回复3"],
            "scene_tag": "问价格",
            "keywords": ["价格", "贵", "高"]
        }
    ],
    "config": {
        "api_key": null,  // 本地AI预留
        "api_base": null
    }
}
"""

import json
import os
import re
import sys
import shutil
import threading
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from edition_limits import get_sample_limit
from reply_display import DEFAULT_REPLY_HIGHLIGHT_COLOR, DEFAULT_SOURCE_HIGHLIGHT_COLOR


def _load_preview_mode_adapter_class():
    """Import the V2 adapter only when the local mode actually needs it."""
    try:
        from preview_adapter import PreviewModeAdapter
    except ImportError:
        return None
    return PreviewModeAdapter


def get_app_base_dir():
    """获取应用基础目录（兼容打包和源码模式）
    
    打包模式: 返回exe所在目录
    源码模式: 返回项目根目录
    """
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def get_data_dir():
    """获取用户数据目录"""
    data_dir = get_app_base_dir() / 'data'
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_bundled_resource_path(relative_path):
    """获取打包资源路径（sys._MEIPASS）
    
    打包模式: 返回临时解压目录中的资源
    源码模式: 返回项目目录中的资源
    """
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path


def init_user_data():
    """首次运行时，从打包数据初始化用户数据"""
    user_path = get_data_dir() / 'local_data.json'
    bundled_path = get_bundled_resource_path('data/local_data.json')
    
    if not user_path.exists():
        if bundled_path.exists():
            shutil.copy(bundled_path, user_path)
            print(f"[初始化] 从模板创建用户数据: {user_path}")
        else:
            print("[警告] 未找到打包数据模板，将创建空数据")
    
    return user_path


class PreviewModeManager:
    """预览模式管理器"""
    
    def __init__(self, data_path: str = None):
        if data_path:
            self.data_path = Path(data_path)
        else:
            self.data_path = init_user_data()
        
        self.project_root = get_app_base_dir()
        self.data_dir = self.data_path.parent
        
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.data = self._load_or_init_data()
        
        self._keyword_index: Dict[str, List[int]] = {}
        self._build_keyword_index()
    
    def _load_or_init_data(self) -> Dict:
        """加载或初始化数据文件"""
        if self.data_path.exists():
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"加载本地数据失败: {e}")
                return self._get_default_data()
        else:
            return self._get_default_data()
    
    def _get_default_data(self) -> Dict:
        """获取默认数据结构，包含示例样本"""
        default_samples = [
            {
                "parent_message": "价格有点高，我们再考虑一下",
                "replies": [
                    "理解您的顾虑，价格确实是家长最关心的问题之一。我们这边先不催您定，如果您方便的话，我把孩子试听时的课堂表现整理发给您，您再判断会更稳一些。",
                    "这个价格其实包含了全套课程服务，包括一对一辅导、课后答疑、阶段测评。如果您担心效果，我们可以先安排一节深度试听课，让孩子完整体验我们的教学模式。",
                    "我建议咱们可以这样：您先带孩子体验一周的正课，感受一下我们的教学氛围和老师风格。如果觉得合适，我们再谈报名事宜，这样您心里也更有底。"
                ],
                "scene_tag": "问价格",
                "stage_tag": "试听后",
                "keywords": ["价格", "贵", "高", "考虑", "再想想"]
            },
            {
                "parent_message": "这门课程适合几岁的孩子？",
                "replies": [
                    "我们的课程适合3-12岁的孩子，根据不同年龄段设计了不同的教学内容和方法，确保每个孩子都能得到最适合的指导。",
                    "课程主要面向学龄前到小学阶段的孩子，大概3到12岁。我们会根据孩子的实际情况进行分班，确保教学效果。",
                    "这个课程覆盖了幼儿园到小学的年龄段，具体来说是3-12岁。您可以带孩子来做个免费的测评，看看适合哪个级别。"
                ],
                "scene_tag": "问课程",
                "stage_tag": "初次接触",
                "keywords": ["课程", "年龄", "孩子", "适合", "几岁"]
            },
            {
                "parent_message": "老师水平怎么样？",
                "replies": [
                    "我们的老师都是经过严格筛选和培训的，都有相关专业背景和丰富教学经验。您可以先安排试听课，亲自感受一下老师的教学风格。",
                    "师资是我们最重视的部分。所有老师都持有教师资格证，平均有5年以上教学经验。我们也欢迎家长随时观摩课堂。",
                    "老师团队是我们机构的核心竞争力。每位老师都经过至少3轮面试和岗前培训，定期接受教学考核。您可以带孩子试听，感受一下。"
                ],
                "scene_tag": "问师资",
                "stage_tag": "初次接触",
                "keywords": ["老师", "师资", "水平", "教学", "经验"]
            },
            {
                "parent_message": "什么时候可以上课？",
                "replies": [
                    "我们目前有多个时间段可选，包括周末和平时晚上。您可以根据孩子的作息时间选择最合适的时段。",
                    "课程时间很灵活，我们有周末班、平日班等多种安排。您可以先告诉我您方便的时间，我来帮您匹配。",
                    "上课时间我们尽量配合家长的需求。现在有空位的时间段包括周六上午、周日下午、周三晚上等，您看哪个方便？"
                ],
                "scene_tag": "问时间",
                "stage_tag": "报名前",
                "keywords": ["时间", "上课", "什么时候", "排课", "时间表"]
            },
            {
                "parent_message": "孩子兴趣一般，不想学",
                "replies": [
                    "孩子的兴趣是可以培养的。很多时候孩子一开始不感兴趣，是因为没有接触到有趣的教学方式。建议您带孩子来试听一下，感受我们互动式的课堂氛围。",
                    "理解您的担心。其实很多孩子一开始都会有这样的想法。我们擅长用游戏化教学激发孩子的兴趣，您可以先让孩子体验一节课看看效果。",
                    "兴趣是可以慢慢培养的。我们会在课堂上设计很多有趣的环节，让孩子在不知不觉中喜欢上学习。建议您先安排一次试听，看看孩子的反应。"
                ],
                "scene_tag": "孩子兴趣一般",
                "stage_tag": "试听前",
                "keywords": ["兴趣", "不想学", "不喜欢", "没兴趣", "不愿意"]
            },
            {
                "parent_message": "我们已经在其他机构报名了",
                "replies": [
                    "好的，理解您的选择。如果后续您对现在机构的课程有任何不满意的地方，随时欢迎回来了解我们的情况。",
                    "没关系，每个机构都有自己的特色。如果您想了解我们的课程和现在的有什么不同，可以随时联系我，我可以帮您做个对比。",
                    "感谢您的信任。如果将来有转课或者增补课程的需求，我们也提供灵活的方案。祝孩子在现在的机构学习顺利！"
                ],
                "scene_tag": "已报名其他",
                "stage_tag": "试听后",
                "keywords": ["报名", "其他机构", "已经", "别的"]
            },
            {
                "parent_message": "能不能便宜一点？",
                "replies": [
                    "理解您的心情。我们的价格是根据课程质量和服务水平来定的，确实性价比很高。不过如果您一次性报名多门课程，我们是有套餐优惠的。",
                    "价格方面我们确实有优惠政策。比如年报会有折扣，多课程组合也有优惠。您可以告诉我您的需求，我帮您算一个最划算的方案。",
                    "我们现在是活动期，报名有优惠。具体优惠力度要看您选择的课程包。我可以帮您详细介绍一下，您看您方便什么时候？"
                ],
                "scene_tag": "问价格",
                "stage_tag": "报名前",
                "keywords": ["便宜", "优惠", "折扣", "价格", "降价"]
            },
            {
                "parent_message": "孩子试听后感觉一般",
                "replies": [
                    "感谢您带孩子来试听。孩子感觉一般可能是因为还没有完全适应我们的教学节奏。建议您可以考虑多试听几次，或者我们可以换一位教学风格更活泼的老师。",
                    "理解您的反馈。每个孩子的适应周期不同，试听一次可能还不够。我们可以安排跟进试听，或者您可以告诉我孩子具体哪里感觉一般，我来调整。",
                    "孩子的感受很重要。试听效果一般可能是多方面原因。我们可以深入沟通一下孩子的学习习惯和偏好，看看能否调整教学方式。"
                ],
                "scene_tag": "试听后犹豫",
                "stage_tag": "试听后",
                "keywords": ["试听", "一般", "感觉", "效果", "犹豫"]
            }
        ]
        
        return {
            "samples": default_samples,
            "config": {
                "api_key": None,
                "api_base": None,
                "source_highlight_color": DEFAULT_SOURCE_HIGHLIGHT_COLOR,
                "reply_highlight_color": DEFAULT_REPLY_HIGHLIGHT_COLOR,
                "v204_generation_enabled": False,
                "preview_mode": True,
                "last_updated": datetime.now().isoformat()
            }
        }
    
    def _build_keyword_index(self):
        """构建关键词索引"""
        self._keyword_index.clear()
        
        for idx, sample in enumerate(self.data.get('samples', [])):
            keywords = sample.get('keywords', [])
            for keyword in keywords:
                if keyword not in self._keyword_index:
                    self._keyword_index[keyword] = []
                self._keyword_index[keyword].append(idx)
    
    def save_data(self):
        """保存数据到文件"""
        self.data['config']['last_updated'] = datetime.now().isoformat()
        
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        
        # 重建索引
        self._build_keyword_index()
    
    def get_data_signature(self) -> str:
        """Return a lightweight signature used to detect data changes."""
        config = self.data.get('config', {})
        last_updated = config.get('last_updated', '')
        return f"{self.data_path}|{last_updated}"

    def has_api_key(self) -> bool:
        """检查是否有本地API Key配置"""
        config = self.data.get('config', {})
        return bool(config.get('api_key'))
    
    def set_api_key(self, api_key: str, api_base: str = None):
        """设置API Key（预留）"""
        self.data['config']['api_key'] = api_key
        if api_base:
            self.data['config']['api_base'] = api_base
        self.save_data()
    
    def clear_api_key(self):
        """清除API Key"""
        self.data['config']['api_key'] = None
        self.data['config']['api_base'] = None
        self.save_data()

    def get_source_highlight_color(self) -> str:
        """获取来源命中词高亮颜色"""
        config = self.data.get('config', {})
        return config.get('source_highlight_color') or DEFAULT_SOURCE_HIGHLIGHT_COLOR

    def set_source_highlight_color(self, color: str):
        """设置来源命中词高亮颜色"""
        self.data['config']['source_highlight_color'] = color or DEFAULT_SOURCE_HIGHLIGHT_COLOR
        self.save_data()

    def get_reply_highlight_color(self) -> str:
        """获取回复正文高亮颜色"""
        config = self.data.get('config', {})
        return config.get('reply_highlight_color') or DEFAULT_REPLY_HIGHLIGHT_COLOR

    def set_reply_highlight_color(self, color: str):
        """设置回复正文高亮颜色"""
        self.data['config']['reply_highlight_color'] = color or DEFAULT_REPLY_HIGHLIGHT_COLOR
        self.save_data()

    def get_v204_generation_enabled(self) -> bool:
        config = self.data.get('config', {})
        return bool(config.get('v204_generation_enabled', False))

    def set_v204_generation_enabled(self, enabled: bool):
        self.data['config']['v204_generation_enabled'] = bool(enabled)
        self.save_data()

    def get_hotkey(self) -> str:
        config = self.data.get('config', {})
        return (config.get('hotkey') or 'ctrl+shift+y').strip() or 'ctrl+shift+y'

    def set_hotkey(self, hotkey: str):
        self.data['config']['hotkey'] = (hotkey or 'ctrl+shift+y').strip() or 'ctrl+shift+y'
        self.save_data()
    
    def match_exact(self, query: str) -> Optional[Dict]:
        """精确匹配和包含匹配
        
        Args:
            query: 用户输入的问题
            
        Returns:
            如果找到匹配，返回样本数据；否则返回None
        """
        query_normalized = self._normalize_text(query)
        
        matched_samples = []
        
        for sample in self.data.get('samples', []):
            parent_normalized = self._normalize_text(sample['parent_message'])
            
            if query_normalized == parent_normalized:
                return sample
            
            if query_normalized and parent_normalized:
                if query_normalized in parent_normalized or parent_normalized in query_normalized:
                    matched_samples.append(sample)
        
        if matched_samples:
            return matched_samples[0]
        
        return None
    
    def match_contains(self, query: str, top_k: int = 5) -> List[Dict]:
        """包含匹配 - 查询包含样本或样本包含查询
        
        Args:
            query: 用户输入的问题
            top_k: 返回数量
            
        Returns:
            匹配的样本列表
        """
        query_normalized = self._normalize_text(query)
        
        if not query_normalized:
            return []
        
        matched = []
        
        for idx, sample in enumerate(self.data.get('samples', [])):
            parent_normalized = self._normalize_text(sample['parent_message'])
            
            if not parent_normalized:
                continue
            
            if query_normalized == parent_normalized:
                sample_copy = sample.copy()
                sample_copy['match_score'] = 1.0
                sample_copy['match_type'] = 'exact'
                matched.append((idx, sample_copy))
                continue
            
            if query_normalized in parent_normalized:
                score = len(query_normalized) / len(parent_normalized)
                sample_copy = sample.copy()
                sample_copy['match_score'] = score
                sample_copy['match_type'] = 'contains'
                matched.append((idx, sample_copy))
                continue
            
            if parent_normalized in query_normalized:
                score = len(parent_normalized) / len(query_normalized)
                sample_copy = sample.copy()
                sample_copy['match_score'] = score
                sample_copy['match_type'] = 'contained'
                matched.append((idx, sample_copy))
        
        matched.sort(key=lambda x: x[1]['match_score'], reverse=True)
        
        return [m[1] for m in matched[:top_k]]
    
    def match_similar(self, query: str, top_k: int = 5) -> List[Dict]:
        """相似匹配 - 基于关键词和包含关系
        
        Args:
            query: 用户输入的问题
            top_k: 返回前k个最相似的样本
            
        Returns:
            相似样本列表，按匹配度排序
        """
        query_keywords = self._extract_keywords(query)
        
        contains_matches = self.match_contains(query, top_k=top_k * 2)
        
        keyword_matches = []
        
        if query_keywords:
            for idx, sample in enumerate(self.data.get('samples', [])):
                sample_keywords = set(sample.get('keywords', []))
                
                intersection = len(query_keywords & sample_keywords)
                
                if intersection > 0:
                    union = len(query_keywords | sample_keywords)
                    score = intersection / union
                    
                    if sample.get('scene_tag') and self._guess_scene(query) == sample['scene_tag']:
                        score += 0.2
                    
                    sample_copy = sample.copy()
                    sample_copy['match_score'] = score
                    sample_copy['match_type'] = 'keyword'
                    keyword_matches.append((idx, sample_copy))
        
        keyword_matches.sort(key=lambda x: x[1]['match_score'], reverse=True)
        keyword_matches = keyword_matches[:top_k * 2]
        
        all_matches = []
        seen_indices = set()
        
        for m in contains_matches:
            idx = self.data['samples'].index(m) if m in self.data['samples'] else -1
            if idx >= 0 and idx not in seen_indices:
                seen_indices.add(idx)
                all_matches.append((idx, m))
        
        for idx, m in keyword_matches:
            if idx not in seen_indices:
                seen_indices.add(idx)
                all_matches.append((idx, m))
        
        # 兜底：按场景标签匹配（关键词无交集但场景相同的样本）
        guessed_scene = self._guess_scene(query) if query_keywords else None
        if guessed_scene:
            for idx, sample in enumerate(self.data.get('samples', [])):
                if idx not in seen_indices and sample.get('scene_tag') == guessed_scene:
                    sample_copy = sample.copy()
                    sample_copy['match_score'] = 0.1
                    sample_copy['match_type'] = 'scene'
                    seen_indices.add(idx)
                    all_matches.append((idx, sample_copy))
        
        all_matches.sort(key=lambda x: x[1]['match_score'], reverse=True)
        
        return [m[1] for m in all_matches[:top_k]]
    
    def match(self, query: str, top_k: int = 5) -> Dict:
        """智能匹配 - 合并所有相关匹配结果
        
        Args:
            query: 用户输入的问题
            
        Returns:
            匹配结果字典，最多返回5条候选
        """
        query_normalized = self._normalize_text(query)
        has_key = self.has_api_key()
        
        all_matches = []
        seen_parents = set()
        
        for sample in self.data.get('samples', []):
            parent_message = sample.get('parent_message', '')
            parent_normalized = self._normalize_text(parent_message)
            
            if not parent_normalized:
                continue
            
            match_type = None
            confidence = 0
            
            if query_normalized == parent_normalized:
                match_type = 'exact'
                confidence = 0.95
            elif query_normalized and parent_normalized:
                if query_normalized in parent_normalized:
                    match_type = 'contains_query'
                    confidence = 0.85
                elif parent_normalized in query_normalized:
                    match_type = 'contains_parent'
                    confidence = 0.80
                else:
                    overlap = self._calc_text_overlap(query_normalized, parent_normalized)
                    if overlap > 0.3:
                        match_type = 'partial'
                        confidence = 0.70 + (overlap * 0.15)
            
            if match_type:
                if parent_message not in seen_parents:
                    seen_parents.add(parent_message)
                    for reply in sample.get('replies', []):
                        all_matches.append({
                            "reply_id": f"local_{match_type}_{len(all_matches)}",
                            "content": reply,
                            "style_tag": self._guess_style(len(all_matches), has_key),
                            "confidence": confidence,
                            "source": self._get_match_source(match_type, parent_message, sample.get('scene_tag', '')),
                            "match_type": match_type
                        })
        
        if all_matches:
            all_matches.sort(key=lambda x: x['confidence'], reverse=True)
            
            result_type = 'exact' if any(m['match_type'] == 'exact' for m in all_matches) else 'contains'
            
            return {
                "match_type": result_type,
                "candidates": all_matches[:top_k],
                "matched_samples": all_matches,
                "source": "local_data"
            }
        
        similar_matches = self.match_similar(query, top_k=top_k)
        
        if similar_matches:
            candidates = []
            
            for i, match in enumerate(similar_matches[:top_k]):
                parent_message = match.get('parent_message', '')
                if parent_message in seen_parents:
                    continue
                seen_parents.add(parent_message)
                
                replies = match.get('replies', [])
                scene_tag = match.get('scene_tag', '未知场景')
                parent_preview = parent_message[:15] if parent_message else ''
                if len(parent_message) > 15:
                    parent_preview += '...'
                source_text = f'"{parent_preview}" —— 相似匹配 ({scene_tag})'
                for reply in replies:
                    candidates.append({
                        "reply_id": f"local_similar_{scene_tag}_{i}",
                        "content": reply,
                        "style_tag": self._guess_style(0, has_key),
                        "confidence": match.get('match_score', 0.5),
                        "source": source_text
                    })
            
            if candidates:
                return {
                    "match_type": "similar",
                    "candidates": candidates[:top_k],
                    "matched_samples": similar_matches,
                    "source": "local_data"
                }
        
        return {
            "match_type": "none",
            "candidates": [],
            "message": "本地数据中暂无相似样本",
            "source": "local_data"
        }
    
    def _get_match_source(self, match_type: str, parent_message: str, scene_tag: str = '') -> str:
        """获取匹配来源描述，包含匹配到的家长问题"""
        parent_preview = parent_message[:15] if parent_message else ''
        if len(parent_message or '') > 15:
            parent_preview += '...'
        
        if match_type == 'exact':
            return f'"{parent_preview}" —— 精确匹配'
        elif match_type == 'contains_query':
            return f'"{parent_preview}" —— 包含匹配'
        elif match_type == 'contains_parent':
            return f'"{parent_preview}" —— 被包含匹配'
        elif match_type == 'partial':
            return f'"{parent_preview}" —— 模糊匹配'
        return f'"{parent_preview}" —— 匹配'
    
    def add_sample(self, parent_message: str, replies: List[str], 
                   scene_tag: str = None, stage_tag: str = None) -> str:
        """添加新样本
        
        Args:
            parent_message: 家长问题
            replies: 回复列表（最多5条）
            scene_tag: 场景标签
            stage_tag: 阶段标签
            
        Returns:
            样本ID
        """
        # 自动提取关键词
        keywords = self._extract_keywords(parent_message)
        
        # 限制回复数量
        replies = replies[:5]
        
        sample_limit = get_sample_limit()
        current_count = len(self.data.get('samples', []))
        if sample_limit is not None and current_count >= sample_limit:
            raise ValueError(f"公开版最多保存 {sample_limit} 条样本")

        sample = {
            "parent_message": parent_message,
            "replies": replies,
            "scene_tag": scene_tag or self._guess_scene(parent_message),
            "stage_tag": stage_tag,
            "keywords": list(keywords),
            "created_at": datetime.now().isoformat()
        }
        
        self.data['samples'].append(sample)
        self.save_data()
        
        return f"sample_{len(self.data['samples']) - 1}"
    
    def import_conversations(self, conversations: List[Dict]) -> int:
        """批量导入对话数据
        
        Args:
            conversations: 对话列表，格式为 [{"parent_message": "...", "advisor_reply": "...", ...}]
            
        Returns:
            成功导入的数量
        """
        imported_count = 0
        sample_limit = get_sample_limit()
        
        for conv in conversations:
            if sample_limit is not None and len(self.data.get('samples', [])) >= sample_limit:
                break

            parent_msg = conv.get('parent_message', '')
            advisor_reply = conv.get('advisor_reply', '')
            
            if parent_msg and advisor_reply:
                # 检查是否已存在相似样本
                similar = self.match_similar(parent_msg, top_k=1)
                
                # 如果匹配度不高，添加新样本
                if not similar or similar[0].get('match_score', 0) < 0.7:
                    self.add_sample(
                        parent_message=parent_msg,
                        replies=[advisor_reply],
                        scene_tag=conv.get('scene_tag'),
                        stage_tag=conv.get('stage_tag')
                    )
                    imported_count += 1
        
        return imported_count
    
    def get_all_samples(self) -> List[Dict]:
        """获取所有样本"""
        return self.data.get('samples', [])
    
    def get_sample_count(self) -> int:
        """获取样本数量"""
        return len(self.data.get('samples', []))
    
    def clear_all_samples(self):
        """清空所有样本（保留默认数据结构）"""
        self.data['samples'] = []
        self.save_data()
    
    def reset_to_default(self):
        """重置为默认样本"""
        self.data = self._get_default_data()
        self.save_data()
    
    # ===== 文本处理辅助方法 =====
    
    def _calc_text_overlap(self, text1: str, text2: str) -> float:
        """计算两个文本的字符重叠比例"""
        if not text1 or not text2:
            return 0
        
        set1 = set(text1)
        set2 = set(text2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        if union == 0:
            return 0
        
        base_overlap = intersection / union
        
        for i in range(min(len(text1), len(text2)) - 2):
            for j in range(i + 3, min(len(text1), len(text2)) + 1):
                sub = text1[i:j]
                if sub in text2:
                    base_overlap += 0.1
        
        return min(base_overlap, 1.0)
    
    def _normalize_text(self, text: str) -> str:
        """标准化文本（去除空格、标点，小写）"""
        if not text:
            return ""
        
        # 去除标点和空格
        text = re.sub(r'[^\w]', '', text)
        # 转小写
        text = text.lower()
        
        return text
    
    def _extract_keywords(self, text: str) -> set:
        """提取关键词"""
        # 常见关键词词库（可扩展）
        keyword_patterns = [
            '价格', '贵', '便宜', '优惠', '折扣',
            '课程', '上课', '学习', '教学',
            '老师', '师资', '水平',
            '孩子', '年龄', '几岁',
            '时间', '什么时候', '安排',
            '试听', '体验', '效果',
            '兴趣', '喜欢', '愿意',
            '报名', '机构', '已经',
            '考虑', '犹豫', '想想',
            '退款', '退课', '换课'
        ]
        
        keywords = set()
        
        for kw in keyword_patterns:
            if kw in text:
                keywords.add(kw)
        
        return keywords
    
    def _guess_scene(self, text: str) -> str:
        """猜测场景标签"""
        scene_keywords = {
            '问价格': ['价格', '贵', '便宜', '优惠', '多少钱'],
            '问课程': ['课程', '学什么', '内容', '教什么'],
            '问师资': ['老师', '师资', '水平', '经验'],
            '问时间': ['时间', '什么时候', '上课时间', '排课'],
            '孩子兴趣一般': ['兴趣', '不想学', '不喜欢', '没兴趣'],
            '试听后犹豫': ['试听', '体验', '效果一般', '犹豫'],
            '已报名其他': ['已经报名', '其他机构', '别的'],
            '问进度': ['进度', '学了多久', '效果怎么样']
        }
        
        for scene, kws in scene_keywords.items():
            for kw in kws:
                if kw in text:
                    return scene
        
        return '其他'
    
    def _guess_style(self, index: int, has_key: bool = False) -> str:
        """猜测风格标签（仅在有API key时启用）"""
        if not has_key:
            return ""
        styles = ['温和共情型', '专业自信型', '行动推动型']
        return styles[index % len(styles)]
    
    def delete_sample(self, index: int) -> bool:
        """删除样本
        
        Args:
            index: 样本索引
            
        Returns:
            是否成功删除
        """
        samples = self.data.get('samples', [])
        
        if 0 <= index < len(samples):
            samples.pop(index)
            self.save_data()
            return True
        
        return False
    
    def update_sample(self, index: int, parent_message: str = None, 
                      replies: List[str] = None, scene_tag: str = None,
                      stage_tag: str = None) -> bool:
        """更新样本
        
        Args:
            index: 样本索引
            parent_message: 新的家长问题（可选）
            replies: 新的回复列表（可选）
            scene_tag: 新的场景标签（可选）
            stage_tag: 新的阶段标签（可选）
            
        Returns:
            是否成功更新
        """
        samples = self.data.get('samples', [])
        
        if 0 <= index < len(samples):
            sample = samples[index]
            
            if parent_message is not None:
                sample['parent_message'] = parent_message
                sample['keywords'] = list(self._extract_keywords(parent_message))
            
            if replies is not None:
                sample['replies'] = replies[:5]
            
            if scene_tag is not None:
                sample['scene_tag'] = scene_tag
            
            if stage_tag is not None:
                sample['stage_tag'] = stage_tag
            
            sample['updated_at'] = datetime.now().isoformat()
            
            self.save_data()
            return True
        
        return False
    
    def match_with_scene(self, query: str, scene_filter: str = None, top_k: int = 5) -> Dict:
        """带场景过滤的匹配
        
        Args:
            query: 用户输入的问题
            scene_filter: 场景过滤（可选，None表示全仓库匹配）
            top_k: 返回数量
            
        Returns:
            匹配结果
        """
        exact_match = self.match_exact(query)
        
        if exact_match:
            if scene_filter and exact_match.get('scene_tag') != scene_filter:
                pass
            else:
                return {
                    "match_type": "exact",
                    "candidates": [
                        {
                            "reply_id": f"local_exact_{i}",
                            "content": reply,
                            "style_tag": self._guess_style(i),
                            "confidence": 0.95,
                            "source": "精确匹配"
                        }
                        for i, reply in enumerate(exact_match.get('replies', []))
                    ],
                    "matched_sample": exact_match,
                    "source": "local_data"
                }
        
        similar_matches = self.match_similar(query, top_k=top_k * 2)
        
        if scene_filter:
            similar_matches = [m for m in similar_matches if m.get('scene_tag') == scene_filter]
        
        similar_matches = similar_matches[:top_k]
        
        if similar_matches:
            candidates = []
            seen_contents = set()
            
            for i, match in enumerate(similar_matches):
                replies = match.get('replies', [])
                if replies:
                    content = replies[0]
                    content_normalized = self._normalize_text(content)
                    
                    if content_normalized not in seen_contents:
                        seen_contents.add(content_normalized)
                        candidates.append({
                            "reply_id": f"local_similar_{match.get('scene_tag', 'unknown')}_{i}",
                            "content": content,
                            "style_tag": self._guess_style(0),
                            "confidence": match.get('match_score', 0.5),
                            "source": f"相似匹配 ({match.get('scene_tag', '未知场景')})"
                        })
            
            if candidates:
                return {
                    "match_type": "similar",
                    "candidates": candidates,
                    "matched_samples": similar_matches,
                    "source": "local_data",
                    "scene_filter": scene_filter
                }
        
        return {
            "match_type": "none",
            "candidates": [],
            "message": "本地数据中暂无相似样本，建议导入更多对话数据",
            "source": "local_data"
        }
    
    def get_enums(self) -> Dict:
        """获取枚举定义"""
        return {
            "scene_tags": [
                "", "问价格", "问课程", "问师资", "问时间", 
                "孩子兴趣一般", "试听后犹豫", "已报名其他", "问进度", "其他"
            ],
            "stage_tags": ["", "初次接触", "试听前", "试听后", "报名前", "上课中", "课后跟进"],
            "sample_statuses": ["draft", "active", "archived"],
            "source_types": ["manual_import", "wechat_forward", "preview_mode"],
            "quality_scores": [1, 2, 3]
        }


# ===== 预览模式API客户端 =====

class PreviewAPIClient:
    """预览模式API客户端 - 本地数据匹配"""
    
    def __init__(self, preview_manager: PreviewModeManager = None, user_id: str = "preview_user"):
        self.preview_manager = preview_manager or PreviewModeManager()
        self.user_id = user_id
        self.is_preview = True
        self.v2_adapter = None
        self._v2_adapter_lock = threading.Lock()
        self._v2_adapter_building = False
        self._v2_adapter_signature = None
        self._start_v2_adapter_warmup()

    def _create_v2_adapter(self):
        adapter_cls = _load_preview_mode_adapter_class()
        if adapter_cls is None:
            return None
        try:
            return adapter_cls(self.preview_manager)
        except Exception:
            return None

    def _start_v2_adapter_warmup(self):
        if self.v2_adapter or self._v2_adapter_building:
            return

        self._v2_adapter_building = True

        def _worker():
            try:
                adapter = self._create_v2_adapter()
                if adapter is not None:
                    with self._v2_adapter_lock:
                        self.v2_adapter = adapter
                        self._v2_adapter_signature = self.preview_manager.get_data_signature()
            finally:
                self._v2_adapter_building = False

        threading.Thread(target=_worker, daemon=True).start()

    def _ensure_v2_adapter(self):
        if self.v2_adapter:
            return
        if self._v2_adapter_building:
            return
        self._start_v2_adapter_warmup()

    def _sync_v2_adapter(self):
        """Keep the V2 adapter aligned with the latest preview data."""
        if not self.v2_adapter:
            return

        current_signature = self.preview_manager.get_data_signature()
        if self._v2_adapter_signature == current_signature:
            return

        try:
            self.v2_adapter.preview_manager = self.preview_manager
            self.v2_adapter.refresh()
            self._v2_adapter_signature = current_signature
        except Exception:
            self.v2_adapter = None

    def _use_v204_generation(self) -> bool:
        """检查是否启用V204智能生成"""
        try:
            return getattr(self.preview_manager, "get_v204_generation_enabled", lambda: False)()
        except Exception:
            return False

    def _check_ai_quota(self):
        """检查AI生成配额"""
        from gui_utils import is_public_edition
        if is_public_edition():
            return False, "公开版不支持AI生成"
        
        # 从 preview_manager 的 state 中读取 AI 使用情况
        try:
            state = self.preview_manager.data.get('state', {})
            access_mode = state.get('reply_access_mode', 'free')
            
            # 只有 Plus 用户有 AI 配额
            if access_mode not in ('plus_monthly', 'plus_yearly'):
                return False, "需要开通Plus会员才能使用AI生成"
            
            # 检查本月使用次数（简化版，实际应从服务器获取）
            ai_usage = state.get('ai_usage_count', 0)
            ai_limit = 500  # Plus 每月500次
            
            if ai_usage >= ai_limit:
                return False, f"本月AI生成次数已用完（{ai_usage}/{ai_limit}）"
            
            return True, "ok"
        except Exception:
            return False, "检查配额失败"

    def _find_sample_for_candidate(self, candidate: Dict):
        content = candidate.get("content", "")
        if not content:
            return -1, None

        for idx, sample in enumerate(self.preview_manager.get_all_samples()):
            if content in sample.get("replies", []):
                return idx, sample
        return -1, None

    def _guess_fallback_source_type(self, match_type: str, candidate: Dict) -> str:
        source_text = str(candidate.get("source", ""))
        if match_type == "exact":
            return "local_exact"
        if "精确匹配" in source_text or "精准匹配" in source_text:
            return "local_exact"
        if "包含匹配" in source_text or "模糊匹配" in source_text:
            return "local_exact"
        if match_type == "similar":
            return "local_keyword"
        return "local_none"

    def _enrich_fallback_candidates(self, candidates: List[Dict], match_type: str) -> List[Dict]:
        enriched = []
        for index, candidate in enumerate(candidates):
            payload = dict(candidate)
            sample_index, sample = self._find_sample_for_candidate(payload)
            payload.setdefault("reply_id", f"local_fallback_{match_type}_{index}")
            payload.setdefault("style_tag", "模板回复")
            payload.setdefault("confidence", 0.0 if match_type == "none" else payload.get("confidence", 0.0))
            payload.setdefault("source_type", self._guess_fallback_source_type(match_type, payload))
            if sample_index >= 0:
                payload.setdefault("matched_sample_id", str(sample_index))
                payload.setdefault("matched_parent", sample.get("parent_message", ""))
            enriched.append(payload)
        return enriched
    
    def get_enums(self) -> Dict:
        """获取枚举"""
        return self.preview_manager.get_enums()
    
    def generate_reply(self, query: str, scene_hint: str = None, 
                       stage_hint: str = None, top_k: int = 5,
                       use_ai_generation: bool = False) -> Dict:
        """生成候选回复 - 本地匹配"""
        self._ensure_v2_adapter()
        self._sync_v2_adapter()
        
        # 如果勾选了AI生成且有权限，使用V204引擎
        if use_ai_generation and self._use_v204_generation():
            # 检查AI生成配额
            quota_ok, quota_msg = self._check_ai_quota()
            if not quota_ok:
                # 配额不足，降级到本地检索
                pass
            else:
                # 使用AI生成
                try:
                    return self.v2_adapter.match_v2(
                        query=query,
                        top_k=top_k,
                        scene_hint=scene_hint,
                        stage_hint=stage_hint,
                        inference_mode='user_api_key' if self.preview_manager.has_api_key() else 'retrieval_only',
                    )
                except Exception:
                    self.v2_adapter = None
        
        if self.v2_adapter:
            try:
                v2_result = self.v2_adapter.match_v2(
                    query=query,
                    top_k=top_k,
                    scene_hint=scene_hint,
                    stage_hint=stage_hint,
                    inference_mode='user_api_key' if self.preview_manager.has_api_key() else 'retrieval_only',
                )
                # V2 returned results — use them
                if v2_result and v2_result.get('candidates'):
                    return v2_result
                # V2 returned empty — fall through to V1 match()
            except Exception:
                self.v2_adapter = None
        
        match_result = self.preview_manager.match(query, top_k=top_k)
        
        candidates = match_result.get('candidates', [])
        
        scene_filter = scene_hint if scene_hint else None
        if scene_filter and candidates:
            filtered = []
            for c in candidates:
                parent_idx = -1
                for idx, s in enumerate(self.preview_manager.get_all_samples()):
                    if c.get('content') in s.get('replies', []):
                        parent_idx = idx
                        break
                if parent_idx >= 0:
                    sample = self.preview_manager.get_all_samples()[parent_idx]
                    if sample.get('scene_tag') == scene_filter:
                        filtered.append(c)
            if filtered:
                candidates = filtered
        
        if not candidates:
            candidates = [
                {
                    "reply_id": "no_match_001",
                    "content": f"本地数据中暂无相似样本",
                    "style_tag": "提示",
                    "confidence": 0.0,
                    "source": "无匹配",
                    "source_type": "local_none",
                }
            ]
        else:
            candidates = self._enrich_fallback_candidates(candidates, match_result.get('match_type', 'none'))
        
        return {
            "query": query,
            "candidates": candidates,
            "match_type": match_result.get('match_type', 'none'),
            "model_used": "preview-mode (本地数据)",
            "latency_ms": 10,
            "scene_filter": scene_filter
        }
    
    def delete_sample(self, index: int) -> Dict:
        """删除样本"""
        
        success = self.preview_manager.delete_sample(index)
        
        return {
            "success": success,
            "index": index,
            "total_samples": self.preview_manager.get_sample_count(),
            "message": "删除成功" if success else "删除失败（索引无效）"
        }
    
    def search(self, query: str, top_k: int = 5, scene_filter: str = None) -> Dict:
        """检索相似样本"""
        self._ensure_v2_adapter()
        self._sync_v2_adapter()
        if self.v2_adapter:
            try:
                return self.v2_adapter.match_v2(
                    query=query,
                    top_k=top_k,
                    scene_hint=scene_filter,
                    inference_mode='retrieval_only',
                )
            except Exception:
                self.v2_adapter = None
        
        similar = self.preview_manager.match_similar(query, top_k=top_k)
        
        results = []
        all_samples = self.preview_manager.get_all_samples()
        for sample in similar:
            sample_index = all_samples.index(sample) if sample in all_samples else None
            results.append({
                "sample_id": f"local_{similar.index(sample)}",
                "parent_message": sample.get('parent_message', ''),
                "advisor_reply": sample.get('replies', [''])[0],
                "scene_tag": sample.get('scene_tag', ''),
                "similarity": sample.get('match_score', 0.5),
                "source_type": "local_keyword",
                "matched_sample_id": str(sample_index) if sample_index is not None else "",
            })
        
        return {
            "query": query,
            "total": len(results),
            "results": results
        }
    
    def start_context_session(self, session_id: str = None):
        if self.v2_adapter:
            return self.v2_adapter.start_context_session(session_id)
        return None

    def add_context_user_message(self, content: str, metadata: Dict = None):
        if self.v2_adapter:
            return self.v2_adapter.add_context_user_message(content, metadata=metadata)
        return None

    def add_context_assistant_reply(self, content: str, metadata: Dict = None):
        if self.v2_adapter:
            return self.v2_adapter.add_context_assistant_reply(content, metadata=metadata)
        return None

    def add_context_system_message(self, content: str):
        if self.v2_adapter:
            return self.v2_adapter.add_context_system_message(content)
        return None

    def build_prompt_context(self, max_turns: int = None, format_template: str = None) -> str:
        if self.v2_adapter:
            return self.v2_adapter.build_prompt_context(max_turns=max_turns, format_template=format_template)
        return ""

    def get_context_summary(self) -> Dict:
        if self.v2_adapter:
            return self.v2_adapter.get_context_summary()
        return {}

    def cluster_saved_samples(self, method: str = "greedy", text_field: str = "parent_message"):
        if self.v2_adapter:
            return self.v2_adapter.cluster_saved_samples(method=method, text_field=text_field)
        return None

    def get_cluster_summary(self, method: str = "greedy", text_field: str = "parent_message") -> Optional[str]:
        if self.v2_adapter:
            return self.v2_adapter.get_cluster_summary(method=method, text_field=text_field)
        return None

    def find_similar_saved_samples(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.3,
        text_field: str = "parent_message",
    ) -> List[Dict]:
        if self.v2_adapter:
            return self.v2_adapter.find_similar_saved_samples(
                query,
                top_k=top_k,
                threshold=threshold,
                text_field=text_field,
            )
        return []

    def suggest_saved_sample_categories(self, max_categories: int = 10, text_field: str = "parent_message") -> List[Dict]:
        if self.v2_adapter:
            return self.v2_adapter.suggest_saved_sample_categories(
                max_categories=max_categories,
                text_field=text_field,
            )
        return []

    def create_sample(self, parent_message: str, advisor_reply: str,
                      scene_tag: str = None, quality_score: int = 1) -> Dict:
        """创建样本"""
        
        sample_id = self.preview_manager.add_sample(
            parent_message=parent_message,
            replies=[advisor_reply],
            scene_tag=scene_tag
        )
        
        return {
            "sample_id": sample_id,
            "status": "active",
            "message": "样本已保存到本地数据",
            "total_samples": self.preview_manager.get_sample_count()
        }
    
    def import_samples(self, samples: List[Dict]) -> Dict:
        """批量导入样本"""
        
        imported = self.preview_manager.import_conversations(samples)
        
        return {
            "imported_count": imported,
            "total_samples": self.preview_manager.get_sample_count(),
            "message": f"成功导入 {imported} 条样本"
        }
    
    def get_stats(self) -> Dict:
        """获取统计"""
        return {
            "total_samples": self.preview_manager.get_sample_count(),
            "preview_mode": True,
            "has_api_key": self.preview_manager.has_api_key(),
            "data_path": str(self.preview_manager.data_path)
        }
    
    def check_available(self) -> Dict:
        """检查可用性"""
        return {
            "preview_mode": True,
            "local_data_available": True,
            "llm_available": self.preview_manager.has_api_key(),
            "sample_count": self.preview_manager.get_sample_count()
        }


# ===== 测试入口 =====

if __name__ == '__main__':
    # 测试预览模式
    pm = PreviewModeManager()
    
    # 测试精确匹配
    print("=== 测试精确匹配 ===")
    result = pm.match("价格有点高，我们再考虑一下")
    print(f"匹配类型: {result['match_type']}")
    print(f"候选数: {len(result['candidates'])}")
    
    # 测试相似匹配
    print("\n=== 测试相似匹配 ===")
    result = pm.match("太贵了，能不能便宜点")
    print(f"匹配类型: {result['match_type']}")
    for c in result['candidates']:
        print(f"  - {c['style_tag']}: {c['content'][:30]}...")
    
    # 测试无匹配
    print("\n=== 测试无匹配 ===")
    result = pm.match("请问你们有游泳课吗")
    print(f"匹配类型: {result['match_type']}")
    print(f"消息: {result.get('message', 'N/A')}")
    
    # 添加新样本
    print("\n=== 添加新样本 ===")
    pm.add_sample(
        parent_message="请问你们有游泳课吗",
        replies=["我们目前主要提供学科类辅导课程，暂时没有游泳课。不过我们有合作的运动机构，可以推荐给您。"],
        scene_tag="问课程"
    )
    print(f"样本总数: {pm.get_sample_count()}")
    
    # 再次匹配
    result = pm.match("请问你们有游泳课吗")
    print(f"再次匹配类型: {result['match_type']}")
