import fitz  # PyMuPDF

def find_target_pages():
    # 填入你之前的页码作为搜索中心点
    center_points = [50, 56] 
    search_radius = 5  # 前后搜 5 页
    
    doc = fitz.open("example_report.pdf") # ⚠️ 请替换为你的真实文件名，如 "alibaba_report.pdf"

    print(f"Total pages: {doc.page_count}")
    
    for center in center_points:
        print(f"\n--- Searching around Page {center} ---")
        start = max(0, center - search_radius)
        end = min(doc.page_count, center + search_radius)
        
        for i in range(start, end):
            page = doc.load_page(i)
            text = page.get_text()[:100].replace("\n", " ") # 只看前100个字
            
            # 打印 物理页码(索引+1) 和 开头文字，方便你人肉比对
            print(f"[Physical Page {i+1}] (Index {i}): {text}...")

if __name__ == "__main__":
    find_target_pages()