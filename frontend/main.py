# 文件: frontend/main.py
import streamlit as st
import requests
import pandas as pd
import os

# 获取 API 地址，默认是 localhost，在 Docker 中会被覆盖为 http://backend:8000
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

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
                    resp = requests.post(f"{API_URL}/upload", files=files)
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
        
        # --- 新增：智能摘要板块 ---
        st.markdown("### 🧠 智能分析报告")
        
        if "summary" not in st.session_state:
            st.session_state.summary = None
            
        if st.button("✨ 生成核心摘要"):
            with st.spinner("正在综合全篇财报生成摘要，请稍候..."):
                try:
                    # 调用后端分析接口
                    res = requests.post(f"{API_URL}/analyze/summary", json={"focus": "general"})
                    if res.status_code == 200:
                        summary_text = res.json().get("summary", "生成失败")
                        st.session_state.summary = summary_text
                    else:
                        st.error(f"生成失败: {res.status_code}")
                except Exception as e:
                    st.error(f"请求错误: {e}")

        if st.session_state.summary:
            st.markdown(st.session_state.summary)
            
        st.divider()
        st.markdown("### 💬 对话 DeepSeek")
        
        # 预设问题
        preset_questions = [
            "这份财报的营收是多少？",
            "净利润同比增长了多少？",
            "公司的毛利率是多少？",
            "请生成一份财务摘要"
        ]
        
        st.markdown("#### 💡 常见问题")
        cols = st.columns(2)
        for i, question in enumerate(preset_questions):
            col = cols[i % 2]
            with col:
                if st.button(f"📝 {question}", key=f"preset_{i}"):
                    # 点击预设问题，添加到输入框
                    st.session_state.pending_question = question
        
        # 聊天记录逻辑
        if "messages" not in st.session_state:
            st.session_state.messages = []
        
        # 处理预设问题
        if "pending_question" in st.session_state:
            prompt = st.session_state.pending_question
            del st.session_state.pending_question
            
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("DeepSeek 正在思考..."):
                    try:
                        payload = {"context": context_text, "question": prompt}
                        res = requests.post(f"{API_URL}/chat", json=payload)
                        
                        if res.status_code == 200:
                            ai_msg = res.json().get("answer", "错误")
                        else:
                            ai_msg = "服务器错误"
                            
                        st.markdown(ai_msg)
                        st.session_state.messages.append({"role": "assistant", "content": ai_msg})
                    except Exception as e:
                        st.error(f"网络错误: {e}")
        
        # 正常输入
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
                        res = requests.post(f"{API_URL}/chat", json=payload)
                        
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