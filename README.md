# 财报AI分析助手 (Financial Report AI Assistant)

<p align="center">
  <img alt="Python Version" src="https://img.shields.io/badge/python-3.11-blue">
  <img alt="Framework" src="https://img.shields.io/badge/Backend-FastAPI-green">
  <img alt="Framework" src="https://img.shields.io/badge/Frontend-Streamlit-red">
  <img alt="Deploy" src="https://img.shields.io/badge/Docker-Ready-blue">
  <img alt="GPU" src="https://img.shields.io/badge/GPU-CUDA_12.6-green">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-lightgrey">
</p>

利用大语言模型（LLM）帮助非金融专业人士读懂上市公司 PDF 财报。上传财报，用自然语言提问、计算指标、生成摘要。

---

## 核心功能

- **智能PDF解析**: PyMuPDF + LlamaParse 混合解析，支持无边框表格
- **RAG问答**: 基于 FAISS + BGE-M3 向量检索，精准回答财务数据问题
- **AI Agent**: LangGraph ReAct 循环，自动规划、调用工具、反思重试
- **19种财务指标**: 增长率、利润率、ROE、EPS、PE、资产负债率、流动比率等
- **一键摘要**: 结构化财报核心摘要

---

## 硬件要求

| 要求 | 说明 |
|------|------|
| **NVIDIA GPU** | 必须，RAG 向量化需要 CUDA 加速 |
| **显存 >= 4GB** | BGE-M3 模型约 2GB，加上推理开销 |
| **磁盘 >= 15GB** | Docker 镜像 + torch CUDA wheel |

> 没有 GPU 也可以运行，但 RAG 向量化会极慢（CPU 模式），不推荐。

---

## 第一次使用（Docker 部署）

### 第 1 步：安装前置软件

| 软件 | 说明 | 下载 |
|------|------|------|
| Docker Desktop | 容器运行环境 | [下载](https://www.docker.com/products/docker-desktop/) |
| Git | 版本控制（可选） | [下载](https://git-scm.com) |

> 没有 Git？直接在 GitHub 页面点 "Code" → "Download ZIP"，解压即可。

**安装后确保 Docker Desktop 已启动**（任务栏能看到 Docker 图标）。

### 第 2 步：获取代码

```bash
git clone https://github.com/Jerry518520/financial-analysis-AI-assistant
cd financial-analysis-AI-assistant
```

或下载 ZIP 解压后，用终端进入项目目录。

### 第 3 步：配置 API Key

复制环境变量模板：

```bash
# Windows CMD
copy env.template .env

# Windows PowerShell / Mac / Linux
cp env.template .env
```

编辑 `.env` 文件，填入你的 API Key：

```env
DEEPSEEK_API_KEY=sk-你的key
LLAMA_CLOUD_API_KEY=llx-你的key
```

**获取方式**：
- DeepSeek API Key: https://platform.deepseek.com/
- LlamaCloud API Key: https://cloud.llamaindex.ai/ （免费）

### 第 4 步：（可选）预下载加速

首次构建需要下载约 850MB 的 PyTorch CUDA 包，Docker 内下载较慢（30-60 分钟）。

**想加速？** 双击运行 `download_wheels.bat`，用浏览器/系统工具多线程下载，快 10 倍。

```bash
# 双击这个文件即可：
download_wheels.bat
```

> 不运行也能构建，只是慢。这个步骤完全可选。

### 第 5 步：构建并启动

```bash
docker-compose build
docker-compose up
```

首次构建时间参考：
- **有预下载**: 5-10 分钟
- **无预下载**: 30-60 分钟（取决于网速）
- **后续构建**: 2-5 分钟（有缓存）

### 第 6 步：访问应用

- **前端界面**: http://localhost:8501
- **后端API文档**: http://localhost:8000/docs

### 停止应用

```bash
# Ctrl + C 停止，然后：
docker-compose down
```

---

## 更新到最新版本

```bash
git pull
docker-compose build
docker-compose up
```

---

## 本地开发（可选）

需要 Python 3.11+ 和 NVIDIA GPU。

```bash
# 1. 安装依赖
poetry install

# 2. 安装 CUDA 版 torch（poetry 默认装的是 CPU 版）
poetry run poe install-cuda-torch

# 3. 配置 .env（同上）

# 4. 启动后端
poetry run poe start

# 5. 启动前端（另一个终端）
poetry run streamlit run frontend/main.py
```

---

## 项目结构

```
financial-report-ai-assistant/
├── src/                          # 后端源码
│   └── financial_report_ai_assistant/
│       ├── api/                  # FastAPI 路由
│       ├── core/                 # Agent 核心逻辑
│       └── services/             # PDF解析、RAG、计算服务
├── frontend/                     # Streamlit 前端
├── docker/wheels/                # 预下载的 wheel 文件（git 忽略）
├── scripts/                      # 工具脚本
├── Dockerfile                    # 后端镜像
├── Dockerfile.frontend           # 前端镜像
├── docker-compose.yml            # 编排配置
├── download_wheels.bat           # 预下载加速脚本
├── pyproject.toml                # Poetry 依赖定义
├── requirements-docker.txt       # Docker 构建依赖
└── .env                          # API Key（不提交到 git）
```

---

## 常见问题

**Q: 构建时卡在下载 torch 很久？**

A: 双击运行 `download_wheels.bat` 预下载，再构建。或者耐心等，最终会完成。

**Q: 启动后报 CUDA 不可用？**

A: 确保已安装 NVIDIA 驱动。运行 `nvidia-smi` 检查驱动是否正常。

**Q: 前端连不上后端？**

A: 确保两个容器都在运行。Docker 内前端通过 `http://backend:8000` 访问后端，不需要改配置。

**Q: 如何查看日志？**

A: `docker-compose logs -f` 查看实时日志，`docker-compose logs backend` 只看后端。

---

## 技术栈

| 层 | 技术 |
|---|------|
| 前端 | Streamlit |
| 后端 | FastAPI |
| AI Agent | LangGraph (ReAct) |
| 向量数据库 | FAISS |
| Embedding | BAAI/bge-m3 |
| PDF解析 | PyMuPDF + LlamaParse |
| LLM | DeepSeek API |
| 容器化 | Docker + Docker Compose |
| 依赖管理 | Poetry |
