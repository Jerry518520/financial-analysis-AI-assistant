"""
RAG 服务单元测试
覆盖 rag_service.py 中的文本切分、页码提取、预览等纯逻辑函数。
向量库构建和查询等依赖外部模型的函数通过 mock 测试。
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ============================================================
# 1. _extract_page_num - 页码提取
# ============================================================
class TestExtractPageNum:
    def test_normal_page(self):
        from financial_report_ai_assistant.services.rag_service import _extract_page_num
        assert _extract_page_num("--- Page 5 ---\n内容") == 5

    def test_page_1(self):
        from financial_report_ai_assistant.services.rag_service import _extract_page_num
        assert _extract_page_num("--- Page 1 ---\n内容") == 1

    def test_large_page_number(self):
        from financial_report_ai_assistant.services.rag_service import _extract_page_num
        assert _extract_page_num("--- Page 100 ---\n内容") == 100

    def test_no_page_marker(self):
        """没有页码标记时返回默认值 1"""
        from financial_report_ai_assistant.services.rag_service import _extract_page_num
        assert _extract_page_num("纯文本内容没有页码标记") == 1

    def test_empty_string(self):
        from financial_report_ai_assistant.services.rag_service import _extract_page_num
        assert _extract_page_num("") == 1

    def test_multiple_page_markers(self):
        """多个页码标记时取第一个"""
        from financial_report_ai_assistant.services.rag_service import _extract_page_num
        assert _extract_page_num("--- Page 3 ---\n--- Page 5 ---") == 3


# ============================================================
# 2. _split_by_page - 按页切分文本
# ============================================================
class TestSplitByPage:
    def test_normal_split(self):
        from financial_report_ai_assistant.services.rag_service import _split_by_page
        text = "--- Page 1 ---\n第一页内容\n--- Page 2 ---\n第二页内容\n--- Page 3 ---\n第三页内容"
        docs = _split_by_page(text)
        assert len(docs) == 3
        assert docs[0].metadata["page_num"] == 1
        assert docs[1].metadata["page_num"] == 2
        assert docs[2].metadata["page_num"] == 3
        assert "第一页内容" in docs[0].page_content

    def test_single_page(self):
        from financial_report_ai_assistant.services.rag_service import _split_by_page
        text = "--- Page 1 ---\n只有一页"
        docs = _split_by_page(text)
        assert len(docs) == 1

    def test_large_page_split(self):
        """超大页面应被分块"""
        from financial_report_ai_assistant.services.rag_service import _split_by_page
        large_content = "内容" * 2000  # 超过默认 max_chars_per_chunk=3000
        text = f"--- Page 1 ---\n{large_content}"
        docs = _split_by_page(text, max_chars_per_chunk=500)
        assert len(docs) > 1
        # 所有块都应标记为同一页
        for doc in docs:
            assert doc.metadata["page_num"] == 1

    def test_empty_text(self):
        from financial_report_ai_assistant.services.rag_service import _split_by_page
        docs = _split_by_page("")
        assert len(docs) == 0

    def test_no_page_markers(self):
        """没有 Page 标记时不产生任何文档"""
        from financial_report_ai_assistant.services.rag_service import _split_by_page
        docs = _split_by_page("纯文本没有页码标记")
        assert len(docs) == 0

    def test_empty_page_content(self):
        """空页内容应被跳过"""
        from financial_report_ai_assistant.services.rag_service import _split_by_page
        text = "--- Page 1 ---\n有效内容\n--- Page 2 ---\n\n--- Page 3 ---\n更多内容"
        docs = _split_by_page(text)
        assert len(docs) == 2
        assert docs[0].metadata["page_num"] == 1
        assert docs[1].metadata["page_num"] == 3

    def test_page_num_map_updated(self):
        """PAGE_NUM_MAP 应被正确更新"""
        import financial_report_ai_assistant.services.rag_service as rag_module
        text = "--- Page 1 ---\n内容A\n--- Page 2 ---\n内容B"
        rag_module._split_by_page(text)
        assert rag_module.PAGE_NUM_MAP[0] == 1
        assert rag_module.PAGE_NUM_MAP[1] == 2


# ============================================================
# 3. _rebuild_page_num_map - 重建页码映射
# ============================================================
class TestRebuildPageNumMap:
    def test_normal_rebuild(self):
        import financial_report_ai_assistant.services.rag_service as rag_module
        rag_module.PAGE_NUM_MAP = {}
        text = "--- Page 1 ---\n内容\n--- Page 2 ---\n内容\n--- Page 3 ---\n内容"
        rag_module._rebuild_page_num_map(text)
        assert len(rag_module.PAGE_NUM_MAP) == 3
        assert rag_module.PAGE_NUM_MAP[0] == 1
        assert rag_module.PAGE_NUM_MAP[2] == 3

    def test_empty_text(self):
        import financial_report_ai_assistant.services.rag_service as rag_module
        rag_module.PAGE_NUM_MAP = {0: 1, 1: 2}  # 先污染，再验证重建清空
        rag_module._rebuild_page_num_map("")
        assert len(rag_module.PAGE_NUM_MAP) == 0

    def test_skips_empty_pages(self):
        import financial_report_ai_assistant.services.rag_service as rag_module
        rag_module.PAGE_NUM_MAP = {}
        text = "--- Page 1 ---\n内容\n--- Page 2 ---\n\n--- Page 3 ---\n内容"
        rag_module._rebuild_page_num_map(text)
        assert len(rag_module.PAGE_NUM_MAP) == 2
        assert rag_module.PAGE_NUM_MAP[0] == 1
        assert rag_module.PAGE_NUM_MAP[1] == 3


# ============================================================
# 4. get_device - 设备检测
# ============================================================
class TestGetDevice:
    @patch("financial_report_ai_assistant.services.rag_service.torch.cuda.is_available")
    def test_cuda_available(self, mock_cuda):
        mock_cuda.return_value = True
        from financial_report_ai_assistant.services.rag_service import get_device
        assert get_device() == "cuda"

    @patch("financial_report_ai_assistant.services.rag_service.torch.cuda.is_available")
    def test_no_cuda_raises_error(self, mock_cuda):
        mock_cuda.return_value = False
        from financial_report_ai_assistant.services.rag_service import get_device
        with pytest.raises(RuntimeError, match="CUDA GPU"):
            get_device()


# ============================================================
# 5. preview_chunks - 预览切块
# ============================================================
class TestPreviewChunks:
    def test_normal_preview(self):
        from financial_report_ai_assistant.services.rag_service import preview_chunks
        text = "--- Page 1 ---\n第一页内容\n--- Page 2 ---\n第二页内容"
        chunks = preview_chunks(text)
        assert len(chunks) == 2

    def test_empty_text(self):
        from financial_report_ai_assistant.services.rag_service import preview_chunks
        chunks = preview_chunks("")
        assert len(chunks) == 0

    def test_custom_max_chars(self):
        """preview_chunks 不直接控制切块大小，切块大小由 _split_by_page 的 max_chars_per_chunk 控制"""
        from financial_report_ai_assistant.services.rag_service import preview_chunks
        large_content = "A" * 1000
        text = f"--- Page 1 ---\n{large_content}"
        chunks = preview_chunks(text, max_chars=100)
        # 1000字符 < 3000(max_chars_per_chunk)，不会分块，但会截断预览显示
        assert len(chunks) == 1


# ============================================================
# 6. query_rag - RAG 查询（mock vector_store）
# ============================================================
class TestQueryRag:
    @patch("financial_report_ai_assistant.services.rag_service.load_vector_store")
    def test_no_vector_store_and_no_cache(self, mock_load):
        """vector_store 为空且无法加载缓存"""
        mock_load.return_value = False
        import financial_report_ai_assistant.services.rag_service as rag_module
        rag_module.vector_store = None

        from financial_report_ai_assistant.services.rag_service import query_rag
        result = query_rag("测试问题")
        assert "知识库尚未建立" in result

    @patch("financial_report_ai_assistant.services.rag_service.load_vector_store")
    def test_successful_query(self, mock_load):
        """vector_store 为空但可以从缓存加载"""
        # 模拟一个成功的加载
        mock_store = MagicMock()
        mock_doc = MagicMock()
        mock_doc.page_content = "测试文档内容"
        mock_store.similarity_search.return_value = [mock_doc]

        import financial_report_ai_assistant.services.rag_service as rag_module
        rag_module.vector_store = mock_store

        from financial_report_ai_assistant.services.rag_service import query_rag
        result = query_rag("测试问题")
        assert "测试文档内容" in result


# ============================================================
# 7. query_rag_with_source - 带来源的 RAG 查询
# ============================================================
class TestQueryRagWithSource:
    @patch("financial_report_ai_assistant.services.rag_service.load_vector_store")
    def test_no_vector_store(self, mock_load):
        mock_load.return_value = False
        import financial_report_ai_assistant.services.rag_service as rag_module
        rag_module.vector_store = None

        from financial_report_ai_assistant.services.rag_service import query_rag_with_source
        result = query_rag_with_source("测试")
        assert result["context"] == "系统提示：知识库尚未建立。"
        assert result["page_num"] == 1

    @patch("financial_report_ai_assistant.services.rag_service.load_vector_store")
    def test_successful_query_with_source(self, mock_load):
        mock_store = MagicMock()
        mock_doc = MagicMock()
        mock_doc.page_content = "营收1000万"
        mock_doc.metadata = {"page_num": 5}
        mock_store.similarity_search.return_value = [mock_doc]

        import financial_report_ai_assistant.services.rag_service as rag_module
        rag_module.vector_store = mock_store

        from financial_report_ai_assistant.services.rag_service import query_rag_with_source
        result = query_rag_with_source("营收是多少")
        assert result["context"] == "营收1000万"
        assert result["page_num"] == 5

    @patch("financial_report_ai_assistant.services.rag_service.load_vector_store")
    def test_empty_search_results(self, mock_load):
        """搜索结果为空"""
        mock_store = MagicMock()
        mock_store.similarity_search.return_value = []

        import financial_report_ai_assistant.services.rag_service as rag_module
        rag_module.vector_store = mock_store

        from financial_report_ai_assistant.services.rag_service import query_rag_with_source
        result = query_rag_with_source("不存在的关键词")
        assert "未找到" in result["context"]

    @patch("financial_report_ai_assistant.services.rag_service.load_vector_store")
    def test_missing_page_num_metadata(self, mock_load):
        """文档缺少 page_num 元数据时应返回默认值 1"""
        mock_store = MagicMock()
        mock_doc = MagicMock()
        mock_doc.page_content = "内容"
        mock_doc.metadata = {}  # 缺少 page_num
        mock_store.similarity_search.return_value = [mock_doc]

        import financial_report_ai_assistant.services.rag_service as rag_module
        rag_module.vector_store = mock_store

        from financial_report_ai_assistant.services.rag_service import query_rag_with_source
        result = query_rag_with_source("测试")
        assert result["page_num"] == 1


# ============================================================
# 8. build_vector_store - 向量库构建（mock 外部依赖）
# ============================================================
class TestBuildVectorStore:
    @patch("financial_report_ai_assistant.services.rag_service.load_vector_store")
    def test_empty_text_returns_false(self, mock_load):
        """空文本应返回 False"""
        mock_load.return_value = False
        import financial_report_ai_assistant.services.rag_service as rag_module
        rag_module.vector_store = None

        from financial_report_ai_assistant.services.rag_service import build_vector_store
        result = build_vector_store("")
        assert result is False


# ============================================================
# 9. load_vector_store - 加载向量库
# ============================================================
class TestLoadVectorStore:
    @patch("financial_report_ai_assistant.services.rag_service.os.path.exists")
    def test_index_not_exists(self, mock_exists):
        mock_exists.return_value = False
        import financial_report_ai_assistant.services.rag_service as rag_module
        rag_module.vector_store = None

        from financial_report_ai_assistant.services.rag_service import load_vector_store
        result = load_vector_store()
        assert result is False
