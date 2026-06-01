#!/usr/bin/env python3
"""Storage层验证脚本"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

server_root = project_root / 'server'
sys.path.insert(0, str(server_root))

os.environ['DATABASE_PATH'] = str(project_root / 'data' / 'test.db')

from server.app.storage import SQLiteRepo, EmbeddingService

def test_sqlite():
    repo = SQLiteRepo()
    
    sample_id = repo.create_sample({
        'user_id': 'test_user',
        'parent_message': '价格有点高，我们再考虑一下',
        'advisor_reply': '理解您的顾虑，我这边先不催您定...',
        'source_type': 'pc_instant_save'
    })
    print(f'Sample created: {sample_id}')
    
    sample = repo.get_sample(sample_id)
    if sample:
        print(f'Sample retrieved: {sample["parent_message"][:20]}...')
    else:
        print('Sample not found!')
    
    repo.update_sample(sample_id, {'scene_tag': '问价格', 'stage_tag': '试听后'})
    print('Sample updated')
    
    stats = repo.get_user_stats('test_user')
    print(f'User stats: total={stats["total_samples"]}, drafts={stats["draft_samples"]}')
    
    repo.activate_sample(sample_id)
    print('Sample activated')
    
    print('SQLiteRepo: OK!')

def test_embedding():
    service = EmbeddingService()
    
    if service.is_available():
        embedding = service.embed('价格有点高')
        if embedding:
            print(f'Embedding dimension: {len(embedding)}')
            print('EmbeddingService: OK!')
        else:
            print('Embedding generation failed!')
    else:
        print('EmbeddingService: Not available (sentence-transformers not installed)')
        print('Run: pip install sentence-transformers')

if __name__ == '__main__':
    test_sqlite()
    test_embedding()