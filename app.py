import os
import sqlite3
from datetime import datetime
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image

# ==========================================
# 1. 介面美化設定 (CSS)
# ==========================================
st.set_page_config(page_title="AI 智慧營養師", page_icon="🥗", layout="wide")
st.markdown("""
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    </style>
    """, unsafe_allow_html=True)

# API 設定
genai.configure(api_key=st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.6-flash")

# ==========================================
# 2. 資料庫管理
# ==========================================
def get_db_conn():
    return sqlite3.connect("food_data.db")

def init_db():
    conn = get_db_conn()
    conn.execute("CREATE TABLE IF NOT EXISTS food_logs (id INTEGER PRIMARY KEY, date TEXT, content TEXT, weight REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS user_profile (id INTEGER PRIMARY KEY, h REAL, w REAL, a INTEGER, m TEXT, status TEXT)")
    conn.execute("INSERT OR IGNORE INTO user_profile VALUES (1, 170.0, 65.0, 30, '無', '久坐辦公')")
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 3. 頁籤結構
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🥗 拍照分析", "📖 飲食日誌", "✨ AI 統整", "📈 趨勢", "⚙️ 個人設定"])

# 獲取最新個人資料
profile = pd.read_sql("SELECT * FROM user_profile WHERE id=1", get_db_conn()).iloc[0]

with tab5:
    st.subheader("⚙️ 個人健康設定")
    col1, col2 = st.columns(2)
    with col1:
        h = st.number_input("身高 (cm)", value=float(profile['h']))
        w = st.number_input("體重 (kg)", value=float(profile['w']))
        status = st.selectbox("運動狀態", ["久坐辦公", "輕度運動", "中度運動", "高強度訓練"], index=["久坐辦公", "輕度運動", "中度運動", "高強度訓練"].index(profile['status']))
    with col2:
        a = st.number_input("年齡", value=int(profile['a']))
        m = st.text_area("病史/備註", value=profile['m'])
    
    if st.button("💾 儲存所有設定"):
        get_db_conn().execute("UPDATE user_profile SET h=?, w=?, a=?, m=?, status=? WHERE id=1", (h, w, a, m, status))
        st.success("設定已更新！")

with tab1:
    st.title("🥗 拍照分析")
    uploaded_file = st.file_uploader("上傳餐點照片", type=["jpg", "png"])
    if uploaded_file and st.button("✨ 根據我的設定進行 AI 分析"):
        with st.spinner("AI 正在根據您的運動習慣分析..."):
            image = Image.open(uploaded_file)
            user_context = f"使用者資料：身高{profile['h']}cm, 體重{profile['w']}kg, 年齡{profile['a']}, 運動狀態：{profile['status']}, 病史：{profile['m']}"
            res = model.generate_content([f"請結合使用者背景資料給予餐點營養分析與建議: {user_context}", image])
            st.markdown(res.text)
            st.session_state.last_res = res.text
            
    if "last_res" in st.session_state and st.button("➕ 加入紀錄"):
        get_db_conn().execute("INSERT INTO food_logs (date, content, weight) VALUES (?,?,?)", 
                             (datetime.now().strftime("%Y-%m-%d"), st.session_state.last_res, profile['w']))
        st.success("紀錄成功")

with tab2:
    st.subheader("📖 飲食歷史")
    st.dataframe(pd.read_sql("SELECT * FROM food_logs", get_db_conn()), use_container_width=True)

with tab3:
    st.subheader("✨ AI 智慧統整")
    if st.button("產出月度健康報告"):
        logs = pd.read_sql("SELECT * FROM food_logs", get_db_conn()).to_string()
        res = model.generate_content(f"基於以下飲食紀錄，給予長期健康優化建議: {logs}")
        st.markdown(res.text)

with tab4:
    st.subheader("📈 體重趨勢")
    df = pd.read_sql("SELECT * FROM food_logs", get_db_conn())
    if not df.empty: st.line_chart(df['weight'])