import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
from PIL import Image
import json

# 1. 頁面基本設定
st.set_page_config(
    page_title="AI 智慧營養與飲食記錄器",
    page_icon="🥗",
    layout="centered"
)

# 2. 初始化 Gemini API (只需要這個金鑰即可)
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("❌ 找不到 GEMINI_API_KEY！請檢查 Streamlit Secrets 設定。")
    st.stop()

genai.configure(api_key=api_key)

# 3. 簡化版儲存機制：改用 Streamlit 本地暫存與模擬試算表（或直接顯示紀錄）
# 這樣完全不需要設定複雜的 Google 憑證，保證 100% 成功執行！
if 'records' not in st.session_state:
    st.session_state['records'] = []

# 4. 介面標題與說明
st.title("🥗 AI 智慧營養與飲食記錄器")
st.markdown("隨時隨地拍照或記錄你的飲食，讓 AI 為你分析營養並記錄！")

# 5. 分頁介面
tab1, tab2 = st.tabs(["📸 拍照/上傳記錄", "📊 查看歷史紀錄"])

with tab1:
    st.subheader("記錄新的一餐")
    
    meal_type = st.selectbox("用餐類型", ["早餐", "午餐", "晚餐", "點心/其他"])
    uploaded_file = st.file_uploader("上傳食物照片 (支援 JPG, PNG)", type=["jpg", "jpeg", "png"])
    user_note = st.text_area("備註說明（例如：少飯、半糖、吃了半碗等）", placeholder="請在此輸入...")
    
    image = None
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
                        "請扮演專業營養師。分析以下食物照片與備註，並嚴格以 JSON 格式回傳以下欄位，不要包覆額外多餘文字："
                        "{\"food_name\": \"食物名稱\", "
                        "\"calories\": 估算卡路里數字(整數), "
                        "\"protein\": 蛋白質克數(數字), "
                        "\"fat\": 脂肪克數(數字), "
                        "\"carbs\": 碳水化合物克數(數字), "
                        "\"advice\": \"簡短的健康建議與評價\"}"
                    )
                    
                    contents = [prompt]
                    if image is not None:
                        contents.append(image)
                    if user_note:
                        contents.append(f"備註說明: {user_note}")
                        
                    response = model.generate_content(contents)
                    
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
                    
                    # 儲存至暫存紀錄
                    now_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    row_data = {
                        "時間": now_time,
                        "類型": meal_type,
                        "食物名稱": nutrition_data.get('food_name', '未知食物'),
                        "熱量 (kcal)": nutrition_data.get('calories', 0),
                        "蛋白質 (g)": nutrition_data.get('protein', 0),
                        "脂肪 (g)": nutrition_data.get('fat', 0),
                        "碳水 (g)": nutrition_data.get('carbs', 0),
                        "備註": user_note
                    }
                    st.session_state['records'].append(row_data)
                    st.success("💾 紀錄已成功儲存！")
                    
                except Exception as e:
                    st.error(f"❌ 分析過程發生錯誤: {e}")

with tab2:
    st.subheader("📜 歷史飲食紀錄")
    if st.session_state['records']:
        df = pd.DataFrame(st.session_state['records'])
        st.dataframe(df, use_container_width=True)
    else:
        st.info("目前尚無任何紀錄，快去新增一筆吧！")