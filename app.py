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

# 3. 初始化：讀取個人設定檔與飲食記錄
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
        try:
            st.session_state.food_logs = pd.read_csv(LOG_FILE).to_dict("records")
        except:
            st.session_state.food_logs = []
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
        # 【第二階段新增】選擇餐別
        meal_type = st.selectbox("選擇餐別", ["早餐", "午餐", "晚餐", "點心/其他"])
        
        camera_file = st.camera_input("拍攝你的餐點")
        uploaded_file = st.file_uploader("或上傳照片", type=["jpg", "jpeg", "png"])
        image_to_process = camera_file or uploaded_file

        if image_to_process:
            image = Image.open(image_to_process)
            image.thumbnail((800, 800))
            if image.mode != 'RGB': 
                image = image.convert('RGB')
                
            st.image(image, use_container_width=True)

            if st.button("✨ 開始 AI 營養分析"):
                with st.spinner("AI 正在分析營養素..."):
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    # 【第二階段優化】精準要求回傳營養素結構
                    prompt = (
                        f"你是專業營養師。使用者背景：{st.session_state.profile}。"
                        f"本次記錄餐別為：{meal_type}。"
                        f"請分析此食物的名稱、份量、預估總熱量(大卡)，"
                        f"以及蛋白質、澱粉(碳水化合物)、脂肪的大約克數(g)，並給予健康建議。"
                    )
                    response = model.generate_content([image, prompt])
                    st.session_state.last_analysis = response.text
            
            if "last_analysis" in st.session_state:
                st.markdown("### 💡 分析結果")
                st.markdown(st.session_state.last_analysis)
                
                if st.button("➕ 確認將此餐點加入紀錄"):
                    new_log = {
                        "日期": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                        "餐別": meal_type,
                        "體重": st.session_state.profile['weight'],
                        "內容": st.session_state.last_analysis
                    }
                    st.session_state.food_logs.append(new_log)
                    
                    # 寫入 CSV 檔案
                    df_to_save = pd.DataFrame(st.session_state.food_logs)
                    df_to_save.to_csv(LOG_FILE, index=False)
                    
                    del st.session_state.last_analysis
                    st.success("紀錄已成功永久保存！")
                    st.rerun()

    with tab2:
        st.subheader("我的飲食日誌")
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🗑️ 清空所有紀錄"):
                st.session_state.food_logs = []
                if os.path.exists(LOG_FILE): 
                    os.remove(LOG_FILE)
                st.rerun()
                
        if not st.session_state.food_logs:
            st.info("目前尚無任何飲食紀錄，快去拍照上傳開始記錄吧！")
        else:
            for i, log in enumerate(reversed(st.session_state.food_logs)):
                date_str = log.get("日期", f"紀錄 #{i+1}")
                m_type = log.get("餐別", "餐點")
                
                with st.expander(f"📅 {date_str} 【{m_type}】"):
                    st.markdown(log.get('內容', ''))