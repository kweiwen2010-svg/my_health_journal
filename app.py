import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials

# 1. 頁面基本設定
st.set_page_config(
    page_title="AI 智慧營養與飲食記錄器",
    page_icon="🥗",
    layout="centered"
)

# 2. 初始化 Gemini API
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 找不到 GEMINI_API_KEY！請檢查 Streamlit Secrets 設定。")
    st.stop()

genai.configure(api_key=api_key)

# 3. Google 試算表連線設定（使用最穩定的服務帳戶檔案或雲端共用唯讀/編輯）
@st.cache_resource
def init_gspread():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        # 雲端部署時，若無本地 credentials.json 檔案，會自動改為快取暫存或提示
        # 請確保你有將 credentials.json 一併上傳至 GitHub，或是直接使用以下安全讀取方式
        import os
        if os.path.exists("credentials.json"):
            client = gspread.service_account(filename="credentials.json")
        else:
            # 如果是在雲端且沒有檔案，提供明確指引
            st.error("❌ 雲端缺少 credentials.json 檔案。請確保已將該檔案上傳至 GitHub 專案根目錄。")
            st.stop()
            
        sheet_url = st.secrets.get("GOOGLE_SHEETS_URL")
        if not sheet_url:
            st.error("❌ 找不到 GOOGLE_SHEETS_URL！請檢查 Streamlit Secrets 設定。")
            st.stop()
            
        spreadsheet = client.open_by_url(sheet_url)
        return spreadsheet
    except Exception as e:
        st.error(f"❌ Google 試算表連線失敗: {e}")
        st.stop()

# 取得試算表與工作表
try:
    db = init_gspread()
    sheet = db.get_worksheet(0) 
except Exception as e:
    st.stop()

# 4. 介面標題
st.title("🥗 AI 智慧營養與飲食記錄器")
st.markdown("隨時隨地拍照或記錄你的飲食，讓 AI 為你分析營養並安全儲存！")

# 5. 使用者輸入介面
tab1, tab2 = st.tabs(["📸 拍照/上傳記錄", "📊 查看歷史紀錄"])

with tab1:
    st.subheader("記錄新的一餐")
    
    meal_type = st.selectbox("用餐類型", ["早餐", "午餐", "晚餐", "點心/其他"])
    uploaded_file = st.file_uploader("上傳食物照片 (支援 JPG, PNG)", type=["jpg", "jpeg", "png"])
    user_note = st.text_area("備註說明（例如：少飯、半糖、吃了半碗等）", placeholder="請在此輸入...")
    
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption="已上傳的食物照片", use_column_width=True)
    
    if st.button("🚀 開始 AI 營養分析與記錄", type="primary"):
        if uploaded_file is None and not user_note:
            st.warning("⚠️ 請至少上傳照片或輸入備註說明！")
        else:
            with st.spinner("AI 正在分析營養成分中，請稍候..."):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    prompt = (
                        "請扮演專業營養師。分析以下食物照片與備註，並嚴格以 JSON 格式回傳以下欄位："
                        "{\"food_name\": \"食物名稱\", "
                        "\"calories\": 估算卡路里數字(整數), "
                        "\"protein\": 蛋白質克數(數字), "
                        "\"fat\": 脂肪克數(數字), "
                        "\"carbs\": 碳水化合物克數(數字), "
                        "\"advice\": \"簡短的健康建議與評價\"}"
                    )
                    
                    contents = [prompt]
                    if uploaded_file is not None:
                        contents.append(image)
                    if user_note:
                        contents.append(f"備註說明: {user_note}")
                        
                    response = model.generate_content(contents)
                    
                    import json
                    result_text = response.text.strip()
                    if result_text.startswith("```json"):
                        result_text = result_text[7:-3].strip()
                    elif result_text.startswith("```"):
                        result_text = result_text[3:-3].strip()
                        
                    nutrition_data = json.loads(result_text)
                    
                    st.success("✅ 分析成功！")
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("🔥 熱量", f"{nutrition_data.get('calories', 0)} kcal")
                    col2.metric("🥩 蛋白質", f"{nutrition_data.get('protein', 0)} g")
                    col3.metric("🥑 脂肪", f"{nutrition_data.get('fat', 0)} g")
                    col4.metric("🍞 碳水", f"{nutrition_data.get('carbs', 0)} g")
                    
                    st.info(f"💡 **營養師建議**：{nutrition_data.get('advice', '無')}")
                    
                    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    row_data = [
                        now_time,
                        meal_type,
                        nutrition_data.get('food_name', '未知食物'),
                        nutrition_data.get('calories', 0),
                        nutrition_data.get('protein', 0),
                        nutrition_data.get('fat', 0),
                        nutrition_data.get('carbs', 0),
                        user_note
                    ]
                    sheet.append_row(row_data)
                    st.success("💾 紀錄已成功自動儲存至 Google 試算表！")
                    
                except Exception as e:
                    st.error(f"❌ 分析或儲存過程發生錯誤: {e}")

with tab2:
    st.subheader("📜 歷史飲食紀錄")
    if st.button("🔄 重新載入資料"):
        st.rerun()
        
    try:
        data = sheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
        else:
            st.info("目前尚無任何紀錄，快去新增一筆吧！")
    except Exception as e:
        st.error(f"無法讀取歷史紀錄: {e}")