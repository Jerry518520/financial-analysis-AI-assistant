# 文件: src/financial_report_ai_assistant/services/ai_chat.py
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

# ==================== LLM 提供商配置 ====================
# 支持 "deepseek" 和 "mimo" 两种提供商，通过 LLM_PROVIDER 环境变量切换
_LLM_PROVIDER_CONFIG = {
    "deepseek": {
        "env_key": "DEEPSEEK_API_KEY",
        "model": "deepseek-chat",
        "base_url": "https://api.deepseek.com",
    },
    "mimo": {
        "env_key": "MIMO_API_KEY",
        "model": os.getenv("MIMO_MODEL", "mimo-v2.5"),
        "base_url": "https://token-plan-cn.xiaomimimo.com/v1",
    },
}


def _get_provider_config() -> dict:
    """获取当前 LLM 提供商配置"""
    provider = os.getenv("LLM_PROVIDER", "deepseek").lower()
    if provider not in _LLM_PROVIDER_CONFIG:
        print(f"⚠️ 未知 LLM_PROVIDER '{provider}'，回退到 deepseek")
        provider = "deepseek"
    return _LLM_PROVIDER_CONFIG[provider]


# 延迟初始化：不再在模块级 raise，首次访问时才创建 LLM 实例
_llm_instance = None


def get_llm():
    """获取或延迟初始化 LLM 实例（根据 LLM_PROVIDER 选择 DeepSeek 或 MiMo）"""
    global _llm_instance
    if _llm_instance is None:
        config = _get_provider_config()
        api_key = os.getenv(config["env_key"])
        if not api_key:
            raise ValueError(f"❌ 未找到 {config['env_key']}，请检查 .env 文件！")
        provider = os.getenv("LLM_PROVIDER", "deepseek").lower()

        # MiMo API 使用 api-key 请求头认证，而非标准 Bearer
        extra_kwargs = {}
        if provider == "mimo":
            extra_kwargs["default_headers"] = {"api-key": api_key}

        _llm_instance = ChatOpenAI(
            model=config["model"],
            api_key=api_key,
            base_url=config["base_url"],
            temperature=0.3,
            timeout=60,
            max_retries=2,
            **extra_kwargs,
        )
        print(f"✅ LLM 已初始化: provider={provider}, model={config['model']}")
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