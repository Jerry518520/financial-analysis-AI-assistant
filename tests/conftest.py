"""
全局测试配置和公共 fixtures。
"""
import sys
import os
import pytest

# 确保 src 目录在 Python path 中
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# 设置测试用的环境变量（避免真实 API Key 泄露）
os.environ.setdefault("DEEPSEEK_API_KEY", "test-fake-key-for-testing")
os.environ.setdefault("LLAMA_CLOUD_API_KEY", "test-fake-key-for-testing")
os.environ.setdefault("HF_HUB_URL", "https://hf-mirror.com")
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
