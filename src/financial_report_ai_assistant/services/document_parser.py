# 文件: src/financial_report_ai_assistant/services/document_parser.py
import os
import hashlib
import fitz  # PyMuPDF
from llama_parse import LlamaParse
from typing import Dict, Any, List
from dotenv import load_dotenv

load_dotenv()

# ===========================
# 🎯 狙击手配置 (Sniper Config)
# ===========================
# 这里填入你“侦察”到的高价值页码 (1-based，即你看到的页码)
# 第 49 页: 预计是股权架构图 (复杂 Image)
# 第 55 页: 预计是第一张表格 (Table)
TARGET_PAGE_NUMBERS = [50, 56] 

# 缓存目录
CACHE_DIR = "cache_data"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cache_path(file_content: bytes, pages: List[int]) -> str:
    """
    生成带有页码标识的缓存文件名。
    例如: llama_parsed_abc123_pages_49_55.md
    """
    file_hash = hashlib.md5(file_content).hexdigest()
    pages_suffix = "_pages_" + "_".join(map(str, pages))
    return os.path.join(CACHE_DIR, f"llama_parsed_{file_hash}{pages_suffix}.md")

def create_sniper_pdf(file_content: bytes, target_pages: List[int]) -> str:
    """
    【狙击手切片】
    只提取指定的页码，生成一个微型 PDF。
    """
    doc = fitz.open(stream=file_content, filetype="pdf")
    total_pages = doc.page_count
    
    # 创建新文档
    new_doc = fitz.open()
    
    print(f"✂️ [狙击模式] 原文档 {total_pages} 页，正在提取目标页: {target_pages} ...")
    
    valid_pages = []
    for p in target_pages:
        # 转换为 0-based 索引
        idx = p - 1
        if 0 <= idx < total_pages:
            new_doc.insert_pdf(doc, from_page=idx, to_page=idx)
            valid_pages.append(p)
        else:
            print(f"⚠️ 警告: 目标页 {p} 超出文档范围，已跳过。")
            
    if len(valid_pages) == 0:
        return None
        
    subset_filename = f"temp_sniper_{'_'.join(map(str, valid_pages))}.pdf"
    new_doc.save(subset_filename)
    new_doc.close()
    doc.close()
    
    return subset_filename

def parse_pdf_bytes(file_content: bytes) -> Dict[str, Any]:
    print(f"🚀 [Phase 3.3] 启动 LlamaParse 狙击模式，目标页: {TARGET_PAGE_NUMBERS}")
    
    # 1. 检查缓存
    cache_path = get_cache_path(file_content, TARGET_PAGE_NUMBERS)
    
    if os.path.exists(cache_path):
        print(f"♻️ 发现本地缓存！任务已完成，直接加载: {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            full_markdown = f.read()
        return {
            "page_count": len(TARGET_PAGE_NUMBERS),
            "text_preview_snippet": full_markdown[:500],
            "full_text": full_markdown,
            "tables": [],
            "status": "success"
        }

    # 2. 制作“狙击”文件
    target_file = create_sniper_pdf(file_content, TARGET_PAGE_NUMBERS)
    
    if not target_file:
        return {"status": "error", "error": "无法生成目标切片，请检查页码配置"}

    # 3. 发射！(调用 API)
    try:
        api_key = os.getenv("LLAMA_CLOUD_API_KEY")
        if not api_key:
            return {"status": "error", "error": "Missing LLAMA_CLOUD_API_KEY"}
            
        print(f"💸 正在发送切片文件 {target_file} 到 LlamaCloud (消耗 {len(TARGET_PAGE_NUMBERS)} 点数)...")
        
        parser = LlamaParse(
            result_type="markdown", 
            premium_mode=True, 
            language="en",
            verbose=True
        )
        
        documents = parser.load_data(target_file)
        full_markdown = "\n\n".join([doc.text for doc in documents])
        
        print(f"✅ LlamaParse 狙击成功！")
        
        # 4. 写入缓存
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(full_markdown)
        print(f"💾 战果已保存至: {cache_path}")
        
        return {
            "page_count": len(TARGET_PAGE_NUMBERS),
            "text_preview_snippet": full_markdown[:500],
            "full_text": full_markdown, 
            "tables": [],
            "status": "success"
        }

    except Exception as e:
        print(f"❌ 狙击失败: {e}")
        return {"status": "error", "error": str(e)}
        
    finally:
        if target_file and os.path.exists(target_file):
            try: os.remove(target_file)
            except: pass