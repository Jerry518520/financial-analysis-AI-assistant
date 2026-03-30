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
from dotenv import load_dotenv
from financial_report_ai_assistant.services.financial_calculator import (
    calculate_growth_rate, calculate_margin, calculate_roe, format_percentage,
    calculate_debt_ratio, calculate_current_ratio, calculate_quick_ratio,
    calculate_eps, calculate_pe, calculate_turnover, calculate_inventory_turnover,
    calculate_dividend_yield, analyze_trend, analyze_yoy, compare_to_industry,
    generate_chart_data, calculate_avg, calculate_max, calculate_min, calculate_variance
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
def tool_calculate_roe(net_income: float, equity: float) -> str:
    """计算净资产收益率 (ROE)。输入净利润和净资产。"""
    res = calculate_roe(net_income, equity)
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
def tool_calculate_inventory_turnover(cogs: float, inventory: float) -> str:
    """计算存货周转率。输入营业成本和存货金额。"""
    res = calculate_inventory_turnover(cogs, inventory)
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


def get_tools():
    """返回 19 个财务计算工具列表"""
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

⚠️ 重要规则：
- 参数必须是具体的数字，禁止传表达式或 null
- 如果找不到某个参数的数据，直接用自然语言回答，不要调用工具
- 每次最多调用 2 个工具

【背景信息】：
{state['context']}

【已完成的工具调用结果】：
{_format_tool_results(state.get('tool_results', []))}"""

    # 合并历史消息
    messages = [
        {"role": "system", "content": system_text},
        {"role": "user", "content": state["question"]},
    ]

    # 追加之前的工具调用历史（让 LLM 知道之前做了什么）
    for prev_tc in state.get("tool_results", []):
        if prev_tc.startswith("[工具调用]"):
            messages.append({"role": "assistant", "tool_calls": [{"type": "function", "function": {"name": "（历史）", "arguments": "{}"}}]})
            messages.append({"role": "tool", "content": prev_tc})

    response = llm_with_tools.invoke(messages)

    # 检查是否有 tool_calls（原生 Function Calling）
    if response.tool_calls:
        new_results = []
        new_messages = []

        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]

            tool_map = _get_tool_map()
            if tool_name in tool_map:
                try:
                    result = tool_map[tool_name].invoke(tool_args)
                    new_results.append(f"[工具调用] {tool_name}({tool_args}) → {result}")
                    print(f"🔧 工具调用成功: {tool_name}({tool_args}) → {result}")
                except Exception as e:
                    new_results.append(f"[工具调用失败] {tool_name}: {str(e)}")
                    print(f"❌ 工具调用失败: {tool_name}: {e}")
            else:
                new_results.append(f"[未知工具] {tool_name}")
                print(f"⚠️ 未知工具: {tool_name}")

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
3. 包含具体的数值和计算结果
4. 如有需要，给出分析和建议
5. 使用 Markdown 格式
6. 即使背景信息中没有直接相关的数据，也要基于已有信息给出尽可能有用的分析，说明哪些数据缺失，而不是简单地说"未找到"
7. 所有章节标题统一使用 Markdown 二级标题格式，如：## 一、债务结构与规模，而不是直接写"一、债务结构与规模"
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
    r"毛利率", r"净利率", r"资产负债率", r"流动比率", r"速动比率",
    r"周转率", r"股息",
]

_NEEDS_AGENT_PATTERNS = [
    r"EPS", r"PE", r"ROE", r"ROA",
    r"影响", r"原因", r"为什么", r"前景", r"风险", r"评估",
    r"分析", r"对比", r"趋势", r"预测", r"建议", r"策略", r"综合", r"总结",
    r"同比增长", r"环比", r"增长率",
    r"盈利能力", r"偿债能力", r"运营能力",
    r"每股", r"股本",
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
    """轻量级查询：单次 LLM 调用 + RAG 上下文，适合简单事实性问题"""
    from financial_report_ai_assistant.services.ai_chat import get_llm
    llm = get_llm()

    prompt = f"""你是一位专业的金融分析师。请根据以下财报背景信息，直接回答用户的问题。

【背景信息】：
{context}

【用户问题】：{query}

回答要求：
1. 直接回答，不要有任何开场白、问候语或自我介绍
2. 禁止以"好的"、"作为一名金融分析师"、"我将..."等开头
3. 如果背景信息中没有相关数据，请如实告知"财报中未找到相关数据"
4. 包含具体的数值（如有）
5. 使用 Markdown 格式
6. 所有章节标题统一使用 Markdown 二级标题格式，如：## 一、债务结构与规模"""

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
{answer[:2000]}  # 截断避免超长

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
