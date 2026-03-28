# 文件: frontend/main.py
import streamlit as st
import requests
import pandas as pd
import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

def get_recommended_questions(user_question):
    """根据用户问题推荐相关问题"""
    question_lower = user_question.lower()
    
    recommendations = {
        # 基础数据
        "营收": ["净利润是多少？", "毛利率是多少？", "营收同比增长多少？"],
        "收入": ["净利润是多少？", "毛利率是多少？", "营收同比增长多少？"],
        "净利润": ["毛利率是多少？", "ROE是多少？", "净利润同比增长多少？"],
        "资产": ["负债是多少？", "资产负债率是多少？", "现金流是多少？"],
        # 盈利能力
        "利润": ["毛利率是多少？", "ROE是多少？", "净利率是多少？"],
        "毛利率": ["净利率是多少？", "ROE是多少？", "公司的盈利能力强吗？"],
        "净利率": ["毛利率是多少？", "ROE是多少？", "EPS是多少？"],
        "ROE": ["净利率是多少？", "EPS是多少？", "公司的盈利能力强吗？"],
        "EPS": ["PE是多少？", "ROE是多少？", "每股收益增长了多少？"],
        "PE": ["EPS是多少？", "股价是多少？", "估值合理吗？"],
        # 偿债能力
        "负债": ["资产负债率是多少？", "公司的偿债能力如何？", "流动比率是多少？"],
        "资产负债率": ["流动比率是多少？", "速动比率是多少？", "公司的偿债能力如何？"],
        "流动比率": ["速动比率是多少？", "资产负债率是多少？", "偿债能力如何？"],
        "速动比率": ["流动比率是多少？", "资产负债率是多少？", "偿债能力如何？"],
        # 运营能力
        "周转": ["资产周转率是多少？", "存货周转率是多少？", "运营效率如何？"],
        "存货": ["存货周转率是多少？", "资产周转率是多少？", "库存管理如何？"],
        # 成长能力
        "增长": ["净利润同比增长多少？", "营收同比增长多少？", "公司的发展能力如何？"],
        "同比": ["净利润同比增长多少？", "营收同比增长多少？", "分析一下公司的成长趋势"],
        "趋势": ["分析一下公司的成长趋势", "营收同比增长了多少？", "未来发展前景如何？"],
        # 综合分析
        "风险": ["经营风险有哪些？", "财务风险有哪些？", "公司面临哪些主要风险？"],
        "摘要": ["公司的盈利能力强吗？", "公司面临哪些主要风险？", "未来发展前景如何？"],
        "行业": ["与行业平均水平对比如何？", "公司在行业中地位如何？", "竞争优势是什么？"],
        "对比": ["与行业平均水平对比如何？", "公司在行业中地位如何？"],
    }
    
    for key, questions in recommendations.items():
        if key in question_lower:
            return questions
    
    return ["公司的盈利能力强吗？", "毛利率是多少？", "净利润同比增长多少？"]


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
        
        # 预设问题（按分类）
        preset_questions = {
            "📊 基础数据": [
                "这份财报的营收是多少？",
                "净利润是多少？",
                "公司总资产是多少？",
            ],
            "📈 盈利能力": [
                "公司的毛利率是多少？",
                "净利率是多少？",
                "净资产收益率(ROE)是多少？",
                "每股收益(EPS)是多少？",
            ],
            "📉 成长能力": [
                "净利润同比增长了多少？",
                "营收同比增长了多少？",
                "分析一下公司的成长趋势",
            ],
            "🏦 偿债能力": [
                "资产负债率是多少？",
                "流动比率是多少？",
                "速动比率是多少？",
            ],
            "🔄 运营能力": [
                "资产周转率是多少？",
                "存货周转率是多少？",
            ],
            "🔍 综合分析": [
                "请生成一份财务摘要",
                "公司的盈利能力强吗？",
                "公司面临哪些主要风险？",
                "与行业平均水平对比如何？",
            ]
        }
        
        for category, questions in preset_questions.items():
            st.markdown(f"**{category}**")
            category_key = category.split()[1] if len(category.split()) > 1 else category
            for i, question in enumerate(questions):
                col = st.columns(2)[i % 2]
                with col:
                    if st.button(f"📝 {question}", key=f"preset_{category_key}_{i}"):
                        st.session_state.pending_question = question
            st.markdown("")
        
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
                            source_page = res.json().get("source_page", 1)
                            st.session_state.last_source_page = source_page
                            recommended_questions = get_recommended_questions(prompt)
                            if recommended_questions:
                                st.session_state.last_recommended = recommended_questions
                        else:
                            ai_msg = "服务器错误"

                        st.markdown(ai_msg)
                        st.session_state.messages.append({"role": "assistant", "content": ai_msg})

                        if st.session_state.get("last_source_page"):
                            page = st.session_state.last_source_page
                            st.image(f"{API_URL}/highlight?page={page}&x=0&y=0&w=600&h=800", caption=f"📄 来源：第 {page} 页")
                        
                        # 显示推荐问题
                        if "last_recommended" in st.session_state:
                            st.markdown("**💡 你可能还想问：**")
                            for i, q in enumerate(st.session_state.last_recommended):
                                col = st.columns(2)[i % 2]
                                with col:
                                    if st.button(f"📝 {q}", key=f"recommended_{i}"):
                                        st.session_state.pending_question = q
                            del st.session_state.last_recommended
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
                            source_page = res.json().get("source_page", 1)
                            st.session_state.last_source_page = source_page
                            recommended_questions = get_recommended_questions(prompt)
                            if recommended_questions:
                                st.session_state.last_recommended = recommended_questions
                        else:
                            ai_msg = "服务器错误"

                        st.markdown(ai_msg)
                        st.session_state.messages.append({"role": "assistant", "content": ai_msg})

                        if st.session_state.get("last_source_page"):
                            page = st.session_state.last_source_page
                            st.image(f"{API_URL}/highlight?page={page}&x=0&y=0&w=600&h=800", caption=f"📄 来源：第 {page} 页")

                        if "last_recommended" in st.session_state:
                            st.markdown("**💡 你可能还想问：**")
                            for i, q in enumerate(st.session_state.last_recommended):
                                col = st.columns(2)[i % 2]
                                with col:
                                    if st.button(f"📝 {q}", key=f"chat_recommended_{i}"):
                                        st.session_state.pending_question = q
                            del st.session_state.last_recommended
                    except Exception as e:
                        st.error(f"网络错误: {e}")
    else:
        st.info("👈 请先上传文件")