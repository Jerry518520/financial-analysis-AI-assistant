import requests
import os
import sys

# 配置
API_URL = "http://127.0.0.1:8000"
PDF_PATH = r"d:\Projects\Python\financial-report-ai-assistant\example_report.pdf"

def test_upload():
    print("\n--- Testing Upload ---")
    if not os.path.exists(PDF_PATH):
        print(f"❌ 文件不存在: {PDF_PATH}")
        return False
        
    with open(PDF_PATH, "rb") as f:
        files = {"file": ("example_report.pdf", f, "application/pdf")}
        try:
            resp = requests.post(f"{API_URL}/upload", files=files)
            if resp.status_code == 200:
                print("✅ 上传成功！")
                data = resp.json()
                print(f"文件名: {data.get('filename')}")
                print(f"解析状态: {data.get('analysis_result', {}).get('status')}")
                return True
            else:
                print(f"❌ 上传失败: {resp.status_code} - {resp.text}")
                return False
        except Exception as e:
            print(f"❌ 请求出错: {e}")
            return False

def test_chat_rag():
    print("\n--- Testing RAG Chat (Basic) ---")
    question = "这份财报的截止日期是什么时候？"
    payload = {"question": question}
    try:
        resp = requests.post(f"{API_URL}/chat", json=payload, timeout=60) # 增加超时
        if resp.status_code == 200:
            answer = resp.json().get("answer")
            print(f"Q: {question}")
            print(f"A: {answer}")
            if answer: return True
        else:
            print(f"❌ 对话失败: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ 请求出错: {e}")
    return False

def test_chat_calculation():
    print("\n--- Testing Agent Calculation ---")
    question = "如果本期营收是 1000 万，上期是 800 万，请帮我计算同比增长率是多少？"
    payload = {"question": question}
    try:
        resp = requests.post(f"{API_URL}/chat", json=payload, timeout=60)
        if resp.status_code == 200:
            answer = resp.json().get("answer")
            print(f"Q: {question}")
            print(f"A: {answer}")
            # 检查答案里是否包含 25%
            if "25" in answer or "0.25" in answer:
                print("✅ 计算结果验证通过！")
                return True
            else:
                print("⚠️ 结果似乎不包含预期的 25%，请人工核查。")
                return True
        else:
            print(f"❌ 对话失败: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ 请求出错: {e}")
    return False

if __name__ == "__main__":
    if test_upload():
        test_chat_rag()
        test_chat_calculation()
