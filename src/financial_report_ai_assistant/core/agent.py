from langgraph.graph import StateGraph, END
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from typing import TypedDict, List, Optional, Union, Annotated
import operator
import os
from difflib import SequenceMatcher
from dotenv import load_dotenv
from financial_report_ai_assistant.services.financial_calculator import (
    calculate_growth_rate, calculate_margin, calculate_roe, format_percentage,
    calculate_debt_ratio, calculate_current_ratio, calculate_quick_ratio,
    calculate_eps, calculate_pe, calculate_turnover, calculate_inventory_turnover,
    calculate_dividend_yield, analyze_trend, analyze_yoy, compare_to_industry,
    generate_chart_data, calculate_avg, calculate_max, calculate_min, calculate_variance
)

load_dotenv()

MAX_ITERATIONS = 8

class AgentState(TypedDict):
    question: str
    context: str
    plan: List[str]
    tool_calls: Annotated[list[str], operator.add]
    tool_results: Annotated[list[str], operator.add]
    reflection: str
    final_answer: str
    iteration: int
    should_continue: bool
    _executor_continue: bool  # executor 是否成功执行了工具（供 reflection 参考）

# 1. 定义 Tools - 盈利能力
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

# 2. 定义 Tools - 偿债能力
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

# 3. 定义 Tools - 运营能力
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

# 4. 定义 Tools - 股息
@tool
def tool_calculate_dividend_yield(dividend_per_share: float, price_per_share: float) -> str:
    """计算股息率。输入每股股息和每股股价。"""
    res = calculate_dividend_yield(dividend_per_share, price_per_share)
    return format_percentage(res)

# 5. 定义 Tools - 趋势分析
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
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("⚠️ Warning: DEEPSEEK_API_KEY not found.")
        return None
    return ChatOpenAI(
        model="deepseek-chat",
        api_key=api_key,
        base_url="https://api.deepseek.com",
        temperature=0.1,
        max_tokens=1024,
    )

# ==================== Agent 核心逻辑 ====================

def planner_node(state: AgentState):
    """规划器：将复杂问题分解为多个子任务"""
    llm = create_llm()
    if not llm:
        return {"plan": ["错误：API Key 未配置"]}
    
    planner_prompt = f"""你是一位专业的金融分析师助手。用户提出了一个复杂问题，你需要将其分解为多个可执行的子任务。

【用户问题】：{state['question']}

【背景信息】：
{state['context']}

请分析这个问题需要哪些步骤才能回答。输出一个任务列表，每行一个任务。
格式示例：
1. 从背景信息中提取2023年营收数据
2. 从背景信息中提取2022年营收数据
3. 计算同比增长率
4. 与行业平均对比

只输出任务列表，不要其他内容。
"""
    
    response = llm.invoke(planner_prompt)
    plan = response.content.strip().split('\n')
    plan = [p.strip() for p in plan if p.strip()]
    
    return {"plan": plan, "iteration": 0}

# 模糊匹配阈值：0.7 可容忍 1-2 个字符的拼写错误
_FUZZY_THRESHOLD = 0.7


def _fuzzy_match(name: str, candidates: list[str]) -> str | None:
    """用 SequenceMatcher 模糊匹配，找到最接近的候选名。"""
    name_lower = name.lower().replace("_", "")
    best_score = 0.0
    best_match = None
    for candidate in candidates:
        cand_lower = candidate.lower().replace("_", "")
        score = SequenceMatcher(None, name_lower, cand_lower).ratio()
        if score > best_score and score >= _FUZZY_THRESHOLD:
            best_score = score
            best_match = candidate
    return best_match


def _get_tool_map_v2():
    """构建工具名称 → 工具函数的映射表（支持模糊匹配）"""
    tools = get_tools()
    return {tool.name: tool for tool in tools}, list({tool.name for tool in tools})

def executor_node(state: AgentState):
    """执行器：根据当前计划调用工具（支持批量调用多个工具）"""
    llm = create_llm()
    if not llm:
        return {"tool_results": ["错误：API Key 未配置"], "should_continue": False, "_executor_continue": False}

    tool_map, tool_names = _get_tool_map_v2()

    current_plan = state.get("plan", [])
    previous_results = state.get("tool_results", [])
    iteration = state.get("iteration", 0)

    # 全局硬上限：超过 MAX_ITERATIONS 直接停止
    if iteration >= MAX_ITERATIONS:
        return {"should_continue": False, "_executor_continue": False}

    executor_prompt = f"""你是一位专业的金融分析师。根据用户的【问题】和【背景信息】，决定需要调用哪些工具来完成任务。

【用户问题】：{state['question']}

【背景信息】：
{state['context']}

【待完成任务】：
{chr(10).join(current_plan)}

【已完成的工具调用结果】：
{chr(10).join(previous_results) if previous_results else "无"}

请分析需要调用哪些工具来推进任务。
⚠️ 重要：只调用与问题直接相关的工具，不要调用无关工具。一次最多调用 2 个工具。

⚠️ 参数规则（必须严格遵守）：
- 所有数值参数必须是具体的数字，如 120000000、0.25
- 禁止输出表达式（如 5000000000 + 14700000000）
- 禁止输出 null，如果找不到数据请直接输出 FINISH
- 如果已完成的工具调用结果中已有足够信息来回答问题，请直接输出 FINISH

可用的工具列表：
{chr(10).join(f"- {name}: {tool.description}" for name, tool in tool_map.items())}

如果需要调用工具，输出JSON数组格式（最多2个调用）：
[{{"name": "工具函数名", "args": {{"参数名": 参数值}}}}]

如果所有任务都已完成，或不需要再调用工具，请输出：
[{{"name": "FINISH", "args": {{}}}}]

⚠️ 只输出一个紧凑的 JSON 数组，不要任何其他文字、注释或换行！
"""

    response = llm.invoke(executor_prompt)
    response_text = response.content.strip()

    import json
    import re

    new_calls = []
    new_results = []

    def _validate_args(args: dict, tool_name: str) -> tuple[bool, dict]:
        """验证并清洗工具参数，确保数值类型的参数是有效数值（不能是表达式、null、字符串）。
        返回 (是否合法, 清洗后的参数)。"""
        cleaned = {}
        for key, value in args.items():
            if value is None:
                # null 参数 → 不合法，LLM 没找到数据
                return False, {}
            if isinstance(value, (int, float)):
                cleaned[key] = value
            elif isinstance(value, str):
                # 检查字符串是否是表达式（含运算符的数字）
                stripped = value.strip()
                if re.match(r'^[\d\s\+\-\*\/\.\(\),]+$', stripped) and re.search(r'[\+\-\*\/]', stripped):
                    # 是数学表达式，不合法
                    return False, {}
                # 尝试把纯数字字符串转为 float
                try:
                    cleaned[key] = float(stripped)
                except ValueError:
                    cleaned[key] = value  # 普通字符串保留
            elif isinstance(value, list):
                # 列表参数（如 values=[100, 120, 150]），检查每个元素
                valid_list = []
                for item in value:
                    if isinstance(item, (int, float)):
                        valid_list.append(item)
                    elif isinstance(item, str):
                        try:
                            valid_list.append(float(item.strip()))
                        except (ValueError, AttributeError):
                            return False, {}
                    else:
                        return False, {}
                cleaned[key] = valid_list
            else:
                cleaned[key] = value
        return True, cleaned

    def _extract_json_objects(text: str) -> list[dict]:
        """从文本中安全提取完整的 JSON 对象列表。
        
        关键：避免贪婪匹配导致截断的 JSON 被当作完整数组解析。
        策略：逐个提取完整 JSON 对象（用大括号配对），忽略截断的尾巴。
        """
        objects = []
        i = 0
        text = text.strip()
        while i < len(text):
            # 找下一个 '{'
            brace_start = text.find('{', i)
            if brace_start == -1:
                break
            # 从这里开始尝试匹配完整的 JSON 对象
            depth = 0
            in_string = False
            escape_next = False
            j = brace_start
            while j < len(text):
                ch = text[j]
                if escape_next:
                    escape_next = False
                    j += 1
                    continue
                if ch == '\\' and in_string:
                    escape_next = True
                    j += 1
                    continue
                if ch == '"' and not escape_next:
                    in_string = not in_string
                    j += 1
                    continue
                if in_string:
                    j += 1
                    continue
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        # 找到完整的 JSON 对象
                        candidate = text[brace_start:j+1]
                        try:
                            obj = json.loads(candidate)
                            if isinstance(obj, dict) and "name" in obj:
                                objects.append(obj)
                        except json.JSONDecodeError:
                            pass  # 配对但不合法 JSON，跳过
                        i = j + 1
                        break
                j += 1
            else:
                # 到达文本末尾仍未闭合 → 截断，停止
                break
        return objects

    def _parse_and_execute(raw_text: str) -> bool:
        """尝试解析 LLM 返回的工具调用 JSON 并执行。返回是否成功执行了工具。
        
        关键：只有工具真正执行成功才算 success。
        工具执行出错、参数无效、未知工具等都不计入 success，避免死循环。
        """
        nonlocal new_calls, new_results
        
        # 先检查是否 FINISH
        if "FINISH" in raw_text and not re.search(r'\[[\s\S]*"name"[\s\S]*\]', raw_text):
            return True  # FINISH 信号，算"成功"

        # 策略一：先尝试直接解析整个 JSON 数组（理想情况，未截断）
        array_match = re.search(r'\[[\s\S]*\]', raw_text)
        tool_calls_json = None
        if array_match:
            try:
                parsed = json.loads(array_match.group())
                if isinstance(parsed, list) and len(parsed) > 0:
                    tool_calls_json = parsed
            except json.JSONDecodeError:
                pass  # 数组不完整，用策略二

        # 策略二：数组解析失败 → 逐个提取完整 JSON 对象（容忍截断）
        if tool_calls_json is None:
            tool_calls_json = _extract_json_objects(raw_text)
            if not tool_calls_json:
                return False  # 完全无法解析

        for tool_call in tool_calls_json:
            tool_name = tool_call.get("name")
            tool_args = tool_call.get("args", {})

            if tool_name == "FINISH":
                return True

            # 1. 工具名模糊匹配：LLM 可能拼错工具名
            if tool_name not in tool_map:
                matched = _fuzzy_match(tool_name, tool_names)
                if matched:
                    new_results.append(f"工具名修正: {tool_name} → {matched}")
                    tool_name = matched
                else:
                    new_results.append(f"未知工具: {tool_name}")
                    continue  # 不计入 new_calls

            # 2. 参数名模糊匹配：LLM 可能拼错参数名
            tool_func = tool_map[tool_name]
            if tool_func.args_schema and hasattr(tool_func.args_schema, 'model_fields'):
                valid_param_names = list(tool_func.args_schema.model_fields.keys())
                corrected_args = {}
                for arg_key, arg_value in tool_args.items():
                    if arg_key in valid_param_names:
                        corrected_args[arg_key] = arg_value
                    else:
                        # 尝试模糊匹配参数名
                        matched_param = _fuzzy_match(arg_key, valid_param_names)
                        if matched_param:
                            corrected_args[matched_param] = arg_value
                            new_results.append(f"参数名修正: {tool_name}.{arg_key} → {matched_param}")
                        # 否则静默忽略无效参数（避免因多余参数报错）
                tool_args = corrected_args

            # 参数验证：拒绝表达式、null、无效值
            valid, cleaned_args = _validate_args(tool_args, tool_name)
            if not valid:
                new_results.append(f"工具 {tool_name} 参数无效: {tool_args}，请提供具体的数值而非表达式或 null")
                continue  # 不计入 new_calls

            try:
                result = tool_func.invoke(cleaned_args)
                new_results.append(str(result))
                new_calls.append(f"{tool_name}({cleaned_args})")
            except Exception as e:
                new_results.append(f"工具 {tool_name} 执行出错: {str(e)}")
                # 不追加到 new_calls → 工具出错不算"成功调用"

        return len(new_calls) > 0

    try:
        success = _parse_and_execute(response_text)
    except Exception as e:
        success = False
        new_results.append(f"JSON 解析出错: {str(e)}，原始返回: {response_text[:200]}")

    # JSON 解析失败时，让 LLM 重新生成一次严格格式（提高容错性）
    if not success:
        print(f"⚠️ executor 首次解析失败，尝试重试... 原始返回: {response_text[:200]}")
        retry_prompt = f"""你刚才的输出格式有误。请严格按以下要求重新输出：

要求：
1. 输出一个合法的 JSON 数组，每个元素包含 "name" 和 "args" 字段
2. args 中的数值参数必须是具体的数字（如 120000000），不能是表达式（如 5000000000 + 14700000000）、不能是 null
3. 如果找不到某个参数的数据，请直接输出 [{{"name": "FINISH", "args": {{}}}}] 跳过
4. 如果不需要调用工具，输出：[{{"name": "FINISH", "args": {{}}}}]

用户问题：{state['question']}
背景信息：{state['context'][:3000]}

只输出 JSON 数组，不要任何其他文字！"""
        retry_response = llm.invoke(retry_prompt)
        retry_text = retry_response.content.strip()
        try:
            # 清理可能的 markdown 代码块包裹
            retry_text = re.sub(r'^```(?:json)?\s*', '', retry_text)
            retry_text = re.sub(r'\s*```$', '', retry_text)
            success = _parse_and_execute(retry_text)
        except Exception as e:
            new_results.append(f"重试也失败: {str(e)}")

    # FINISH 信号
    if success and not new_calls:
        return {"should_continue": False, "tool_calls": new_calls, "tool_results": new_results, "_executor_continue": False}
    
    # 如果没有成功调用任何工具，停止循环并告知 answer 节点
    if not new_calls:
        new_results.append("⚠️ 所有工具调用均失败，无法完成计算。将基于已有信息直接回答。")
        return {"should_continue": False, "tool_calls": new_calls, "tool_results": new_results, "_executor_continue": False}

    return {
        "tool_calls": new_calls,
        "tool_results": new_results,
        "iteration": iteration + 1,
        "should_continue": True,  # 有工具调用成功 → 交给 reflection 决定是否继续
        "_executor_continue": True,
    }

def reflection_node(state: AgentState):
    """反思节点：检查工具返回结果是否合理"""
    llm = create_llm()
    if not llm:
        return {"reflection": "API Key 未配置"}
    
    tool_results = state.get("tool_results", [])
    plan = state.get("plan", [])
    iteration = state.get("iteration", 0)
    
    reflection_prompt = f"""你是一位专业的金融分析师。请审查刚才的工具执行结果，判断是否合理。

【用户问题】：{state['question']}

【待完成任务】：
{chr(10).join(plan)}

【工具执行结果】：
{chr(10).join(tool_results) if tool_results else "无"}

请进行以下检查：
1. 数值是否合理？（如增长率是否在-100%到500%之间，百分比是否在0-100%之间）
2. 数据是否来自可靠的背景信息？
3. 任务是否已完成？

请输出以下格式的判断：
- 如果结果合理且任务完成：FINISH
- 如果结果合理但需要继续：CONTINUE
- 如果结果异常需要重新执行：RETRY（并说明原因）

只输出判断结果和简短原因，不要其他内容。
"""
    
    response = llm.invoke(reflection_prompt)
    reflection = response.content.strip()

    # 处理三种判断结果
    # 关键：如果 executor 没有成功执行任何工具，不允许 RETRY/CONTINUE，避免死循环
    executor_wants_continue = state.get("_executor_continue", True)
    if "FINISH" in reflection:
        should_continue = False
    elif "RETRY" in reflection and executor_wants_continue and iteration < MAX_ITERATIONS:
        # RETRY 仅当 executor 本身还想继续时才允许
        should_continue = True
    elif "CONTINUE" in reflection and executor_wants_continue and iteration < MAX_ITERATIONS:
        should_continue = True
    else:
        # 达到迭代上限或 executor 已停止，都停止
        should_continue = False

    return {"reflection": reflection, "should_continue": should_continue}

def answer_node(state: AgentState):
    """生成最终回答"""
    llm = create_llm()
    if not llm:
        return {"final_answer": "Agent 初始化失败，请检查 API Key。"}
    
    context = state.get("context", "")
    tool_results = state.get("tool_results", [])
    plan = state.get("plan", [])
    reflection = state.get("reflection", "")
    
    answer_prompt = f"""你是一位专业的金融分析师。请根据以下信息生成最终回答。

【用户问题】：{state['question']}

【背景信息】：
{context}

【任务列表】：
{chr(10).join(plan)}

【工具执行结果】：
{chr(10).join(tool_results) if tool_results else "无"}

【反思结果】：
{reflection}

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

def should_continue_edge(state: AgentState) -> str:
    """判断是否继续循环（含全局硬上限保护）"""
    if state.get("iteration", 0) >= MAX_ITERATIONS:
        return "end"
    if state.get("should_continue", False):
        return "continue"
    return "end"

def build_agent_graph():
    """构建 Agent 工作流图"""
    workflow = StateGraph(AgentState)
    
    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("answer", answer_node)
    
    workflow.set_entry_point("planner")
    
    workflow.add_edge("planner", "executor")
    workflow.add_edge("executor", "reflection")
    
    workflow.add_conditional_edges(
        "reflection",
        should_continue_edge,
        {
            "continue": "executor",
            "end": "answer"
        }
    )
    
    workflow.add_edge("answer", END)
    
    # recursion_limit 设置为 MAX_ITERATIONS * 每轮步数(planner1 + executor1 + reflection1) + answer + 安全余量
    return workflow.compile(checkpointer=None)

_agent_graph = None

def create_financial_agent():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph

def run_agent_query(query: str, context: str = ""):
    """运行真正的 Agent"""
    import time
    agent = create_financial_agent()
    if not agent:
        return "Agent 初始化失败，请检查 API Key。"
    
    try:
        initial_state = {
            "question": query,
            "context": context,
            "plan": [],
            "tool_calls": [],
            "tool_results": [],
            "reflection": "",
            "final_answer": "",
            "iteration": 0,
            "should_continue": True,
            "_executor_continue": True,
        }
        
        print(f"🤖 Agent 开始执行 | 问题: {query[:50]}... | 上下文长度: {len(context)} 字符")
        start_time = time.time()
        
        result = agent.invoke(initial_state, {"recursion_limit": MAX_ITERATIONS * 5 + 20})
        
        elapsed = time.time() - start_time
        final_answer = result.get("final_answer", "")
        print(f"✅ Agent 执行完成 | 耗时: {elapsed:.1f}s | 回答长度: {len(final_answer)} 字符")
        
        if not final_answer.strip():
            print(f"⚠️ Agent 返回空回答！完整 state: tool_calls={result.get('tool_calls', [])}, tool_results={result.get('tool_results', [])}")
            return "⚠️ Agent 未能生成有效回答。这可能是由于 API 响应异常，请稍后重试。"
        
        return final_answer
    
    except Exception as e:
        error_msg = str(e)
        if "recursion_limit" in error_msg.lower() or "recursion" in error_msg.lower():
            return "⚠️ 问题较为复杂，分析超时。请尝试将问题拆分为更具体的子问题重新提问。例如：不要问\"未来发展前景如何\"，而是问\"营收同比增长了多少\"。"
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

# 需要 Agent 深度分析的指标（涉及数值计算或复杂推理）
_NEEDS_AGENT_PATTERNS = [
    r"\bEPS\b", r"\bPE\b", r"\bROE\b", r"\bROA\b",
    r"影响", r"原因", r"为什么", r"前景", r"风险", r"评估",
    r"分析", r"对比", r"趋势", r"预测", r"建议", r"策略", r"综合", r"总结",
    r"同比增长", r"环比", r"增长率",
    r"盈利能力", r"偿债能力", r"运营能力",
    r"每股", r"股本",
]

def is_simple_query(question: str) -> bool:
    """判断问题是否为简单查询（不需要多步工具调用）"""
    q = question.strip()
    if len(q) > 50:
        return False
    # 先检查是否匹配需要 Agent 的模式
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
