"""V2.03测试脚本 - 向量检索+智能增强集成"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from local_search import (
    LocalSearchEngine,
    SearchContext,
    SearchResult,
    LocalEmbeddingService,
    LocalChromaRepo
)


def test_embedding_service():
    """测试Embedding服务"""
    print("=" * 60)
    print("测试 LocalEmbeddingService")
    print("=" * 60)
    
    service = LocalEmbeddingService()
    
    info = service.get_model_info()
    print(f"模型信息: {info}")
    
    if not service.is_available():
        print("[警告] sentence-transformers未安装，Embedding服务不可用")
        print("[提示] 运行: pip install sentence-transformers")
        return False
    
    text = "课程多少钱"
    embedding = service.embed(text)
    
    if embedding:
        print(f"[OK] 文本: '{text}'")
        print(f"  Embedding维度: {len(embedding)}")
        print(f"  前5个值: {embedding[:5]}")
        
        text2 = "价格是多少"
        embedding2 = service.embed(text2)
        
        if embedding2:
            similarity = service.similarity(embedding, embedding2)
            print(f"[OK] 相似度计算:")
            print(f"  '{text}' vs '{text2}'")
            print(f"  相似度: {similarity:.4f}")
        
        return True
    else:
        print("[FAIL] Embedding生成失败")
        return False


def test_chroma_repo():
    """测试Chroma向量库"""
    print("\n" + "=" * 60)
    print("测试 LocalChromaRepo")
    print("=" * 60)
    
    repo = LocalChromaRepo()
    
    stats = repo.get_stats()
    print(f"统计信息: {stats}")
    
    if not repo.is_available():
        print("[警告] chromadb未安装，向量库不可用")
        print("[提示] 运行: pip install chromadb")
        return False
    
    print(f"[OK] Chroma可用")
    print(f"  持久化路径: {repo.persist_dir}")
    
    count = repo.get_count()
    print(f"  当前样本数: {count}")
    
    return True


def test_search_engine():
    """测试LocalSearchEngine"""
    print("\n" + "=" * 60)
    print("测试 LocalSearchEngine")
    print("=" * 60)
    
    engine = LocalSearchEngine()
    
    stats = engine.get_stats()
    print(f"引擎统计:")
    print(f"  样本数: {stats['sample_count']}")
    print(f"  向量样本数: {stats['vector_sample_count']}")
    print(f"  向量可用: {stats['vector_available']}")
    print(f"  Chroma可用: {stats['chroma_available']}")
    print(f"  智能增强: {stats['intelligence_enabled']}")
    
    queries = [
        "课程多少钱",
        "价格是多少",
        "老师是谁",
        "上课时间"
    ]
    
    for query in queries:
        print(f"\n[测试] 查询: '{query}'")
        
        context = SearchContext(query=query, top_k=3, mode='hybrid')
        
        results = engine.search(context)
        
        if results:
            print(f"  结果数: {len(results)}")
            for i, r in enumerate(results[:2]):
                print(f"  [{i+1}] 来源: {r.source_type}")
                print(f"      置信度: {r.confidence:.2f}")
                print(f"      内容: {r.content[:50]}...")
        else:
            print("  [无结果]")
    
    return True


def test_intelligence_integration():
    """测试智能增强集成"""
    print("\n" + "=" * 60)
    print("测试 智能增强集成")
    print("=" * 60)
    
    engine = LocalSearchEngine()
    
    if not engine.enable_intelligence:
        print("[警告] 智能增强未启用（local_intelligence模块未安装）")
        return False
    
    query = "课程多少钱"
    
    analysis = engine.analyze_query(query)
    print(f"[OK] 查询分析: '{query}'")
    print(f"  意图: {analysis.get('intent', 'unknown')}")
    print(f"  置信度: {analysis.get('confidence', 0):.2f}")
    print(f"  实体: {analysis.get('entities', {})}")
    
    context = SearchContext(query=query, top_k=3)
    results = engine.search(context)
    
    for r in results[:1]:
        if hasattr(r, 'source_detail') and '意图' in r.source_detail:
            print(f"[OK] 结果包含意图信息:")
            print(f"  {r.source_detail}")
    
    return True


def test_vector_mode():
    """测试向量检索模式"""
    print("\n" + "=" * 60)
    print("测试 向量检索模式")
    print("=" * 60)
    
    engine = LocalSearchEngine()
    
    if not engine.embedding_service.is_available():
        print("[跳过] Embedding服务不可用")
        return True
    
    queries = [
        ("课程多少钱", "价格是多少"),
        ("老师是谁", "师资怎么样"),
        ("上课时间", "什么时候上课")
    ]
    
    for q1, q2 in queries:
        print(f"\n[对比测试]")
        print(f"  查询1: '{q1}'")
        print(f"  查询2: '{q2}'（语义相似）")
        
        context1 = SearchContext(query=q1, top_k=3, mode='vector')
        context2 = SearchContext(query=q2, top_k=3, mode='vector')
        
        results1 = engine.search(context1)
        results2 = engine.search(context2)
        
        print(f"  查询1结果: {len(results1)}条")
        print(f"  查询2结果: {len(results2)}条")
        
        if results1 and results2:
            print(f"  是否命中相同样本: {results1[0].matched_sample_id == results2[0].matched_sample_id}")
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("V2.03 向量检索+智能增强 - 全量测试")
    print("=" * 60)
    
    tests = [
        ('LocalEmbeddingService', test_embedding_service),
        ('LocalChromaRepo', test_chroma_repo),
        ('LocalSearchEngine', test_search_engine),
        ('智能增强集成', test_intelligence_integration),
        ('向量检索模式', test_vector_mode)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"[ERROR] {name}: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: 通过 {passed}/{len(tests)}")
    print("=" * 60)
    
    return passed, failed


if __name__ == '__main__':
    run_all_tests()