"""测试脚本 - V2.00模块验证"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)


def test_data_types():
    """测试数据类型"""
    print("=" * 50)
    print("测试数据类型")
    print("=" * 50)
    
    from local_search.data_types import SearchContext, SearchResult, WeightConfig
    
    context = SearchContext(
        query="价格有点高",
        top_k=5,
        mode='hybrid',
        inference_mode='retrieval_only'
    )
    print(f"[OK] SearchContext创建成功: {context.query}")
    
    result = SearchResult(
        reply_id='test_001',
        content='这是一个测试回复',
        confidence=0.85,
        source_type='local_exact',
        source_detail='精确匹配'
    )
    print(f"[OK] SearchResult创建成功: {result.content}")
    print(f"  is_local: {result.is_local()}")
    print(f"  is_ai: {result.is_ai_generated()}")
    
    weight = WeightConfig()
    print(f"[OK] WeightConfig创建成功: {weight.to_dict()}")
    
    print()


def test_retrievers():
    """测试检索器"""
    print("=" * 50)
    print("测试检索器")
    print("=" * 50)
    
    from local_search.data_types import SearchContext
    from local_search.retrievers import ExactRetriever, KeywordRetriever, HybridRetriever
    
    samples = [
        {
            'parent_message': '价格有点高，我们再考虑一下',
            'replies': ['回复1', '回复2'],
            'keywords': ['价格', '贵', '高']
        },
        {
            'parent_message': '这门课程适合几岁的孩子？',
            'replies': ['回复3'],
            'keywords': ['课程', '年龄']
        }
    ]
    
    context = SearchContext(query='价格有点高', top_k=3)
    
    exact_retriever = ExactRetriever()
    exact_results = exact_retriever.retrieve(context, samples)
    print(f"[OK] ExactRetriever: {len(exact_results)}条结果")
    for r in exact_results:
        print(f"  - {r.source_type}: {r.confidence}")
    
    keyword_retriever = KeywordRetriever()
    keyword_results = keyword_retriever.retrieve(context, samples)
    print(f"[OK] KeywordRetriever: {len(keyword_results)}条结果")
    for r in keyword_results:
        print(f"  - {r.source_type}: {r.confidence}")
    
    hybrid_retriever = HybridRetriever()
    hybrid_results = hybrid_retriever.retrieve(context, samples)
    print(f"[OK] HybridRetriever: {len(hybrid_results)}条结果")
    for r in hybrid_results:
        print(f"  - {r.source_type}: {r.confidence}")
    
    print()


def test_search_engine():
    """测试检索引擎"""
    print("=" * 50)
    print("测试检索引擎")
    print("=" * 50)
    
    from local_search.data_types import SearchContext
    from local_search.search_engine import LocalSearchEngine
    
    data_path = Path(__file__).parent.parent / 'data' / 'local_data.json'
    
    engine = LocalSearchEngine(data_path=str(data_path))
    
    print(f"[OK] 搜索引擎初始化成功")
    print(f"  样本数: {engine.get_sample_count()}")
    
    context = SearchContext(
        query='价格有点高',
        top_k=5,
        mode='hybrid'
    )
    
    results = engine.search(context)
    
    print(f"[OK] 搜索完成: {len(results)}条结果")
    for r in results:
        print(f"  - [{r.source_type}] {r.confidence:.2f}: {r.content[:50]}...")
    
    stats = engine.get_stats()
    print(f"[OK] 统计信息: {stats}")
    
    print()


def test_providers():
    """测试AI提供商"""
    print("=" * 50)
    print("测试AI提供商（不调用实际API）")
    print("=" * 50)
    
    from remote_ai.providers import get_provider, get_available_providers
    
    providers = get_available_providers()
    print(f"[OK] 可用提供商: {providers}")
    
    for provider_name in providers:
        provider = get_provider(provider_name, 'test_key')
        info = provider.get_provider_info()
        print(f"  - {provider_name}: {info['model']}")
    
    print()


def test_user_key_engine():
    """测试用户自带Key引擎"""
    print("=" * 50)
    print("测试UserKeyAIEngine")
    print("=" * 50)
    
    from remote_ai.user_key_engine import UserKeyAIEngine
    
    engine = UserKeyAIEngine()
    
    engine.configure_provider('deepseek', 'test_key', model='deepseek-chat')
    print(f"[OK] 配置DeepSeek成功")
    
    summary = engine.get_config_summary()
    print(f"[OK] 配置摘要: {summary}")
    
    print()


def test_unified_engine():
    """测试统一推理引擎"""
    print("=" * 50)
    print("测试UnifiedInferenceEngine")
    print("=" * 50)
    
    from local_search.data_types import SearchContext
    from remote_ai.unified_engine import UnifiedInferenceEngine
    
    engine = UnifiedInferenceEngine()
    
    print(f"[OK] 统一引擎初始化成功")
    print(f"  可用模式: {engine.get_available_modes()}")
    
    context = SearchContext(
        query='价格有点高',
        top_k=3,
        inference_mode='retrieval_only'
    )
    
    results = engine.search(context)
    
    print(f"[OK] 搜索完成: {len(results)}条结果")
    for r in results:
        print(f"  - [{r.source_type}] {r.confidence:.2f}")
    
    print()


def test_gui_display():
    """测试GUI显示"""
    print("=" * 50)
    print("测试GUIDisplayHelper")
    print("=" * 50)
    
    from local_search.data_types import SearchResult
    from local_search.gui_display import GUIDisplayHelper
    
    helper = GUIDisplayHelper()
    
    result = SearchResult(
        reply_id='test_001',
        content='测试回复内容',
        confidence=0.85,
        source_type='local_exact',
        source_detail='精确匹配'
    )
    
    formatted = helper.format_result_for_display(result)
    print(f"[OK] 格式化成功:")
    print(f"  - icon: {formatted['icon']}")
    print(f"  - color: {formatted['color']}")
    print(f"  - source_label: {formatted['source_label']}")
    print(f"  - confidence_label: {formatted['confidence_label']}")
    
    print()


def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print(" V2.00 模块测试")
    print("=" * 60 + "\n")
    
    try:
        test_data_types()
        test_retrievers()
        test_search_engine()
        test_providers()
        test_user_key_engine()
        test_unified_engine()
        test_gui_display()
        
        print("\n" + "=" * 60)
        print(" 所有测试通过！")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()