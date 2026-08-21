import os
import sqlite3
import re
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
    .stButton>button { width: 100% !important; border-radius: 20px !important; background-color: #2ecc71 !important; color: white !important; font-weight: bold !important; }
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
model = genai.GenerativeModel("gemini-3.6-flash")

def init_db():
    conn = sqlite3.connect("food_data.db")
    c = conn.cursor()
    # 建立或升級 food_logs 表，加入營養素欄位
    c.execute("""CREATE TABLE IF NOT EXISTS food_logs (
                 id INTEGER PRIMARY KEY AUTOINCREMENT, 
                 date TEXT, 
                 meal_type TEXT, 
                 content TEXT, 
                 weight REAL,
                 calories REAL,
                 protein REAL,
                 fat REAL,
                 carbs REAL)""")
    
    # 建立個人檔案表
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

# 簡單的數值解析輔助函數（從 AI 回傳文字中萃取數字）
def extract_nutrition(text):
    def find_num(pattern, string):
        match = re.search(pattern, string)
        if match:
            try:
                return float(match.group(1))
            except:
                return 0.0
        return 0.0

    calories = find_num(r'熱量[^\d]*(\d+\.?\d*)', text)
    protein = find_num(r'蛋白質[^\d]*(\d+\.?\d*)', text)
    fat = find_num(r'脂肪[^\d]*(\d+\.?\d*)', text)
    carbs = find_num(r'(?:碳水化合物|澱粉)[^\d]*(\d+\.?\d*)', text)
    return calories, protein, fat, carbs

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
        
        if st.form_submit_button("💾 儲存個人資料"):
            update_user_profile({"height": h_val, "weight": w_val, "age": a_val, "activity": act_val, "medical": med_val})
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
            with st.spinner("AI 正在精算熱量與三大營養素..."):
                try:
                    p = get_user_profile()
                    prompt = f"""
                    你是一位專業營養師。請根據以下用戶資料分析照片中的餐點：
                    - 用戶身型：{p['age']}歲, {p['height']}cm, {p['weight']}kg
                    - 運動狀態：{p['activity']}
                    - 健康備註/過敏源：{p['medical']}
                    - 用戶補充說明：{user_note}
                    
                    請務必在回答最上方嚴格依照以下格式列出數據（方便系統抓取）：
                    - 預估熱量：XXX 大卡
                    - 蛋白質：XX 克
                    - 脂肪：XX 克
                    - 碳水化合物/澱粉：XX 克
                    
                    接著評估：
                    1. 這份餐點是否適合該用戶目前的身體狀態與運動習慣？
                    2. 營養過剩或不足之處與優化建議。
                    """
                    response = model.generate_content([prompt, image])
                    st.session_state.last_analysis = response.text
                    st.markdown(response.text)
                except Exception as e:
                    st.error(f"❌ 分析失敗，錯誤訊息：{e}")

    if "last_analysis" in st.session_state and st.button("➕ 加入日誌"):
        cal, pro, fat, carb = extract_nutrition(st.session_state.last_analysis)
        current_weight = get_user_profile()['weight']
        
        conn = sqlite3.connect("food_data.db")
        c = conn.cursor()
        c.execute("""INSERT INTO food_logs (date, meal_type, content, weight, calories, protein, fat, carbs) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                  (datetime.now().strftime("%Y-%m-%d %H:%M"), meal_type, st.session_state.last_analysis, current_weight, cal, pro, fat, carb))
        conn.commit()
        conn.close()
        st.success("✅ 紀錄成功已存入日誌與趨勢分析庫！")
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
            with st.expander(f"📌 {row['date']} 【{row['meal_type']}】(🔥 {row.get('calories', 0)} 大卡)"):
                st.write(row['content'])

# ------------------------------------------
# TAB 3: AI 每日加總與分析
# ------------------------------------------
with tab3:
    st.subheader("🤖 AI 每日加總與綜合評估")
    conn = sqlite3.connect("food_data.db")
    df_logs = pd.read_sql("SELECT * FROM food_logs ORDER BY date DESC", conn)
    conn.close()
    
    if df_logs.empty:
        st.info("尚無飲食紀錄可供加總分析。")
    else:
        df_logs['day'] = df_logs['date'].str.split(' ').str[0]
        unique_days = df_logs['day'].unique()
        p = get_user_profile()
        
        for day in unique_days:
            day_records = df_logs[df_logs['day'] == day]
            total_cal = day_records['calories'].sum()
            total_pro = day_records['protein'].sum()
            total_fat = day_records['fat'].sum()
            total_carb = day_records['carbs'].sum()
            
            with st.expander(f"📅 日期：{day} | 總熱量: {total_cal}大卡"):
                st.markdown(f"**📊 當日營養小計**：蛋白質 {total_pro}g | 脂肪 {total_fat}g | 碳水/澱粉 {total_carb}g")
                st.divider()
                
                all_content = ""
                for _, r in day_records.iterrows():
                    st.markdown(f"**【{r['meal_type']}】({r['date']})**")
                    st.write(r['content'])
                    st.divider()
                    all_content += f"\n[{r['meal_type']}]: {r['content']}"
                
                if st.button(f"🔍 執行 {day} 每日營養加總分析", key=f"btn_{day}"):
                    with st.spinner("正在產生每日總結..."):
                        res = model.generate_content(f"營養師，請根據當日紀錄與背景 {p} 做總結：{all_content}")
                        st.markdown(res.text)

# ------------------------------------------
# TAB 4: 歷史趨勢 (新增每日熱量、營養素與體重圖表)
# ------------------------------------------
with tab4:
    st.subheader("📈 每日健康與營養趨勢圖")
    conn = sqlite3.connect("food_data.db")
    df_logs = pd.read_sql("SELECT * FROM food_logs", conn)
    conn.close()
    
    if df_logs.empty:
        st.info("累積多筆紀錄後即可觀看趨勢圖表。")
    else:
        # 將日期格式化為僅保留天，並以天為單位進行加總 (若同一天有多餐)
        df_logs['day'] = df_logs['date'].str.split(' ').str[0]
        df_daily = df_logs.groupby('day').agg({
            'weight': 'last',       # 該天最後記錄的體重
            'calories': 'sum',      # 該天總熱量
            'protein': 'sum',       # 該天總蛋白質
            'fat': 'sum',           # 該天總脂肪
            'carbs': 'sum'          # 該天總澱粉/碳水
        }).reset_index()
        
        df_daily = df_daily.set_index('day')
        
        st.markdown("### ⚖️ 每日體重趨勢 (kg)")
        st.line_chart(df_daily[['weight']])
        
        st.markdown("### 🔥 每日總熱量趨勢 (大卡)")
        st.line_chart(df_daily[['calories']])
        
        st.markdown("### 🥗 每日三大營養素/澱粉趨勢 (克)")
        st.line_chart(df_daily[['protein', 'fat', 'carbs']])