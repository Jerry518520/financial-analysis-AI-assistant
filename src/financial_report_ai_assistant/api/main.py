# 文件: src/financial_report_ai_assistant/api/main.py
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
import uvicorn
import os
import hashlib
import io
import asyncio

# 导入所有服务
from financial_report_ai_assistant.services.document_parser import parse_pdf_bytes
# from financial_report_ai_assistant.services.ai_chat import get_ai_response # 废弃，改用 Agent
from financial_report_ai_assistant.core.agent import run_agent_query, generate_recommendations
# 【新增】导入 RAG 服务
from financial_report_ai_assistant.services.rag_service import build_vector_store, query_rag, query_rag_with_source, get_current_pdf_hash, RAG_NOT_FOUND
# 【新增】导入 Analysis 路由
from financial_report_ai_assistant.api.analysis import router as analysis_router
import threading

app = FastAPI(title="AI 财报分析助手")

# 【新增】保存当前 PDF 路径，供 /highlight 使用
CURRENT_PDF_PATH = None
_current_pdf_lock = threading.Lock()
CACHE_DIR = "cache_data"
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB 上传限制

app.include_router(analysis_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    question: str
    conversation_history: list = []  # 历史对话记录 [(question, answer), ...]
    pdf_hash: str = ""  # 前端当前文档哈希，用于校验历史数据一致性

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.post("/upload")
async def upload_financial_report(file: UploadFile = File(...)):
    global CURRENT_PDF_PATH
    content = await file.read()
    
    if len(content) > MAX_UPLOAD_SIZE:
        return JSONResponse(status_code=413, content={"error": f"文件过大，最大支持 {MAX_UPLOAD_SIZE // (1024*1024)}MB"})
    
    try:
        # 0. 【新增】保存 PDF 到缓存目录，供 /highlight 使用
        os.makedirs(CACHE_DIR, exist_ok=True)
        file_hash = hashlib.md5(content).hexdigest()
        pdf_path = os.path.join(CACHE_DIR, f"current_{file_hash}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(content)
        with _current_pdf_lock:
            CURRENT_PDF_PATH = pdf_path
        print(f"📁 PDF 已保存: {pdf_path}")

        # 1. 解析 PDF (获取全量文本)
        result = parse_pdf_bytes(content)
        
        # 2. 构建 RAG 向量库（传入文件哈希，新文件自动重建索引）
        full_text = result.get("full_text", "")
        print(f"📝 解析结果: 文本长度 = {len(full_text)} 字符")
        if full_text:
            print("🚀 开始构建 RAG 向量库...")
            # 使用 asyncio.to_thread 避免阻塞事件循环（GPU 计算 + 模型加载耗时较长）
            success = await asyncio.to_thread(build_vector_store, full_text, file_hash)
            if success:
                print(">>> RAG 索引构建成功！")
            else:
                print(">>> RAG 索引构建失败！")
        else:
            print("⚠️ 解析结果中没有 full_text 字段")
        
        # 为了前端显示清爽，我们把 full_text 从返回结果里去掉 (太大了，没必要传给前端)
        if "full_text" in result:
            del result["full_text"]
            
        return {"filename": file.filename, "analysis_result": result, "pdf_hash": file_hash}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"解析失败: {str(e)}"})


@app.post("/preview-chunks")
async def preview_chunks_endpoint(file: UploadFile = File(...)):
    """预览切块效果"""
    content = await file.read()
    result = parse_pdf_bytes(content)
    
    if result.get("status") == "error":
        return JSONResponse(status_code=500, content={"error": f"解析失败: {result.get('error', '未知错误')}"})
    
    full_text = result.get("full_text", "")
    if not full_text:
        return JSONResponse(status_code=422, content={"error": "解析结果中没有文本内容"})
    
    from financial_report_ai_assistant.services.rag_service import preview_chunks
    chunks = preview_chunks(full_text)
    
    return {
        "total_chunks": len(chunks),
        "chunks": [
            {"index": i+1, "length": len(c), "content": c[:500] + "..." if len(c) > 500 else c}
            for i, c in enumerate(chunks)
        ]
    }

@app.post("/chat")
async def chat_with_report(request: ChatRequest):
    try:
        # RAG 检索（当前问题，使用较低阈值提高中文财务术语召回率）
        rag_result = await asyncio.to_thread(query_rag_with_source, request.question, 5, 0.3)
        relevant_context = rag_result["context"]
        page_num = rag_result["page_num"]
        source_pages = rag_result.get("source_pages", [page_num])

        # 只保留 top-2 来源页面（按相似度排序），避免引用过多无关页面
        source_pages = source_pages[:2]

        print(f"🔍 用户问: {request.question}")
        print(f"📄 RAG 返回页码: {page_num}，所有来源页: {source_pages}")

        # RAG 未找到相关内容时，直接返回提示，不浪费 LLM 调用
        if RAG_NOT_FOUND in relevant_context and not request.conversation_history:
            return {
                "answer": "财报中未找到与该问题相关的数据。请确认问题是否与当前上传的财报相关，或尝试换个问法。",
                "source_page": 1,
                "source_pages": [],
                "recommendations": ["查看财报核心摘要", "营收是多少", "净利润是多少"]
            }

        # 【关键修复】构建增强上下文：当前 RAG 结果 + 历史对话中提取的数据
        enhanced_context = _build_enhanced_context(
            current_context=relevant_context,
            history=request.conversation_history,
            current_question=request.question,
            request_pdf_hash=request.pdf_hash
        )

        # 将有效页码列表注入上下文，约束 LLM 只能引用实际存在的页码
        if source_pages:
            pages_str = "、".join(str(p) for p in source_pages)
            enhanced_context += f"\n\n【有效来源页码】：第 {pages_str} 页（回答中引用的页码必须来自此列表）"

        # 简单问题走轻量级通道（1次LLM调用 vs Agent的3-4次）
        from financial_report_ai_assistant.core.agent import is_simple_query, run_lightweight_query
        if is_simple_query(request.question):
            print(f"⚡ 轻量级查询模式（简单问题快速通道）")
            answer = await asyncio.to_thread(run_lightweight_query, request.question, enhanced_context)
        else:
            print(f"🤖 Agent 深度分析模式")
            answer = await asyncio.to_thread(run_agent_query, request.question, enhanced_context)

        # 生成推荐问题（基于回答动态生成）
        recommendations = await asyncio.to_thread(generate_recommendations, request.question, answer, enhanced_context)
        print(f"💡 推荐问题: {recommendations}")

        return {
            "answer": answer,
            "source_page": page_num,
            "source_pages": source_pages,
            "recommendations": recommendations,
            "pdf_hash": get_current_pdf_hash()
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"对话处理失败: {str(e)}"})


def _build_enhanced_context(current_context: str, history: list, current_question: str, request_pdf_hash: str = "") -> str:
    """
    构建增强上下文：合并当前 RAG 结果 + 从历史对话中提取的数值数据。
    如果 request_pdf_hash 与当前索引文档不一致，跳过历史注入防止跨文档数据污染。
    """
    if not history:
        return current_context

    # 文档一致性校验：历史数据可能来自不同文档，跳过注入
    current_hash = get_current_pdf_hash()
    if request_pdf_hash and current_hash and request_pdf_hash != current_hash:
        print(f"⚠️ 历史数据文档不一致 (请求hash={request_pdf_hash[:8]}..., 当前hash={current_hash[:8]}...)，跳过历史注入")
        return current_context

    # 从历史对话中提取数值数据（问答对）
    history_data = []
    for i, (q, a) in enumerate(history[-5:]):  # 只取最近 5 轮
        history_data.append(f"【历史问题 {i+1}】{q}\n【历史回答 {i+1}】{a[:500]}...")  # 截断避免过长

    history_joined = "\n\n".join(history_data)
    enhanced = f"""【当前问题相关文档】
{current_context}

【历史对话记录（用于数据复用）】
{history_joined}

【重要提示】
1. 历史数据仅来自同一份文档，可以直接复用已计算的指标
2. 如果用户问"刚才计算的毛利率是多少"，请从历史回答中找到具体数值回答
3. 所有数值必须来自上述文档内容或历史计算结果，禁止编造"""

    return enhanced

@app.get("/highlight")
async def highlight_page(
    page: int = Query(1, ge=1, description="页码"),
    x: float = Query(0, ge=0, description="X坐标"),
    y: float = Query(0, ge=0, description="Y坐标"),
    w: float = Query(100, ge=1, description="宽度"),
    h: float = Query(50, ge=1, description="高度")
):
    global CURRENT_PDF_PATH
    with _current_pdf_lock:
        pdf_path = CURRENT_PDF_PATH
    if not pdf_path or not os.path.exists(pdf_path):
        return JSONResponse(status_code=404, content={"error": "PDF 未上传或不存在"})

    try:
        import fitz
        from PIL import Image, ImageDraw

        doc = fitz.open(pdf_path)
        page_index = page - 1
        if page_index >= len(doc):
            page_index = len(doc) - 1

        pdf_page = doc[page_index]
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = pdf_page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        doc.close()

        img = Image.open(io.BytesIO(img_data))
        draw = ImageDraw.Draw(img)

        x1, y1 = x * zoom, y * zoom
        x2, y2 = (x + w) * zoom, (y + h) * zoom
        draw.rectangle([x1, y1, x2, y2], outline="red", width=3)

        output = io.BytesIO()
        img.save(output, format="PNG")
        img_bytes = output.getvalue()

        return Response(content=img_bytes, media_type="image/png")

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": f"渲染失败: {str(e)}"})

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)