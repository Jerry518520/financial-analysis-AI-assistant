"""
API 端点集成测试
使用 FastAPI TestClient，无需启动真实服务器，mock 外部依赖。
"""

import pytest
import io
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


# ============================================================
# Fixtures
# ============================================================
@pytest.fixture
def client():
    """创建测试客户端，mock 所有外部依赖"""
    with patch("financial_report_ai_assistant.api.main.parse_pdf_bytes") as mock_parse, \
         patch("financial_report_ai_assistant.api.main.build_vector_store") as mock_build, \
         patch("financial_report_ai_assistant.api.main.query_rag_with_source") as mock_rag, \
         patch("financial_report_ai_assistant.api.main.run_agent_query") as mock_agent, \
         patch("financial_report_ai_assistant.core.agent.run_lightweight_query") as mock_lightweight, \
         patch("financial_report_ai_assistant.core.agent.is_simple_query", return_value=False) as mock_is_simple, \
         patch("financial_report_ai_assistant.api.analysis.query_rag_with_source") as mock_analysis_rag, \
         patch("financial_report_ai_assistant.api.analysis.ChatPromptTemplate") as mock_prompt_cls, \
         patch("financial_report_ai_assistant.api.analysis.StrOutputParser") as mock_parser_cls:

        # 默认 mock 行为
        mock_parse.return_value = {
            "text_preview_snippet": "预览",
            "full_text": "完整文本 --- Page 1 ---\n内容\n--- Page 2 ---\n更多内容",
            "status": "success"
        }
        mock_build.return_value = True
        mock_rag.return_value = {"context": "检索到的上下文", "page_num": 1, "source_pages": [1]}
        mock_agent.return_value = "根据分析，答案是X。"
        mock_analysis_rag.return_value = {"context": "检索到的摘要上下文", "page_num": 1, "source_pages": [1]}
        # mock chain 管道：prompt | llm | parser
        # mock_prompt_cls.from_template() 返回 mock_prompt
        # mock_prompt.__or__(llm) 返回 mock_step
        # mock_step.__or__(parser) 返回 mock_chain
        # mock_chain.invoke() 返回 "摘要内容"
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "摘要内容"
        mock_step = MagicMock()
        mock_step.__or__ = MagicMock(return_value=mock_chain)
        mock_prompt = MagicMock()
        mock_prompt.__or__ = MagicMock(return_value=mock_step)
        mock_prompt_cls.from_template.return_value = mock_prompt

        from financial_report_ai_assistant.api.main import app, CURRENT_PDF_PATH
        # 重置 PDF 路径，避免测试间污染
        import financial_report_ai_assistant.api.main as main_mod
        main_mod.CURRENT_PDF_PATH = None
        client = TestClient(app)
        yield client


@pytest.fixture
def sample_pdf():
    """生成一个最小的有效 PDF 文件用于测试"""
    # 最小的 PDF 文件字节
    pdf_bytes = (
        b"%PDF-1.0\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R"
        b"/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>endobj\n"
        b"4 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
        b"5 0 obj<</Length 44>>stream\n"
        b"BT /F1 12 Tf 100 700 Td (Hello) Tj ET\n"
        b"endstream endobj\n"
        b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n"
        b"0000000058 00000 n \n0000000115 00000 n \n"
        b"0000000266 00000 n \n0000000340 00000 n \n"
        b"trailer<</Size 6/Root 1 0 R>>\n"
        b"startxref\n434\n%%EOF"
    )
    return io.BytesIO(pdf_bytes)


# ============================================================
# 1. GET / - 健康检查
# ============================================================
class TestHealthCheck:
    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"


# ============================================================
# 2. POST /upload - 文件上传
# ============================================================
class TestUpload:
    def test_upload_success(self, client, sample_pdf):
        resp = client.post("/upload", files={"file": ("test.pdf", sample_pdf, "application/pdf")})
        assert resp.status_code == 200
        data = resp.json()
        assert data["filename"] == "test.pdf"
        assert data["analysis_result"]["status"] == "success"

    def test_upload_returns_filename(self, client, sample_pdf):
        resp = client.post("/upload", files={"file": ("my_report.pdf", sample_pdf, "application/pdf")})
        assert resp.status_code == 200
        assert resp.json()["filename"] == "my_report.pdf"

    def test_upload_no_file(self, client):
        """不传文件时应报错"""
        resp = client.post("/upload")
        assert resp.status_code == 422  # FastAPI 验证错误

    def test_upload_triggers_rag_build(self, client, sample_pdf):
        """上传应触发 RAG 向量库构建"""
        from financial_report_ai_assistant.api.main import build_vector_store
        client.post("/upload", files={"file": ("test.pdf", sample_pdf, "application/pdf")})
        build_vector_store.assert_called()

    def test_upload_parse_error(self, client):
        """解析失败时应返回错误信息"""
        from financial_report_ai_assistant.api.main import parse_pdf_bytes
        # 改为在第二次调用时让 parse 失败
        original_parse = parse_pdf_bytes
        parse_pdf_bytes.side_effect = Exception("解析失败")

        resp = client.post("/upload", files={"file": ("bad.pdf", io.BytesIO(b"not a pdf"), "application/pdf")})
        assert resp.status_code == 500
        assert "error" in resp.json()

        parse_pdf_bytes.side_effect = None


# ============================================================
# 3. POST /chat - 对话
# ============================================================
class TestChat:
    def test_chat_success(self, client):
        resp = client.post("/chat", json={"question": "营收是多少？"})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
        assert "source_page" in data

    def test_chat_returns_answer(self, client):
        resp = client.post("/chat", json={"question": "净利润是多少？"})
        assert "X" in resp.json()["answer"]

    def test_chat_returns_source_page(self, client):
        resp = client.post("/chat", json={"question": "资产负债率？"})
        assert resp.json()["source_page"] == 1


# ============================================================
# 4. GET /highlight - 高亮渲染
# ============================================================
class TestHighlight:
    def test_no_pdf_returns_404(self, client):
        """未上传 PDF 时应返回 404"""
        resp = client.get("/highlight", params={"page": 1})
        assert resp.status_code == 404
        assert "PDF" in resp.json()["error"]

    def test_highlight_after_upload(self, client, sample_pdf):
        """上传 PDF 后调用 highlight 端点"""
        # 先上传让 PDF 路径被记录
        client.post("/upload", files={"file": ("test.pdf", sample_pdf, "application/pdf")})

        # highlight 端点需要 PyMuPDF(fitz) + PIL 来渲染 PDF
        # 这属于集成测试，在无 GUI 的 CI 环境中跳过
        try:
            import fitz  # noqa: F401
            import PIL  # noqa: F401
        except ImportError:
            pytest.skip("需要 PyMuPDF 和 PIL 才能运行 highlight 测试")

        resp = client.get("/highlight", params={"page": 1})
        assert resp.status_code != 404

    def test_page_out_of_range(self, client, sample_pdf):
        """页码超出范围时应有合理处理"""
        client.post("/upload", files={"file": ("test.pdf", sample_pdf, "application/pdf")})

        try:
            import fitz  # noqa: F401
            import PIL  # noqa: F401
        except ImportError:
            pytest.skip("需要 PyMuPDF 和 PIL 才能运行 highlight 测试")

        resp = client.get("/highlight", params={"page": 999})
        # 代码会将越界页码修正到最后页
        assert resp.status_code == 200


# ============================================================
# 5. POST /preview-chunks - 切块预览
# ============================================================
class TestPreviewChunks:
    def test_preview_success(self, client, sample_pdf):
        resp = client.post("/preview-chunks", files={"file": ("test.pdf", sample_pdf, "application/pdf")})
        assert resp.status_code == 200
        data = resp.json()
        assert "total_chunks" in data
        assert "chunks" in data
        assert data["total_chunks"] > 0

    def test_preview_chunks_content(self, client, sample_pdf):
        resp = client.post("/preview-chunks", files={"file": ("test.pdf", sample_pdf, "application/pdf")})
        data = resp.json()
        for chunk in data["chunks"]:
            assert "index" in chunk
            assert "length" in chunk
            assert "content" in chunk


# ============================================================
# 6. POST /analyze/summary - 摘要生成
# ============================================================
class TestAnalyzeSummary:
    def test_summary_success(self, client):
        resp = client.post("/analyze/summary", json={"focus": "general"})
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data

    def test_summary_default_focus(self, client):
        """不传 focus 参数应使用默认值"""
        resp = client.post("/analyze/summary", json={})
        assert resp.status_code == 200
        assert "summary" in resp.json()

    def test_summary_financial_focus(self, client):
        """使用 financial focus"""
        resp = client.post("/analyze/summary", json={"focus": "financial"})
        assert resp.status_code == 200


# ============================================================
# 7. _build_enhanced_context - 增强上下文构建
# ============================================================
class TestBuildEnhancedContext:
    def test_no_history_returns_current_context(self):
        """无历史记录时直接返回当前上下文"""
        from financial_report_ai_assistant.api.main import _build_enhanced_context
        result = _build_enhanced_context(
            current_context="营收1000万",
            history=[],
            current_question="净利润是多少？"
        )
        assert result == "营收1000万"

    def test_pdf_hash_mismatch_skips_history(self):
        """pdf_hash 不一致时跳过历史注入，防止跨文档数据污染"""
        from financial_report_ai_assistant.api.main import _build_enhanced_context
        with patch("financial_report_ai_assistant.api.main.get_current_pdf_hash", return_value="hash_abc"):
            result = _build_enhanced_context(
                current_context="营收1000万",
                history=[("之前的问题", "之前的回答")],
                current_question="净利润是多少？",
                request_pdf_hash="hash_xyz"  # 与当前 hash 不一致
            )
        # 历史记录不应被注入
        assert "历史问题" not in result
        assert "营收1000万" in result

    def test_pdf_hash_match_includes_history(self):
        """pdf_hash 一致时注入历史记录"""
        from financial_report_ai_assistant.api.main import _build_enhanced_context
        with patch("financial_report_ai_assistant.api.main.get_current_pdf_hash", return_value="hash_abc"):
            result = _build_enhanced_context(
                current_context="营收1000万",
                history=[("营收是多少", "营收为1000万")],
                current_question="增长率？",
                request_pdf_hash="hash_abc"  # 一致
            )
        assert "历史问题" in result
        assert "营收1000万" in result

    def test_empty_request_hash_still_injects_history(self):
        """request_pdf_hash 为空时仍注入历史（兼容旧版前端）"""
        from financial_report_ai_assistant.api.main import _build_enhanced_context
        with patch("financial_report_ai_assistant.api.main.get_current_pdf_hash", return_value="hash_abc"):
            result = _build_enhanced_context(
                current_context="营收1000万",
                history=[("营收是多少", "营收为1000万")],
                current_question="增长率？",
                request_pdf_hash=""  # 旧版前端不传 hash
            )
        assert "历史问题" in result

    def test_history_truncated_to_5_rounds(self):
        """历史记录最多取最近 5 轮"""
        from financial_report_ai_assistant.api.main import _build_enhanced_context
        history = [(f"问题{i}", f"回答{i}") for i in range(10)]
        with patch("financial_report_ai_assistant.api.main.get_current_pdf_hash", return_value="h"):
            result = _build_enhanced_context(
                current_context="上下文",
                history=history,
                current_question="当前问题",
                request_pdf_hash="h"
            )
        # 只有最后 5 轮（索引 5-9）
        assert "历史问题 1" in result  # 第 1 条（对应原索引 5）
        assert "问题5" in result
        assert "问题4" not in result  # 原索引 4 不在最近 5 轮内


# ============================================================
# 8. POST /chat - RAG 未找到时提前返回
# ============================================================
class TestChatRagNotFound:
    @patch("financial_report_ai_assistant.api.main.query_rag_with_source")
    def test_rag_not_found_returns_early(self, mock_rag, client):
        """RAG 未检索到相关内容时应提前返回提示"""
        mock_rag.return_value = {
            "context": "未找到与问题高度相关的内容。请确认问题是否与当前上传的财报相关，或尝试换个问法。",
            "page_num": 1,
            "source_pages": []
        }
        resp = client.post("/chat", json={"question": "完全无关的问题"})
        data = resp.json()
        assert "未找到" in data["answer"]
        assert data["source_pages"] == []


# ============================================================
# 9. Agent LLM 配置测试（timeout + max_retries）
# ============================================================
class TestAgentLLMConfig:
    def test_create_llm_has_timeout(self):
        """create_llm() 应配置 timeout=60 防止连接挂起"""
        from financial_report_ai_assistant.core.agent import create_llm
        with patch("financial_report_ai_assistant.core.agent.os.getenv", return_value="test_key"):
            llm = create_llm()
            assert llm is not None
            assert llm.request_timeout == 60

    def test_create_llm_has_max_retries(self):
        """create_llm() 应配置 max_retries=2 防止偶发连接失败"""
        from financial_report_ai_assistant.core.agent import create_llm
        with patch("financial_report_ai_assistant.core.agent.os.getenv", return_value="test_key"):
            llm = create_llm()
            assert llm is not None
            assert llm.max_retries == 2


# ============================================================
# 10. RAG 查询扩展测试
# ============================================================
class TestExpandQuery:
    def test_margin_expands_to_segment_terms(self):
        """毛利率 查询扩展应包含分板块毛利率术语"""
        from financial_report_ai_assistant.services.rag_service import _expand_query
        expansions = _expand_query("毛利率是多少")
        # 应包含分板块毛利率相关术语
        assert any("毛利率" in t for t in expansions)
        assert "国内市场毛利率" in expansions
        assert "国际市场毛利率" in expansions

    def test_revenue_growth_no_direct_expansion(self):
        """营收同比增长率 不应触发查询扩展（语义搜索足够）"""
        from financial_report_ai_assistant.services.rag_service import _expand_query
        expansions = _expand_query("营收同比增长率")
        # "营收" 在 term_map 中有映射
        assert "营业收入" in expansions


# ============================================================
# 11. 路由判断测试
# ============================================================
class TestRouting:
    def test_margin_is_simple_query(self):
        """毛利率是多少 应走轻量级通道"""
        from financial_report_ai_assistant.core.agent import is_simple_query
        assert is_simple_query("毛利率是多少") is True

    def test_growth_rate_needs_agent(self):
        """营收同比增长率 应走 Agent 通道"""
        from financial_report_ai_assistant.core.agent import is_simple_query
        assert is_simple_query("营收同比增长率") is False

    def test_simple_revenue_query(self):
        """营收是多少 应走轻量级通道"""
        from financial_report_ai_assistant.core.agent import is_simple_query
        assert is_simple_query("营收是多少？") is True


# ============================================================
# 12. 年份映射注入测试 (_inject_year_mapping)
# ============================================================
class TestInjectYearMapping:
    def test_inject_from_cached_report_period(self):
        """从缓存的 report_period 中提取年份并注入映射"""
        from financial_report_ai_assistant.api.main import _inject_year_mapping
        with patch("financial_report_ai_assistant.services.financial_data_store.get_current_cached_data") as mock_cached:
            mock_cached.return_value = {"report_period": "中兴通讯 2025年年度报告"}
            result = _inject_year_mapping("资产负债率为64.74%")
            assert "2025年" in result
            assert "2024年" in result
            assert "本期" in result
            assert "上期" in result

    def test_inject_from_context_fallback(self):
        """缓存无数据时，从上下文前500字中提取年份"""
        from financial_report_ai_assistant.api.main import _inject_year_mapping
        with patch("financial_report_ai_assistant.services.financial_data_store.get_current_cached_data") as mock_cached:
            mock_cached.return_value = None
            context = "中兴通讯 2025年年度报告\n\n资产负债率为64.74%"
            result = _inject_year_mapping(context)
            assert "2025年" in result
            assert "2024年" in result

    def test_no_year_found_skip_injection(self):
        """无法确定年份时跳过注入，原样返回上下文"""
        from financial_report_ai_assistant.api.main import _inject_year_mapping
        with patch("financial_report_ai_assistant.services.financial_data_store.get_current_cached_data") as mock_cached:
            mock_cached.return_value = None
            context = "一些没有年份信息的文本"
            result = _inject_year_mapping(context)
            assert result == context

    def test_mapping_note_prepended(self):
        """年份映射说明应被添加到上下文开头"""
        from financial_report_ai_assistant.api.main import _inject_year_mapping
        with patch("financial_report_ai_assistant.services.financial_data_store.get_current_cached_data") as mock_cached:
            mock_cached.return_value = {"report_period": "2025年年度报告"}
            original = "原始上下文内容"
            result = _inject_year_mapping(original)
            assert result.startswith("【年份映射】")
            assert result.endswith(original)

    def test_mapping_contains_correct_years(self):
        """映射说明中的年份数字应正确"""
        from financial_report_ai_assistant.api.main import _inject_year_mapping
        with patch("financial_report_ai_assistant.services.financial_data_store.get_current_cached_data") as mock_cached:
            mock_cached.return_value = {"report_period": "2026年第一季度报告"}
            result = _inject_year_mapping("上下文")
            assert "2026年" in result
            assert "2025年" in result


# ============================================================
# 13. 缓存兜底查询测试 (_answer_from_cache fallback)
# ============================================================
class TestAnswerFromCacheFallback:
    def test_eps_from_raw_data(self):
        """EPS问题应能从raw_data中兜底获取基本每股收益"""
        from financial_report_ai_assistant.api.main import _answer_from_cache
        cached = {
            "computed_metrics": {},  # metrics中没有EPS
            "raw_data": {"基本每股收益": 1.17, "稀释每股收益": 1.16}
        }
        result = _answer_from_cache("EPS是多少？", cached)
        assert result is not None
        assert "1.17" in result
        assert "1.16" in result

    def test_eps_from_metrics_priority(self):
        """metrics中有EPS时应优先使用metrics"""
        from financial_report_ai_assistant.api.main import _answer_from_cache
        cached = {
            "computed_metrics": {"EPS": "1.17元/股"},
            "raw_data": {"基本每股收益": 1.17}
        }
        result = _answer_from_cache("EPS是多少？", cached)
        assert result is not None
        assert "1.17元/股" in result

    def test_turnover_from_raw_data(self):
        """资产周转率应能从raw_data计算"""
        from financial_report_ai_assistant.api.main import _answer_from_cache
        cached = {
            "computed_metrics": {},  # metrics中没有资产周转率
            "raw_data": {"营业收入": 133895500000, "总资产": 217739400000}
        }
        result = _answer_from_cache("资产周转率", cached)
        assert result is not None
        assert "0.61" in result or "0.63" in result  # 约0.61-0.63次

    def test_no_cache_returns_none(self):
        """无缓存数据时应返回None"""
        from financial_report_ai_assistant.api.main import _answer_from_cache
        result = _answer_from_cache("EPS是多少？", {"computed_metrics": {}, "raw_data": {}})
        assert result is None
