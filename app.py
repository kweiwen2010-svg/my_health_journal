import os
import sqlite3
from datetime import datetime
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image

# ==========================================
# 1. 頁面與 CSS 設定
# ==========================================
st.set_page_config(page_title="AI 智慧營養師", page_icon="🥗", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #f5f7f9; }
    div[data-testid="stVerticalBlock"] { background-color: white; border-radius: 15px; padding: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .stButton>button { width: 100%; border-radius: 20px; background-color: #2ecc71; color: white; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 資料庫與 AI 初始化
# ==========================================
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.6-flash")

def init_db():
    conn = sqlite3.connect("food_data.db")
    c = conn.cursor()
    # 紀錄表
    c.execute("""CREATE TABLE IF NOT EXISTS food_logs (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, meal_type TEXT, content TEXT, weight REAL)""")
    # 設定表
    c.execute("""CREATE TABLE IF NOT EXISTS user_profile (
                 id INTEGER PRIMARY KEY, height REAL, weight REAL, age INTEGER, activity TEXT, medical TEXT)""")
    # 初始化預設設定
    c.execute("INSERT OR IGNORE INTO user_profile (id, height, weight, age, activity, medical) VALUES (1, 170.0, 65.0, 35, '久坐不動', '無')")
    conn.commit()
    conn.close()

init_db()

def get_user_profile():
    conn = sqlite3.connect("food_data.db")
    df = pd.read_sql("SELECT * FROM user_profile WHERE id=1", conn)
    conn.close()
    return df.iloc[0].to_dict()

def update_user_profile(data):
    conn = sqlite3.connect("food_data.db")
    c = conn.cursor()
    c.execute("UPDATE user_profile SET height=?, weight=?, age=?, activity=?, medical=? WHERE id=1",
              (data['height'], data['weight'], data['age'], data['activity'], data['medical']))
    conn.commit()
    conn.close()

# ==========================================
# 3. 介面邏輯
# ==========================================
st.title("🥗 AI 智慧營養管理")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📸 記錄", "📖 日誌", "🤖 AI 評估", "📈 趨勢", "⚙️ 設定"])

with tab5:
    st.subheader("個人檔案設定")
    p = get_user_profile()
    new_p = {
        "height": st.number_input("身高 (cm)", value=p['height']),
        "weight": st.number_input("體重 (kg)", value=p['weight']),
        "age": st.number_input("年齡", value=p['age']),
        "activity": st.selectbox("運動狀態", ["久坐不動", "輕度運動", "中度運動", "高度運動"], index=["久坐不動", "輕度運動", "中度運動", "高度運動"].index(p['activity'])),
        "medical": st.text_area("健康備註/過敏源", value=p['medical'])
    }
    if st.button("💾 儲存個人資料"):
        update_user_profile(new_p)
        st.success("✅ 設定已更新並永久儲存")

with tab1:
    st.subheader("餐點分析")
    meal_type = st.selectbox("餐別", ["早餐", "午餐", "晚餐", "點心"])
    uploaded_file = st.file_uploader("上傳餐點照片", type=["jpg", "png"])
    
    if uploaded_file and st.button("✨ AI 深度評估"):
        p = get_user_profile()
        image = Image.open(uploaded_file)
        prompt = f"""
        你是一位專業營養師。請根據以下用戶資料分析照片中的餐點：
        用戶資料：{p['age']}歲, {p['height']}cm, {p['weight']}kg, 運動狀態：{p['activity']}, 健康備註：{p['medical']}。
        請回答：這份餐點是否適合該用戶？有無營養過剩或不足？
        """
        res = model.generate_content([prompt, image])
        st.session_state.last_analysis = res.text
        st.markdown(res.text)

    if "last_analysis" in st.session_state and st.button("➕ 加入日誌"):
        conn = sqlite3.connect("food_data.db")
        c = conn.cursor()
        c.execute("INSERT INTO food_logs (date, meal_type, content, weight) VALUES (?, ?, ?, ?)",
                  (datetime.now().strftime("%Y-%m-%d %H:%M"), meal_type, st.session_state.last_analysis, get_user_profile()['weight']))
        conn.commit()
        conn.close()
        st.success("✅ 紀錄成功！")
        del st.session_state.last_analysis

# (Tab 2, 3, 4 保持原本邏輯即可)
with tab2:
    st.subheader("飲食日誌")
    conn = sqlite3.connect("food_data.db")
    df = pd.read_sql("SELECT * FROM food_logs ORDER BY date DESC", conn)
    conn.close()
    for _, row in df.iterrows():
        st.write(f"**{row['date']}** - {row['meal_type']}")
        st.info(row['content'])

with tab3:
    st.subheader("AI 綜合建議")
    if st.button("🤖 產生個人化建議"):
        p = get_user_profile()
        conn = sqlite3.connect("food_data.db")
        logs = pd.read_sql("SELECT content FROM food_logs", conn).to_string()
        conn.close()
        prompt = f"根據用戶資料 {p} 與以下歷史飲食紀錄，給予專業建議：{logs}"
        st.markdown(model.generate_content(prompt).text)