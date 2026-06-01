# 快捷回复助手 - 打包与部署指南

> 本文档说明如何将项目打包并部署到其他环境（云服务器、客户机器等）

> 当前桌面版以 `build.bat` 打包为准，会生成 `dist/QuickReplyAssistant/` 目录；打包时需要保留 `data/`，避免覆盖验证数据。下面的压缩包 / 虚拟环境 / 云服务器说明保留为早期部署方案参考。

---

## 一、依赖管理策略

### 方案A：项目独立虚拟环境（推荐）

在项目目录内创建独立虚拟环境，便于整体打包。

```bash
# 在项目目录下创建虚拟环境
cd E:/fsl-works/fsl/助手_项目
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r server/requirements.txt
```

**优点**：
- 所有依赖在项目目录内
- 打包时直接复制整个目录
- 不受系统环境影响

---

### 方案B：全局虚拟环境（当前状态）

当前依赖安装在：
```
C:\Users\fengshuiliang\ai_venv\opencode_venv
```

**缺点**：
- 打包需要单独处理依赖
- 不同机器需要重新安装

---

## 二、打包方案

### 方案1：完整打包（推荐）

包含源代码 + 虚拟环境 + 数据目录。

```bash
# 1. 创建项目虚拟环境
cd E:/fsl-works/fsl/助手_项目
python -m venv venv
venv\Scripts\activate
pip install -r server/requirements.txt

# 2. 初始化数据库（可选，预置数据）
python scripts/init_db.py

# 3. 打包（压缩整个目录）
# Windows PowerShell:
Compress-Archive -Path "E:/fsl-works/fsl/助手_项目" -DestinationPath "回复助手_v0.1.0.zip"
```

**打包后目录结构**：
```
助手_项目/
├── venv/                    # 独立虚拟环境 ★
├── server/                  # 后端代码
├── pc-client/               # PC客户端
├── shared/                  # 共享模块
├── scripts/                 # 工具脚本
├── data/                    # 数据目录（可选）
├── requirements.txt         # 依赖清单
├── README.md
├── AGENTS.md
└── DEPLOY.md               # 本文档 ★
```

---

### 方案2：仅代码打包 + 依赖清单

不包含虚拟环境，目标机器自行安装。

```bash
# 打包代码（不含venv）
# Windows PowerShell:
$exclude = @("venv", "__pycache__", "*.pyc", ".env")
Get-ChildItem -Path "E:/fsl-works/fsl/助手_项目" -Recurse |
  Where-Object { $exclude -notcontains $_.Name } |
  Compress-Archive ...

# 或简单排除venv目录：
Compress-Archive -Path "server", "pc-client", "shared", "scripts", "README.md", "AGENTS.md", "requirements.txt" -DestinationPath "回复助手_code_v0.1.0.zip"
```

**目标机器部署**：
```bash
# 1. 解压
unzip 回复助手_code_v0.1.0.zip

# 2. 创建虚拟环境并安装依赖
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 填入实际配置

# 4. 启动服务
python server/app/main.py
```

---

## 三、云服务器部署

### 环境要求

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.10+ | 必须 |
| 内存 | 4GB+ | Embedding模型需要 |
| 存储 | 10GB+ | Chroma向量库持久化 |

### 部署步骤

```bash
# 1. 上传打包文件到服务器
scp 回复助手_v0.1.0.zip user@server:/home/user/

# 2. 解压
ssh user@server
cd /home/user
unzip 回复助手_v0.1.0.zip

# 3. 激活虚拟环境
cd 助手_项目
source venv/bin/activate

# 4. 配置环境变量
cp .env.example .env
vim .env  # 编辑配置

# 5. 启动服务
python server/app/main.py

# 6. 或使用 systemd 后台运行
# 创建服务文件: /etc/systemd/system/reply-helper.service
```

**systemd 服务文件**：
```ini
[Unit]
Description=快捷回复助手
After=network.target

[Service]
Type=simple
User=user
WorkingDirectory=/home/user/助手_项目
Environment="PATH=/home/user/助手_项目/venv/bin"
ExecStart=/home/user/助手_项目/venv/bin/python server/app/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## 四、Docker 部署（可选）

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server/ ./server/
COPY shared/ ./shared/
COPY scripts/ ./scripts/

ENV DATABASE_PATH=/app/data/samples.db
ENV VECTOR_STORE_PATH=/app/data/chroma

EXPOSE 5000

CMD ["python", "server/app/main.py"]
```

```bash
# 构建镜像
docker build -t reply-helper:v0.1.0 .

# 运行容器
docker run -d -p 5000:5000 -v /app/data:/app/data reply-helper:v0.1.0
```

---

## 五、依赖清单

当前 `requirements.txt` 包含：

```
flask>=2.3.0           # Web框架
flask-cors>=4.0.0      # CORS支持
chromadb>=0.4.0        # 向量库 ★ 需安装
sentence-transformers>=2.2.0  # Embedding ★ 需安装
openai>=1.0.0          # 大模型调用
wechatpy>=1.8.0        # 公众号SDK
pydantic>=2.0.0        # 数据验证
cryptography>=41.0.0   # 加密
python-dotenv>=1.0.0   # 环境变量
pytest>=7.0.0          # 测试
keyboard>=0.13.5       # PC客户端快捷键
pyperclip>=1.8.0       # PC客户端剪贴板
```

---

## 六、当前状态检查

```bash
# 查看当前依赖安装位置
pip show flask

# 查看已安装依赖
pip list

# 查看Python路径
python -c "import sys; print(sys.prefix)"
```

---

## 七、下一步建议

1. **立即操作**：为项目创建独立虚拟环境
   ```bash
   cd E:/fsl-works/fsl/助手_项目
   python -m venv venv
   venv\Scripts\activate
   pip install -r server/requirements.txt
   ```

2. **验证向量检索**：安装 sentence-transformers + chromadb
   ```bash
   pip install sentence-transformers chromadb
   python scripts/test_storage.py
   ```

3. **打包测试**：压缩并测试在其他目录运行

---

版本：v0.1.0
更新：2026-05-18
