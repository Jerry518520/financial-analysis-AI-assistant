# 文件: frontend/main.py
import streamlit as st
import streamlit.components.v1 as components
import requests
import os
import re
import threading
import time
import plotly.graph_objects as go
import markdown as _md_lib

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

/* ===== 聊天气泡内文字强制可见 ===== */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] span,
[data-testid="stChatMessage"] li,
[data-testid="stChatMessage"] div,
[data-testid="stChatMessage"] td,
[data-testid="stChatMessage"] th,
[data-testid="stChatMessage"] strong,
[data-testid="stChatMessage"] code,
[data-testid="stChatMessage"] pre {
    color: #e2e8f0 !important;
}

/* ===== Markdown 列表样式强制覆盖 ===== */
[data-testid="stChatMessage"] ul,
[data-testid="stChatMessage"] ol,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] ul,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] ol {
    background: transparent !important;
    color: #e2e8f0 !important;
    border: none !important;
    padding-left: 1.5rem !important;
    margin: 0.5rem 0 !important;
    list-style-position: outside !important;
}

[data-testid="stChatMessage"] ul li,
[data-testid="stChatMessage"] ol li,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] ul li,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] ol li {
    background: transparent !important;
    color: #e2e8f0 !important;
    padding: 0.25rem 0 !important;
    margin: 0.2rem 0 !important;
    display: list-item !important;
}

[data-testid="stChatMessage"] ul li::marker,
[data-testid="stChatMessage"] ol li::marker,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] ul li::marker,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] ol li::marker {
    color: #00d4aa !important;
}

/* ===== Streamlit 原生组件样式覆盖 ===== */

/* Selectbox 下拉菜单 */
[data-testid="stSelectbox"] {
    background: #1a1d29 !important;
    border-radius: 8px !important;
}
[data-testid="stSelectbox"] > div {
    background: #1a1d29 !important;
}
[data-testid="stSelectbox"] > div > div {
    background: #1a1d29 !important;
    border: 1px solid rgba(0, 212, 170, 0.2) !important;
    border-radius: 8px !important;
    color: #e2e8f0 !important;
}
[data-testid="stSelectbox"] label {
    color: #00d4aa !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] {
    background: #1a1d29 !important;
}
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: #1a1d29 !important;
    color: #e2e8f0 !important;
}
[data-testid="stSelectbox"] [data-baseweb="popover"] {
    background: #1a1d29 !important;
}
[data-testid="stSelectbox"] [data-baseweb="popover"] [data-baseweb="menu"] {
    background: #1a1d29 !important;
}
[data-testid="stSelectbox"] [role="option"] {
    background: #1a1d29 !important;
    color: #e2e8f0 !important;
}
[data-testid="stSelectbox"] [role="option"]:hover {
    background: #262b40 !important;
    color: #00d4aa !important;
}

/* BaseWeb 下拉菜单（portal 渲染，需全局覆盖） */
[data-baseweb="popover"],
[data-baseweb="menu"],
[data-baseweb="select"] ul,
div[data-baseweb="popover"] div[role="listbox"],
div[data-baseweb="popover"] div[role="option"],
div[data-baseweb="popover"] li,
div[data-baseweb="popover"] ul {
    background: #1a1d29 !important;
    background-color: #1a1d29 !important;
    color: #e2e8f0 !important;
    border: 1px solid rgba(0, 212, 170, 0.2) !important;
}
div[data-baseweb="popover"] div[role="option"]:hover,
div[data-baseweb="popover"] li:hover,
div[data-baseweb="popover"] ul li:hover {
    background: #262b40 !important;
    background-color: #262b40 !important;
    color: #00d4aa !important;
}
div[data-baseweb="popover"] div[role="option"][aria-selected="true"] {
    background: #262b40 !important;
    background-color: #262b40 !important;
    color: #00d4aa !important;
}

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

/* 聊天输入框 — 多层选择器确保覆盖 Streamlit 内联样式 */
[data-testid="stChatInput"],
[data-testid="stChatInput"] div,
[data-testid="stChatInput"] section,
[data-testid="stChatInput"] fieldset {
    background: #1a1d29 !important;
    border: 1px solid rgba(0, 212, 170, 0.2) !important;
    border-radius: 12px !important;
}
[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] input,
[data-testid="stChatInput"] [class*="textInput"],
[data-testid="stChatInput"] [class*="stTextArea"],
[data-testid="stChatInput"] [class*="stTextInput"] {
    background: transparent !important;
    color: #e2e8f0 !important;
    caret-color: #00d4aa !important;
    -webkit-text-fill-color: #e2e8f0 !important;
}
[data-testid="stChatInput"] textarea::placeholder,
[data-testid="stChatInput"] input::placeholder {
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
    border: 1px solid rgba(0, 212, 170, 0.1) !important;
}
[data-testid="stExpander"] details summary {
    background: #1a1d29 !important;
    color: #00d4aa !important;
}
[data-testid="stExpander"] details[open] summary {
    background: #1a1d29 !important;
}
[data-testid="stExpander"] details > div {
    background: #141620 !important;
}
[data-testid="stExpander"] details > div > div {
    background: #141620 !important;
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
}

/* ===== 侧边栏 ===== */
[data-testid="stSidebar"] {
    background: #0a0d14 !important;
    border-right: 1px solid rgba(0, 212, 170, 0.1) !important;
}
[data-testid="stSidebar"] .stMarkdown h1,
[data-testid="stSidebar"] .stMarkdown h2,
[data-testid="stSidebar"] .stMarkdown h3 {
    color: #00d4aa !important;
}
[data-testid="stSidebar"] .stMarkdown p {
    color: #94a3b8 !important;
}

/* ===== 进度条 ===== */
[data-testid="stProgressBar"] > div {
    background: #1a1d29 !important;
}
[data-testid="stProgressBar"] > div > div {
    background: linear-gradient(90deg, #00d4aa, #00b894) !important;
}

/* ===== Markdown 表格 ===== */
.stMarkdown table,
.stMarkdown th,
.stMarkdown td {
    background: #1a1d29 !important;
    color: #cbd5e1 !important;
    border-color: rgba(255,255,255,0.08) !important;
}
.stMarkdown th {
    background: #141620 !important;
    color: #00d4aa !important;
    font-weight: 600 !important;
}
.stMarkdown tr:hover td {
    background: #1e2235 !important;
}

/* ===== 分隔线 ===== */
hr {
    border-color: rgba(0, 212, 170, 0.15) !important;
}

/* ===== Tabs ===== */
.stTabs [data-baseweb="tab-list"] {
    background: #0f1117 !important;
    border-radius: 8px !important;
}
.stTabs [data-baseweb="tab"] {
    color: #8892a4 !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    color: #00d4aa !important;
    background: #1a1d29 !important;
    border-bottom-color: #00d4aa !important;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 辅助函数：提取来源页码
# ============================================================
def _extract_source_pages(msg):
    """从 assistant 消息中提取所有来源页码"""
    return sorted(set(re.findall(r'第(\d+)页', msg.get("content", ""))))


# ============================================================
# 渲染消息内容（Markdown → HTML）
# ============================================================
def _render_message_content(msg):
    """将 Markdown 消息内容渲染为带格式的 HTML"""
    content = msg.get("content", "")

    if msg.get("role") == "assistant":
        # 提取参考来源（如果有）
        source_pages = msg.get("source_pages", [])
        source_html = ""
        if source_pages:
            pages_str = ", ".join([f"第{p}页" for p in source_pages])
            source_html = f"""
            <div style="
                margin-top: 0.6rem;
                padding-top: 0.6rem;
                border-top: 1px solid rgba(0, 212, 170, 0.1);
                font-size: 0.78rem;
                color: #64748b;
            ">
                📎 参考来源: {pages_str}
            </div>
            """

        # Markdown 转 HTML（修复表格和列表渲染）
        html_content = _md_lib.markdown(content, extensions=['tables', 'fenced_code'])
        return f"""
        <div style="
            line-height: 1.85;
            color: #e2e8f0;
        ">
            {html_content}
            {source_html}
        </div>
        """
    else:
        return content


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


def _render_radar_chart(radar_data: dict):
    """渲染能力雷达图（SASAC 企业绩效评价框架）"""
    dims = radar_data.get("dimensions", [])
    if not dims:
        return

    composite = radar_data.get("composite_score", 0)
    composite_grade = radar_data.get("composite_grade", "?")
    composite_label = radar_data.get("composite_label", "")
    industry = radar_data.get("industry", "")
    z_score = radar_data.get("z_score")

    GRADE_COLORS = {
        "A": "#ffd700", "B": "#00d4aa", "C": "#4fc3f7",
        "D": "#ffb74d", "E": "#ef5350",
    }

    # ---- 1. Plotly 雷达图（带权重标注） ----
    categories = [f'{d["name"]}<br>({int(d.get("weight", 0)*100)}%)' for d in dims]
    values = [d["score"] for d in dims]
    categories_closed = categories + [categories[0]]
    values_closed = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(0, 212, 170, 0.2)',
        line=dict(color='#00d4aa', width=2),
        hovertemplate='%{theta}: %{r:.1f}/100<extra></extra>',
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, range=[0, 100],
                tickfont=dict(size=10, color='#8892a4'),
                gridcolor='rgba(255,255,255,0.08)',
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color='#e2e8f0'),
                gridcolor='rgba(255,255,255,0.08)',
            ),
            bgcolor='rgba(0,0,0,0)',
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False,
        margin=dict(l=60, r=60, t=30, b=30),
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ---- 2. 综合评分 + Z-Score ----
    comp_color = GRADE_COLORS.get(composite_grade, "#8892a4")
    z_html = ""
    if z_score:
        z_val = z_score["z_score"]
        z_zone = z_score["zone"]
        z_colors = {"安全": "#00d4aa", "灰色": "#ffb74d", "危险": "#ef5350"}
        z_color = z_colors.get(z_zone, "#8892a4")
        z_html = (
            f'<div style="text-align:center; margin-top:0.8rem; padding-top:0.8rem; '
            f'border-top:1px solid rgba(255,255,255,0.06);">'
            f'<span style="font-size:11px; color:#8892a4; letter-spacing:1px;">ALTMAN Z-SCORE</span><br>'
            f'<span style="font-size:28px; font-weight:900; color:{z_color};">{z_val:.2f}</span>'
            f'<span style="font-size:13px; color:{z_color}; margin-left:8px;">{z_zone}</span>'
            f'</div>'
        )

    st.markdown(
        f'<div style="text-align:center; margin-bottom:1rem;">'
        f'<span style="font-size:13px; color:#8892a4; letter-spacing:2px;">COMPOSITE SCORE</span><br>'
        f'<span style="font-size:36px; font-weight:900; color:{comp_color};">'
        f'{composite:.0f}<span style="font-size:16px; color:#8892a4;">/100</span></span>'
        f'<span style="display:inline-block; width:44px; height:44px; border:2px solid {comp_color}; '
        f'border-radius:8px; text-align:center; line-height:44px; font-size:24px; font-weight:900; '
        f'color:{comp_color}; margin-left:12px; vertical-align:middle;">{composite_grade}</span>'
        f'<br><span style="font-size:13px; color:{comp_color};">{composite_label}</span>'
        f'<span style="font-size:12px; color:#8892a4; margin-left:8px;">{industry}</span>'
        f'{z_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ---- 3. 维度卡片 ----
    def _fmt_val(val, name):
        if val is None:
            return "-"
        pct = {"毛利率", "净利率", "ROE", "资产负债率", "营收增长率", "净利润增长率",
               "营业利润率", "成本费用利润率", "现金回收率", "现金流动负债比",
               "总资产增长率", "资本保值增值率", "营运资本比", "留存收益比", "EBIT资产比"}
        return f"{val*100:.1f}%" if name in pct else f"{val:.2f}"

    for i in range(0, len(dims), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            if i + j >= len(dims):
                break
            d = dims[i + j]
            score = d["score"]
            grade = d.get("grade", "?")
            label = d.get("label", "")
            weight = d.get("weight", 0)
            color = GRADE_COLORS.get(grade, "#8892a4")
            detail = d.get("detail", [])

            bench_lines = []
            for item in detail:
                if item.get("benchmark") is not None and len(bench_lines) < 2:
                    cv = _fmt_val(item.get("company"), item["name"])
                    bv = _fmt_val(item["benchmark"], item["name"])
                    bench_lines.append(f'{item["name"]}: {cv} vs {bv}')
            bench_text = " | ".join(bench_lines) if bench_lines else ""

            with col:
                bench_html = f'<div style="font-size:11px; color:#8892a4; margin-top:6px;">{bench_text}</div>' if bench_text else ''
                st.markdown(
                    f'<div style="border:1px solid rgba(255,255,255,0.08); border-radius:10px; '
                    f'padding:0.8rem 1rem; margin-bottom:0.5rem;">'
                    f'<div style="display:flex; align-items:center; gap:0.8rem;">'
                    f'<div style="width:44px; height:44px; border:2px solid {color}; border-radius:8px; '
                    f'text-align:center; line-height:44px; font-size:20px; font-weight:900; color:{color}; '
                    f'flex-shrink:0;">{grade}</div>'
                    f'<div style="flex:1;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:baseline;">'
                    f'<span style="font-weight:600; color:#e2e8f0;">{d["name"]}<span style="font-size:11px; color:#8892a4; margin-left:4px;">{int(weight*100)}%</span></span>'
                    f'<span style="font-weight:700; color:{color};">{score:.1f}<span style="font-size:11px; color:#8892a4;">/100</span></span>'
                    f'</div>'
                    f'<div style="height:5px; background:rgba(255,255,255,0.06); border-radius:3px; margin-top:4px;">'
                    f'<div style="height:100%; width:{min(score,100)}%; background:{color}; border-radius:3px;"></div>'
                    f'</div>'
                    f'</div></div>'
                    f'{bench_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ---- 4. 明细表格 ----
    with st.expander("📊 各维度评分明细"):
        for dim in dims:
            weight_pct = int(dim.get("weight", 0) * 100)
            st.markdown(f"**{dim['name']}** ({weight_pct}%) — {dim.get('label', '')} {dim['grade']} 级 ({dim['score']:.1f}/100)")
            if dim.get("detail"):
                rows = []
                for item in dim["detail"]:
                    cv = _fmt_val(item.get("company"), item["name"])
                    bv = _fmt_val(item["benchmark"], item["name"])
                    sc = f'{item["score"]:.1f}'
                    rows.append(f"| {item['name']} | {cv} | {bv} | {sc} |")
                table = "| 指标 | 公司值 | 行业基准 | 得分 |\n|---|---|---|---|\n" + "\n".join(rows)
                st.markdown(table)


def _extract_history_for_api():
    """从历史消息中提取 (question, answer) 列表用于 API 调用

    注意：只提取完整的问答对（user + assistant），排除当前未回答的问题
    """
    history = []
    messages = st.session_state.get("messages", [])

    # 找到最后一个完整的问答对（确保有 user 和 assistant）
    # messages 格式：[user1, assistant1, user2, assistant2, ...]
    # 如果最后一条是 user（当前问题还没回答），则排除它
    n = len(messages)
    if n == 0:
        return history

    # 如果最后一条是 user（没有对应的 assistant），则只取到前一条
    if messages[-1].get("role") == "user":
        n = n - 1

    # 现在 n 是完整的长度（偶数），取所有完整的问答对
    for i in range(0, n, 2):
        if i + 1 < n:
            user_msg = messages[i]
            ai_msg = messages[i + 1]
            if user_msg.get("role") == "user" and ai_msg.get("role") == "assistant":
                # 截取回答前500字符，避免过长
                answer = ai_msg.get("content", "")[:500]
                history.append((user_msg.get("content", ""), answer))

    # 只返回最近 5 轮（避免过长）
    return history[-5:]


# ============================================================
# 页面布局
# ============================================================
st.set_page_config(
    page_title="财报 AI 助手",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 隐藏侧边栏 + 美化
st.markdown("""
    <style>
        [data-testid="collapsedControl"] { display: none; }
        section[data-testid="stSidebar"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# 标题
st.title("📊 财报 AI 助手")
st.caption("上传财报 PDF，AI 自动解析关键数据并回答你的问题")

# ============================================================
# Session State 初始化
# ============================================================
if "result" not in st.session_state:
    st.session_state.result = {}
if "messages" not in st.session_state:
    st.session_state.messages = []
if "summary" not in st.session_state:
    st.session_state.summary = None
if "radar_data" not in st.session_state:
    st.session_state.radar_data = None
if "current_pdf_hash" not in st.session_state:
    st.session_state.current_pdf_hash = ""


# ============================================================
# 自动滚动 JS（让最新回答始终可见）
# ============================================================
def _auto_scroll():
    components.html("""
    <script>
    function scrollToBottom() {
        const chatArea = window.parent.document.querySelector('[data-testid="stChatMessageContainer"]');
        if (chatArea) {
            chatArea.scrollTop = chatArea.scrollHeight;
        } else {
            window.parent.scrollTo(0, document.body.scrollHeight);
        }
    }
    setTimeout(scrollToBottom, 100);
    </script>
    """, height=0)


# ============================================================
# 主布局：左右两栏
# ============================================================
col1, col2 = st.columns([1, 2], gap="large")

with col1:
    st.markdown("### 📄 上传财报 PDF")
    uploaded_file = st.file_uploader(
        "选择 PDF 文件",
        type="pdf",
        label_visibility="collapsed",
    )
    if uploaded_file:
        st.success(f"已选择: {uploaded_file.name}")

    st.divider()

    if st.button("✨ 生成核心摘要", use_container_width=True):
        if not st.session_state.get("result"):
            st.warning("请先上传并解析财报 PDF")
        else:
            progress_text = st.empty()
            progress_bar = st.progress(0)
            summary_result = {"data": None, "error": None}
            radar_result = {"data": None, "error": None}

            # 行业选择
            try:
                ind_res = requests.get(f"{API_URL}/analyze/industries", timeout=10)
                industry_list = ind_res.json().get("industries", []) if ind_res.status_code == 200 else []
            except Exception:
                industry_list = ["制造业", "科技/互联网", "金融业", "零售/消费品", "能源", "医药", "房地产"]

            industry_options = ["自动识别"] + industry_list
            selected_industry = st.selectbox(
                "行业基准对比",
                industry_options,
                index=0,
                help='选择行业后，能力雷达图将与同行业公司基准值对比。选"自动识别"由 AI 从财报推断行业。',
            )
            industry_param = "" if selected_industry == "自动识别" else selected_industry

            def _generate_summary():
                try:
                    res = requests.post(f"{API_URL}/analyze/summary", json={"focus": "general"}, timeout=120)
                    if res.status_code == 200:
                        summary_result["data"] = res.json().get("summary", "生成失败")
                    else:
                        summary_result["error"] = f"生成失败: HTTP {res.status_code}"
                except Exception as e:
                    summary_result["error"] = f"请求错误: {e}"

            def _generate_radar():
                try:
                    res = requests.post(f"{API_URL}/analyze/radar", json={"industry": industry_param}, timeout=120)
                    if res.status_code == 200:
                        radar_result["data"] = res.json()
                    else:
                        radar_result["error"] = res.json().get("error", f"HTTP {res.status_code}")
                except Exception as e:
                    radar_result["error"] = f"请求错误: {e}"

            t1 = threading.Thread(target=_generate_summary, daemon=True)
            t2 = threading.Thread(target=_generate_radar, daemon=True)
            t1.start()
            t2.start()

            steps = [
                (0, "🔍 正在检索财报关键信息..."),
                (20, "🔍 正在检索财报关键信息..."),
                (45, "🧠 AI 正在综合分析财务数据..."),
                (70, "🧠 AI 正在整理分析结论..."),
                (90, "📝 正在生成最终摘要..."),
            ]
            for pct, text in steps:
                progress_bar.progress(pct, text=text)
                t1.join(timeout=5)
                t2.join(timeout=0.1)
                if not t1.is_alive() and not t2.is_alive():
                    break

            t1.join(timeout=60)
            t2.join(timeout=60)

            if summary_result["data"]:
                progress_bar.progress(100, text="✅ 分析完成！")
                st.session_state.summary = summary_result["data"]
            elif summary_result["error"]:
                progress_bar.empty()
                st.error(summary_result["error"])

            if radar_result["data"]:
                st.session_state.radar_data = radar_result["data"]
            elif radar_result["error"]:
                st.warning(f"雷达图生成失败: {radar_result['error']}")

    if st.session_state.summary:
        summary_html = _md_lib.markdown(st.session_state.summary, extensions=['tables', 'fenced_code'])
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
            {summary_html}
        </div>
        """, unsafe_allow_html=True)

    if st.session_state.radar_data:
        _render_radar_chart(st.session_state.radar_data)

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
                     # 转为 markdown 表格（避免白底）
                     if rows and isinstance(rows[0], dict):
                         headers = list(rows[0].keys())
                         md_rows = ["| " + " | ".join(str(r.get(h, "")) for h in headers) + " |" for r in rows]
                         header_line = "| " + " | ".join(headers) + " |"
                         separator = "| " + " | ".join(["---"] * len(headers)) + " |"
                         st.markdown(header_line + "\n" + separator + "\n" + "\n".join(md_rows))
                     elif rows and isinstance(rows[0], list):
                         md_rows = ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
                         st.markdown("\n".join(md_rows))
                     else:
                         st.write(rows)

    st.divider()
    st.markdown("### 💬 对话 DeepSeek")

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
            "应收账款周转率是多少？",
        ],
        "💰 分红": [
            "今年分红了吗？",
            "股息率是多少？",
        ],
    }

    # 如果还没上传文件，显示预设问题引导
    if not st.session_state.result:
        st.markdown("##### 💡 试试问这些问题（上传财报后即可提问）")
        for category, questions in preset_questions.items():
            st.markdown(f"**{category}**")
            for q in questions:
                st.markdown(f"• {q}")
        st.markdown("---")
        st.info("👆 请先在左侧上传财报 PDF 文件，然后就可以开始提问了！")

    # 渲染历史消息
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(_render_message_content(msg), unsafe_allow_html=True)
            # AI 回答下方显示推荐问题
            if msg["role"] == "assistant" and msg.get("recommendations"):
                _render_recommended(msg["recommendations"], idx)

    # 处理挂起的推荐问题
    if "pending_question" in st.session_state:
        user_question = st.session_state.pop("pending_question")
        st.session_state.messages.append({"role": "user", "content": user_question})

        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            with st.spinner("AI 正在分析财报..."):
                try:
                    history = _extract_history_for_api()
                    resp = requests.post(
                        f"{API_URL}/chat",
                        json={"question": user_question, "history": history},
                        timeout=120,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        answer = data.get("answer", "无法回答")
                        source_pages = data.get("source_pages", [])
                        recommendations = data.get("recommendations", [])
                    else:
                        answer = f"请求失败: HTTP {resp.status_code}"
                        source_pages = []
                        recommendations = []
                except Exception as e:
                    answer = f"连接错误: {e}"
                    source_pages = []
                    recommendations = []

            ai_msg = {
                "role": "assistant",
                "content": answer,
                "source_pages": source_pages,
                "recommendations": recommendations,
            }
            st.session_state.messages.append(ai_msg)
            st.markdown(_render_message_content(ai_msg), unsafe_allow_html=True)
            if recommendations:
                _render_recommended(recommendations, len(st.session_state.messages) - 1)

        _auto_scroll()

    # 聊天输入框（仅在已上传文件后显示）
    if st.session_state.result:
        if user_question := st.chat_input("请提问这份财报的内容..."):
            st.session_state.messages.append({"role": "user", "content": user_question})

            with st.chat_message("user"):
                st.markdown(user_question)

            with st.chat_message("assistant"):
                with st.spinner("AI 正在分析财报..."):
                    try:
                        history = _extract_history_for_api()
                        resp = requests.post(
                            f"{API_URL}/chat",
                            json={"question": user_question, "history": history},
                            timeout=120,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            answer = data.get("answer", "无法回答")
                            source_pages = data.get("source_pages", [])
                            recommendations = data.get("recommendations", [])
                        else:
                            answer = f"请求失败: HTTP {resp.status_code}"
                            source_pages = []
                            recommendations = []
                    except Exception as e:
                        answer = f"连接错误: {e}"
                        source_pages = []
                        recommendations = []

                ai_msg = {
                    "role": "assistant",
                    "content": answer,
                    "source_pages": source_pages,
                    "recommendations": recommendations,
                }
                st.session_state.messages.append(ai_msg)
                st.markdown(_render_message_content(ai_msg), unsafe_allow_html=True)
                if recommendations:
                    _render_recommended(recommendations, len(st.session_state.messages) - 1)

            _auto_scroll()
