import streamlit as st
import pandas as pd
from datetime import datetime
import os

# 頁面基本設定
st.set_page_config(page_title="AI 智慧營養與飲食日誌", page_icon="🥗", layout="centered")

# ==========================================
# 第一階段：初始化 Session State (側欄資料長期記憶)
# ==========================================
if 'user_height' not in st.session_state:
    st.session_state.user_height = 170.0
if 'user_weight' not in st.session_state:
    st.session_state.user_weight = 65.0
if 'user_history' not in st.session_state:
    st.session_state.user_history = "無"

# 側欄介面設定
st.sidebar.header("個人基本資料")
st.sidebar.number_input("身高 (cm)", value=st.session_state.user_height, key='user_height')
st.sidebar.number_input("體重 (kg)", value=st.session_state.user_weight, key='user_weight')
st.sidebar.text_area("病史/特別需求", value=st.session_state.user_history, key='user_history')

st.sidebar.write("---")
st.sidebar.write(f"目前記憶體體重: {st.session_state.user_weight} kg")

# 主畫面標題
st.title("🥗 AI 智慧營養與飲食日誌")

# 分頁籤設計
tab1, tab2 = st.tabs(["📷 拍照分析", "📊 飲食日誌"])

# CSV 紀錄檔案路徑
LOG_FILE = "food_log.csv"

with tab1:
    st.header("上傳餐點照片進行分析")
    
    # 預留後續第二階段的餐別選擇位置
    meal_type = st.selectbox("選擇餐別", ["早餐", "午餐", "晚餐", "其他"])
    
    uploaded_file = st.file_uploader("選擇食物照片...", type=["jpg", "jpeg", "png"])
    
    if uploaded_file is not None:
        st.image(uploaded_file, caption="已上傳的餐點", use_container_width=True)
        
        if st.button("開始分析並儲存紀錄"):
            # 模擬 AI 分析與寫入 CSV
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
            weight_recorded = st.session_state.user_weight
            
            new_data = pd.DataFrame([{
                "時間": current_time,
                "餐別": meal_type,
                "體重": weight_recorded,
                "身高": st.session_state.user_height,
                "病史": st.session_state.user_history,
                "分析結果": "這是一份測試分析結果（後續將接入真實 AI 營養分析）"
            }])
            
            if os.path.exists(LOG_FILE):
                df_existing = pd.read_csv(LOG_FILE)
                df_combined = pd.concat([new_data, df_existing], ignore_index=True)
            else:
                df_combined = new_data
                
            df_combined.to_csv(LOG_FILE, index=False, encoding="utf-8-sig")
            st.success(f"已成功儲存！當下記錄體重：{weight_recorded} kg，餐別：{meal_type}")

with tab2:
    st.header("我的飲食日誌")
    
    if st.button("清空所有記錄"):
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
            st.success("已清空所有紀錄！")
            st.rerun()
            
    if os.path.exists(LOG_FILE):
        df_logs = pd.read_csv(LOG_FILE)
        
        for index, row in df_logs.iterrows():
            with st.expander(f"📅 {row['時間']} | 【{row.get('餐別', '未分類')}】 (體重: {row['體重']}kg)"):
                st.write(f"**身高**：{row['身高']} cm")
                st.write(f"**病史**：{row['病史']}")
                st.write(f"**分析內容**：{row['分析結果']}")
    else:
        st.info("目前還沒有任何飲食紀錄，快去拍張照開始記錄吧！")