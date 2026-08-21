import os
import sqlite3
from datetime import datetime
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image

# ==========================================
# 1. 頁面與 CSS 美化設定
# ==========================================
st.set_page_config(page_title="健康營養記錄器", page_icon="🥗", layout="centered")

st.markdown("""
    <style>
    /* 全域字體與背景 */
    .stApp { background-color: #f5f7f9; }
    
    /* 卡片式設計 */
    div[data-testid="stExpander"], div[data-testid="stVerticalBlock"] {
        background-color: white;
        border-radius: 15px;
        padding: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* 調整按鈕樣式 */
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        height: 3.5em;
        background-color: #2ecc71;
        color: white;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover { background-color: #27ae60; }
    
    /* 標題調整 */
    h1, h2 { color: #2c3e50; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 模型與資料庫
# ==========================================
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 找不到 Gemini API Key！")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.6-flash")

def init_db():
    conn = sqlite3.connect("food_data.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, meal_type TEXT, content TEXT, weight REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

def load_all_logs():
    conn = sqlite3.connect("food_data.db")
    df = pd.read_sql("SELECT * FROM food_logs ORDER BY date DESC", conn)
    conn.close()
    return df

# ==========================================
# 3. 主要介面結構
# ==========================================
st.title("🥗 健康營養管理")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📸 拍照記錄", "📖 日誌", "🤖 分析", "📈 趨勢", "⚙️ 設定"])

# Session State 初始化
if "user_settings" not in st.session_state:
    st.session_state.user_settings = {"height": 170.0, "weight": 65.0, "age": 35, "activity": "久坐不動", "medical": "無"}

with tab1:
    st.subheader("今日餐點記錄")
    meal_type = st.selectbox("選擇餐別", ["早餐", "午餐", "晚餐", "點心/其他"])
    uploaded_file = st.file_uploader("點擊這裡上傳餐點照片", type=["jpg", "jpeg", "png"])
    
    if uploaded_file:
        st.image(uploaded_file, caption="已選取圖片", use_container_width=True)
        if st.button("✨ 執行 AI 智慧分析"):
            with st.spinner("AI 正在分析餐點營養..."):
                image = Image.open(uploaded_file)
                response = model.generate_content(["請分析這份餐點的營養與份量建議", image])
                st.session_state.last_analysis = response.text
                st.markdown(f"**分析結果：**\n\n{response.text}")

    if "last_analysis" in st.session_state and st.button("➕ 儲存至日誌"):
        conn = sqlite3.connect("food_data.db")
        c = conn.cursor()
        c.execute("INSERT INTO food_logs (date, meal_type, content, weight) VALUES (?, ?, ?, ?)",
                  (datetime.now().strftime("%Y-%m-%d %H:%M"), meal_type, st.session_state.last_analysis, st.session_state.user_settings["weight"]))
        conn.commit()
        conn.close()
        st.success("✅ 紀錄已儲存！")
        del st.session_state.last_analysis

with tab2:
    st.subheader("我的飲食日誌")
    df_logs = load_all_logs()
    if df_logs.empty: st.info("目前尚無飲食紀錄。")
    for _, row in df_logs.iterrows():
        with st.container():
            st.markdown(f"**{row['meal_type']}** | {row['date']}")
            st.write(row['content'])
            st.divider()

with tab3:
    st.subheader("AI 營養師建議")
    if st.button("🤖 產生健康總結報告"):
        df_logs = load_all_logs()
        summary_prompt = f"背景：{st.session_state.user_settings}。歷史紀錄：{df_logs['content'].tolist()}。請提供專業健康建議。"
        res = model.generate_content(summary_prompt)
        st.markdown(res.text)

with tab4:
    st.subheader("體重變化趨勢")
    df_logs = load_all_logs()
    if not df_logs.empty: st.line_chart(df_logs['weight'])
    else: st.info("累積多筆紀錄後即可觀察變化。")

with tab5:
    st.subheader("個人檔案設定")
    st.session_state.user_settings["height"] = st.number_input("身高 (cm)", value=st.session_state.user_settings["height"])
    st.session_state.user_settings["weight"] = st.number_input("體重 (kg)", value=st.session_state.user_settings["weight"])
    st.session_state.user_settings["age"] = st.number_input("年齡", value=st.session_state.user_settings["age"])
    st.session_state.user_settings["activity"] = st.selectbox("運動狀態", ["久坐不動", "輕度運動", "中度運動", "高度運動"])
    st.session_state.user_settings["medical"] = st.text_area("健康備註", value=st.session_state.user_settings["medical"])
    st.success("設定已暫存 (更換資料庫後將自動永久同步)")