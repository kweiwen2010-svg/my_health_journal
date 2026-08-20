import os
import sqlite3
from datetime import datetime
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image

# ==========================================
# 1. 頁面基本設定
# ==========================================
st.set_page_config(page_title="AI 智慧營養與飲食記錄器", page_icon="🥗", layout="centered")

# ==========================================
# 2. 自動載入 API Key 與 模型設定
# ==========================================
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 找不到 Gemini API Key！請檢查 Streamlit Secrets 設定。")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.6-flash")

# ==========================================
# 3. 資料庫與輔助函式
# ==========================================
def init_db():
    conn = sqlite3.connect("food_data.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT, meal_type TEXT, content TEXT, calories REAL,
            protein REAL, carbs REAL, fat REAL, weight REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

def load_all_logs():
    conn = sqlite3.connect("food_data.db")
    try:
        df = pd.read_sql("SELECT * FROM food_logs", conn)
    except Exception:
        df = pd.DataFrame()
    conn.close()
    return df

# ==========================================
# 4. 側邊欄：個人設定
# ==========================================
st.sidebar.title("📌 個人健康設定")
user_height = st.sidebar.number_input("身高 (cm)", value=170.0)
user_weight = st.sidebar.number_input("體重 (kg)", value=65.0)
user_age = st.sidebar.number_input("年齡", value=35, step=1)
user_medical = st.sidebar.text_area("病史/過敏源備註", value="無")

# ==========================================
# 5. 頂部導覽與頁面內容
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs(["拍照分析", "飲食日誌", "AI 智慧統整", "歷史趨勢"])

with tab1:
    st.title("🥗 AI 智慧營養與飲食記錄器")
    meal_type = st.selectbox("選擇餐別", ["早餐", "午餐", "晚餐", "點心/其他"])
    uploaded_file = st.file_uploader("拍攝或上傳你的餐點", type=["jpg", "jpeg", "png"])
    user_note = st.text_input("💡 補充說明")

    if uploaded_file is not None:
        st.image(uploaded_file, caption="已載入餐點圖片", use_container_width=True)
        if st.button("✨ 開始 AI 營養分析"):
            with st.spinner("AI 營養師正在分析中..."):
                try:
                    image = Image.open(uploaded_file)
                    prompt = f"扮演營養師分析圖片：1.內容份量 2.熱量/蛋白質/碳水/脂肪估算 3.建議。補充：{user_note}"
                    response = model.generate_content([prompt, image])
                    st.markdown(response.text)
                    st.session_state.last_analysis = response.text
                except Exception as e:
                    st.error(f"分析失敗: {e}")

    if "last_analysis" in st.session_state:
        if st.button("➕ 將此餐點加入紀錄"):
            conn = sqlite3.connect("food_data.db")
            c = conn.cursor()
            c.execute("INSERT INTO food_logs (date, meal_type, content, weight) VALUES (?, ?, ?, ?)",
                      (datetime.now().strftime("%Y-%m-%d %H:%M"), meal_type, st.session_state.last_analysis, user_weight))
            conn.commit()
            conn.close()
            st.success("✅ 成功加入紀錄！")

with tab2:
    st.title("📖 我的飲食日誌")
    df_logs = load_all_logs()
    if df_logs.empty:
        st.info("尚無記錄。")
    else:
        if st.button("🗑️ 清空所有紀錄"):
            conn = sqlite3.connect("food_data.db")
            c = conn.cursor()
            c.execute("DELETE FROM food_logs")
            conn.commit()
            conn.close()
            st.rerun()
        for _, row in df_logs.iterrows():
            with st.expander(f"⏰ {row['date']} - 【{row['meal_type']}】"):
                st.write(row['content'])

with tab3:
    st.title("✨ AI 智慧統整")
    df_logs = load_all_logs()
    st.write(f"總共記錄了 {len(df_logs)} 筆資料。")

with tab4:
    st.title("📈 歷史趨勢")
    df_logs = load_all_logs()
    if not df_logs.empty and 'weight' in df_logs.columns:
        st.line_chart(df_logs['weight'])
    else:
        st.info("尚無體重歷史數據可供繪圖。")