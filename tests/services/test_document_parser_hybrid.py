import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src")))

from financial_report_ai_assistant.services.document_parser import parse_pdf_bytes, get_cache_path


def _make_single_page_mock(mock_fitz, text="<p>Page 1 Text</p>"):
    """构造一个「含表格、但 PyMuPDF 提取质量不佳」的单页 PDF mock。

    这样解析流程一定会走到 LlamaParse 分支，便于观察 parser 模式是否生效。
    """
    mock_doc = MagicMock()
    mock_fitz.open.return_value = mock_doc
    mock_doc.__len__.return_value = 1

    page = MagicMock()
    tables = MagicMock()
    table = MagicMock()
    table.cells = [1, 2, 3, 4, 5]  # > 4 cells
    tables.tables = [table]
    page.find_tables.return_value = tables
    page.get_text.return_value = text
    page.get_images.return_value = []  # 无图片，避免走进图表页分支

    mock_doc.__iter__.return_value = iter([page])
    mock_doc.__getitem__.side_effect = lambda idx: page
    return mock_doc


class TestParserMode(unittest.TestCase):
    """解析引擎选择（POST /upload?parser=）相关行为"""

    def test_cache_path_differs_per_mode(self):
        """不同解析引擎的缓存必须分开，避免换引擎后命中旧缓存"""
        self.assertNotEqual(get_cache_path(b"x", "hybrid"), get_cache_path(b"x", "pymupdf"))
        self.assertIn("hybrid", os.path.basename(get_cache_path(b"x", "hybrid")))
        self.assertIn("pymupdf", os.path.basename(get_cache_path(b"x", "pymupdf")))
        # 默认(不传 mode)保持历史文件名 parsed_hybrid_*.md，避免旧缓存失效
        self.assertIn("hybrid", os.path.basename(get_cache_path(b"x")))

    @patch('financial_report_ai_assistant.services.document_parser.fitz')
    @patch('financial_report_ai_assistant.services.document_parser.LlamaParse')
    @patch('financial_report_ai_assistant.services.document_parser.os.path.exists')
    @patch('financial_report_ai_assistant.services.document_parser.os.getenv')
    @patch('builtins.open', new_callable=MagicMock)
    def test_pymupdf_mode_skips_llamaparse(self, mock_open, mock_getenv, mock_exists,
                                           mock_llama_parse, mock_fitz):
        """选择「仅 PyMuPDF」时，任何情况下都不应调用 LlamaParse"""
        mock_exists.return_value = False
        mock_getenv.return_value = "fake_key"
        _make_single_page_mock(mock_fitz)

        result = parse_pdf_bytes(b"fake_content", parser="pymupdf")

        self.assertEqual(result["status"], "success")
        mock_llama_parse.assert_not_called()

    @patch('financial_report_ai_assistant.services.document_parser.fitz')
    @patch('financial_report_ai_assistant.services.document_parser.LlamaParse')
    @patch('financial_report_ai_assistant.services.document_parser.os.path.exists')
    @patch('financial_report_ai_assistant.services.document_parser.os.getenv')
    @patch('builtins.open', new_callable=MagicMock)
    def test_unknown_parser_falls_back_to_auto(self, mock_open, mock_getenv, mock_exists,
                                               mock_llama_parse, mock_fitz):
        """未知引擎值（如已下线的 kimi/mimo）应安全回退为 auto，不报错"""
        mock_exists.return_value = False
        mock_getenv.return_value = "fake_key"
        _make_single_page_mock(mock_fitz)

        result = parse_pdf_bytes(b"fake_content", parser="kimi")

        self.assertEqual(result["status"], "success")
        # 回退到 auto → 与默认行为一致，表格页仍会尝试 LlamaParse
        mock_llama_parse.assert_called()

class TestHybridParser(unittest.TestCase):
    
    @patch('financial_report_ai_assistant.services.document_parser.fitz')
    @patch('financial_report_ai_assistant.services.document_parser.LlamaParse')
    @patch('financial_report_ai_assistant.services.document_parser.os.path.exists')
    @patch('financial_report_ai_assistant.services.document_parser.os.getenv')
    @patch('builtins.open', new_callable=MagicMock) # Patch built-in open globally for simplicity or specifically
    def test_hybrid_logic(self, mock_open, mock_getenv, mock_exists, mock_llama_parse, mock_fitz):
        # Setup mocks
        mock_exists.return_value = False # No cache
        mock_getenv.return_value = "fake_key"
        
        # Mock PDF Document
        mock_doc = MagicMock()
        mock_fitz.open.return_value = mock_doc
        mock_doc.__len__.return_value = 2
        
        # Page 1: Has table
        page1 = MagicMock()
        table1 = MagicMock()
        table1.cells = [1, 2, 3, 4, 5] # > 4 cells
        mock_tables1 = MagicMock()
        mock_tables1.tables = [table1]
        page1.find_tables.return_value = mock_tables1
        # _get_page_text 调用 get_text("html") 后用 regex 提取，需返回 HTML 格式
        page1.get_text.return_value = "<p>Page 1 Text</p>"
        page1.get_images.return_value = []  # 无图片，避免图片检测逻辑误触发

        # Page 2: No table
        page2 = MagicMock()
        mock_tables2 = MagicMock()
        mock_tables2.tables = []
        page2.find_tables.return_value = mock_tables2
        page2.get_text.return_value = "<p>Page 2 Text</p>"
        page2.get_images.return_value = []  # 无图片
        
        # Setup iteration
        mock_doc.__iter__.return_value = iter([page1, page2])
        # Setup indexing
        def get_page(idx):
            if idx == 0: return page1
            if idx == 1: return page2
            raise IndexError
        mock_doc.__getitem__.side_effect = get_page

        # Mock LlamaParse
        mock_parser_instance = MagicMock()
        mock_llama_parse.return_value = mock_parser_instance
        mock_llama_doc = MagicMock()
        mock_llama_doc.text = "LlamaParse Table Content"
        mock_parser_instance.load_data.return_value = [mock_llama_doc]

        # Execute
        # We need to mock open for writing cache too, but we can just let the mock handle it
        result = parse_pdf_bytes(b"fake_content")
        
        # Verify
        if result.get("status") == "error":
            print("Error:", result.get("error"))
        
        self.assertEqual(result["status"], "success")
        full_text = result["full_text"]
        
        # Check Page 1 used LlamaParse (should contain "LlamaParse Enhanced")
        self.assertIn("LlamaParse Enhanced", full_text)
        self.assertIn("LlamaParse Table Content", full_text)

        # Check Page 2 used direct text (should NOT contain "LlamaParse Enhanced")
        self.assertIn("Page 2", full_text)
        self.assertIn("Page 2 Text", full_text)
        self.assertNotIn("Page 2 (LlamaParse Enhanced)", full_text)
        
        # Check that LlamaParse was called
        mock_llama_parse.assert_called()
        
if __name__ == '__main__':
    unittest.main()
