import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../src")))

from financial_report_ai_assistant.services.document_parser import parse_pdf_bytes

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
        page1.get_text.return_value = "Page 1 Text"
        
        # Page 2: No table
        page2 = MagicMock()
        mock_tables2 = MagicMock()
        mock_tables2.tables = []
        page2.find_tables.return_value = mock_tables2
        page2.get_text.return_value = "Page 2 Text"
        
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
        
        # Check Page 1 used LlamaParse (should contain "Table Enhanced")
        self.assertIn("Table Enhanced", full_text)
        self.assertIn("LlamaParse Table Content", full_text)
        
        # Check Page 2 used direct text (should NOT contain "Table Enhanced")
        self.assertIn("Page 2", full_text)
        self.assertIn("Page 2 Text", full_text)
        self.assertNotIn("Page 2 (Table Enhanced)", full_text)
        
        # Check that LlamaParse was called
        mock_llama_parse.assert_called()
        
if __name__ == '__main__':
    unittest.main()
