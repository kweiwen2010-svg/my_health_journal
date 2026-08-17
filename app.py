import os
import google.generativeai as genai
import pandas as pd
import streamlit as st
from PIL import Image
from datetime import datetime

# 1. 頁面設定
st.set_page_config(page_title="AI 智慧營養師", page_icon="🥗", layout="centered")
st.title("🥗 AI 智慧營養與飲食記錄器")

# 2. 自動載入 API Key
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 找不到 Gemini API Key！請檢查 Streamlit Secrets 設定。")
    st.stop()
genai.configure(api_key=api_key)

# 3. 檔案儲存路徑設定
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

# 【升級關鍵】初始化個人資料：優先從 CSV 讀取，沒有的話才用預設值
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

# 若讀取後仍無數值，給予預設值
if "user_age" not in st.session_state: st.session_state.user_age = 30
if "user_height" not in st.session_state: st.session_state.user_height = 170.0
if "user_weight" not in st.session_state: st.session_state.user_weight = 65.0
if "user_activity" not in st.session_state: st.session_state.user_activity = "久坐少動"
if "user_medical" not in st.session_state: st.session_state.user_medical = ""
if "selected_meal_type" not in st.session_state: st.session_state.selected_meal_type = "午餐"

def save_profile():
    """將目前的個人資料寫入 CSV 永久保存"""
    profile_data = [{
        "年齡": st.session_state.user_age,
        "身高": st.session_state.user_height,
        "體重": st.session_state.user_weight,
        "運動狀態": st.session_state.user_activity,
        "病史": st.session_state.user_medical
    }]
    pd.DataFrame(profile_data).to_csv(PROFILE_FILE, index=False)

# 4. 側邊欄：個人設定（每當數值改變時，自動呼叫 save_profile 存檔）
st.sidebar.header("個人基本資料")
st.session_state.user_age = st.sidebar.slider("年齡", 10, 100, value=st.session_state.user_age, on_change=save_profile)
st.session_state.user_height = st.sidebar.number_input("身高 (cm)", 100.0, 220.0, value=st.session_state.user_height, on_change=save_profile)
st.session_state.user_weight = st.sidebar.number_input("體重 (kg)", 30.0, 150.0, value=st.session_state.user_weight, on_change=save_profile)

activity_list = ["久坐少動", "輕度運動", "中度運動", "高度運動"]
current_act_idx = activity_list.index(st.session_state.user_activity) if st.session_state.user_activity in activity_list else 0
st.session_state.user_activity = st.sidebar.selectbox("運動狀態", activity_list, index=current_act_idx, on_change=save_profile)

st.session_state.user_medical = st.sidebar.text_area("病史 / 飲食禁忌", value=st.session_state.user_medical)
if st.sidebar.button("💾 儲存個人資料"):
    save_profile()
    st.sidebar.success("個人資料已永久儲存！")

# 5. 主畫面分頁：加入第三階段的「📊 當日統整與建議」
tab1, tab2, tab3 = st.tabs(["📸 拍照分析", "📊 飲食日誌", "✨ AI 智慧統整"])

with tab1:
    meal_list = ["早餐", "午餐", "晚餐", "點心"]
    current_meal_idx = meal_list.index(st.session_state.selected_meal_type) if st.session_state.selected_meal_type in meal_list else 1
    current_meal_type = st.selectbox("選擇餐別", meal_list, index=current_meal_idx)
    st.session_state.selected_meal_type = current_meal_type

    camera_file = st.camera_input("拍攝你的餐點")
    uploaded_file = st.file_uploader("或上傳照片", type=["jpg", "jpeg", "png"])
    image_to_process = camera_file or uploaded_file

    if image_to_process:
        image = Image.open(image_to_process)
        image.thumbnail((800, 800))  # 嚴格壓縮圖片尺寸
        if image.mode != 'RGB': 
            image = image.convert('RGB')
        
        st.image(image, caption=f"已載入 {current_meal_type} 餐點圖片", use_container_width=True)

        # 點擊按鈕進行分析
        if st.button("✨ 開始 AI 營養分析"):
            try:
                model = genai.GenerativeModel("gemini-2.5-flash")
                prompt = (
                    f"你是專業營養師。這是一份【{current_meal_type}】的餐點。"
                    f"使用者背景：年齡 {st.session_state.user_age} 歲、"
                    f"身高 {st.session_state.user_height} cm、體重 {st.session_state.user_weight} kg、"
                    f"運動狀態：{st.session_state.user_activity}、病史/禁忌：「{st.session_state.user_medical}」。"
                    f"請分析此食物的名稱、份量、預估熱量、以及三大營養素（蛋白質、碳水化合物/澱粉、脂肪）的大致克數，並給予專業建議。"
                )
                with st.spinner("AI 正在分析..."):
                    response = model.generate_content([image, prompt])
                    st.session_state.last_analysis = response.text
                    st.session_state.analyzed_meal_type = current_meal_type
            except Exception as e:
                st.error(f"分析失敗: {e}")

        # 當有分析結果時，顯示結果與「加入紀錄」按鈕
        if "last_analysis" in st.session_state:
            active_meal = st.session_state.get('analyzed_meal_type', current_meal_type)
            st.markdown(f"### 💡 【{active_meal}】分析結果")
            st.markdown(st.session_state.last_analysis)
            
            if st.button("➕ 將此餐點加入紀錄"):
                new_log = {
                    "日期": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
                    "餐別": active_meal,
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
                if "analyzed_meal_type" in st.session_state:
                    del st.session_state.analyzed_meal_type
                
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
            
            raw_m_type = log.get("餐別")
            m_type = raw_m_type if pd.notna(raw_m_type) else "餐點"
            
            raw_weight = log.get("體重")
            w_str = f"{raw_weight}kg" if pd.notna(raw_weight) else "N/A"
            
            with st.expander(f"📅 {date_str} - 【{m_type}】 (體重: {w_str})"):
                st.markdown(log.get("內容", ""))

with tab3:
    st.subheader("✨ 當日飲食統整與 AI 智慧建議")
    
    selected_date = st.date_input("選擇要統整的日期", value=datetime.today().date())
    
    if not st.session_state.food_logs:
        st.info("目前尚無任何飲食紀錄，請先至「拍照分析」新增紀錄！")
    else:
        # 將 food_logs 轉為 DataFrame 並過濾選定日期的紀錄
        df_logs = pd.DataFrame(st.session_state.food_logs)
        # 假設日期格式為 'YYYY-MM-DD HH:MM'，擷取前 10 碼作為 'YYYY-MM-DD'
        df_logs['only_date'] = pd.to_datetime(df_logs['日期']).dt.date
        target_df = df_logs[df_logs['only_date'] == selected_date]
        
        if target_df.empty:
            st.warning(f"📅 找不到 {selected_date} 的飲食紀錄。")
        else:
            st.success(f"找到 {selected_date} 共 {len(target_df)} 筆餐點紀錄：")
            
            # 條列顯示當日各餐點摘要
            for idx, row in target_df.iterrows():
                with st.expander(f"🕒 {row['日期']} - 【{row['餐別']}】"):
                    st.markdown(row['內容'])
            
            st.divider()
            
            # 點擊按鈕讓 Gemini 進行綜合分析
            if st.button("🚀 執行 Gemini 綜合營養分析與建議"):
                try:
                    model = genai.GenerativeModel("gemini-2.5-flash")
                    
                    # 組合當日所有飲食細節
                    meals_summary_text = ""
                    for idx, row in target_df.iterrows():
                        meals_summary_text += f"\n--- 【{row['餐別']} ({row['日期']})】 ---\n{row['content'] if 'content' in row else row['內容']}\n"
                    
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
                        f"1. 今日整體熱量與三大營養素（蛋白質、碳水化合物、脂肪）的綜合評估\n"
                        f"2. 優勢與需要改進的地方\n"
                        f"3. 針對接下來的晚餐或明天的具體飲食調整建議（語氣請溫暖、專業、具體）"
                    )
                    
                    with st.spinner("Gemini 正在為您統整今日營養狀況..."):
                        summary_response = model.generate_content(summary_prompt)
                        st.markdown("### 📋 AI 智慧統整報告")
                        st.markdown(summary_response.text)
                except Exception as e:
                    st.error(f"統整分析失敗: {e}")