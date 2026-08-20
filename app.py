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
# 2. 模型設定
# ==========================================
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 找不到 Gemini API Key！")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3.6-flash")

# ==========================================
# 3. 資料庫初始化
# ==========================================
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
    df = pd.read_sql("SELECT * FROM food_logs", conn)
    conn.close()
    return df

# ==========================================
# 4. 頂部五個分頁（無側欄，功能整合）
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(["拍照分析", "飲食日誌", "AI 智慧統整", "歷史趨勢", "個人設定"])

# 初始化 Session State 來儲存個人設定
if "user_settings" not in st.session_state:
    st.session_state.user_settings = {
        "height": 170.0, "weight": 65.0, "age": 35, 
        "activity": "久坐不動", "medical": "無"
    }

with tab5:
    st.title("⚙️ 個人設定")
    st.session_state.user_settings["height"] = st.number_input("身高 (cm)", value=st.session_state.user_settings["height"])
    st.session_state.user_settings["weight"] = st.number_input("體重 (kg)", value=st.session_state.user_settings["weight"])
    st.session_state.user_settings["age"] = st.number_input("年齡", value=st.session_state.user_settings["age"])
    st.session_state.user_settings["activity"] = st.selectbox("運動狀態", ["久坐不動", "輕度運動", "中度運動", "高度運動"])
    st.session_state.user_settings["medical"] = st.text_area("病史/過敏源備註", value=st.session_state.user_settings["medical"])
    st.success("個人設定已更新！")

with tab1:
    st.title("🥗 AI 智慧營養與飲食記錄器")
    meal_type = st.selectbox("選擇餐別", ["早餐", "午餐", "晚餐", "點心/其他"])
    uploaded_file = st.file_uploader("拍攝或上傳你的餐點", type=["jpg", "jpeg", "png"])
    user_note = st.text_input("💡 補充說明")

    if uploaded_file is not None:
        st.image(uploaded_file, caption="已載入餐點圖片", use_container_width=True)
        if st.button("✨ 開始 AI 營養分析"):
            with st.spinner("AI 正在分析..."):
                image = Image.open(uploaded_file)
                response = model.generate_content(["請分析這份餐點的營養內容與份量", image])
                st.markdown(response.text)
                st.session_state.last_analysis = response.text

    if "last_analysis" in st.session_state and st.button("➕ 加入紀錄"):
        conn = sqlite3.connect("food_data.db")
        c = conn.cursor()
        c.execute("INSERT INTO food_logs (date, meal_type, content, weight) VALUES (?, ?, ?, ?)",
                  (datetime.now().strftime("%Y-%m-%d %H:%M"), meal_type, st.session_state.last_analysis, st.session_state.user_settings["weight"]))
        conn.commit()
        conn.close()
        st.success("✅ 已儲存至飲食日誌！")

with tab2:
    st.title("📖 我的飲食日誌")
    df_logs = load_all_logs()
    if df_logs.empty:
        st.info("尚無紀錄。")
    for _, row in df_logs.iterrows():
        with st.expander(f"⏰ {row['date']} - {row['meal_type']}"):
            st.write(row['content'])

with tab3:
    st.title("✨ AI 智慧統整")
    df_logs = load_all_logs()
    if st.button("🤖 執行綜合健康總結"):
        user_info = st.session_state.user_settings
        summary_prompt = f"""
        請扮演專業營養師，根據以下個人背景與歷史飲食紀錄，提供健康評估與建議：
        背景：身高 {user_info['height']}cm, 體重 {user_info['weight']}kg, 年齡 {user_info['age']}歲, 運動狀態：{user_info['activity']}, 病史備註：{user_info['medical']}
        
        歷史紀錄：
        {df_logs['content'].tolist()}
        """
        res = model.generate_content(summary_prompt)
        st.markdown(res.text)

with tab4:
    st.title("📈 歷史趨勢")
    df_logs = load_all_logs()
    if not df_logs.empty:
        st.line_chart(df_logs['weight'])