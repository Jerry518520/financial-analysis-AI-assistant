# 文件: src/financial_report_ai_assistant/api/main.py
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 导入服务
from src.financial_report_ai_assistant.services.document_parser import parse_pdf_bytes
from src.financial_report_ai_assistant.services.ai_chat import get_ai_response

app = FastAPI(title="AI 财报分析助手")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义数据模型
class ChatRequest(BaseModel):
    context: str
    question: str

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Backend is Running!"}

@app.post("/upload")
async def upload_financial_report(file: UploadFile = File(...)):
    content = await file.read()
    try:
        result = parse_pdf_bytes(content)
        return {"filename": file.filename, "analysis_result": result}
    except Exception as e:
        return {"error": f"解析失败: {str(e)}"}

# --- 新增 Chat 接口 ---
@app.post("/chat")
async def chat_with_report(request: ChatRequest):
    answer = get_ai_response(request.context, request.question)
    return {"answer": answer}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)