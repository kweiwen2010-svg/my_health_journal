import streamlit as st
import json
import os
import google.generativeai as genai

# 1. 頁面基本設定
st.set_page_config(page_title="AI 智慧營養與飲食記錄器", page_icon="🥗", layout="centered")

# 2. 設定 Gemini API Key (優先從 Streamlit Secrets 讀取，沒有的話則使用預設或提示)
gemini_api_key = st.secrets.get("GEMINI_API_KEY", "AIzaSyBQvJyxa1pNoR37zdkS-vuqACWIGpS4t70")
if gemini_api_key:
    genai.configure(api_key=gemini_api_key)

st.title("🥗 AI 智慧營養與飲食記錄器 (本地版)")
st.markdown("---")

# 3. 側邊欄：手機本地 JSON 檔上傳區
st.sidebar.header("📁 資料管理")
uploaded_file = st.sidebar.file_uploader("請上傳您的記錄檔 (JSON)", type=["json"])

data = None
if uploaded_file is not None:
    try:
        data = json.load(uploaded_file)
        st.sidebar.success("✅ 記錄檔載入成功！")
    except Exception as e:
        st.sidebar.error(f"❌ 檔案解析失敗：{e}")
else:
    st.sidebar.info("ℹ️ 請上傳您的本地 JSON 檔案以開始記錄與分析。")

# 4. 主畫面邏輯
if data is not None:
    st.subheader("📋 目前的記錄內容")
    # 顯示目前載入的 JSON 內容（可自由調整呈現方式）
    st.json(data)
    
    st.markdown("---")
    st.subheader("🤖 AI 營養分析與建議")
    
    user_prompt = st.text_area("輸入你想對 AI 詢問的問題或補充飲食內容：", "請幫我分析這份飲食記錄的營養均衡度，並給予改善建議。")
    
    if st.button("🚀 開始讓 AI 分析"):
        if not gemini_api_key:
            st.error("❌ 找不到 Gemini API Key，請檢查設定。")
        else:
            with st.spinner("AI 正在努力分析您的飲食中..."):
                try:
                    # 組合提示詞與 JSON 資料
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    full_content = f"{user_prompt}\n\n以下是目前的資料：\n{json.dumps(data, ensure_ascii=False, indent=2)}"
                    
                    response = model.generate_content(full_content)
                    
                    st.success("✨ 分析完成！")
                    st.write(response.text)
                    
                    # 模擬更新資料或把結果存進資料結構中
                    # (這裡你可以依需求把 AI 回應存入 data，或者直接提供下載)
                    
                except Exception as e:
                    st.error(f"❌ AI 呼叫失敗：{e}")

    st.markdown("---")
    st.subheader("📥 儲存與下載")
    # 提供下載更新後的 JSON 檔案，讓你可以存回手機
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    st.download_button(
        label="📥 下載最新的記錄檔 (JSON)",
        data=json_str,
        file_name="my_health_data.json",
        mime="application/json"
    )

else:
    # 當還沒上傳檔案時的導引畫面
    st.info("👋 歡迎使用！請點擊左側選單的 **「瀏覽檔案」** 來上傳你的 JSON 紀錄檔，即可開始使用。")
    
    # 提供一個範例按鈕讓使用者可以下載空白範本
    sample_data = {
        "user": "Vincent",
        "records": [
            {"date": "2026-06-07", "meal": "早餐", "food": "燕麥粥、水煮蛋", "calories": 350}
        ]
    }
    st.download_button(
        label="📥 下載空白範例 JSON 檔",
        data=json.dumps(sample_data, ensure_ascii=False, indent=2),
        file_name="sample_health_data.json",
        mime="application/json"
    )