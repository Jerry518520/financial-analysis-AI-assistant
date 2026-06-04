"""
Agent 全链路集成测试 — 覆盖所有可能出错的路径
运行方式：poetry run python tests/integration_agent_test.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# 确保 .env 加载
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from financial_report_ai_assistant.core.agent import (
    run_agent_query, is_simple_query, generate_recommendations,
    create_llm, get_tools, _get_tool_map, build_agent_graph
)
import traceback

PASS = 0
FAIL = 0

def run_test(name, fn):
    global PASS, FAIL
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    try:
        result = fn()
        print(f"[PASS] {result}")
        PASS += 1
    except Exception as e:
        print(f"[FAIL] {e}")
        traceback.print_exc()
        FAIL += 1


# ========== 1. LLM 基础连接 ==========
def test_llm_connection():
    llm = create_llm()
    assert llm is not None, "LLM 创建失败"
    resp = llm.invoke("回复OK")
    assert resp.content, "LLM 返回空内容"
    return f"LLM 连接正常，回复: {resp.content[:50]}"

# ========== 2. 工具绑定 + Function Calling ==========
def test_function_calling_basic():
    llm = create_llm()
    tools = get_tools()
    llm_with_tools = llm.bind_tools(tools)
    resp = llm_with_tools.invoke([
        {"role": "system", "content": "你是一个助手。"},
        {"role": "user", "content": "帮我计算 ROE，净利润150亿，净资产1000亿"}
    ])
    print(f"  response.tool_calls = {resp.tool_calls}")
    print(f"  response.content = {resp.content[:100] if resp.content else '(empty)'}")
    assert resp.tool_calls, "LLM 没有返回 tool_calls"
    tc = resp.tool_calls[0]
    assert "name" in tc, f"tool_calls 缺少 name: {tc}"
    assert "args" in tc, f"tool_calls 缺少 args: {tc}"
    assert tc["name"] == "tool_calculate_roe", f"工具名错误: {tc['name']}"
    return f"Function Calling 正常，工具: {tc['name']}，参数: {tc['args']}"

# ========== 3. 工具实际执行 ==========
def test_tool_execution():
    tool_map = _get_tool_map()
    result = tool_map["tool_calculate_roe"].invoke({"net_income": 150, "equity": 1000})
    print(f"  ROE 结果: {result}")
    assert "15" in result, f"ROE 计算结果不对: {result}"
    return f"工具执行正常: {result}"

# ========== 4. Agent 单轮查询（简单路径） ==========
def test_agent_simple():
    answer = run_agent_query("你好", "")
    assert answer, "Agent 返回空回答"
    return f"回答长度: {len(answer)} 字符"

# ========== 5. Agent 财务查询（工具调用路径） ==========
def test_agent_with_calculation():
    context = "公司2024年净利润150亿元，净资产1000亿元。"
    answer = run_agent_query("ROE是多少？", context)
    assert answer, "Agent 返回空回答"
    print(f"  回答: {answer[:200]}")
    # 应该包含 15% 的 ROE 结果
    return f"回答长度: {len(answer)} 字符"

# ========== 6. Agent 数据缺失场景 ==========
def test_agent_no_data():
    context = "公司主营手机业务，2024年销售额增长10%。"
    answer = run_agent_query("ROE是多少？", context)
    assert answer, "Agent 返回空回答"
    print(f"  回答: {answer[:200]}")
    return f"回答长度: {len(answer)} 字符"

# ========== 7. Agent 多轮工具调用 ==========
def test_agent_multi_tool():
    context = "2024年净利润150亿，净资产1000亿，总资产2000亿，总负债800亿。"
    answer = run_agent_query("计算ROE和资产负债率", context)
    assert answer, "Agent 返回空回答"
    print(f"  回答: {answer[:300]}")
    return f"回答长度: {len(answer)} 字符"

# ========== 8. is_simple_query 分类 ==========
def test_simple_query_classification():
    assert is_simple_query("营收是多少？") == True
    assert is_simple_query("净利润有多少？") == True
    assert is_simple_query("ROE是多少？") == True
    assert is_simple_query("净资产收益率(ROE)是多少？") == True
    assert is_simple_query("分析公司的盈利能力") == False
    assert is_simple_query("请评估公司的偿债风险") == False
    assert is_simple_query("EPS是多少？") == False
    assert is_simple_query("PE是多少？") == False
    return "所有分类测试通过"

# ========== 9. generate_recommendations ==========
def test_recommendations():
    recs = generate_recommendations("ROE是多少？", "公司ROE为15%", "净利润150亿")
    assert isinstance(recs, list), f"返回类型错误: {type(recs)}"
    assert len(recs) > 0, "推荐列表为空"
    print(f"  推荐问题: {recs}")
    return f"推荐问题: {recs}"

# ========== 10. LangGraph 工作流构建 ==========
def test_graph_build():
    graph = build_agent_graph()
    assert graph is not None, "工作流构建失败"
    result = graph.invoke({
        "question": "1+1等于几",
        "context": "",
        "messages": [],
        "tool_results": [],
        "final_answer": "",
        "iteration": 0,
    }, {"recursion_limit": 20})
    answer = result.get("final_answer", "")
    assert answer, f"工作流返回空答案，state: {result}"
    return f"工作流正常，回答长度: {len(answer)}"

# ========== 11. 边界：长上下文 ==========
def test_long_context():
    context = "财报数据" * 5000  # ~30000 字符
    answer = run_agent_query("营收是多少？", context)
    assert answer, "长上下文返回空回答"
    return f"长上下文测试通过，回答长度: {len(answer)}"

# ========== 12. 边界：空上下文 ==========
def test_empty_context():
    answer = run_agent_query("ROE是多少？", "")
    assert answer, "空上下文返回空回答"
    return f"空上下文测试通过，回答: {answer[:100]}"

# ========== 13. 边界：iteration 超限 ==========
def test_max_iterations():
    """模拟超限场景"""
    from financial_report_ai_assistant.core.agent import should_continue_edge, MAX_ITERATIONS
    # 不到上限 + 无答案 → continue
    assert should_continue_edge({"iteration": 1}) == "continue"
    # 到上限 → end
    assert should_continue_edge({"iteration": MAX_ITERATIONS}) == "end"
    # 有答案 → end
    assert should_continue_edge({"final_answer": "some answer", "iteration": 1}) == "end"
    # 空 dict → continue
    assert should_continue_edge({}) == "continue"
    return "迭代控制逻辑正确"


if __name__ == "__main__":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    print("=" * 60)
    print("Agent 全链路集成测试")
    print("=" * 60)

    run_test("LLM 基础连接", test_llm_connection)
    run_test("Function Calling 基础", test_function_calling_basic)
    run_test("工具实际执行", test_tool_execution)
    run_test("Agent 简单查询", test_agent_simple)
    run_test("Agent 财务计算", test_agent_with_calculation)
    run_test("Agent 数据缺失", test_agent_no_data)
    run_test("Agent 多工具调用", test_agent_multi_tool)
    run_test("简单问题分类", test_simple_query_classification)
    run_test("推荐问题生成", test_recommendations)
    run_test("LangGraph 工作流", test_graph_build)
    run_test("长上下文边界", test_long_context)
    run_test("空上下文边界", test_empty_context)
    run_test("迭代控制边界", test_max_iterations)

    print(f"\n{'='*60}")
    print(f"结果: {PASS} passed, {FAIL} failed")
    print(f"{'='*60}")

    if FAIL > 0:
        sys.exit(1)
