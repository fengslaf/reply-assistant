# CONTRIBUTING - 协作开发指南

> 当前仓库的主链路已经转为桌面端双系统：`回复助手` 和 `客户数据系统`。下面保留的老目录树和示例命令是早期项目规划，仅作历史参考。

## 项目结构

```
助手_项目/
├── server/                  # 后端服务
│   ├── app/
│   │   ├── api/             # API路由层
│   │   ├── services/        # 业务逻辑层
│   │   ├── storage/         # 数据库操作层
│   │   ├── llm/             # 大模型调用层
│   │   ├── prompts/         # Prompt模板
│   │   └── models/          # ORM层（可选）
│   └── tests/               # 测试用例
├── pc-client/               # PC客户端
│   ├── app/                 # 客户端代码
│   └── tests/               # 测试用例
├── shared/                  # 共享模块
│   ├── constants/           # 枚举常量
│   └── schemas/             # 数据结构
├── scripts/                 # 工具脚本
├── docs/                    # 文档
└── data/                    # 数据存储
```

## 开发流程

### 1. 新增API接口

```bash
# 1. 创建API文件
server/app/api/new_feature.py

# 2. 定义Blueprint
new_feature_bp = Blueprint('new_feature', __name__)

# 3. 在main.py注册
from app.api.new_feature import new_feature_bp
app.register_blueprint(new_feature_bp)

# 4. 编写测试
server/tests/test_new_feature.py
```

### 2. 新增Service

```bash
# 1. 创建Service文件
server/app/services/new_service.py

# 2. 在__init__.py导出
from .new_service import NewService

# 3. 在API层调用
from server.app.services import NewService
```

### 3. 新增LLM提供商

```bash
# 1. 在openai_client.py的PROVIDER_CONFIGS添加
PROVIDER_CONFIGS["new_provider"] = {
    "api_base": "https://api.new-provider.com/v1",
    "models": ["model-1", "model-2"],
    "default_model": "model-1"
}

# 2. 无需修改其他代码，自动兼容
```

### 4. 修改枚举

```bash
# 1. 只修改 shared/constants/enums.py
# 2. 所有模块自动生效（无需修改其他代码）
# 3. 同步更新 09_枚举规范.md
```

## 代码规范

### 必须遵守

1. **所有样本必须带user_id**
   - 不允许"先不做隔离，后面再补"

2. **枚举集中维护**
   - 不允许前后端各写一套

3. **解析结果不入正式库**
   - 合并转发解析结果必须进审核流

4. **Prompt集中管理**
   - 不允许客户端自己拼Prompt

5. **接口显式传user_id**
   - 不允许隐式默认值

### 禁止行为

- `as any`, `@ts-ignore` 类型抑制
- 空catch块 `catch(e) {}`
- 删除失败测试来"通过"
- 直接操作数据库（必须通过Storage层）

## 测试要求

### 运行测试

```bash
# 全部测试
pytest server/tests/ pc-client/tests/ -v

# 单模块测试
pytest server/tests/test_services.py -v
pytest server/tests/test_api.py -v

# 验证脚本
python scripts/test_storage.py
python scripts/test_llm.py --test list
```

### 测试覆盖

- 新增Service → 必须有test_services.py覆盖
- 新增API → 必须有test_api.py覆盖
- 新增模块 → 必须有独立测试文件

## 环境配置

### 本地开发

```bash
# 1. 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 2. 安装依赖
pip install -r server/requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑.env填入配置

# 4. 初始化数据库
python scripts/init_db.py

# 5. 启动服务
python server/app/main.py
```

### 必填配置

```env
DATABASE_PATH=./data/samples.db
VECTOR_STORE_PATH=./data/chroma
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-xxx
```

### 可选配置

```env
WECHAT_APPID=wx...        # 公众号配置
WECHAT_TOKEN=xxx
```

## 文档更新

当修改代码时，同步更新：

| 修改内容 | 需更新文档 |
|----------|------------|
| 新增/修改API | 08_API接口契约.md |
| 新增/修改枚举 | 09_枚举规范.md |
| 新增模块 | AGENTS.md |
| 完成任务包 | 当前节点.md |
| 版本发布 | CHANGELOG.md |

## Git提交规范

### 提交格式

```
[类型] 简短描述

# 类型：
# feat    - 新功能
# fix     - 修复
# docs    - 文档
# test    - 测试
# refactor- 重构

# 示例：
feat: 新增公众号回调服务框架
fix: 解决numpy兼容性问题
docs: 更新AGENTS.md
```

### 提交时机

- 每个功能模块完成后
- 测试通过后
- 文档更新后

## 常见问题

### Q: numpy导入失败？

检查CPU是否支持AVX2。不支持时：
- Python 3.12 + numpy 1.26.4
- torch 2.2.0+cpu

### Q: Embedding模型下载失败？

配置镜像：
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### Q: 公众号服务不可用？

检查配置：
```bash
curl http://localhost:5000/api/v1/wechat/status
```

---

## 联系方式

- 设计文档目录：`E:\fsl-works\fsl\助手_专题`
- 问题反馈：提交Issue或联系项目负责人
