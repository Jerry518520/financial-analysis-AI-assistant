# 测试脚本：检查解析和RAG构建

import requests
import os
import json

# 1. 清理旧缓存
print("清理缓存...")
if os.path.exists('cache_data'):
    import shutil
    shutil.rmtree('cache_data')
if os.path.exists('faiss_index'):
    import shutil
    shutil.rmtree('faiss_index')
os.makedirs('cache_data', exist_ok=True)

# 2. 上传文件
print("\n上传文件...")
url = 'http://localhost:8000/upload'
files = {'file': open('中兴通讯：2025年年度报告摘要.PDF', 'rb')}
response = requests.post(url, files=files)
print(f"状态码: {response.status_code}")
print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

# 3. 检查缓存
print("\n检查缓存...")
cache_files = os.listdir('cache_data')
print(f"缓存文件: {cache_files}")

# 4. 尝试生成摘要
print("\n生成摘要...")
url = 'http://localhost:8000/analyze/summary'
data = {'focus': 'general'}
response = requests.post(url, json=data)
print(f"状态码: {response.status_code}")
print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")

# 5. 检查 faiss_index
print("\n检查 faiss_index...")
if os.path.exists('faiss_index'):
    index_files = os.listdir('faiss_index')
    print(f"索引文件: {index_files}")
else:
    print("faiss_index 目录不存在")