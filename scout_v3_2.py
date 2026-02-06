# 文件: scout_v3_2.py
import fitz
import re

def scout_v3_2(pdf_path: str):
    doc = fitz.open(pdf_path)
    print(f"🚀 Scout V3.2 (严苛模式) 启动...\n")
    
    # 定义你要观察的特定页面 (方便调试 P50, P56, P92)
    # 注意：这里填的是物理页码
    debug_pages = [50, 56, 92] 

    page_scores = []

    for i, page in enumerate(doc):
        text = page.get_text()
        phys_page = i + 1
        
        # --- 1. 视觉特征提取 ---
        drawings = len(page.get_drawings()) # 矢量绘图数量
        images = len(page.get_images())     # 图片数量
        
        # --- 2. 架构图评分逻辑 (大幅升级) ---
        struct_score = 0
        hit_reasons = []
        
        # A. 关键词检测 (Organizational Structure)
        if re.search(r"Organizational Structure", text, re.IGNORECASE):
            # 【新规则】: 关键词必须在页面上半部分 (前500字符)，防止正文引用干扰
            if text.find("Organizational Structure") < 500:
                struct_score += 10
                hit_reasons.append("Title Match")
            else:
                # 如果只是在正文里提到，分数很低
                struct_score += 1
                hit_reasons.append("Text Ref")
        
        # B. 视觉检测 (阈值大幅提高)
        # 真正的架构图通常由大量方框(rect)和线条(line)组成，数量通常 > 30
        if struct_score > 0: # 必须先有关键词
            if drawings > 30: 
                struct_score += 50
                hit_reasons.append(f"Complex Vector({drawings})")
            elif images >= 1: 
                struct_score += 50
                hit_reasons.append(f"Image Object({images})")
            
        # --- 3. 利润表评分逻辑 (保持稳健) ---
        fin_score = 0
        if "Financial Summary" in text and "Revenue" in text:
             fin_score += 20
        elif "Consolidated Statements of Operations" in text and "Revenue" in text:
             fin_score += 20

        # 记录
        page_scores.append({
            "page": phys_page,
            "struct_score": struct_score,
            "fin_score": fin_score,
            "reasons": hit_reasons
        })

        # --- 🔍 重点嫌疑人调试日志 ---
        if phys_page in debug_pages:
            print(f"🔍 [调试 P{phys_page}]")
            print(f"   - 架构图得分: {struct_score} {hit_reasons}")
            print(f"   - 视觉特征: Vector={drawings}, Image={images}")
            print(f"   - 文本前100字: {text[:50].replace(chr(10), ' ')}...\n")

    # --- 结算 ---
    best_structure = sorted(page_scores, key=lambda x: x['struct_score'], reverse=True)[0]
    best_financial = sorted(page_scores, key=lambda x: x['fin_score'], reverse=True)[0]

    print("-" * 30)
    print(f"✅ 最终推荐架构图: 第 {best_structure['page']} 页 (分: {best_structure['struct_score']})")
    print(f"✅ 最终推荐利润表: 第 {best_financial['page']} 页 (分: {best_financial['fin_score']})")

if __name__ == "__main__":
    try:
        scout_v3_2("temp_upload.pdf") 
    except FileNotFoundError:
        print("❌ 未找到文件")