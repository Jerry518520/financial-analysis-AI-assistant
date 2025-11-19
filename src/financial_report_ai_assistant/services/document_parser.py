# 文件: src/financial_report_ai_assistant/services/document_parser.py
import fitz  # PyMuPDF
import pandas as pd

def parse_pdf_bytes(file_content: bytes):
    """
    接收 PDF 的二进制数据，返回解析后的文本摘要和表格数据
    """
    with fitz.open(stream=file_content, filetype="pdf") as doc:
        
        page_count = doc.page_count
        first_page_text = ""
        if page_count > 0:
            first_page_text = doc.load_page(0).get_text()
            
        extracted_tables = []
        
        # --- 【关键修改】定义我们要扫描的页面 ---
        # 1. 扫描前 3 页 (看看封面信息)
        # 2. 扫描第 189 页 (索引是188) -> 这是你之前在 Notebook 里验证过有数据的地方！
        # 3. 稍微多看两页 (189, 190)
        target_pages = [0, 1, 2] 
        if page_count > 190:
            target_pages.extend([188, 189, 190]) 
        
        # 去重并排序，防止报错
        target_pages = sorted(list(set([p for p in target_pages if p < page_count])))

        print(f"正在扫描页面: {target_pages} ...") # 在后端终端打印日志，方便你观察

        for page_index in target_pages:
            page = doc.load_page(page_index)
            tables = page.find_tables()
            
            if tables:
                for tab in tables:
                    df = tab.to_pandas()
                    # 过滤掉少于2行的无效小表
                    if len(df) < 2:
                        continue
                    
                    # 替换掉 DataFrame 中的 NaN 空值，否则 JSON 转换会报错
                    df = df.fillna("")

                    table_data = df.to_dict(orient='records')
                    
                    extracted_tables.append({
                        "page": page_index + 1, # 显示为人类阅读的页码 (从1开始)
                        "data": table_data
                    })
                    
    return {
        "page_count": page_count,
        "text_preview_snippet": first_page_text[:500] + "...", 
        "tables": extracted_tables, 
        "status": "success"
    }