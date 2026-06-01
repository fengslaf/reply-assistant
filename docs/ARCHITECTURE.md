# 架构设计文档

## V0.2.04 当前架构

当前桌面版已经从“单一回复流程”升级为“产品首页 + 双本地系统”的结构：

- 产品首页 `快捷助手全家桶` 作为总入口，统一展示状态、套餐和模块入口。
- `回复助手` 从首页直接进入主界面，不再经过登录页 / 本地启动页。
- `客户数据系统（个人数据系统）` 独立存储、独立检索、独立表格展示。
- 公开版仅保留本地免费能力，不依赖服务器。
- `V2.04` 是回复助手里的可选智能生成增强开关，默认关闭。

```
快捷助手全家桶（首页）
├── 回复助手
│   ├── 直接进入主界面
│   ├── 本地检索 / 候选回复
│   └── V2.04 智能生成增强（可开关）
├── 客户数据系统
│   ├── 导入 / 检索 / 表格查看 / 编辑
│   └── 独立数据目录 `data/personal_data/`
└── 套餐状态
    └── 公开版：本地免费能力
```

## 早期服务端架构（历史）

> 下面内容保留的是早期服务端方案背景；当前桌面端入口和本地双系统请以本节为准。

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           快捷回复助手                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────────────┐
│  公众号/服务号    │     │   PC客户端        │     │      管理后台            │
│                  │     │                  │     │    (审核/统计)           │
│  - 消息接收      │     │  - 快捷键唤起     │     │                          │
│  - 合并转发      │     │  - 剪贴板读取     │     │                          │
│  - #学习指令     │     │  - 候选展示       │     │                          │
│                  │     │  - 一键复制       │     │                          │
│                  │     │  - 收藏样本       │     │                          │
└───────┬──────────┘     └───────┬──────────┘     └───────────┬──────────────┘
        │                        │                            │
        │ HTTPS                  │ HTTP                       │ HTTP
        │                        │                            │
        ▼                        ▼                            ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Flask 后端服务                                     │
│                      http://localhost:5000                                  │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        │ Blueprint注册
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API层                                           │
│                        server/app/api/*.py                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│  /api/v1/user         │ 用户身份映射                                        │
│  /api/v1/message      │ 消息接收、合并转发解析                              │
│  /api/v1/samples      │ 样本CRUD、激活、归档                                │
│  /api/v1/search       │ 向量检索                                            │
│  /api/v1/generate     │ 候选回复生成                                        │
│  /api/v1/wechat       │ 公众号回调                                          │
│  /api/v1/enums        │ 枚举查询                                            │
│  /api/v1/stats        │ 统计数据                                            │
│  /api/v1/admin        │ 管理接口                                            │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        │ 调用Service
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Service层                                        │
│                       server/app/services/*.py                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  SampleService        │ 样本业务逻辑                                         │
│  SearchService        │ 检索业务逻辑                                         │
│  GenerateService      │ 生成业务逻辑                                         │
│  ForwardService       │ 合并转发处理                                         │
│  WeChatCallbackService│ 公众号回调处理                                       │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        │ 调用Storage/LLM/Prompt
        │
        ▼
┌───────────────┬───────────────┬───────────────┬───────────────┐
│   Storage层   │    LLM层      │  Prompts层    │   Models层    │
│               │               │               │               │
│ storage/*.py  │   llm/*.py    │ prompts/*.py  │ models/*.py   │
├───────────────┼───────────────┼───────────────┼───────────────┤
│ SQLiteRepo    │ BaseLLMClient │ reply_prompt  │ SampleModel   │
│ ChromaRepo    │ OpenAIClient  │               │ UserModel     │
│ EmbeddingSvc  │ LLMService    │               │               │
└───────┬───────┴───────────────┴───────────────┴───────────────┘
        │
        │ 数据存储
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                             数据存储层                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  SQLite          │ Chroma          │ 本地文件系统                            │
│  ./data/samples.db│ ./data/chroma  │ ./logs/app.log                         │
│                  │                 │ ./data/*.db                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 层级职责

### API层
- 接收HTTP请求
- 参数验证
- 调用Service
- 返回JSON响应

### Service层
- 核心业务逻辑
- 调用多个Storage
- 调用LLM/Prompt
- 事务管理

### Storage层
- 数据库操作封装
- 向量库操作封装
- Embedding生成

### LLM层
- 多模型兼容
- 统一调用接口
- 失败重试

### Prompts层
- Prompt模板管理
- 风格分类
- 响应解析

## 数据流向

### 入库流程

```
公众号消息 → WeChatCallbackService → ForwardService.parse()
                                                    ↓
                                            ForwardCandidate列表
                                                    ↓
                                            用户确认角色
                                                    ↓
                                            ForwardService.confirm_roles()
                                                    ↓
                                            SampleService.create()
                                                    ↓
                                            SQLiteRepo.create_sample()
                                                    ↓
                                            用户审核 → SampleService.activate()
                                                    ↓
                                            EmbeddingService.embed()
                                                    ↓
                                            ChromaRepo.add_sample()
```

### 查询流程

```
PC客户端 → APIClient.generate_reply()
                        ↓
                GenerateService.generate_reply()
                        ↓
                SearchService.search_similar()
                        ↓
                EmbeddingService.embed()
                        ↓
                ChromaRepo.search_similar()
                        ↓
                SQLiteRepo.get_sample()
                        ↓
                LLMService.simple_chat()
                        ↓
                reply_prompt模板
                        ↓
                5条候选回复
```

## 扩展点

### 新增LLM提供商
```
llm/openai_client.py → PROVIDER_CONFIGS["new_provider"] = {...}
无需修改其他代码
```

### 新增Service
```
services/new_service.py → class NewService
api/__init__.py → from .new_service import new_service_bp
```

### 新增Storage
```
storage/new_repo.py → class NewRepo(BaseRepo)
services/*.py → from storage import NewRepo
```

### 新增API
```
api/new_api.py → new_api_bp = Blueprint(...)
main.py → app.register_blueprint(new_api_bp)
```

---

版本: v0.2.0
更新时间: 2026-05-19
