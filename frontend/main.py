import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="洞察者 AI 财报助手", page_icon="📊", layout="wide")

with st.sidebar:
    st.header("🤖 洞察者 Insightful")
    st.markdown("---")
    st.markdown("专为非专业人士打造的\n上市公司财报分析工具")

st.title("📊 AI 财报分析助手 (表格提取版)")
st.write("---")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. 上传财报")
    uploaded_file = st.file_uploader("请上传 PDF 文件", type="pdf")
    
    if uploaded_file is not None:
        if st.button("🚀 开始深度解析", type="primary"):
            with st.spinner("AI 正在识别文档中的财务表格..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                    # 这里的 URL 还是指向你的本地后端
                    response = requests.post("http://127.0.0.1:8000/upload", files=files)
                    
                    if response.status_code == 200:
                        st.session_state.result = response.json()
                        st.success("解析完成！")
                    else:
                        st.error(f"服务器报错: {response.text}")
                except Exception as e:
                    st.error(f"无法连接后端: {e}")

with col2:
    st.subheader("2. 解析结果")
    
    if 'result' in st.session_state:
        res = st.session_state.result
        data = res.get("analysis_result", {})
        
        # 1. 展示基本信息
        st.metric("📄 总页数", data.get("page_count", 0))
        
        st.markdown("### 📋 发现的财务表格 (前5页预览)")
        
        tables = data.get("tables", [])
        
        if tables:
            for idx, table_info in enumerate(tables):
                st.markdown(f"**表格 #{idx+1} (来源: 第 {table_info['page']} 页)**")
                
                # 把字典数据转回 DataFrame 以便展示
                df_display = pd.DataFrame(table_info['data'])
                st.dataframe(df_display, use_container_width=True)
        else:
            st.warning("在前5页中没有检测到明显的表格结构。")
            
        with st.expander("查看文本预览"):
             st.info(data.get("text_preview_snippet", "无内容"))
             
    else:
        st.info("👈 请先在左侧上传文件并点击分析")