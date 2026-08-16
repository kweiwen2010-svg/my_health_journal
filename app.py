import os
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image

# 1. 頁面設定
st.set_page_config(page_title="AI 智慧營養師", page_icon="🥗", layout="centered")
st.title("🥗 AI 智慧營養與飲食記錄器")

# 2. 自動載入 API Key
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 找不到 Gemini API Key！請檢查 Streamlit Secrets 設定。")
    st.stop()
genai.configure(api_key=api_key)

# 3. 永久儲存設定 (CSV) 與 Session State 初始化
LOG_FILE = "food_log.csv"

if "food_logs" not in st.session_state:
    if os.path.exists(LOG_FILE):
        try:
            df = pd.read_csv(LOG_FILE)
            st.session_state.food_logs = df.to_dict("records")
        except:
            st.session_state.food_logs = []
    else:
        st.session_state.food_logs = []

# 初始化側欄基本資料的 session_state 預設值
if "user_age" not in st.session_state:
    st.session_state.user_age = 30
if "user_height" not in st.session_state:
    st.session_state.user_height = 170.0
if "user_weight" not in st.session_state:
    st.session_state.user_weight = 65.0
if "user_activity" not in st.session_state:
    st.session_state.user_activity = "久坐少動"
if "user_medical" not in st.session_state:
    st.session_state.user_medical = ""

# 4. 側邊欄：個人設定（綁定 session_state 確保不歸零）
st.sidebar.header("個人基本資料")
st.session_state.user_age = st.sidebar.slider("年齡", 10, 100, st.session_state.user_age)
st.session_state.user_height = st.sidebar.number_input("身高 (cm)", 100.0, 220.0, st.session_state.user_height)
st.session_state.user_weight = st.sidebar.number_input("體重 (kg)", 30.0, 150.0, st.session_state.user_weight)
st.session_state.user_activity = st.sidebar.selectbox(
    "運動狀態", 
    ["久坐少動", "輕度運動", "中度運動", "高度運動"], 
    index=["久坐少動", "輕度運動", "中度運動", "高度運動"].index(st.session_state.user_activity)
)
st.session_state.user_medical = st.sidebar.text_area("病史 / 飲食禁忌", st.session_state.user_medical)

# 5. 主畫面與拍照
tab1, tab2 = st.tabs(["📸 拍照分析", "📊 飲食日誌"])

with tab1:
    camera_file = st.camera_input("拍攝你的餐點")
    uploaded_file = st.file_uploader("或上傳照片", type=["jpg", "jpeg", "png"])
    image_to_process = camera_file or uploaded_file

    if image_to_process:
        image = Image.open(image_to_process)
        image.thumbnail((800, 800))  # 嚴格壓縮圖片尺寸
        if image.mode != 'RGB': 
            image = image.convert('RGB')
        
        st.image(image, caption="已載入餐點圖片", use_container_width=True)

        # 點擊按鈕進行分析
        if st.button("✨ 開始 AI 營養分析"):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = (
                    f"你是專業營養師。使用者背景：年齡 {st.session_state.user_age} 歲、"
                    f"身高 {st.session_state.user_height} cm、體重 {st.session_state.user_weight} kg、"
                    f"運動狀態：{st.session_state.user_activity}、病史/禁忌：「{st.session_state.user_medical}」。"
                    f"請分析此食物的名稱、份量、熱量與建議。"
                )
                with st.spinner("AI 正在分析..."):
                    response = model.generate_content([image, prompt])
                    st.session_state.last_analysis = response.text
            except Exception as e:
                st.error(f"分析失敗: {e}")

        # 當有分析結果時，顯示結果與「加入紀錄」按鈕
        if "last_analysis" in st.session_state:
            st.markdown("### 💡 分析結果")
            st.markdown(st.session_state.last_analysis)
            
            if st.button("➕ 將此餐點加入紀錄"):
                new_log = {
                    "日期": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                    "身高": st.session_state.user_height,
                    "體重": st.session_state.user_weight,
                    "病史": st.session_state.user_medical,
                    "內容": st.session_state.last_analysis
                }
                st.session_state.food_logs.append(new_log)
                
                # 寫入 CSV 檔案
                df_to_save = pd.DataFrame(st.session_state.food_logs)
                df_to_save.to_csv(LOG_FILE, index=False)
                
                # 清除暫存並提示
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
        # 讓最新紀錄顯示在最上方
        for i, log in enumerate(reversed(st.session_state.food_logs)):
            date_str = log.get("日期", f"紀錄 #{i+1}")
            content = log.get("內容") or log.get("details", str(log))
            
            with st.expander(f"📅 {date_str} (體重: {log.get('體重', 'N/A')}kg)"):
                st.markdown(content)