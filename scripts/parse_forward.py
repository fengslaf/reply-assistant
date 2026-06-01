#!/usr/bin/env python3
"""合并转发消息解析器"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from shared.constants.enums import RoleGuess
from shared.schemas.sample import ForwardCandidate


def parse_forward_message(content: str) -> List[ForwardCandidate]:
    """
    解析合并转发消息
    
    格式:
        人物标识
        时间（YYYY年MM月DD日 HH:MM）
        消息内容
        （空行分隔下一组）
    
    Args:
        content: 合并转发消息原文
    
    Returns:
        List[ForwardCandidate]: 解析出的候选消息列表
    """
    
    candidates = []
    
    # 按空行分隔多组消息
    blocks = content.strip().split('\n\n')
    
    temp_id_counter = 1
    
    for block in blocks:
        if not block.strip():
            continue
        
        lines = block.strip().split('\n')
        
        if len(lines) < 3:
            # 格式不完整，跳过
            continue
        
        sender = lines[0].strip()
        time_str = lines[1].strip()
        content_lines = lines[2:]  # 消息内容可能有多行
        
        # 验证时间格式: YYYY年MM月DD日 HH:MM
        time_pattern = r'\d{4}年\d{2}月\d{2}日 \d{2}:\d{2}'
        if not re.match(time_pattern, time_str):
            # 时间格式不匹配，尝试其他格式或跳过
            # 宽容处理：如果第二行不是时间，可能整个是消息内容
            if len(lines) >= 1:
                sender = "未知"
                time_str = ""
                content_lines = lines
            else:
                continue
        
        # 合并多行消息内容
        message_content = '\n'.join(content_lines).strip()
        
        if not message_content:
            continue
        
        # 生成临时ID
        temp_id = f"temp_{temp_id_counter:03d}"
        temp_id_counter += 1
        
        # 创建候选
        candidate = ForwardCandidate(
            temp_id=temp_id,
            sender=sender,
            time=time_str,
            content=message_content,
            role_guess=RoleGuess.UNKNOWN.value
        )
        
        candidates.append(candidate)
    
    return candidates


def extract_qa_pairs(candidates: List[ForwardCandidate]) -> List[Tuple[str, str]]:
    """
    从候选消息中提取问答对 (parent_message, advisor_reply)
    
    规则:
        - 相邻消息中，第一问后第一答为一对
        - 需要用户确认角色
    
    Args:
        candidates: 解析出的候选消息
    
    Returns:
        List[Tuple]: (家长问题, 顾问回复) 列表
    """
    
    qa_pairs = []
    
    # TODO: 实现问答对提取逻辑
    # 当前版本：需要用户手动确认角色
    
    return qa_pairs


# ===== 测试 =====
if __name__ == '__main__':
    # 测试用例: 来自转发案例.txt
    test_content = """
xxxx
2026年05月18日 14:30
test

xxxx
2026年05月18日 14:30
testt

yyyy
2026年05月18日 15:26
testxx
"""
    
    results = parse_forward_message(test_content)
    
    print("解析结果:")
    for r in results:
        print(f"  [{r.temp_id}] {r.sender} @ {r.time}: {r.content}")
        print(f"    角色猜测: {r.role_guess}")