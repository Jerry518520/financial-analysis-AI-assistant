# 文件: src/financial_report_ai_assistant/services/document_parser.py
import fitz  # PyMuPDF
import pdfplumber
import pandas as pd
from typing import Dict, Any, List
import os
import re

def _is_real_table(df: pd.DataFrame) -> bool:
    """
    【V4.3 救赎版过滤器】
    1. 彻底移除了误杀主表的 'long_cells' 长度检查。
    2. 仅保留 '数字密度' 检查，这是最安全、最鲁棒的特征。
    3. 保留 iloc 修复，防止代码崩溃。
    """
    if len(df) < 2: return False 
    if len(df.columns) < 2: return False 

    valid_numeric_col_found = False
    
    # 遍历每一列，寻找“金额列”
    for i in range(len(df.columns)):
        try:
            # 使用 iloc 安全获取数据
            col_series = df.iloc[:, i]
            col_values = col_series.astype(str).tolist()
            
            # 统计有效内容行数（忽略空行）
            non_empty_cells = [x for x in col_values if x.strip()]
            if len(non_empty_cells) == 0: continue

            # 统计包含数字的单元格
            numeric_cells = sum(1 for x in non_empty_cells if re.search(r'\d', x))
            
            # 计算比例：在非空单元格中，有多少是数字？
            ratio = numeric_cells / len(non_empty_cells)
            
            # 阈值：只要有一列，其 30% 的内容包含数字，就认为是真表格
            # (利润表的年份列、金额列都会命中这个规则)
            if ratio > 0.3:
                valid_numeric_col_found = True
                break
        except Exception:
            continue
            
    return valid_numeric_col_found

def parse_pdf_bytes(file_content: bytes) -> Dict[str, Any]:
    """
    Hybrid Parsing V4.3 (Stable):
    专注于数据召回率 (Recall)，防止误杀核心表格。
    """
    
    temp_filename = "temp_processing.pdf"
    with open(temp_filename, "wb") as f:
        f.write(file_content)

    doc_fitz = fitz.open(temp_filename)
    pdf_plumber = pdfplumber.open(temp_filename)
    
    page_count = len(pdf_plumber.pages)
    print(f"🔄 [V4.3 最终版] 正在解析，已移除激进过滤，确保主表被收录...")

    full_text_list = []
    extracted_tables = []
    
    # 保持这套参数，它对无框主表（Main Table）效果最好
    TABLE_SETTINGS = {
        "vertical_strategy": "text", 
        "horizontal_strategy": "text",
        "snap_tolerance": 5, 
        "intersection_x_tolerance": 5,
    }

    scan_limit_start = 0
    scan_limit_end = page_count 

    for i in range(page_count):
        try:
            # --- A. 基础文本 ---
            page_fitz = doc_fitz.load_page(i)
            raw_text = page_fitz.get_text()
            page_content_buffer = [raw_text]
            
            # --- B. 表格提取 ---
            if i >= scan_limit_start and i < scan_limit_end:
                page_plumber = pdf_plumber.pages[i]
                
                tables = page_plumber.extract_tables(TABLE_SETTINGS)
                
                if tables:
                    for table_data in tables:
                        # 清洗空行
                        clean_rows = []
                        for row in table_data:
                            if not any(cell and str(cell).strip() for cell in row): continue
                            clean_rows.append([str(cell).strip() if cell else "" for cell in row])
                        
                        if not clean_rows: continue
                        
                        df = pd.DataFrame(clean_rows)
                        
                        # 表头提升
                        if len(df) > 1:
                            new_header = df.iloc[0].astype(str).str.replace("\n", " ").str.strip()
                            df.columns = new_header
                            df = df[1:]
                        
                        # [关键] 宽松的过滤器，确保不漏掉主表
                        if not _is_real_table(df):
                            continue

                        extracted_tables.append({
                            "page": i + 1,
                            "data": df.to_dict(orient='records')
                        })
                        
                        # 注入 Markdown
                        try:
                            markdown_table = df.to_markdown(index=False, tablefmt="github")
                            annotated_markdown = f"\n\n[Table Data Page {i+1}]:\n{markdown_table}\n\n"
                            page_content_buffer.append(annotated_markdown)
                        except Exception:
                            pass 
            
            full_text_list.append("".join(page_content_buffer))
            
            if (i+1) % 50 == 0:
                print(f"   ...已处理 {i+1}/{page_count} 页")

        except Exception as e:
            print(f"⚠️ 第 {i+1} 页异常: {e}")
            continue

    full_text = "\n--------------------\n".join(full_text_list)
    
    doc_fitz.close()
    pdf_plumber.close()
    if os.path.exists(temp_filename):
        try: os.remove(temp_filename)
        except: pass
    
    print(f"✅ [V4.3] 解析完成：提取了 {len(extracted_tables)} 个表格 (包含主表)。")

    return {
        "page_count": page_count,
        "text_preview_snippet": full_text[:1000],
        "full_text": full_text,
        "tables": extracted_tables, 
        "status": "success"
    }