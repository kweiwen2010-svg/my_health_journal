import os
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image
from datetime import datetime
import re
import sqlite3

# 1. 頁面設定
st.set_page_config(page_title="AI 智慧營養師", page_icon="🥗", layout="centered")
st.title("🥗 AI 智慧營養與飲食記錄器")

# 2. 自動載入 API Key
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 找不到 Gemini API Key！請檢查 Streamlit Secrets 設定。")
    st.stop()
genai.configure(api_key=api_key)

# ... (原本的 API 設定程式碼) ...
genai.configure(api_key=api_key)

# ⬇️ 請直接貼在這裡
model = genai.GenerativeModel('gemini-3.6-flash')
# --- 新增的 SQLite 機制 ---
def init_db():
    conn = sqlite3.connect("food_data.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS food_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  date TEXT, meal_type TEXT, content TEXT, 
                  calories REAL, protein REAL, carbs REAL, fat REAL, 
                  weight REAL, medical TEXT)''')
    conn.commit()
    conn.close()

def save_to_db(log):
    conn = sqlite3.connect("food_data.db")
    c = conn.cursor()
    c.execute("INSERT INTO food_logs (date, meal_type, content, calories, protein, carbs, fat, weight, medical) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
              (log["日期"], log["餐別"], log["內容"], log["熱量"], log["蛋白質"], log["碳水化合物"], log["脂肪"], log.get("體重"), log.get("病史")))
    conn.commit()
    conn.close()

init_db() # 執行一次初始化
# -------------------------

# 3. 檔案儲存路徑
LOG_FILE = "food_log.csv"
PROFILE_FILE = "user_profile.csv"

# 初始化飲食日誌
if "food_logs" not in st.session_state:
    if os.path.exists(LOG_FILE):
        try:
            df = pd.read_csv(LOG_FILE)
            st.session_state.food_logs = df.to_dict("records")
        except:
            st.session_state.food_logs = []
    else:
        st.session_state.food_logs = []

# 初始化個人資料
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

# 預設值
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

# 側邊欄
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
    
    # 保留你想要的補充說明框
    supplement_text = st.text_area("💡 補充說明 (例如：分食比例、飯後水果等)", placeholder="輸入未拍攝到的食物或分食份量...")

    image_to_process = camera_file or uploaded_file

    if image_to_process:
        image = Image.open(image_to_process)
        image.thumbnail((800, 800))
        if image.mode != 'RGB': image = image.convert('RGB')
        st.image(image, caption=f"已載入 {current_meal_type} 餐點圖片", use_container_width=True)

        if st.button("✨ 開始 AI 營養分析"):
            try:
                model = genai.GenerativeModel("gemini-3.6-flash")
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
                
                # --- 原本的存檔方式 ---
                pd.DataFrame(st.session_state.food_logs).to_csv(LOG_FILE, index=False)
                
                # --- 新增的同步備份 ---
                save_to_db(new_log)
                
                st.success("紀錄已存入！(並已同步至資料庫)")
                st.rerun()
with tab2:
    st.subheader("我的飲食日誌")
    if st.button("🗑️ 清空所有紀錄"):
        st.session_state.food_logs = []
        if os.path.exists(LOG_FILE): os.remove(LOG_FILE)
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
            st.success(f"找到 {selected_date} 共 {len(target_df)} 筆餐點紀錄：")
            for idx, row in target_df.iterrows():
                with st.expander(f"🕒 {row['日期']} - 【{row['餐別']}】"):
                    st.markdown(row['內容'])
            
            st.divider()
            st.markdown("### 📊 當日營養攝取視覺化指標")
            ref_calories = 2400
            col_v1, col_v2, col_v3 = st.columns(3)
            col_v1.metric("今日記錄餐數", f"{len(target_df)} 餐")
            col_v2.metric("參考建議熱量", f"{ref_calories} kcal")
            col_v3.metric("狀態提示", "需加強營養攝取" if len(target_df) < 3 else "紀錄完整")
            
            st.markdown("🎯 **全日紀錄完整度指標**")
            st.progress(min(len(target_df) / 4.0, 1.0), text=f"已記錄 {len(target_df)} / 4 餐 (早/午/晚/點心)")
            st.divider()
            
            if st.button("🚀 執行 Gemini 綜合營養分析與視覺化建議"):
                try:
                    model = genai.GenerativeModel("gemini-3.6-flash")
                    meals_summary_text = ""
                    for idx, row in target_df.iterrows():
                        meals_summary_text += f"\n--- 【{row['餐別']} ({row['日期']})】 ---\n{row['內容']}\n"
                    
                    summary_prompt = (
                        f"你是一位專業營養師。請根據以下使用者今日 ({selected_date}) 的所有飲食紀錄內容，進行全日營養總結與評估。\n\n"
                        f"【使用者個人背景】\n"
                        f"- 年齡: {st.session_state.user_age} 歲\n"
                        f"- 身高: {st.session_state.user_height} cm\n"
                        f"- 體重: {st.session_state.user_weight} kg\n"
                        f"- 運動狀態: {st.session_state.user_activity}\n"
                        f"- 病史/禁忌: {st.session_state.user_medical}\n\n"
                        f"【今日各餐點詳細記錄】\n"
                        f"{meals_summary_text}\n\n"
                        f"請提供：\n"
                        f"1. 今日整體熱量與三大營養素（蛋白質、碳水化合物、脂肪）的綜合評估與數據推估\n"
                        f"2. 優勢與需要改進的地方\n"
                        f"3. 針對接下來的晚餐或明天的具體飲食調整建議（語氣請溫暖、專業、具體）"
                    )
                    with st.spinner("Gemini 正在為您統整今日營養狀況與圖表解析..."):
                        summary_response = model.generate_content(summary_prompt)
                        st.markdown("### 📋 AI 智慧統整報告")
                        st.markdown(summary_response.text)
                except Exception as e:
                    st.error(f"統整分析失敗: {e}")

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