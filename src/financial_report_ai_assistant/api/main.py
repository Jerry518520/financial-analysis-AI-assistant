# 文件: src/financial_report_ai_assistant/api/main.py
from fastapi import FastAPI, File, UploadFile
import uvicorn

# --- 【注意这里】路径变了，匹配你现有的文件名 ---
from src.financial_report_ai_assistant.services.document_parser import parse_pdf_bytes

app = FastAPI(title="AI 财报分析助手")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Insightful Backend is Running!"}

@app.post("/upload")
async def upload_financial_report(file: UploadFile = File(...)):
    """
    上传并直接解析 PDF
    """
    # 1. 读取文件内容
    content = await file.read()
    
    # 2. 调用 document_parser.py 里的函数
    try:
        result = parse_pdf_bytes(content)
        
        return {
            "filename": file.filename,
            "analysis_result": result
        }
    except Exception as e:
        return {"error": f"解析失败: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)