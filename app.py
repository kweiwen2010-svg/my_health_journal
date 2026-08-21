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
if not api_key:
    st.error("❌ 找不到 Gemini API Key！")
    st.stop()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

def init_db():
    conn = sqlite3.connect("food_data.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS food_logs (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, meal_type TEXT, content TEXT, weight REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS user_profile (
                 id INTEGER PRIMARY KEY, height REAL, weight REAL, age INTEGER, activity TEXT, medical TEXT)""")
    c.execute("INSERT OR IGNORE INTO user_profile (id, height, weight, age, activity, medical) VALUES (1, 178.0, 75.0, 56, '中度運動', '無')")
    conn.commit()
    conn.close()

init_db()

def get_user_profile():
    conn = sqlite3.connect("food_data.db")
    df = pd.read_sql("SELECT * FROM user_profile WHERE id=1", conn)
    conn.close()
    if df.empty:
        return {"height": 178.0, "weight": 75.0, "age": 56, "activity": "中度運動", "medical": "無"}
    return df.iloc[0].to_dict()

def update_user_profile(data):
    conn = sqlite3.connect("food_data.db")
    c = conn.cursor()
    c.execute("UPDATE user_profile SET height=?, weight=?, age=?, activity=?, medical=? WHERE id=1",
              (data['height'], data['weight'], data['age'], data['activity'], data['medical']))
    conn.commit()
    conn.close()

# ==========================================
# 3. 介面結構
# ==========================================
st.title("🥗 AI 智慧營養管理")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📸 記錄", "📖 日誌", "🤖 AI 評估", "📈 趨勢", "⚙️ 設定"])

# ------------------------------------------
# TAB 5: 個人設定
# ------------------------------------------
with tab5:
    st.subheader("⚙️ 個人檔案設定")
    p = get_user_profile()
    
    with st.form("profile_form"):
        h_val = st.number_input("身高 (cm)", value=float(p['height']))
        w_val = st.number_input("體重 (kg)", value=float(p['weight']))
        a_val = st.number_input("年齡", value=int(p['age']))
        
        activities = ["久坐不動", "輕度運動", "中度運動", "高度運動"]
        act_idx = activities.index(p['activity']) if p['activity'] in activities else 2
        act_val = st.selectbox("運動狀態", activities, index=act_idx)
        
        med_val = st.text_area("健康備註/過敏源", value=str(p['medical']))
        
        submitted = st.form_submit_button("💾 儲存個人資料")
        if submitted:
            new_p = {
                "height": h_val,
                "weight": w_val,
                "age": a_val,
                "activity": act_val,
                "medical": med_val
            }
            update_user_profile(new_p)
            st.success("✅ 個人資料已成功儲存！")

# ------------------------------------------
# TAB 1: 拍照與記錄
# ------------------------------------------
with tab1:
    st.subheader("📸 餐點分析")
    meal_type = st.selectbox("選擇餐別", ["早餐", "午餐", "晚餐", "點心"])
    uploaded_file = st.file_uploader("上傳餐點照片", type=["jpg", "jpeg", "png"])
    user_note = st.text_input("💡 補充說明 (例如：吃了一半、加了一匙糖)")
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="已上傳餐點", use_container_width=True)
        
        if st.button("✨ AI 深度評估"):
            with st.spinner("AI 正在結合您的個人資料進行深度分析..."):
                try:
                    p = get_user_profile()
                    prompt = f"""
                    你是一位專業營養師。請根據以下用戶資料分析照片中的餐點：
                    - 用戶身型：{p['age']}歲, {p['height']}cm, {p['weight']}kg
                    - 運動狀態：{p['activity']}
                    - 健康備註/過敏源：{p['medical']}
                    - 用戶補充說明：{user_note}
                    
                    請評估：
                    1. 這份餐點大致包含哪些食物與營養成分？
                    2. 這份餐點是否適合該用戶目前的身體狀態與運動習慣？
                    3. 有無營養過剩、不足或需要注意的健康風險？
                    """
                    response = model.generate_content([prompt, image])
                    st.session_state.last_analysis = response.text
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"❌ 分析失敗，錯誤訊息：{e}")

    if "last_analysis" in st.session_state and st.button("➕ 加入日誌"):
        conn = sqlite3.connect("food_data.db")
        c = conn.cursor()
        c.execute("INSERT INTO food_logs (date, meal_type, content, weight) VALUES (?, ?, ?, ?)",
                  (datetime.now().strftime("%Y-%m-%d %H:%M"), meal_type, st.session_state.last_analysis, get_user_profile()['weight']))
        conn.commit()
        conn.close()
        st.success("✅ 紀錄成功已存入日誌！")
        del st.session_state.last_analysis

# ------------------------------------------
# TAB 2: 飲食日誌
# ------------------------------------------
with tab2:
    st.subheader("📖 我的飲食日誌")
    conn = sqlite3.connect("food_data.db")
    df = pd.read_sql("SELECT * FROM food_logs ORDER BY date DESC", conn)
    conn.close()
    if df.empty:
        st.info("目前尚無飲食紀錄。")
    else:
        for _, row in df.iterrows():
            with st.container(border=True):
                st.markdown(f"**⏰ {row['date']} - {row['meal_type']}**")
                st.write(row['content'])

# ------------------------------------------
# TAB 3: AI 綜合評估
# ------------------------------------------
with tab3:
    st.subheader("🤖 AI 綜合健康建議")
    if st.button("🤖 產生個人化健康總結報告"):
        with st.spinner("AI 正在綜整您的歷史紀錄..."):
            try:
                p = get_user_profile()
                conn = sqlite3.connect("food_data.db")
                df_logs = pd.read_sql("SELECT content FROM food_logs", conn)
                conn.close()
                logs_list = df_logs['content'].tolist() if not df_logs.empty else ["無"]
                prompt = f"請扮演專業營養師，根據用戶資料 {p} 與以下歷史飲食紀錄，給予全方位健康與飲食調整建議：{logs_list}"
                response = model.generate_content(prompt)
                st.markdown(response.text)
            except Exception as e:
                st.error(f"❌ 產生建議失敗，錯誤訊息：{e}")

# ------------------------------------------
# TAB 4: 歷史趨勢
# ------------------------------------------
with tab4:
    st.subheader("📈 體重變化趨勢")
    conn = sqlite3.connect("food_data.db")
    df_logs = pd.read_sql("SELECT * FROM food_logs", conn)
    conn.close()
    if not df_logs.empty and 'weight' in df_logs.columns:
        st.line_chart(df_logs['weight'])
    else:
        st.info("累積多筆紀錄後即可觀察體重趨勢。")