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
                print("⚠️ CUDA 不可用，回退到 CPU（向量化会很慢）")
                device = "cpu"
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
PROJECT_ROOT = Path(__file__).parent.parent.parent

# RAG 查询结果状态常量（供 main.py / analysis.py 使用）
RAG_NOT_FOUND = "未找到"
RAG_INDEX_MISSING = "系统提示：知识库尚未建立"

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
        print(f"🟢 检测到 GPU: {device_name}")
        return "cuda"
    else:
        raise RuntimeError(
            "❌ 未检测到 CUDA GPU！RAG 向量化需要 GPU 加速。\n"
            "请检查：\n"
            "1. 是否安装了 NVIDIA 驱动\n"
            "2. 是否安装了 CUDA Toolkit\n"
            "3. 是否安装了支持 CUDA 的 PyTorch (pip install torch --index-url https://download.pytorch.org/whl/cu118)"
        )

def preview_chunks(full_text: str, max_chars: int = 500):
    """预览切块效果（简单按页切分）"""
    docs = _split_by_page(full_text)
    print(f"📊 切块预览 | 总计 {len(docs)} 个块\n")
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

    page_pattern = r'--- Page (\d+) ---\n'
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
                # 表格内容：不切分，保持完整，并增强上下文
                enhanced_content = _enhance_table_content(content, page_num)
                doc = Document(page_content=enhanced_content, metadata={"page_num": page_num, "type": "table"})
                documents.append(doc)
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


def _is_table_content(content: str) -> bool:
    """检测内容是否为表格（markdown 表格或财务数据表）"""
    # 检测 markdown 表格标记
    has_table_markers = "|" in content and "---" in content
    
    # 检测财务表格关键词
    financial_table_keywords = [
        "合并资产负债表", "合并利润表", "合并现金流量表",
        "资产总计", "负债总计", "营业收入", "净利润",
        "流动资产", "非流动资产", "流动负债", "非流动负债",
        "货币资金", "应收账款", "存货", "固定资产"
    ]
    has_financial_keywords = any(kw in content for kw in financial_table_keywords)
    
    # 检测数字密度（表格通常有很多数字）
    digit_count = sum(1 for c in content if c.isdigit())
    digit_ratio = digit_count / len(content) if content else 0
    
    # 如果满足任一条件，认为是表格
    return has_table_markers or (has_financial_keywords and digit_ratio > 0.05)


def _enhance_table_content(content: str, page_num: int) -> str:
    """增强表格内容的上下文信息，便于检索"""
    # 提取表格中的关键财务指标作为前缀
    indicators = []
    
    # 常见的财务指标模式
    patterns = [
        r'(营业收入|营业成本|毛利|净利润|总资产|总负债|净资产|货币资金|应收账款|存货)',
        r'(流动资产|非流动资产|流动负债|非流动负债|所有者权益)',
        r'(毛利率|净利率|ROE|ROA|资产负债率|流动比率)'
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, content)
        indicators.extend(matches)
    
    # 去重并限制数量
    unique_indicators = list(dict.fromkeys(indicators))[:10]
    
    if unique_indicators:
        header = f"【第{page_num}页财务数据表，包含：{', '.join(unique_indicators)}】\n"
        return header + content
    
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
    global vector_store, PAGE_NUM_MAP, _current_pdf_hash
    device = get_device()
    print(f"🔥 RAG 服务启动 | 计算设备: {device}")
    print(f"📂 INDEX_PATH: {INDEX_PATH}")

    with _vector_store_lock:
        try:
            if pdf_hash:
                old_hash = ""
                if INDEX_HASH_PATH.exists():
                    old_hash = INDEX_HASH_PATH.read_text().strip()

                if pdf_hash == old_hash and os.path.exists(str(INDEX_PATH / "index.faiss")):
                    print(f"♻️ 相同文件 (hash={pdf_hash[:8]}...)，复用已有索引")
                    if _load_vector_store_internal():
                        _rebuild_page_num_map(full_text)
                        print("✅ 使用已有索引，跳过重建")
                        return True
                    else:
                        print("⚠️ 旧索引加载失败，清空内存并强制重建")
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
            print("✅ embedding 模型加载成功")

            print("🔪 正在按 PDF 页切分文本...")
            documents = _split_by_page(full_text)
            print(f"✅ 切分完成：共生成 {len(documents)} 个碎片。")

            if len(documents) == 0:
                print("❌ 错误：切分后没有 chunks！")
                return False

            print("🧠 正在进行向量化...")
            new_store = FAISS.from_documents(documents, embeddings)
            print("✅ FAISS 向量库创建成功")

            INDEX_PATH.mkdir(parents=True, exist_ok=True)
            new_store.save_local(str(INDEX_PATH))

            # 构建成功后才替换全局变量，避免中间状态被查询到
            vector_store = new_store
            _current_pdf_hash = pdf_hash

            if pdf_hash:
                INDEX_HASH_PATH.write_text(pdf_hash)

            print(f"🎉 索引构建成功并已保存！包含 {vector_store.index.ntotal} 条向量。")
            print(f"📄 页码映射表: {PAGE_NUM_MAP}")
            return True

        except Exception as e:
            import traceback
            print(f"❌ RAG 构建失败: {e}")
            print(f"❌ 详细错误: {traceback.format_exc()}")
            vector_store = None
            PAGE_NUM_MAP = {}
            return False

def _clear_index():
    """删除旧的索引文件"""
    import shutil
    if INDEX_PATH.exists():
        shutil.rmtree(INDEX_PATH)
        print("🗑️ 旧索引已删除")


def get_current_pdf_hash() -> str:
    """返回当前向量库对应的 PDF 哈希（用于前端验证文档一致性）"""
    return _current_pdf_hash

def _rebuild_page_num_map(full_text: str, max_chars_per_chunk: int = 3000):
    """重建页码映射表（必须与 _split_by_page 的分块逻辑完全一致）"""
    global PAGE_NUM_MAP
    PAGE_NUM_MAP = {}

    page_pattern = r'--- Page (\d+) ---\n'
    parts = re.split(page_pattern, full_text)

    doc_index = 0
    i = 1
    while i < len(parts):
        page_num = int(parts[i])
        content = parts[i + 1] if i + 1 < len(parts) else ""
        if content.strip():
            if len(content) > max_chars_per_chunk:
                # 长页面切分成多个子块，每个子块都映射到同一页码
                sub_chunks = [content[j:j+max_chars_per_chunk] for j in range(0, len(content), max_chars_per_chunk)]
                for sub_chunk in sub_chunks:
                    PAGE_NUM_MAP[doc_index] = page_num
                    doc_index += 1
            else:
                PAGE_NUM_MAP[doc_index] = page_num
                doc_index += 1
        i += 2

    print(f"📄 PAGE_NUM_MAP 已重建: {PAGE_NUM_MAP}")

def _load_vector_store_internal():
    """内部加载向量库（不加锁，由调用方负责锁）"""
    global vector_store
    index_path_str = str(INDEX_PATH)
    print(f"🔍 尝试加载向量库: {index_path_str}")
    if os.path.exists(index_path_str):
        device = get_device()
        print(f"♻️ 发现本地向量索引，正在加载 (Device: {device})...")
        try:
            embeddings = SentenceTransformerEmbeddings(
                model_name="BAAI/bge-m3",
                device=device
            )
            # allow_dangerous_deserialization=True is needed for recent langchain versions if loading pickle
            vector_store = FAISS.load_local(index_path_str, embeddings, allow_dangerous_deserialization=True)
            print("✅ 本地索引加载成功！")
            return True
        except Exception as e:
            print(f"⚠️ 本地索引加载失败: {e}")
            # 加载失败时清空内存，防止旧数据残留
            vector_store = None
            return False
    return False

def load_vector_store():
    """加载向量库（带线程锁，外部调用入口）"""
    with _vector_store_lock:
        return _load_vector_store_internal()

def query_rag(question: str, top_k: int = 5, similarity_threshold: float = 0.2):
    """
    查询 RAG，返回合并后的相关文档内容。
    
    similarity_threshold: 余弦相似度阈值（0~1），低于此值的文档会被过滤掉。
    由于使用了 normalize_embeddings=True，FAISS 内积分数就等于余弦相似度。
    """
    global vector_store
    print(f"🔍 query_rag 被调用 | 问题: {question}")

    with _vector_store_lock:
        if vector_store is None:
            print("⚠️ vector_store 为空，尝试加载...")
            if not _load_vector_store_internal():
                print("❌ 加载失败，返回错误消息")
                return "系统提示：知识库尚未建立，且无本地缓存。"
        print("✅ vector_store 已就绪，执行相似度搜索...")
        docs_and_scores = vector_store.similarity_search_with_score(question, k=top_k)

    # 按相似度阈值过滤（FAISS inner product = cosine similarity，因为向量已归一化）
    filtered = [(doc, score) for doc, score in docs_and_scores if score >= similarity_threshold]

    if not filtered:
        print(f"⚠️ 所有文档相似度低于阈值 {similarity_threshold}，拒绝返回无关数据")
        if docs_and_scores:
            best_score = docs_and_scores[0][1]
            print(f"📊 最高相似度仅为 {best_score:.4f}，低于阈值 {similarity_threshold}")
        return "未找到与问题高度相关的内容。请确认问题是否与当前上传的财报相关，或尝试换个问法。"

    # 打印每个文档的相似度分数（调试用）
    print(f"📊 相似度分数:")
    for i, (doc, score) in enumerate(filtered):
        page = doc.metadata.get("page_num", "?")
        preview = doc.page_content[:50].replace("\n", " ")
        print(f"  [{i+1}] 分数={score:.4f} 页码={page} 内容={preview}...")

    print(f"📄 检索到 {len(filtered)} 个有效文档（阈值: {similarity_threshold}）")
    return "\n\n".join([doc.page_content for doc, _ in filtered])

def query_rag_with_source(question: str, top_k: int = 5, similarity_threshold: float = 0.2) -> Dict[str, Any]:
    """
    查询 RAG 并返回上下文 + 来源页码。
    
    返回多个相关文档片段拼接后的上下文（跨页问题可覆盖多个页面），
    以及最佳匹配文档的页码（用于前端溯源高亮）。
    
    similarity_threshold: 余弦相似度阈值（0~1），低于此值的文档会被过滤掉。
    """
    global vector_store
    print(f"🔍 query_rag_with_source 被调用 | 问题: {question}")

    with _vector_store_lock:
        if vector_store is None:
            print("⚠️ vector_store 为空，尝试加载...")
            if not _load_vector_store_internal():
                print("❌ 加载失败")
                return {"context": "系统提示：知识库尚未建立。", "page_num": 1}
        print("✅ vector_store 已就绪，执行相似度搜索...")
        docs_and_scores = vector_store.similarity_search_with_score(question, k=top_k)

    if not docs_and_scores:
        return {"context": "未找到相关内容。", "page_num": 1}

    # 按相似度阈值过滤
    filtered = [(doc, score) for doc, score in docs_and_scores if score >= similarity_threshold]

    if not filtered:
        print(f"⚠️ 所有文档相似度低于阈值 {similarity_threshold}，拒绝返回无关数据")
        if docs_and_scores:
            best_score = docs_and_scores[0][1]
            print(f"📊 最高相似度仅为 {best_score:.4f}，低于阈值 {similarity_threshold}")
        return {
            "context": "未找到与问题高度相关的内容。请确认问题是否与当前上传的财报相关，或尝试换个问法。",
            "page_num": 1,
            "source_pages": []
        }

    print(f"📄 检索到 {len(filtered)} 个有效文档（阈值: {similarity_threshold}）")

    # 打印每个文档的相似度分数（调试用）
    print(f"📊 相似度分数:")
    for i, (doc, score) in enumerate(filtered):
        page = doc.metadata.get("page_num", "?")
        preview = doc.page_content[:50].replace("\n", " ")
        print(f"  [{i+1}] 分数={score:.4f} 页码={page} 内容={preview}...")

    # 取最佳匹配的页码（用于前端溯源）
    best_doc = filtered[0][0]
    page_num = best_doc.metadata.get("page_num", 1)

    # 拼接所有相关文档片段作为上下文（解决跨页问题）
    contexts = [doc.page_content for doc, _ in filtered]
    context = "\n\n---\n\n".join(contexts)

    # 同时记录所有来源页码，去重
    source_pages = sorted(set(
        doc.metadata.get("page_num", 1) for doc, _ in filtered
    ))

    print(f"📄 最佳匹配页码: {page_num}，所有来源页: {source_pages}")
    return {
        "context": context,
        "page_num": page_num,
        "source_pages": source_pages
    }