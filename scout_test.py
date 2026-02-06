# 文件: scout_test.py (用于测试自动寻页逻辑)
import fitz
import re

def scout_high_value_pages(pdf_path: str):
    doc = fitz.open(pdf_path)
    
    # 定义“高价值”的指纹特征
    # 比如：利润表通常包含 "Consolidated Statements of Operations" 且包含 "Revenue"
    # 比如：架构图通常包含 "Organizational Structure"
    
    targets = {
        "structure_chart": [],
        "financial_table": []
    }
    
    print(f"🕵️ 侦察兵启动，正在扫描 {doc.page_count} 页文档...")
    
    for i, page in enumerate(doc):
        text = page.get_text()
        
        # 1. 寻找架构图 (Structure)
        # 规则：标题包含 Structure，且正文包含 Diagram 或 Subsidiaries
        if "Organizational Structure" in text and ("Diagram" in text or "subsidiaries" in text):
            # 记录物理页码 (i+1)
            targets["structure_chart"].append(i + 1)
            print(f"   [P{i+1}] 发现疑似架构图！")

        # 2. 寻找利润表 (Operations / Income)
        # 规则：标题包含 Consolidated Statements...Operations 且包含 Revenue
        # 注意：有时候标题是全部大写的，要忽略大小写
        if "Consolidated Statements of Operations" in text and "Revenue" in text:
             targets["financial_table"].append(i + 1)
             print(f"   [P{i+1}] 发现疑似利润表！")
             
    print("\n✅ 侦察报告：")
    print(f"   架构图位置: {targets['structure_chart']}")
    print(f"   利润表位置: {targets['financial_table']}")
    
    return targets

if __name__ == "__main__":
    # 替换成你本地的那个临时文件名，或者重新上传后的路径
    # 如果不知道文件名，可以去查看 create_sniper_pdf 里的逻辑，或者直接指定你测试用的那个全量PDF
    # 这里假设你有个 full.pdf (你需要把之前的阿里财报重命名为 full.pdf 放在根目录方便测试)
    try:
        scout_high_value_pages("temp_upload.pdf") # 或者你上传时的原始文件名
    except:
        print("请把你的财报 PDF 放在根目录并重命名为 temp_upload.pdf 后再运行此脚本")