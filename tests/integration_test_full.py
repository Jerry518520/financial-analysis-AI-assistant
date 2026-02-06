import requests
import time
import subprocess
import os
import sys

# 配置
API_URL = "http://127.0.0.1:8000"
PDF_PATH = r"d:\Projects\Python\financial-report-ai-assistant\example_report.pdf"

def wait_for_server(url, timeout=30):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            resp = requests.get(url)
            if resp.status_code == 200:
                print("✅ 服务器已就绪！")
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)
        print("Waiting for server...")
    print("❌ 服务器启动超时！")
    return False

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
        resp = requests.post(f"{API_URL}/chat", json=payload)
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
    # 假设财报里有相关数据，或者我们可以问一个通用的计算问题来测试工具调用
    # 比如我们问一个显式包含数字的问题，强迫 Agent 计算
    question = "如果本期营收是 1000 万，上期是 800 万，请帮我计算同比增长率是多少？"
    payload = {"question": question}
    try:
        resp = requests.post(f"{API_URL}/chat", json=payload)
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

def main():
    # 1. 启动服务
    print("🚀 正在启动 uvicorn 服务...")
    # 使用 Popen 后台启动
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "financial_report_ai_assistant.api.main:app", "--host", "127.0.0.1", "--port", "8000", "--app-dir", "src"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        # creationflags=subprocess.CREATE_NEW_CONSOLE # Windows only, optional to see logs
    )
    
    try:
        if wait_for_server(API_URL):
            # 2. 运行测试
            if test_upload():
                test_chat_rag()
                test_chat_calculation()
        else:
            print("Skipping tests due to server failure.")
    finally:
        # 3. 清理服务
        print("\n🛑 正在停止服务...")
        process.terminate()
        process.wait()
        print("✅ 服务已停止。")

if __name__ == "__main__":
    main()
