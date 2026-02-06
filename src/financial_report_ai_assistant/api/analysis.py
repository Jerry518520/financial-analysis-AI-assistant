from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from financial_report_ai_assistant.services.rag_service import query_rag
from financial_report_ai_assistant.services.ai_chat import llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

router = APIRouter()

class AnalysisRequest(BaseModel):
    focus: str = "general" # general, financial, risk, business

@router.post("/analyze/summary")
async def generate_report_summary(request: AnalysisRequest):
    """
    生成财报的核心摘要
    """
    # 1. 针对摘要任务，我们需要检索更广泛的关键信息
    # 构造几个核心查询词，分别检索，然后合并上下文
    search_queries = [
        "Financial Highlights and Key Figures",
        "Management Discussion and Analysis (MD&A)",
        "Business Overview and Outlook",
        "Risk Factors",
        "主要财务数据和指标",
        "管理层讨论与分析",
        "公司业务概要"
    ]
    
    contexts = []
    for q in search_queries:
        # 每个 query 找 top 2，避免上下文过长
        ctx = query_rag(q, top_k=2)
        if ctx and "系统提示：知识库尚未建立" not in ctx:
            contexts.append(ctx)
            
    if not contexts:
        return {"summary": "无法生成摘要：知识库尚未建立或未检索到有效信息。请先上传并解析财报。"}
        
    full_context = "\n---\n".join(contexts)
    
    # 2. 调用 LLM 生成摘要
    template = """
    你是一位资深的金融分析师。请根据以下从财报中检索到的片段，为用户生成一份结构清晰的【财报核心摘要】。
    
    【检索到的财报片段】：
    {context}
    
    【任务要求】：
    1. **核心财务指标**：提取营收、净利润、毛利率等关键数据及其同比变化（如果片段中有）。
    2. **经营亮点**：简述本季度的业务进展或重大成就。
    3. **风险提示**：如果有提及，列出主要的风险因素。
    4. **未来展望**：管理层对未来的预期。
    
    请使用 Markdown 格式输出，使用小标题（###）分隔不同部分。如果某些信息在片段中未找到，请直接省略该部分，不要编造。
    保持语言专业、客观、精炼。
    """
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    
    try:
        print("💡 正在生成摘要...")
        summary = chain.invoke({"context": full_context})
        return {"summary": summary}
    except Exception as e:
        print(f"❌ 摘要生成失败: {e}")
        return {"summary": f"生成摘要时发生错误: {str(e)}"}
