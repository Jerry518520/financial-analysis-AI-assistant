"""统一财务数据缓存：一次提取，多处复用。

上传PDF时一次性提取所有财务数据并缓存，概要、对话、雷达图都从缓存读取，
确保所有路径返回的数值100%一致。
"""
import threading
from typing import Dict, Optional

_cache: Dict[str, dict] = {}
_lock = threading.Lock()


def get_cached_data(pdf_hash: str) -> Optional[dict]:
    """获取指定PDF的缓存财务数据"""
    with _lock:
        return _cache.get(pdf_hash)


def set_cached_data(pdf_hash: str, data: dict):
    """缓存财务数据"""
    with _lock:
        _cache[pdf_hash] = data
        print(f"📦 财务数据已缓存: pdf_hash={pdf_hash[:8]}..., 指标数={len(data.get('computed_metrics', {}))}")


def get_current_cached_data() -> Optional[dict]:
    """获取当前文档的缓存数据"""
    from financial_report_ai_assistant.services.rag_service import get_current_pdf_hash
    pdf_hash = get_current_pdf_hash()
    if pdf_hash:
        return get_cached_data(pdf_hash)
    return None


def clear_cache(pdf_hash: str = None):
    """清除缓存"""
    with _lock:
        if pdf_hash:
            _cache.pop(pdf_hash, None)
        else:
            _cache.clear()
