"""本地Chroma向量库操作层"""

import hashlib
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMA = True
except ImportError:
    HAS_CHROMA = False


class LocalChromaRepo:
    """本地Chroma向量库 - V2.03
    
    用于存储样本的embedding向量，支持语义检索
    """
    
    def __init__(self, persist_dir: str = None):
        """初始化
        
        Args:
            persist_dir: 向量库持久化路径（默认./data/chroma）
        """
        self.persist_dir = persist_dir or str(Path(__file__).parent.parent / 'data' / 'cache' / 'local_search' / 'chroma')
        
        if not HAS_CHROMA:
            self.client = None
            self.collection = None
            return
        
        persist_path = Path(self.persist_dir)
        persist_path.mkdir(parents=True, exist_ok=True)
        self.sync_state_path = persist_path / 'sync_state.json'
        
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self.collection = None
    
    def get_or_create_collection(self, name: str = 'local_samples') -> Any:
        """获取或创建集合
        
        Args:
            name: 集合名称
            
        Returns:
            Chroma集合对象
        """
        if not HAS_CHROMA:
            return None
        
        if self.collection is None or self.collection.name != name:
            self.collection = self.client.get_or_create_collection(
                name=name,
                metadata={'type': 'local_samples'}
            )
        
        return self.collection

    def _sanitize_metadata_value(self, value: Any) -> Any:
        """Normalize metadata values to Chroma-friendly primitive types."""
        if value is None:
            return ''
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, (list, tuple, set)):
            return ','.join(str(item) for item in value if item is not None)
        return str(value)

    def _sanitize_metadata(self, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not metadata:
            return {}
        return {
            str(key): self._sanitize_metadata_value(value)
            for key, value in metadata.items()
        }

    def _make_sample_key(self, sample: Dict[str, Any]) -> str:
        created_at = str(sample.get('created_at') or '').strip()
        if created_at:
            source = f"created_at::{created_at}"
        else:
            source = json.dumps({
                'parent_message': sample.get('parent_message', ''),
                'replies': sample.get('replies', []),
                'scene_tag': sample.get('scene_tag', ''),
                'stage_tag': sample.get('stage_tag', ''),
                'keywords': sample.get('keywords', []),
            }, ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(source.encode('utf-8')).hexdigest()

    def _make_sample_fingerprint(self, sample: Dict[str, Any]) -> str:
        normalized = {
            'parent_message': sample.get('parent_message', ''),
            'replies': sample.get('replies', []),
            'scene_tag': sample.get('scene_tag', ''),
            'stage_tag': sample.get('stage_tag', ''),
            'keywords': sample.get('keywords', []),
            'quality_score': sample.get('quality_score', 1.0),
            'created_at': sample.get('created_at', ''),
        }
        source = json.dumps(normalized, ensure_ascii=False, sort_keys=True)
        return hashlib.sha1(source.encode('utf-8')).hexdigest()

    def _load_sync_state(self) -> Dict[str, Any]:
        if not hasattr(self, 'sync_state_path') or not self.sync_state_path.exists():
            return {}
        try:
            with open(self.sync_state_path, 'r', encoding='utf-8') as f:
                state = json.load(f)
            return state if isinstance(state, dict) else {}
        except Exception:
            return {}

    def _save_sync_state(self, state: Dict[str, Any]):
        if not hasattr(self, 'sync_state_path'):
            return
        try:
            with open(self.sync_state_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[LocalChromaRepo] 保存同步状态失败: {e}")
    
    def add_sample(self, sample_id: str, parent_message: str, 
                   embedding: List[float], metadata: Dict[str, Any] = None,
                   user_id: str = None):
        """添加样本
        
        Args:
            sample_id: 样本ID
            parent_message: 父消息文本
            embedding: embedding向量
            metadata: 元数据（scene_tag, advisor_reply等）
            
        Returns:
            是否成功
        """
        if not HAS_CHROMA:
            return False
        
        collection = self.get_or_create_collection()
        if collection is None:
            return False
        
        try:
            sanitized_metadata = self._sanitize_metadata(metadata)
            if hasattr(collection, 'upsert'):
                collection.upsert(
                    ids=[sample_id],
                    embeddings=[embedding],
                    documents=[parent_message],
                    metadatas=[sanitized_metadata]
                )
            else:
                try:
                    collection.delete(ids=[sample_id])
                except Exception:
                    pass
                collection.add(
                    ids=[sample_id],
                    embeddings=[embedding],
                    documents=[parent_message],
                    metadatas=[sanitized_metadata]
                )
            return True
        except Exception as e:
            print(f"[LocalChromaRepo] 添加样本失败: {e}")
            return False
    
    def add_samples_batch(self, sample_ids: List[str], parent_messages: List[str],
                          embeddings: List[List[float]], metadatas: List[Dict] = None,
                          user_id: str = None):
        """批量添加样本
        
        Args:
            sample_ids: 样本ID列表
            parent_messages: 父消息列表
            embeddings: embedding向量列表
            metadatas: 元数据列表
            
        Returns:
            成功添加数量
        """
        if not HAS_CHROMA:
            return 0
        
        collection = self.get_or_create_collection()
        if collection is None:
            return 0
        
        try:
            sanitized_metadatas = [
                self._sanitize_metadata(metadata)
                for metadata in (metadatas or [{}] * len(sample_ids))
            ]
            if hasattr(collection, 'upsert'):
                collection.upsert(
                    ids=sample_ids,
                    embeddings=embeddings,
                    documents=parent_messages,
                    metadatas=sanitized_metadatas
                )
            else:
                try:
                    collection.delete(ids=sample_ids)
                except Exception:
                    pass
                collection.add(
                    ids=sample_ids,
                    embeddings=embeddings,
                    documents=parent_messages,
                    metadatas=sanitized_metadatas
                )
            return len(sample_ids)
        except Exception as e:
            print(f"[LocalChromaRepo] 批量添加样本失败: {e}")
            return 0
    
    def search_similar(self, query_embedding: List[float], 
                       top_k: int = 5, user_id: str = None) -> List[Dict[str, Any]]:
        """检索相似样本
        
        Args:
            query_embedding: 查询embedding向量
            top_k: 返回数量
            
        Returns:
            相似样本列表
        """
        if not HAS_CHROMA:
            return []
        
        collection = self.get_or_create_collection()
        if collection is None:
            return []
        
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            if not results or not results['ids'] or not results['ids'][0]:
                return []
            
            similar_items = []
            for i, sample_id in enumerate(results['ids'][0]):
                item = {
                    'sample_id': sample_id,
                    'parent_message': results['documents'][0][i] if results['documents'] else '',
                    'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                    'distance': results['distances'][0][i] if results['distances'] else 0
                }
                similar_items.append(item)
            
            return similar_items
        except Exception as e:
            print(f"[LocalChromaRepo] 检索失败: {e}")
            return []
    
    def delete_sample(self, sample_id: str):
        """删除样本
        
        Args:
            sample_id: 样本ID
            
        Returns:
            是否成功
        """
        if not HAS_CHROMA:
            return False
        
        collection = self.get_or_create_collection()
        if collection is None:
            return False
        
        try:
            collection.delete(ids=[sample_id])
            return True
        except Exception as e:
            print(f"[LocalChromaRepo] 删除样本失败: {e}")
            return False
    
    def delete_samples_batch(self, sample_ids: List[str]):
        """批量删除样本
        
        Args:
            sample_ids: 样本ID列表
            
        Returns:
            是否成功
        """
        if not HAS_CHROMA:
            return False
        
        collection = self.get_or_create_collection()
        if collection is None:
            return False
        
        try:
            collection.delete(ids=sample_ids)
            return True
        except Exception as e:
            print(f"[LocalChromaRepo] 批量删除样本失败: {e}")
            return False
    
    def get_count(self) -> int:
        """获取样本数量"""
        if not HAS_CHROMA:
            return 0
        
        collection = self.get_or_create_collection()
        if collection is None:
            return 0
        
        try:
            return collection.count()
        except Exception:
            return 0
    
    def clear_collection(self):
        """清空集合"""
        if not HAS_CHROMA:
            return
        
        try:
            self.client.delete_collection(name='local_samples')
            self.collection = None
        except Exception as e:
            print(f"[LocalChromaRepo] 清空集合失败: {e}")
    
    def sync_from_local_data(self, samples: List[Dict], 
                              embedding_service: Any, user_id: str = None,
                              data_signature: str = None, force: bool = False) -> int:
        """从local_data.json同步样本
        
        Args:
            samples: 样本列表
            embedding_service: Embedding服务
            
        Returns:
            同步数量
        """
        if not HAS_CHROMA or not embedding_service:
            return 0
        
        if not embedding_service.is_available():
            return 0

        current_state = self._load_sync_state()
        current_signature = data_signature or ''
        if not force and current_signature:
            if current_state.get('data_signature') == current_signature:
                expected_count = current_state.get('sample_count', 0)
                try:
                    if self.get_count() == expected_count and expected_count > 0:
                        return expected_count
                except Exception:
                    pass

        current_entries = current_state.get('sample_entries', {}) if isinstance(current_state, dict) else {}
        needs_full_rebuild = force or not isinstance(current_entries, dict) or not current_entries
        if not needs_full_rebuild:
            try:
                needs_full_rebuild = self.get_count() != len(current_entries)
            except Exception:
                needs_full_rebuild = True

        sample_ids = []
        parent_messages = []
        embeddings = []
        metadatas = []
        new_entries: Dict[str, Dict[str, Any]] = {}
        seen_ids = set()

        for sample in samples:
            parent_message = sample.get('parent_message', '')
            if not parent_message:
                continue

            sample_id = self._make_sample_key(sample)
            fingerprint = self._make_sample_fingerprint(sample)
            seen_ids.add(sample_id)

            previous_entry = current_entries.get(sample_id, {}) if isinstance(current_entries, dict) else {}
            if not needs_full_rebuild and previous_entry.get('fingerprint') == fingerprint:
                new_entries[sample_id] = previous_entry
                continue

            embedding = embedding_service.embed(parent_message)
            if embedding:
                sample_ids.append(sample_id)
                parent_messages.append(parent_message)
                embeddings.append(embedding)
                metadatas.append(self._sanitize_metadata({
                    'scene_tag': sample.get('scene_tag', ''),
                    'stage_tag': sample.get('stage_tag', ''),
                    'quality_score': sample.get('quality_score', 1.0),
                    'advisor_reply': sample.get('replies', [''])[0][:200] if sample.get('replies') else ''
                }))
                new_entries[sample_id] = {'fingerprint': fingerprint}
            elif previous_entry:
                new_entries[sample_id] = previous_entry

        try:
            collection = self.get_or_create_collection()
            if collection is None:
                return 0

            if needs_full_rebuild:
                self.clear_collection()
                if sample_ids:
                    self.add_samples_batch(sample_ids, parent_messages, embeddings, metadatas)
            else:
                deleted_ids = [sample_id for sample_id in current_entries.keys() if sample_id not in seen_ids]
                if deleted_ids:
                    self.delete_samples_batch(deleted_ids)
                if sample_ids:
                    self.add_samples_batch(sample_ids, parent_messages, embeddings, metadatas)

            try:
                vector_count = self.get_count()
            except Exception:
                vector_count = len(new_entries)

            if not new_entries and not needs_full_rebuild and current_entries:
                new_entries = current_entries

            self._save_sync_state({
                'data_signature': current_signature,
                'sample_count': len(new_entries),
                'vector_count': vector_count,
                'sample_entries': new_entries,
            })

            return vector_count
        except Exception as e:
            print(f"[LocalChromaRepo] 鍚屾鏍锋湰澶辫触: {e}")
            return 0
    
    def is_available(self) -> bool:
        """检查是否可用"""
        return HAS_CHROMA and self.client is not None
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'available': self.is_available(),
            'persist_dir': self.persist_dir,
            'sample_count': self.get_count(),
            'has_chroma': HAS_CHROMA
        }


def get_chroma_repo(persist_dir: str = None) -> LocalChromaRepo:
    """获取Chroma向量库实例
    
    Args:
        persist_dir: 持久化路径
        
    Returns:
        LocalChromaRepo实例
    """
    return LocalChromaRepo(persist_dir=persist_dir)
