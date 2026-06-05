"""自动化测试脚本 - AI财报分析助手测试用例"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import requests
import json
import time

BASE_URL = "http://localhost:8000"

# Sheet 1 和 Sheet 2 的测试问题
QUESTIONS = [
    "营收是多少？",
    "净利润是多少？",
    "总资产是多少？",
    "毛利率是多少？",
    "净利率是多少？",
    "ROE是多少？",
    "EPS是多少？",
    "净利润同比增长率",
    "营收同比增长率",
    "成长趋势如何？",
    "资产负债率",
    "流动比率",
    "速动比率",
    "资产周转率",
    "存货周转率",
    "财务摘要",
    "盈利能力评估",
    "风险分析",
    "行业对比",
]

def upload_pdf(filepath):
    """上传 PDF 并返回结果"""
    print(f"\n{'='*60}")
    print(f"上传文件: {filepath}")
    print(f"{'='*60}")
    with open(filepath, "rb") as f:
        files = {"file": (filepath.split("/")[-1].split("\\")[-1], f, "application/pdf")}
        resp = requests.post(f"{BASE_URL}/upload", files=files, timeout=300)
    if resp.status_code == 200:
        result = resp.json()
        print(f"上传成功! pdf_hash: {result.get('pdf_hash', 'N/A')}")
        return result.get("pdf_hash", "")
    else:
        print(f"上传失败: {resp.status_code} - {resp.text}")
        return None

def ask_question(question, pdf_hash="", conversation_history=None):
    """提问并返回回答"""
    if conversation_history is None:
        conversation_history = []
    payload = {
        "question": question,
        "conversation_history": conversation_history,
        "pdf_hash": pdf_hash,
    }
    resp = requests.post(f"{BASE_URL}/chat", json=payload, timeout=120)
    if resp.status_code == 200:
        return resp.json()
    else:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

def run_test_sheet(pdf_path, sheet_name):
    """对一份 PDF 运行全部 19 个测试"""
    pdf_hash = upload_pdf(pdf_path)
    if not pdf_hash:
        print(f"跳过 {sheet_name}")
        return []

    # 等待 RAG 索引构建完成
    time.sleep(3)

    results = []
    conversation_history = []

    for i, q in enumerate(QUESTIONS):
        print(f"\n[{sheet_name}] Q{i+1}: {q}")
        answer_data = ask_question(q, pdf_hash, conversation_history)
        answer = answer_data.get("answer", answer_data.get("error", "无回答"))
        source_page = answer_data.get("source_page", "N/A")
        source_pages = answer_data.get("source_pages", [])

        # 截断显示
        answer_short = answer[:300] + "..." if len(answer) > 300 else answer
        print(f"  回答: {answer_short}")
        print(f"  来源页: {source_page}, 所有来源页: {source_pages}")

        results.append({
            "seq": i + 1,
            "question": q,
            "answer": answer,
            "source_page": source_page,
            "source_pages": source_pages,
        })

        # 维护对话历史
        conversation_history.append([q, answer])

    return results

def main():
    pdf1 = r"D:\Projects\Python\financial-report-ai-assistant\中兴通讯：2025年年度报告摘要.PDF"
    pdf2 = r"D:\Projects\Python\financial-report-ai-assistant\600212_20260430_6IF1.pdf"

    print("=" * 60)
    print("开始测试 Sheet 1 (中兴通讯)")
    print("=" * 60)
    sheet1_results = run_test_sheet(pdf1, "Sheet1")

    print("\n\n")
    print("=" * 60)
    print("开始测试 Sheet 2 (600212)")
    print("=" * 60)
    sheet2_results = run_test_sheet(pdf2, "Sheet2")

    # 保存结果到 JSON
    output = {
        "sheet1": sheet1_results,
        "sheet2": sheet2_results,
    }
    with open("test_results.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n\n结果已保存到 test_results.json")

if __name__ == "__main__":
    main()
