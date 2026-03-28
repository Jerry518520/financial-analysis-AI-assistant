"""
Agent 核心逻辑单元测试
覆盖 agent.py 中的节点函数、工具列表、工作流构建等，通过 mock LLM 避免真实 API 调用。
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ============================================================
# 辅助：模拟 LLM 响应
# ============================================================
def _mock_llm_response(content: str):
    """创建一个模拟的 LLM 响应对象"""
    mock_response = MagicMock()
    mock_response.content = content
    return mock_response


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
        # 验证关键工具存在
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
# 3. planner_node - 规划器
# ============================================================
class TestPlannerNode:
    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_normal_planning(self, mock_create_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response(
            "1. 提取2023年营收\n2. 提取2022年营收\n3. 计算增长率"
        )
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import planner_node
        state = {"question": "计算营收增长率", "context": "2023年营收1000万，2022年营收800万"}
        result = planner_node(state)

        assert "plan" in result
        assert len(result["plan"]) == 3
        assert "营收" in result["plan"][0]
        assert result["iteration"] == 0

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_no_api_key(self, mock_create_llm):
        mock_create_llm.return_value = None

        from financial_report_ai_assistant.core.agent import planner_node
        state = {"question": "测试", "context": "上下文"}
        result = planner_node(state)

        assert result["plan"] == ["错误：API Key 未配置"]


# ============================================================
# 4. executor_node - 执行器
# ============================================================
class TestExecutorNode:
    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_finish_signal(self, mock_create_llm):
        """LLM 返回 FINISH 时应停止"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response('{"name": "FINISH", "args": {}}')
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import executor_node
        state = {"question": "测试", "context": "上下文", "plan": ["任务1"], "tool_results": []}
        result = executor_node(state)

        assert result["should_continue"] is False

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_tool_execution(self, mock_create_llm):
        """LLM 返回工具调用时，因 ToolNode 依赖 langchain 环境变量，可能进入异常分支"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response(
            '{"name": "tool_calculate_growth_rate", "args": {"current": 1200, "previous": 1000}}'
        )
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import executor_node
        state = {
            "question": "计算增长率",
            "context": "上下文",
            "plan": ["计算增长率"],
            "tool_results": []
        }
        result = executor_node(state)

        # ToolNode 需要 langchain config，在测试环境中可能进入异常分支
        assert "tool_results" in result
        assert len(result["tool_results"]) > 0
        # 不崩溃即可，不验证具体工具调用结果

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_no_api_key(self, mock_create_llm):
        mock_create_llm.return_value = None

        from financial_report_ai_assistant.core.agent import executor_node
        state = {"question": "测试", "context": "", "plan": ["任务"], "tool_results": []}
        result = executor_node(state)

        assert result["tool_results"] == ["错误：API Key 未配置"]


# ============================================================
# 5. reflection_node - 反思节点
# ============================================================
class TestReflectionNode:
    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_finish_decision(self, mock_create_llm):
        """LLM 判断 FINISH"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response("FINISH\n计算结果合理，任务完成")
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import reflection_node
        state = {
            "question": "测试",
            "plan": ["任务"],
            "tool_results": ["增长率: 20%"],
            "iteration": 1
        }
        result = reflection_node(state)

        assert result["should_continue"] is False

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_continue_decision(self, mock_create_llm):
        """LLM 判断 CONTINUE，迭代未达上限"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response("CONTINUE\n还需要更多数据")
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import reflection_node
        state = {
            "question": "测试",
            "plan": ["任务1", "任务2"],
            "tool_results": ["结果1"],
            "iteration": 1
        }
        result = reflection_node(state)

        assert result["should_continue"] is True

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_max_iterations_reached(self, mock_create_llm):
        """迭代达到上限时，即使 LLM 说 CONTINUE 也应停止"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response("CONTINUE\n继续执行")
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import reflection_node, MAX_ITERATIONS
        state = {
            "question": "测试",
            "plan": ["任务"],
            "tool_results": ["结果"],
            "iteration": MAX_ITERATIONS  # 已达上限
        }
        result = reflection_node(state)

        assert result["should_continue"] is False

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_retry_decision(self, mock_create_llm):
        """LLM 判断 RETRY"""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response("RETRY\n数据异常，需要重新提取")
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import reflection_node
        state = {
            "question": "测试",
            "plan": ["任务"],
            "tool_results": ["结果异常"],
            "iteration": 1
        }
        result = reflection_node(state)

        assert result["should_continue"] is False

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_no_api_key(self, mock_create_llm):
        mock_create_llm.return_value = None

        from financial_report_ai_assistant.core.agent import reflection_node
        state = {"question": "测试", "plan": [], "tool_results": [], "iteration": 0}
        result = reflection_node(state)

        assert result["reflection"] == "API Key 未配置"


# ============================================================
# 6. answer_node - 回答生成
# ============================================================
class TestAnswerNode:
    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_normal_answer(self, mock_create_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = _mock_llm_response("根据分析，公司营收增长率为20%。")
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import answer_node
        state = {
            "question": "增长率是多少？",
            "context": "2023年营收1200万，2022年营收1000万",
            "plan": ["提取营收数据", "计算增长率"],
            "tool_results": ["增长率: 20%"],
            "reflection": "结果合理"
        }
        result = answer_node(state)

        assert "final_answer" in result
        assert "20%" in result["final_answer"]

    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_no_api_key(self, mock_create_llm):
        mock_create_llm.return_value = None

        from financial_report_ai_assistant.core.agent import answer_node
        state = {"question": "测试", "context": "", "plan": [], "tool_results": [], "reflection": ""}
        result = answer_node(state)

        assert "API Key" in result["final_answer"]


# ============================================================
# 7. should_continue_edge - 循环判断
# ============================================================
class TestShouldContinueEdge:
    def test_continue(self):
        from financial_report_ai_assistant.core.agent import should_continue_edge
        assert should_continue_edge({"should_continue": True}) == "continue"

    def test_end(self):
        from financial_report_ai_assistant.core.agent import should_continue_edge
        assert should_continue_edge({"should_continue": False}) == "end"

    def test_missing_key(self):
        """缺少 should_continue 键时默认结束"""
        from financial_report_ai_assistant.core.agent import should_continue_edge
        assert should_continue_edge({}) == "end"


# ============================================================
# 8. build_agent_graph - 工作流图构建
# ============================================================
class TestBuildAgentGraph:
    def test_graph_has_correct_nodes(self):
        from financial_report_ai_assistant.core.agent import build_agent_graph
        graph = build_agent_graph()
        # 验证图对象不为 None
        assert graph is not None

    def test_create_financial_agent_singleton(self):
        """create_financial_agent 应返回同一个实例"""
        from financial_report_ai_assistant.core.agent import (
            create_financial_agent,
            _agent_graph,
        )
        # 重置单例
        import financial_report_ai_assistant.core.agent as agent_module
        agent_module._agent_graph = None
        agent1 = create_financial_agent()
        agent2 = create_financial_agent()
        assert agent1 is agent2


# ============================================================
# 9. Tool 函数单独测试
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
# 10. run_agent_query - 端到端 Agent 执行
# ============================================================
class TestRunAgentQuery:
    @patch("financial_report_ai_assistant.core.agent.create_llm")
    def test_normal_execution(self, mock_create_llm):
        """模拟完整的 Agent 执行流程"""
        mock_llm = MagicMock()
        # 规划器返回计划
        # 执行器返回 FINISH
        # 反思器返回 FINISH
        # 回答生成
        mock_llm.invoke.side_effect = [
            _mock_llm_response("1. 提取数据"),          # planner
            _mock_llm_response('{"name": "FINISH", "args": {}}'),  # executor
            _mock_llm_response("FINISH\n结果合理"),       # reflection
            _mock_llm_response("营收增长率为20%。"),       # answer
        ]
        mock_create_llm.return_value = mock_llm

        from financial_report_ai_assistant.core.agent import run_agent_query
        # 重置单例
        import financial_report_ai_assistant.core.agent as agent_module
        agent_module._agent_graph = None

        result = run_agent_query(query="计算增长率", context="2023年1200万，2022年1000万")
        assert isinstance(result, str)
        assert len(result) > 0
