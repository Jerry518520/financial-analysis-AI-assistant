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
import base64

# 导入所有服务
from financial_report_ai_assistant.services.document_parser import parse_pdf_bytes
# from financial_report_ai_assistant.services.ai_chat import get_ai_response # 废弃，改用 Agent
from financial_report_ai_assistant.core.agent import run_agent_query
# 【新增】导入 RAG 服务
from financial_report_ai_assistant.services.rag_service import build_vector_store, query_rag, query_rag_with_source
# 【新增】导入 Analysis 路由
from financial_report_ai_assistant.api.analysis import router as analysis_router

app = FastAPI(title="AI 财报分析助手")

# 【新增】保存当前 PDF 路径，供 /highlight 使用
CURRENT_PDF_PATH = None
CACHE_DIR = "cache_data"

app.include_router(analysis_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    # 注意：现在不需要前端传 context 了，context 由后端自己查
    # 但为了兼容 MVP 代码，我们先留着，只不过不用它了
    context: str | None = None 
    question: str

@app.get("/")
def read_root():
    return {"status": "ok"}

@app.post("/upload")
async def upload_financial_report(file: UploadFile = File(...)):
    global CURRENT_PDF_PATH
    content = await file.read()
    try:
        # 0. 【新增】保存 PDF 到缓存目录，供 /highlight 使用
        os.makedirs(CACHE_DIR, exist_ok=True)
        file_hash = hashlib.md5(content).hexdigest()
        pdf_path = os.path.join(CACHE_DIR, f"current_{file_hash}.pdf")
        with open(pdf_path, "wb") as f:
            f.write(content)
        CURRENT_PDF_PATH = pdf_path
        print(f"📁 PDF 已保存: {pdf_path}")

        # 1. 解析 PDF (获取全量文本)
        result = parse_pdf_bytes(content)
        
        # 2. 【新增】构建 RAG 向量库
        # 这一步会用你的 4060 进行计算
        full_text = result.get("full_text", "")
        print(f"📝 解析结果: 文本长度 = {len(full_text)} 字符")
        if full_text:
            print("🚀 开始构建 RAG 向量库...")
            success = build_vector_store(full_text)
            if success:
                print(">>> RAG 索引构建成功！")
            else:
                print(">>> RAG 索引构建失败！")
        else:
            print("⚠️ 解析结果中没有 full_text 字段")
        
        # 为了前端显示清爽，我们把 full_text 从返回结果里去掉 (太大了，没必要传给前端)
        if "full_text" in result:
            del result["full_text"]
            
        return {"filename": file.filename, "analysis_result": result}
    except Exception as e:
        return {"error": f"解析失败: {str(e)}"}


@app.post("/preview-chunks")
async def preview_chunks_endpoint(file: UploadFile = File(...)):
    """预览切块效果"""
    content = await file.read()
    result = parse_pdf_bytes(content)
    full_text = result.get("full_text", "")
    
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
    rag_result = query_rag_with_source(request.question)

    relevant_context = rag_result["context"]
    page_num = rag_result["page_num"]

    print(f"🔍 用户问: {request.question}")
    print(f"� RAG 返回页码: {page_num}")

    answer = run_agent_query(query=request.question, context=relevant_context)

    return {"answer": answer, "source_page": page_num}

@app.get("/highlight")
async def highlight_page(
    page: int = Query(1, ge=1, description="页码"),
    x: float = Query(0, ge=0, description="X坐标"),
    y: float = Query(0, ge=0, description="Y坐标"),
    w: float = Query(100, ge=1, description="宽度"),
    h: float = Query(50, ge=1, description="高度")
):
    global CURRENT_PDF_PATH
    if not CURRENT_PDF_PATH or not os.path.exists(CURRENT_PDF_PATH):
        return JSONResponse(status_code=404, content={"error": "PDF 未上传或不存在"})

    try:
        import fitz
        from PIL import Image, ImageDraw

        doc = fitz.open(CURRENT_PDF_PATH)
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
        return {"error": f"渲染失败: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)