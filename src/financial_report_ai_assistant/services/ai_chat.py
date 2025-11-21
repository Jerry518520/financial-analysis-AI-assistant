# 文件: src/financial_report_ai_assistant/services/ai_chat.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 1. 加载环境变量
load_dotenv()

# 2. 获取 Key
api_key = os.getenv("DEEPSEEK_API_KEY")
if not api_key:
    raise ValueError("❌ 未找到 DEEPSEEK_API_KEY，请检查 .env 文件！")

# 3. 初始化 DeepSeek 模型
# 注意：这里用了 langchain_openai 库，但配置的是 DeepSeek 的地址
llm = ChatOpenAI(
    model="deepseek-chat", 
    api_key=api_key,
    base_url="https://api.deepseek.com", # DeepSeek 的官方接口地址
    temperature=0.3
)

def get_ai_response(context_text: str, user_question: str):
    """
    发送请求给 DeepSeek
    """
    # 定义提示词模板
    template = """
    你是一位专业的金融分析师。请根据以下提供的财报片段回答用户问题。
    如果文中没有提到相关信息，请诚实地说“根据当前片段无法回答”。
    
    【财报片段】：
    {context}
    
    【用户问题】：
    {question}
    """
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    
    try:
        response = chain.invoke({
            "context": context_text,
            "question": user_question
        })
        return response
    except Exception as e:
        return f"DeepSeek 思考失败: {str(e)}"