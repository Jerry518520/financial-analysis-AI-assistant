from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from financial_report_ai_assistant.services.rag_service import query_rag_with_source, RAG_NOT_FOUND, RAG_INDEX_MISSING, RAG_INDEX_BUILDING
from financial_report_ai_assistant.services.ai_chat import get_llm
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import asyncio
import hashlib
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
        "Revenue Cost Profit Margin",
        "Balance Sheet Total Assets",
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
    # 使用与对话接口相同的自然语言查询，确保检索到相同的 chunk
    # 对话问"净利率是多少" → RAG 检索 → Agent 用 tool_calculate_margin 计算
    # 雷达图用相同查询 → RAG 检索到相同 chunk → 提取原始数据 → Python 计算
    "净利润 营业收入 归母净利润",
    "营业收入 营业成本 毛利率",
    "营业利润 利润总额",
    "总资产 负债总额 净资产",
    "流动资产 流动负债 存货 应收账款",
    "经营活动现金流 利息费用",
    "上期营业收入 上期净利润 增长率",
    "主要财务数据和指标",
]

RADAR_EXTRACTION_PROMPT = """你是一位金融数据提取专家。请从以下财报片段中提取【原始财务数据】（金额，单位：元），以严格JSON格式返回。
比率指标由系统自动计算，你只需要提取数字。

【检索到的财报片段】：
{context}

【数据使用规则（必须严格遵守）】：
- 所有数据必须基于【合并报表】，禁止使用母公司报表数据
- 营业收入和营业成本必须来自同一张表（合并利润表或主要会计数据表）
- 净利润优先使用"归属于上市公司股东的净利润"，如无则用"净利润"。禁止用"利润总额-所得税费用"代替净利润（利润表有其他调整项，这样算会出错）
- 使用最新年度（2024年优先）的数据
- 金额直接提取原始数字，不要转换为小数或百分比
- 如果某个数据在片段中找不到，设为 null。绝对不要编造或自行计算缺失的原始数据

【任务要求】：
提取以下合并报表原始数据，推断公司所属行业：

{{
  "industry": "行业名称",
  "raw": {{
    "营业收入": 170899152276,
    "营业成本": 78651952846,
    "营业利润": 119629406544,
    "利润总额": 120145678901,
    "净利润": 89334728025,
    "总资产": 345678901234,
    "负债总额": 97888777778,
    "净资产": 247890123456,
    "流动资产": 198765432100,
    "流动负债": 123456789000,
    "存货": 45678901234,
    "应收账款": 34567890123,
    "平均总资产": 330000000000,
    "平均净资产": 240000000000,
    "平均存货": 43000000000,
    "平均应收账款": 32000000000,
    "经营活动现金流净额": 98765432100,
    "所得税费用": 30810950876,
    "利息费用": 5678901234,
    "息税前利润": 125824580135,
    "成本费用总额": 100000000000,
    "上期营业收入": 147693604994,
    "上期净利润": 77521476277,
    "上期总资产": 310000000000,
    "期初所有者权益": 230000000000,
    "留存收益": 50000000000,
    "营运资本": 75308643100
  }}
}}

2. 推断公司所属行业（从以下列表中选择最匹配的一个：{industry_list}）

3. 如果某个数据在片段中找不到，设为 null

4. 严格按上述JSON格式输出，不要有任何其他文字"""


@router.get("/analyze/industries")
async def get_industries():
    from financial_report_ai_assistant.services.financial_calculator import list_industries
    return {"industries": list_industries()}


@router.post("/analyze/radar")
async def generate_radar_chart(request: RadarRequest):
    """生成能力雷达图数据"""
    # 1. RAG 检索（跨查询去重，避免重复 chunk 浪费上下文预算）
    seen_chunks = set()
    unique_chunks = []
    all_source_pages = set()
    for q in RADAR_SEARCH_QUERIES:
        # 使用与对话接口完全相同的 RAG 参数，确保检索到相同的 chunk
        result = await asyncio.to_thread(query_rag_with_source, q, 8, 0.3)
        ctx = result.get("context", "")
        if ctx and RAG_INDEX_MISSING not in ctx and RAG_NOT_FOUND not in ctx and RAG_INDEX_BUILDING not in ctx:
            # 按分隔符拆分为独立 chunk，逐个去重
            for chunk in ctx.split("\n---\n"):
                chunk = chunk.strip()
                if not chunk:
                    continue
                chunk_key = hashlib.md5(chunk.encode()).hexdigest()  # 用全文 hash 去重，避免前缀相同的不同 chunk 被误删
                if chunk_key not in seen_chunks:
                    seen_chunks.add(chunk_key)
                    unique_chunks.append(chunk)
            all_source_pages.update(result.get("source_pages", []))

    if not unique_chunks:
        return JSONResponse(status_code=400, content={"error": "无法生成雷达图：知识库尚未建立或未检索到有效信息。"})

    full_context = "\n---\n".join(unique_chunks)
    if len(full_context) > MAX_CONTEXT_CHARS:
        # 截断到最近的分隔符，避免切断数字
        cut_pos = full_context.rfind("\n---\n", 0, MAX_CONTEXT_CHARS)
        if cut_pos < MAX_CONTEXT_CHARS // 2:
            cut_pos = full_context.rfind("\n", 0, MAX_CONTEXT_CHARS)
        if cut_pos < MAX_CONTEXT_CHARS // 2:
            cut_pos = MAX_CONTEXT_CHARS
        full_context = full_context[:cut_pos] + "\n\n[... 上下文已截断 ...]"

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

    # 如果只有 metrics 没有 raw，说明 LLM 未遵循新 prompt，打印警告
    if company_metrics and "raw" not in data:
        print("[RADAR-WARN] LLM 返回了旧格式 metrics（未经 Python 验证），数据可能不准确")

    # 如果 LLM 返回的是原始数据（raw 字段），用 Python 计算比率
    raw_data = data.get("raw")
    if raw_data and isinstance(raw_data, dict):
        # 先验证原始数据的合理性
        raw_data = _validate_raw_data(raw_data)
        computed = _compute_ratios_from_raw(raw_data)
        if computed:
            company_metrics = computed
            print(f"[RADAR] 从原始数据计算了 {len(computed)} 个比率指标")

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


def _safe_div(numerator, denominator):
    """安全除法，避免除零和 None"""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _validate_raw_data(raw: dict) -> dict:
    """验证 LLM 提取的原始数据是否合理，修正明显错误的提取结果。

    常见错误模式：
    1. LLM 用"利润总额 - 所得税费用"凑净利润（错误，利润表有其他调整项）
    2. LLM 混淆母公司和合并报表数据
    3. LLM 提取了错误年份的数据
    4. LLM 把「利润总额」当「营业利润」提取（两者在利润表中相邻）
    5. LLM 把「利润总额」当「净利润」提取
    """
    warnings = []
    营业收入 = raw.get("营业收入")
    营业成本 = raw.get("营业成本")
    营业利润 = raw.get("营业利润")
    净利润 = raw.get("净利润")
    利润总额 = raw.get("利润总额")
    所得税费用 = raw.get("所得税费用")

    # 检查 1: 净利润不应大于利润总额（净利润 = 利润总额 - 所得税费用 - 其他调整）
    if 净利润 and 利润总额 and 净利润 > 利润总额 * 1.01:
        warnings.append(f"净利润({净利润}) > 利润总额({利润总额})，可能把利润总额当净利润，清空净利润")
        raw["净利润"] = None

    # 检查 2: 营业利润不应大于营业收入（营业利润率不可能超过 100%）
    if 营业利润 and 营业收入 and 营业收入 > 0 and 营业利润 > 营业收入 * 1.01:
        warnings.append(f"营业利润({营业利润}) > 营业收入({营业收入})，可能把利润总额当营业利润，清空营业利润")
        raw["营业利润"] = None

    # 检查 3: 营业利润不应大于利润总额（营业利润是利润总额的子项）
    if 营业利润 and 利润总额 and 营业利润 > 利润总额 * 1.01:
        warnings.append(f"营业利润({营业利润}) > 利润总额({利润总额})，提取可能有误，清空营业利润")
        raw["营业利润"] = None

    # 检查 4: 营业成本不应大于营业收入（除非亏损严重）
    if 营业成本 and 营业收入 and 营业收入 > 0 and 营业成本 > 营业收入 * 1.5:
        warnings.append(f"营业成本({营业成本}) > 营业收入({营业收入})×1.5，可能提取错误")
        raw["营业成本"] = None

    # 检查 5: 如果没有净利润但有利润总额，标记警告
    if 净利润 is None and 利润总额 is not None:
        warnings.append(f"缺少净利润数据，只有利润总额({利润总额})，不能用利润总额-所得税费用代替")

    # 检查 6: 营业收入不应为负
    if 营业收入 is not None and 营业收入 < 0:
        warnings.append(f"营业收入为负({营业收入})，可能提取错误")
        raw["营业收入"] = None

    # 检查 7: 净利润/营业收入不应超过 100%
    if 净利润 and 营业收入 and 营业收入 > 0:
        ratio = 净利润 / 营业收入
        if ratio > 1.0:
            warnings.append(f"净利率={ratio:.1%} 超过100%，数据来源可能不一致，清空净利润")
            raw["净利润"] = None

    if warnings:
        print(f"[RADAR-VALIDATE] {'; '.join(warnings)}")

    return raw


def _compute_ratios_from_raw(raw: dict) -> dict:
    """从原始财务数据计算各项比率指标（Python 精确计算，替代 LLM 算术）。

    raw: LLM 提取的原始数据（金额，单位：元）
    返回: 与 compute_radar_scores 兼容的比率字典
    """
    metrics = {}

    # 盈利能力
    营业收入 = raw.get("营业收入")
    营业成本 = raw.get("营业成本")
    净利润 = raw.get("净利润")
    营业利润 = raw.get("营业利润")
    利润总额 = raw.get("利润总额")
    成本费用总额 = raw.get("成本费用总额")
    总资产 = raw.get("总资产")
    净资产 = raw.get("净资产")
    平均总资产 = raw.get("平均总资产") or 总资产
    平均净资产 = raw.get("平均净资产") or 净资产

    metrics["毛利率"] = _safe_div(
        (营业收入 - 营业成本) if (营业收入 and 营业成本) else None,
        营业收入
    )
    metrics["净利率"] = _safe_div(净利润, 营业收入)
    metrics["ROE"] = _safe_div(净利润, 平均净资产)
    metrics["营业利润率"] = _safe_div(营业利润, 营业收入)
    metrics["成本费用利润率"] = _safe_div(利润总额, 成本费用总额)

    # 资产质量
    平均存货 = raw.get("平均存货") or raw.get("存货")
    平均应收账款 = raw.get("平均应收账款") or raw.get("应收账款")
    经营活动现金流净额 = raw.get("经营活动现金流净额")

    metrics["资产周转率"] = _safe_div(营业收入, 平均总资产)
    metrics["存货周转率"] = _safe_div(营业成本, 平均存货)
    metrics["应收账款周转率"] = _safe_div(营业收入, 平均应收账款)
    metrics["现金回收率"] = _safe_div(经营活动现金流净额, 平均总资产)

    # 债务风险
    流动资产 = raw.get("流动资产")
    流动负债 = raw.get("流动负债")
    存货 = raw.get("存货")
    利息费用 = raw.get("利息费用")
    息税前利润 = raw.get("息税前利润")

    metrics["资产负债率"] = _safe_div(raw.get("负债总额") or (总资产 - 净资产 if 总资产 and 净资产 else None), 总资产)
    metrics["流动比率"] = _safe_div(流动资产, 流动负债)
    metrics["速动比率"] = _safe_div(
        (流动资产 - 存货) if (流动资产 is not None and 存货 is not None) else 流动资产,
        流动负债
    )
    metrics["利息保障倍数"] = _safe_div(息税前利润, 利息费用)
    metrics["现金流动负债比"] = _safe_div(经营活动现金流净额, 流动负债)

    # 经营增长
    上期营业收入 = raw.get("上期营业收入")
    上期净利润 = raw.get("上期净利润")
    上期总资产 = raw.get("上期总资产")
    期初所有者权益 = raw.get("期初所有者权益")

    metrics["营收增长率"] = _safe_div(
        (营业收入 - 上期营业收入) if (营业收入 and 上期营业收入) else None,
        上期营业收入
    )
    metrics["净利润增长率"] = _safe_div(
        (净利润 - 上期净利润) if (净利润 and 上期净利润) else None,
        上期净利润
    )
    metrics["总资产增长率"] = _safe_div(
        (总资产 - 上期总资产) if (总资产 and 上期总资产) else None,
        上期总资产
    )
    metrics["资本保值增值率"] = _safe_div(净资产, 期初所有者权益)

    # Altman Z-Score 相关
    留存收益 = raw.get("留存收益")
    营运资本 = raw.get("营运资本")

    metrics["营运资本比"] = _safe_div(营运资本, 总资产)
    metrics["留存收益比"] = _safe_div(留存收益, 总资产)
    metrics["EBIT资产比"] = _safe_div(息税前利润, 总资产)
    metrics["权益负债比"] = _safe_div(净资产, raw.get("负债总额") or (总资产 - 净资产 if 总资产 and 净资产 else None))

    # 过滤掉 None 值
    return {k: v for k, v in metrics.items() if v is not None}
