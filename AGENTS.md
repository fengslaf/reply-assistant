# 快捷回复助手：项目导航

本文档帮助后续开发者快速定位功能模块，用于功能增加、Bug修复、性能优化。

> 当前桌面版主链路以 `start_gui.py`、`preview_mode.py`、`preview_adapter.py`、`local_search/`、`local_intelligence/`、`personal_data.py` 为准。下面保留的是早期服务端 / PC 客户端约定，仅作历史参考。

## 快速定位表

| 需求 | 定位文件 | 说明 |
|------|----------|------|
| 新增API接口 | `server/app/api/*.py` | 每个接口独立文件，按功能命名 |
| 修改枚举定义 | `shared/constants/enums.py` | 所有枚举集中管理 |
| 修改数据结构 | `shared/schemas/sample.py` | Pydantic定义 |
| 修改配置项 | `server/app/config.py` | 环境变量映射 |
| 修改合并转发解析 | `scripts/parse_forward.py` | 解析逻辑独立模块 |
| 修改数据库表 | `scripts/init_db.py` | SQLite定义 |
| 修改Prompt模板 | `server/app/prompts/*.py` | 大模型Prompt独立目录 |
| 修改存储层 | `server/app/storage/*.py` | 数据库操作层 |
| 修改LLM调用 | `server/app/llm/*.py` | 大模型调用层 ★ |
| 修改业务逻辑 | `server/app/services/*.py` | Service层核心逻辑 |
| 新增模型提供商 | `server/app/llm/openai_client.py` | PROVIDER_CONFIGS |

## 目录结构详解

```
助手_项目/
│
├── server/                          # 后端服务
│   ├── app/
│   │   ├── main.py                  # [入口] Flask启动 + 路由注册
│   │   ├── config.py                # [配置] 环境变量映射
│   │   │
│   │   ├── api/                     # [API层] 每个接口独立文件
│   │   │   ├── user.py              # 用户身份: /api/v1/user/*
│   │   │   ├── message.py           # 消息接收: /api/v1/message/*
│   │   │   ├── sample.py            # 样本管理: /api/v1/samples/*
│   │   │   ├── search.py            # 检索: /api/v1/search/*
│   │   │   ├── generate.py          # 生成: /api/v1/generate/*
│   │   │   ├── stats.py             # 统计: /api/v1/stats/*
│   │   │   ├── enums.py             # 枚举: /api/v1/enums/*
│   │   │   └── admin.py             # 管理: /api/v1/admin/*
│   │   │
│   │   ├── services/                # [Service层] 核心业务逻辑
│   │   │   ├── sample_service.py    # 样本CRUD逻辑
│   │   │   ├── search_service.py    # 检索逻辑
│   │   │   ├── generate_service.py  # 生成逻辑
│   │   │   └── forward_service.py   # 合并转发处理
│   │   │
│   │   ├── storage/                 # [Storage层] 数据库操作
│   │   │   ├── sqlite_repo.py       # SQLite操作 ★ 已验证
│   │   │   ├── chroma_repo.py       # Chroma向量库操作
│   │   │   └── embedding_service.py # Embedding生成
│   │   │
│   │   ├── llm/                     # [LLM层] 大模型调用 ★ 新增
│   │   │   ├── base.py              # 抽象基类 + LLMConfig/LLMResponse
│   │   │   ├── openai_client.py     # OpenAI兼容客户端（多模型）
│   │   │   └── llm_service.py       # 业务服务层
│   │   │
│   │   ├── prompts/                 # [Prompt层] 模板管理
│   │   │   └── reply_prompt.py      # 候选回复生成Prompt
│   │   │
│   │   └── models/                  # [Model层] 数据模型（待实现）
│   │
│   └── tests/                       # [测试] 单元测试
│
├── pc-client/                       # PC客户端（待开发）
│   ├── app/
│   │   ├── main.py                  # 客户端入口
│   │   ├── hotkey.py                # 全局快捷键
│   │   ├── clipboard.py             # 剪贴板操作
│   │   ├── window.py                # 悬浮窗口
│   │   └── api_client.py            # 后端API调用
│   └── tests/
│
├── shared/                          # [共享模块] 前后端共用
│   ├── constants/
│   │   └── enums.py                 # 所有枚举定义 ★
│   │
│   └── schemas/
│       └── sample.py                # 所有数据结构 ★
│
├── scripts/                         # [工具脚本]
│   ├── init_db.py                   # 数据库初始化 ★
│   ├── parse_forward.py             # 合并转发解析 ★
│   ├── test_storage.py              # Storage验证脚本
│   └── test_llm.py                  # LLM验证脚本 ★
│
├── docs/                            # 设计文档
│
├── .env.example                     # 环境变量模板
├── README.md                        # 项目说明
├── AGENTS.md                        # 本导航文档 ★
└── DEPLOY.md                        # 部署指南
```

## 模块职责说明

### API层 (`server/app/api/`)
- **职责**: 接收请求、参数验证、调用Service、返回响应
- **原则**: 每个文件对应一类接口，不包含业务逻辑
- **新增接口**: 创建新文件 → 在main.py注册

### Service层 (`server/app/services/`)
- **职责**: 核心业务逻辑，调用Storage和外部API
- **原则**: 不直接操作数据库，通过Storage层
- **新增逻辑**: 创建新service → 在API层调用

### Storage层 (`server/app/storage/`)
- **职责**: 数据库操作、向量库操作、Embedding
- **原则**: 封装所有存储操作，返回数据对象
- **新增存储**: 创建新repo文件 → 在Service层调用

### LLM层 (`server/app/llm/`) ★ 新增
- **职责**: 大模型调用抽象，支持多提供商
- **原则**: 统一接口，易于切换模型
- **支持模型**: DeepSeek, 智谱GLM, 通义千问, 百川, Moonshot, OpenAI, Ollama
- **新增提供商**: 在openai_client.py的PROVIDER_CONFIGS添加

### Prompts层 (`server/app/prompts/`)
- **职责**: 大模型Prompt模板管理
- **原则**: 所有Prompt集中管理，便于调优
- **新增Prompt**: 创建新prompt文件 → 在Service层调用

### Shared层 (`shared/`)
- **职责**: 前后端共用的常量和数据结构
- **原则**: 任何模块都可导入，保持一致性
- **修改枚举**: 只修改 `enums.py`，API自动更新

## 典型任务定位

### 任务1: 新增"批量删除样本"功能
1. `shared/schemas/sample.py` - 新增请求结构
2. `server/app/api/sample.py` - 新增路由
3. `server/app/services/sample_service.py` - 新增批量删除逻辑
4. `server/app/storage/sqlite_repo.py` - 新增批量删除SQL

### 任务2: 修改"问价格"场景标签为"询价"
1. `shared/constants/enums.py` - 修改枚举值
2. `09_枚举规范.md` - 同步更新文档
3. 所有模块自动生效（无需修改其他代码）

### 任务3: 优化候选回复生成速度
1. `server/app/services/generate_service.py` - 优化逻辑
2. `server/app/prompts/reply_prompt.py` - 优化Prompt
3. `server/app/storage/chroma_repo.py` - 优化检索效率

### 任务4: Bug: 合并转发时间格式错误
1. `scripts/parse_forward.py` - 定位到时间解析正则
2. 修改正则表达式
3. 运行测试验证

### 任务5: 新增支持"讯飞星火"模型
1. `server/app/llm/openai_client.py` - 在PROVIDER_CONFIGS添加讯飞配置
2. `server/app/config.py` - 无需修改，配置兼容
3. 测试: `python scripts/test_llm.py --provider xunfei --api-key xxx`

---

## 开发流程

### 新增功能
```
1. 在 shared/schemas/ 定义数据结构
2. 在 server/app/storage/ 实现存储（如需要）
3. 在 server/app/services/ 实现逻辑
4. 在 server/app/api/ 创建路由文件
5. 在 main.py 注册路由
6. 编写测试
```

### 修复Bug
```
1. 根据错误信息定位模块
2. 在对应模块修复
3. 不跨模块修改（保持隔离）
```

### 性能优化
```
1. 定位到 Service 或 Storage 层
2. 不修改 API 层（保持接口稳定）
```

---

## 设计文档对应

| 设计文档 | 对应代码 |
|----------|----------|
| 06_最终设计文档.md | 目录结构 + 模块职责 |
| 07_最终开发计划.md | 开发流程 + 任务拆分 |
| 08_API接口契约.md | `server/app/api/*.py` |
| 09_枚举规范.md | `shared/constants/enums.py` |

---

## LLM模块使用说明

### 配置环境变量
```env
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-your-key
LLM_API_BASE=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

### 支持的提供商
| 提供商 | api_base | 默认模型 |
|--------|----------|----------|
| deepseek | https://api.deepseek.com | deepseek-chat |
| zhipu | https://open.bigmodel.cn/api/paas/v4 | glm-4-flash |
| qwen | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-plus |
| openai | https://api.openai.com/v1 | gpt-4o-mini |
| ollama | http://localhost:11434/v1 | llama3 |

### 代码调用示例
```python
from server.app.llm.llm_service import LLMService

# 使用系统默认配置
response = LLMService.simple_chat("你好")

# 用户自带key
client = LLMService.create_user_client("zhipu", user_api_key)
response = client.simple_chat("你好")
```

---

## 后续交接清单

1. 阅读 `README.md` 了解项目定位
2. 阅读 `AGENTS.md`（本文件）了解模块定位
3. 阅读 `08_API接口契约.md` 了解接口规范
4. 阅读 `09_枚举规范.md` 了解枚举定义
5. 运行 `python scripts/init_db.py` 初始化数据库
6. 运行 `python server/app/main.py` 启动服务
7. 访问 `/api/v1/enums/all` 验证枚举接口
8. 运行 `python scripts/test_storage.py` 验证Storage层
9. 运行 `python scripts/test_llm.py --test list` 查看支持的模型

---

版本: v0.2.0
更新时间: 2026-05-19
