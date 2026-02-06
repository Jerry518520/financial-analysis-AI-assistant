# 🤖 财报AI分析助手 (Financial Report AI Assistant)

<!-- 这一行是徽章(Badges)，它们是项目状态的可视化标志，非常专业。 -->
<p align="center">
  <img alt="Python Version" src="https://img.shields.io/badge/python-3.11-blue">
  <img alt="Framework" src="https://img.shields.io/badge/Backend-FastAPI-green">
  <img alt="Framework" src="https://img.shields.io/badge/Frontend-Streamlit-red">
  <img alt="Deploy" src="https://img.shields.io/badge/Docker-Ready-blue">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-lightgrey">
</p>

> ⚠️ **项目状态：MVP (最小可行性产品) 已完成**
> 这是一个旨在学习和展示现代AI应用开发全流程的项目。

这是一个Web应用，旨在利用大语言模型（LLM）的能力，帮助非金融专业人士轻松读懂并分析上市公司的PDF格式财务报表。用户只需上传一份财报，即可通过自然语言进行提问、要求计算和生成通俗易懂的摘要。

---

## ✨ 核心功能

*   **📄 智能PDF解析**: 集成 **LlamaParse**，支持从复杂的中文财报PDF中提取文本和无边框表格。
*   **💬 核心指标问答**: 基于 **RAG (检索增强生成)** 技术，精准回答关于营收、净利润等具体数据的问题。
*   **💡 智能分析与计算**: 内置 **AI Agent** (基于 LangGraph)，能自动调用计算器工具计算同比增长率、ROE、毛利率等指标。
*   **✍️ 一键生成摘要**: 针对长文档生成结构化的核心财务摘要，快速掌握企业经营状况。
*   **🐳 Docker一键部署**: 提供完整的 Docker Compose 配置，支持前后端一键启动，解决环境依赖问题。

---

## 🛠️ 技术栈与架构

本项目采用前后端分离的现代Web架构：

*   **前端**: **Streamlit** - 交互式数据分析界面。
*   **后端**: **FastAPI** - 高性能异步API服务。
*   **AI核心**:
    *   **LangGraph**: 构建具备 Tool Calling 能力的智能体。
    *   **FAISS**: 本地向量数据库，用于知识库检索。
    *   **LlamaParse**: 专业的文档解析服务。
*   **基础设施**:
    *   **Docker & Docker Compose**: 容器化部署。
    *   **Poetry**: 依赖管理。

---

## 🚀 快速开始 (Docker 推荐)

这是最简单、最推荐的运行方式，无需在本地配置复杂的 Python 环境。

### 1. 前置准备
*   安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/) 并启动。
*   获取 API Key:
    *   **DeepSeek API Key**: 用于大模型对话。
    *   **LlamaCloud API Key**: 用于 PDF 解析 (可在 [LlamaCloud](https://cloud.llamaindex.ai/) 免费申请)。

### 2. 配置环境变量
在项目根目录下创建一个 `.env` 文件，填入你的 Key：

```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
LLAMA_CLOUD_API_KEY=llx-xxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. 一键启动
在项目根目录打开终端，运行：

```bash
docker-compose up --build
```

### 4. 访问应用
*   **前端界面**: 打开浏览器访问 [http://localhost:8501](http://localhost:8501)
*   **后端文档**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🐍 本地开发运行 (可选)

如果你想进行代码开发，可以使用 Poetry 在本地运行。

1.  **安装依赖**:
    ```bash
    poetry install
    ```
2.  **启动后端**:
    ```bash
    poetry run uvicorn financial_report_ai_assistant.api.main:app --reload
    ```
3.  **启动前端**:
    ```bash
    poetry run streamlit run frontend/main.py
    ```

---

## 📝 验收清单

- [x] 上传 PDF 文件并解析成功
- [x] 提问“今年的营收是多少”，能准确检索并回答
- [x] 提问“计算净利润增长率”，能调用计算器工具
- [x] 点击“生成摘要”，能输出完整的财报分析
