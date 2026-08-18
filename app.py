import os
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image
from datetime import datetime
import re

# 1. 頁面設定 (保持不變)
st.set_page_config(page_title="AI 智慧營養師", page_icon="🥗", layout="centered")
st.title("🥗 AI 智慧營養與飲食記錄器")

# 2. 自動載入 API Key (保持不變)
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 找不到 Gemini API Key！請檢查 Streamlit Secrets 設定。")
    st.stop()
genai.configure(api_key=api_key)

# 3. 檔案儲存路徑 (保持不變)
LOG_FILE = "food_log.csv"
PROFILE_FILE = "user_profile.csv"

# 初始化飲食日誌 (保持不變)
if "food_logs" not in st.session_state:
    if os.path.exists(LOG_FILE):
        try:
            df = pd.read_csv(LOG_FILE)
            st.session_state.food_logs = df.to_dict("records")
        except:
            st.session_state.food_logs = []
    else:
        st.session_state.food_logs = []

# 初始化個人資料 (保持不變)
if "profile_loaded" not in st.session_state:
    if os.path.exists(PROFILE_FILE):
        try:
            profile_df = pd.read_csv(PROFILE_FILE)
            if not profile_df.empty:
                row = profile_df.iloc[0]
                st.session_state.user_age = int(row.get("年齡", 30))
                st.session_state.user_height = float(row.get("身高", 170.0))
                st.session_state.user_weight = float(row.get("體重", 65.0))
                st.session_state.user_activity = str(row.get("運動狀態", "久坐少動"))
                st.session_state.user_medical = str(row.get("病史", "")) if pd.notna(row.get("病史")) else ""
        except:
            pass
    st.session_state.profile_loaded = True

# 預設值 (保持不變)
if "user_age" not in st.session_state: st.session_state.user_age = 30
if "user_height" not in st.session_state: st.session_state.user_height = 170.0
if "user_weight" not in st.session_state: st.session_state.user_weight = 65.0
if "user_activity" not in st.session_state: st.session_state.user_activity = "久坐少動"
if "user_medical" not in st.session_state: st.session_state.user_medical = ""
if "selected_meal_type" not in st.session_state: st.session_state.selected_meal_type = "午餐"

def save_profile():
    profile_data = [{
        "年齡": st.session_state.user_age,
        "身高": st.session_state.user_height,
        "體重": st.session_state.user_weight,
        "運動狀態": st.session_state.user_activity,
        "病史": st.session_state.user_medical
    }]
    pd.DataFrame(profile_data).to_csv(PROFILE_FILE, index=False)

def extract_nutrition_values(text):
    calories, protein, carbs, fat = 0.0, 0.0, 0.0, 0.0
    cal_match = re.search(r'(?:熱量|卡路里).*?(\d+(?:\.\d+)?)', text)
    if cal_match: calories = float(cal_match.group(1))
    pro_match = re.search(r'蛋白質.*?(\d+(?:\.\d+)?)', text)
    if pro_match: protein = float(pro_match.group(1))
    carb_match = re.search(r'(?:碳水化合物|碳水|澱粉).*?(\d+(?:\.\d+)?)', text)
    if carb_match: carbs = float(carb_match.group(1))
    fat_match = re.search(r'脂肪.*?(\d+(?:\.\d+)?)', text)
    if fat_match: fat = float(fat_match.group(1))
    return calories, protein, carbs, fat

# 側邊欄 (完全恢復原樣)
st.sidebar.header("個人基本資料")
st.session_state.user_age = st.sidebar.slider("年齡", 10, 100, value=st.session_state.user_age, on_change=save_profile)
st.session_state.user_height = st.sidebar.number_input("身高 (cm)", 100.0, 220.0, value=st.session_state.user_height, on_change=save_profile)
st.session_state.user_weight = st.sidebar.number_input("體重 (kg)", 30.0, 150.0, value=st.session_state.user_weight, on_change=save_profile)
activity_list = ["久坐少動", "輕度運動", "中度運動", "高度運動"]
st.session_state.user_activity = st.sidebar.selectbox("運動狀態", activity_list, index=activity_list.index(st.session_state.user_activity) if st.session_state.user_activity in activity_list else 0, on_change=save_profile)
st.session_state.user_medical = st.sidebar.text_area("病史 / 飲食禁忌", value=st.session_state.user_medical)
if st.sidebar.button("💾 儲存個人資料"):
    save_profile()
    st.sidebar.success("個人資料已永久儲存！")

# 主畫面分頁
tab1, tab2, tab3, tab4 = st.tabs(["📸 拍照分析", "📊 飲食日誌", "✨ AI 智慧統整", "📈 歷史趨勢"])

with tab1:
    meal_list = ["早餐", "午餐", "晚餐", "點心"]
    current_meal_type = st.selectbox("選擇餐別", meal_list, index=meal_list.index(st.session_state.selected_meal_type))
    st.session_state.selected_meal_type = current_meal_type

    camera_file = st.camera_input("拍攝你的餐點")
    uploaded_file = st.file_uploader("或上傳照片", type=["jpg", "jpeg", "png"])
    
    # --- 【新增部分：僅在此處加入說明框】 ---
    supplement_text = st.text_area("💡 補充說明 (例如：分食比例、飯後水果等)", placeholder="輸入未拍攝到的食物或分食份量...")
    # --------------------------------------

    image_to_process = camera_file or uploaded_file

    if image_to_process:
        image = Image.open(image_to_process)
        image.thumbnail((800, 800))
        if image.mode != 'RGB': image = image.convert('RGB')
        st.image(image, caption=f"已載入 {current_meal_type} 餐點圖片", use_container_width=True)

        if st.button("✨ 開始 AI 營養分析"):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                # --- 【新增部分：在 Prompt 加入說明資訊】 ---
                prompt = (
                    f"你是專業營養師。這是一份【{current_meal_type}】的餐點。\n"
                    f"使用者補充資訊：{supplement_text}\n" # 加入這行
                    f"請分析此食物，若補充資訊提到分食請折算，提到水果等請一併加總。\n"
                    f"務必包含以下格式總結：\n"
                    f"- 熱量: [數字] 大卡\n- 蛋白質: [數字] g\n- 碳水化合物: [數字] g\n- 脂肪: [數字] g\n"
                )
                # ----------------------------------------
                with st.spinner("AI 正在分析..."):
                    response = model.generate_content([image, prompt])
                    st.session_state.last_analysis = response.text
                    st.session_state.analyzed_meal_type = current_meal_type
            except Exception as e:
                st.error(f"分析失敗: {e}")

        if "last_analysis" in st.session_state:
            st.markdown(f"### 💡 【{st.session_state.get('analyzed_meal_type')}】分析結果")
            st.markdown(st.session_state.last_analysis)
            if st.button("➕ 將此餐點加入紀錄"):
                cal, pro, carb, fat = extract_nutrition_values(st.session_state.last_analysis)
                new_log = {
                    "日期": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                    "餐別": st.session_state.analyzed_meal_type,
                    "身高": st.session_state.user_height,
                    "體重": st.session_state.user_weight,
                    "病史": st.session_state.user_medical,
                    "內容": st.session_state.last_analysis,
                    "熱量": cal, "蛋白質": pro, "碳水化合物": carb, "脂肪": fat
                }
                st.session_state.food_logs.append(new_log)
                pd.DataFrame(st.session_state.food_logs).to_csv(LOG_FILE, index=False)
                st.success("紀錄已存入！")
                st.rerun()

# [其餘 Tab2, Tab3, Tab4 保持你之前的版本邏輯完全不變]
with tab2:
    st.subheader("我的飲食日誌")
    if st.button("🗑️ 清空所有紀錄"):
        st.session_state.food_logs = []
        if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
        st.rerun()
    for log in reversed(st.session_state.food_logs):
        with st.expander(f"📅 {log.get('日期')} - 【{log.get('餐別')}】"):
            st.markdown(log.get("內容", ""))

with tab3:
    st.subheader("✨ 當日飲食統整")
    selected_date = st.date_input("選擇日期", value=datetime.today().date())
    df = pd.DataFrame(st.session_state.food_logs)
    if not df.empty:
        df['only_date'] = pd.to_datetime(df['日期']).dt.date
        target = df[df['only_date'] == selected_date]
        st.write(f"今日共 {len(target)} 筆紀錄")

with tab4:
    st.subheader("📈 長期歷史趨勢")
    if st.session_state.food_logs:
        df = pd.DataFrame(st.session_state.food_logs)
        df['date_str'] = pd.to_datetime(df['日期']).dt.strftime('%Y-%m-%d')
        st.line_chart(df.groupby('date_str')[['熱量', '蛋白質', '碳水化合物', '脂肪']].sum())