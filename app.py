import os
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image
from datetime import datetime
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. 頁面設定
st.set_page_config(page_title="AI 智慧營養師", page_icon="🥗", layout="centered")
st.title("🥗 AI 智慧營養與飲食記錄器 (雲端同步版)")

# 2. 自動載入 API Key
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 找不到 Gemini API Key！請檢查 Streamlit Secrets 設定。")
    st.stop()
genai.configure(api_key=api_key)

# 3. Google Sheets 雲端連線設定
SHEET_NAME = "health"  # 對應你建立的 Google 試算表名稱

@st.cache_resource
def init_gspread():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    # 讀取當前資料夾下的 json 憑證檔案
    json_files = [f for f in os.listdir(".") if f.endswith(".json") and "health-" in f]
    if not json_files:
        st.error("❌ 找不到 Google Service Account JSON 憑證檔案！")
        st.stop()
    
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_files[0], scope)
    client = gspread.authorize(creds)
    return client

try:
    gc = init_gspread()
    sheet = gc.open(SHEET_NAME).sheet1
except Exception as e:
    st.error(f"❌ Google Sheets 連線失敗，請檢查共用設定或檔名是否正確：{e}")
    st.stop()

# 初始化飲食日誌 (從 Google Sheets 載入)
if "food_logs" not in st.session_state:
    try:
        data = sheet.get_all_records()
        st.session_state.food_logs = data if data else []
    except Exception:
        st.session_state.food_logs = []

def save_logs_to_cloud():
    """將目前的 food_logs 同步寫回 Google Sheets"""
    try:
        sheet.clear()
        if st.session_state.food_logs:
            df_temp = pd.DataFrame(st.session_state.food_logs)
            # 寫入標題與資料
            sheet.update([df_temp.columns.values.tolist()] + df_temp.values.tolist())
        else:
            # 若為空則保留表頭
            sheet.update([["日期", "餐別", "身高", "體重", "病史", "內容", "熱量", "蛋白質", "碳水化合物", "脂肪"]])
    except Exception as e:
        st.warning(f"⚠️ 雲端同步失敗: {e}")

# 初始化個人資料預設值
if "user_age" not in st.session_state: st.session_state.user_age = 30
if "user_height" not in st.session_state: st.session_state.user_height = 170.0
if "user_weight" not in st.session_state: st.session_state.user_weight = 65.0
if "user_activity" not in st.session_state: st.session_state.user_activity = "久坐少動"
if "user_medical" not in st.session_state: st.session_state.user_medical = ""
if "selected_meal_type" not in st.session_state: st.session_state.selected_meal_type = "午餐"

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

# 側邊欄
st.sidebar.header("個人基本資料")
st.session_state.user_age = st.sidebar.slider("年齡", 10, 100, value=st.session_state.user_age)
st.session_state.user_height = st.sidebar.number_input("身高 (cm)", 100.0, 220.0, value=st.session_state.user_height)
st.session_state.user_weight = st.sidebar.number_input("體重 (kg)", 30.0, 150.0, value=st.session_state.user_weight)
activity_list = ["久坐少動", "輕度運動", "中度運動", "高度運動"]
st.session_state.user_activity = st.sidebar.selectbox("運動狀態", activity_list, index=activity_list.index(st.session_state.user_activity) if st.session_state.user_activity in activity_list else 0)
st.session_state.user_medical = st.sidebar.text_area("病史 / 飲食禁忌", value=st.session_state.user_medical)

# 主畫面分頁
tab1, tab2, tab3, tab4 = st.tabs(["📸 拍照分析", "📊 飲食日誌", "✨ AI 智慧統整", "📈 歷史趨勢"])

with tab1:
    meal_list = ["早餐", "午餐", "晚餐", "點心"]
    current_meal_type = st.selectbox("選擇餐別", meal_list, index=meal_list.index(st.session_state.selected_meal_type))
    st.session_state.selected_meal_type = current_meal_type

    camera_file = st.camera_input("拍攝你的餐點")
    uploaded_file = st.file_uploader("或上傳照片", type=["jpg", "jpeg", "png"])
    
    supplement_text = st.text_area("💡 補充說明 (例如：分食比例、飯後水果等)", placeholder="輸入未拍攝到的食物或分食份量...")

    image_to_process = camera_file or uploaded_file

    if image_to_process:
        image = Image.open(image_to_process)
        image.thumbnail((800, 800))
        if image.mode != 'RGB': image = image.convert('RGB')
        st.image(image, caption=f"已載入 {current_meal_type} 餐點圖片", use_container_width=True)

        if st.button("✨ 開始 AI 營養分析"):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = (
                    f"你是專業營養師。這是一份【{current_meal_type}】的餐點。\n"
                    f"使用者補充資訊：{supplement_text}\n"
                    f"請分析此食物，若補充資訊提到分食請折算，提到水果等請一併加總。\n"
                    f"務必包含以下格式總結：\n"
                    f"- 熱量: [數字] 大卡\n- 蛋白質: [數字] g\n- 碳水化合物: [數字] g\n- 脂肪: [數字] g\n"
                )
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
                save_logs_to_cloud()  # 同步寫入 Google Sheets
                st.success("紀錄已成功同步至雲端！")
                st.rerun()

with tab2:
    st.subheader("我的飲食日誌")
    if st.button("🗑️ 清空所有紀錄"):
        st.session_state.food_logs = []
        save_logs_to_cloud()
        st.rerun()
    if not st.session_state.food_logs:
        st.info("目前尚無任何飲食紀錄，快去拍照上傳開始記錄吧！")
    else:
        for i, log in enumerate(reversed(st.session_state.food_logs)):
            date_str = log.get("日期", f"紀錄 #{i+1}")
            m_type = log.get("餐別", "餐點")
            w_str = f"{log.get('體重')}kg" if pd.notna(log.get("體重")) else "N/A"
            with st.expander(f"📅 {date_str} - 【{m_type}】 (體重: {w_str})"):
                st.markdown(log.get("內容", ""))

with tab3:
    st.subheader("✨ 當日飲食統整與 AI 視覺化建議")
    selected_date = st.date_input("選擇要統整的日期", value=datetime.today().date(), key="summary_date")
    
    if not st.session_state.food_logs:
        st.info("目前尚無任何飲食紀錄，請先至「拍照分析」新增紀錄！")
    else:
        df_logs = pd.DataFrame(st.session_state.food_logs)
        df_logs['only_date'] = pd.to_datetime(df_logs['日期']).dt.date
        target_df = df_logs[df_logs['only_date'] == selected_date]
        
        if target_df.empty:
            st.warning(f"📅 找不到 {selected_date} 的飲食紀錄。")
        else:
        ...

with tab4:
    st.subheader("📈 長期歷史趨勢與每日營養加總追蹤")
    if not st.session_state.food_logs:
        st.info("目前尚無足夠的歷史資料可供繪製趨勢圖，快去記錄幾天看看吧！")
    else:
        df_history = pd.DataFrame(st.session_state.food_logs)
        df_history['datetime'] = pd.to_datetime(df_history['日期'])
        df_history['date_str'] = df_history['datetime'].dt.strftime('%Y-%m-%d')
        for col in ['熱量', '蛋白質', '碳水化合物', '脂肪', '體重']:
            if col not in df_history.columns:
                df_history[col] = 0.0

        st.markdown("### 🔥 每日熱量攝取總計 (kcal)")
        cal_daily = df_history.groupby('date_str')['熱量'].sum().reset_index().set_index('date_str')
        st.line_chart(cal_daily, color="#ff7043")
        st.divider()
        
        st.markdown("### 🧬 每日三大營養素總計 (克 / g)")
        nutrients_daily = df_history.groupby('date_str')[['蛋白質', '碳水化合物', '脂肪']].sum().reset_index().set_index('date_str')
        st.line_chart(nutrients_daily)
        st.divider()
        
        st.markdown("### ⚖️ 每日體重變化趨勢 (kg)")
        weight_daily = df_history.groupby('date_str')['體重'].mean().reset_index().set_index('date_str')
        st.line_chart(weight_daily, color="#29b6f6")