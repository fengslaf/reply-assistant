# 本地检索系统 vs 大模型对比学习

本文档从知识点角度对比本地检索系统与大语言模型（LLM），帮助理解两种技术路线的差异与互补。

---

## 一、核心区别

| 维度 | 本地检索系统（本项目） | 大语言模型（LLM） |
|------|------------------------|-------------------|
| **工作原理** | 匹配+返回已有内容 | 理解+生成新内容 |
| **输出来源** | 从样本库中检索 | 从模型权重中生成 |
| **需要下载** | 无（或~100MB Embedding模型） | 有（1.5GB-14GB模型） |
| **需要网络** | 无（本地运行） | 有（或本地推理） |
| **响应速度** | ~10ms | 500ms-3000ms |
| **可控性** | 高（样本可控） | 低（生成不可控） |
| **知识更新** | 增删样本即可 | 需重新训练/RAG |

---

## 二、知识点对照表

### 1. 文本表示

| 知识点 | 本地检索系统 | 大语言模型 |
|--------|-------------|-----------|
| **词袋模型** | ✓ keyword_matcher.py（关键词计数） | - |
| **TF-IDF** | ✓ keyword_extractor.py（关键词权重） | - |
| **Word Embedding** | ✓ m3e-small（词→向量） | ✓ Transformer Embedding |
| **Contextual Embedding** | ✗（无上下文理解） | ✓ BERT/GPT（上下文感知） |
| **向量维度** | 512维（m3e-small） | 768-4096维 |

**代码示例**：
```python
# 本地检索：词袋+TF-IDF
keywords = extractor.extract("课程多少钱")  # ['课程', '多少钱']
tfidf_weight = extractor.compute_tfidf("课程", corpus)

# 大模型：上下文Embedding
embedding = model.encode("课程多少钱")  # [0.12, 0.34, ..., 0.56] (512维)
```

---

### 2. 相似度计算

| 知识点 | 本地检索系统 | 大语言模型 |
|--------|-------------|-----------|
| **Jaccard相似度** | ✓ similarity_calculator.py | - |
| **Cosine相似度** | ✓ Chroma向量检索 | ✓ Embedding对比 |
| **Dice系数** | ✓ similarity_calculator.py | - |
| **Overlap系数** | ✓ similarity_calculator.py | - |
| **欧氏距离** | ✓ Chroma（可选） | ✓ Embedding距离 |

**代码示例**：
```python
# 本地检索：关键词相似度
jaccard = calc.jaccard(["课程", "钱"], ["价格", "费用"])  # 0.25
cosine = calc.cosine(vec1, vec2)  # 0.85

# Chroma向量检索
results = chroma_repo.search(query_embedding, top_k=3)
# 返回: [{'id': 'sample_1', 'distance': 0.15, 'similarity': 0.85}]
```

---

### 3. 检索策略

| 知识点 | 本地检索系统 | 大语言模型 |
|--------|-------------|-----------|
| **精确匹配** | ✓ ExactRetriever | - |
| **关键词匹配** | ✓ KeywordRetriever | - |
| **向量检索** | ✓ VectorRetriever（Chroma） | ✓ RAG检索 |
| **混合检索** | ✓ HybridRetriever（权重融合） | ✓ RAG+关键词 |
| **BM25** | ✓ 可扩展 | ✓ RAG常用 |

**代码示例**：
```python
# 本地检索：混合检索
results = engine.search(SearchContext(
    query="课程多少钱",
    mode='hybrid',
    weights={'vector': 0.4, 'keyword': 0.3, 'scene': 0.15, 'quality': 0.15}
))
# 综合得分 = vector_score*0.4 + keyword_score*0.3 + ...

# RAG：向量检索+LLM生成
docs = retriever.get_relevant_documents(query)
response = llm.generate(prompt + docs)
```

---

### 4. 意图识别

| 知识点 | 本地检索系统 | 大语言模型 |
|--------|-------------|-----------|
| **关键词匹配** | ✓ IntentClassifier（规则） | ✓ Prompt分类 |
| **实体抽取** | ✓ EntityExtractor（正则） | ✓ NER模型 |
| **意图类型** | 14种预定义 | 无限（生成理解） |
| **置信度** | ✓ 关键词覆盖率 | ✓ 模型输出概率 |

**代码示例**：
```python
# 本地检索：规则意图识别
result = classifier.classify("课程多少钱")
# {'intent': 'price', 'confidence': 0.78, 'keywords': ['课程钱', '多少钱']}

# 大模型：Prompt意图识别
prompt = "判断用户意图：课程多少钱"
response = llm.generate(prompt)
# "用户意图是询问价格"
```

---

### 5. 实体抽取

| 知识点 | 本地检索系统 | 大语言模型 |
|--------|-------------|-----------|
| **正则表达式** | ✓ EntityExtractor | - |
| **NER模型** | ✗ | ✓ BERT-NER |
| **实体类型** | 10+预定义（money/phone等） | 无限 |
| **值解析** | ✓ 解析数值+单位 | ✓ 模型理解 |

**代码示例**：
```python
# 本地检索：正则实体抽取
entities = extractor.extract("课程费用2980元")
# {'money': ['2980元(值:2980.0)'], 'number': []}

# 大模型：NER抽取
entities = ner_model.predict("课程费用2980元")
# [{'text': '2980元', 'type': 'MONEY', 'start': 4, 'end': 9}]
```

---

### 6. 质量评估

| 知识点 | 本地检索系统 | 大语言模型 |
|--------|-------------|-----------|
| **长度评估** | ✓ QualityScorer | - |
| **关键词覆盖** | ✓ QualityScorer | - |
| **结构评估** | ✓ QualityScorer（列表/分段） | - |
| **信息密度** | ✓ QualityScorer | - |
| **礼貌用语** | ✓ QualityScorer | - |
| **行动引导** | ✓ QualityScorer | - |
| **等级评定** | ✓ A-F等级 | - |

**代码示例**：
```python
# 本地检索：规则质量评分
score = scorer.score("课程费用为2980元，包含30课时...")
# {'total_score': 0.44, 'grade': 'D', 'suggestions': ['建议补充关键词...']}

# 大模型：无内置质量评分（需额外Prompt）
```

---

### 7. 样本扩充

| 知识点 | 本地检索系统 | 大语言模型 |
|--------|-------------|-----------|
| **同义词替换** | ✓ SampleExpander | ✓ 生成变体 |
| **模板填充** | ✓ SampleExpander | ✓ 生成模板 |
| **语气变体** | ✓ SampleExpander | ✓ 生成语气 |
| **扩充倍数** | 2-3倍 | 无限 |

**代码示例**：
```python
# 本地检索：模板扩充
variants = expander.expand("课程费用2980元")
# ["学费为2980元", "培训费用2980元", "课程价格为2980元"]

# 大模型：生成扩充
prompt = "为'课程费用2980元'生成3个变体"
variants = llm.generate(prompt)
# ["学费是2980元", "课程收费2980", "培训费2980元"]
```

---

### 8. 向量数据库

| 知识点 | 本地检索系统 | 大语言模型 |
|--------|-------------|-----------|
| **Chroma** | ✓ ChromaRepo | ✓ RAG常用 |
| **FAISS** | ✓ 可扩展 | ✓ RAG常用 |
| **Milvus** | ✓ 可扩展 | ✓ 生产环境 |
| **持久化** | ✓ JSON/SQLite | ✓ 向量索引 |
| **索引类型** | HNSW/IVF | HNSW/IVF |

**代码示例**：
```python
# 本地检索：Chroma
repo = LocalChromaRepo(persist_dir="./data/chroma")
repo.add_samples([{"id": "1", "text": "课程费用2980元", "embedding": vec}])
results = repo.search(query_embedding, top_k=3)

# RAG：Chroma+LLM
docs = chroma.get_relevant_documents(query)
response = llm.generate(prompt + docs)
```

---

### 9. Embedding模型

| 知识点 | 本地检索系统 | 大语言模型 |
|--------|-------------|-----------|
| **模型类型** | m3e-small（编码器） | Transformer（编码器） |
| **模型大小** | ~100MB | 1.5GB-14GB |
| **输出维度** | 512维 | 768-4096维 |
| **训练数据** | 中文语料 | 多语言语料 |
| **推理速度** | ~10ms | ~50ms |

**代码示例**：
```python
# 本地检索：m3e-small
service = LocalEmbeddingService(model_name="m3e-small")
embedding = service.embed("课程多少钱")  # [0.12, 0.34, ...]

# 大模型：BERT Embedding
embedding = bert_model.encode("课程多少钱")  # [0.23, 0.45, ...]
```

---

## 三、技术路线对比

### 本地检索系统（本项目）

```
用户问题 → 意图识别 → 实体抽取 → 检索样本库 → 返回匹配内容
           (规则)      (正则)      (向量+关键词)
           ↓           ↓           ↓
         置信度      实体值      综合得分
```

**优点**：
- 无需下载大模型
- 响应速度快（~10ms）
- 结果可控（样本可控）
- 知识更新简单（增删样本）

**缺点**：
- 无语义理解能力
- 无法生成新内容
- 依赖样本质量

---

### 大语言模型（LLM）

```
用户问题 → Prompt → LLM推理 → 生成新内容
           ↓        ↓         ↓
         上下文    权重计算   输出概率
```

**优点**：
- 深度语义理解
- 可生成新内容
- 无限意图理解

**缺点**：
- 需下载大模型（1.5GB+）
- 响应速度慢（500ms+）
- 生成不可控
- 知识更新难（需重新训练）

---

### RAG（检索增强生成）

```
用户问题 → 检索文档 → Prompt+文档 → LLM推理 → 生成回复
           ↓          ↓            ↓         ↓
         向量检索    上下文构建    权重计算   输出概率
```

**优点**：
- 结合检索+生成优点
- 知识可更新（更新文档库）
- 生成有依据（基于检索文档）

**缺点**：
- 需检索系统+LLM
- 响应速度更慢（检索+推理）
- 复杂度高

---

## 四、本项目知识点清单

### 已实现知识点

| 模块 | 知识点 | 文件 |
|------|--------|------|
| **关键词提取** | jieba分词、正则提取、TF-IDF | keyword_extractor.py |
| **相似度计算** | Jaccard、Cosine、Dice、Overlap | similarity_calculator.py |
| **聚类算法** | greedy聚类、层次聚类、关键词分组 | cluster_engine.py |
| **意图识别** | 关键词匹配、置信度计算、子意图识别 | intent_classifier.py |
| **实体抽取** | 正则表达式、值解析、单位解析 | entity_extractor.py |
| **质量评分** | 6维度评估、A-F等级、改进建议 | quality_scorer.py |
| **样本扩充** | 同义词替换、模板填充、语气变体 | sample_expander.py |
| **向量检索** | Chroma、HNSW索引、相似度阈值 | chroma_repo.py |
| **Embedding** | m3e-small、sentence-transformers | embedding_service.py |
| **混合检索** | 权重融合、来源标注、置信度计算 | search_engine.py |

### 可扩展知识点

| 知识点 | 说明 | 扩展方式 |
|--------|------|----------|
| **BM25** | 更好的关键词检索 | 替换KeywordRetriever |
| **FAISS** | 更快的向量检索 | 替换ChromaRepo |
| **BERT-NER** | 更强的实体抽取 | 替换EntityExtractor |
| **BERT分类** | 更强的意图识别 | 替换IntentClassifier |
| **LLM生成** | 生成新内容 | 集成remote_ai |
| **RAG** | 检索+生成 | 集成LLM+检索 |

---

## 五、学习路径建议

### 初学者路径

1. **关键词检索** → keyword_matcher.py（词袋模型）
2. **意图识别** → intent_classifier.py（规则引擎）
3. **实体抽取** → entity_extractor.py（正则表达式）
4. **相似度计算** → similarity_calculator.py（Jaccard/Cosine）
5. **质量评分** → quality_scorer.py（多维度评估）

### 进阶路径

1. **向量检索** → chroma_repo.py（Chroma向量库）
2. **Embedding** → embedding_service.py（m3e-small）
3. **混合检索** → search_engine.py（权重融合）
4. **聚类算法** → cluster_engine.py（层次聚类）

### 高级路径

1. **RAG实现** → 检索+LLM生成
2. **多模态检索** → 文本+图片+音频
3. **实时索引** → 流式更新向量库
4. **分布式检索** → 多机向量检索

---

## 六、与大模型的知识点交集

| 交集知识点 | 本地检索系统 | 大语言模型 |
|------------|-------------|-----------|
| **向量表示** | Embedding（m3e-small） | Embedding（BERT/GPT） |
| **相似度计算** | Cosine相似度 | Cosine相似度 |
| **向量数据库** | Chroma | Chroma/FAISS |
| **意图理解** | 规则匹配 | Prompt理解 |
| **实体抽取** | 正则表达式 | NER模型 |

---

## 七、总结

| 维度 | 本地检索系统 | 大语言模型 |
|------|-------------|-----------|
| **定位** | 检索引擎（匹配+返回） | 推理引擎（理解+生成） |
| **知识来源** | 样本库（外部知识） | 模型权重（内部知识） |
| **适用场景** | FAQ、客服、知识库问答 | 创作、对话、复杂推理 |
| **技术难度** | 中等（规则+向量） | 高（深度学习） |
| **部署成本** | 低（无大模型） | 高（需GPU/大模型） |

**最佳实践**：
- 简单问答 → 本地检索系统（本项目）
- 复杂生成 → 大语言模型（LLM）
- 高质量问答 → RAG（检索+生成）

---

版本: v2.03
更新时间: 2026-05-23