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
model = genai.GenerativeModel("gemini-1.5-flash")

def init_db():
    conn = sqlite3.connect("food_data.db")
    c = conn.cursor()
    # 擴充欄位：儲存營養數據
    c.execute("""CREATE TABLE IF NOT EXISTS food_logs (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, meal_type TEXT, 
                 content TEXT, calories REAL, protein REAL, carbs REAL, fat REAL, weight REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS user_profile (
                 id INTEGER PRIMARY KEY, height REAL, weight REAL, age INTEGER, activity TEXT, medical TEXT)""")
    c.execute("INSERT OR IGNORE INTO user_profile (id, height, weight, age, activity, medical) VALUES (1, 170.0, 65.0, 35, '久坐不動', '無')")
    conn.commit()
    conn.close()

init_db()

# ... (保持 get_user_profile 和 update_user_profile 函數) ...
def get_user_profile():
    conn = sqlite3.connect("food_data.db")
    df = pd.read_sql("SELECT * FROM user_profile WHERE id=1", conn)
    conn.close()
    return df.iloc[0].to_dict()

# ==========================================
# 3. 介面邏輯
# ==========================================
st.title("🥗 AI 智慧營養管理")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📸 記錄", "📖 日誌", "🤖 AI 評估", "📈 趨勢", "⚙️ 設定"])

with tab1:
    st.subheader("餐點分析")
    meal_type = st.selectbox("餐別", ["早餐", "午餐", "晚餐", "點心"])
    uploaded_file = st.file_uploader("上傳餐點照片", type=["jpg", "jpeg", "png"])
    user_note = st.text_input("💡 補充說明（例如：吃了半份、加了一匙糖）")
    
    if uploaded_file and st.button("✨ AI 精準營養分析"):
        with st.spinner("AI 正在計算營養並評估中..."):
            p = get_user_profile()
            image = Image.open(uploaded_file)
            prompt = f"""
            你是一位營養師。請分析照片中的餐點並考慮用戶補充說明：{user_note}
            用戶資料：{p['age']}歲, {p['height']}cm, {p['weight']}kg, 運動：{p['activity']}。
            請輸出：
            1. 預估熱量(kcal)、蛋白質(g)、碳水(g)、脂肪(g)。
            2. 給予適合該用戶的精簡建議。
            請用 Markdown 格式，並將數據明確標示出來。
            """
            response = model.generate_content([prompt, image])
            st.session_state.last_analysis = response.text
            st.markdown(response.text)

    if "last_analysis" in st.session_state and st.button("➕ 加入日誌"):
        conn = sqlite3.connect("food_data.db")
        c = conn.cursor()
        c.execute("INSERT INTO food_logs (date, meal_type, content, weight) VALUES (?, ?, ?, ?)",
                  (datetime.now().strftime("%Y-%m-%d %H:%M"), meal_type, st.session_state.last_analysis, get_user_profile()['weight']))
        conn.commit()
        conn.close()
        st.success("✅ 紀錄已存入日誌！")
        del st.session_state.last_analysis

with tab2:
    st.subheader("我的飲食日誌")
    conn = sqlite3.connect("food_data.db")
    df = pd.read_sql("SELECT * FROM food_logs ORDER BY date DESC", conn)
    conn.close()
    for _, row in df.iterrows():
        with st.expander(f"{row['date']} - {row['meal_type']}"):
            st.markdown(row['content'])