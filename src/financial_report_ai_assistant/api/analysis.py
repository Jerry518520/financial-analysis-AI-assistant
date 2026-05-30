from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from financial_report_ai_assistant.services.rag_service import query_rag_with_source, RAG_NOT_FOUND, RAG_INDEX_MISSING, RAG_INDEX_BUILDING
from financial_report_ai_assistant.services.ai_chat import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import asyncio
import json
import re

from financial_report_ai_assistant.api.utils import extract_cited_pages

router = APIRouter()

def _extract_cited_pages(text: str) -> list:
    """从 LLM 回答中提取引用的页码（兼容旧调用）"""
    return extract_cited_pages(text)

class AnalysisRequest(BaseModel):
    focus: str = "general" # general, financial, risk, business

# 不同 focus 对应的检索关键词
FOCUS_QUERIES = {
    "general": [
        "营业收入 营业成本 净利润 毛利率",
        "归属于上市公司股东的净利润",
        "合并利润表 营业收入 净利润",
        "主要财务数据和指标",
        "总资产 所有者权益",
        "Business Overview and Outlook",
    ],
    "financial": [
        "营业收入 营业成本 毛利率",
        "归属于上市公司股东的净利润",
        "合并利润表 营业收入 营业成本 净利润 利润总额",
        "主要财务数据和指标",
        "合并资产负债表 总资产 负债总额",
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
        if ctx and RAG_INDEX_MISSING not in ctx and RAG_NOT_FOUND not in ctx and RAG_INDEX_BUILDING not in ctx:
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

【数据使用规则（必须严格遵守）】：
- 营业收入和营业成本必须来自同一张表（合并利润表或主要会计数据表），禁止混合不同表格的数据
- 毛利率 = (营业收入 - 营业成本) / 营业收入，用合并报表数据计算。如果片段中没有营业成本数据，直接写"毛利率：见财报原文"，禁止估算
- 净利润优先使用"归属于上市公司股东的净利润"，如无则用"净利润"
- 禁止用利润总额代替净利润，禁止用营业总成本代替营业成本
- 如果某个指标在片段中确实找不到，直接省略该指标，不要编造或估算

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
        # 只展示 LLM 实际引用的页码，过滤幻觉页码
        # 兜底：如果 LLM 回答中未提取到页码，使用向量检索的来源页
        cited = extract_cited_pages(summary)
        valid_cited = [p for p in cited if p in all_source_pages]
        source_pages = sorted(valid_cited) if valid_cited else sorted(all_source_pages)
        return {"summary": summary, "source_pages": source_pages}
    except Exception as e:
        print(f"❌ 摘要生成失败: {e}")
        return JSONResponse(status_code=500, content={"error": f"生成摘要时发生错误: {str(e)}"})


# ==================== 能力雷达图 ====================

class RadarRequest(BaseModel):
    industry: str = ""  # 空字符串表示自动识别

RADAR_SEARCH_QUERIES = [
    "主要财务数据和指标",
    "合并利润表 营业收入 净利润 营业利润 营业成本",
    "合并资产负债表 资产总额 负债总额 流动资产 流动负债",
    "毛利率 净利率 ROE 资产负债率",
    "流动比率 速动比率 资产周转率 存货周转率",
    "营业收入同比增长率 净利润增长率 总资产增长率",
    "应收账款 利息保障倍数 现金流量 营运资本",
    "留存收益 息税前利润 EBIT",
]

RADAR_EXTRACTION_PROMPT = """你是一位金融数据提取专家。请从以下财报片段中提取关键财务指标，以严格JSON格式返回。

【检索到的财报片段】：
{context}

【任务要求】：
1. 提取以下指标的最新一期数值（合并报表优先）：

盈利能力：
   - 毛利率（小数，如0.25表示25%）
   - 净利率（小数）
   - ROE / 净资产收益率 / 加权平均净资产收益率（小数）
   - 营业利润率（小数，营业利润/营业收入）
   - 成本费用利润率（小数，利润总额/成本费用总额）

资产质量：
   - 资产周转率（数值，营业收入/平均总资产）
   - 存货周转率（数值）
   - 应收账款周转率（数值，营业收入/平均应收账款）
   - 现金回收率（小数，经营活动现金流净额/平均总资产）

债务风险：
   - 资产负债率（小数）
   - 流动比率（数值）
   - 速动比率（数值）
   - 利息保障倍数（数值，息税前利润/利息费用）
   - 现金流动负债比（小数，经营活动现金流净额/流动负债）

经营增长：
   - 营收增长率 / 营业收入同比增长率（小数）
   - 净利润增长率 / 净利润同比增长率（小数）
   - 总资产增长率（小数）
   - 资本保值增值率（小数，期末所有者权益/期初所有者权益）

Altman Z-Score 相关（尽量提取，用于破产风险评估）：
   - 营运资本比（小数，营运资本/总资产）
   - 留存收益比（小数，留存收益/总资产）
   - EBIT资产比（小数，息税前利润/总资产）
   - 权益负债比（数值，权益市值或净资产/负债总额）

2. 推断公司所属行业（从以下列表中选择最匹配的一个：{industry_list}）

3. 如果某个指标在片段中未找到，设为null

4. 严格按以下JSON格式输出，不要有任何其他文字：

{{
  "industry": "行业名称",
  "metrics": {{
    "毛利率": 0.25,
    "净利率": 0.08,
    "ROE": 0.10,
    "营业利润率": 0.10,
    "成本费用利润率": 0.12,
    "资产负债率": 0.50,
    "流动比率": 1.50,
    "速动比率": 1.00,
    "利息保障倍数": 5.0,
    "现金流动负债比": 0.25,
    "资产周转率": 0.80,
    "存货周转率": 4.00,
    "应收账款周转率": 6.00,
    "现金回收率": 0.10,
    "营收增长率": 0.08,
    "净利润增长率": 0.08,
    "总资产增长率": 0.10,
    "资本保值增值率": 1.10,
    "营运资本比": 0.05,
    "留存收益比": 0.15,
    "EBIT资产比": 0.08,
    "权益负债比": 1.00
  }}
}}"""


@router.get("/analyze/industries")
async def get_industries():
    from financial_report_ai_assistant.services.financial_calculator import list_industries
    return {"industries": list_industries()}


@router.post("/analyze/radar")
async def generate_radar_chart(request: RadarRequest):
    """生成能力雷达图数据"""
    # 1. RAG 检索
    contexts = []
    all_source_pages = set()
    for q in RADAR_SEARCH_QUERIES:
        result = await asyncio.to_thread(query_rag_with_source, q, 2)
        ctx = result.get("context", "")
        if ctx and RAG_INDEX_MISSING not in ctx and RAG_NOT_FOUND not in ctx and RAG_INDEX_BUILDING not in ctx:
            contexts.append(ctx)
            all_source_pages.update(result.get("source_pages", []))

    if not contexts:
        return JSONResponse(status_code=400, content={"error": "无法生成雷达图：知识库尚未建立或未检索到有效信息。"})

    full_context = "\n---\n".join(contexts)[:MAX_CONTEXT_CHARS]

    # 2. LLM 提取结构化数据
    from financial_report_ai_assistant.services.financial_calculator import list_industries
    industry_list = "、".join(list_industries())

    prompt = ChatPromptTemplate.from_template(RADAR_EXTRACTION_PROMPT)
    chain = prompt | get_llm() | StrOutputParser()

    try:
        raw_response = await asyncio.to_thread(chain.invoke, {"context": full_context, "industry_list": industry_list})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"LLM 提取失败: {str(e)}"})

    # 3. 解析 JSON
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', raw_response)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return JSONResponse(status_code=500, content={"error": "未能从财报中提取足够的财务数据生成雷达图。"})
        else:
            return JSONResponse(status_code=500, content={"error": "未能从财报中提取足够的财务数据生成雷达图。"})

    company_metrics = data.get("metrics", {})
    industry = request.industry or data.get("industry", "")

    # 4. 计算评分
    from financial_report_ai_assistant.services.financial_calculator import compute_radar_scores, INDUSTRY_BENCHMARKS
    if industry not in INDUSTRY_BENCHMARKS:
        # LLM 推断的行业不在列表中，尝试模糊匹配
        for valid_industry in INDUSTRY_BENCHMARKS:
            if valid_industry in industry or industry in valid_industry:
                industry = valid_industry
                break
        else:
            industry = "制造业"  # 默认

    result = compute_radar_scores(company_metrics, industry)
    result["extracted_metrics"] = company_metrics
    result["source_pages"] = sorted(all_source_pages)

    return result
