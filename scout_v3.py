# 文件: scout_v3.py (终极侦察兵)
import fitz
import re

def scout_v3(pdf_path: str):
    doc = fitz.open(pdf_path)
    print(f"🚀 Scout V3 (X-Ray Mode) 启动，扫描 {doc.page_count} 页...\n")
    
    structure_keywords = {
        "Organizational Structure": 5,
        "Diagram": 3,
        "subsidiaries": 1
    }
    
    financial_keywords = {
        "Financial Summary": 10,
        "Consolidated Statements of Operations": 10,
        "Revenue": 2,
        "Net income": 2,
        "Year ended March 31": 3
    }

    page_scores = []

    for i, page in enumerate(doc):
        text = page.get_text()
        
        # --- [新功能] X光检测：计算绘图指令数量 ---
        # get_drawings() 会返回页面上的线条、方框等矢量图数量
        drawings = page.get_drawings()
        drawings_count = len(drawings)
        
        # --- 1. 架构图评分 ---
        struct_score = 0
        hit_words = []
        for kw, score in structure_keywords.items():
            if re.search(re.escape(kw), text, re.IGNORECASE):
                struct_score += score
                hit_words.append(kw)
        
        # 【核心逻辑升级】
        # 如果命中了 "Structure" 关键词，且页面上有大量绘图 (>10个)，大概率是真图
        if struct_score > 0 and drawings_count > 10:
            struct_score += 50  # 给予巨大奖励，直接秒杀纯文本页
            hit_words.append(f"[Graphics found: {drawings_count}]")
            
        # --- 2. 利润表评分 (保持不变) ---
        fin_score = 0
        fin_hits = []
        for kw, score in financial_keywords.items():
            if re.search(re.escape(kw), text, re.IGNORECASE):
                fin_score += score
                fin_hits.append(kw)

        if struct_score > 5 or fin_score > 5:
            page_scores.append({
                "page": i + 1,
                "struct_score": struct_score,
                "fin_score": fin_score,
                "struct_hits": hit_words,
                "fin_hits": fin_hits
            })

    # --- 结算 ---
    best_structure = sorted(page_scores, key=lambda x: x['struct_score'], reverse=True)
    best_financial = sorted(page_scores, key=lambda x: x['fin_score'], reverse=True)

    print("-" * 30)
    if best_structure:
        top1 = best_structure[0]
        print(f"✅ 最佳架构图: 第 {top1['page']} 页 (得分: {top1['struct_score']})")
        print(f"   - 命中特征: {top1['struct_hits']}")
    else:
        print("❌ 未找到架构图")

    if best_financial:
        top1 = best_financial[0]
        print(f"✅ 最佳利润表: 第 {top1['page']} 页 (得分: {top1['fin_score']})")
        print(f"   - 命中特征: {top1['fin_hits']}")
    print("-" * 30)

if __name__ == "__main__":
    try:
        scout_v3("temp_upload.pdf") 
    except FileNotFoundError:
        print("❌ 未找到文件")