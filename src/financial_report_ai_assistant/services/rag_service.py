# 文件: src/financial_report_ai_assistant/services/rag_service.py
import torch
import os
import re
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
    def __init__(self, model_name: str, device: str = "cpu"):
        self.model = SentenceTransformer(model_name, device=device)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = self.model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        embedding = self.model.encode([text], normalize_embeddings=True)
        return embedding[0].tolist()

vector_store = None
PAGE_NUM_MAP: Dict[int, int] = {}
PROJECT_ROOT = Path(__file__).parent.parent.parent
INDEX_PATH = PROJECT_ROOT / "faiss_index"

def get_device():
    # ⚠️ 关键点：既然修好了 torch，一定要用 cuda
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

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

def _extract_page_num(text: str) -> int:
    """从文本中提取页码"""
    match = re.search(r'--- Page (\d+) ---', text)
    if match:
        return int(match.group(1))
    return 1

def _split_by_page(full_text: str, max_chars_per_chunk: int = 3000) -> List[Document]:
    """按 PDF 页切分文本，每块记录 page_num"""
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
            if len(content) > max_chars_per_chunk:
                sub_chunks = [content[j:j+max_chars_per_chunk] for j in range(0, len(content), max_chars_per_chunk)]
                for sub_chunk in sub_chunks:
                    doc = Document(page_content=sub_chunk.strip(), metadata={"page_num": page_num})
                    documents.append(doc)
                    PAGE_NUM_MAP[doc_index] = page_num
                    doc_index += 1
            else:
                doc = Document(page_content=content.strip(), metadata={"page_num": page_num})
                documents.append(doc)
                PAGE_NUM_MAP[doc_index] = page_num
                doc_index += 1
        i += 2

    return documents

def build_vector_store(full_text: str):
    global vector_store, PAGE_NUM_MAP
    device = get_device()
    print(f"🔥 RAG 服务启动 | 计算设备: {device}")
    print(f"📂 INDEX_PATH: {INDEX_PATH}")

    try:
        # 检查本地索引是否存在且完整
        if os.path.exists(str(INDEX_PATH)) and os.path.exists(str(INDEX_PATH / "index.faiss")):
            print("♻️ 发现本地 FAISS 索引，尝试加载...")
            if load_vector_store():
                # 索引已加载，重新构建 PAGE_NUM_MAP
                _rebuild_page_num_map(full_text)
                print("✅ 使用已有索引，跳过重建")
                return True

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
        vector_store = FAISS.from_documents(documents, embeddings)
        print("✅ FAISS 向量库创建成功")

        INDEX_PATH.mkdir(parents=True, exist_ok=True)
        vector_store.save_local(str(INDEX_PATH))
        print(f"🎉 索引构建成功并已保存！包含 {vector_store.index.ntotal} 条向量。")
        print(f"📄 页码映射表: {PAGE_NUM_MAP}")
        return True

    except Exception as e:
        import traceback
        print(f"❌ RAG 构建失败: {e}")
        print(f"❌ 详细错误: {traceback.format_exc()}")
        return False

def _rebuild_page_num_map(full_text: str):
    """重建页码映射表"""
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
            PAGE_NUM_MAP[doc_index] = page_num
            doc_index += 1
        i += 2

    print(f"📄 PAGE_NUM_MAP 已重建: {PAGE_NUM_MAP}")

def load_vector_store():
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
            return False
    return False

def query_rag(question: str, top_k: int = 5):
    global vector_store
    print(f"🔍 query_rag 被调用 | 问题: {question}")
    if vector_store is None:
        print("⚠️ vector_store 为空，尝试加载...")
        if not load_vector_store():
            print("❌ 加载失败，返回错误消息")
            return "系统提示：知识库尚未建立，且无本地缓存。"

    print("✅ vector_store 已就绪，执行相似度搜索...")
    docs = vector_store.similarity_search(question, k=top_k)
    print(f"📄 检索到 {len(docs)} 个文档")
    return "\n\n".join([doc.page_content for doc in docs])

def query_rag_with_source(question: str, top_k: int = 3) -> Dict[str, Any]:
    """查询 RAG 并返回上下文 + 来源页码"""
    global vector_store
    print(f"🔍 query_rag_with_source 被调用 | 问题: {question}")
    if vector_store is None:
        print("⚠️ vector_store 为空，尝试加载...")
        if not load_vector_store():
            print("❌ 加载失败")
            return {"context": "系统提示：知识库尚未建立。", "page_num": 1}

    print("✅ vector_store 已就绪，执行相似度搜索...")
    docs = vector_store.similarity_search(question, k=top_k)

    if not docs:
        return {"context": "未找到相关内容。", "page_num": 1}

    best_doc = docs[0]
    page_num = best_doc.metadata.get("page_num", 1)
    context = best_doc.page_content

    print(f"📄 最佳匹配文档页码: {page_num}")
    return {
        "context": context,
        "page_num": page_num
    }