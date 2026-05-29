"""API 层共享工具函数"""

import re


def extract_cited_pages(text: str) -> list:
    """从 LLM 回答中提取引用的页码（如"根据第3页数据"或"（第3页）"）"""
    return list(dict.fromkeys(
        int(m) for m in re.findall(r'第(\d+)页', text)
    ))
