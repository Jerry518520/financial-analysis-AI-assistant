import os
import hashlib
import fitz  # PyMuPDF
import re
from llama_parse import LlamaParse
from typing import Dict, Any, List, Tuple
from dotenv import load_dotenv

load_dotenv()

CACHE_DIR = "cache_data"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# 为了防止 LlamaParse 处理过多页面导致超时或消耗过多额度，设置一个软上限
MAX_LLAMA_PAGES = 20 

def _is_suspected_table_page(page) -> bool:
    """
    使用启发式规则判断页面是否可能包含无边框表格。
    规则：
    1. 关键词匹配（财报常见表头）
    2. 数字密度检测（表格页通常包含大量数字）
    """
    text = page.get_text()
    
    # 1. 关键词列表 (中英文)
    table_keywords = [
        "Consolidated Balance Sheet", "Consolidated Income Statement", "Cash Flow",
        "合并资产负债表", "合并利润表", "合并现金流量表", "主要财务指标",
        "资产", "负债", "权益", "收入", "费用", "Assets", "Liabilities", "Equity", "Revenue"
    ]
    
    has_keyword = any(kw in text for kw in table_keywords)
    
    # 2. 数字密度检测
    # 统计数字字符在总字符中的占比，或者统计连续数字串的数量
    # 简单策略：如果页面中有超过 15 个独立的数字串（长度>1），且包含关键词，则大概率是表格
    # 匹配像 1,234.56 或 2023 这样的数字
    digit_sequences = re.findall(r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b', text)
    valid_digits = [d for d in digit_sequences if len(d) > 1]
    
    # 阈值可以调整
    if has_keyword and len(valid_digits) > 15:
        return True
        
    return False

def get_cache_path(file_content: bytes) -> str:
    # 简单的哈希缓存，避免重复解析同一文件
    file_hash = hashlib.md5(file_content).hexdigest()
    return os.path.join(CACHE_DIR, f"parsed_hybrid_{file_hash}.md")

def parse_pdf_bytes(file_content: bytes) -> Dict[str, Any]:
    print(f"🚀 [Hybrid Parser] 启动混合解析引擎...")
    
    # 1. 检查全量缓存
    cache_path = get_cache_path(file_content)
    if os.path.exists(cache_path):
        print(f"♻️ 发现本地完整缓存！直接加载...")
        with open(cache_path, "r", encoding="utf-8") as f:
            full_text = f.read()
        return {"text_preview_snippet": full_text[:500], "full_text": full_text, "status": "success"}

    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        total_pages = len(doc)
        
        table_pages_indices = []
        text_pages_content = {} # {page_index: text_content}

        print(f"🕵️ 正在扫描 {total_pages} 页文档结构...")
        
        # 2. 第一次扫描：分流 (Table Detection)
        for i, page in enumerate(doc):
            # 使用 PyMuPDF 的 find_tables() 寻找表格
            # strategy='lines' 适合财报这种有明显边框的表
            # vertical_strategy='text' 辅助无框表
            try:
                tables = page.find_tables(horizontal_strategy='lines', vertical_strategy='lines')
                
                # 如果发现表格，且表格面积看起来不是误判（例如不是页眉页脚的小框）
                has_valid_table = False
                if tables.tables:
                    # 简单判断：如果表格覆盖了一定区域
                    for tab in tables.tables:
                        if len(tab.cells) > 4: # 至少有4个格子的才算表，过滤掉奇怪的框
                            has_valid_table = True
                            break
                
                # 如果 PyMuPDF 没检测到，尝试启发式检测（针对无边框表格）
                if not has_valid_table:
                    if _is_suspected_table_page(page):
                        print(f"👀 Page {i+1} 疑似包含无边框表格（启发式检测命中），将送往 LlamaParse。")
                        has_valid_table = True

                if has_valid_table:
                    table_pages_indices.append(i)
                else:
                    # 普通页面：直接提取文本
                    text = page.get_text()
                    text_pages_content[i] = f"--- Page {i+1} ---\n{text}\n"
            except Exception as e:
                print(f"⚠️ Page {i+1} 检测出错: {e}, 降级为普通文本")
                text = page.get_text()
                text_pages_content[i] = f"--- Page {i+1} ---\n{text}\n"

        print(f"📊 扫描结果：发现 {len(table_pages_indices)} 页包含表格，将送往 LlamaParse。剩余 {len(text_pages_content)} 页本地提取。")

        # 3. 处理表格页面 (LlamaParse)
        llama_pages_content = {} # {page_index: markdown_content}
        
        if table_pages_indices:
            # 如果表格页太多，按优先级截断（防止 demo 跑太久）
            target_indices = table_pages_indices[:MAX_LLAMA_PAGES]
            if len(table_pages_indices) > MAX_LLAMA_PAGES:
                print(f"⚠️ 表格页过多 ({len(table_pages_indices)} > {MAX_LLAMA_PAGES})，仅处理前 {MAX_LLAMA_PAGES} 页表格...")
                # 对于那些被截断的表格页，我们还是要提取纯文本，不能丢弃
                for idx in table_pages_indices[MAX_LLAMA_PAGES:]:
                    page = doc[idx]
                    text = page.get_text()
                    text_pages_content[idx] = f"--- Page {idx+1} (Table Skipped) ---\n{text}\n"
            
            # 构建临时 PDF 子集
            subset_filename = f"temp_tables_{hashlib.md5(file_content).hexdigest()[:8]}.pdf"
            new_doc = fitz.open()
            for idx in target_indices:
                new_doc.insert_pdf(doc, from_page=idx, to_page=idx)
            new_doc.save(subset_filename)
            new_doc.close()
            
            # 发送给 LlamaParse
            print(f"💸 正在调用 LlamaParse 处理 {len(target_indices)} 页表格...")
            api_key = os.getenv("LLAMA_CLOUD_API_KEY")
            if not api_key: return {"status": "error", "error": "Missing LLAMA_CLOUD_API_KEY"}
            
            # 针对中文财报优化，使用 zh 语言代码
            parser = LlamaParse(result_type="markdown", premium_mode=True, language="zh")
            documents = parser.load_data(subset_filename)
            
            # 映射回原始页码
            # LlamaParse 返回的 documents 列表顺序对应我们 subset pdf 的页顺序
            for idx, result_doc in enumerate(documents):
                if idx < len(target_indices):
                    original_page_idx = target_indices[idx]
                    llama_pages_content[original_page_idx] = f"--- Page {original_page_idx+1} (Table Enhanced) ---\n{result_doc.text}\n"
            
            # 清理临时文件
            if os.path.exists(subset_filename):
                try:
                    os.remove(subset_filename)
                except:
                    pass

        doc.close()

        # 4. 合并所有内容 (按页码顺序)
        final_full_text = []
        for i in range(total_pages):
            if i in llama_pages_content:
                final_full_text.append(llama_pages_content[i])
            elif i in text_pages_content:
                final_full_text.append(text_pages_content[i])
        
        full_text_str = "\n".join(final_full_text)
        
        # 5. 写入缓存
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(full_text_str)

        return {
            "text_preview_snippet": full_text_str[:500], 
            "full_text": full_text_str, 
            "status": "success"
        }

    except Exception as e:
        print(f"❌ 解析失败: {e}")
        return {"status": "error", "error": str(e)}
