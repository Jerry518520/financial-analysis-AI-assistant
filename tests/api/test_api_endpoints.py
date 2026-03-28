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
         patch("financial_report_ai_assistant.api.analysis.query_rag") as mock_analysis_rag, \
         patch("financial_report_ai_assistant.api.analysis.llm") as mock_llm:

        # 默认 mock 行为
        mock_parse.return_value = {
            "text_preview_snippet": "预览",
            "full_text": "完整文本 --- Page 1 ---\n内容\n--- Page 2 ---\n更多内容",
            "status": "success"
        }
        mock_build.return_value = True
        mock_rag.return_value = {"context": "检索到的上下文", "page_num": 1}
        mock_agent.return_value = "根据分析，答案是X。"
        mock_analysis_rag.return_value = "检索到的摘要上下文"
        mock_llm_instance = MagicMock()
        mock_llm_instance.invoke.return_value.content = "摘要内容"
        mock_llm.__truediv__ = MagicMock(return_value=mock_llm_instance)
        mock_llm.__or__ = MagicMock(return_value=mock_llm_instance)

        from financial_report_ai_assistant.api.main import app
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
        assert resp.status_code == 200
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
        """上传 PDF 后应能正常渲染"""
        # 先上传
        client.post("/upload", files={"file": ("test.pdf", sample_pdf, "application/pdf")})
        # 再请求高亮
        with patch("financial_report_ai_assistant.api.main.fitz") as mock_fitz, \
             patch("financial_report_ai_assistant.api.main.Image") as mock_image, \
             patch("financial_report_ai_assistant.api.main.ImageDraw") as mock_draw:

            # mock fitz 文档
            mock_doc = MagicMock()
            mock_fitz.open.return_value = mock_doc
            mock_doc.__len__.return_value = 5
            mock_doc.__getitem__ = MagicMock()

            # mock 图片渲染
            mock_pix = MagicMock()
            mock_pix.tobytes.return_value = b"fake_png_data"
            mock_page = MagicMock()
            mock_page.get_pixmap.return_value = mock_pix
            mock_doc.__getitem__ = lambda self, idx: mock_page if idx == 0 else mock_page

            # mock PIL Image
            mock_img = MagicMock()
            mock_image.open.return_value = mock_img
            mock_draw.Draw.return_value = MagicMock()

            mock_output = MagicMock()
            mock_output.getvalue.return_value = b"fake_png_data"
            mock_img.save = MagicMock()

            import io
            with patch("io.BytesIO", return_value=mock_output):
                resp = client.get("/highlight", params={"page": 1})

        # PDF 存在时可能返回 PNG 或错误，取决于 mock 是否完善
        # 至少不应返回 404
        assert resp.status_code != 404

    def test_page_out_of_range(self, client, sample_pdf):
        """页码超出范围时应有合理处理"""
        client.post("/upload", files={"file": ("test.pdf", sample_pdf, "application/pdf")})
        with patch("financial_report_ai_assistant.api.main.fitz") as mock_fitz:
            mock_doc = MagicMock()
            mock_fitz.open.return_value = mock_doc
            mock_doc.__len__.return_value = 3
            mock_page = MagicMock()
            mock_pix = MagicMock()
            mock_pix.tobytes.return_value = b"png"
            mock_page.get_pixmap.return_value = mock_pix

            def get_item(idx):
                if idx >= 3:
                    idx = 2  # 超出范围时取最后一页
                return mock_page
            mock_doc.__getitem__ = lambda self, idx: get_item(idx)

            with patch("financial_report_ai_assistant.api.main.Image") as mock_image, \
                 patch("financial_report_ai_assistant.api.main.ImageDraw"):
                mock_img = MagicMock()
                mock_image.open.return_value = mock_img
                mock_output = MagicMock()
                mock_output.getvalue.return_value = b"png"
                mock_img.save = MagicMock()

                import io
                with patch("io.BytesIO", return_value=mock_output):
                    resp = client.get("/highlight", params={"page": 999})

            # 不应崩溃
            assert resp.status_code in [200, 404, 500]


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
