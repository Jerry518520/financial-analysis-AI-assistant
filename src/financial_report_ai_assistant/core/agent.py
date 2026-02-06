from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from financial_report_ai_assistant.services.financial_calculator import (
    calculate_growth_rate, calculate_margin, calculate_roe, format_percentage
)

load_dotenv()

# 1. 定义 Tools
@tool
def tool_calculate_growth_rate(current: float, previous: float) -> str:
    """计算增长率。输入本期数值和上期数值。"""
    res = calculate_growth_rate(current, previous)
    return format_percentage(res)

@tool
def tool_calculate_margin(profit: float, revenue: float) -> str:
    """计算利润率。输入利润和营收。"""
    res = calculate_margin(profit, revenue)
    return format_percentage(res)

@tool
def tool_calculate_roe(net_income: float, equity: float) -> str:
    """计算净资产收益率 (ROE)。输入净利润和净资产。"""
    res = calculate_roe(net_income, equity)
    return format_percentage(res)

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
    
    tools = [tool_calculate_growth_rate, tool_calculate_margin, tool_calculate_roe]
    
    system_prompt = """你是一位专业的金融分析师。你的任务是根据用户提供的【背景信息】（通常来自财报检索）来回答问题。
    
    原则：
    1. 如果问题涉及具体的财务指标计算（如增长率、利润率、ROE），你必须调用提供的工具进行精确计算，严禁自己估算。
    2. 如果背景信息中没有足够的数据支持计算或回答，请诚实告知用户。
    3. 回答要条理清晰，数据准确。
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
