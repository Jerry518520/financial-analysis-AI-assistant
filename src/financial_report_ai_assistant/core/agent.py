# 文件: src/financial_report_ai_assistant/core/agent.py
"""
Agent 核心模块 — ReAct 模式（原生 Function Calling）

架构：
  agent_node (LLM 意图识别 + 工具调用)
      ↓ 需要继续
  agent_node (循环)
      ↓ 完成
  answer_node (LLM 生成最终回答)

工具层保持 19 个财务计算工具不变。
LLM 通过 DeepSeek 原生 Function Calling 选择并调用工具，
无需手写 JSON 解析，稳定性大幅提升。
"""

from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from typing import TypedDict, List, Annotated
import operator
import os
import re
from dotenv import load_dotenv
from financial_report_ai_assistant.services.financial_calculator import (
    calculate_growth_rate, calculate_margin, calculate_roe, format_percentage,
    calculate_debt_ratio, calculate_current_ratio, calculate_quick_ratio,
    calculate_eps, calculate_pe, calculate_turnover, calculate_inventory_turnover,
    calculate_dividend_yield, analyze_trend, analyze_yoy, compare_to_industry,
    generate_chart_data, calculate_avg, calculate_max, calculate_min, calculate_variance,
    get_industry_benchmark, list_industries, list_industry_metrics
)

load_dotenv()

MAX_ITERATIONS = 5


# ==================== 工具定义（19 个，保持不变） ====================

@tool
def tool_calculate_growth_rate(current: float, previous: float) -> str:
    """计算同比增长率。输入本期数值和上期数值。"""
    res = calculate_growth_rate(current, previous)
    return format_percentage(res)

@tool
def tool_calculate_margin(profit: float, revenue: float) -> str:
    """计算利润率（毛利率、净利率）。输入利润和营收。"""
    res = calculate_margin(profit, revenue)
    return format_percentage(res)

@tool
def tool_calculate_roe(net_income: float, equity: float, beginning_equity: float = None) -> str:
    """计算净资产收益率 (ROE)。输入净利润和期末净资产；如有期初净资产也请传入，系统会自动使用平均净资产口径。"""
    res = calculate_roe(net_income, equity, beginning_equity)
    return format_percentage(res)

@tool
def tool_calculate_eps(net_income: float, shares_outstanding: float) -> str:
    """计算每股收益 (EPS)。输入净利润和总股本（万股或亿股）。"""
    res = calculate_eps(net_income, shares_outstanding)
    if isinstance(res, str):
        return res
    return f"{res:.2f} 元/股"

@tool
def tool_calculate_pe(price_per_share: float, eps: float) -> str:
    """计算市盈率 (PE)。输入每股股价和每股收益。"""
    res = calculate_pe(price_per_share, eps)
    if isinstance(res, str):
        return res
    return f"{res:.2f} 倍"

@tool
def tool_calculate_debt_ratio(total_liabilities: float, total_assets: float) -> str:
    """计算资产负债率。输入负债总额和资产总额。"""
    res = calculate_debt_ratio(total_liabilities, total_assets)
    return format_percentage(res)

@tool
def tool_calculate_current_ratio(current_assets: float, current_liabilities: float) -> str:
    """计算流动比率。输入流动资产和流动负债。"""
    res = calculate_current_ratio(current_assets, current_liabilities)
    if isinstance(res, str):
        return res
    return f"{res:.2f}"

@tool
def tool_calculate_quick_ratio(current_assets: float, inventory: float, current_liabilities: float) -> str:
    """计算速动比率。输入流动资产、存货和流动负债。"""
    res = calculate_quick_ratio(current_assets, inventory, current_liabilities)
    if isinstance(res, str):
        return res
    return f"{res:.2f}"

@tool
def tool_calculate_turnover(revenue: float, total_assets: float) -> str:
    """计算资产周转率。输入营业收入和总资产。"""
    res = calculate_turnover(revenue, total_assets)
    if isinstance(res, str):
        return res
    return f"{res:.2f} 次"

@tool
def tool_calculate_inventory_turnover(cogs: float, inventory: float, beginning_inventory: float = None) -> str:
    """计算存货周转率。输入营业成本和期末存货金额；如有期初存货也请传入，系统会自动使用平均存货口径。"""
    res = calculate_inventory_turnover(cogs, inventory, beginning_inventory)
    if isinstance(res, str):
        return res
    return f"{res:.2f} 次"

@tool
def tool_calculate_dividend_yield(dividend_per_share: float, price_per_share: float) -> str:
    """计算股息率。输入每股股息和每股股价。"""
    res = calculate_dividend_yield(dividend_per_share, price_per_share)
    return format_percentage(res)

@tool
def tool_analyze_trend(values: list) -> str:
    """分析多年趋势。输入多年数据列表，如 [100, 120, 150]。"""
    res = analyze_trend(values)
    return str(res)

@tool
def tool_analyze_yoy(current: float, previous: float) -> str:
    """进行同比分析。输入本期数值和上期数值。"""
    res = analyze_yoy(current, previous)
    return str(res)

@tool
def tool_compare_to_industry(value: float, industry_avg: float) -> str:
    """与行业平均对比。输入公司数值和行业平均值。"""
    res = compare_to_industry(value, industry_avg)
    return str(res)

@tool
def tool_generate_chart_data(years: list, values: list, metric_name: str = "指标") -> str:
    """生成图表数据。输入年份列表和数值列表，如 years=[2021,2022,2023], values=[100,120,150]。"""
    res = generate_chart_data(years, values, metric_name)
    return str(res)

@tool
def tool_calculate_avg(values: list) -> str:
    """计算平均值。输入数值列表。"""
    res = calculate_avg(values)
    return str(res)

@tool
def tool_calculate_max(values: list) -> str:
    """计算最大值。输入数值列表。"""
    res = calculate_max(values)
    return str(res)

@tool
def tool_calculate_min(values: list) -> str:
    """计算最小值。输入数值列表。"""
    res = calculate_min(values)
    return str(res)

@tool
def tool_calculate_variance(values: list) -> str:
    """计算方差（衡量波动性）。输入数值列表。"""
    res = calculate_variance(values)
    return str(res)


@tool
def tool_get_industry_benchmark(industry: str, metric: str) -> str:
    """查询行业基准值。输入行业名称（如"制造业"、"科技/互联网"、"医药"等）和指标名称（如"毛利率"、"净利率"、"ROE"等）。可用行业：制造业、科技/互联网、金融业、零售/消费品、能源、医药、房地产。注意：数据为近似参考值，非权威数据源。"""
    result = get_industry_benchmark(industry, metric)
    if result is None:
        available = list_industries()
        return f"未找到 {industry} 的 {metric} 基准数据。可用行业: {', '.join(available)}"
    return f"{industry}行业 {metric} 平均水平: {result}（注：此为近似参考值，非权威数据源）"


@tool
def tool_list_industries() -> str:
    """列出所有可用的行业分类。当用户问行业对比但未指定行业时使用。"""
    industries = list_industries()
    return f"可用行业: {', '.join(industries)}"


def get_tools():
    """返回财务计算工具列表（含行业基准查询）"""
    return [
        tool_calculate_growth_rate,
        tool_calculate_margin,
        tool_calculate_roe,
        tool_calculate_eps,
        tool_calculate_pe,
        tool_calculate_debt_ratio,
        tool_calculate_current_ratio,
        tool_calculate_quick_ratio,
        tool_calculate_turnover,
        tool_calculate_inventory_turnover,
        tool_calculate_dividend_yield,
        tool_analyze_trend,
        tool_analyze_yoy,
        tool_compare_to_industry,
        tool_generate_chart_data,
        tool_calculate_avg,
        tool_calculate_max,
        tool_calculate_min,
        tool_calculate_variance,
        tool_get_industry_benchmark,
        tool_list_industries,
    ]


def create_llm():
    """创建 LLM 实例"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("⚠️ Warning: DEEPSEEK_API_KEY not found.")
        return None
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=api_key,
        base_url="https://api.deepseek.com",
        temperature=0.1,
    )


# ==================== Agent State ====================

class AgentState(TypedDict):
    question: str
    context: str
    messages: Annotated[list, operator.add]  # LangChain Message 对象列表
    tool_results: Annotated[list[str], operator.add]  # 工具结果文本列表
    final_answer: str
    iteration: int


# ==================== 工具映射表 ====================

_TOOL_MAP: dict = {}  # 工具名 → 工具函数

_NUM_PATTERN = re.compile(r'-?[\d,]+\.?\d*')

def _safe_float(value) -> float | None:
    """从数值或字符串中安全提取 float。LLM 可能传 '100万'、'15.5%' 等格式。"""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        m = _NUM_PATTERN.search(value.replace(',', ''))
        if m:
            try:
                return float(m.group().replace(',', ''))
            except ValueError:
                pass
    return None

def _validate_tool_args(tool_name: str, tool_args: dict) -> dict:
    """校验工具参数：确保数值参数是有效的 float，列表参数是有效的 list[float]。
    字符串参数（如行业名称）直接透传，由工具自身的 Pydantic 模型校验。"""
    validated = {}
    for key, value in tool_args.items():
        if value is None:
            continue
        if isinstance(value, list):
            nums = [n for item in value if (n := _safe_float(item)) is not None]
            if nums:
                validated[key] = nums
        elif isinstance(value, str):
            n = _safe_float(value)
            if n is not None:
                validated[key] = n
            else:
                # 非数值字符串（如行业名称），直接透传给工具
                validated[key] = value
        else:
            n = _safe_float(value)
            if n is not None:
                validated[key] = n
    return validated


def _get_tool_map():
    """懒加载工具映射表"""
    global _TOOL_MAP
    if not _TOOL_MAP:
        for tool in get_tools():
            _TOOL_MAP[tool.name] = tool
    return _TOOL_MAP


# ==================== Agent 节点 ====================

def agent_node(state: AgentState):
    """Agent 核心节点：意图识别 + 工具调用（原生 Function Calling）
    
    流程：
    1. 构建 system prompt（包含背景信息和工具调用历史）
    2. 调用 LLM（bind_tools 绑定 19 个工具）
    3. 如果 LLM 返回 tool_calls → 执行工具，记录结果，继续循环
    4. 如果 LLM 返回纯文本 → 任务完成，转到 answer_node
    """
    llm = create_llm()
    if not llm:
        return {"final_answer": "Agent 初始化失败，请检查 API Key。", "iteration": state.get("iteration", 0)}

    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)

    iteration = state.get("iteration", 0)

    # 硬上限保护
    if iteration >= MAX_ITERATIONS:
        return {"final_answer": "", "iteration": iteration}

    # 构建 system prompt
    system_text = f"""你是一位专业的金融分析师助手。用户提出了一个财务问题，你需要：
1. 分析背景信息中是否包含回答问题所需的数值数据
2. 如果需要计算，调用相应的财务工具
3. 如果背景信息中没有相关数据，直接说明"财报中未找到相关数据"，不要调用任何工具
4. 如果背景信息中包含"[注：本页包含图片/图表]"标记，说明该页部分数据以图形形式呈现无法自动提取，应在回答中说明数据来源受限

⚠️ 重要规则：
- 参数必须是具体的数字，禁止传表达式或 null
- 如果找不到某个参数的数据，直接用自然语言回答，不要调用工具
- 每次最多调用 2 个工具
- 【关键】优先使用历史对话中已计算的数据，避免重复计算
- 【数据校验】所有数值必须来自背景信息原文，禁止编造或推测任何数字
- 【来源标注】回答中引用的每个数据必须标注来源页码，格式为"根据第X页数据，XXX为YYY"。每个数据片段前已标注[来源：第X页]，请直接使用该页码，不要自行推断
- 【数据优先级】当背景信息中同时包含合并报表和母公司报表数据时，必须优先使用合并报表数据进行计算和分析
- 【直接引用优先】如果背景信息中直接给出了用户询问的指标数值（如每股收益EPS、每股净资产、市盈率等），直接引用该数值，不要尝试用公式计算。只有当背景信息中没有直接给出该指标时，才调用计算工具
- 【衍生指标计算】以下指标通常需要计算，如果背景信息中未直接给出，应使用工具计算：
  - 净利率 = 净利润 / 营业收入（使用 tool_calculate_margin）
  - 资产周转率 = 营业收入 / 总资产（使用 tool_calculate_turnover）
  - 存货周转率 = 营业成本 / 存货（使用 tool_calculate_inventory_turnover，同时传入期初存货以使用平均口径；如无期初数据则回退到简化口径）
  - EPS = 净利润 / 总股本（使用 tool_calculate_eps），但如果背景信息中已直接给出"基本每股收益"或"稀释每股收益"则直接引用
  - ROE = 净利润 / 平均净资产（使用 tool_calculate_roe，同时传入期初净资产以使用平均口径；如无期初数据则回退到简化口径）
  - 速动比率 = (流动资产 - 存货) / 流动负债（使用 tool_calculate_quick_ratio）
- 【行业对比】当用户问"行业对比"、"行业平均水平"时：
  1. 先用 tool_list_industries 查看可用行业
  2. 根据公司所属行业，用 tool_get_industry_benchmark 查询各指标的行业平均值
  3. 再用 tool_compare_to_industry 将公司数据与行业平均值对比
  4. 如果无法确定公司所属行业，先问用户或根据业务特征推断
  5. 回答中必须注明"行业数据为近似参考值，非权威数据源，仅供方向性对比"
- 【多期数据年份标注】当财务数据包含多期（如本期/上期、2025年/2024年）时：
  - 财务报表中左边/前面的列是本期（较新年份），右边/后面的列是上期（较旧年份）
  - 回答时必须准确标注每个数值对应的年份，如"2025年为XX，2024年为XX"
  - 禁止将本期数值标注为上期年份，或将上期数值标注为本期年份
- 【数据完整性】当背景信息中存在多个匹配项时（如多年数据、分板块数据、多个期间对比），必须全部列出，不得只挑其中一个回答

【背景信息】（包含当前文档和历史对话数据）：
{state['context']}

【已完成的工具调用结果】（当前对话内）：
{_format_tool_results(state.get('tool_results', []))}

【数据复用指南】：
1. 如果用户问"刚才计算的XXX是多少"或"之前的XXX"，从历史对话记录中找到对应数值
2. 如果历史回答中已经计算过毛利率、净利率等指标，直接使用该数值，不要重新调用工具
3. 如果当前问题需要前置计算结果（如计算ROE需要先知道净利润和净资产），检查上下文中是否已有这些值
4. 表格数据中的数值可以直接引用，格式为"根据第X页表格数据，XXX为YYY"
"""

    # 合并历史消息（不要伪造 tool_calls 消息，历史工具结果已在 system prompt 里）
    messages = [
        {"role": "system", "content": system_text},
        {"role": "user", "content": state["question"]},
    ]

    response = llm_with_tools.invoke(messages)

    # 检查是否有 tool_calls（原生 Function Calling）
    if response.tool_calls:
        new_results = []
        new_messages = []

        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]

            tool_map = _get_tool_map()
            if tool_name not in tool_map:
                new_results.append(f"[未知工具] {tool_name}")
                print(f"⚠️ 未知工具: {tool_name}")
                continue

            # 校验参数：确保数值类型正确，防止 LLM 传入字符串/null
            validated_args = _validate_tool_args(tool_name, tool_args)
            if not validated_args:
                new_results.append(f"[工具调用跳过] {tool_name}: 参数校验失败，无有效数值参数")
                print(f"⚠️ 工具参数校验失败: {tool_name}({tool_args})")
                continue

            try:
                result = tool_map[tool_name].invoke(validated_args)
                new_results.append(f"[工具调用] {tool_name}({tool_args}) → {result}")
                print(f"🔧 工具调用成功: {tool_name}({tool_args}) → {result}")
            except Exception as e:
                new_results.append(f"[工具调用失败] {tool_name}: {str(e)}")
                print(f"❌ 工具调用失败: {tool_name}: {e}")

        return {
            "tool_results": new_results,
            "iteration": iteration + 1,
        }
    else:
        # LLM 没有调用工具 → 直接给出答案（可能是"未找到数据"或简单推理）
        if response.content.strip():
            # 如果有内容，直接作为最终答案
            return {
                "final_answer": response.content.strip(),
                "iteration": iteration,
            }
        else:
            # 空回答，停止循环让 answer_node 生成
            return {
                "iteration": iteration,
            }


def _format_tool_results(results: list[str]) -> str:
    """格式化工具结果列表为文本"""
    if not results:
        return "无"
    return "\n".join(results)


def should_continue_edge(state: AgentState) -> str:
    """判断是否继续循环"""
    if state.get("iteration", 0) >= MAX_ITERATIONS:
        return "end"
    # 如果有 final_answer，说明 agent_node 已经给出答案
    if state.get("final_answer", ""):
        return "end"
    # 如果没有 final_answer 且有工具结果，继续循环
    return "continue"


def answer_node(state: AgentState):
    """生成最终回答"""
    llm = create_llm()
    if not llm:
        return {"final_answer": "Agent 初始化失败，请检查 API Key。"}

    context = state.get("context", "")
    tool_results = state.get("tool_results", [])
    final_answer = state.get("final_answer", "")

    # 如果 agent_node 已经生成了答案（如"未找到数据"），直接返回
    if final_answer:
        return {}

    answer_prompt = f"""你是一位专业的金融分析师。请根据以下信息生成最终回答。

【用户问题】：{state['question']}

【背景信息】：
{context}

【工具执行结果】：
{_format_tool_results(tool_results)}

请生成一个完整、专业的回答。回答要求：
1. 直接回答用户的问题，不要有任何开场白、问候语或自我介绍
2. 禁止以"好的"、"作为一名金融分析师"、"我将..."等开头，第一句话就是实质性内容
3. 包含具体的数值和计算结果，每个数据必须来自【背景信息】或【工具执行结果】，禁止编造任何数字
4. 如有需要，给出分析和建议
5. 使用 Markdown 格式
6. 【关键】如果背景信息和工具结果中没有足够的数据回答问题，必须明确说明"财报中未找到相关数据"，禁止推测或编造
7. 所有引用的数值必须标注来源页码，格式为"根据第X页数据，XXX为YYY"。每个数据片段前已标注[来源：第X页]，请直接使用该页码
8. 【数据优先级】当同时存在合并报表和母公司报表数据时，必须优先使用合并报表数据
9. 【直接引用优先】如果背景信息中直接给出了用户询问的指标数值（如每股收益EPS、每股净资产等），直接引用该数值，不要尝试用公式重新计算
10. 所有章节标题统一使用 Markdown 二级标题格式，如：## 一、债务结构与规模，而不是直接写"一、债务结构与规模"
11. 【多期数据年份标注】当财务数据包含多期时，必须准确标注每个数值对应的年份。财务报表中左边/前面的列是本期（较新年份），右边/后面的列是上期（较旧年份），禁止将两年数据互换
12. 【数据完整性】当背景信息中存在多个匹配项时（如多年数据、分板块数据、多个期间对比），必须全部列出，不得只挑其中一个回答
"""

    response = llm.invoke(answer_prompt)
    return {"final_answer": response.content}


# ==================== 构建工作流图 ====================

def build_agent_graph():
    """构建 Agent 工作流图（ReAct 模式：agent ↔ 循环 → answer）"""
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", agent_node)
    workflow.add_node("answer", answer_node)

    workflow.set_entry_point("agent")

    workflow.add_conditional_edges(
        "agent",
        should_continue_edge,
        {
            "continue": "agent",
            "end": "answer"
        }
    )

    workflow.add_edge("answer", END)

    return workflow.compile(checkpointer=None)


_agent_graph = None

def create_financial_agent():
    """获取/创建 Agent 单例"""
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph


def run_agent_query(query: str, context: str = ""):
    """运行 Agent 查询"""
    import time
    agent = create_financial_agent()
    if not agent:
        return "Agent 初始化失败，请检查 API Key。"

    try:
        initial_state = {
            "question": query,
            "context": context,
            "messages": [],
            "tool_results": [],
            "final_answer": "",
            "iteration": 0,
        }

        print(f"🤖 Agent 开始执行 | 问题: {query[:50]}... | 上下文长度: {len(context)} 字符")
        start_time = time.time()

        result = agent.invoke(initial_state, {"recursion_limit": MAX_ITERATIONS * 3 + 10})

        elapsed = time.time() - start_time
        final_answer = result.get("final_answer", "")
        print(f"✅ Agent 执行完成 | 耗时: {elapsed:.1f}s | 回答长度: {len(final_answer)} 字符 | 迭代: {result.get('iteration', 0)}")

        if not final_answer.strip():
            print(f"⚠️ Agent 返回空回答！tool_results={result.get('tool_results', [])}")
            return "⚠️ Agent 未能生成有效回答。请稍后重试。"

        return final_answer

    except Exception as e:
        error_msg = str(e)
        if "recursion_limit" in error_msg.lower():
            return "⚠️ 分析超时。请尝试将问题拆分为更具体的子问题重新提问。"
        return f"Agent 执行出错: {error_msg}"


# ==================== 轻量级查询（简单问题快速通道） ====================

import re as _re

_SIMPLE_QUERY_PATTERNS = [
    r"是多少", r"有多少", r"多少", r"是什么", r"有哪些",
    r"列出", r"写出来", r"给出",
    r"营收", r"收入", r"利润", r"净利润", r"毛利",
    r"资产", r"负债", r"现金流", r"现金",
    r"毛利率", r"资产负债率", r"流动比率",
    r"股息",
]

_NEEDS_AGENT_PATTERNS = [
    r"EPS", r"PE", r"ROE", r"ROA",
    r"影响", r"原因", r"为什么", r"前景", r"风险", r"评估",
    r"分析", r"对比", r"趋势", r"预测", r"建议", r"策略", r"综合", r"总结",
    r"同比增长", r"环比", r"增长率",
    r"盈利能力", r"偿债能力", r"运营能力",
    r"每股", r"股本",
    r"净利率", r"速动比率", r"周转率", r"资产周转率", r"存货周转率",
    r"行业",
]

def is_simple_query(question: str) -> bool:
    """判断问题是否为简单查询（不需要工具调用）"""
    q = question.strip()
    if len(q) > 50:
        return False
    for pattern in _NEEDS_AGENT_PATTERNS:
        if _re.search(pattern, q):
            return False
    for pattern in _SIMPLE_QUERY_PATTERNS:
        if _re.search(pattern, q):
            return True
    return False

def run_lightweight_query(query: str, context: str = "") -> str:
    """轻量级查询：单次 LLM 调用 + RAG 上下文，适合简单事实性问题
    
    【注意】轻量级查询也支持历史数据复用，context 中已包含历史对话记录
    """
    from financial_report_ai_assistant.services.ai_chat import get_llm
    llm = get_llm()

    prompt = f"""你是一位专业的金融分析师。请根据以下财报背景信息，直接回答用户的问题。

【背景信息】（包含当前文档和历史对话数据）：
{context}

【用户问题】：{query}

回答要求：
1. 直接回答，不要有任何开场白、问候语或自我介绍
2. 禁止以"好的"、"作为一名金融分析师"、"我将..."等开头
3. 如果背景信息中没有相关数据，请如实告知"财报中未找到相关数据"，禁止编造任何数字
4. 包含具体的数值（如有），每个数据必须来自背景信息原文，禁止推测
5. 所有引用的数值必须标注来源页码，格式为"根据第X页数据，XXX为YYY"。每个数据片段前已标注[来源：第X页]，请直接使用该页码
6. 使用 Markdown 格式
7. 所有章节标题统一使用 Markdown 二级标题格式，如：## 一、债务结构与规模

【重要提示】：
- 如果用户问"刚才计算的XXX是多少"，请从历史对话记录中找到对应数值
- 如果历史回答中已有毛利率、净利率等指标，直接使用该数值回答
- 表格数据中的数值可以直接引用，但必须标注页码
- 当同时存在合并报表和母公司报表数据时，必须优先使用合并报表数据
- 如果背景信息中直接给出了用户询问的指标数值（如每股收益EPS、每股净资产等），直接引用，不要尝试用公式计算
- 当数据包含多期时，必须准确标注每个数值对应的年份。报表中左边/前面的列是本期（较新年份），右边/后面的列是上期（较旧年份），禁止将两年数据互换
- 当背景信息中存在多个匹配项时（如多年数据、分板块数据、多个期间对比），必须全部列出，不得只挑其中一个回答"""

    response = llm.invoke(prompt)
    return response.content


def generate_recommendations(query: str, answer: str, context: str = "") -> list:
    """基于对话上下文生成推荐问题
    
    Args:
        query: 用户原始问题
        answer: AI 的回答
        context: RAG 检索的上下文（可选）
    
    Returns:
        list: 3 个推荐问题字符串
    """
    from financial_report_ai_assistant.services.ai_chat import get_llm
    llm = get_llm()
    
    prompt = f"""基于以下对话，生成 3 个用户最可能想问的后续问题。

【用户问题】：{query}

【AI 回答】：
{answer[:2000]}

要求：
1. 问题必须紧扣财报分析主题
2. 问题应该是有意义的后续追问，而非重复之前的问题
3. 如果 AI 回答问了"您想计算哪个指标"，推荐问题应该是具体选项
4. 如果 AI 回答给了数值，推荐问题可以是"为什么增长/下降"、"同比/环比"等延伸
5. 问题简短，10-20字以内
6. 严格按 JSON 数组格式输出，不要有任何其他文字

示例输出：
["净利润同比增长率", "营业收入是多少", "毛利率变化趋势"]

请直接输出 JSON 数组："""

    try:
        response = llm.invoke(prompt)
        import json
        import re
        
        # 提取 JSON 数组
        content = response.content.strip()
        # 尝试直接解析
        try:
            recommendations = json.loads(content)
        except json.JSONDecodeError:
            # 尝试提取 JSON 数组
            match = re.search(r'\[.*?\]', content, re.DOTALL)
            if match:
                recommendations = json.loads(match.group())
            else:
                # 解析失败，返回默认推荐
                return ["净利润是多少", "营业收入是多少", "毛利率是多少"]
        
        # 验证结果
        if isinstance(recommendations, list) and len(recommendations) > 0:
            return recommendations[:3]  # 最多 3 个
        else:
            return ["净利润是多少", "营业收入是多少", "毛利率是多少"]
            
    except Exception as e:
        print(f"⚠️ 生成推荐失败: {e}")
        return ["净利润是多少", "营业收入是多少", "毛利率是多少"]
