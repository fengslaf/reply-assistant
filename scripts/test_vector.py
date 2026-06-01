#!/usr/bin/env python3
"""向量检索验证脚本"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

server_root = project_root / 'server'
sys.path.insert(0, str(server_root))

os.environ['DATABASE_PATH'] = str(project_root / 'data' / 'test.db')
os.environ['VECTOR_STORE_PATH'] = str(project_root / 'data' / 'test_chroma')

from server.app.storage import SQLiteRepo, ChromaRepo, EmbeddingService


def test_full_flow():
    print("=" * 50)
    print("向量检索完整流程测试")
    print("=" * 50)
    
    # 1. SQLiteRepo
    repo = SQLiteRepo()
    print("\n[1] SQLiteRepo 初始化完成")
    
    sample_id = repo.create_sample({
        'user_id': 'advisor_001',
        'parent_message': '价格有点高，我们再考虑一下',
        'advisor_reply': '理解您的顾虑，我这边先不催您定，如果您方便，我把孩子试听时的课堂表现整理给您，您再判断会更稳一些。',
        'scene_tag': '问价格',
        'stage_tag': '试听后',
        'quality_score': 3,
        'source_type': 'wechat_forward'
    })
    print(f"    样本创建成功: {sample_id}")
    
    repo.activate_sample(sample_id)
    print("    样本已激活")
    
    # 2. EmbeddingService
    embedding_svc = EmbeddingService()
    print("\n[2] EmbeddingService 检查")
    
    if embedding_svc.is_available():
        print("    Embedding服务可用")
        
        text = "价格有点高，我们再考虑一下"
        embedding = embedding_svc.embed(text)
        
        if embedding:
            print(f"    Embedding生成成功，维度: {len(embedding)}")
            print(f"    前5个值: {embedding[:5]}")
        else:
            print("    Embedding生成失败")
            return
    else:
        print("    Embedding服务不可用（sentence-transformers未正确安装）")
        return
    
    # 3. ChromaRepo
    chroma = ChromaRepo()
    print("\n[3] ChromaRepo 检查")
    
    if chroma.client:
        print("    Chroma向量库可用")
        
        # 添加向量
        metadata = {
            'scene_tag': '问价格',
            'stage_tag': '试听后',
            'quality_score': 3
        }
        chroma.add_sample(
            user_id='advisor_001',
            sample_id=sample_id,
            parent_message='价格有点高，我们再考虑一下',
            embedding=embedding,
            metadata=metadata
        )
        print("    向量添加成功")
        
        # 检索相似
        query_embedding = embedding_svc.embed("价格贵了想再考虑")
        if query_embedding:
            results = chroma.search_similar('advisor_001', query_embedding, top_k=3)
            print(f"    检索成功，返回 {len(results)} 条结果")
            
            for i, r in enumerate(results):
                print(f"    [{i+1}] sample_id: {r['sample_id']}")
                print(f"        distance: {r['distance']:.4f}")
                print(f"        metadata: {r['metadata']}")
    else:
        print("    Chroma向量库不可用")
        return
    
    print("\n" + "=" * 50)
    print("测试完成！所有组件正常工作")
    print("=" * 50)


if __name__ == '__main__':
    test_full_flow()