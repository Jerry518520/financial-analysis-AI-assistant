# 文件: src/financial_report_ai_assistant/services/rag_service.py
import torch
import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
# ⚠️ 关键点：必须引入 MarkdownTextSplitter
from langchain_text_splitters import MarkdownTextSplitter 

vector_store = None
INDEX_PATH = "faiss_index"

def get_device():
    # ⚠️ 关键点：既然修好了 torch，一定要用 cuda
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

def build_vector_store(full_text: str):
    global vector_store
    device = get_device()
    print(f"🔥 RAG 服务启动 | 计算设备: {device}")

    try:
        embeddings = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': device}
        )

        # ⚠️ 关键点：适配 LlamaParse 的输出格式
        # ⚠️ 关键修改：把 500 改成 2000
    # Markdown 表格通常很占字符，大窗口能保证表格的完整性（表头+数据在一起）
        text_splitter = MarkdownTextSplitter(
            chunk_size=2000,
            chunk_overlap=200
        )
        
        print("🔪 正在进行 Markdown 智能切分...")
        chunks = text_splitter.split_text(full_text)
        print(f"✅ 切分完成：共生成 {len(chunks)} 个碎片。")

        if len(chunks) == 0:
            return False

        print("🧠 正在进行向量化...")
        vector_store = FAISS.from_texts(chunks, embeddings)
        vector_store.save_local(INDEX_PATH)
        print(f"🎉 索引构建成功并已保存！包含 {vector_store.index.ntotal} 条向量。")
        return True
        
    except Exception as e:
        print(f"❌ RAG 构建失败: {e}")
        return False

def load_vector_store():
    global vector_store
    if os.path.exists(INDEX_PATH):
        device = get_device()
        print(f"♻️ 发现本地向量索引，正在加载 (Device: {device})...")
        try:
            embeddings = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                model_kwargs={'device': device}
            )
            # allow_dangerous_deserialization=True is needed for recent langchain versions if loading pickle
            vector_store = FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
            print("✅ 本地索引加载成功！")
            return True
        except Exception as e:
            print(f"⚠️ 本地索引加载失败: {e}")
            return False
    return False

def query_rag(question: str, top_k: int = 5):
    global vector_store
    if vector_store is None:
        # 尝试懒加载
        if not load_vector_store():
            return "系统提示：知识库尚未建立，且无本地缓存。"
    
    docs = vector_store.similarity_search(question, k=top_k)
    return "\n\n".join([doc.page_content for doc in docs])