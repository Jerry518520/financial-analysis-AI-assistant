# 文件: frontend/main.py
import streamlit as st
import requests
import pandas as pd
import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# ============================================================
# 深邃金融主题 CSS — 暗色系 + 翡翠绿accent + 金色点缀
# ============================================================
st.markdown("""
<style>
/* ===== 全局基础 ===== */
[data-testid="stAppViewContainer"] {
    background: #0f1117;
    color: #e2e8f0;
}

/* 隐藏 Streamlit 默认顶部栏和底部 */
[data-testid="stToolbar"],
[data-testid="stDecoration"],
footer { display: none !important; }

/* ===== 标题 ===== */
h1 {
    background: linear-gradient(135deg, #00d4aa 0%, #00b894 50%, #f0b429 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-size: 2.4rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px;
    margin-bottom: 0.3rem !important;
}

/* ===== 副标题 ===== */
h2, h3 {
    color: #00d4aa !important;
    font-weight: 700 !important;
    border-bottom: 1px solid rgba(0, 212, 170, 0.15);
    padding-bottom: 0.5rem;
}

/* ===== 正文文字 ===== */
p, span, div, li, td, th {
    color: #cbd5e1 !important;
}

/* ===== Streamlit 原生组件样式覆盖 ===== */

/* 输入框 / 文件上传 */
[data-testid="stFileUploader"] {
    background: #1a1d29;
    border: 2px dashed rgba(0, 212, 170, 0.3);
    border-radius: 12px;
    padding: 1.5rem;
    transition: border-color 0.3s, box-shadow 0.3s;
}
[data-testid="stFileUploader"]:hover {
    border-color: rgba(0, 212, 170, 0.6);
    box-shadow: 0 0 20px rgba(0, 212, 170, 0.1);
}
[data-testid="stFileUploader"] section {
    background: transparent !important;
    border: none !important;
}
[data-testid="stFileUploader"] label {
    color: #00d4aa !important;
}
[data-testid="stFileUploader"] p {
    color: #64748b !important;
    font-size: 0.9rem;
}

/* 主按钮（开始解析） */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #00d4aa, #00b894) !important;
    color: #0f1117 !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.6rem 1.5rem !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
    box-shadow: 0 4px 15px rgba(0, 212, 170, 0.3) !important;
}
.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 25px rgba(0, 212, 170, 0.4) !important;
}

/* 次级按钮（预设问题/推荐问题/生成摘要） */
.stButton > button:not([kind="primary"]) {
    background: #1e2233 !important;
    color: #a5b4fc !important;
    border: 1px solid rgba(165, 180, 252, 0.15) !important;
    border-radius: 8px !important;
    font-size: 0.85rem !important;
    padding: 0.4rem 0.8rem !important;
    transition: all 0.2s !important;
}
.stButton > button:not([kind="primary"]):hover {
    background: #262b40 !important;
    border-color: #00d4aa !important;
    color: #00d4aa !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
}

/* 聊天输入框 */
[data-testid="stChatInput"] {
    background: #1a1d29 !important;
    border: 1px solid rgba(0, 212, 170, 0.2) !important;
    border-radius: 12px !important;
}
[data-testid="stChatInput"] textarea {
    background: transparent !important;
    color: #e2e8f0 !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #475569 !important;
}

/* ===== 聊天气泡 ===== */
[data-testid="stChatMessage"] {
    border-radius: 12px;
}
[data-testid="stChatMessage"][data-testid*="assistant"] {
    background: #1a1d29 !important;
}
[data-testid="stChatMessage"][data-testid*="user"] {
    background: #162032 !important;
}

/* ===== 信息/成功/错误框 ===== */
[data-testid="stAlert"] {
    border-radius: 8px !important;
}
[data-testid="stSuccess"] {
    background: rgba(0, 212, 170, 0.1) !important;
    border-left: 4px solid #00d4aa !important;
}
[data-testid="stInfo"] {
    background: rgba(74, 144, 217, 0.1) !important;
    border-left: 4px solid #4a90d9 !important;
}
[data-testid="stError"] {
    background: rgba(239, 68, 68, 0.1) !important;
    border-left: 4px solid #ef4444 !important;
}
[data-testid="stWarning"] {
    background: rgba(240, 180, 41, 0.1) !important;
    border-left: 4px solid #f0b429 !important;
}

/* ===== Expander 折叠面板 ===== */
.streamlit-expanderHeader {
    background: #1a1d29 !important;
    color: #00d4aa !important;
    border-radius: 8px !important;
    border: 1px solid rgba(0, 212, 170, 0.1) !important;
}
[data-testid="stExpander"] details {
    background: #141620 !important;
    border-radius: 8px !important;
}

/* ===== 数据表格 ===== */
[data-testid="stDataFrame"] {
    background: #1a1d29 !important;
    border-radius: 8px !important;
    border: 1px solid rgba(255,255,255,0.05) !important;
}
[data-testid="stDataFrame"] table {
    color: #cbd5e1 !important;
}
[data-testid="stDataFrame"] th {
    background: #141620 !important;
    color: #00d4aa !important;
    font-weight: 600 !important;
    border-bottom: 1px solid rgba(0, 212, 170, 0.2) !important;
}
[data-testid="stDataFrame"] td {
    border-bottom: 1px solid rgba(255,255,255,0.03) !important;
}
[data-testid="stDataFrame"] tr:hover td {
    background: rgba(0, 212, 170, 0.05) !important;
}

/* ===== Divider ===== */
hr, [data-testid="stDivider"] {
    border-color: rgba(0, 212, 170, 0.1) !important;
    margin: 1.5rem 0 !important;
}

/* ===== Spinner ===== */
[aria-busy="true"] {
    color: #00d4aa !important;
}

/* ===== 列间距优化 ===== */
[data-testid="stHorizontalBlock"] {
    gap: 2rem;
}

/* ===== 滚动条美化 ===== */
::-webkit-scrollbar {
    width: 6px;
}
::-webkit-scrollbar-track {
    background: #0f1117;
}
::-webkit-scrollbar-thumb {
    background: #2a2d3a;
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: #3a3d4a;
}

/* ===== 自定义工具类 ===== */
.metric-card {
    background: #1a1d29;
    border: 1px solid rgba(0, 212, 170, 0.1);
    border-radius: 12px;
    padding: 1.2rem;
    margin-bottom: 0.8rem;
    transition: border-color 0.3s, box-shadow 0.3s;
}
.metric-card:hover {
    border-color: rgba(0, 212, 170, 0.3);
    box-shadow: 0 0 20px rgba(0, 212, 170, 0.05);
}

.gold-accent {
    color: #f0b429 !important;
}

.dim-text {
    color: #475569 !important;
    font-size: 0.85rem;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# 业务逻辑函数（不变）
# ============================================================

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


def call_chat_api(prompt):
    """统一的聊天 API 调用逻辑"""
    payload = {"question": prompt}
    res = requests.post(f"{API_URL}/chat", json=payload)

    if res.status_code == 200:
        data = res.json()
        ai_msg = data.get("answer", "错误")
        source_pages = data.get("source_pages", [data.get("source_page", None)])
        # 确保列表中的 None 被过滤掉
        source_pages = [p for p in source_pages if p is not None]
        recommended = get_recommended_questions(prompt)
        return ai_msg, source_pages, recommended
    else:
        try:
            error_detail = res.json().get("error", "未知错误")
        except Exception:
            error_detail = f"HTTP {res.status_code}"
        return f"❌ 服务器错误：{error_detail}", [], None


def _render_source_images(source_pages, btn_key):
    """渲染溯源按钮，点击后展开来源页图片（支持多页）"""
    if not source_pages:
        return

    if len(source_pages) == 1:
        label = f"📄 查看来源（第 {source_pages[0]} 页）"
    else:
        pages_str = "、".join(str(p) for p in source_pages)
        label = f"📄 查看来源（第 {pages_str} 页）"

    if st.button(label, key=btn_key):
        # 点击时用 rerun 展开
        st.session_state["_expanded_source"] = btn_key

    # 仅当用户点击了当前按钮时展开图片
    if st.session_state.get("_expanded_source") == btn_key:
        for page in source_pages:
            try:
                st.image(
                    f"{API_URL}/highlight?page={page}&x=0&y=0&w=600&h=800",
                    caption=f"📄 来源：第 {page} 页"
                )
            except Exception:
                st.caption(f"⚠️ 第 {page} 页溯源图片加载失败")


def _render_recommended(rec_list, msg_idx):
    """渲染推荐问题按钮"""
    if not rec_list:
        return
    st.markdown("**💡 你可能还想问：**")
    rec_cols = st.columns(3)
    for i, q in enumerate(rec_list):
        with rec_cols[i]:
            if st.button(f"→ {q}", key=f"rec_{msg_idx}_{i}", use_container_width=True):
                st.session_state.pending_question = q
                st.rerun()


def _process_chat(prompt):
    """处理一次对话：发送问题 → 渲染回答 → 追加历史消息 → 渲染溯源和推荐"""
    # 递增溯源按钮计数器，确保 key 唯一
    st.session_state["_source_btn_counter"] = st.session_state.get("_source_btn_counter", 0) + 1
    btn_key = f"source_new_{st.session_state['_source_btn_counter']}"

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("DeepSeek 正在思考..."):
            ai_msg, source_pages, recommended = call_chat_api(prompt)
            st.markdown(ai_msg)
            msg_idx = len(st.session_state.messages)
            st.session_state.messages.append({
                "role": "assistant",
                "content": ai_msg,
                "source_pages": source_pages,
                "recommended": recommended,
                "source_btn_key": btn_key,
            })

            _render_source_images(source_pages, btn_key)
            _render_recommended(recommended, msg_idx)


# ============================================================
# 页面布局
# ============================================================

st.set_page_config(page_title="洞察者 AI", page_icon="📊", layout="wide")

# 顶部标题区
st.markdown("""
<div style="margin-bottom: 1.5rem;">
    <h1 style="margin-bottom: 0.2rem;">洞察者 AI</h1>
    <p style="color: #475569; font-size: 0.95rem; margin: 0;">
        基于 RAG + Agent 的智能财报分析助手 &nbsp;·&nbsp; DeepSeek 驱动
    </p>
</div>
""", unsafe_allow_html=True)

# 如果还没有上传结果，显示引导页面
if 'result' not in st.session_state:

    st.markdown("""
    <div style="
        text-align: center;
        padding: 4rem 2rem;
        margin: 2rem auto;
        max-width: 600px;
        background: linear-gradient(135deg, #1a1d29 0%, #141620 100%);
        border: 1px solid rgba(0, 212, 170, 0.1);
        border-radius: 16px;
    ">
        <div style="font-size: 4rem; margin-bottom: 1rem;">📊</div>
        <h2 style="color: #00d4aa; margin-bottom: 0.5rem;">上传你的第一份财报</h2>
        <p style="color: #64748b; font-size: 0.95rem; line-height: 1.8;">
            支持 PDF 格式的上市公司年度/季度财报<br>
            AI 将自动解析财务数据，支持自由对话问答
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("**📤 上传财报**")
        uploaded_file = st.file_uploader("选择 PDF 文件", type="pdf", label_visibility="collapsed")

        if uploaded_file is not None:
            if st.button("🚀 开始解析", type="primary", use_container_width=True):
                with st.spinner("正在提取数据..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                        resp = requests.post(f"{API_URL}/upload", files=files)
                        if resp.status_code == 200:
                            st.session_state.result = resp.json()
                            st.session_state.messages = []
                            st.session_state.summary = None
                            if "pending_question" in st.session_state:
                                del st.session_state.pending_question
                            st.success(f"✅ 解析成功！已上传：{uploaded_file.name}")
                            st.rerun()
                        else:
                            try:
                                err = resp.json().get("error", "未知错误")
                            except Exception:
                                err = f"HTTP {resp.status_code}"
                            st.error(f"解析失败：{err}")
                    except Exception as e:
                        st.error(f"连接错误: {e}")

    with col2:
        st.markdown("""
        <div style="padding: 2rem; background: #1a1d29; border-radius: 12px; border: 1px solid rgba(0,212,170,0.08);">
            <h3 style="color: #f0b429; margin-top: 0;">💡 功能特性</h3>
            <ul style="line-height: 2.2; color: #94a3b8;">
                <li>🧠 <strong style="color: #e2e8f0;">AI 智能摘要</strong> — 一键生成财报核心要点</li>
                <li>💬 <strong style="color: #e2e8f0;">自由对话</strong> — 基于财报内容的深度问答</li>
                <li>📊 <strong style="color: #e2e8f0;">财务计算</strong> — 19 种专业分析工具自动调用</li>
                <li>📄 <strong style="color: #e2e8f0;">精准溯源</strong> — 回答定位到原文页码</li>
                <li>🔄 <strong style="color: #e2e8f0;">多份财报</strong> — 支持切换不同财报分析</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

else:
    # ===== 已上传状态：主界面 =====

    # 获取当前文件名
    current_filename = st.session_state.result.get("filename", "未知文件")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown(f"**📤 上传财报**")
        st.caption(f"当前：`{current_filename}`")
        uploaded_file = st.file_uploader("替换 PDF 文件", type="pdf", label_visibility="collapsed")

        if uploaded_file is not None:
            if st.button("🚀 重新解析", type="primary", use_container_width=True):
                with st.spinner("正在提取数据..."):
                    try:
                        files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
                        resp = requests.post(f"{API_URL}/upload", files=files)
                        if resp.status_code == 200:
                            st.session_state.result = resp.json()
                            st.session_state.messages = []
                            st.session_state.summary = None
                            if "pending_question" in st.session_state:
                                del st.session_state.pending_question
                            st.success(f"✅ 解析成功！已上传：{uploaded_file.name}")
                            st.rerun()
                        else:
                            try:
                                err = resp.json().get("error", "未知错误")
                            except Exception:
                                err = f"HTTP {resp.status_code}"
                            st.error(f"解析失败：{err}")
                    except Exception as e:
                        st.error(f"连接错误: {e}")

    with col2:
        data = st.session_state.result.get("analysis_result", {})

        # 展示表格
        tables = data.get("tables", [])
        if tables:
            st.info(f"📊 发现 {len(tables)} 个表格")
            with st.expander("查看表格"):
                 for t in tables:
                     rows = t.get('data', [])
                     if not rows:
                         st.caption("（此表格内容为空）")
                     else:
                         st.dataframe(pd.DataFrame(rows))

        st.divider()

        # --- 智能摘要板块 ---
        st.markdown("### 🧠 智能分析报告")

        if "summary" not in st.session_state:
            st.session_state.summary = None

        if st.button("✨ 生成核心摘要", use_container_width=True):
            with st.spinner("正在综合全篇财报生成摘要，请稍候..."):
                try:
                    res = requests.post(f"{API_URL}/analyze/summary", json={"focus": "general"})
                    if res.status_code == 200:
                        st.session_state.summary = res.json().get("summary", "生成失败")
                    else:
                        st.error(f"生成失败: {res.status_code}")
                except Exception as e:
                    st.error(f"请求错误: {e}")

        if st.session_state.summary:
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #1a1d29 0%, #162032 100%);
                border: 1px solid rgba(0, 212, 170, 0.15);
                border-left: 4px solid #00d4aa;
                border-radius: 8px;
                padding: 1.2rem 1.5rem;
                line-height: 1.8;
                color: #cbd5e1;
            ">
                {st.session_state.summary}
            </div>
            """, unsafe_allow_html=True)

        st.divider()
        st.markdown("### 💬 对话 DeepSeek")

        # 初始化 session state
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # ========== 预设问题 ==========
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
            cols = st.columns(len(questions))
            for i, question in enumerate(questions):
                with cols[i]:
                    if st.button(f"→ {question}", key=f"preset_{category}_{i}", use_container_width=True):
                        st.session_state.pending_question = question
                        st.rerun()

        # ========== 渲染历史消息 ==========
        is_processing = "pending_question" in st.session_state
        for idx, msg in enumerate(st.session_state.messages):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant":
                    # 回答进行中时，隐藏所有历史消息的推荐按钮（避免重复显示）
                    if not is_processing:
                        btn_key = msg.get("source_btn_key", f"source_hist_{idx}")
                        _render_source_images(msg.get("source_pages", []), btn_key)
                        _render_recommended(msg.get("recommended"), idx)
                    else:
                        btn_key = msg.get("source_btn_key", f"source_hist_{idx}")
                        _render_source_images(msg.get("source_pages", []), btn_key)

        # ========== 处理 pending_question ==========
        if "pending_question" in st.session_state:
            prompt = st.session_state.pending_question
            del st.session_state.pending_question
            _process_chat(prompt)

        # ========== 正常输入 ==========
        if prompt := st.chat_input("请输入问题..."):
            _process_chat(prompt)
