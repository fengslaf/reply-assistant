# API 使用指南

本文档保留的是早期后端接口说明，用于历史参考，不影响公开版本地功能。

## 基础信息

- **服务地址**: `http://localhost:5000`
- **API 版本**: `/api/v1`
- **认证方式**: Header `X-User-ID`

---

## 快速测试

```bash
# 健康检查
curl http://localhost:5000/api/v1/health

# 获取枚举
curl http://localhost:5000/api/v1/enums/all

# 检查服务可用性
curl http://localhost:5000/api/v1/search/available
curl http://localhost:5000/api/v1/generate/available
```

---

## 样本管理 API

### 创建样本

```bash
POST /api/v1/samples
Header: X-User-ID: advisor_001

{
  "parent_message": "价格有点高，我们再考虑一下",
  "advisor_reply": "理解您的顾虑，我这边先不催您定...",
  "scene_tag": "问价格",
  "stage_tag": "试听后",
  "quality_score": 3,
  "source_type": "wechat_forward",
  "auto_activate": false
}
```

**响应**:
```json
{
  "sample_id": "uuid-xxx",
  "status": "draft",
  "message": "样本创建成功"
}
```

### 激活样本

```bash
POST /api/v1/samples/{sample_id}/activate
```

**响应**:
```json
{
  "sample_id": "uuid-xxx",
  "status": "active",
  "vector_synced": true,
  "message": "样本已激活，可参与检索"
}
```

### 获取待审核样本

```bash
GET /api/v1/samples/drafts?page=1&limit=20
Header: X-User-ID: advisor_001
```

### 获取激活样本

```bash
GET /api/v1/samples/active?page=1&limit=20
Header: X-User-ID: advisor_001
```

### 获取用户统计

```bash
GET /api/v1/samples/stats
Header: X-User-ID: advisor_001
```

---

## 检索 API

### 检索相似样本

```bash
POST /api/v1/search
Header: X-User-ID: advisor_001

{
  "query": "价格有点高，我们再考虑一下",
  "top_k": 5,
  "scene_filter": "问价格",
  "stage_filter": "试听后"
}
```

**响应**:
```json
{
  "query": "...",
  "total": 3,
  "results": [
    {
      "sample_id": "...",
      "parent_message": "...",
      "advisor_reply": "...",
      "scene_tag": "问价格",
      "similarity": 0.85
    }
  ]
}
```

---

## 生成 API

### 生成候选回复

```bash
POST /api/v1/generate/reply
Header: X-User-ID: advisor_001

{
  "query": "价格有点高，我们再考虑一下",
  "scene_hint": "问价格",
  "stage_hint": "试听后"
}
```

**响应**:
```json
{
  "query": "...",
  "candidates": [
    {
      "reply_id": "...",
      "content": "理解您的顾虑...",
      "style_tag": "温和共情型",
      "confidence": 0.7
    },
    {
      "reply_id": "...",
      "content": "根据试听课的情况...",
      "style_tag": "专业自信型",
      "confidence": 0.7
    },
    {
      "reply_id": "...",
      "content": "我建议您可以...",
      "style_tag": "行动推动型",
      "confidence": 0.7
    }
  ],
  "model_used": "deepseek-chat",
  "latency_ms": 1500
}
```

---

## 枚举 API

### 获取所有枚举

```bash
GET /api/v1/enums/all
```

**响应**:
```json
{
  "scene_tags": ["问价格", "问课程", "问师资", ...],
  "stage_tags": ["初次接触", "试听前", "试听后", ...],
  "sample_statuses": ["draft", "active", "archived"],
  "source_types": ["wechat_forward", "manual_input", "pc_favorite"],
  "quality_scores": [1, 2, 3]
}
```

---

## 状态检查

### 检查检索服务

```bash
GET /api/v1/search/available
```

### 检查生成服务

```bash
GET /api/v1/generate/available
```

---

## 错误处理

所有错误响应格式：
```json
{
  "error": "错误信息"
}
```

常见错误：
- `缺少 X-User-ID` (400)
- `非法场景标签` (400)
- `样本不存在` (400)

---

## LLM 配置

在 `.env` 文件配置：

```env
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-xxx
LLM_MODEL=deepseek-chat
```

支持的提供商：
- deepseek
- zhipu (智谱)
- qwen (通义)
- openai
- ollama (本地)

---

## 用户自带 Key

（待实现）用户可通过 API 提供自己的 API Key：

```bash
POST /api/v1/user/llm-config
Header: X-User-ID: advisor_001

{
  "provider": "zhipu",
  "api_key": "user-own-key",
  "model": "glm-4-flash"
}
```

---

## 调用示例 (Python)

```python
import requests

BASE_URL = "http://localhost:5000/api/v1"
USER_ID = "advisor_001"

headers = {"X-User-ID": USER_ID}

# 创建样本
response = requests.post(
    f"{BASE_URL}/samples",
    headers=headers,
    json={
        "parent_message": "价格有点高",
        "advisor_reply": "理解您的顾虑...",
        "scene_tag": "问价格",
        "source_type": "manual_input"
    }
)

# 激活样本
sample_id = response.json()["sample_id"]
requests.post(f"{BASE_URL}/samples/{sample_id}/activate", headers=headers)

# 检索
response = requests.post(
    f"{BASE_URL}/search",
    headers=headers,
    json={"query": "价格有点高", "top_k": 5}
)

# 生成
response = requests.post(
    f"{BASE_URL}/generate/reply",
    headers=headers,
    json={"query": "价格有点高", "scene_hint": "问价格"}
)
candidates = response.json()["candidates"]
```

---

版本: v0.2.0
更新时间: 2026-05-19
