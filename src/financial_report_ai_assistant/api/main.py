# --------------------------------------------------------------------------
# 文件: src/financial_report_ai_assistant/api/main.py
# --------------------------------------------------------------------------

# 从 fastapi 库中，导入 FastAPI 这个“总设计师”类
from fastapi import FastAPI
# 导入两个新的工具: UploadFile 用于接收文件, File 用于声明文件参数
from fastapi import File,UploadFile

# 创建一个 FastAPI 的实例，我们给它取名叫 app
#  这个 app 对象，就是我们整个 Web 应用的核心
app = FastAPI(
    title="AI 财报分析助手",
    description="一个为非专业人士分析上市公司财报的AI工具",
    version="0.1.0",
)

# 这是一个“装饰器”，它像一个便利贴，把下面的函数“贴”在了网站的根路径("/")上
#    @app.get 的意思是：当收到一个 GET 请求访问 "/" 时，就执行这个函数
@app.get("/")
def read_root():
    """
    根路径，用于简单的服务健康检查。
    """
    # 4. 函数返回一个 Python 字典。FastAPI 会自动把它变成浏览器能看懂的 JSON 格式
    return {"status": "ok", "message": "Welcome to the Insightful AI Analyst!"}

# 我们创建一个新的接口，路径是 /upload
#  注意！这次我们用 @app.post，而不是 @app.get
@app.post("/upload")
async def upload_financial_report(file: UploadFile = File(...)):
    """
    接收用户上传的 PDF 格式财报文件。
    """
    # 3. 这是一个异步函数 (async def)，目前我们只需要知道这是 FastAPI 处理IO操作的推荐方式
    # 4. 我们暂时只做一个简单的操作：返回一个包含文件名、内容类型的字典
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": file.size,
    }