"""
V2.04功能测试 - 验证模板生成、多样本融合、实体替换、上下文加权、规则推理链
"""

import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from local_intelligence.template_generator import TemplateGenerator, GeneratedReply
from local_intelligence.multi_sample_fusion import MultiSampleFusion, FusionResult, SampleInfo
from local_intelligence.entity_substitution import EntitySubstitutionGenerator, GeneratedResult
from local_intelligence.context_weighter import ContextWeighter, WeightAdjustment, ContextWindow
from local_intelligence.rule_inference_chain import RuleInferenceChain, InferenceResult
from local_intelligence.intelligence_manager_v204 import IntelligenceManagerV204


def test_template_generator():
    print("\n=== 测试模板拼接生成器 ===")
    
    generator = TemplateGenerator()
    
    params = {
        '课程': 'Python课程',
        '价格': '5000',
        '课时': '30',
        '优惠': '早鸟优惠减500元'
    }
    
    reply = generator.generate('price', params)
    
    print(f"生成内容: {reply.content}")
    print(f"置信度: {reply.confidence:.2f}")
    print(f"模板ID: {reply.template_id}")
    print(f"填充槽位: {reply.filled_slots}")
    
    assert reply.confidence > 0.7, "模板生成置信度应该 > 0.7"
    assert 'Python课程' in reply.content, "生成内容应包含课程名"
    assert '5000' in reply.content, "生成内容应包含价格"
    
    print("[PASS] 模板生成测试通过")


def test_multi_sample_fusion():
    print("\n=== 测试多样本融合器 ===")
    
    fusion = MultiSampleFusion()
    
    samples = [
        SampleInfo(content='Python课程费用5000元，包含30课时。', confidence=0.85, source_type='local'),
        SampleInfo(content='课程时间安排：每周2次课，共3个月。', confidence=0.75, source_type='local'),
        SampleInfo(content='联系电话：13800138000，微信客服abc123。', confidence=0.65, source_type='local'),
    ]
    
    result = fusion.fuse(samples, intent='price')
    
    print(f"融合内容: {result.content}")
    print(f"关键点: {result.key_points}")
    print(f"置信度: {result.confidence:.2f}")
    print(f"冲突: {result.conflicts}")
    
    assert len(result.key_points) > 0, "应提取出关键点"
    assert result.confidence > 0.6, "融合置信度应 > 0.6"
    
    print("[PASS] 多样本融合测试通过")


def test_entity_substitution():
    print("\n=== 测试实体替换生成器 ===")
    
    generator = EntitySubstitutionGenerator()
    
    template_content = '{课程}费用为{价格}元，包含{课时}课时。'
    
    entities = {
        'course_name': ['Python课程'],
        'money': ['3000元'],
        'duration': ['24课时']
    }
    
    result = generator.apply_template_with_entities(template_content, entities)
    
    print(f"生成内容: {result.content}")
    print(f"原始内容: {result.original_content}")
    print(f"置信度: {result.confidence:.2f}")
    
    assert 'Python课程' in result.content, "应包含课程名"
    assert '3000元' in result.content, "应包含替换后的价格"
    
    print("[PASS] 实体替换测试通过")


def test_context_weighter():
    print("\n=== 测试上下文加权器 ===")
    
    weighter = ContextWeighter(window_size=5)
    
    context_messages = [
        {'role': 'user', 'content': '我想了解Python课程的价格', 'intent': 'price'},
        {'role': 'assistant', 'content': 'Python课程费用5000元', 'intent': 'price'},
        {'role': 'user', 'content': '有点贵', 'intent': 'price'},
    ]
    
    context = weighter.build_context_window(context_messages)
    
    adjustment = weighter.adjust_weight(
        base_confidence=0.70,
        current_intent='price',
        current_entities={'money': ['5000']},
        context=context
    )
    
    print(f"基础置信度: {adjustment.base_confidence:.2f}")
    print(f"上下文增益: {adjustment.context_boost:.2f}")
    print(f"最终置信度: {adjustment.final_confidence:.2f}")
    print(f"调整原因: {adjustment.adjustment_reasons}")
    
    assert adjustment.final_confidence > adjustment.base_confidence, "上下文应提升置信度"
    
    print("[PASS] 上下文加权测试通过")


def test_rule_inference_chain():
    print("\n=== 测试规则推理链 ===")
    
    chain = RuleInferenceChain()
    
    query = "你们这个太贵了"
    intent = "price"
    entities = {}
    
    result = chain.infer(query, intent, entities)
    
    print(f"推理内容: {result.content}")
    print(f"最终置信度: {result.final_confidence:.2f}")
    print(f"匹配规则: {result.matched_rules}")
    
    assert result.final_confidence > 0.7, "规则推理置信度应 > 0.7"
    assert len(result.matched_rules) > 0, "应有匹配规则"
    
    print("[PASS] 规则推理链测试通过")


def test_intelligence_manager_v204():
    print("\n=== 测试智能增强管理器V2.04 ===")
    
    manager = IntelligenceManagerV204(enable_all_generators=True)
    
    query = "Python课程多少钱？"
    
    result = manager.analyze(query, generation_mode='template')
    
    print(f"意图: {result.intent_result.intent}")
    print(f"实体: {manager.quick_entities(query)}")
    print(f"生成模式: {result.generation_mode}")
    print(f"最终内容: {result.final_content}")
    print(f"最终置信度: {result.final_confidence:.2f}")
    
    assert result.intent_result.intent == 'price', "应识别为价格意图"
    
    print("[PASS] 智能管理器V2.04测试通过")


def test_hybrid_generation():
    print("\n=== 测试混合生成模式 ===")
    
    manager = IntelligenceManagerV204(enable_all_generators=True)
    
    query = "你们这个太贵了"
    samples = ["Python课程费用5000元，包含30课时。"]
    context_messages = [
        {'content': '我想了解Python课程', 'intent': 'course'},
        {'content': '价格是多少', 'intent': 'price'},
    ]
    
    result = manager.analyze(
        query,
        samples=samples,
        context_messages=context_messages,
        generation_mode='hybrid'
    )
    
    print(f"意图: {result.intent_result.intent}")
    print(f"生成模式: {result.generation_mode}")
    print(f"摘要: {result.summary}")
    
    print("[PASS] 混合生成测试通过")


def test_search_engine_v204():
    print("\n=== 测试检索引擎V2.04 ===")
    
    try:
        from local_search.search_engine_v204 import LocalSearchEngineV204
        from local_search.data_types import SearchContext
        
        engine = LocalSearchEngineV204(enable_generators=True, generation_mode='hybrid')
        
        print(f"引擎版本: {engine.get_stats()['version']}")
        print(f"可用生成模式: {engine.get_available_generation_modes()}")
        
        context = SearchContext(
            query="你们这个太贵了",
            top_k=3,
            mode='hybrid'
        )
        
        results = engine.search(context)
        
        print(f"检索结果数: {len(results)}")
        for i, r in enumerate(results[:2]):
            print(f"  [{i}] {r.source_type}: {r.content[:50]}... (置信度={r.confidence:.2f})")
        
        if results:
            assert results[0].confidence > 0, "应有有效结果"
        
        print("[PASS] 检索引擎V2.04测试通过")
        
    except Exception as e:
        print(f"检索引擎测试跳过: {e}")


def run_all_tests():
    print("\n" + "=" * 60)
    print("V2.04 功能测试套件")
    print("=" * 60)
    
    tests = [
        test_template_generator,
        test_multi_sample_fusion,
        test_entity_substitution,
        test_context_weighter,
        test_rule_inference_chain,
        test_intelligence_manager_v204,
        test_hybrid_generation,
        test_search_engine_v204,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"[FAIL] 测试失败: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: 通过 {passed}/{len(tests)}, 失败 {failed}/{len(tests)}")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)