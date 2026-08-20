import os
import sqlite3
from datetime import datetime
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image

# ==========================================
# 1. 頁面設定與 API
# ==========================================
st.set_page_config(page_title="AI 智慧營養記錄", page_icon="🥗", layout="centered")
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.6-flash")

# ==========================================
# 2. 資料庫初始化（包含個人資料表）
# ==========================================
def init_db():
    conn = sqlite3.connect("food_data.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS food_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, meal_type TEXT, 
        content TEXT, weight REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY, height REAL, weight REAL, age INTEGER, medical TEXT)""")
    # 初始化設定
    c.execute("INSERT OR IGNORE INTO user_profile (id, height, weight, age, medical) VALUES (1, 170.0, 65.0, 35, '無')")
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 3. 側邊欄：持久化個人設定
# ==========================================
st.sidebar.title("📌 個人健康設定")
conn = sqlite3.connect("food_data.db")
profile = pd.read_sql("SELECT * FROM user_profile WHERE id=1", conn).iloc[0]

new_h = st.sidebar.number_input("身高 (cm)", value=float(profile['height']))
new_w = st.sidebar.number_input("體重 (kg)", value=float(profile['weight']))
new_a = st.sidebar.number_input("年齡", value=int(profile['age']))
new_m = st.sidebar.text_area("病史/備註", value=profile['medical'])

if st.sidebar.button("💾 儲存個人資料"):
    c = conn.cursor()
    c.execute("UPDATE user_profile SET height=?, weight=?, age=?, medical=? WHERE id=1", (new_h, new_w, new_a, new_m))
    conn.commit()
    st.sidebar.success("已更新！")
conn.close()

# ==========================================
# 4. 分頁內容
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["拍照分析", "飲食日誌", "AI 智慧統整", "歷史趨勢"])

with tab1:
    st.title("🥗 拍照分析")
    uploaded_file = st.file_uploader("上傳餐點", type=["jpg", "png"])
    if uploaded_file and st.button("✨ 開始分析"):
        image = Image.open(uploaded_file)
        response = model.generate_content(["請分析這餐的營養建議", image])
        st.markdown(response.text)
        st.session_state.last_analysis = response.text
    
    if "last_analysis" in st.session_state:
        if st.button("➕ 加入紀錄"):
            conn = sqlite3.connect("food_data.db")
            conn.execute("INSERT INTO food_logs (date, meal_type, content, weight) VALUES (?,?,?,?)",
                         (datetime.now().strftime("%Y-%m-%d %H:%M"), "一般", st.session_state.last_analysis, new_w))
            conn.commit()
            conn.close()
            st.success("紀錄成功")

with tab2:
    st.title("📖 飲食日誌")
    df = pd.read_sql("SELECT * FROM food_logs", sqlite3.connect("food_data.db"))
    st.dataframe(df)

with tab3:
    st.title("✨ AI 智慧統整")
    if st.button("開始 AI 統整分析"):
        logs = pd.read_sql("SELECT * FROM food_logs", sqlite3.connect("food_data.db")).to_string()
        user_info = f"身高:{new_h}, 體重:{new_w}, 年齡:{new_a}, 病史:{new_m}"
        prompt = f"你是專業營養師，這是使用者資料:{user_info}，這是飲食紀錄:{logs}。請給予整體健康與飲食建議。"
        res = model.generate_content(prompt)
        st.markdown(res.text)

with tab4:
    st.title("📈 體重歷史趨勢")
    df = pd.read_sql("SELECT * FROM food_logs", sqlite3.connect("food_data.db"))
    if not df.empty:
        st.line_chart(df['weight'])