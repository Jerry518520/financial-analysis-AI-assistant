import os
import hashlib
import fitz  # PyMuPDF
import re
import html as html_mod
import base64
import requests
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv

# LlamaParse 可选依赖（免费额度有限，未配置 API Key 时自动跳过）
try:
    from llama_parse import LlamaParse
    LLAMA_PARSE_AVAILABLE = True
except ImportError:
    LLAMA_PARSE_AVAILABLE = False

load_dotenv()

CACHE_DIR = "cache_data"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# 为了防止 LlamaParse 处理过多页面导致超时或消耗过多额度，设置一个软上限
MAX_LLAMA_PAGES = 20


def _get_page_text(page) -> str:
    """
    从 PDF 页面提取纯文本。
    PyMuPDF 的 get_text() 对 Type0 子集字体（中文 PDF 常见）解码为乱码，
    而 get_text("html") 通过 HTML 实体保留了正确的 Unicode codepoint。
    """
    html_content = page.get_text("html")
    # 提取 HTML 标签之间的文本内容
    texts = re.findall(r'>([^<]+)<', html_content)
    # 解码 HTML 实体为 Unicode，拼接为纯文本
    decoded = [html_mod.unescape(t) for t in texts]
    return "\n".join(decoded)

# 【策略调整】非必要不使用 LlamaParse
# 优先级：1. PyMuPDF 提取表格文本  2. LlamaParse（仅当 PyMuPDF 效果差时）
# 只有无边框表格且 PyMuPDF 提取效果差时，才使用 LlamaParse
FORCE_LLAMA_PARSE = os.getenv("FORCE_LLAMA_PARSE", "false").lower() == "true" 

# LlamaParse 支持的语言代码
LLAMA_LANG_MAP = {
    "chinese": "ch_sim",    # 简体中文
    "english": "en",        # 英文
    "japanese": "ja",       # 日文
    "korean": "ko",         # 韩文
}

def _detect_language(doc, sample_pages: int = 5) -> str:
    """
    从 PDF 前几页采样文本，检测主要语言。
    返回 LlamaParse 支持的 language 代码。
    """
    import unicodedata
    
    cjk_chars = 0   # 中日韩字符数
    latin_chars = 0 # 拉丁字符数
    total_chars = 0
    
    for i in range(min(sample_pages, len(doc))):
        text = _get_page_text(doc[i])
        for ch in text:
            if unicodedata.category(ch).startswith("C"):
                continue  # 跳过控制字符、空格等
            total_chars += 1
            # CJK Unified Ideographs 范围
            if '\u4e00' <= ch <= '\u9fff' or '\u3400' <= ch <= '\u4dbf':
                cjk_chars += 1
            elif ch.isascii() and ch.isalpha():
                latin_chars += 1
    
    if total_chars == 0:
        return "en"  # 无法检测时默认英文
    
    cjk_ratio = cjk_chars / total_chars
    latin_ratio = latin_chars / total_chars
    
    # 如果 CJK 字符占比 > 20%，认为是中文（大部分财报的场景）
    if cjk_ratio > 0.2:
        return LLAMA_LANG_MAP["chinese"]
    
    return LLAMA_LANG_MAP["english"]


# ==================== Kimi 多模态解析 ====================

KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"
KIMI_MODEL = os.getenv("KIMI_MODEL", "moonshot-v1-8k-vision-preview")

KIMI_PARSE_PROMPT = """请仔细分析这张财报页面图片，提取其中的所有内容，以 Markdown 格式输出。

要求：
1. 文字内容直接输出
2. 【最重要】所有表格必须用 Markdown 表格格式输出（| 分隔），每个数值必须完整放在一个单元格内，禁止将数字拆分到多个单元格
3. 表格每行必须用 | 开头和结尾，列数保持一致
4. 如果有图表，描述图表的关键数据和趋势
5. 保留页码、脚注等辅助信息
6. 不要添加任何解释或总结，只输出页面原始内容
7. 数字必须保持原始精度，禁止省略小数位或截断数字"""


def _parse_page_with_kimi(page_image_bytes: bytes, page_num: int) -> str:
    """用 Kimi 多模态模型解析单个 PDF 页面图片，返回 Markdown 文本。"""
    api_key = os.getenv("KIMI_API_KEY")
    if not api_key:
        return ""

    b64_image = base64.b64encode(page_image_bytes).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": KIMI_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}},
                    {"type": "text", "text": KIMI_PARSE_PROMPT},
                ],
            }
        ],
        "max_tokens": 8192,
        "temperature": 0.1,
    }

    try:
        resp = requests.post(KIMI_API_URL, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        print(f"✅ Kimi Page {page_num}: {len(content)} chars")
        return content
    except Exception as e:
        print(f"⚠️ Kimi Page {page_num} 解析失败: {e}")
        return ""


# ==================== MiMo 多模态解析 ====================

MIMO_API_URL = "https://token-plan-cn.xiaomimimo.com/v1/chat/completions"
MIMO_MODEL = os.getenv("MIMO_MODEL", "mimo-v2.5")

MIMO_PARSE_PROMPT = """请仔细分析这张财报页面图片，提取其中的所有内容，以 Markdown 格式输出。

要求：
1. 文字内容直接输出
2. 【最重要】所有表格必须用 Markdown 表格格式输出（| 分隔），每个数值必须完整放在一个单元格内，禁止将数字拆分到多个单元格
3. 表格每行必须用 | 开头和结尾，列数保持一致
4. 如果有图表，描述图表的关键数据和趋势
5. 保留页码、脚注等辅助信息
6. 不要添加任何解释或总结，只输出页面原始内容
7. 数字必须保持原始精度，禁止省略小数位或截断数字"""


def _parse_page_with_mimo(page_image_bytes: bytes, page_num: int) -> str:
    """用 MiMo 多模态模型解析单个 PDF 页面图片，返回 Markdown 文本。"""
    api_key = os.getenv("MIMO_API_KEY")
    if not api_key:
        return ""

    b64_image = base64.b64encode(page_image_bytes).decode("utf-8")

    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "model": MIMO_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a document parsing assistant. Output in the SAME language as the source document. If the document is in Chinese, output in Chinese. If in English, output in English. Always use Markdown format.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_image}"}},
                    {"type": "text", "text": MIMO_PARSE_PROMPT},
                ],
            }
        ],
        "max_completion_tokens": 8192,
        "temperature": 0.1,
    }

    try:
        resp = requests.post(MIMO_API_URL, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        print(f"✅ MiMo Page {page_num}: {len(content)} chars")
        return content
    except Exception as e:
        print(f"⚠️ MiMo Page {page_num} 解析失败: {e}")
        return ""


def _render_page_to_png(page, dpi: int = 200) -> bytes:
    """将 PDF 页面渲染为 PNG 图片字节。"""
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat)
    return pix.tobytes("png")

def _is_suspected_table_page(page) -> bool:
    """
    使用启发式规则判断页面是否可能包含无边框表格。
    规则：
    1. 关键词匹配（财报常见表头）
    2. 数字密度检测（表格页通常包含大量数字）
    """
    text = _get_page_text(page)

    # 1. 关键词列表 (中英文，覆盖常见财报表格)
    table_keywords = [
        # 英文 — 三表 + 关键科目
        "Consolidated Balance Sheet", "Consolidated Income Statement", "Cash Flow",
        "Balance Sheet", "Income Statement", "Statement of Financial Position",
        "Statement of Operations", "Statement of Comprehensive Income",
        "Assets", "Liabilities", "Equity", "Revenue", "Cost", "Profit",
        "Operating", "Investing", "Financing", "Depreciation", "Amortization",
        "Accounts Receivable", "Accounts Payable", "Inventories", "Goodwill",
        "Intangible", "Provision", "Impairment", "Dividend", "Earnings",
        # 中文 — 三表 + 关键科目
        "合并资产负债表", "合并利润表", "合并现金流量表", "主要财务指标",
        "资产负债表", "利润表", "现金流量表", "所有者权益变动表",
        "资产", "负债", "权益", "收入", "费用", "成本", "利润", "现金",
        "应收", "应付", "存货", "固定资产", "无形资产", "商誉",
        "减值", "折旧", "摊销", "分红", "股利", "营业收入", "营业成本",
    ]

    has_keyword = any(kw in text for kw in table_keywords)

    # 2. 数字密度检测
    # 匹配像 1,234.56 或 2023 这样的数字
    digit_sequences = re.findall(r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b', text)
    valid_digits = [d for d in digit_sequences if len(d) > 1]
    has_enough_digits = len(valid_digits) > 15

    # OR 逻辑：有关键词 或 数字密度足够高，都可能是表格页
    if has_keyword or has_enough_digits:
        return True

    return False


def _extract_table_with_pymupdf(page) -> str:
    """
    使用 PyMuPDF 提取页面中的表格内容，返回格式化的文本。

    策略（按优先级）：
    1. 有边框表格：find_tables(lines, lines)
    2. 无边框表格：find_tables(text, text) —— 根据文本列对齐检测
    3. 文本块分析（启发式）
    4. 兜底：返回原始文本
    """
    text = _get_page_text(page)

    # ---------- 1. 尝试有边框表格 ----------
    try:
        tables = page.find_tables(horizontal_strategy='lines', vertical_strategy='lines')
        if tables.tables and _is_table_extraction_valid(tables.tables):
            result = _tables_to_markdown(tables.tables)
            if result and len(result) > len(text) * 0.3:
                return result
        elif tables.tables:
            print(f"⚠️ 有边框表格质量不合格（cell 含换行），跳过")
    except Exception as e:
        print(f"⚠️ PyMuPDF 有边框表格提取失败: {e}")

    # ---------- 2. 尝试无边框表格（text 策略） ----------
    try:
        # vertical_strategy='text' 会根据文本的列对齐来推断表格结构
        tables = page.find_tables(
            vertical_strategy='text',
            horizontal_strategy='text',
            snap_tolerance=5,
            join_tolerance=3,
        )
        if tables.tables and _is_table_extraction_valid(tables.tables):
            result = _tables_to_markdown(tables.tables)
            if result and len(result) > len(text) * 0.3:
                print(f"✅ 通过 text 策略提取到无边框表格 ({len(result)} 字符)")
                return result
        elif tables.tables:
            print(f"⚠️ 无边框表格质量不合格（cell 含换行），跳过")
    except Exception as e:
        print(f"⚠️ PyMuPDF 无边框表格提取失败: {e}")

    # ---------- 3. 文本块启发式分析 ----------
    blocks = page.get_text("blocks")
    if len(blocks) > 3:
        lines = text.split('\n')
        formatted_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            has_chinese = bool(re.search(r'[\u4e00-\u9fff]', line))
            has_number = bool(re.search(r'\d', line))
            # \u653e\u5bbd\uff1a\u6709\u4e2d\u6587\u6216\u6709\u6570\u5b57\u5373\u53ef\uff08\u7eaf\u82f1\u6587/\u7eaf\u6570\u5b57\u884c\u4e0d\u518d\u4e22\u5f03\uff09
            if has_chinese or has_number:
                formatted_lines.append(line)
        if len(formatted_lines) > 3:
            return "\n".join(formatted_lines)

    # ---------- 4. 兜底 ----------
    return text


def _tables_to_markdown(tables) -> str:
    """将 PyMuPDF 提取的表格列表转为 Markdown 格式。"""
    table_texts = []
    for tab in tables:
        rows = []
        for row in tab.extract():
            if row:
                cleaned = [str(cell).strip() if cell else "" for cell in row]
                rows.append("| " + " | ".join(cleaned) + " |")
        if rows:
            col_count = len(rows[0].split("|")) - 2
            separator = "|" + "---|" * col_count
            rows.insert(1, separator)
            table_texts.append("\n".join(rows))
    return "\n\n".join(table_texts) if table_texts else ""


def _is_table_extraction_valid(tables) -> bool:
    """校验 PyMuPDF 提取的表格质量（页面级别，所有表格都合格才通过）。

    逐表检查：如果某个 table 中超过 20% 的 cell 含换行符，判定该 table 结构损坏。
    任意一个 table 不合格，整页回退到原始文本（避免坏 table 污染数据）。
    """
    for tab in tables:
        total_cells = 0
        newline_cells = 0
        for row in tab.extract():
            if row:
                for cell in row:
                    if cell:
                        total_cells += 1
                        if '\n' in str(cell):
                            newline_cells += 1
        # 如果换行比例超过 20%，认为该 table 结构损坏
        if total_cells > 0 and (newline_cells / total_cells) >= 0.2:
            return False
    return True


def _is_pymupdf_extraction_good(page_text: str) -> bool:
    """
    判断 PyMuPDF 提取的表格文本质量是否足够好
    
    质量标准：
    1. 包含足够的数字（表格应该有数据）
    2. 包含财务关键词
    3. 文本结构清晰（有换行、有对齐感）
    """
    if not page_text or len(page_text) < 50:
        return False
    
    # 检查数字密度
    digit_count = sum(1 for c in page_text if c.isdigit())
    digit_ratio = digit_count / len(page_text) if page_text else 0
    
    # 检查财务关键词
    financial_keywords = [
        "资产", "负债", "权益", "收入", "成本", "利润", "现金",
        "Assets", "Liabilities", "Equity", "Revenue", "Cost", "Profit"
    ]
    has_financial_kw = any(kw in page_text for kw in financial_keywords)
    
    # 检查是否有合理的行数（表格应该有多行）
    line_count = len([l for l in page_text.split('\n') if l.strip()])
    
    # 质量标准：有财务关键词 + 数字密度 > 1.5% + 行数 > 3
    return has_financial_kw and digit_ratio > 0.015 and line_count > 3

def get_cache_path(file_content: bytes, parser: str = "llamaparse") -> str:
    """根据文件内容和解析引擎生成缓存路径，不同 parser 的缓存互不干扰。"""
    file_hash = hashlib.md5(file_content).hexdigest()
    return os.path.join(CACHE_DIR, f"parsed_hybrid_{parser}_{file_hash}.md")

def parse_pdf_bytes(file_content: bytes, parser: str = "llamaparse", progress_callback=None) -> Dict[str, Any]:
    """解析 PDF 文件内容，返回结构化文本。

    Args:
        file_content: PDF 文件的字节内容
        parser: 解析引擎选择 - "llamaparse"、"kimi" 或 "mimo"
        progress_callback: 可选回调函数 callback(current_page, total_pages, phase)，用于报告解析进度
    """
    print(f"🚀 [Hybrid Parser] 启动混合解析引擎 (parser={parser})...")

    # 1. 检查全量缓存（缓存键包含 parser 选择）
    cache_path = get_cache_path(file_content, parser)
    if os.path.exists(cache_path):
        print(f"♻️ 发现本地完整缓存！直接加载...")
        with open(cache_path, "r", encoding="utf-8") as f:
            full_text = f.read()
        return {"text_preview_snippet": full_text[:500], "full_text": full_text, "status": "success"}

    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        total_pages = len(doc)
        
        table_pages_indices = []
        image_pages_indices = []
        text_pages_content = {} # {page_index: text_content}

        print(f"🕵️ 正在扫描 {total_pages} 页文档结构...")
        
        # 2. 第一次扫描：分流 (Table Detection)
        for i, page in enumerate(doc):
            # 使用 PyMuPDF 的 find_tables() 寻找表格
            # strategy='lines' 适合财报这种有明显边框的表
            # vertical_strategy='text' 辅助无框表
            try:
                # 先尝试 lines 策略（有边框表）
                tables = page.find_tables(horizontal_strategy='lines', vertical_strategy='lines')

                # 再尝试 text 策略（无边框表）
                if not tables.tables:
                    tables = page.find_tables(
                        vertical_strategy='text',
                        horizontal_strategy='text',
                        snap_tolerance=5,
                        join_tolerance=3,
                    )

                # 如果发现表格，且表格面积看起来不是误判，且结构质量合格
                has_valid_table = False
                if tables.tables and _is_table_extraction_valid(tables.tables):
                    for tab in tables.tables:
                        if len(tab.cells) > 4:
                            has_valid_table = True
                            break

                # 如果 PyMuPDF 两种策略都没检测到，尝试启发式检测
                if not has_valid_table:
                    if _is_suspected_table_page(page):
                        print(f"👀 Page {i+1} 疑似包含无边框表格（启发式检测命中），将送往 LlamaParse。")
                        has_valid_table = True

                if has_valid_table:
                    table_pages_indices.append(i)
                else:
                    # 普通页面：直接提取文本
                    text = _get_page_text(page)
                    # 检测页面是否包含图片/图表
                    images = page.get_images()
                    if images and len(text.strip()) < 50:
                        # 图片页面文本很少，标记需要 LlamaParse 处理
                        image_pages_indices.append(i)
                        text_pages_content[i] = f"--- Page {i+1} ---\n{text}\n"
                    else:
                        text_pages_content[i] = f"--- Page {i+1} ---\n{text}\n"
            except Exception as e:
                print(f"⚠️ Page {i+1} 检测出错: {e}, 降级为普通文本")
                text = _get_page_text(page)
                text_pages_content[i] = f"--- Page {i+1} ---\n{text}\n"

        print(f"📊 扫描结果：发现 {len(table_pages_indices)} 页包含表格，{len(image_pages_indices)} 页包含图表/图片，{len(text_pages_content)} 页纯文本。")
        if progress_callback:
            progress_callback(0, total_pages, "结构扫描完成，开始解析页面")

        # 3. 处理表格页面（优先 PyMuPDF，必要时 LlamaParse）
        llama_pages_content = {} # {page_index: markdown_content}
        pymupdf_table_pages = {} # {page_index: markdown_content}
        
        if table_pages_indices:
            # 【新策略】先用 PyMuPDF 尝试提取表格
            pages_need_llama = []  # 记录 PyMuPDF 处理效果不好的页面
            
            for idx in table_pages_indices:
                page = doc[idx]
                
                # 尝试 PyMuPDF 提取
                pymupdf_result = _extract_table_with_pymupdf(page)
                
                # 检查提取质量
                if _is_pymupdf_extraction_good(pymupdf_result) and not FORCE_LLAMA_PARSE:
                    # PyMuPDF 提取效果好，直接使用
                    print(f"✅ Page {idx+1}: PyMuPDF 提取成功")
                    pymupdf_table_pages[idx] = f"--- Page {idx+1} ---\n{pymupdf_result}\n"
                else:
                    # PyMuPDF 效果不好，标记为需要 LlamaParse
                    print(f"⚠️ Page {idx+1}: PyMuPDF 效果不佳，将使用 LlamaParse")
                    pages_need_llama.append(idx)
            
            # 对 PyMuPDF 效果不好的页面，使用外部解析引擎
            if pages_need_llama:
                if parser in ("kimi", "mimo"):
                    # 多模态模型：逐页渲染为图片并解析，无页数限制
                    parse_fn = _parse_page_with_kimi if parser == "kimi" else _parse_page_with_mimo
                    label = "Kimi" if parser == "kimi" else "MiMo"
                    print(f"🔮 使用 {label} 多模态解析 {len(pages_need_llama)} 页表格...")
                    for idx in pages_need_llama:
                        page = doc[idx]
                        img_bytes = _render_page_to_png(page)
                        result = parse_fn(img_bytes, idx + 1)
                        if result:
                            llama_pages_content[idx] = f"--- Page {idx+1} ({label} Enhanced) ---\n{result}\n"
                        else:
                            text = _get_page_text(page)
                            pymupdf_table_pages[idx] = f"--- Page {idx+1} (PyMuPDF Fallback) ---\n{text}\n"
                        if progress_callback:
                            progress_callback(idx + 1, total_pages, f"表格页解析中 ({idx+1}/{total_pages})")
                else:
                    # LlamaParse：限制页数
                    target_indices = pages_need_llama[:MAX_LLAMA_PAGES]
                    if len(pages_need_llama) > MAX_LLAMA_PAGES:
                        print(f"⚠️ 需要 LlamaParse 的页面共 {len(pages_need_llama)} 页，只处理前 {MAX_LLAMA_PAGES} 页")
                        for idx in pages_need_llama[MAX_LLAMA_PAGES:]:
                            page = doc[idx]
                            text = _get_page_text(page)
                            pymupdf_table_pages[idx] = f"--- Page {idx+1} (PyMuPDF Fallback) ---\n{text}\n"

                    api_key = os.getenv("LLAMA_CLOUD_API_KEY")
                    if not api_key or not LLAMA_PARSE_AVAILABLE:
                        print("⚠️ LlamaParse 不可用（缺少 API Key 或未安装），降级为 PyMuPDF 提取")
                        for idx in target_indices:
                            page = doc[idx]
                            text = _get_page_text(page)
                            pymupdf_table_pages[idx] = f"--- Page {idx+1} (PyMuPDF Fallback) ---\n{text}\n"
                    else:
                        subset_filename = f"temp_tables_{hashlib.md5(file_content).hexdigest()[:8]}.pdf"
                        new_doc = fitz.open()
                        for idx in target_indices:
                            new_doc.insert_pdf(doc, from_page=idx, to_page=idx)
                        new_doc.save(subset_filename)
                        new_doc.close()

                        detected_lang = _detect_language(doc)
                        print(f"💸 正在调用 LlamaParse 处理 {len(target_indices)} 页表格...")
                        try:
                            llama_parser = LlamaParse(result_type="markdown", premium_mode=False, language=detected_lang)
                            documents = llama_parser.load_data(subset_filename)
                            for idx, result_doc in enumerate(documents):
                                if idx < len(target_indices):
                                    original_page_idx = target_indices[idx]
                                    llama_pages_content[original_page_idx] = f"--- Page {original_page_idx+1} (LlamaParse Enhanced) ---\n{result_doc.text}\n"
                                else:
                                    last_page_idx = target_indices[-1]
                                    if last_page_idx in llama_pages_content:
                                        llama_pages_content[last_page_idx] += f"\n{result_doc.text}\n"
                            if len(documents) < len(target_indices):
                                for i in range(len(documents), len(target_indices)):
                                    original_page_idx = target_indices[i]
                                    page = doc[original_page_idx]
                                    text = _get_page_text(page)
                                    pymupdf_table_pages[original_page_idx] = f"--- Page {original_page_idx+1} (PyMuPDF Fallback) ---\n{text}\n"
                        except Exception as e:
                            print(f"⚠️ LlamaParse 调用失败: {e}，降级为 PyMuPDF")
                            for idx in target_indices:
                                page = doc[idx]
                                text = _get_page_text(page)
                                pymupdf_table_pages[idx] = f"--- Page {idx+1} (PyMuPDF Fallback) ---\n{text}\n"

                        if os.path.exists(subset_filename):
                            try:
                                os.remove(subset_filename)
                            except OSError:
                                pass

        # 3b. 处理图片/图表页面
        if image_pages_indices:
            if parser in ("kimi", "mimo"):
                # 多模态模型：逐页渲染为图片并解析，无页数限制
                parse_fn = _parse_page_with_kimi if parser == "kimi" else _parse_page_with_mimo
                label = "Kimi" if parser == "kimi" else "MiMo"
                print(f"🔮 使用 {label} 多模态解析 {len(image_pages_indices)} 页图表...")
                for idx in image_pages_indices:
                    page = doc[idx]
                    img_bytes = _render_page_to_png(page)
                    result = parse_fn(img_bytes, idx + 1)
                    if result:
                        llama_pages_content[idx] = f"--- Page {idx+1} ({label} 图表提取) ---\n{result}\n"
                        print(f"✅ Page {idx+1}: {label} 图表提取成功")
                    else:
                        text = _get_page_text(page)
                        text_pages_content[idx] = f"--- Page {idx+1} ---\n{text}\n[注：本页包含图片/图表，{label} 解析失败]"
                    if progress_callback:
                        progress_callback(idx + 1, total_pages, f"图表页解析中 ({idx+1}/{total_pages})")
            else:
                # LlamaParse
                api_key = os.getenv("LLAMA_CLOUD_API_KEY")
                if not api_key or not LLAMA_PARSE_AVAILABLE:
                    print(f"⚠️ LlamaParse 不可用（{len(image_pages_indices)} 页图表将保留原始文本）")
                    for idx in image_pages_indices:
                        page = doc[idx]
                        text = _get_page_text(page)
                        text_pages_content[idx] = f"--- Page {idx+1} ---\n{text}\n[注：本页包含图片/图表，缺少 API Key 无法自动提取]"
                else:
                    target_image_indices = image_pages_indices[:MAX_LLAMA_PAGES]
                    if len(image_pages_indices) > MAX_LLAMA_PAGES:
                        print(f"⚠️ 图表页面共 {len(image_pages_indices)} 页，只处理前 {MAX_LLAMA_PAGES} 页")

                    subset_filename = f"temp_images_{hashlib.md5(file_content).hexdigest()[:8]}.pdf"
                    new_doc = fitz.open()
                    for idx in target_image_indices:
                        new_doc.insert_pdf(doc, from_page=idx, to_page=idx)
                    new_doc.save(subset_filename)
                    new_doc.close()

                    print(f"💸 正在调用 LlamaParse 处理 {len(target_image_indices)} 页图表...")
                    detected_lang = _detect_language(doc)
                    try:
                        llama_parser = LlamaParse(result_type="markdown", premium_mode=True, language=detected_lang)
                        documents = llama_parser.load_data(subset_filename)
                        for idx, result_doc in enumerate(documents):
                            if idx < len(target_image_indices):
                                original_page_idx = target_image_indices[idx]
                                llama_pages_content[original_page_idx] = f"--- Page {original_page_idx+1} (LlamaParse 图表提取) ---\n{result_doc.text}\n"
                        if len(documents) < len(target_image_indices):
                            for i in range(len(documents), len(target_image_indices)):
                                original_page_idx = target_image_indices[i]
                                page = doc[original_page_idx]
                                text = _get_page_text(page)
                                text_pages_content[original_page_idx] = f"--- Page {original_page_idx+1} ---\n{text}\n[注：本页包含图片/图表，LlamaParse 仅返回部分结果]"
                    except Exception as e:
                        print(f"⚠️ LlamaParse 图表提取失败: {e}，保留原始文本")
                        for idx in target_image_indices:
                            page = doc[idx]
                            text = _get_page_text(page)
                            text_pages_content[idx] = f"--- Page {idx+1} ---\n{text}\n[注：本页包含图片/图表，LlamaParse 提取失败]"

                    if os.path.exists(subset_filename):
                        try:
                            os.remove(subset_filename)
                        except OSError:
                            pass

        # 4. 合并所有内容 (按页码顺序)
        # 优先级：LlamaParse > PyMuPDF 表格 > 纯文本
        final_full_text = []
        for i in range(total_pages):
            if i in llama_pages_content:
                final_full_text.append(llama_pages_content[i])
            elif i in pymupdf_table_pages:
                final_full_text.append(pymupdf_table_pages[i])
            elif i in text_pages_content:
                final_full_text.append(text_pages_content[i])
        
        full_text_str = "\n".join(final_full_text)
        
        # 5. 写入缓存
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(full_text_str)

        return {
            "text_preview_snippet": full_text_str[:500], 
            "full_text": full_text_str, 
            "status": "success"
        }

    except Exception as e:
        print(f"❌ 解析失败: {e}")
        return {"status": "error", "error": str(e)}
    finally:
        # 确保 doc 资源被释放（即使在 LlamaParse 等异常路径上）
        try:
            doc.close()
        except (NameError, AttributeError):
            pass
