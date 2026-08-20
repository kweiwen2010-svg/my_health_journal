import os
import sqlite3
from datetime import datetime
import google.generativeai as genai
import pandas as pd
import streamlit as st

# ==========================================
# 1. 頁面基本設定
# ==========================================
st.set_page_config(page_title="AI 智慧營養與飲食記錄器", page_icon="🥗", layout="centered")

# ==========================================
# 2. 自動載入 API Key 與 模型設定
# ==========================================
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
  st.error("❌ 找不到 Gemini API Key！請檢查 Streamlit Secrets 設定。")
  st.stop()

genai.configure(api_key=api_key)

# 🟢 指定使用最新的 3.6 模型
model = genai.GenerativeModel("gemini-3.6-flash")


# ==========================================
# 3. SQLite 資料庫初始化（確保資料永久儲存）
# ==========================================
def init_db():
  conn = sqlite3.connect("food_data.db")
  c = conn.cursor()
  c.execute("""
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            meal_type TEXT,
            content TEXT,
            calories REAL,
            protein REAL,
            carbs REAL,
            fat REAL,
            weight REAL,
            medical TEXT
        )
    """)
  conn.commit()
  conn.close()


init_db()

# ==========================================
# 4. 側邊欄與頁面導覽
# ==========================================
# 新的頂部頁籤選單
tab1, tab2, tab3, tab4 = st.tabs(["拍照分析", "飲食日誌", "AI 智慧統整", "歷史趨勢"])

with tab1:
  # 這裡放原本「拍照分析」的所有程式碼
  pass

with tab2:
  # 這裡放原本「飲食日誌」的所有程式碼
  pass

with tab3:
  # 這裡放原本「AI 智慧統整」的所有程式碼
  pass

with tab4:
  # 這裡放原本「歷史趨勢」的所有程式碼
  pass

# 讀取資料庫的共用函式（自動相容中英文欄位防錯）


def load_all_logs():
  conn = sqlite3.connect("food_data.db")
  try:
    df = pd.read_sql("SELECT * FROM food_logs", conn)
  except Exception:
    df = pd.DataFrame()
  conn.close()
  return df


# ==========================================
# 5. 頁面一：拍照分析
# ==========================================
if menu == "拍照分析":
  st.title("🥗 AI 智慧營養與飲食記錄器")

  meal_type = st.selectbox("選擇餐別", ["早餐", "午餐", "晚餐", "點心/其他"])
  uploaded_file = st.file_uploader(
      "拍攝或上傳你的餐點", type=["jpg", "jpeg", "png"]
  )
  user_note = st.text_input("💡 補充說明（例如：分食比例、飯後水果等）")

  if uploaded_file is not None:
    st.image(uploaded_file, caption="已載入餐點圖片", use_container_width=True)

    if st.button("✨ 開始 AI 營養分析"):
      with st.spinner("AI 營養師正在分析中..."):
        try:
          from PIL import Image

          image = Image.open(uploaded_file)

          prompt = f"""
                    請扮演專業營養師，針對這張餐點圖片進行分析：
                    1. 估算內容與份量。
                    2. 提供營養成分估算（熱量 kcal, 蛋白質 g, 碳水化合物 g, 脂肪 g）。
                    3. 給予營養建議。
                    補充備註：{user_note}
                    """
          response = model.generate_content([prompt, image])
          st.markdown(response.text)

          # 暫存結果供寫入使用
          st.session_state.last_analysis = response.text
          st.session_state.last_image = image
        except Exception as e:
          st.error(f"分析失敗: {e}")

  # 儲存按鈕
  if "last_analysis" in st.session_state:
    weight_input = st.number_input("記錄目前體重 (kg)", value=65.0, step=0.1)
    if st.button("➕ 將此餐點加入紀錄"):
      conn = sqlite3.connect("food_data.db")
      c = conn.cursor()
      now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
      c.execute(
          """
                INSERT INTO food_logs (date, meal_type, content, calories, protein, carbs, fat, weight)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
          (
              now_str,
              meal_type,
              st.session_state.last_analysis,
              740.0,
              25.0,
              106.0,
              22.0,
              weight_input,
          ),
      )
      conn.commit()
      conn.close()
      st.success("✅ 成功加入紀錄，已永久保存！")

# ==========================================
# 6. 頁面二：飲食日誌
# ==========================================
elif menu == "飲食日誌":
  st.title("📖 我的飲食日誌")

  df_logs = load_all_logs()

  if df_logs.empty:
    st.info("目前還沒有任何記錄，快去「拍照分析」新增第一筆吧！")
  else:
    if st.button("🗑️ 清空所有紀錄"):
      conn = sqlite3.connect("food_data.db")
      c = conn.cursor()
      c.execute("DELETE FROM food_logs")
      conn.commit()
      conn.close()
      st.experimental_rerun()

    # 自動適配欄位名稱防錯
    date_col = "日期" if "日期" in df_logs.columns else "date"
    meal_col = "餐別" if "餐別" in df_logs.columns else "meal_type"
    weight_col = "體重" if "體重" in df_logs.columns else "weight"

    for index, row in df_logs.iterrows():
      d_val = row.get(date_col, "未知時間")
      m_val = row.get(meal_col, "餐點")
      w_val = row.get(weight_col, 0.0)

      with st.expander(f"⏰ {d_val} - 【{m_val}】 (體重: {w_val}kg)"):
        content_val = (
            row["content"] if "content" in row else row.get("內容", "無詳細內容")
        )
        st.write(content_val)

# ==========================================
# 7. 頁面三與四：AI 智慧統整與歷史趨勢
# ==========================================
elif menu == "AI 智慧統整":
  st.title("✨ AI 智慧統整")
  df_logs = load_all_logs()
  if df_logs.empty:
    st.info("尚無數據可供統整。")
  else:
    st.write(
        f"總共記錄了 {len(df_logs)} 筆飲食資料，資料庫運作正常，隨時隨地都可以查看！"
    )

elif menu == "歷史趨勢":
  st.title("📈 歷史趨勢")
  df_logs = load_all_logs()
  if df_logs.empty:
    st.info("尚無歷史數據。")
  else:
    weight_col = "體重" if "體重" in df_logs.columns else "weight"
    if weight_col in df_logs.columns:
      st.line_chart(df_logs[weight_col])