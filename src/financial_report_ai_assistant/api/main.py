# 文件: src/financial_report_ai_assistant/api/main.py
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 导入所有服务
from financial_report_ai_assistant.services.document_parser import parse_pdf_bytes
from src.financial_report_ai_assistant.services.ai_chat import get_ai_response
# 【新增】导入 RAG 服务
from src.financial_report_ai_assistant.services.rag_service import build_vector_store, query_rag

app = FastAPI(title="AI 财报分析助手")

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
    content = await file.read()
    try:
        # 1. 解析 PDF (获取全量文本)
        result = parse_pdf_bytes(content)
        
        # 2. 【新增】构建 RAG 向量库
        # 这一步会用你的 4060 进行计算
        full_text = result.get("full_text", "")
        if full_text:
            success = build_vector_store(full_text)
            if success:
                print(">>> RAG 索引构建成功！")
            else:
                print(">>> RAG 索引构建失败！")
        
        # 为了前端显示清爽，我们把 full_text 从返回结果里去掉 (太大了，没必要传给前端)
        if "full_text" in result:
            del result["full_text"]
            
        return {"filename": file.filename, "analysis_result": result}
    except Exception as e:
        return {"error": f"解析失败: {str(e)}"}

@app.post("/chat")
async def chat_with_report(request: ChatRequest):
    # 1. 【新增】RAG 检索
    # 去向量库里找和问题最相关的 3 个片段
    relevant_context = query_rag(request.question)
    
    print(f"🔍 用户问: {request.question}")
    print(f"📖 RAG 检索到的背景: {relevant_context[:100]}...") # 打印日志看看
    
    # 2. 发给 DeepSeek
    # 用检索到的片段，替换掉请求里的 context
    answer = get_ai_response(relevant_context, request.question)
    
    return {"answer": answer}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)