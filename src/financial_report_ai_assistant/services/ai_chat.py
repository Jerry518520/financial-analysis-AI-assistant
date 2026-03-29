# 文件: src/financial_report_ai_assistant/services/ai_chat.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# 延迟初始化：不再在模块级 raise，首次访问时才创建 LLM 实例
_llm_instance = None


def get_llm():
    """获取或延迟初始化 DeepSeek LLM 实例"""
    global _llm_instance
    if _llm_instance is None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("❌ 未找到 DEEPSEEK_API_KEY，请检查 .env 文件！")
        _llm_instance = ChatOpenAI(
            model="deepseek-chat",
            api_key=api_key,
            base_url="https://api.deepseek.com",
            temperature=0.3,
        )
    return _llm_instance


# 向后兼容的属性访问（analysis.py 通过 `from ai_chat import llm` 使用）
# @property 方式无法用在模块级别，所以提供一个 module-level 属性代理
class _LLMProxy:
    """代理对象，延迟加载 LLM 实例，支持 analysis.py 中的 `from ai_chat import llm` 用法"""
    def __getattr__(self, name):
        return getattr(get_llm(), name)

    def __call__(self, *args, **kwargs):
        return get_llm()(*args, **kwargs)


llm = _LLMProxy()