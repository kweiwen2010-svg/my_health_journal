import os
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image

# 1. 頁面設定
st.set_page_config(page_title="AI 智慧營養師", page_icon="🥗", layout="centered")

# 2. API Key 設定
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 找不到 Gemini API Key！")
    st.stop()
genai.configure(api_key=api_key)

# 3. 初始化：讀取飲食記錄與個人設定檔
PROFILE_FILE = "user_profile.csv"
LOG_FILE = "food_log.csv"

# 載入個人資料
if "profile" not in st.session_state:
    if os.path.exists(PROFILE_FILE):
        df_profile = pd.read_csv(PROFILE_FILE)
        st.session_state.profile = df_profile.iloc[0].to_dict()
    else:
        st.session_state.profile = None

# 載入飲食日誌
if "food_logs" not in st.session_state:
    if os.path.exists(LOG_FILE):
        st.session_state.food_logs = pd.read_csv(LOG_FILE).to_dict("records")
    else:
        st.session_state.food_logs = []

# --- 邏輯：檢查是否已建檔 ---
if st.session_state.profile is None:
    st.title("🥗 歡迎使用 AI 智慧營養師")
    st.subheader("請先建立您的個人健康檔案")
    
    with st.form("profile_form"):
        age = st.number_input("年齡", 10, 100, 30)
        height = st.number_input("身高 (cm)", 100.0, 220.0, 170.0)
        weight = st.number_input("體重 (kg)", 30.0, 150.0, 65.0)
        activity = st.selectbox("運動狀態", ["久坐少動", "輕度運動", "中度運動", "高度運動"])
        medical = st.text_area("病史 / 飲食禁忌")
        
        if st.form_submit_button("儲存並開始使用"):
            profile_data = {
                "age": age, "height": height, "weight": weight, 
                "activity": activity, "medical": medical
            }
            # 存入 Session 並寫入 CSV
            st.session_state.profile = profile_data
            pd.DataFrame([profile_data]).to_csv(PROFILE_FILE, index=False)
            st.rerun()

else:
    # --- 正式功能頁面 ---
    st.title("🥗 AI 智慧營養與飲食記錄器")
    st.sidebar.header("個人基本資料")
    st.sidebar.write(f"年齡: {st.session_state.profile['age']}")
    st.sidebar.write(f"身高: {st.session_state.profile['height']} cm")
    st.sidebar.write(f"體重: {st.session_state.profile['weight']} kg")
    
    if st.sidebar.button("重新設定個人資料"):
        st.session_state.profile = None
        if os.path.exists(PROFILE_FILE): os.remove(PROFILE_FILE)
        st.rerun()

    tab1, tab2 = st.tabs(["📸 拍照分析", "📊 飲食日誌"])

    with tab1:
        camera_file = st.camera_input("拍攝你的餐點")
        uploaded_file = st.file_uploader("或上傳照片", type=["jpg", "jpeg", "png"])
        image_to_process = camera_file or uploaded_file

        if image_to_process:
            image = Image.open(image_to_process)
            st.image(image, use_container_width=True)

            if st.button("✨ 開始 AI 營養分析"):
                with st.spinner("AI 正在分析..."):
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    prompt = f"使用者背景：{st.session_state.profile}。請分析此食物的名稱、份量、熱量與建議。"
                    response = model.generate_content([image, prompt])
                    st.session_state.last_analysis = response.text
            
            if "last_analysis" in st.session_state:
                st.markdown(st.session_state.last_analysis)
                if st.button("➕ 確認加入紀錄"):
                    new_log = {"日期": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "內容": st.session_state.last_analysis}
                    st.session_state.food_logs.append(new_log)
                    pd.DataFrame(st.session_state.food_logs).to_csv(LOG_FILE, index=False)
                    del st.session_state.last_analysis
                    st.success("紀錄已保存！")
                    st.rerun()

    with tab2:
        st.subheader("我的飲食日誌")
        for log in reversed(st.session_state.food_logs):
            st.write(f"📅 {log['日期']}")
            st.markdown(log['內容'])