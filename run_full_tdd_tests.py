"""
AI财报分析助手 - 完整TDD测试脚本
1. 按测试用例逐一提问，对比参考答案
2. 生成核心概要，验证概要数据与对话数据一致性
"""
import requests
import time
import sys
import os
import json
import re

# Windows GBK encoding fix
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

API_URL = "http://127.0.0.1:8000"

# Sheet 1: 中兴通讯 2025年年度报告
SHEET1_PDF = r"d:\Projects\Python\financial-report-ai-assistant\cache_data\current_5e2036053ccf0722489cb9ccedfcd836.pdf"
SHEET1_TESTS = [
    {"id": 1, "cat": "基础数据类", "q": "营收是多少？", "ref": ["133,895.5", "133895.5", "133895500000", "1338.95"]},
    {"id": 2, "cat": "基础数据类", "q": "净利润是多少？", "ref": ["5,617.7", "5617.7", "5617700000", "56.18"]},
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
    {"id": 8, "cat": "成长能力类", "q": "净利润同比增长率", "ref": ["-207.78", "-2.0778", "207.78", "亏损扩大", "亏损"]},
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

# 核心概要一致性验证的关键数据点
SUMMARY_CONSISTENCY_CHECKS_SHEET1 = {
    "营业收入": ["133,895.5", "133895.5", "1338.96", "1,338.95", "1338.95", "1,338.96"],
    "净利润": ["5,617.7", "5617.7", "56.18"],
    "总资产": ["217,739.4", "217739.4", "2177.39", "2,177.39", "2177.39"],
    "毛利率": ["31.28"],
    "净利率": ["4.20", "4.2"],
    "ROE": ["7.58"],
    "EPS": ["1.17"],
    "营收增长率": ["10.38"],
    "净利润增长率": ["-33.32", "33.32"],
    "资产负债率": ["65.26"],
    "流动比率": ["1.76"],
    "速动比率": ["1.16"],
}

SUMMARY_CONSISTENCY_CHECKS_SHEET2 = {
    "营业收入": ["298,539,137.97", "298539137.97", "2.99", "2.99"],
    "净利润": ["-20,853,234.99", "-21,496,858.30", "-0.21", "-2149.69", "-2085.32"],
    "总资产": ["2,687,936,467.26", "2687936467.26", "26.88", "26.76"],
    "毛利率": ["24.21"],
    "净利率": ["-6.98", "-6.99", "-7.20"],
    "ROE": ["-3.66"],
    "EPS": ["-0.0305"],
    "营收增长率": ["48.24"],
    "资产负债率": ["77.59"],
    "流动比率": ["1.20", "1.2"],
    "速动比率": ["0.82"],
}


def upload_pdf(pdf_path, force_upload=True):
    """上传PDF并等待RAG构建完成"""
    print(f"\n📤 上传PDF: {os.path.basename(pdf_path)}")

    with open(pdf_path, "rb") as f:
        files = {"file": (os.path.basename(pdf_path), f, "application/pdf")}
        resp = requests.post(f"{API_URL}/upload", files=files, timeout=600)
    if resp.status_code == 200:
        data = resp.json()
        print(f"   ✅ 上传成功, hash={data.get('pdf_hash', 'N/A')[:8]}...")
        time.sleep(15)  # 等待后台提取完成（含正则兜底提取资产负债表数据）
        return data.get('pdf_hash', '')
    else:
        print(f"   ❌ 上传失败: {resp.status_code} - {resp.text[:200]}")
        return None


def ask_question(question, timeout=120):
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


def generate_summary(focus="general"):
    """生成核心概要"""
    try:
        resp = requests.post(f"{API_URL}/analyze/summary", json={"focus": focus}, timeout=180)
        if resp.status_code == 200:
            return resp.json().get("summary", "")
        else:
            return f"[HTTP {resp.status_code}] {resp.text[:200]}"
    except requests.exceptions.Timeout:
        return "[TIMEOUT] 摘要生成超时"
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


def _extract_numbers_from_text(text: str) -> set:
    """从文本中提取所有数值（支持百分比、亿元、百万元等格式）"""
    import re
    text_clean = text.lower().replace(",", "").replace(" ", "")
    # 提取所有数字（包括小数、负数）
    numbers = set()
    for match in re.finditer(r'-?\d+\.?\d*', text_clean):
        numbers.add(match.group())
    return numbers


def _convert_to_comparable_numbers(keywords: list) -> set:
    """将关键词列表转换为可比较的数值集合，支持单位换算"""
    import re
    numbers = set()
    for kw in keywords:
        kw_clean = kw.replace(",", "").replace(" ", "")
        # 提取数值
        match = re.search(r'-?\d+\.?\d*', kw_clean)
        if match:
            num = float(match.group())
            numbers.add(match.group())
            # 如果是百万元单位，也添加亿元等价物
            if num > 1000:  # 大数值可能是百万元
                yi_value = num / 10000  # 百万→亿
                numbers.add(f"{yi_value:.2f}")
                numbers.add(f"{yi_value:.1f}")
    return numbers


def check_summary_consistency(summary, chat_answers, consistency_checks, sheet_name):
    """验证核心概要数据与对话回答的一致性，支持单位换算匹配"""
    print(f"\n{'='*60}")
    print(f"🔍 {sheet_name} - 核心概要一致性验证")
    print(f"{'='*60}")

    if not summary or summary.startswith("["):
        print(f"   ❌ 概要生成失败: {summary[:100]}")
        return []

    results = []
    summary_numbers = _extract_numbers_from_text(summary)

    for data_name, keywords in consistency_checks.items():
        # 检查概要中是否包含关键数据（支持字符串匹配和数值匹配）
        found_in_summary = False
        matched_kw = ""
        summary_clean = summary.lower().replace(",", "").replace(" ", "")

        # 1. 字符串匹配
        for kw in keywords:
            kw_clean = kw.lower().replace(",", "").replace(" ", "")
            if kw_clean in summary_clean:
                found_in_summary = True
                matched_kw = kw
                break

        # 2. 数值匹配（支持单位换算）
        if not found_in_summary:
            ref_numbers = _convert_to_comparable_numbers(keywords)
            matched_numbers = ref_numbers & summary_numbers
            if matched_numbers:
                found_in_summary = True
                matched_kw = f"数值匹配:{matched_numbers.pop()}"

        # 检查对话回答中是否包含该数据
        found_in_chat = False
        chat_matched = ""
        for answer_data in chat_answers:
            answer_text = answer_data.get("answer", "").lower().replace(",", "").replace(" ", "")
            for kw in keywords:
                kw_clean = kw.lower().replace(",", "").replace(" ", "")
                if kw_clean in answer_text:
                    found_in_chat = True
                    chat_matched = kw
                    break
            if found_in_chat:
                break

        # 判定一致性
        if found_in_summary and found_in_chat:
            status = "✅"
            reason = f"概要与对话均包含 {matched_kw}/{chat_matched}"
        elif found_in_summary and not found_in_chat:
            status = "⚠️"
            reason = f"概要包含 {matched_kw}，但对话中未找到"
        elif not found_in_summary and found_in_chat:
            status = "❌"
            reason = f"对话包含 {chat_matched}，但概要中缺失"
        else:
            status = "❌"
            reason = "概要和对话中均未找到"

        print(f"   {status} {data_name}: {reason}")
        results.append({
            "data_name": data_name,
            "status": status,
            "reason": reason,
            "found_in_summary": found_in_summary,
            "found_in_chat": found_in_chat,
        })

    return results


def run_sheet(sheet_name, pdf_path, tests, consistency_checks, force_upload=True):
    """运行一个Sheet的所有测试"""
    print(f"\n{'='*60}")
    print(f"📋 开始测试: {sheet_name}")
    print(f"{'='*60}")

    pdf_hash = upload_pdf(pdf_path, force_upload=force_upload)
    if not pdf_hash:
        return [], [], ""

    # Part 1: 逐一提问
    results = []
    for t in tests:
        print(f"\n--- Q{t['id']:02d} [{t['cat']}] {t['q']} ---")
        answer = ask_question(t["q"])
        status, reason = check_answer(answer, t["ref"])

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

    # Part 2: 生成核心概要
    print(f"\n--- 生成核心概要 ---")
    summary = generate_summary("general")
    if summary and not summary.startswith("["):
        print(f"   ✅ 概要生成成功 ({len(summary)} 字符)")
        # 显示概要前500字符
        print(f"   概要预览: {summary[:500]}...")
    else:
        print(f"   ❌ 概要生成失败: {summary[:100]}")

    # Part 3: 一致性验证
    consistency_results = check_summary_consistency(
        summary, results, consistency_checks, sheet_name
    )

    return results, consistency_results, summary


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


def print_consistency_summary(sheet_name, consistency_results):
    """打印一致性验证汇总"""
    if not consistency_results:
        print(f"\n   ⚠️ {sheet_name}: 无一致性验证结果")
        return

    total = len(consistency_results)
    consistent = sum(1 for r in consistency_results if r["status"] == "✅")
    warnings = sum(1 for r in consistency_results if r["status"] == "⚠️")
    inconsistent = sum(1 for r in consistency_results if r["status"] == "❌")

    print(f"\n{'='*60}")
    print(f"🔍 {sheet_name} 概要一致性汇总")
    print(f"{'='*60}")
    print(f"   检查项: {total}")
    print(f"   一致:   {consistent}")
    print(f"   警告:   {warnings}")
    print(f"   不一致: {inconsistent}")
    print(f"   一致率: {consistent/total*100:.1f}%")

    if inconsistent > 0:
        print(f"\n   不一致项:")
        for r in consistency_results:
            if r["status"] == "❌":
                print(f"   - {r['data_name']}: {r['reason']}")


def main():
    print("🚀 AI财报分析助手 - 完整TDD测试")
    print(f"   API: {API_URL}")
    print(f"   测试内容: 38题问答 + 核心概要一致性验证")

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

    # ===== Sheet 1 =====
    sheet1_results, sheet1_consistency, sheet1_summary = run_sheet(
        "Sheet 1 (中兴通讯)", SHEET1_PDF, SHEET1_TESTS, SUMMARY_CONSISTENCY_CHECKS_SHEET1
    )
    print_summary("Sheet 1 (中兴通讯)", sheet1_results)
    print_consistency_summary("Sheet 1 (中兴通讯)", sheet1_consistency)

    # ===== Sheet 2 =====
    sheet2_results, sheet2_consistency, sheet2_summary = run_sheet(
        "Sheet 2 (600212)", SHEET2_PDF, SHEET2_TESTS, SUMMARY_CONSISTENCY_CHECKS_SHEET2
    )
    print_summary("Sheet 2 (600212)", sheet2_results)
    print_consistency_summary("Sheet 2 (600212)", sheet2_consistency)

    # ===== 总汇总 =====
    all_results = sheet1_results + sheet2_results
    total = len(all_results)
    passed = sum(1 for r in all_results if r["status"] == "✅")
    failed = sum(1 for r in all_results if r["status"] == "❌")

    all_consistency = sheet1_consistency + sheet2_consistency
    c_total = len(all_consistency)
    c_consistent = sum(1 for r in all_consistency if r["status"] == "✅")
    c_inconsistent = sum(1 for r in all_consistency if r["status"] == "❌")

    print(f"\n{'='*60}")
    print(f"📊 总汇总")
    print(f"{'='*60}")
    print(f"   【问答测试】")
    print(f"   总题数: {total}")
    print(f"   通过:   {passed}")
    print(f"   失败:   {failed}")
    print(f"   通过率: {passed/total*100:.1f}%")
    print(f"")
    print(f"   【概要一致性】")
    print(f"   检查项: {c_total}")
    print(f"   一致:   {c_consistent}")
    print(f"   不一致: {c_inconsistent}")
    if c_total > 0:
        print(f"   一致率: {c_consistent/c_total*100:.1f}%")
    print(f"{'='*60}")

    # 保存详细结果
    output = {
        "sheet1": {
            "qa_results": sheet1_results,
            "consistency": sheet1_consistency,
            "summary_preview": sheet1_summary[:1000] if sheet1_summary else "",
        },
        "sheet2": {
            "qa_results": sheet2_results,
            "consistency": sheet2_consistency,
            "summary_preview": sheet2_summary[:1000] if sheet2_summary else "",
        },
        "totals": {
            "qa_total": total, "qa_passed": passed, "qa_failed": failed,
            "c_total": c_total, "c_consistent": c_consistent, "c_inconsistent": c_inconsistent,
        }
    }
    with open("tdd_test_results_full.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n📄 详细结果已保存到 tdd_test_results_full.json")


if __name__ == "__main__":
    main()
