# 文件: scout_v2.py
import fitz
import re

def scout_v2(pdf_path: str):
    doc = fitz.open(pdf_path)
    print(f"🚀 Scout V2 启动，扫描 {doc.page_count} 页...\n")
    
    # 定义计分规则
    # 格式: {"关键词": 分数}
    structure_keywords = {
        "Organizational Structure": 5,  # 核心词
        "Diagram": 3,                   # 辅助词：通常图表页会有这个词
        "subsidiaries": 1,
        "holding": 1
    }
    
    financial_keywords = {
        "Financial Summary": 10,        # 核心词：针对摘要表
        "Consolidated Statements of Operations": 10, # 核心词：针对正式表
        "Revenue": 2,                   # 辅助词：必须有营收
        "Net income": 2,                # 辅助词：必须有净利
        "Year ended March 31": 3        # 辅助词：表头特征
    }

    # 用于存储每一页的得分
    page_scores = []

    for i, page in enumerate(doc):
        text = page.get_text()
        
        # --- 1. 架构图评分 ---
        struct_score = 0
        hit_words = []
        for kw, score in structure_keywords.items():
            # 忽略大小写匹配
            if re.search(re.escape(kw), text, re.IGNORECASE):
                struct_score += score
                hit_words.append(kw)
        
        # 惩罚机制：如果这一页字数特别多（>3000字符），可能是法律文本，扣分
        if len(text) > 3000:
            struct_score -= 5
            
        # --- 2. 利润表评分 ---
        fin_score = 0
        fin_hits = []
        for kw, score in financial_keywords.items():
            if re.search(re.escape(kw), text, re.IGNORECASE):
                fin_score += score
                fin_hits.append(kw)

        # 记录高分页 (只记录有分数的，减少日志干扰)
        if struct_score > 5 or fin_score > 5:
            page_scores.append({
                "page": i + 1,
                "struct_score": struct_score,
                "fin_score": fin_score,
                "struct_hits": hit_words,
                "fin_hits": fin_hits,
                "text_len": len(text)
            })

    # --- 决算时刻：选出冠军 ---
    # 按分数排序，取 Top 1
    best_structure = sorted(page_scores, key=lambda x: x['struct_score'], reverse=True)
    best_financial = sorted(page_scores, key=lambda x: x['fin_score'], reverse=True)

    print("-" * 30)
    print("🏆 侦察结果分析：")
    
    if best_structure:
        top1 = best_structure[0]
        print(f"✅ 最佳架构图: 第 {top1['page']} 页 (得分: {top1['struct_score']})")
        print(f"   - 命中关键词: {top1['struct_hits']}")
        print(f"   - 页面字数: {top1['text_len']}")
    else:
        print("❌ 未找到架构图")

    if best_financial:
        top1 = best_financial[0]
        print(f"✅ 最佳利润表: 第 {top1['page']} 页 (得分: {top1['fin_score']})")
        print(f"   - 命中关键词: {top1['fin_hits']}")
    else:
        print("❌ 未找到利润表")
        
    print("-" * 30)
    # 打印前3名候补，方便调试
    print("\n🔍 候补名单 (调试用):")
    print(f"架构图 Top 3: {[p['page'] for p in best_structure[:3]]}")
    print(f"利润表 Top 3: {[p['page'] for p in best_financial[:3]]}")

if __name__ == "__main__":
    try:
        scout_v2("temp_upload.pdf") 
    except FileNotFoundError:
        print("❌ 请确保 'temp_upload.pdf' 存在于根目录")