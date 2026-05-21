from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from financial_report_ai_assistant.services.rag_service import query_rag_with_source, RAG_NOT_FOUND, RAG_INDEX_MISSING
from financial_report_ai_assistant.services.ai_chat import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import asyncio

router = APIRouter()

class AnalysisRequest(BaseModel):
    focus: str = "general" # general, financial, risk, business

# 不同 focus 对应的检索关键词
FOCUS_QUERIES = {
    "general": [
        "Financial Highlights and Key Figures",
        "主要财务数据和指标",
        "Business Overview and Outlook",
        "公司业务概要",
    ],
    "financial": [
        "Financial Highlights and Key Figures",
        "主要财务数据和指标",
        "Revenue and Profit Analysis",
        "收入和利润分析",
        "Balance Sheet",
        "合并资产负债表",
    ],
    "risk": [
        "Risk Factors",
        "风险因素",
        "风险管理",
        "Liquidity and Capital Resources",
    ],
    "business": [
        "Business Overview and Outlook",
        "公司业务概要",
        "Management Discussion and Analysis (MD&A)",
        "管理层讨论与分析",
    ],
}

# 上下文最大字符数限制（防止超出 DeepSeek 上下文窗口）
MAX_CONTEXT_CHARS = 30000

@router.post("/analyze/summary")
async def generate_report_summary(request: AnalysisRequest):
    """
    生成财报的核心摘要
    """
    # 1. 根据 focus 选择检索关键词
    search_queries = FOCUS_QUERIES.get(request.focus, FOCUS_QUERIES["general"])
    
    contexts = []
    all_source_pages = set()
    for q in search_queries:
        # 每个 query 找 top 2，避免上下文过长
        result = await asyncio.to_thread(query_rag_with_source, q, 2)
        ctx = result.get("context", "")
        if ctx and RAG_INDEX_MISSING not in ctx and RAG_NOT_FOUND not in ctx:
            contexts.append(ctx)
            all_source_pages.update(result.get("source_pages", []))

    if not contexts:
        return {"summary": "无法生成摘要：知识库尚未建立或未检索到有效信息。请先上传并解析财报。", "source_pages": []}
        
    # 拼接上下文，截断到安全范围内
    full_context = "\n---\n".join(contexts)
    if len(full_context) > MAX_CONTEXT_CHARS:
        print(f"⚠️ 上下文长度 {len(full_context)} 超过限制 {MAX_CONTEXT_CHARS}，进行截断")
        # 截断到最近的换行符，避免切断数字
        cut_pos = full_context.rfind("\n", 0, MAX_CONTEXT_CHARS)
        if cut_pos < MAX_CONTEXT_CHARS // 2:
            cut_pos = MAX_CONTEXT_CHARS  # 换行符太远，直接硬截断
        full_context = full_context[:cut_pos] + "\n\n[... 上下文已截断 ...]"
    
    # 2. 根据 focus 调整生成提示
    focus_instructions = {
        "general": "请涵盖核心财务指标、经营亮点、风险提示和未来展望。",
        "financial": "请重点分析核心财务指标（营收、净利润、毛利率等）及其同比变化趋势。",
        "risk": "请重点识别和分析主要风险因素、风险管理策略。",
        "business": "请重点描述业务概况、经营亮点和未来展望。",
    }
    focus_hint = focus_instructions.get(request.focus, focus_instructions["general"])
    
    template = """你是一位资深的金融分析师。请根据以下从财报中检索到的片段，为用户生成一份结构清晰的【财报核心摘要】。

【重要】禁止任何开场白、问候语或自我介绍，直接从正文内容开始。

【检索到的财报片段】：
{context}

【任务要求】：
1. **核心财务指标**：提取营收、净利润、毛利率等关键数据及其同比变化（如果片段中有）。
2. **经营亮点**：简述本季度的业务进展或重大成就。
3. **风险提示**：如果有提及，列出主要的风险因素。
4. **未来展望**：管理层对未来的预期。

【分析重点】：{focus_hint}

请使用 Markdown 格式输出，使用小标题（###）分隔不同部分。如果某些信息在片段中未找到，请直接省略该部分，不要编造。
保持语言专业、客观、精炼。

【数据来源要求】：
- 每个核心财务指标必须标注来源页码，格式为"（第X页）"
- 禁止编造任何数字，所有数据必须来自上述检索片段"""
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | get_llm() | StrOutputParser()
    
    try:
        print("💡 正在生成摘要...")
        summary = await asyncio.to_thread(chain.invoke, {"context": full_context, "focus_hint": focus_hint})
        return {"summary": summary, "source_pages": sorted(all_source_pages)}
    except Exception as e:
        print(f"❌ 摘要生成失败: {e}")
        return JSONResponse(status_code=500, content={"error": f"生成摘要时发生错误: {str(e)}"})
