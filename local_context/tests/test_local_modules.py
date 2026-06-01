import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from local_context import LocalContextManager, ContextWindow, WindowStrategy
from local_cluster import LocalClusterManager, SimilarityMethod, SimilarityCalculator


def test_context_manager():
    print("=" * 60)
    print("测试 LocalContextManager")
    print("=" * 60)
    
    manager = LocalContextManager(
        window_strategy=WindowStrategy.FIXED_SIZE,
        max_turns=5
    )
    
    print("\n1. 启动会话")
    session_id = manager.start_session()
    print(f"   会话ID: {session_id}")
    
    print("\n2. 添加对话")
    manager.add_user_message("您好，我想咨询一下课程价格")
    manager.add_assistant_reply("您好！我们的课程价格根据不同级别有所不同，初级课程500元，中级课程800元，高级课程1200元。")
    manager.add_user_message("那高级课程包括哪些内容呢？")
    manager.add_assistant_reply("高级课程包括：项目实战、架构设计、性能优化、源码分析等模块，共计48课时。")
    manager.add_user_message("有优惠吗？")
    manager.add_assistant_reply("目前报名高级课程可以享受早鸟优惠，立减200元，实际价格1000元。")
    
    print("\n3. 获取当前上下文（窗口限制5轮）")
    context = manager.get_current_context()
    for turn in context:
        role_icon = "[U]" if turn.role.value == "user" else "[A]"
        print(f"   {role_icon} {turn.content}")
    
    print("\n4. 获取会话摘要")
    summary = manager.get_session_summary()
    print(f"   对话数: {summary['count']}")
    print(f"   角色: {summary['roles']}")
    print(f"   预估tokens: {summary['estimated_tokens']}")
    
    print("\n5. 构建提示上下文")
    prompt_context = manager.build_prompt_context(format_template="[{role}] {content}")
    print(prompt_context)
    
    print("\n6. 搜索关键词")
    keyword_results = manager.search_by_keywords(["价格", "优惠"])
    print(f"   找到 {len(keyword_results)} 条相关对话")
    for turn in keyword_results:
        print(f"   - {turn.content[:30]}...")
    
    print("\n7. 获取对话对")
    pairs = manager.get_conversation_pairs(limit=3)
    print(f"   对话对数: {len(pairs)}")
    for pair in pairs:
        print(f"   Q: {pair['query'].content[:30]}...")
        print(f"   R: {pair['reply'].content[:30]}...")
    
    print("\n[OK] LocalContextManager 测试完成")


def test_cluster_manager():
    print("\n" + "=" * 60)
    print("测试 LocalClusterManager")
    print("=" * 60)
    
    samples = [
        "您好，我想咨询一下课程价格，请问初级课程多少钱？",
        "老师您好，请问高级课程的收费标准是什么？",
        "你好，我想了解一下Python课程的费用",
        "请问有没有关于价格优惠的活动？",
        "您好，我想报名课程，有早鸟优惠吗？",
        "老师，课程质量怎么样？有试听吗？",
        "请问课程的内容包括哪些模块？",
        "高级课程有什么特色？和其他课程有什么区别？",
        "您好，请问上课时间是怎么安排的？",
        "老师，课程时长是多少？每周几次课？",
    ]
    
    manager = LocalClusterManager(
        similarity_threshold=0.3,
        min_cluster_size=2,
        similarity_method=SimilarityMethod.JACCARD
    )
    
    print("\n1. 关键词提取")
    for i, sample in enumerate(samples[:3]):
        keywords = manager.get_sample_keywords(sample)
        print(f"   样本{i+1}: {keywords}")
    
    print("\n2. 获取所有关键词统计")
    keywords_info = manager.get_all_keywords(samples)
    print(f"   总关键词数: {keywords_info['total_unique']}")
    print(f"   热门关键词: {keywords_info['keywords'][:10]}")
    
    print("\n3. 聚类分析（greedy方法）")
    report = manager.cluster_samples(samples, method="greedy")
    print(f"   聚类数: {report.total_clusters}")
    print(f"   统计: 平均大小={report.statistics['avg_cluster_size']:.1f}, 单例数={report.statistics['singleton_count']}")
    
    print("\n4. 按关键词分组")
    keyword_groups = manager.cluster_by_keywords(samples)
    for keyword, group_samples in keyword_groups.items():
        print(f"   【{keyword}】({len(group_samples)}条)")
        for s in group_samples[:2]:
            print(f"     - {s[:40]}...")
    
    print("\n5. 查找相似样本")
    query = "请问课程价格是多少？有优惠吗？"
    similar = manager.find_similar_samples(query, samples, top_k=3, threshold=0.2)
    print(f"   查询: {query}")
    print(f"   相似样本:")
    for item in similar:
        print(f"   [{item['similarity']:.3f}] {item['sample'][:40]}...")
        print(f"     共同关键词: {item['common_keywords']}")
    
    print("\n6. 查重分析")
    duplicates = manager.analyze_duplicates(samples, duplicate_threshold=0.5)
    print(f"   可能重复对数: {duplicates['duplicate_count']}")
    if duplicates['duplicate_pairs']:
        for dup in duplicates['duplicate_pairs'][:3]:
            print(f"   [{dup['similarity']:.3f}] 样本{dup['index_1']} <-> 样本{dup['index_2']}")
    
    print("\n7. 推荐分类")
    categories = manager.suggest_categories(samples, max_categories=5)
    for cat in categories:
        print(f"   【{cat['category']}】关键词出现{cat['count']}次，涉及{cat['sample_count']}条样本")
    
    print("\n8. 聚类摘要")
    summary = manager.get_cluster_summary()
    print(summary)
    
    print("\n[OK] LocalClusterManager 测试完成")


def test_similarity_methods():
    print("\n" + "=" * 60)
    print("测试不同相似度计算方法")
    print("=" * 60)
    
    text1 = "您好，我想咨询课程价格"
    text2 = "老师您好，请问课程费用是多少"
    
    methods = [
        SimilarityMethod.JACCARD,
        SimilarityMethod.COSINE,
        SimilarityMethod.DICE,
        SimilarityMethod.OVERLAP,
    ]
    
    for method in methods:
        calc = SimilarityCalculator(method=method)
        result = calc.calculate(text1, text2)
        print(f"   {method.value}: {result.similarity:.3f}")
        print(f"     共同关键词: {result.common_keywords}")


def test_context_window_strategies():
    print("\n" + "=" * 60)
    print("测试不同窗口策略")
    print("=" * 60)
    
    manager = LocalContextManager(max_turns=20)
    manager.start_session()
    
    from datetime import datetime, timedelta
    
    now = datetime.now()
    for i in range(10):
        manager.add_user_message(f"用户问题{i+1}: 请问课程内容{i+1}")
        manager.add_assistant_reply(f"助手回复{i+1}: 关于课程内容{i+1}的详细解答")
    
    print("\n1. 固定大小窗口（最多5轮）")
    manager.switch_strategy(WindowStrategy.FIXED_SIZE, max_turns=5)
    context = manager.get_current_context()
    print(f"   保留轮数: {len(context)}")
    
    print("\n2. 时间窗口（最近1分钟）")
    manager.switch_strategy(WindowStrategy.TIME_BASED, max_time_minutes=1)
    context = manager.get_current_context()
    print(f"   保留轮数: {len(context)}")
    
    print("\n[OK] 窗口策略测试完成")


if __name__ == "__main__":
    test_context_manager()
    test_cluster_manager()
    test_similarity_methods()
    test_context_window_strategies()
    
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)