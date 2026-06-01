# Changelog

## V0.2.04

### V2.03 ← V2.04 合并记录

#### 新增模块
- `local_intelligence/template_generator.py`：模板拼接生成器
- `local_intelligence/multi_sample_fusion.py`：多样本融合器
- `local_intelligence/entity_substitution.py`：实体替换生成器
- `local_intelligence/context_weighter.py`：上下文加权器
- `local_intelligence/rule_inference_chain.py`：规则推理链
- `local_intelligence/intelligence_manager_v204.py`：V2.04 智能增强管理器
- `local_search/search_engine_v204.py`：带智能生成增强的本地检索器
- `personal_data.py`：个人数据系统数据解析、搜索与年级换算

#### 核心升级
1. V2.04 智能生成增强已合入，但默认关闭；在设置中开启后固定使用 `hybrid` 模式。
2. 首页升级为“快捷助手全家桶”产品面板，新增与回复助手同级的“客户数据系统（个人数据系统）”入口，并支持免费版 / 本地永久版 / 月卡 / 年卡状态展示。
3. 回复助手从首页启动时，直接进入主界面，不再经过登录页 / 本地启动页。
4. 个人数据系统使用独立目录 `data/personal_data/`，与回复助手样本数据完全隔离。
5. 年级换算规则升级为：
   - `六年级 -> 初一`
   - `初三 -> 高一`
   - `高三 -> 高三+1 / 高三+2 / ...`

#### 生效方式
- 回复助手本地模式：开启后，V2.04 会参与候选生成与排序。
- 个人数据系统：开启后，V2.04 会参与顶部智能摘要与结果重排。
- 关闭开关时：两套本地模块继续走当前稳定链路，不改变原有结果。

## V0.2.03

### V2.02 ← V2.03 合并记录

#### 新增模块
- `local_search/embedding_service.py`: 本地向量编码服务，默认 `m3e-small`
- `local_search/chroma_repo.py`: 本地 Chroma 向量库封装
- `local_search/tests/test_v203.py`: V2.03 回归脚本
- `docs/KNOWLEDGE_LEARNING.md`: 知识点学习说明

#### 核心升级
1. 意图识别前置过滤：先缩小样本池，再进入检索
2. 语义向量检索：支持“课程多少钱”匹配“价格是多少”这类语义相近问题
3. 自动同步：`local_data.json` 自动索引到 Chroma 向量库

#### 依赖变更
- 新增：`sentence-transformers`（可选，向量检索）
- 新增：`chromadb`（可选，向量存储）
- 两者未安装时自动回退到现有检索流程

## V0.2.02

### V2.01 ← V2.02 合并记录

#### 新增模块
- `local_intelligence/`: 智能增强模块（意图识别、实体抽取、质量评分、样本扩充、动态提示词）

#### 核心功能
1. **智能增强**
   - 意图识别：先判断用户问题属于哪一类
   - 实体抽取：自动提取金额、时间、课程名、电话等关键信息
   - 质量评分：为候选回复做质量评估，帮助挑选更合适的样本
   - 样本扩充：基于样本内容生成更多可参考的表达方式
   - 动态提示词：根据问题类型自动组织更贴合场景的 prompt

#### 接入方式
- 现有界面保持不变
- 生成链路会先经过智能增强层，再进入原有检索/AI 生成流程
- 若增强模块不可用，自动回退到原有流程，不影响主功能

#### 知识点覆盖
| 模块 | 知识点 |
|------|--------|
| `local_intelligence` | 意图识别、实体抽取、质量评分、样本扩充、提示词构建 |

---

## V0.2.01

### V2.00 ← V2.01 合并记录

#### 新增模块
- `local_context/`: 上下文管理模块（会话历史、窗口策略、历史检索）
- `local_cluster/`: 关键词聚类模块（关键词提取、相似度计算、聚类分析）

#### 核心功能
1. **上下文管理**
   - 会话生命周期管理（创建 / 结束 / 持久化）
   - 多种窗口策略（固定大小 / 时间 / Token 限制 / 智能裁剪）
   - 历史检索（按关键词 / 时间 / 角色筛选）
   - 对话对提取（Q&A 配对）
2. **关键词聚类**
   - 关键词提取（`jieba` 分词 / 正则匹配）
   - 多种相似度计算（Jaccard / Cosine / Dice / Overlap）
   - 三种聚类方法（greedy / 层次 / 关键词分组）
   - 查重分析、推荐分类、相似样本检索

#### 依赖变更
- 新增：`jieba`（中文分词，安装命令：`pip install jieba`）
- 无强制依赖：`jieba` 未安装时自动降级为正则匹配

#### 知识点覆盖
| 模块 | 知识点 |
|------|--------|
| `local_context` | 数据结构、状态管理、持久化、窗口策略 |
| `local_cluster` | 中文分词、TF-IDF、相似度算法、聚类算法 |

#### 使用方式
```python
# 上下文管理
from local_context import LocalContextManager, WindowStrategy

ctx = LocalContextManager(max_turns=10)
ctx.start_session()
ctx.add_user_message("问题")
ctx.add_assistant_reply("回答")
prompt_context = ctx.build_prompt_context()

# 关键词聚类
from local_cluster import LocalClusterManager

cluster = LocalClusterManager(similarity_threshold=0.3)
report = cluster.cluster_samples(["问题1", "问题2"])
summary = cluster.get_cluster_summary()
similar = cluster.find_similar_samples("问题", ["问题1", "问题2"], top_k=5)
categories = cluster.suggest_categories(["问题1", "问题2"])
```

---

## V0.2.0

### V1.00 ← V2.00 合并记录

#### 新增模块
- `local_search/`: 本地检索模块（向量 + 关键词 + 精确混合检索）
- `remote_ai/`: 远程 AI 推理模块（多提供商支持）
- `preview_adapter.py`: V1.00 兼容适配器

#### 核心功能
1. 检索能力升级：向量检索（m3e-small）+ 关键词匹配 + 权重融合
2. AI 推理支持：用户自带 key（DeepSeek / 智谱 / 文心 / OpenAI）
3. 来源标注：结果明确标注来源类型（`local_vector` / `local_keyword` / `ai_remote`）

#### 依赖变更
- 新增：`sentence-transformers`（可选，向量检索）
- 新增：`chromadb`（可选，向量存储）

#### 使用方式
```python
from local_search import LocalSearchEngine, SearchContext

engine = LocalSearchEngine()
result = engine.search(SearchContext(query="问题", mode="hybrid"))
```
