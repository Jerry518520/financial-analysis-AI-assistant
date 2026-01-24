# 项目架构文档 (ARCHITECTURE.md)

## 项目概述
**一句话描述**：基于 RAG（检索增强生成）技术的智能财报分析助手。
**详细描述**：本项目旨在通过结合高精度的 PDF 解析（PyMuPDF + LlamaParse）与先进的向量检索技术，为用户提供一个能够深度理解并回答复杂财报问题的 AI 助手。系统能够自动识别财报中的表格与文本，并利用混合解析策略确保数据提取的准确性，最终通过 LLM（如 DeepSeek）生成专业的回应。

## 技术栈清单
| 核心库 | 作用 |
| :--- | :--- |
| **LangChain** | 整个 RAG 流程的编排者，负责文本切分、Prompt 管理及 LLM 交互。 |
| **Streamlit** | 提供直观的前端交互界面，支持文件上传与实时对话。 |
| **FastAPI** | 后端 API 服务，处理前端请求并调度底层服务。 |
| **PyMuPDF (fitz)** | 负责本地 PDF 文本提取及智能表格检测（分流器）。 |
| **LlamaParse** | 针对包含复杂表格的页面进行高精度 Markdown 转换。 |
| **FAISS** | 高性能本地向量数据库，用于存储和检索文档碎片。 |
| **HuggingFace** | 提供本地 Embedding 模型 (`all-MiniLM-L6-v2`)，无需依赖外部 API。 |
| **DeepSeek / OpenAI** | 核心大语言模型，负责理解检索内容并生成答案。 |

## 目录结构说明
- **frontend/**: 包含基于 Streamlit 的用户界面代码。
- **src/financial_report_ai_assistant/**:
  - **api/**: 定义了 FastAPI 的路由和控制器，处理 Web 请求。
  - **core/**: 包含系统的核心引擎，如 Agent 决策逻辑和基础 RAG 实现。
  - **services/**: 具体的业务逻辑实现，包括：
    - `document_parser.py`: 混合解析引擎（PyMuPDF + LlamaParse）。
    - `rag_service.py`: 向量库构建与检索逻辑。
    - `ai_chat.py`: LLM 对话交互服务。
  - **utils/**: 通用的工具类，如日志配置。
- **tests/**: 包含单元测试和集成测试，确保核心解析和计算逻辑的稳定性。

## 核心逻辑流程
1. **上传与解析 (Ingestion)**: 
   - 用户通过 UI 上传 PDF 财报。
   - `document_parser.py` 扫描文档：普通页使用 PyMuPDF，表格页送往 LlamaParse。
2. **向量化与存储 (Indexing)**:
   - 解析后的全量 Markdown 文本由 `rag_service.py` 进行智能切分。
   - 使用 HuggingFace 模型将文本块转换为向量，并存入 FAISS 索引。
3. **检索与问答 (RAG Flow)**:
   - 用户提出财报相关问题。
   - 系统将问题向量化，在 FAISS 中检索最相关的 top-k 个文本碎片。
   - 将检索到的背景知识与用户问题组合，发送给 LLM 生成最终答案。
