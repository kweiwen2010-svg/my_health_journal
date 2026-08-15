import io
import os
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image

# 1. 頁面設定
st.set_page_config(
    page_title="AI 智慧營養師", page_icon="🥗", layout="centered"
)

st.title("🥗 AI 智慧營養與飲食記錄器")

# 2. 自動載入 API Key（支援 Streamlit Secrets 與本地環境變數）
api_key = None
try:
    # 嘗試從 Streamlit Cloud 的 secrets 讀取
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    # 如果沒有，則從本機環境變數讀取
    api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    st.error(
        "❌ 找不到 Gemini API Key！請確認已在 Streamlit 後台設定 Secrets，或於本機設定環境變數。"
    )
    st.stop()

# 設定 Google GenAI
genai.configure(api_key=api_key)


# 3. 初始化個人資料的 Session State (如果沒有就給預設值)
if "profile" not in st.session_state:
    st.session_state.profile = {
        "age": 30,
        "height": 170.0,
        "weight": 65.0,
        "activity": "久坐少動 (Little/no exercise)",
        "medical_history": "無",
    }

# 4. 側邊欄：使用者基本資料設定 (從 session_state 讀取預設值)
st.sidebar.header("個人基本資料")

# 讓輸入框綁定目前的狀態
age = st.sidebar.slider(
    "年齡", 10, 100, st.session_state.profile["age"]
)
height = st.sidebar.number_input(
    "身高 (cm)", 100.0, 220.0, st.session_state.profile["height"]
)
weight = st.sidebar.number_input(
    "體重 (kg)", 30.0, 150.0, st.session_state.profile["weight"]
)

activity_options = [
    "久坐少動 (Little/no exercise)",
    "輕度運動 (Light exercise)",
    "中度運動 (Moderate exercise)",
    "高度運動 (Heavy exercise)",
]
default_activity_idx = activity_options.index(
    st.session_state.profile["activity"]
)
activity = st.sidebar.selectbox(
    "運動狀態", activity_options, index=default_activity_idx
)

medical_history = st.sidebar.text_area(
    "病史 / 飲食禁忌", value=st.session_state.profile["medical_history"]
)

# 儲存按鈕
if st.sidebar.button("💾 儲存我的個人設定"):
    st.session_state.profile = {
        "age": age,
        "height": height,
        "weight": weight,
        "activity": activity,
        "medical_history": medical_history,
    }
    st.sidebar.success("個人資料已儲存！")

# 5. 初始化 Session State 記錄當日飲食
if "food_logs" not in st.session_state:
    st.session_state.food_logs = []

# 6. 主畫面分頁
tab1, tab2 = st.tabs(["📸 拍照記錄飲食", "📊 今日營養清單與建議"])

with tab1:
    st.subheader("使用手機相機或上傳照片分析食物")

    camera_file = st.camera_input("拍攝你的餐點")
    uploaded_file = st.file_uploader(
        "或者上傳食物照片", type=["jpg", "jpeg", "png"]
    )

    image_to_process = camera_file if camera_file else uploaded_file

    if image_to_process:
        # 讀取圖片並進行更嚴格的壓縮與調整大小
        image = Image.open(image_to_process)
        # 將畫質降至 800x800，並轉為 RGB 模式（確保相容性）
        image.thumbnail((800, 800))
        if image.mode != 'RGB':
            image = image.convert('RGB')

        st.image(image, caption="準備分析的餐點", use_container_width=True)

        if st.button("✨ 開始 AI 營養分析", type="primary"):
            try:
                # 使用支援多模態的最新模型
                model = genai.GenerativeModel("gemini-2.5-flash")

                prompt = f"""
                你是一個專業營養師。請分析這張照片中的食物：
                1. 辨識食物名稱與預估份量。
                2. 估算總熱量 (大卡)、蛋白質 (g)、脂肪 (g)、碳水化合物 (g)。
                3. 考慮使用者的病史：「{medical_history}」，給予這道菜的適宜度評語與健康建議。
                
                請以繁體中文回答，並使用清晰的條列式呈現。
                """

                with st.spinner("AI 正在分析食物營養成分中..."):
                    response = model.generate_content([image, prompt])

                st.success("分析完成！")
                st.markdown(response.text)

                # 加入今日記錄按鈕
                if st.button("➕ 將此餐點加入今日記錄"):
                    st.session_state.food_logs.append(
                        {
                            "details": response.text,
                        }
                    )
                    st.success("已成功加入記錄！")

            except Exception as e:
                st.error(
                    f"分析失敗，請檢查網路連線或 API 金鑰權限。錯誤訊息: {e}"
                )

with tab2:
    st.subheader("今日飲食日誌")
    if not st.session_state.food_logs:
        st.info("今天還沒有記錄任何餐點，快去拍張照吧！")
    else:
        for i, log in enumerate(st.session_state.food_logs):
            with st.expander(f"餐點紀錄 #{i+1}"):
                st.markdown(log["details"])

        if st.button("🗑️ 清空今日記錄"):
            st.session_state.food_logs = []
            st.rerun()