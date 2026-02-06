# 项目优化与功能增强更新日志 (2025-02-06)

本次更新主要集中在提升 PDF 解析精度、增强 Agent 的计算与分析能力，以及完善系统的工程化体验。

## 1. 核心解析能力增强 (Document Parser)
**文件**: `src/financial_report_ai_assistant/services/document_parser.py`

*   **新增启发式无边框表格检测**: 
    *   针对 PyMuPDF 无法识别的无边框表格（Open Table），增加了 `_is_suspected_table_page` 检测函数。
    *   通过检测页面中的“财报关键词”（如 *Consolidated Balance Sheet*）和“高密度数字分布”，智能判定表格页。
    *   一旦判定为表格页，强制通过 LlamaParse 进行高精度解析，显著解决了无边框表格数据丢失的问题。
*   **中文财报适配**:
    *   将 LlamaParse 的 `language` 参数从默认的 `en` 调整为 `zh`，大幅提升了中文财报中字段名的识别准确率。

## 2. 智能 Agent 与计算工具链 (Agent & Calculator)
**文件**: `src/financial_report_ai_assistant/services/financial_calculator.py`
**文件**: `src/financial_report_ai_assistant/core/agent.py`

*   **实现财务计算器**:
    *   新增 `financial_calculator.py`，封装了 `calculate_growth_rate` (增长率)、`calculate_margin` (利润率)、`calculate_roe` (ROE) 等核心算法。
*   **重构 Agent 架构**:
    *   将 Agent 核心从旧版 LangChain 迁移至最新的 **LangGraph** (`create_react_agent`)。
    *   赋予 Agent **Tool Calling** 能力：Agent 现在能识别用户意图（如“计算同比增长”），自动调用计算器函数获取精确结果，彻底告别 LLM 的“幻觉估算”。

## 3. RAG 知识库持久化 (RAG Service)
**文件**: `src/financial_report_ai_assistant/services/rag_service.py`

*   **本地持久化**:
    *   新增 `save_local` 逻辑，在构建完 FAISS 向量索引后自动保存到本地 `faiss_index` 目录。
*   **智能加载**:
    *   新增 `load_vector_store` 逻辑，服务启动或查询时若内存无索引，自动尝试从磁盘加载。实现了“一次解析，多次使用”，无需每次重启服务都重新解析 PDF。

## 4. 智能分析与摘要生成 (Analysis API & Frontend)
**文件**: `src/financial_report_ai_assistant/api/analysis.py`
**文件**: `frontend/main.py`

*   **后端摘要接口**:
    *   新增 `/analyze/summary` 接口。该接口会自动检索财报中的 MD&A、风险因素、关键财务数据等核心章节。
    *   利用 LLM 综合上下文，生成包含“核心财务指标”、“经营亮点”、“风险提示”和“未来展望”的结构化 Markdown 报告。
*   **前端体验升级**:
    *   在 Streamlit 界面的“智能分析”板块新增 **✨ 生成核心摘要** 按钮。
    *   用户点击即可一键获取财报精华，配合下方的对话框，形成“主动报告 + 被动问答”的完整分析体验。

## 5. 工程化与稳定性 (Engineering)
**文件**: `src/financial_report_ai_assistant/api/main.py`

*   **路由集成**: 注册了新的 Analysis 路由模块。
*   **导入路径修正**: 统一修正了项目中的模块导入路径，解决了相对导入在不同启动方式下的兼容性问题。
