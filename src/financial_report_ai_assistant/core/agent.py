from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
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

# 6. 定义 Tools - 同比分析
@tool
def tool_analyze_yoy(current: float, previous: float) -> str:
    """进行同比分析。输入本期数值和上期数值。"""
    res = analyze_yoy(current, previous)
    return str(res)

# 7. 定义 Tools - 行业对比
@tool
def tool_compare_to_industry(value: float, industry_avg: float) -> str:
    """与行业平均对比。输入公司数值和行业平均值。"""
    res = compare_to_industry(value, industry_avg)
    return str(res)

# 8. 定义 Tools - 图表数据生成
@tool
def tool_generate_chart_data(years: list, values: list, metric_name: str = "指标") -> str:
    """生成图表数据。输入年份列表和数值列表，如 years=[2021,2022,2023], values=[100,120,150]。"""
    res = generate_chart_data(years, values, metric_name)
    return str(res)

# 9. 定义 Tools - 统计计算
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

# 2. Agent 构建
def create_financial_agent():
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("⚠️ Warning: DEEPSEEK_API_KEY not found.")
        return None
    
    # DeepSeek V3/R1 目前对 Function Calling 支持可能有限，视具体版本而定
    # 如果是 DeepSeek-V3，通常支持 OpenAI 格式的 Tools
    llm = ChatOpenAI(
        model="deepseek-chat",
        api_key=api_key,
        base_url="https://api.deepseek.com",
        temperature=0.1 # 计算任务需要低温度
    )
    
    tools = [
        # 盈利能力
        tool_calculate_growth_rate,
        tool_calculate_margin,
        tool_calculate_roe,
        tool_calculate_eps,
        tool_calculate_pe,
        # 偿债能力
        tool_calculate_debt_ratio,
        tool_calculate_current_ratio,
        tool_calculate_quick_ratio,
        # 运营能力
        tool_calculate_turnover,
        tool_calculate_inventory_turnover,
        # 股息
        tool_calculate_dividend_yield,
        # 趋势分析
        tool_analyze_trend,
        tool_analyze_yoy,
        # 行业对比
        tool_compare_to_industry,
        # 图表数据
        tool_generate_chart_data,
        # 统计分析
        tool_calculate_avg,
        tool_calculate_max,
        tool_calculate_min,
        tool_calculate_variance,
    ]
    
    system_prompt = """你是一位专业的金融分析师。你的任务是根据用户提供的【背景信息】（通常来自财报检索）来回答问题。
    
    原则：
    1. 如果问题涉及具体的财务指标计算（如增长率、利润率、ROE、资产负债率等），你必须调用提供的工具进行精确计算，严禁自己估算。
    2. 如果背景信息中没有足够的数据支持计算或回答，请诚实告知用户。
    3. 回答要条理清晰，数据准确。
    4. 当用户询问以下类型的指标时，必须使用对应的工具：
       - 增长类：使用 tool_calculate_growth_rate
       - 盈利类：使用 tool_calculate_margin、tool_calculate_roe、tool_calculate_eps、tool_calculate_pe
       - 偿债类：使用 tool_calculate_debt_ratio、tool_calculate_current_ratio、tool_calculate_quick_ratio
       - 运营类：使用 tool_calculate_turnover、tool_calculate_inventory_turnover
       - 股息类：使用 tool_calculate_dividend_yield
    """
    
    # 使用 LangGraph 的 prebuilt agent
    # 注意：当前版本的 langgraph 使用 prompt 参数而不是 state_modifier
    agent_executor = create_react_agent(llm, tools, prompt=system_prompt)
    
    return agent_executor

def run_agent_query(query: str):
    agent = create_financial_agent()
    if agent:
        try:
            # LangGraph invoke 接受 messages 列表
            result = agent.invoke({"messages": [("user", query)]})
            # 结果在 messages 的最后一条
            return result["messages"][-1].content
        except Exception as e:
            return f"Agent 执行出错: {str(e)}"
    else:
        return "Agent 初始化失败，请检查 API Key。"
