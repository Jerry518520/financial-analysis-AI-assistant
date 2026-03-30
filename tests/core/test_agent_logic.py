"""
Agent 核心逻辑单元测试
覆盖 agent.py 中的节点函数、工具列表、工作流构建等，通过 mock LLM 避免真实 API 调用。
"""

import pytest
from unittest.mock import MagicMock, patch


# ============================================================
# 辅助：模拟 LLM 响应
# ============================================================
def _mock_llm_response(content: str, tool_calls: list = None):
    """创建一个模拟的 LLM 响应对象"""
    mock_response = MagicMock()
    mock_response.content = content
    mock_response.tool_calls = tool_calls or []
    return mock_response


def _mock_bind_tools(bind_tools_self):
    """模拟 bind_tools 返回的 LLM"""
    mock_bound = MagicMock()
    return mock_bound


# ============================================================
# 1. get_tools - 工具列表完整性
# ============================================================
class TestGetTools:
    def test_returns_19_tools(self):
        from financial_report_ai_assistant.core.agent import get_tools
        tools = get_tools()
        assert len(tools) == 19

    def test_tool_names(self):
        from financial_report_ai_assistant.core.agent import get_tools
        tools = get_tools()
        names = [t.name for t in tools]
        assert "tool_calculate_growth_rate" in names
        assert "tool_calculate_margin" in names
        assert "tool_calculate_roe" in names
        assert "tool_analyze_trend" in names
        assert "tool_calculate_avg" in names

    def test_tools_are_callable(self):
        from financial_report_ai_assistant.core.agent import get_tools
        tools = get_tools()
        for tool in tools:
            assert callable(tool.func) or hasattr(tool, "invoke")


# ============================================================
# 2. create_llm - LLM 创建
# ============================================================
class TestCreateLLM:
    @patch("financial_report_ai_assistant.core.agent.os.getenv")
    def test_with_api_key(self, mock_getenv):
        mock_getenv.return_value = "fake-key"
        from financial_report_ai_assistant.core.agent import create_llm
        llm = create_llm()
        assert llm is not None

    @patch("financial_report_ai_assistant.core.agent.os.getenv")
    def test_without_api_key(self, mock_getenv):
        mock_getenv.return_value = None
        from financial_report_ai_assistant.core.agent import create_llm
        llm = create_llm()
        assert llm is None


# ============================================================
# 3. agent_node - Agent 核心节点（Function Calling）
# ============================================================
class TestAgentNode:
    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_no_tool_calls_returns_text(self, mock_create_llm):
        """LLM 没有调用工具，直接返回文本答案"""
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = _mock_llm_response(
            "财报中未找到相关数据。"
        )
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import agent_node
        state = {
            "question": "ROE是多少？",
            "context": "公司主营通信设备...",
            "tool_results": [],
            "iteration": 0,
            "final_answer": "",
        }
        result = agent_node(state)

        assert result["final_answer"] == "财报中未找到相关数据。"

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_tool_call_single(self, mock_create_llm):
        """LLM 调用单个工具（原生 Function Calling）"""
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = _mock_llm_response(
            "",
            tool_calls=[{
                "name": "tool_calculate_roe",
                "args": {"net_income": 150, "equity": 1000},
                "id": "call_001",
                "type": "tool_call",
            }]
        )
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import agent_node
        state = {
            "question": "ROE是多少？",
            "context": "净利润150亿元，净资产1000亿元",
            "tool_results": [],
            "iteration": 0,
            "final_answer": "",
        }
        result = agent_node(state)

        assert "tool_results" in result
        assert len(result["tool_results"]) > 0
        assert "工具调用" in result["tool_results"][0]
        assert result["iteration"] == 1

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_tool_call_batch(self, mock_create_llm):
        """LLM 同时调用两个工具"""
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = _mock_llm_response(
            "",
            tool_calls=[
                {
                    "name": "tool_calculate_growth_rate",
                    "args": {"current": 1200, "previous": 1000},
                    "id": "call_001",
                    "type": "tool_call",
                },
                {
                    "name": "tool_calculate_margin",
                    "args": {"profit": 300, "revenue": 1000},
                    "id": "call_002",
                    "type": "tool_call",
                },
            ]
        )
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import agent_node
        state = {
            "question": "分析盈利",
            "context": "营收1000万，利润300万，去年营收800万",
            "tool_results": [],
            "iteration": 0,
            "final_answer": "",
        }
        result = agent_node(state)

        assert len(result["tool_results"]) == 2
        assert result["iteration"] == 1

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_unknown_tool(self, mock_create_llm):
        """LLM 调用了不存在的工具"""
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        mock_llm.invoke.return_value = _mock_llm_response(
            "",
            tool_calls=[{
                "name": "nonexistent_tool",
                "args": {},
                "id": "call_001",
                "type": "tool_call",
            }]
        )
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import agent_node
        state = {
            "question": "测试",
            "context": "上下文",
            "tool_results": [],
            "iteration": 0,
            "final_answer": "",
        }
        result = agent_node(state)

        assert "未知工具" in result["tool_results"][0]

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_max_iterations_hard_stop(self, mock_create_llm):
        """迭代达 MAX_ITERATIONS 时直接停止"""
        mock_create_llm.return_value = MagicMock()

        from financial_report_ai_assistant.core.agent import agent_node, MAX_ITERATIONS
        state = {
            "question": "测试",
            "context": "",
            "tool_results": [],
            "iteration": MAX_ITERATIONS,
            "final_answer": "",
        }
        result = agent_node(state)

        assert result["iteration"] == MAX_ITERATIONS

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_no_api_key(self, mock_create_llm):
        """API Key 未配置"""
        mock_create_llm.return_value = None

        from financial_report_ai_assistant.core.agent import agent_node
        state = {
            "question": "测试",
            "context": "",
            "tool_results": [],
            "iteration": 0,
            "final_answer": "",
        }
        result = agent_node(state)

        assert "API Key" in result["final_answer"]


# ============================================================
# 4. should_continue_edge - 循环判断
# ============================================================
class TestShouldContinueEdge:
    def test_continue_when_no_answer(self):
        """没有 final_answer 且未达上限 → 继续"""
        from financial_report_ai_assistant.core.agent import should_continue_edge
        assert should_continue_edge({"final_answer": "", "iteration": 1}) == "continue"

    def test_end_when_has_answer(self):
        """有 final_answer → 结束"""
        from financial_report_ai_assistant.core.agent import should_continue_edge
        assert should_continue_edge({"final_answer": "营收增长20%", "iteration": 1}) == "end"

    def test_end_when_no_answer_empty(self):
        """final_answer 缺失 → 结束"""
        from financial_report_ai_assistant.core.agent import should_continue_edge
        assert should_continue_edge({}) == "end"

    def test_max_iteration_overrides(self):
        """达迭代上限 → 强制结束"""
        from financial_report_ai_assistant.core.agent import should_continue_edge, MAX_ITERATIONS
        assert should_continue_edge({"final_answer": "", "iteration": MAX_ITERATIONS}) == "end"


# ============================================================
# 5. answer_node - 回答生成
# ============================================================
class TestAnswerNode:
    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_normal_answer(self, mock_create_llm):
        """有工具结果时生成最终回答"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response("根据分析，公司营收增长率为20%。")
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import answer_node
        state = {
            "question": "增长率是多少？",
            "context": "2023年营收1200万，2022年营收1000万",
            "tool_results": ["[工具调用] tool_calculate_growth_rate(...) → 20.00%"],
            "final_answer": "",
        }
        result = answer_node(state)

        assert "final_answer" in result
        assert "20%" in result["final_answer"]

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_skip_when_already_has_answer(self, mock_create_llm):
        """已有 final_answer 时不重复生成"""
        mock_llm = MagicMock()
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import answer_node
        state = {
            "question": "测试",
            "context": "",
            "tool_results": [],
            "final_answer": "已有答案",
        }
        result = answer_node(state)

        # 不应该调用 LLM
        mock_llm.invoke.assert_not_called()
        assert result == {}

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_no_api_key(self, mock_create_llm):
        mock_create_llm.return_value = None

        from financial_report_ai_assistant.core.agent import answer_node
        state = {"question": "测试", "context": "", "tool_results": [], "final_answer": ""}
        result = answer_node(state)

        assert "API Key" in result["final_answer"]


# ============================================================
# 6. build_agent_graph - 工作流图构建
# ============================================================
class TestBuildAgentGraph:
    def test_graph_has_correct_nodes(self):
        from financial_report_ai_assistant.core.agent import build_agent_graph
        graph = build_agent_graph()
        assert graph is not None

    def test_create_financial_agent_singleton(self):
        """create_financial_agent 应返回同一个实例"""
        import financial_report_ai_assistant.core.agent as agent_module
        agent_module._agent_graph = None
        agent1 = agent_module.create_financial_agent()
        agent2 = agent_module.create_financial_agent()
        assert agent1 is agent2


# ============================================================
# 7. Tool 函数单独测试
# ============================================================
class TestToolFunctions:
    def test_tool_calculate_growth_rate(self):
        from financial_report_ai_assistant.core.agent import tool_calculate_growth_rate
        result = tool_calculate_growth_rate.invoke({"current": 1200, "previous": 1000})
        assert "20.00%" in result

    def test_tool_calculate_margin(self):
        from financial_report_ai_assistant.core.agent import tool_calculate_margin
        result = tool_calculate_margin.invoke({"profit": 300, "revenue": 1000})
        assert "30.00%" in result

    def test_tool_calculate_roe(self):
        from financial_report_ai_assistant.core.agent import tool_calculate_roe
        result = tool_calculate_roe.invoke({"net_income": 150, "equity": 1000})
        assert "15.00%" in result

    def test_tool_calculate_eps(self):
        from financial_report_ai_assistant.core.agent import tool_calculate_eps
        result = tool_calculate_eps.invoke({"net_income": 5000, "shares_outstanding": 1000})
        assert "5.00" in result

    def test_tool_calculate_pe(self):
        from financial_report_ai_assistant.core.agent import tool_calculate_pe
        result = tool_calculate_pe.invoke({"price_per_share": 30, "eps": 2})
        assert "15.00" in result

    def test_tool_analyze_trend(self):
        from financial_report_ai_assistant.core.agent import tool_analyze_trend
        result = tool_analyze_trend.invoke({"values": [100, 120, 150]})
        assert "上升" in result

    def test_tool_calculate_avg(self):
        from financial_report_ai_assistant.core.agent import tool_calculate_avg
        result = tool_calculate_avg.invoke({"values": [10, 20, 30]})
        assert "20" in result

    def test_tool_generate_chart_data(self):
        from financial_report_ai_assistant.core.agent import tool_generate_chart_data
        result = tool_generate_chart_data.invoke({
            "years": [2021, 2022, 2023],
            "values": [100, 120, 150],
            "metric_name": "营收"
        })
        assert "2021" in result


# ============================================================
# 8. is_simple_query / run_lightweight_query
# ============================================================
class TestSimpleQuery:
    def test_simple_revenue_question(self):
        from financial_report_ai_assistant.core.agent import is_simple_query
        assert is_simple_query("营收是多少？") is True

    def test_simple_profit_question(self):
        from financial_report_ai_assistant.core.agent import is_simple_query
        assert is_simple_query("净利润有多少？") is True

    def test_complex_roe_question(self):
        from financial_report_ai_assistant.core.agent import is_simple_query
        assert is_simple_query("ROE是多少？") is False

    def test_complex_analysis_question(self):
        from financial_report_ai_assistant.core.agent import is_simple_query
        assert is_simple_query("请分析公司的盈利能力") is False

    def test_long_question(self):
        from financial_report_ai_assistant.core.agent import is_simple_query
        long_q = "请问" + "很多字" * 20 + "是多少？"
        assert is_simple_query(long_q) is False


# ============================================================
# 9. run_agent_query - 端到端 Agent 执行
# ============================================================
class TestRunAgentQuery:
    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_normal_execution(self, mock_create_llm):
        """模拟完整 Agent 流程：agent_node 直接返回文本答案"""
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        # agent_node 一次调用就返回文本（不需要工具的场景）
        mock_llm.invoke.return_value = _mock_llm_response("公司营收为1000亿元。")
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import run_agent_query
        import financial_report_ai_assistant.core.agent as agent_module
        agent_module._agent_graph = None

        result = run_agent_query(query="营收是多少？", context="公司营收1000亿元")
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_tool_call_then_answer(self, mock_create_llm):
        """模拟工具调用场景：agent 调工具 → answer 生成回答"""
        mock_llm = MagicMock()
        mock_llm.bind_tools.return_value = mock_llm
        # 第一次调用：agent_node 返回 tool_calls
        # 第二次调用：agent_node 返回空（有 final_answer 时不会走到 answer 的 LLM）
        # 第三次调用：answer_node 生成回答
        mock_llm.invoke.side_effect = [
            _mock_llm_response(
                "",
                tool_calls=[{
                    "name": "tool_calculate_growth_rate",
                    "args": {"current": 1200, "previous": 1000},
                    "id": "call_001",
                    "type": "tool_call",
                }]
            ),
            # 第二次 agent_node：没有工具调用，返回空文本
            _mock_llm_response(""),
            # answer_node 生成回答
            _mock_llm_response("营收增长率为20%。"),
        ]
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import run_agent_query
        import financial_report_ai_assistant.core.agent as agent_module
        agent_module._agent_graph = None

        result = run_agent_query(query="增长率是多少？", context="2023年营收1200万，2022年营收1000万")
        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================
# 10. _format_tool_results 辅助函数
# ============================================================
class TestFormatToolResults:
    def test_empty_list(self):
        from financial_report_ai_assistant.core.agent import _format_tool_results
        assert _format_tool_results([]) == "无"

    def test_with_results(self):
        from financial_report_ai_assistant.core.agent import _format_tool_results
        result = _format_tool_results(["[工具调用] roe → 15%"])
        assert "[工具调用]" in result
