# 文件: frontend/main.py
import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="洞察者 AI", page_icon="🤖", layout="wide")

st.title("🤖 洞察者 (DeepSeek 版)")

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("1. 上传财报")
    uploaded_file = st.file_uploader("上传 PDF", type="pdf")
    
    if uploaded_file is not None:
        if st.button("🚀 开始解析", type="primary"):
            with st.spinner("正在提取数据..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                    resp = requests.post("http://127.0.0.1:8000/upload", files=files)
                    if resp.status_code == 200:
                        st.session_state.result = resp.json()
                        st.success("解析成功！")
                    else:
                        st.error("解析失败")
                except Exception as e:
                    st.error(f"连接错误: {e}")

with col2:
    st.subheader("2. 智能分析")
    
    if 'result' in st.session_state:
        data = st.session_state.result.get("analysis_result", {})
        
        # 拿到文本片段作为上下文
        context_text = data.get("text_preview_snippet", "")
        
        # 展示表格
        tables = data.get("tables", [])
        if tables:
            st.info(f"📊 发现 {len(tables)} 个表格")
            with st.expander("查看表格"):
                 for t in tables:
                     st.dataframe(pd.DataFrame(t['data']))
        
        st.divider()
        st.markdown("### 💬 对话 DeepSeek")
        
        # 聊天记录逻辑
        if "messages" not in st.session_state:
            st.session_state.messages = []

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("请输入问题..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("DeepSeek 正在思考..."):
                    try:
                        payload = {"context": context_text, "question": prompt}
                        res = requests.post("http://127.0.0.1:8000/chat", json=payload)
                        
                        if res.status_code == 200:
                            ai_msg = res.json().get("answer", "错误")
                        else:
                            ai_msg = "服务器错误"
                            
                        st.markdown(ai_msg)
                        st.session_state.messages.append({"role": "assistant", "content": ai_msg})
                    except Exception as e:
                        st.error(f"网络错误: {e}")
    else:
        st.info("👈 请先上传文件")