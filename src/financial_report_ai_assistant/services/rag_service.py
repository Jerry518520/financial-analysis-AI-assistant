# 文件: src/financial_report_ai_assistant/services/rag_service.py
import torch
import os
import re
import threading
from pathlib import Path
from typing import List, Dict, Any

# 配置 HuggingFace 镜像
os.environ["HF_HUB_URL"] = "https://hf-mirror.com"
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document


class SentenceTransformerEmbeddings(Embeddings):
    def __init__(self, model_name: str, device: str = None):
        if device is None:
            try:
                device = get_device()
            except RuntimeError:
                print("[WARN] CUDA 不可用，回退到 CPU（向量化会很慢）")
                device = "cpu"
        # 优先使用本地缓存，避免联网下载超时
        try:
            self.model = SentenceTransformer(model_name, device=device, local_files_only=True)
            print(f"[OK] 模型从本地缓存加载: {model_name}")
        except Exception:
            print(f"[WARN] 本地缓存未命中，尝试联网下载: {model_name}")
            self.model = SentenceTransformer(model_name, device=device)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()

vector_store = None
_vector_store_lock = threading.Lock()  # 保护 vector_store 的并发读写
PAGE_NUM_MAP: Dict[int, int] = {}
_current_pdf_hash: str = ""  # 当前向量库对应的 PDF 哈希，用于检测文档切换
_pending_pdf_hash: str = ""  # 正在构建索引的 PDF 哈希，防止构建期间查询命中旧索引
PROJECT_ROOT = Path(__file__).parent.parent.parent

# RAG 查询结果状态常量（供 main.py / analysis.py 使用）
RAG_NOT_FOUND = "未找到"
RAG_INDEX_MISSING = "系统提示：知识库尚未建立"
RAG_INDEX_BUILDING = "系统提示：新文档正在处理中"

# Docker 挂载: ./faiss_index:/app/faiss_index
# 本地开发: PROJECT_ROOT / "faiss_index"
# 通过环境变量或固定路径 /app/faiss_index 统一
INDEX_PATH = Path(os.environ.get("FAISS_INDEX_PATH", str(PROJECT_ROOT / "faiss_index")))
INDEX_HASH_PATH = INDEX_PATH / ".pdf_hash"  # 记录当前索引对应哪个 PDF

def get_device():
    """
    获取计算设备。必须有 CUDA GPU，否则直接报错终止。
    向量化 BGE-M3 模型在 CPU 上极其缓慢，不适合生产使用。
    """
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        print(f"[GPU] 检测到 GPU: {device_name}")
        return "cuda"
    else:
        raise RuntimeError(
            "[ERR] 未检测到 CUDA GPU！RAG 向量化需要 GPU 加速。\n"
            "请检查：\n"
            "1. 是否安装了 NVIDIA 驱动\n"
            "2. 是否安装了 CUDA Toolkit\n"
            "3. 是否安装了支持 CUDA 的 PyTorch (pip install torch --index-url https://download.pytorch.org/whl/cu118)"
        )

def preview_chunks(full_text: str, max_chars: int = 500):
    """预览切块效果（简单按页切分）"""
    docs = _split_by_page(full_text)
    print(f"[STAT] 切块预览 | 总计 {len(docs)} 个块\n")
    for i, doc in enumerate(docs):
        page = doc.metadata.get("page_num", "?")
        content = doc.page_content[:max_chars] + "..." if len(doc.page_content) > max_chars else doc.page_content
        print(f"--- 块 {i+1}/{len(docs)} (页码: {page}, 长度: {len(doc.page_content)} 字符) ---")
        print(content)
        print()
    return [doc.page_content for doc in docs]

def _split_by_page(full_text: str, max_chars_per_chunk: int = 3000) -> List[Document]:
    """按 PDF 页切分文本，每块记录 page_num
    
    【修复】改进表格数据处理：
    1. 识别表格标记，尽量保持表格完整性
    2. 表格内容不切分，避免数据断裂
    3. 增强表格行的上下文信息
    """
    global PAGE_NUM_MAP
    PAGE_NUM_MAP = {}

    # 【修复】兼容 \r\n 和末尾无换行符的情况
    page_pattern = r'--- Page (\d+)(?:\s*\([^)]*\))?\s*---\r?\n'
    parts = re.split(page_pattern, full_text)

    documents = []
    doc_index = 0

    i = 1
    while i < len(parts):
        page_num = int(parts[i])
        content = parts[i + 1] if i + 1 < len(parts) else ""

        if content.strip():
            # 【修复】检测是否为表格内容（包含 markdown 表格标记或财务关键词）
            is_table = _is_table_content(content)
            
            if is_table:
                # 【修复】先压缩表格中的空单元格，减少 embedding 噪音
                compressed_content = _compress_markdown_table(content)

                # 【修复】超长表格按行拆分（每 20 行一个 chunk），避免单 chunk 过大导致 embedding 稀释
                if len(compressed_content) > max_chars_per_chunk:
                    table_chunks = _split_table_by_rows(compressed_content, page_num, rows_per_chunk=20)
                    for chunk_text in table_chunks:
                        enhanced = _enhance_table_content(chunk_text, page_num)
                        doc = Document(page_content=enhanced, metadata={"page_num": page_num, "type": "table"})
                        documents.append(doc)
                        PAGE_NUM_MAP[doc_index] = page_num
                        doc_index += 1
                else:
                    # 短表格：保持完整
                    enhanced_content = _enhance_table_content(compressed_content, page_num)
                    doc = Document(page_content=enhanced_content, metadata={"page_num": page_num, "type": "table"})
                    documents.append(doc)
                    PAGE_NUM_MAP[doc_index] = page_num
                    doc_index += 1

                # 【关键修复】提取关键财务指标行作为独立 chunk，提高检索精度
                # 整页表格的 embedding 容易被大量数字和空单元格稀释语义，
                # 独立的关键行 chunk 能让"资产总额"等词获得更高的检索相似度
                # 【修复】传入未压缩 content 用于表头提取，保持列对齐
                key_rows = _extract_key_table_rows(content, page_num)
                for row_text in key_rows:
                    documents.append(Document(page_content=row_text, metadata={"page_num": page_num, "type": "table_row"}))
                    PAGE_NUM_MAP[doc_index] = page_num
                    doc_index += 1
            elif len(content) > max_chars_per_chunk:
                # 普通长文本：按长度切分
                sub_chunks = [content[j:j+max_chars_per_chunk] for j in range(0, len(content), max_chars_per_chunk)]
                for sub_chunk in sub_chunks:
                    doc = Document(page_content=sub_chunk.strip(), metadata={"page_num": page_num, "type": "text"})
                    documents.append(doc)
                    PAGE_NUM_MAP[doc_index] = page_num
                    doc_index += 1
            else:
                # 普通短文本：保持完整
                doc = Document(page_content=content.strip(), metadata={"page_num": page_num, "type": "text"})
                documents.append(doc)
                PAGE_NUM_MAP[doc_index] = page_num
                doc_index += 1
        i += 2

    return documents


def _compress_markdown_table(content: str) -> str:
    """压缩 markdown 表格中的空单元格，减少 embedding 噪音。
    
    例如：资产总额 |  |  | 217,739.4 | 207,323.2 |  |  | 5.02% | 200,958.3 |
    压缩后：资产总额 | 217,739.4 | 207,323.2 | 5.02% | 200,958.3 |
    """
    lines = content.split('\n')
    result = []
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped.startswith('|'):
            result.append(line)
            continue
        cells = [c.strip() for c in line_stripped.split('|')]
        # 去掉空字符串（由开头/结尾的 | 产生的）和纯空单元格
        cells = [c for c in cells if c]
        if cells:
            result.append('| ' + ' | '.join(cells) + ' |')
    return '\n'.join(result)


def _split_table_by_rows(content: str, page_num: int, rows_per_chunk: int = 20) -> List[str]:
    """将大表格按行数拆分为多个子 chunk，每个 chunk 前附加表头行。

    解决超长表格（100+ 行）作为单个 chunk 时 embedding 语义稀释的问题。
    每个子 chunk 包含表头 + rows_per_chunk 行数据，保持表格结构完整。
    """
    lines = content.split('\n')

    # 提取表头行（第一个非分隔、非空的 | 开头行）和分隔行
    header_line = ""
    separator_line = ""
    data_lines = []
    header_found = False

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped.startswith('|'):
            continue
        if re.match(r'^\|[-\s|]+\|$', line_stripped):
            if header_found:
                separator_line = line_stripped
            continue
        cells = [c.strip() for c in line_stripped.split('|')]
        cells = [c for c in cells if c]
        if not cells:
            continue
        if not header_found:
            header_line = line_stripped
            header_found = True
        else:
            data_lines.append(line_stripped)

    if not header_line or not data_lines:
        return [content]

    # 按 rows_per_chunk 拆分数据行
    chunks = []
    for start in range(0, len(data_lines), rows_per_chunk):
        chunk_lines = [header_line]
        if separator_line:
            chunk_lines.append(separator_line)
        chunk_lines.extend(data_lines[start:start + rows_per_chunk])
        chunks.append('\n'.join(chunk_lines))

    return chunks


# 财务指标行 → 可用于计算的财务指标标签映射
# 作用：让关键行 chunk 在检索时能被对应的查询词高相似度命中
_ROW_METRIC_TAGS = {
    "存货": "存货周转率 速动比率 流动比率",
    "营业成本": "存货周转率 毛利率",
    "营业收入": "资产周转率 净利率 毛利率 营收增长率",
    "营业总收入": "资产周转率 净利率 毛利率 营收增长率",
    "净利润": "净利率 ROE EPS ROA",
    "归母净利润": "净利率 ROE EPS",
    "利润总额": "净利率",
    "营业利润": "净利率",
    "毛利": "毛利率",
    "资产总额": "资产负债率 资产周转率 ROA",
    "资产总计": "资产负债率 资产周转率 ROA",
    "总资产": "资产负债率 资产周转率 ROA",
    "负债总额": "资产负债率",
    "负债总计": "资产负债率",
    "总负债": "资产负债率",
    "净资产": "ROE",
    "所有者权益": "ROE",
    "股东权益": "ROE",
    "流动资产": "流动比率 速动比率",
    "流动负债": "流动比率 速动比率",
    "货币资金": "现金流量",
    "应收账款": "应收账款周转率",
    "每股收益": "PE",
    "基本每股收益": "PE",
    "稀释每股收益": "PE",
    "EPS": "PE",
    "每股净资产": "PB",
}


def _extract_table_title(content: str) -> str:
    """从表格内容中提取表格标题（如"合并利润表"、"母公司资产负债表"）。

    扫描表格前的非表格行，查找财务报表标题关键词。
    """
    title_keywords = [
        ("合并现金流量表", "合并现金流量表"),
        ("合并利润表", "合并利润表"),
        ("合并资产负债表", "合并资产负债表"),
        ("母公司现金流量表", "母公司现金流量表"),
        ("母公司利润表", "母公司利润表"),
        ("母公司资产负债表", "母公司资产负债表"),
        ("利润及利润分配表", "利润表"),
        ("现金流量表", "现金流量表"),
        ("资产负债表", "资产负债表"),
        ("利润表", "利润表"),
        ("主要财务数据", "主要财务数据"),
        ("主要会计数据", "主要会计数据"),
    ]
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('|'):
            continue  # 跳过表格行
        for keyword, title in title_keywords:
            if keyword in line:
                return title
    return ""


def _extract_key_table_rows(content: str, page_num: int) -> List[str]:
    """从表格中提取包含关键财务指标的行作为独立 chunk，提高检索精度。

    每个关键行前面会附加：
    1. 表格标题（如"合并利润表" vs "母公司利润表"），帮助 LLM 区分数据来源
    2. 表头行（年份列标签，如"2025年 | 2024年"），保持原始列对齐，确保 LLM 能正确归属数值
    3. 关联计算指标标签，确保用户查询"存货周转率"时，"存货"等行能被高相似度召回

    注意：content 应为未压缩的原始表格文本，以保持表头与数据行的列对齐。
    """
    key_indicators = [
        "资产总额", "资产总计", "负债总额", "负债总计",
        "营业收入", "营业总收入", "营业成本", "毛利", "毛利率",
        "净利润", "归母净利润", "利润总额", "营业利润",
        "总资产", "总负债", "净资产", "货币资金",
        "应收账款", "存货", "固定资产", "流动资产", "非流动资产",
        "流动负债", "非流动负债", "所有者权益", "股东权益",
        "每股收益", "基本每股收益", "稀释每股收益", "EPS", "每股净资产",
        "资产负债率", "流动比率", "速动比率", "ROE", "ROA",
        "资产周转率", "总资产周转率", "存货周转率", "应收账款周转率",
    ]

    # 提取表头行（第一个非分隔、非空的 | 开头行）
    header_row = ""
    for line in content.split('\n'):
        line = line.strip()
        if not line.startswith('|'):
            continue
        if re.match(r'^\|[-\s|]+\|$', line):
            continue
        cells = [c.strip() for c in line.split('|')]
        cells = [c for c in cells if c]
        if cells:
            header_row = ' | '.join(cells)
            break

    # 提取表格标题（合并/母公司区分）
    table_title = _extract_table_title(content)
    title_prefix = f"【{table_title}】" if table_title else ""

    rows = []
    for line in content.split('\n'):
        line = line.strip()
        if not line.startswith('|'):
            continue
        # 跳过分隔行
        if re.match(r'^\|[-\s|]+\|$', line):
            continue
        cells = [c.strip() for c in line.split('|')]
        cells = [c for c in cells if c]
        if not cells:
            continue
        first_cell = cells[0]
        matched_kw = None
        for kw in key_indicators:
            if kw in first_cell:
                matched_kw = kw
                break
        if matched_kw:
            compressed = ' | '.join(cells)
            # 附加表头行，保持列对齐，让 LLM 能看到年份列标签
            if header_row and header_row != compressed:
                compressed = f"{header_row} | {compressed}"
            # 附加关联计算指标标签，提高检索召回率
            tags = _ROW_METRIC_TAGS.get(matched_kw, "")
            if tags:
                row_text = f"{title_prefix}【第{page_num}页财务数据 | 关联指标：{tags}】{compressed}"
            else:
                row_text = f"{title_prefix}【第{page_num}页财务数据】{compressed}"
            rows.append(row_text)
    return rows


def _is_table_content(content: str) -> bool:
    """检测内容是否为表格（markdown 表格或财务数据表）"""
    # 检测 markdown 表格标记
    has_table_markers = "|" in content and "---" in content
    
    # 检测财务表格关键词（增加资产总额等同义词）
    financial_table_keywords = [
        "合并资产负债表", "合并利润表", "合并现金流量表",
        "资产负债表", "利润表", "现金流量表",
        "资产总计", "资产总额", "负债总计", "负债总额",
        "营业收入", "营业总收入", "净利润", "归母净利润",
        "流动资产", "非流动资产", "流动负债", "非流动负债",
        "货币资金", "应收账款", "存货", "固定资产",
        "每股收益", "每股净资产", "所有者权益", "股东权益",
        "营业成本", "营业利润", "利润总额", "毛利", "毛利率",
        "总资产", "总负债", "净资产", "资产负债率",
        "流动比率", "速动比率", "ROE", "ROA",
        "资产周转率", "存货周转率", "应收账款周转率",
        "基本每股收益", "稀释每股收益", "EPS",
    ]
    has_financial_keywords = any(kw in content for kw in financial_table_keywords)
    
    # 检测数字密度（表格通常有很多数字）
    digit_count = sum(1 for c in content if c.isdigit())
    digit_ratio = digit_count / len(content) if content else 0
    
    # 如果满足任一条件，认为是表格
    return has_table_markers or (has_financial_keywords and digit_ratio > 0.05)


def _enhance_table_content(content: str, page_num: int) -> str:
    """增强表格内容的上下文信息，便于检索"""
    # 提取表格标题（合并/母公司区分）
    table_title = _extract_table_title(content)
    title_prefix = f"【{table_title}】" if table_title else ""

    # 提取表格中的关键财务指标作为前缀
    indicators = []

    # 常见的财务指标模式（覆盖基础数据、盈利能力、偿债能力、运营能力、每股指标）
    # 【修复】增加"资产总额"等同义词，确保前缀描述中包含用户可能查询的词
    patterns = [
        r'(营业收入|营业成本|毛利|净利润|总资产|总负债|净资产|货币资金|应收账款|存货)',
        r'(流动资产|非流动资产|流动负债|非流动负债|所有者权益|股东权益)',
        r'(毛利率|净利率|ROE|ROA|资产负债率|流动比率|速动比率)',
        r'(每股收益|每股净资产|基本每股收益|稀释每股收益|EPS)',
        r'(资产周转率|存货周转率|应收账款周转率|总资产周转率)',
        r'(经营活动|投资活动|筹资活动|现金流量)',
        r'(资产总额|资产总计|负债总额|负债总计|营业总收入|归母净利润)',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content)
        indicators.extend(matches)

    # 去重并限制数量
    unique_indicators = list(dict.fromkeys(indicators))[:10]

    if unique_indicators:
        header = f"{title_prefix}【第{page_num}页财务数据表，包含：{', '.join(unique_indicators)}】\n"
        return header + content
    elif title_prefix:
        return f"{title_prefix}【第{page_num}页】\n" + content

    return content

def _reset_index_state():
    """清空索引磁盘文件 + 内存状态（vector_store / PAGE_NUM_MAP）。
    必须在 _vector_store_lock 内调用。"""
    global vector_store, PAGE_NUM_MAP
    _clear_index()
    vector_store = None
    PAGE_NUM_MAP = {}

def build_vector_store(full_text: str, pdf_hash: str = ""):
    """
    构建 RAG 向量库。

    pdf_hash: 上传文件的 MD5 哈希。
              - 如果和上次索引的哈希一致，且索引文件存在，则复用旧索引（只重建 PAGE_NUM_MAP）
              - 如果不同，强制删除旧索引并重建
              - 如果不传，每次都强制重建
    """
    global vector_store, PAGE_NUM_MAP, _current_pdf_hash, _pending_pdf_hash
    _pending_pdf_hash = pdf_hash  # 标记正在构建的 PDF
    device = get_device()
    print(f"[RAG] RAG 服务启动 | 计算设备: {device}")
    print(f"📂 INDEX_PATH: {INDEX_PATH}")

    with _vector_store_lock:
        try:
            if pdf_hash:
                old_hash = ""
                if INDEX_HASH_PATH.exists():
                    old_hash = INDEX_HASH_PATH.read_text().strip()

                if pdf_hash == old_hash and os.path.exists(str(INDEX_PATH / "index.faiss")):
                    print(f"[REUSE] 相同文件 (hash={pdf_hash[:8]}...)，尝试复用已有索引")
                    if _load_vector_store_internal():
                        # 【修复】校验：复用索引前，检查 full_text 生成的 chunk 数是否与索引向量数一致
                        temp_docs = _split_by_page(full_text)
                        expected = len(temp_docs)
                        actual = vector_store.index.ntotal
                        if expected == actual:
                            print(f"[OK] 索引一致性校验通过 ({actual} 条向量)，跳过重建")
                            _pending_pdf_hash = ""
                            return True
                        else:
                            print(f"[WARN] 索引不一致：预期 {expected} 条向量，实际 {actual} 条。强制重建！")
                            vector_store = None
                            _reset_index_state()
                    else:
                        print("[WARN] 旧索引加载失败，清空内存并强制重建")
                        vector_store = None
                else:
                    if old_hash and old_hash != pdf_hash:
                        print(f"🔄 检测到新文件 (旧hash={old_hash[:8]}..., 新hash={pdf_hash[:8]}...)，删除旧索引并重建")
                    _reset_index_state()
            else:
                _reset_index_state()

            print("🔄 正在加载 embedding 模型...")
            embeddings = SentenceTransformerEmbeddings(
                model_name="BAAI/bge-m3",
                device=device
            )
            print("[OK] embedding 模型加载成功")

            print("🔪 正在按 PDF 页切分文本...")
            documents = _split_by_page(full_text)
            print(f"[OK] 切分完成：共生成 {len(documents)} 个碎片。")

            if len(documents) == 0:
                print("[ERR] 错误：切分后没有 chunks！")
                _pending_pdf_hash = ""
                return False

            print("🧠 正在进行向量化...")
            new_store = FAISS.from_documents(documents, embeddings)
            print("[OK] FAISS 向量库创建成功")

            INDEX_PATH.mkdir(parents=True, exist_ok=True)
            new_store.save_local(str(INDEX_PATH))

            # 构建成功后才替换全局变量，避免中间状态被查询到
            vector_store = new_store
            _current_pdf_hash = pdf_hash

            if pdf_hash:
                INDEX_HASH_PATH.write_text(pdf_hash)

            expected_chunks = len(documents)
            actual_vectors = vector_store.index.ntotal
            print(f"🎉 索引构建成功并已保存！包含 {actual_vectors} 条向量。")
            print(f"📄 页码映射表: {PAGE_NUM_MAP}")
            
            # 【修复】校验：如果向量数和文档数不一致，打印警告
            if actual_vectors != expected_chunks:
                print(f"[WARN] 警告：预期索引 {expected_chunks} 条向量，实际只有 {actual_vectors} 条！")
            
            _pending_pdf_hash = ""
            return True

        except Exception as e:
            import traceback
            print(f"[ERR] RAG 构建失败: {e}")
            print(f"[ERR] 详细错误: {traceback.format_exc()}")
            vector_store = None
            PAGE_NUM_MAP = {}
            _pending_pdf_hash = ""
            return False

def clear_pending_state():
    """清除 _pending_pdf_hash 标记（供外部调用，如 full_text 为空时）"""
    global _pending_pdf_hash
    with _vector_store_lock:
        _pending_pdf_hash = ""

def _clear_index():
    """删除旧的索引文件（删除目录内容而非目录本身，兼容 Docker 卷挂载）"""
    import shutil
    if INDEX_PATH.exists():
        for item in INDEX_PATH.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        print("🗑️ 旧索引已删除")


def get_current_pdf_hash() -> str:
    """返回当前向量库对应的 PDF 哈希（用于前端验证文档一致性）"""
    return _current_pdf_hash

def _rebuild_page_num_map(full_text: str, max_chars_per_chunk: int = 3000):
    """重建页码映射表（复用 _split_by_page 的拆分逻辑，确保表格检测一致）"""
    # _split_by_page 会同时重建 PAGE_NUM_MAP（全局副作用）
    _split_by_page(full_text, max_chars_per_chunk)
    print(f"📄 PAGE_NUM_MAP 已重建: {PAGE_NUM_MAP}")

def _load_vector_store_internal():
    """内部加载向量库（不加锁，由调用方负责锁）"""
    global vector_store
    index_path_str = str(INDEX_PATH)
    print(f"🔍 尝试加载向量库: {index_path_str}")
    if os.path.exists(index_path_str):
        device = get_device()
        print(f"[REUSE] 发现本地向量索引，正在加载 (Device: {device})...")
        try:
            embeddings = SentenceTransformerEmbeddings(
                model_name="BAAI/bge-m3",
                device=device
            )
            # allow_dangerous_deserialization=True is needed for recent langchain versions if loading pickle
            vector_store = FAISS.load_local(index_path_str, embeddings, allow_dangerous_deserialization=True)
            print("[OK] 本地索引加载成功！")
            return True
        except Exception as e:
            print(f"[WARN] 本地索引加载失败: {e}")
            vector_store = None
            _clear_index()  # 删除损坏文件，防止无限重试
            return False
    return False

def load_vector_store():
    """加载向量库（带线程锁，外部调用入口）"""
    with _vector_store_lock:
        return _load_vector_store_internal()

def query_rag(question: str, top_k: int = 5, similarity_threshold: float = 0.4):
    """
    查询 RAG，返回合并后的相关文档内容。
    
    similarity_threshold: 余弦相似度阈值（0~1），低于此值的文档会被过滤掉。
    由于使用了 normalize_embeddings=True，FAISS 内积分数就等于余弦相似度。
    """
    global vector_store
    print(f"🔍 query_rag 被调用 | 问题: {question}")

    with _vector_store_lock:
        if vector_store is None:
            print("[WARN] vector_store 为空，尝试加载...")
            if not _load_vector_store_internal():
                print("[ERR] 加载失败，返回错误消息")
                return "系统提示：知识库尚未建立，且无本地缓存。"
        print("[OK] vector_store 已就绪，执行相似度搜索...")
        docs_and_scores = vector_store.similarity_search_with_score(question, k=top_k)

    # 按相似度阈值过滤（FAISS 余弦距离，分数越低越相似）
    filtered = [(doc, score) for doc, score in docs_and_scores if score <= (2 - similarity_threshold)]

    if not filtered:
        print(f"[WARN] 所有文档相似度低于阈值 {similarity_threshold}，拒绝返回无关数据")
        if docs_and_scores:
            best_score = docs_and_scores[0][1]
            print(f"[STAT] 最高相似度仅为 {best_score:.4f}，低于阈值 {similarity_threshold}")
        return "未找到与问题高度相关的内容。请确认问题是否与当前上传的财报相关，或尝试换个问法。"

    # 打印每个文档的相似度分数（调试用）
    print(f"[STAT] 相似度分数:")
    for i, (doc, score) in enumerate(filtered):
        page = doc.metadata.get("page_num", "?")
        preview = doc.page_content[:50].replace("\n", " ")
        print(f"  [{i+1}] 分数={score:.4f} 页码={page} 内容={preview}...")

    print(f"📄 检索到 {len(filtered)} 个有效文档（阈值: {similarity_threshold}）")
    contexts = []
    for doc, _ in filtered:
        page = doc.metadata.get("page_num", "?")
        contexts.append(f"[来源：第{page}页]\n{doc.page_content}")
    return "\n\n".join(contexts)

def _expand_query(question: str) -> List[str]:
    """扩展查询词，提高中文财务术语的召回率。

    对包含特定财务关键词的问题，生成补充查询以检索同义/相关表格数据。
    如果原查询包含"合并"限定词，扩展词也保留"合并"前缀，避免检索到母公司数据。
    """
    expansions = []
    term_map = {
        "总资产": ["资产总计", "合并资产负债表", "资产合计", "资产总额"],
        "资产总额": ["资产总计", "合并资产负债表", "资产合计", "总资产"],
        "总负债": ["负债合计", "负债总计", "合并资产负债表"],
        "负债总额": ["负债合计", "负债总计", "合并资产负债表"],
        "净资产": ["所有者权益", "股东权益", "归属母公司股东权益"],
        "营收": ["营业收入", "营业总收入", "营业净收入"],
        "净利润": ["归属于母公司所有者的净利润", "利润总额", "归母净利润"],
        "归母净利润": ["归属于母公司所有者的净利润", "净利润", "利润总额"],
        "毛利率": ["营业收入", "营业成本", "综合毛利率"],
        "净利率": ["净利润", "营业收入", "销售净利率"],
        "EPS": ["每股收益", "基本每股收益", "稀释每股收益"],
        "每股收益": ["基本每股收益", "稀释每股收益", "EPS"],
        "资产周转率": ["总资产周转率", "营业收入", "总资产"],
        "总资产周转率": ["资产周转率", "营业收入", "总资产"],
        "存货周转率": ["存货", "营业成本"],
        "速动比率": ["流动资产", "存货", "流动负债"],
        "流动比率": ["流动资产", "流动负债"],
        "资产负债率": ["负债合计", "资产总计", "负债总额"],
        "ROE": ["净资产收益率", "净利润", "所有者权益"],
    }

    # 检测原查询是否包含"合并"限定词
    has_consolidated = "合并" in question or "consolidated" in question.lower()

    q = question
    matched_keywords = []
    for keyword, related_terms in term_map.items():
        if keyword in q:
            matched_keywords.append(keyword)
            for term in related_terms:
                # 如果原查询有"合并"但扩展词没有，补上"合并"前缀
                if has_consolidated and "合并" not in term and "母公司" not in term:
                    # 对适合加"合并"前缀的词（利润表相关科目）加上限定
                    financial_items = ["营业收入", "营业成本", "营业总收入", "净利润", "利润总额",
                                       "归母净利润", "归属于母公司所有者的净利润", "营业利润",
                                       "资产总计", "负债合计", "所有者权益", "资产合计", "资产总额",
                                       "负债总计", "股东权益", "营业净收入", "综合毛利率"]
                    if term in financial_items:
                        term = f"合并{term}"
                expansions.append(term)

    # 如果匹配到多个关键词（如"资产周转率"同时匹配"总资产"和"资产周转率"），合并所有扩展
    if not matched_keywords:
        # 无精确匹配时，尝试模糊匹配常见财务术语
        fuzzy_map = {
            "周转": ["资产周转率", "存货周转率", "总资产周转率"],
            "盈利": ["净利润", "毛利率", "净利率", "ROE"],
            "收益": ["每股收益", "EPS", "净利润"],
            "偿债": ["资产负债率", "流动比率", "速动比率"],
        }
        for keyword, related_terms in fuzzy_map.items():
            if keyword in q:
                for term in related_terms:
                    if has_consolidated and "合并" not in term and "母公司" not in term:
                        financial_items = ["净利润", "毛利率", "净利率", "资产周转率",
                                           "存货周转率", "总资产周转率", "资产负债率",
                                           "流动比率", "速动比率", "每股收益", "EPS"]
                        if term in financial_items:
                            term = f"合并{term}"
                    expansions.append(term)
                break

    return expansions


def query_rag_with_source(question: str, top_k: int = 5, similarity_threshold: float = 0.4) -> Dict[str, Any]:
    """
    查询 RAG 并返回上下文 + 来源页码。

    返回多个相关文档片段拼接后的上下文（跨页问题可覆盖多个页面），
    以及最佳匹配文档的页码（用于前端溯源高亮）。

    通过多查询扩展（原始问题 + 同义词补充查询）提高召回率。

    similarity_threshold: 余弦相似度阈值（0~1），低于此值的文档会被过滤掉。
    """
    global vector_store
    print(f"🔍 query_rag_with_source 被调用 | 问题: {question}")

    # 如果正在构建新索引，返回等待提示而非旧数据
    if _pending_pdf_hash:
        print(f"⏳ 索引正在构建中 (pdf_hash={_pending_pdf_hash[:8]}...)，暂不响应查询")
        return {
            "context": RAG_INDEX_BUILDING,
            "page_num": 1,
            "source_pages": [],
        }

    with _vector_store_lock:
        if vector_store is None:
            print("[WARN] vector_store 为空，尝试加载...")
            if not _load_vector_store_internal():
                print("[ERR] 加载失败")
                return {"context": "系统提示：知识库尚未建立。", "page_num": 1}
        print("[OK] vector_store 已就绪，执行相似度搜索...")

        # 主查询
        docs_and_scores = vector_store.similarity_search_with_score(question, k=top_k)

        # 多查询扩展：用同义词补充查询，提高召回率
        # 【修复】扩展结果施加距离惩罚（1.15），防止关键词堆砌查询（如"营业收入 营业总收入"）
        # 因词频优势压过主查询的精确匹配。主查询结果始终优先于扩展结果。
        # FAISS L2 距离：分数越大越不相似，因此乘以 >1 的系数让扩展结果排名更差。
        expansions = _expand_query(question)
        if expansions:
            extra_query = " ".join(expansions[:5])  # 最多 5 个补充词
            print(f"🔄 查询扩展: {extra_query}")
            extra_results = vector_store.similarity_search_with_score(extra_query, k=top_k + 3)
            # 合并结果，去重（按 doc page_content 去重），扩展结果分数衰减
            EXPANSION_SCORE_DECAY = 1.15
            seen_contents = {doc.page_content for doc, _ in docs_and_scores}
            for doc, score in extra_results:
                if doc.page_content not in seen_contents:
                    docs_and_scores.append((doc, score * EXPANSION_SCORE_DECAY))
                    seen_contents.add(doc.page_content)

    if not docs_and_scores:
        return {"context": "未找到相关内容。", "page_num": 1}

    # 按相似度阈值过滤（FAISS 余弦距离，分数越低越相似）
    # cosine_similarity_threshold → L2 距离阈值: 2 * (1 - similarity_threshold)
    max_distance = 2 * (1 - similarity_threshold)
    filtered = [(doc, score) for doc, score in docs_and_scores if score <= max_distance]

    if not filtered:
        print(f"[WARN] 所有文档相似度低于阈值 {similarity_threshold}，拒绝返回无关数据")
        if docs_and_scores:
            best_score = docs_and_scores[0][1]
            print(f"[STAT] 最高相似度仅为 {best_score:.4f}，低于阈值 {similarity_threshold}")
        return {
            "context": "未找到与问题高度相关的内容。请确认问题是否与当前上传的财报相关，或尝试换个问法。",
            "page_num": 1,
            "source_pages": []
        }

    # 按相似度排序（合并后的结果可能无序）
    # FAISS 内积 + normalize_embeddings=True → 分数越低越相似（余弦距离）
    filtered.sort(key=lambda x: x[1], reverse=False)
    # 只取 top_k 个最相关结果
    filtered = filtered[:top_k]

    print(f"📄 检索到 {len(filtered)} 个有效文档（阈值: {similarity_threshold}）")

    # 打印每个文档的相似度分数（调试用）
    print(f"[STAT] 相似度分数:")
    for i, (doc, score) in enumerate(filtered):
        page = doc.metadata.get("page_num", "?")
        preview = doc.page_content[:50].replace("\n", " ")
        print(f"  [{i+1}] 分数={score:.4f} 页码={page} 内容={preview}...")

    # 取最佳匹配的页码（用于前端溯源）
    best_doc = filtered[0][0]
    page_num = best_doc.metadata.get("page_num", 1)

    # 拼接所有相关文档片段作为上下文（解决跨页问题）
    # 每个 chunk 前标注结构化页码，让 LLM 精确知道数据来自哪一页
    contexts = []
    for doc, _ in filtered:
        page = doc.metadata.get("page_num", "?")
        contexts.append(f"[来源：第{page}页]\n{doc.page_content}")
    context = "\n\n---\n\n".join(contexts)

    # 来源页码：按相似度排序，去重（不截断，确保与 LLM 上下文中的页码完全一致）
    source_pages = list(dict.fromkeys(
        doc.metadata.get("page_num", 1) for doc, _ in filtered
    ))

    print(f"📄 最佳匹配页码: {page_num}，所有来源页: {source_pages}")
    return {
        "context": context,
        "page_num": page_num,
        "source_pages": source_pages
    }