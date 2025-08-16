# 🤖 财报AI分析助手 (Financial Report AI Assistant)

<!-- 这一行是徽章(Badges)，它们是项目状态的可视化标志，非常专业。现在是占位符，等我们做到后面阶段再把它们激活。 -->
<p align="center">
  <img alt="Python Version" src="https://img.shields.io/badge/python-3.10%2B-blue">
  <img alt="Framework" src="https://img.shields.io/badge/Backend-FastAPI-green">
  <img alt="Framework" src="https://img.shields.io/badge/Frontend-Streamlit-red">
  <img alt="License" src="https://img.shields.io/badge/license-MIT-lightgrey">
</p>

> ⚠️ **项目状态：正在积极开发中**
> 这是一个旨在学习和展示现代AI应用开发全流程的项目。

这是一个Web应用，旨在利用大语言模型（LLM）的能力，帮助非金融专业人士轻松读懂并分析上市公司的PDF格式财务报表。用户只需上传一份财报，即可通过自然语言进行提问、要求计算和生成通俗易懂的摘要。

---

## ✨ 核心功能

*   **📄 智能PDF解析**: 自动从结构复杂的财报PDF中提取关键文本和核心财务数据表格。
*   **💬 核心指标问答**: 通过自然语言提问（例如：“这季度的营收和净利润是多少？”），AI会从解析出的数据中精准回答。
*   **💡 智能分析与计算**: 支持更复杂的指令（例如：“帮我计算一下毛利率，并和去年同期对比”），AI Agent会自动调用工具链完成计算。
*   **✍️ 一键生成摘要**: 为长达上百页的财报，一键生成一份“给外行看的”核心要点摘要。

---

## 🛠️ 技术栈与架构

本项目采用前后端分离的现代Web架构，并围绕大语言模型（LLM）构建了一套完整的 **RAG (Retrieval-Augmented Generation) 与 Agent** 解决方案。

*   **前端**: **Streamlit** - 用于快速构建数据密集型的交互式Web界面。
*   **后端**: **FastAPI** - 高性能的Python Web框架，提供异步API接口。
*   **数据处理**:
    *   **PyMuPDF & Unstructured.io**: 解析PDF文档，提取文本与表格。
    *   **Pandas**: 清洗、处理和分析从财报中提取的结构化表格数据。
*   **AI核心 (大脑)**:
    *   **RAG技术栈**: 使用 **FAISS** 作为向量数据库，实现对财报文本内容的高效语义检索。
    *   **AI Agent (ReAct模式)**: 构建具备思考-行动-观察循环的智能体，赋予AI调用工具（如财务计算器）的能力。
    *   **模型框架**: **LangChain / LangGraph** - 用于编排和构建复杂的AI调用链与状态机。
*   **工程化 & DevOps**:
    *   **依赖管理**: **Poetry** - 提供专业的Python包管理和可复现的环境。
    *   **容器化**: **Docker** - 将后端服务打包成镜像，实现一键部署和环境隔离。
    *   **代码测试**: **Pytest** - 编写单元测试，确保核心工具函数（如财务计算）的准确性。

---

## 🚀 快速开始

在开始之前，请确保你已经安装了 [Python 3.10+](https://www.python.org/), [Git](https://git-scm.com/) 和 [Poetry](https://python-poetry.org/)。

**1. 克隆本项目**
```bash
git clone https://github.com/[Jerry518520]/financial-report-ai-assistant.git
cd financial-report-ai-assistant