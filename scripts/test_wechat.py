#!/usr/bin/env python3
"""本地模拟测试 - 公众号回调"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import hashlib
import time
import requests

BASE_URL = "http://localhost:5000/api/v1/wechat"


def generate_signature(token: str, timestamp: str, nonce: str) -> str:
    """生成模拟签名"""
    
    params = [token, timestamp, nonce]
    params.sort()
    
    joined = ''.join(params)
    
    return hashlib.sha1(joined.encode()).hexdigest()


def test_verify_callback():
    """测试服务器验证"""
    
    token = "test_token"
    timestamp = str(int(time.time()))
    nonce = "123456"
    echostr = "hello_wechat"
    
    signature = generate_signature(token, timestamp, nonce)
    
    print("\n[测试] 服务器验证")
    print(f"  signature: {signature}")
    print(f"  timestamp: {timestamp}")
    print(f"  nonce: {nonce}")
    print(f"  echostr: {echostr}")
    
    response = requests.get(
        f"{BASE_URL}/callback",
        params={
            "signature": signature,
            "timestamp": timestamp,
            "nonce": nonce,
            "echostr": echostr
        }
    )
    
    print(f"  响应: {response.status_code} - {response.text}")


def test_text_message(content: str):
    """测试文本消息"""
    
    token = "test_token"
    timestamp = str(int(time.time()))
    nonce = "123456"
    
    signature = generate_signature(token, timestamp, nonce)
    
    xml_message = f"""<xml>
<ToUserName>gh_test_public</ToUserName>
<FromUserName>oTestUser123</FromUserName>
<CreateTime>{timestamp}</CreateTime>
<MsgType>text</MsgType>
<Content>{content}</Content>
<MsgId>1234567890</MsgId>
</xml>"""
    
    print("\n[测试] 文本消息")
    print(f"  内容: {content[:50]}...")
    
    response = requests.post(
        f"{BASE_URL}/callback",
        params={
            "signature": signature,
            "timestamp": timestamp,
            "nonce": nonce
        },
        data=xml_message.encode('utf-8'),
        headers={"Content-Type": "application/xml"}
    )
    
    print(f"  响应: {response.status_code}")
    print(f"  内容: {response.text[:200]}")


def test_learn_command():
    """测试 #学习 指令"""
    
    content = """#学习
家长问题：价格有点高，我们再考虑一下
顾问回复：理解您的顾虑，我这边先不催您定，如果您方便，我把孩子试听时的课堂表现整理给您"""
    
    test_text_message(content)


def test_forward_message():
    """测试合并转发"""
    
    content = """张家长
2026年05月18日 14:30
价格有点高，我们再考虑一下

李顾问
2026年05月18日 14:35
理解您的顾虑，我这边先不催您定"""
    
    test_text_message(content)


def test_check_status():
    """检查服务状态"""
    
    print("\n[测试] 服务状态")
    
    response = requests.get(f"{BASE_URL}/status")
    
    print(f"  响应: {response.json()}")


def main():
    """主测试流程"""
    
    print("=" * 50)
    print("公众号回调服务 - 本地模拟测试")
    print("=" * 50)
    
    try:
        test_check_status()
        
        test_verify_callback()
        
        test_text_message("你好")
        
        test_learn_command()
        
        test_forward_message()
        
    except requests.exceptions.ConnectionError:
        print("\n[错误] 服务未启动，请先运行:")
        print("  python server/app/main.py")
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == '__main__':
    main()