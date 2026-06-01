#!/usr/bin/env python3
"""LLM 调用验证脚本"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'server'))

from server.app.llm.llm_service import LLMService
from server.app.llm.openai_client import PROVIDER_CONFIGS


def test_list_providers():
    print("=" * 50)
    print("支持的模型提供商列表")
    print("=" * 50)
    
    providers = LLMService.list_providers()
    
    for name, config in providers.items():
        print(f"\n[{name}]")
        print(f"  API Base: {config['api_base']}")
        print(f"  Models: {', '.join(config['models'])}")
        print(f"  Default: {config['default_model']}")


def test_system_client():
    print("\n" + "=" * 50)
    print("系统默认客户端检查")
    print("=" * 50)
    
    available = LLMService.is_available()
    print(f"\n状态: {'可用' if available else '不可用'}")
    
    if available:
        client = LLMService.get_default_client()
        print(f"提供商: {client.provider_name}")
        print(f"模型: {client.model_name}")
    else:
        print("请设置环境变量 LLM_API_KEY")


def test_user_client(api_key: str, provider: str = "deepseek"):
    print("\n" + "=" * 50)
    print(f"用户自定义客户端测试 ({provider})")
    print("=" * 50)
    
    try:
        client = LLMService.create_user_client(provider, api_key)
        print(f"客户端创建成功")
        print(f"提供商: {client.provider_name}")
        print(f"模型: {client.model_name}")
        print(f"可用: {client.is_available()}")
        
        return client
    except Exception as e:
        print(f"创建失败: {e}")
        return None


def test_chat(client_or_key, provider: str = "deepseek"):
    print("\n" + "=" * 50)
    print("聊天测试")
    print("=" * 50)
    
    if isinstance(client_or_key, str):
        client = LLMService.create_user_client(provider, client_or_key)
    else:
        client = client_or_key
    
    if not client or not client.is_available():
        print("客户端不可用")
        return
    
    prompt = "你好，请用一句话介绍你自己。"
    
    print(f"\n发送消息: {prompt}")
    
    try:
        response = client.simple_chat(prompt)
        
        print(f"\n响应:")
        print(f"  模型: {response.model}")
        print(f"  内容: {response.content}")
        print(f"  Token: {response.usage}")
        print(f"  耗时: {response.latency_ms}ms")
        print(f"  结束原因: {response.finish_reason}")
        
    except Exception as e:
        print(f"\n调用失败: {e}")


def test_generate_service(api_key: str = None):
    print("\n" + "=" * 50)
    print("GenerateService 测试")
    print("=" * 50)
    
    from server.app.services.generate_service import GenerateService
    from shared.schemas.sample import GenerateReplyRequest
    
    if api_key:
        import os
        os.environ['LLM_API_KEY'] = api_key
    
    service = GenerateService()
    
    request = GenerateReplyRequest(
        query="价格有点高，我们再考虑一下",
        scene_hint="问价格",
        stage_hint="试听后",
    )
    
    print(f"\n请求: {request.query}")
    print(f"场景: {request.scene_hint}")
    print(f"阶段: {request.stage_hint}")
    
    response = service.generate_reply("test_user", request)
    
    print(f"\n响应:")
    print(f"  模型: {response.model_used}")
    print(f"  候选数: {len(response.candidates)}")
    print(f"  耗时: {response.latency_ms}ms")
    
    for i, candidate in enumerate(response.candidates):
        print(f"\n  候选{i+1} [{candidate.style_tag}]:")
        print(f"    {candidate.content[:100]}...")
        print(f"    置信度: {candidate.confidence}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='LLM 调用测试')
    parser.add_argument('--api-key', help='API Key')
    parser.add_argument('--provider', default='deepseek', help='提供商名称')
    parser.add_argument('--test', choices=['list', 'check', 'chat', 'generate', 'all'], default='all', help='测试类型')
    
    args = parser.parse_args()
    
    if args.test == 'list' or args.test == 'all':
        test_list_providers()
    
    if args.test == 'check' or args.test == 'all':
        test_system_client()
    
    if args.test == 'chat' and args.api_key:
        test_chat(args.api_key, args.provider)
    
    if args.test == 'generate' and args.api_key:
        test_generate_service(args.api_key)
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)