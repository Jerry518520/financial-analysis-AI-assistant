from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from financial_report_ai_assistant.services.rag_service import query_rag_with_source, RAG_NOT_FOUND, RAG_INDEX_MISSING, RAG_INDEX_BUILDING, get_current_pdf_hash
from financial_report_ai_assistant.services.ai_chat import get_llm
from financial_report_ai_assistant.services.financial_data_store import get_current_cached_data, set_cached_data
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import asyncio
import hashlib
import json
import re

from financial_report_ai_assistant.api.utils import extract_cited_pages

router = APIRouter()

# 雷达图数据缓存：避免每次请求都重新提取，也保证数据一致性
# key = pdf_hash, value = {"raw_data": dict, "industry": str, "ratios": dict}
_radar_data_cache: dict = {}
_radar_cache_lock = __import__('threading').Lock()

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
        "合并资产负债表 流动资产 流动负债 存货",
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

# 摘要专用：从 RAG 上下文中提取原始财务数据的 Prompt
SUMMARY_EXTRACTION_PROMPT = """你是一位金融数据提取专家。请从以下财报片段中提取【原始财务数据】（金额，单位：元），以严格JSON格式返回。
比率指标由系统自动计算，你只需要提取数字。

【检索到的财报片段】：
{context}

【数据使用规则（必须严格遵守）】：
1. 所有数据必须基于【合并报表】，禁止使用母公司报表数据
2. 营业收入和营业成本必须来自同一张表（合并利润表或主要会计数据表），禁止混合不同表格的数据
3. 净利润优先使用"归属于上市公司股东的净利润"，如无则用"净利润"
4. 禁止用"利润总额-所得税费用"代替净利润（利润表有其他调整项，这样算会出错）
5. 使用最新年度的数据
6. 金额直接提取原始数字，不要转换为小数或百分比
7. 【最重要】如果某个数据在片段中找不到或不确定，必须设为 null。宁可返回 null 也不要编造或估算任何数值
8. 禁止用示例中的数值填充——下面的示例仅展示格式，不是真实数据

【任务要求】：
输出必须包含以下14个字段，缺一不可，禁止省略任何字段：

1. "营业收入" — 合并利润表中的营业收入（元）
2. "营业成本" — 合并利润表中的营业成本（元）
3. "净利润" — 归属于上市公司股东的净利润（元）
4. "上期营业收入" — 上年同期营业收入（元）
5. "上期净利润" — 上年同期净利润（元）
6. "总资产" — 合并资产负债表中的资产总计-期末余额（元）
7. "上期总资产" — 合并资产负债表中的资产总计-期初余额/上年年末余额（元）
8. "负债总额" — 合并资产负债表中的负债合计（元）
9. "流动资产" — 合并资产负债表中的流动资产合计（元）
10. "流动负债" — 合并资产负债表中的流动负债合计（元）
11. "存货" — 合并资产负债表中的存货-期末余额（元）
12. "期初存货" — 合并资产负债表中的存货-期初余额/上年年末余额（元）
13. "基本每股收益" — 基本每股收益（元/股），直接从财报中提取，不要计算
14. "加权平均净资产收益率" — 加权平均净资产收益率（百分比数值，如 7.58 表示 7.58%），优先从财报中直接提取；如果财报未给出，设为 null，系统会自动计算

找不到的字段必须设为 null，禁止省略。

示例（仅展示格式，不是真实数据）：
{{"营业收入": 133895500000, "营业成本": 92149800000, "净利润": 5617700000, "上期营业收入": 121298800000, "上期净利润": 8424800000, "总资产": 217739400000, "上期总资产": 207325600000, "负债总额": 142098100000, "流动资产": 150000000000, "流动负债": 85000000000, "存货": 30000000000, "期初存货": 28000000000, "基本每股收益": 1.17, "加权平均净资产收益率": 7.58}}

严格按上述JSON格式输出，不要有任何其他文字。"""

# 上下文最大字符数限制（防止超出 DeepSeek 上下文窗口）
MAX_CONTEXT_CHARS = 30000

# 摘要提取必须包含的字段（用于验证和重试）
SUMMARY_REQUIRED_FIELDS = ["营业收入", "营业成本", "净利润", "总资产", "上期总资产", "负债总额",
                           "流动资产", "流动负债", "存货", "期初存货", "上期营业收入", "上期净利润",
                           "基本每股收益", "加权平均净资产收益率"]


def _parse_extraction_json(raw_response: str) -> dict:
    """从LLM响应中解析JSON，支持纯JSON和markdown包裹的JSON"""
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', raw_response)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    return {}


async def _extract_with_retry(context: str, max_retries: int = 2) -> dict:
    """提取财务数据，缺失字段自动重试补全。

    策略：
    1. 首次完整提取
    2. 检查缺失字段，针对性重试
    3. 合并结果（不覆盖已有值）
    """
    extraction_prompt = ChatPromptTemplate.from_template(SUMMARY_EXTRACTION_PROMPT)
    extraction_chain = extraction_prompt | get_llm() | StrOutputParser()

    # 首次提取
    raw_response = await asyncio.to_thread(extraction_chain.invoke, {"context": context})
    raw_data = _parse_extraction_json(raw_response)

    if not raw_data:
        return raw_data

    # 重试缺失字段
    for attempt in range(max_retries):
        missing = [f for f in SUMMARY_REQUIRED_FIELDS if f not in raw_data or raw_data[f] is None]
        if not missing:
            break

        print(f"🔄 第{attempt+1}次重试，补全缺失字段: {', '.join(missing)}")
        # 构造针对性重试prompt，只问缺失字段
        retry_context = context[:12000]  # 缩短上下文避免token浪费
        retry_prompt = f"""你是一位金融数据提取专家。上一次提取缺少以下字段：{', '.join(missing)}

请仅从以下财报片段中提取这些字段，以JSON格式返回。找不到的字段设为null。
金额单位：元，直接提取原始数字。

【财报片段】：
{retry_context}

严格按JSON格式输出，不要有任何其他文字。"""

        retry_response = await asyncio.to_thread(
            lambda p=retry_prompt: (ChatPromptTemplate.from_template("{query}") | get_llm() | StrOutputParser()).invoke({"query": p})
        )
        retry_data = _parse_extraction_json(retry_response)

        # 合并结果（不覆盖已有值）
        for k, v in retry_data.items():
            if k in SUMMARY_REQUIRED_FIELDS and (k not in raw_data or raw_data[k] is None):
                raw_data[k] = v

    return raw_data


def _compute_all_metrics(raw: dict) -> dict:
    """从原始数据计算所有财务指标（与对话路径统一计算口径）。

    返回格式化的指标字典，供概要和对话共同使用。
    """
    from financial_report_ai_assistant.services.financial_calculator import (
        calculate_margin, calculate_growth_rate, calculate_roe,
        calculate_debt_ratio, calculate_current_ratio, calculate_quick_ratio,
        calculate_turnover, calculate_inventory_turnover,
        format_percentage,
    )

    metrics = {}

    # 原始数据
    营业收入 = raw.get("营业收入")
    营业成本 = raw.get("营业成本")
    净利润 = raw.get("净利润")
    上期营业收入 = raw.get("上期营业收入")
    上期净利润 = raw.get("上期净利润")
    总资产 = raw.get("总资产")
    负债总额 = raw.get("负债总额")
    流动资产 = raw.get("流动资产")
    流动负债 = raw.get("流动负债")
    存货 = raw.get("存货")
    平均净资产 = raw.get("平均净资产") or raw.get("净资产")
    期初所有者权益 = raw.get("期初所有者权益")

    # 直接提取的字段（非计算）
    if raw.get("基本每股收益") is not None:
        # 保留足够精度（最多4位小数，去除尾部0）
        eps_val = raw['基本每股收益']
        eps_str = f"{eps_val:.4f}".rstrip('0').rstrip('.')
        metrics["EPS"] = f"{eps_str}元/股"
    if raw.get("加权平均净资产收益率") is not None:
        # 原始数据已是百分比形式（如 7.58 表示 7.58%），直接格式化，不再乘100
        metrics["ROE"] = f"{raw['加权平均净资产收益率']:.2f}%"
    elif 净利润 and 总资产 and 负债总额:
        # 财报未直接给出 ROE，用 Python 计算
        # 净资产 = 总资产 - 负债总额
        期末净资产 = 总资产 - 负债总额
        期初净资产 = raw.get("期初所有者权益") or (raw.get("上期总资产", 0) - raw.get("上期负债总额", 0) if raw.get("上期总资产") and raw.get("上期负债总额") else None)
        if 期末净资产 > 0:
            roe_value = calculate_roe(净利润, 期末净资产, 期初净资产)
            if roe_value is not None and not isinstance(roe_value, str):
                metrics["ROE"] = format_percentage(roe_value)
    if raw.get("总资产") is not None:
        metrics["总资产_亿元"] = f"{总资产 / 1e8:.2f}亿元"

    # 盈利能力
    if 营业收入 and 营业成本:
        metrics["毛利率"] = calculate_margin(营业收入 - 营业成本, 营业收入)
    if 净利润 and 营业收入:
        metrics["净利率"] = calculate_margin(净利润, 营业收入)

    # 同比增长
    if 营业收入 and 上期营业收入:
        metrics["营收增长率"] = calculate_growth_rate(营业收入, 上期营业收入)
    if 净利润 and 上期净利润:
        metrics["净利润增长率"] = calculate_growth_rate(净利润, 上期净利润)

    # 偿债能力
    if 负债总额 and 总资产:
        metrics["资产负债率"] = calculate_debt_ratio(负债总额, 总资产)
    if 流动资产 and 流动负债:
        metrics["流动比率"] = calculate_current_ratio(流动资产, 流动负债)
    if 流动资产 is not None and 存货 is not None and 流动负债:
        metrics["速动比率"] = calculate_quick_ratio(流动资产, 存货, 流动负债)

    # 运营能力
    if 营业收入 and 总资产:
        metrics["资产周转率"] = calculate_turnover(营业收入, 总资产, raw.get("上期总资产"))
    if 营业成本 and 存货:
        metrics["存货周转率"] = calculate_inventory_turnover(营业成本, 存货, raw.get("期初存货"))

    # 格式化
    RATIO_KEYS = {"流动比率", "速动比率", "资产周转率", "存货周转率"}
    formatted = {}
    for k, v in metrics.items():
        if isinstance(v, (int, float)):
            if k in RATIO_KEYS:
                formatted[k] = f"{v:.2f}"
            else:
                formatted[k] = format_percentage(v)
        else:
            formatted[k] = str(v)

    # 附带原始金额（同时保留原始数字和亿元格式）
    if 营业收入:
        formatted["营业收入"] = f"{营业收入:,.2f}元"
        formatted["营业收入_亿元"] = f"{营业收入 / 1e8:.2f}亿元"
    if 净利润:
        formatted["净利润"] = f"{净利润:,.2f}元"
        formatted["净利润_亿元"] = f"{净利润 / 1e8:.2f}亿元"
    if 营业成本:
        formatted["营业成本"] = f"{营业成本:,.2f}元"
        formatted["营业成本_亿元"] = f"{营业成本 / 1e8:.2f}亿元"
    if 总资产:
        formatted["总资产"] = f"{总资产:,.2f}元"

    return formatted


async def extract_and_cache_financial_data(context: str, pdf_hash: str = None) -> dict:
    """统一提取函数：一次性提取所有财务数据并缓存。

    这是所有数据路径的唯一入口，确保概要、对话、雷达图使用同一份数据。
    """
    # 检查是否已有缓存
    if pdf_hash:
        from financial_report_ai_assistant.services.financial_data_store import get_cached_data
        cached = get_cached_data(pdf_hash)
        if cached:
            print(f"📦 命中缓存: pdf_hash={pdf_hash[:8]}...")
            return cached

    print("📊 开始统一提取财务数据...")

    # 1. RAG检索获取更完整的上下文
    search_queries = FOCUS_QUERIES.get("general", [])
    contexts = []
    all_source_pages = set()
    for q in search_queries:
        result = await asyncio.to_thread(query_rag_with_source, q, 8, 0.3)
        ctx = result.get("context", "")
        if ctx and RAG_INDEX_MISSING not in ctx and RAG_NOT_FOUND not in ctx and RAG_INDEX_BUILDING not in ctx:
            contexts.append(ctx)
            all_source_pages.update(result.get("source_pages", []))

    if not contexts:
        # RAG无结果，用传入的context
        full_context = context[:MAX_CONTEXT_CHARS]
    else:
        full_context = "\n---\n".join(contexts)
        if len(full_context) > MAX_CONTEXT_CHARS:
            cut_pos = full_context.rfind("\n", 0, MAX_CONTEXT_CHARS)
            if cut_pos < MAX_CONTEXT_CHARS // 2:
                cut_pos = MAX_CONTEXT_CHARS
            full_context = full_context[:cut_pos]

    # 2. LLM提取原始数据（带重试）
    raw_data = await _extract_with_retry(full_context, max_retries=2)
    if not raw_data:
        print("⚠️ 统一提取失败：无法提取原始数据")
        return None

    # 调试：检查关键字段
    for f in ["流动资产", "流动负债", "存货", "期初存货"]:
        val = raw_data.get(f)
        print(f"   📊 提取结果: {f} = {val if val is not None else 'NULL'}")

    # 兜底：用正则从RAG检索的原始页面中提取资产负债表数据
    # 对于期初存货和上期总资产，始终用正则提取（LLM经常提取错误值或遗漏）
    missing_bs = [f for f in ["流动资产", "流动负债", "存货"] if raw_data.get(f) is None]
    # 期初存货：如果LLM没提取或值不合理，也加入提取列表
    if raw_data.get("期初存货") is None or raw_data.get("期初存货", 0) <= 0:
        missing_bs.append("期初存货")
    # 上期总资产：用于计算平均总资产（资产周转率）
    if raw_data.get("上期总资产") is None:
        missing_bs.append("上期总资产")
    if missing_bs:
        print(f"⚠️ 资产负债表字段缺失: {missing_bs}，尝试从RAG原始页面提取...")
        import re
        # 从RAG检索相关页面的原始内容
        bs_queries = ["流动资产合计", "流动负债合计", "存货", "存货 期初余额", "资产总计"]
        bs_contexts = []
        for q in bs_queries:
            try:
                result = await asyncio.to_thread(query_rag_with_source, q, 3, 0.3)
                ctx = result.get("context", "")
                if ctx and RAG_INDEX_MISSING not in ctx:
                    bs_contexts.append(ctx)
            except Exception:
                pass
        bs_text = "\n".join(bs_contexts)
        print(f"   📄 资产负债表上下文: {len(bs_text)} 字符, missing_bs={missing_bs}")
        # 调试：打印含"存货"的行
        for _line in bs_text.split('\n'):
            if '存货' in _line:
                print(f"   🔍 存货行: {repr(_line[:150])}")
        # 从原始页面文本中用正则提取（精确匹配表格格式 "| 字段 | 数值 |"）
        for field in missing_bs[:]:
            if field == "期初存货":
                # 特殊处理：从 "| 存货 | 期末值 | 期初值 |" 行提取第二个数值
                m = re.search(r'\|\s*存货\s*\|\s*([\d,]+\.?\d+)\s*\|\s*([\d,]+\.?\d+)', bs_text)
                if m:
                    try:
                        val = float(m.group(2).replace(",", ""))
                        if val > 10000:
                            raw_data["期初存货"] = val
                            missing_bs.remove(field)
                            print(f"   ✅ 正则提取成功: 期初存货 = {val}")
                    except ValueError:
                        pass
            elif field == "上期总资产":
                # 特殊处理：从 "| 资产总计 | 期末值 | 期初值 |" 行提取第二个数值
                m = re.search(r'\|\s*资产[总合]*计\s*\|\s*([\d,]+\.?\d+)\s*\|\s*([\d,]+\.?\d+)', bs_text)
                if m:
                    try:
                        val = float(m.group(2).replace(",", ""))
                        if val > 1000000:
                            raw_data["上期总资产"] = val
                            missing_bs.remove(field)
                            print(f"   ✅ 正则提取成功: 上期总资产 = {val}")
                    except ValueError:
                        pass
            else:
                # 优先匹配带"合计"的行，再匹配普通行
                # 表格格式: | 流动资产合计 | 2,375,622,050.59 | 2,358,409,139.66 |
                patterns = [
                    rf'\|\s*{field}合计\s*\|\s*([\d,]+\.?\d+)',  # | 流动资产合计 | 数值 |
                    rf'\|\s*{field}\s*\|\s*([\d,]+\.?\d+)',      # | 存货 | 数值 |
                ]
                for pat in patterns:
                    m = re.search(pat, bs_text)
                    if m:
                        try:
                            val = float(m.group(1).replace(",", ""))
                            if val > 10000:  # 合理值检查：资产负债表数值通常 > 1万
                                raw_data[field] = val
                                missing_bs.remove(field)
                                print(f"   ✅ 正则提取成功: {field} = {val}")
                                break
                        except ValueError:
                            pass

    # 3. 数据验证
    raw_data = _validate_raw_data(raw_data)

    # 4. Python精确计算所有指标
    computed_metrics = _compute_all_metrics(raw_data)

    # 5. 提取公司名称和报告期
    company_name = ""
    report_period = ""
    # 从上下文中尝试提取
    import re
    for line in full_context.split("\n")[:20]:
        if "公司" in line or "集团" in line:
            if not company_name:
                company_name = line.strip()[:30]
        if "年度报告" in line or "季度报告" in line:
            if not report_period:
                report_period = line.strip()[:30]

    # 6. 组装缓存数据
    cached_data = {
        "pdf_hash": pdf_hash or get_current_pdf_hash() or "",
        "raw_data": raw_data,
        "computed_metrics": computed_metrics,
        "source_pages": sorted(all_source_pages),
        "company_name": company_name,
        "report_period": report_period,
    }

    # 7. 缓存
    if pdf_hash:
        set_cached_data(pdf_hash, cached_data)

    non_null = sum(1 for v in raw_data.values() if v is not None)
    print(f"✅ 统一提取完成: {non_null}个原始字段, {len(computed_metrics)}个计算指标")

    return cached_data


def _inject_missing_data(summary: str, computed_data_str: str) -> str:
    """后处理：检查摘要是否包含所有已计算的数据，缺失则补充。

    策略：从 computed_data_str 中提取每个指标，检查摘要中是否包含其数值。
    如果缺失，在摘要末尾追加一个数据补充表。
    """
    import re

    # 解析 computed_data_str 中的指标和数值
    # 格式："- 毛利率: 31.28%" 或 "- 营业收入_亿元: 1338.95亿元"
    computed_items = []
    for line in computed_data_str.strip().split("\n"):
        line = line.strip()
        if line.startswith("- ") and ":" in line:
            key = line[2:line.index(":")].strip()
            value = line[line.index(":") + 1:].strip()
            computed_items.append((key, value))

    if not computed_items:
        print(f"⚠️ _inject_missing_data: computed_items为空，computed_data_str前200字: {computed_data_str[:200]}")
        return summary

    # 调试：打印所有computed_items
    print(f"🔍 _inject_missing_data: 共{len(computed_items)}项:")
    for k, v in computed_items:
        print(f"   - {k}: {v}")

    # 检查哪些指标在摘要中缺失
    missing = []
    summary_clean = summary.replace(",", "").replace(" ", "")
    print(f"🔍 _inject_missing_data: 共{len(computed_items)}项, 摘要长度={len(summary_clean)}")
    for key, value in computed_items:
        # 提取数值部分（去掉百分号、亿元等）
        value_clean = value.replace(",", "").replace(" ", "")
        # 【修复】必须同时包含指标名称和数值，才算真正包含
        # 避免"1.20"等短数字在页码/章节编号等位置被误匹配
        key_in = key in summary_clean
        val_in = value_clean in summary_clean
        if not key_in or not val_in:
            missing.append((key, value))
            print(f"   ❌ 缺失: {key}={value} (key_in={key_in}, val_in={val_in})")
        else:
            print(f"   ✅ 已有: {key}={value}")

    if not missing:
        return summary

    # 追加补充数据表
    supplement = "\n\n### 补充：系统精确计算的财务指标\n\n| 指标 | 数值 |\n| :--- | :--- |\n"
    for key, value in missing:
        supplement += f"| **{key}** | {value} |\n"
    supplement += "\n*以上数据由系统根据合并报表原始数据精确计算得出，与对话问答中的计算结果完全一致。*\n"

    print(f"📌 后处理：补充了 {len(missing)} 个缺失指标到摘要: {[k for k, v in missing]}")
    return summary + supplement


@router.post("/analyze/summary")
async def generate_report_summary(request: AnalysisRequest):
    """
    生成财报的核心摘要

    统一数据路径：
    1. 优先从缓存读取（上传时已提取的数据）
    2. 缓存未命中时走原有提取流程
    3. LLM 引用计算结果生成摘要（禁止自行计算）
    """
    # ===== Step 1: 优先从缓存读取 =====
    cached = get_current_cached_data()
    computed_data_str = ""
    raw_data = None
    all_source_pages = set()

    if cached and cached.get("computed_metrics"):
        print("📦 概要生成：命中缓存，使用统一数据")
        raw_data = cached.get("raw_data", {})
        computed_metrics = cached.get("computed_metrics", {})
        all_source_pages = set(cached.get("source_pages", []))

        # 格式化为 computed_data_str
        lines = []
        for k, v in computed_metrics.items():
            lines.append(f"- {k}: {v}")
        computed_data_str = "\n".join(lines)
    else:
        # ===== 降级：缓存未命中，走原有提取流程 =====
        print("⚠️ 概要生成：缓存未命中，走提取流程")
        search_queries = FOCUS_QUERIES.get(request.focus, FOCUS_QUERIES["general"])

        contexts = []
        for q in search_queries:
            result = await asyncio.to_thread(query_rag_with_source, q, 8, 0.3)
            ctx = result.get("context", "")
            if ctx and RAG_INDEX_MISSING not in ctx and RAG_NOT_FOUND not in ctx and RAG_INDEX_BUILDING not in ctx:
                contexts.append(ctx)
                all_source_pages.update(result.get("source_pages", []))

        if not contexts:
            return {"summary": "无法生成摘要：知识库尚未建立或未检索到有效信息。请先上传并解析财报。", "source_pages": []}

        full_context = "\n---\n".join(contexts)
        if len(full_context) > MAX_CONTEXT_CHARS:
            cut_pos = full_context.rfind("\n", 0, MAX_CONTEXT_CHARS)
            if cut_pos < MAX_CONTEXT_CHARS // 2:
                cut_pos = MAX_CONTEXT_CHARS
            full_context = full_context[:cut_pos]

        try:
            raw_data = await _extract_with_retry(full_context, max_retries=2)
            if raw_data and isinstance(raw_data, dict):
                raw_data = _validate_raw_data(raw_data)
                computed = _compute_summary_ratios(raw_data)
                if computed:
                    lines = []
                    for k, v in computed.items():
                        lines.append(f"- {k}: {v}")
                    computed_data_str = "\n".join(lines)
        except Exception as e:
            print(f"⚠️ 数据提取/计算失败: {e}")

    # ===== Step 2: RAG检索摘要上下文 =====
    search_queries = FOCUS_QUERIES.get(request.focus, FOCUS_QUERIES["general"])
    contexts = []
    for q in search_queries:
        result = await asyncio.to_thread(query_rag_with_source, q, 8, 0.3)
        ctx = result.get("context", "")
        if ctx and RAG_INDEX_MISSING not in ctx and RAG_NOT_FOUND not in ctx and RAG_INDEX_BUILDING not in ctx:
            contexts.append(ctx)
            all_source_pages.update(result.get("source_pages", []))

    full_context = "\n---\n".join(contexts) if contexts else ""
    if len(full_context) > MAX_CONTEXT_CHARS:
        cut_pos = full_context.rfind("\n", 0, MAX_CONTEXT_CHARS)
        if cut_pos < MAX_CONTEXT_CHARS // 2:
            cut_pos = MAX_CONTEXT_CHARS
        full_context = full_context[:cut_pos]

    # ===== Step 3: 生成摘要（使用精确计算的数据） =====
    focus_instructions = {
        "general": "请全面涵盖：核心财务数据表（含同比变化）、盈利能力分析、经营亮点、风险提示、关键财务健康信号（现金流/资产质量/债务风险）、未来展望。",
        "financial": "请重点分析：核心财务指标的本期值与上期值对比（用表格展示），盈利能力（毛利率、净利率、ROE）的变化趋势及原因，偿债能力（资产负债率、流动比率），运营效率（周转率）。",
        "risk": "请重点识别：财报中明确提及的风险因素（按重要性排列），财务健康信号（现金流是否覆盖净利润、应收账款和存货变化、债务水平），以及管理层对风险的应对措施。",
        "business": "请重点描述：业务概况与核心竞争力，本年度经营亮点与战略方向变化，管理层对未来的展望与资本开支计划，行业地位与市场份额变化。",
    }
    focus_hint = focus_instructions.get(request.focus, focus_instructions["general"])

    if computed_data_str:
        # 有精确计算数据：注入上下文，禁止 LLM 自行计算
        data_section = f"""

【系统已精确计算的财务指标（直接引用，禁止重新计算）】：
{computed_data_str}

以上数据由系统根据合并报表原始数据精确计算得出，与对话问答中的计算结果完全一致。
请在摘要中直接引用这些数据，禁止自行计算任何比率指标。"""
    else:
        # 降级：无精确计算数据，回到旧逻辑
        data_section = """

【数据使用规则（必须严格遵守）】：
- 营业收入和营业成本必须来自同一张表（合并利润表或主要会计数据表），禁止混合不同表格的数据
- 毛利率 = (营业收入 - 营业成本) / 营业收入，用合并报表数据计算。如果片段中没有营业成本数据，直接写"毛利率：见财报原文"，禁止估算
- 净利润优先使用"归属于上市公司股东的净利润"，如无则用"净利润"
- 禁止用利润总额代替净利润，禁止用营业总成本代替营业成本
- 如果某个指标在片段中确实找不到，直接省略该指标，不要编造或估算"""

    template = """你是一位资深的金融分析师。请根据以下从财报中检索到的片段，为用户生成一份结构清晰、有分析深度的【财报核心摘要】。

【重要】禁止任何开场白、问候语或自我介绍，直接从正文内容开始。

【输出格式要求（必须严格遵守）】：
第一行必须是公司名称和报告年份，加粗显示，格式为：**公司名称 YYYY年年度报告**
例如：**贵州茅台 2024年年度报告**
公司名称和年份必须从下方检索到的财报片段中提取，禁止编造。

【数据格式要求（必须严格遵守）】：
- 所有金额统一使用"亿元"为单位，保留2位小数，如"1338.95亿元"
- 所有比率统一使用百分比，保留2位小数，如"25.36%"
- 流动比率、速动比率使用倍数格式，保留2位小数，如"1.76"
- 表格中的数值必须与【系统已精确计算的财务指标】中的数据完全一致，禁止修改或四舍五入

【检索到的财报片段】：
{context}
{data_section}

【任务要求】：

1. **核心财务数据表**：用表格展示关键指标（营收、净利润、毛利率、净利率等），包含本期值、上期值、同比变化。{ratio_instruction}

2. **盈利能力分析**：毛利率和净利率的水平与变化趋势，ROE 表现，与上年同期对比说明变化原因。

3. **经营亮点**：简述本年度的业务进展、重大成就或战略方向变化。如果财报中有管理层对竞争优势的描述，提炼核心要点。

4. **风险提示**：从财报中提取明确提及的风险因素，按重要性排列。如果财报中有"可能面临的风险"等章节，优先引用。

5. **关键财务健康信号**：
   - 现金流质量：经营活动现金流净额是否覆盖净利润
   - 资产质量：应收账款和存货的变化趋势
   - 债务风险：资产负债率的变化

6. **未来展望**：管理层对未来的预期、战略规划、资本开支计划等。

【分析重点】：{focus_hint}

请使用 Markdown 格式输出，使用小标题（###）分隔不同部分。善用表格展示多期数据对比。
如果某些信息在片段中未找到，请直接省略该部分，不要编造。
保持语言专业、客观、精炼。

【数据来源要求】：
- 每个核心财务指标必须标注来源页码，格式为"（第X页）"
- 禁止编造任何数字，所有数据必须来自上述检索片段或系统已计算的数据"""

    ratio_instruction = (
        "直接引用【系统已精确计算的财务指标】中的**所有**数据，禁止自行计算。表格中必须包含所有已计算的指标（毛利率、净利率、资产负债率、流动比率、速动比率等），不得省略任何一项。"
        if computed_data_str
        else "如果有营业成本数据，计算毛利率等比率指标"
    )

    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | get_llm() | StrOutputParser()

    try:
        print("💡 正在生成摘要...")
        summary = await asyncio.to_thread(
            chain.invoke,
            {"context": full_context, "data_section": data_section,
             "ratio_instruction": ratio_instruction, "focus_hint": focus_hint},
        )

        # 后处理：检查摘要是否包含所有已计算的数据，缺失则补充
        if computed_data_str:
            summary = _inject_missing_data(summary, computed_data_str)

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
    # 与对话接口保持一致的简单关键词查询，确保检索到相同的 chunk
    # 对话的补充检索用的就是这些单个术语
    "净利润",
    "营业收入",
    "营业成本",
    "营业利润",
    "总资产",
    "负债总额",
    "净资产",
    "流动资产",
    "流动负债",
    "经营活动现金流",
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
    "期初存货": 43000000000,
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
    # 0. 优先检查统一缓存（上传时已提取的数据）
    unified_cached = get_current_cached_data()
    if unified_cached and unified_cached.get("raw_data"):
        print("📦 雷达图：命中统一缓存")
        from financial_report_ai_assistant.services.financial_calculator import compute_radar_scores
        raw_data = unified_cached["raw_data"]
        computed = _compute_ratios_from_raw(raw_data)
        if computed:
            industry = request.industry or "制造业"
            result = compute_radar_scores(computed, industry)
            result["extracted_metrics"] = computed
            result["source_pages"] = unified_cached.get("source_pages", [])
            result["cached"] = True
            return result

    # 0b. 检查雷达专用缓存
    pdf_hash = get_current_pdf_hash()
    if pdf_hash:
        with _radar_cache_lock:
            cached = _radar_data_cache.get(pdf_hash)
        if cached:
            # 使用缓存的原始数据重新计算（允许用户切换行业重新评分）
            from financial_report_ai_assistant.services.financial_calculator import compute_radar_scores
            industry = request.industry or cached["industry"]
            result = compute_radar_scores(cached["ratios"], industry)
            result["extracted_metrics"] = cached["ratios"]
            result["source_pages"] = cached.get("source_pages", [])
            result["cached"] = True
            return result

    # 1. RAG 检索（与对话接口一致的简单关键词查询）
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

    # 缓存提取结果，后续请求直接复用（保证数据一致性）
    if pdf_hash and raw_data:
        with _radar_cache_lock:
            _radar_data_cache[pdf_hash] = {
                "raw_data": raw_data,
                "industry": industry,
                "ratios": company_metrics,
                "source_pages": sorted(all_source_pages),
            }

    return result


def _compute_summary_ratios(raw: dict) -> dict:
    """从摘要提取的原始数据精确计算比率指标。

    使用与对话接口完全相同的 calculate_* 函数，保证计算结果一致。
    raw: LLM 提取的原始数据（金额，单位：元）
    返回: 计算好的比率指标字典
    """
    from financial_report_ai_assistant.services.financial_calculator import (
        calculate_margin, calculate_growth_rate,
        calculate_debt_ratio, calculate_current_ratio, calculate_quick_ratio,
    )

    metrics = {}

    营业收入 = raw.get("营业收入")
    营业成本 = raw.get("营业成本")
    净利润 = raw.get("净利润")
    上期营业收入 = raw.get("上期营业收入")
    上期净利润 = raw.get("上期净利润")
    总资产 = raw.get("总资产")
    负债总额 = raw.get("负债总额")
    流动资产 = raw.get("流动资产")
    流动负债 = raw.get("流动负债")
    存货 = raw.get("存货")

    # 盈利能力（与对话工具完全一致的计算函数）
    if 营业收入 and 营业成本:
        metrics["毛利率"] = calculate_margin(营业收入 - 营业成本, 营业收入)
    if 净利润 and 营业收入:
        metrics["净利率"] = calculate_margin(净利润, 营业收入)

    # 同比增长
    if 营业收入 and 上期营业收入:
        metrics["营收增长率"] = calculate_growth_rate(营业收入, 上期营业收入)
    if 净利润 and 上期净利润:
        metrics["净利润增长率"] = calculate_growth_rate(净利润, 上期净利润)

    # 偿债能力（与对话工具完全一致的计算函数）
    if 负债总额 and 总资产:
        metrics["资产负债率"] = calculate_debt_ratio(负债总额, 总资产)
    if 流动资产 and 流动负债:
        metrics["流动比率"] = calculate_current_ratio(流动资产, 流动负债)
    if 流动资产 is not None and 存货 is not None and 流动负债:
        metrics["速动比率"] = calculate_quick_ratio(流动资产, 存货, 流动负债)

    # 格式化为百分比字符串，方便摘要 prompt 直接引用
    # 流动比率和速动比率是倍数（如1.76），不是百分比，需要特殊处理
    RATIO_KEYS = {"流动比率", "速动比率"}
    formatted = {}
    from financial_report_ai_assistant.services.financial_calculator import format_percentage
    for k, v in metrics.items():
        if isinstance(v, (int, float)):
            if k in RATIO_KEYS:
                formatted[k] = f"{v:.2f}"
            else:
                formatted[k] = format_percentage(v)
        else:
            formatted[k] = str(v)

    # 附带原始金额（亿元），供摘要展示
    if 营业收入:
        formatted["营业收入_亿元"] = f"{营业收入 / 1e8:.2f}亿元"
    if 净利润:
        formatted["净利润_亿元"] = f"{净利润 / 1e8:.2f}亿元"
    if 营业成本:
        formatted["营业成本_亿元"] = f"{营业成本 / 1e8:.2f}亿元"
    if 上期营业收入:
        formatted["上期营业收入_亿元"] = f"{上期营业收入 / 1e8:.2f}亿元"
    if 上期净利润:
        formatted["上期净利润_亿元"] = f"{上期净利润 / 1e8:.2f}亿元"
    if 总资产:
        formatted["总资产_亿元"] = f"{总资产 / 1e8:.2f}亿元"

    return formatted


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
    """从原始财务数据计算各项比率指标。

    使用与对话接口完全相同的 calculate_* 函数，保证计算结果一致。
    raw: LLM 提取的原始数据（金额，单位：元）
    返回: 与 compute_radar_scores 兼容的比率字典
    """
    from financial_report_ai_assistant.services.financial_calculator import (
        calculate_margin, calculate_roe, calculate_growth_rate,
        calculate_debt_ratio, calculate_current_ratio, calculate_quick_ratio,
        calculate_turnover, calculate_inventory_turnover, calculate_receivables_turnover,
    )

    metrics = {}

    # 原始数据提取
    营业收入 = raw.get("营业收入")
    营业成本 = raw.get("营业成本")
    净利润 = raw.get("净利润")
    营业利润 = raw.get("营业利润")
    利润总额 = raw.get("利润总额")
    成本费用总额 = raw.get("成本费用总额")
    总资产 = raw.get("总资产")
    净资产 = raw.get("净资产")
    负债总额 = raw.get("负债总额")
    平均总资产 = raw.get("平均总资产") or 总资产
    平均净资产 = raw.get("平均净资产") or 净资产
    平均存货 = raw.get("期初存货") or raw.get("存货")
    平均应收账款 = raw.get("平均应收账款") or raw.get("应收账款")
    流动资产 = raw.get("流动资产")
    流动负债 = raw.get("流动负债")
    存货 = raw.get("存货")
    经营活动现金流净额 = raw.get("经营活动现金流净额")
    利息费用 = raw.get("利息费用")
    息税前利润 = raw.get("息税前利润")
    上期营业收入 = raw.get("上期营业收入")
    上期净利润 = raw.get("上期净利润")
    上期总资产 = raw.get("上期总资产")
    期初所有者权益 = raw.get("期初所有者权益")

    # ===== 盈利能力（与对话工具完全一致的计算函数） =====
    if 营业收入 and 营业成本:
        metrics["毛利率"] = calculate_margin(营业收入 - 营业成本, 营业收入)
    if 净利润 and 营业收入:
        metrics["净利率"] = calculate_margin(净利润, 营业收入)
    if 净利润 and 平均净资产:
        metrics["ROE"] = calculate_roe(净利润, 平均净资产, 期初所有者权益)
    if 营业利润 and 营业收入:
        metrics["营业利润率"] = calculate_margin(营业利润, 营业收入)
    if 利润总额 and 成本费用总额:
        metrics["成本费用利润率"] = calculate_margin(利润总额, 成本费用总额)

    # ===== 资产质量 =====
    if 营业收入 and 平均总资产:
        metrics["资产周转率"] = calculate_turnover(营业收入, 总资产, raw.get("上期总资产"))
    if 营业成本 and 平均存货:
        metrics["存货周转率"] = calculate_inventory_turnover(营业成本, raw.get("存货"), raw.get("期初存货"))
    if 营业收入 and 平均应收账款:
        metrics["应收账款周转率"] = calculate_receivables_turnover(营业收入, raw.get("应收账款"), raw.get("平均应收账款"))
    if 经营活动现金流净额 and 平均总资产:
        metrics["现金回收率"] = _safe_div(经营活动现金流净额, 平均总资产)

    # ===== 债务风险 =====
    effective负债 = 负债总额 or (总资产 - 净资产 if 总资产 and 净资产 else None)
    if effective负债 and 总资产:
        metrics["资产负债率"] = calculate_debt_ratio(effective负债, 总资产)
    if 流动资产 and 流动负债:
        metrics["流动比率"] = calculate_current_ratio(流动资产, 流动负债)
    if 流动资产 is not None and 存货 is not None and 流动负债:
        metrics["速动比率"] = calculate_quick_ratio(流动资产, 存货, 流动负债)
    if 息税前利润 and 利息费用:
        metrics["利息保障倍数"] = _safe_div(息税前利润, 利息费用)
    if 经营活动现金流净额 and 流动负债:
        metrics["现金流动负债比"] = _safe_div(经营活动现金流净额, 流动负债)

    # ===== 经营增长 =====
    if 营业收入 and 上期营业收入:
        metrics["营收增长率"] = calculate_growth_rate(营业收入, 上期营业收入)
    if 净利润 and 上期净利润:
        metrics["净利润增长率"] = calculate_growth_rate(净利润, 上期净利润)
    if 总资产 and 上期总资产:
        metrics["总资产增长率"] = calculate_growth_rate(总资产, 上期总资产)
    if 净资产 and 期初所有者权益:
        metrics["资本保值增值率"] = _safe_div(净资产, 期初所有者权益)

    # Altman Z-Score 相关（保留给 Z-Score 计算）
    留存收益 = raw.get("留存收益")
    营运资本 = raw.get("营运资本")
    metrics["营运资本比"] = _safe_div(营运资本, 总资产)
    metrics["留存收益比"] = _safe_div(留存收益, 总资产)
    metrics["EBIT资产比"] = _safe_div(息税前利润, 总资产)
    metrics["权益负债比"] = _safe_div(净资产, effective负债)

    # 过滤掉 None 值
    return {k: v for k, v in metrics.items() if v is not None}
