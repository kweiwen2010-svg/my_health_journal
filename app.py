import os
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image
from datetime import datetime
import re

# 1. 頁面設定
st.set_page_config(page_title="AI 智慧營養師", page_icon="🥗", layout="centered")
st.title("🥗 AI 智慧營養與飲食記錄器")

# 2. 自動載入 API Key
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 找不到 Gemini API Key！請檢查 Streamlit Secrets 設定。")
    st.stop()
genai.configure(api_key=api_key)

# 檔案儲存路徑
LOG_FILE = "food_log.csv"
PROFILE_FILE = "user_profile.csv"

# 初始化設定
if "food_logs" not in st.session_state:
    if os.path.exists(LOG_FILE):
        try:
            df = pd.read_csv(LOG_FILE)
            st.session_state.food_logs = df.to_dict("records")
        except:
            st.session_state.food_logs = []
    else:
        st.session_state.food_logs = []

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
    # 尋找熱量與三大營養素
    cal_match = re.search(r'(?:熱量|卡路里).*?(\d+(?:\.\d+)?)', text)
    if cal_match: calories = float(cal_match.group(1))
    pro_match = re.search(r'蛋白質.*?(\d+(?:\.\d+)?)', text)
    if pro_match: protein = float(pro_match.group(1))
    carb_match = re.search(r'(?:碳水化合物|碳水|澱粉).*?(\d+(?:\.\d+)?)', text)
    if carb_match: carbs = float(carb_match.group(1))
    fat_match = re.search(r'脂肪.*?(\d+(?:\.\d+)?)', text)
    if fat_match: fat = float(fat_match.group(1))
    return calories, protein, carbs, fat

# 側邊欄：個人資料
st.sidebar.header("個人基本資料")
st.session_state.user_age = st.sidebar.slider("年齡", 10, 100, value=30)
st.session_state.user_height = st.sidebar.number_input("身高 (cm)", 100.0, 220.0, value=170.0)
st.session_state.user_weight = st.sidebar.number_input("體重 (kg)", 30.0, 150.0, value=65.0)
st.session_state.user_activity = st.sidebar.selectbox("運動狀態", ["久坐少動", "輕度運動", "中度運動", "高度運動"])
st.session_state.user_medical = st.sidebar.text_area("病史 / 飲食禁忌")

# 主頁面
tab1, tab2, tab3, tab4 = st.tabs(["📸 拍照分析", "📊 飲食日誌", "✨ AI 智慧統整", "📈 歷史趨勢"])

with tab1:
    meal_type = st.selectbox("選擇餐別", ["早餐", "午餐", "晚餐", "點心"])
    
    # 圖片輸入
    camera_file = st.camera_input("拍攝餐點")
    uploaded_file = st.file_uploader("或上傳照片", type=["jpg", "jpeg", "png"])
    image_to_process = camera_file or uploaded_file
    
    # 新增補充說明
    supplement_text = st.text_area("💡 補充說明 (例如：兩人分食吃一半、飯後還有吃蘋果...)", placeholder="在此輸入未拍攝到的食物或分食比例...")

    if image_to_process:
        image = Image.open(image_to_process)
        if st.button("✨ 開始 AI 營養分析"):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = (
                    f"你是專業營養師。這是一份【{meal_type}】的餐點分析。\n"
                    f"照片中的主餐：{meal_type}。\n"
                    f"使用者補充說明：{supplement_text}\n"
                    f"請綜合【照片內容】與【補充說明】進行分析。如果補充說明提到分食，請自動折算攝取量；如果提到額外食物，請一併加總。\n"
                    f"請在回覆的最上方包含以下格式的總結：\n"
                    f"- 熱量: [數字] 大卡\n- 蛋白質: [數字] g\n- 碳水化合物: [數字] g\n- 脂肪: [數字] g\n"
                    f"之後再給予詳細建議。"
                )
                with st.spinner("AI 正在根據補充資訊綜合計算..."):
                    response = model.generate_content([image, prompt])
                    st.session_state.last_analysis = response.text
                    st.session_state.analyzed_meal_type = meal_type
            except Exception as e:
                st.error(f"分析失敗: {e}")

    if "last_analysis" in st.session_state:
        st.markdown("### 💡 分析結果")
        st.markdown(st.session_state.last_analysis)
        if st.button("➕ 確認加入紀錄"):
            cal, pro, carb, fat = extract_nutrition_values(st.session_state.last_analysis)
            new_log = {
                "日期": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "餐別": st.session_state.analyzed_meal_type,
                "體重": st.session_state.user_weight,
                "內容": st.session_state.last_analysis,
                "熱量": cal, "蛋白質": pro, "碳水化合物": carb, "脂肪": fat
            }
            st.session_state.food_logs.append(new_log)
            pd.DataFrame(st.session_state.food_logs).to_csv(LOG_FILE, index=False)
            st.success("紀錄已存入！")
            del st.session_state.last_analysis
            st.rerun()

# [其餘 Tab2, Tab3, Tab4 保持不變，因為邏輯依賴 df_logs，上述存入後會自動更新]
with tab2:
    st.subheader("我的飲食日誌")
    for log in reversed(st.session_state.food_logs):
        with st.expander(f"{log['日期']} - {log['餐別']}"):
            st.markdown(log['內容'])

with tab3:
    st.subheader("✨ 當日營養統整")
    if not st.session_state.food_logs: st.info("尚無記錄")
    else:
        df = pd.DataFrame(st.session_state.food_logs)
        st.metric("今日攝取熱量", df[pd.to_datetime(df['日期']).dt.date == datetime.today().date()]['熱量'].sum())

with tab4:
    st.subheader("📈 長期趨勢")
    if st.session_state.food_logs:
        df = pd.DataFrame(st.session_state.food_logs)
        df['date'] = pd.to_datetime(df['日期']).dt.date
        st.line_chart(df.groupby('date')[['熱量', '蛋白質', '碳水化合物', '脂肪']].sum())