# 文件: src/financial_report_ai_assistant/services/rag_service.py
import os
import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

# 定义全局变量，用于缓存向量数据库
# (在 MVP 阶段，我们暂时存内存里；生产环境通常存硬盘)
vector_store = None

def get_device():
    """
    检查是否有 NVIDIA 显卡，如果有就用，没有就用 CPU
    """
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"

def build_vector_store(full_text: str):
    """
    核心功能：接收全书文本 -> 切块 -> 用显卡向量化 -> 存入 FAISS
    """
    global vector_store
    
    # 1. 检测设备 (召唤 RTX 4060)
    device = get_device()
    print(f"🔥 正在使用设备: {device} 进行向量化计算...")

    # 2. 初始化 Embedding 模型 (本地免费模型)
    # 我们使用 'all-MiniLM-L6-v2'，这是一个体积小(80MB)、速度快、效果好的通用模型
    # 第一次运行时，它会自动从 HuggingFace 下载模型文件，可能会花几十秒
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={'device': device} # 关键：让显卡干活
    )

    # 3. 文本切分 (切菜)
    # chunk_size=500: 每块约 300-400 个中文字
    # chunk_overlap=50: 每块之间重叠一点，防止把一句话切断了
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    
    print("正在切分文档...")
    chunks = text_splitter.split_text(full_text)
    print(f"✅ 文档已切分为 {len(chunks)} 个碎片。")

    # 4. 向量化并建立索引 (最耗时的一步，但你有 4060 应该很快)
    print("正在构建向量索引 (这可能需要几秒钟)...")
    try:
        # FAISS 会调用上面的 embeddings 模型，把 chunks 变成向量存起来
        vector_store = FAISS.from_texts(chunks, embeddings)
        print("🎉 向量数据库构建完成！")
        return True
    except Exception as e:
        print(f"❌ 向量化失败: {e}")
        return False

def query_rag(question: str, top_k: int = 8):
    """
    检索功能：接收问题 -> 找最相关的 top_k 个片段
    """
    global vector_store
    if vector_store is None:
        return "请先上传并解析文档。"
    
    # 1. 在向量库里搜索最相似的片段
    # search_type="similarity" 代表找语义最接近的
    docs = vector_store.similarity_search(question, k=top_k)
    
    # 2. 把找到的片段内容拼接起来
    # docs 是一个列表，每个元素都有 page_content
    context = "\n\n".join([doc.page_content for doc in docs])
    
    return context