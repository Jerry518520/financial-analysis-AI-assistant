"""
AI财报分析助手 - 自动化测试脚本
按照测试用例逐一提问，对比参考答案，输出判定结果
"""
import requests
import time
import sys
import os

# Windows GBK encoding fix
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

API_URL = "http://127.0.0.1:8000"

# Sheet 1: 中兴通讯 2025年年度报告
SHEET1_PDF = r"d:\Projects\Python\financial-report-ai-assistant\cache_data\current_5e2036053ccf0722489cb9ccedfcd836.pdf"
SHEET1_TESTS = [
    {"id": 1, "cat": "基础数据类", "q": "营收是多少？", "ref": ["133,895.5", "133895.5", "133,895,500,000", "133895500000", "1338.95"]},
    {"id": 2, "cat": "基础数据类", "q": "净利润是多少？", "ref": ["5,617.7", "5617.7", "5,617,700,000", "5617700000", "56.18"]},
    {"id": 3, "cat": "基础数据类", "q": "总资产是多少？", "ref": ["217,739.4", "217739.4", "2177.39"]},
    {"id": 4, "cat": "盈利能力类", "q": "毛利率是多少？", "ref": ["31.28", "28.16"]},
    {"id": 5, "cat": "盈利能力类", "q": "净利率是多少？", "ref": ["4.20", "4.2%"]},
    {"id": 6, "cat": "盈利能力类", "q": "ROE是多少？", "ref": ["7.58", "0.0758"]},
    {"id": 7, "cat": "盈利能力类", "q": "EPS是多少？", "ref": ["1.17", "1.16"]},
    {"id": 8, "cat": "成长能力类", "q": "净利润同比增长率", "ref": ["-33.32", "下降33.32"]},
    {"id": 9, "cat": "成长能力类", "q": "营收同比增长率", "ref": ["10.38", "增长10.38"]},
    {"id": 10, "cat": "成长能力类", "q": "成长趋势如何？", "ref": ["收入", "增长", "承压"]},
    {"id": 11, "cat": "偿债能力类", "q": "资产负债率", "ref": ["65.26"]},
    {"id": 12, "cat": "偿债能力类", "q": "流动比率", "ref": ["1.76"]},
    {"id": 13, "cat": "偿债能力类", "q": "速动比率", "ref": ["1.16"]},
    {"id": 14, "cat": "运营能力类", "q": "资产周转率", "ref": ["0.63", "0.61", "0.59"]},
    {"id": 15, "cat": "运营能力类", "q": "存货周转率", "ref": ["未找到", "未提供", "未直接", "没有"]},
    {"id": 16, "cat": "综合分析类", "q": "财务摘要", "ref": ["收入", "增长"]},
    {"id": 17, "cat": "综合分析类", "q": "盈利能力评估", "ref": ["收入", "利润", "下降"]},
    {"id": 18, "cat": "综合分析类", "q": "风险分析", "ref": ["盈利", "现金流", "风险"]},
    {"id": 19, "cat": "综合分析类", "q": "行业对比", "ref": ["梯队", "增长", "潜力"]},
]

# Sheet 2: 600212 2026年Q1报告
SHEET2_PDF = r"d:\Projects\Python\financial-report-ai-assistant\600212_20260430_6IF1.pdf"
SHEET2_TESTS = [
    {"id": 1, "cat": "基础数据类", "q": "营收是多少？", "ref": ["298,539,137.97", "298539137.97"]},
    {"id": 2, "cat": "基础数据类", "q": "净利润是多少？", "ref": ["-20,853,234.99", "-21,496,858.30"]},
    {"id": 3, "cat": "基础数据类", "q": "总资产是多少？", "ref": ["2,687,936,467.26", "2687936467.26", "26.88"]},
    {"id": 4, "cat": "盈利能力类", "q": "毛利率是多少？", "ref": ["24.21"]},
    {"id": 5, "cat": "盈利能力类", "q": "净利率是多少？", "ref": ["-6.98", "-6.99", "-7.20", "-4.19"]},
    {"id": 6, "cat": "盈利能力类", "q": "ROE是多少？", "ref": ["-3.66"]},
    {"id": 7, "cat": "盈利能力类", "q": "EPS是多少？", "ref": ["-0.0305"]},
    {"id": 8, "cat": "成长能力类", "q": "净利润同比增长率", "ref": ["-207.78", "-2.0778"]},
    {"id": 9, "cat": "成长能力类", "q": "营收同比增长率", "ref": ["48.24"]},
    {"id": 10, "cat": "成长能力类", "q": "成长趋势如何？", "ref": ["增长", "高速"]},
    {"id": 11, "cat": "偿债能力类", "q": "资产负债率", "ref": ["77.59"]},
    {"id": 12, "cat": "偿债能力类", "q": "流动比率", "ref": ["1.20", "1.2"]},
    {"id": 13, "cat": "偿债能力类", "q": "速动比率", "ref": ["0.82"]},
    {"id": 14, "cat": "运营能力类", "q": "资产周转率", "ref": ["0.11"]},
    {"id": 15, "cat": "运营能力类", "q": "存货周转率", "ref": ["0.32"]},
    {"id": 16, "cat": "综合分析类", "q": "财务摘要", "ref": ["亏损"]},
    {"id": 17, "cat": "综合分析类", "q": "盈利能力评估", "ref": ["盈利", "较弱", "亏损"]},
    {"id": 18, "cat": "综合分析类", "q": "风险分析", "ref": ["风险", "偿债", "盈利"]},
    {"id": 19, "cat": "综合分析类", "q": "行业对比", "ref": ["行业", "对比"]},
]


def upload_pdf(pdf_path, force_upload=False):
    """上传PDF并等待RAG构建完成"""
    print(f"\n📤 上传PDF: {pdf_path}")

    # 检查是否已有索引（除非强制上传）
    if not force_upload:
        try:
            resp = requests.post(f"{API_URL}/chat", json={"question": "test"}, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if "pdf_hash" in data and data["pdf_hash"]:
                    print(f"   ✅ 已有索引，跳过上传 (hash={data['pdf_hash'][:8]}...)")
                    return True
        except:
            pass

    with open(pdf_path, "rb") as f:
        files = {"file": (pdf_path.split("\\")[-1], f, "application/pdf")}
        resp = requests.post(f"{API_URL}/upload", files=files, timeout=600)
    if resp.status_code == 200:
        data = resp.json()
        print(f"   ✅ 上传成功, hash={data.get('pdf_hash', 'N/A')[:8]}...")
        time.sleep(15)  # 等待后台财务数据提取完成
        return True
    else:
        print(f"   ❌ 上传失败: {resp.status_code} - {resp.text[:200]}")
        return False


def ask_question(question, timeout=90):
    """提问并返回答案"""
    payload = {"question": question}
    try:
        resp = requests.post(f"{API_URL}/chat", json=payload, timeout=timeout)
        if resp.status_code == 200:
            return resp.json().get("answer", "")
        else:
            return f"[HTTP {resp.status_code}] {resp.text[:200]}"
    except requests.exceptions.Timeout:
        return "[TIMEOUT] 请求超时"
    except Exception as e:
        return f"[ERROR] {str(e)}"


def check_answer(answer, ref_keywords):
    """检查答案是否包含参考关键词"""
    if not answer:
        return "❌", "无回答"

    answer_lower = answer.lower().replace(",", "").replace(" ", "")

    matched = []
    for kw in ref_keywords:
        kw_lower = kw.lower().replace(",", "").replace(" ", "")
        if kw_lower in answer_lower:
            matched.append(kw)

    if len(matched) >= 1:
        return "✅", f"匹配: {', '.join(matched)}"
    else:
        return "❌", f"未匹配任何关键词"


def run_sheet(sheet_name, pdf_path, tests, force_upload=True):
    """运行一个Sheet的所有测试"""
    print(f"\n{'='*60}")
    print(f"📋 开始测试: {sheet_name}")
    print(f"{'='*60}")

    if not upload_pdf(pdf_path, force_upload=force_upload):
        return []

    results = []
    for t in tests:
        print(f"\n--- Q{t['id']:02d} [{t['cat']}] {t['q']} ---")
        answer = ask_question(t["q"])
        status, reason = check_answer(answer, t["ref"])

        # 截断过长的回答用于显示
        display_answer = answer[:200] + "..." if len(answer) > 200 else answer
        print(f"   回答: {display_answer}")
        print(f"   判定: {status} ({reason})")

        results.append({
            "id": t["id"],
            "cat": t["cat"],
            "q": t["q"],
            "answer": answer,
            "status": status,
            "reason": reason,
            "ref": t["ref"],
        })

    return results


def print_summary(sheet_name, results):
    """打印Sheet测试汇总"""
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "✅")
    failed = sum(1 for r in results if r["status"] == "❌")

    print(f"\n{'='*60}")
    print(f"📊 {sheet_name} 测试结果汇总")
    print(f"{'='*60}")
    print(f"   总题数: {total}")
    print(f"   通过:   {passed}")
    print(f"   失败:   {failed}")
    print(f"   通过率: {passed/total*100:.1f}%")

    if failed > 0:
        print(f"\n   失败项:")
        for r in results:
            if r["status"] == "❌":
                print(f"   - Q{r['id']:02d} [{r['cat']}] {r['q']}")
                answer_short = r["answer"][:100] if r["answer"] else "(无回答)"
                print(f"     回答: {answer_short}")
                print(f"     期望包含: {r['ref']}")


def main():
    print("🚀 AI财报分析助手 - 自动化测试")
    print(f"   API: {API_URL}")

    # 检查服务器
    try:
        resp = requests.get(f"{API_URL}/", timeout=5)
        if resp.status_code != 200:
            print("❌ 服务器未就绪")
            sys.exit(1)
        print("   ✅ 服务器已就绪")
    except:
        print("❌ 无法连接服务器，请先启动后端服务")
        sys.exit(1)

    # 运行 Sheet 1
    sheet1_results = run_sheet("Sheet 1 (中兴通讯)", SHEET1_PDF, SHEET1_TESTS)
    print_summary("Sheet 1 (中兴通讯)", sheet1_results)

    # 运行 Sheet 2
    sheet2_results = run_sheet("Sheet 2 (600212)", SHEET2_PDF, SHEET2_TESTS)
    print_summary("Sheet 2 (600212)", sheet2_results)

    # 总汇总
    all_results = sheet1_results + sheet2_results
    total = len(all_results)
    passed = sum(1 for r in all_results if r["status"] == "✅")
    failed = sum(1 for r in all_results if r["status"] == "❌")

    print(f"\n{'='*60}")
    print(f"📊 总汇总")
    print(f"{'='*60}")
    print(f"   总题数: {total}")
    print(f"   通过:   {passed}")
    print(f"   失败:   {failed}")
    print(f"   通过率: {passed/total*100:.1f}%")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
