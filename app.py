from datetime import datetime, timedelta
import os
import re
from google import genai
import pandas as pd
import psycopg2
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image

# ==========================================
# 1. 頁面與超大字體的 CSS 設定
# ==========================================
st.set_page_config(page_title="AI 智慧營養管理", page_icon="🥗", layout="centered")

st.markdown(
    """
    <style>
    /* 將整個畫面的基本字體放大約一倍 (28px) */
    html, body, [class*="css"] {
        font-size: 28px !important;
    }
    
    .stApp { 
        background-color: #f5f7f9; 
    }
    
    /* 白色卡片區塊 */
    div[data-testid="stVerticalBlock"] { 
        background-color: white; 
        border-radius: 20px; 
        padding: 25px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
    }
    
    /* 放大分頁籤 (Tabs) 的文字 */
    .stTabs [data-baseweb="tab"] p {
        font-size: 32px !important;
        font-weight: bold !important;
    }
    
    /* 放大所有標題 */
    h1 { font-size: 48px !important; }
    h2 { font-size: 38px !important; }
    h3 { font-size: 32px !important; }
    
    /* 放大按鈕文字與外觀 */
    .stButton>button { 
        width: 100%; 
        border-radius: 25px; 
        background-color: #2ecc71; 
        color: white; 
        font-weight: bold; 
        font-size: 28px !important; 
        padding: 18px; 
    }
    
    /* 放大輸入框、下拉選單、文字輸入區域的字體 */
    input, select, textarea, div[data-baseweb="select"] span {
        font-size: 28px !important;
    }
    
    /* 放大下拉選單展開後的清單文字 */
    div[data-baseweb="popover"] div {
        font-size: 28px !important;
    }
    
    /* 放大折疊目錄 (Expander) 標題文字 */
    .streamlit-expanderHeader p {
        font-size: 28px !important;
        font-weight: bold !important;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. 資料庫與 AI 初始化
# ==========================================
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
  st.error("❌ 找不到 Gemini API Key！")
  st.stop()

client = genai.Client(api_key=api_key)


def get_db_connection():
  database_url = st.secrets.get("DATABASE_URL") or os.environ.get(
      "DATABASE_URL"
  )
  if not database_url:
    st.error(
        "❌ 找不到 DATABASE_URL！請確認是否已設定 Neon 資料庫連線字串。"
    )
    st.stop()
  return psycopg2.connect(database_url)


def init_db():
  conn = get_db_connection()
  c = conn.cursor()
  c.execute("""CREATE TABLE IF NOT EXISTS food_logs (
                 id SERIAL PRIMARY KEY, date TEXT, meal_type TEXT, content TEXT, weight REAL)""")
  c.execute("""CREATE TABLE IF NOT EXISTS daily_summaries (
                 date TEXT PRIMARY KEY, summary TEXT)""")
  c.execute("""CREATE TABLE IF NOT EXISTS user_profile (
                 id INTEGER PRIMARY KEY, height REAL, weight REAL, age INTEGER, activity TEXT, medical TEXT)""")
  
  # 安全為舊表格追加分數欄位 (若已存在會自動忽略錯誤)
  try:
    c.execute("ALTER TABLE food_logs ADD COLUMN score REAL;")
  except Exception:
    conn.rollback()

  try:
    c.execute("ALTER TABLE daily_summaries ADD COLUMN score REAL;")
  except Exception:
    conn.rollback()

  c.execute(
      """INSERT INTO user_profile (id, height, weight, age, activity, medical) 
                 VALUES (1, 178.0, 75.0, 56, '中度運動', '無') 
                 ON CONFLICT (id) DO NOTHING"""
  )
  conn.commit()
  c.close()
  conn.close()


init_db()


def get_user_profile():
  conn = get_db_connection()
  df = pd.read_sql("SELECT * FROM user_profile WHERE id=1", conn)
  conn.close()
  if df.empty:
    return {
        "height": 178.0,
        "weight": 75.0,
        "age": 56,
        "activity": "中度運動",
        "medical": "無",
    }
  return df.iloc[0].to_dict()


def update_user_profile(data):
  conn = get_db_connection()
  c = conn.cursor()
  c.execute(
      "UPDATE user_profile SET height=%s, weight=%s, age=%s, activity=%s,"
      " medical=%s WHERE id=1",
      (
          data["height"],
          data["weight"],
          data["age"],
          data["activity"],
          data["medical"],
      ),
  )
  conn.commit()
  c.close()
  conn.close()


def extract_score(text):
  """從 AI 回覆中用正規表達式抓取分數"""
  match = re.search(r'\[健康分數:\s*(\d+)分?\]', text)
  if match:
    return float(match.group(1))
  return 70.0  # 預設分數


def speak_score_feedback(score):
  """根據分數高低，透過前端語音發出稱讚或噓聲"""
  if score >= 90:
    message = f"太棒了！分數高達 {int(score)} 分，這餐簡直完美，繼續保持！"
  elif score < 70:
    message = f"母湯喔！只有 {int(score)} 分，這餐要稍微檢討一下囉，噓～"
  else:
    message = f"這餐獲得 {int(score)} 分，表現中規中矩，還可以更好喔！"

  js_code = f"""
    <script>
        const utterance = new SpeechSynthesisUtterance("{message}");
        utterance.lang = 'zh-TW';
        utterance.rate = 1.0;
        window.speechSynthesis.speak(utterance);
    </script>
    """
  components.html(js_code, height=0)


def get_streak_days():
  """計算用戶連續打卡的天數"""
  try:
    conn = get_db_connection()
    query = "SELECT DISTINCT LEFT(date, 10) as log_date FROM food_logs ORDER BY log_date DESC"
    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
      return 0

    logged_dates = [datetime.strptime(d, "%Y-%m-%d").date() for d in df['log_date']]
    today = datetime.now().date()
    yesterday = today - timedelta(days=1)
    
    if logged_dates[0] != today and logged_dates[0] != yesterday:
      return 0

    streak = 0
    expected_date = logged_dates[0]
    for d in logged_dates:
      if d == expected_date:
        streak += 1
        expected_date -= timedelta(days=1)
      elif d < expected_date:
        break
    return streak
  except Exception:
    return 0


# ==========================================
# 3. 介面結構（4 個分頁）
# ==========================================
st.title("🥗 AI 智慧營養管理")

# 顯示連續打卡成就看板
streak = get_streak_days()
if streak >= 30:
  badge = "👑 飲食掌控大師 (連續30天)"
elif streak >= 7:
  badge = "🔥 自律達人 (連續7天)"
elif streak >= 3:
  badge = "⭐ 好的開始 (連續3天)"
elif streak >= 1:
  badge = "🌱 新手上路 (已打卡)"
else:
  badge = "💤 尚未開始打卡"

st.info(f"🏆 目前連續打卡成就：**{badge}** （已連續打卡 {streak} 天）")

tab1, tab2, tab3, tab4 = st.tabs(["📸 記錄", "📖 日誌", "🤖 當日總結", "⚙️ 設定"])

# ------------------------------------------
# TAB 1: 拍照與記錄
# ------------------------------------------
with tab1:
  st.subheader("📸 餐點分析")
  meal_type = st.selectbox("選擇餐別", ["早餐", "午餐", "晚餐", "點心"])
  uploaded_file = st.file_uploader(
      "上傳餐點照片", type=["jpg", "jpeg", "png"]
  )
  user_note = st.text_input("💡 補充說明 (例如：吃了一半、加了一匙糖)")

  if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption="已上傳餐點", use_container_width=True)

    if st.button("✨ AI 深度評估"):
      with st.spinner("AI 正在結合您的個人資料進行深度分析..."):
        try:
          p = get_user_profile()
          prompt = [
              f"""
                    你是一位專業營養師。請根據以下用戶資料分析照片中的餐點：
                    - 用戶身型：{p['age']}歲, {p['height']}cm, {p['weight']}kg
                    - 運動狀態：{p['activity']}
                    - 健康備註/過敏源：{p['medical']}
                    - 用戶補充說明：{user_note}
                    
                    請務必在回覆的最開頭明確給出一個 0 到 100 的健康評分，格式固定為：「[健康分數: 85分]」，接著再提供詳細分析：
                    1. 這份餐點大致包含哪些食物與營養成分？
                    2. 這份餐點是否適合該用戶目前的身體狀態與運動習慣？
                    3. 有無營養過剩、不足或需要注意的健康風險？
                    """,
              image,
          ]
          response = client.models.generate_content(
              model="gemini-2.5-flash", contents=prompt
          )
          st.session_state.last_analysis = response.text
          st.markdown(response.text)
        except Exception as e:
          st.error(f"❌ 分析失敗，錯誤訊息：{e}")

  if "last_analysis" in st.session_state and st.button("➕ 加入日誌"):
    score_val = extract_score(st.session_state.last_analysis)
    conn = get_db_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO food_logs (date, meal_type, content, weight, score) VALUES"
        " (%s, %s, %s, %s, %s)",
        (
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            meal_type,
            st.session_state.last_analysis,
            get_user_profile()["weight"],
            score_val,
        ),
    )
    conn.commit()
    c.close()
    conn.close()
    
    # 觸發語音特效
    speak_score_feedback(score_val)
    
    st.success(f"✅ 紀錄成功已存入日誌！(評分: {score_val}分)")
    del st.session_state.last_analysis

# ------------------------------------------
# TAB 2: 飲食日誌
# ------------------------------------------
with tab2:
  st.subheader("📖 我的飲食日誌")
  conn = get_db_connection()
  df = pd.read_sql(
      "SELECT * FROM food_logs ORDER BY date DESC", conn
  )
  conn.close()
  if df.empty:
    st.info("目前尚無飲食紀錄。")
  else:
    for _, row in df.iterrows():
      score_display = (
          f" ⭐ {int(row['score'])}分" if pd.notnull(row["score"]) else ""
      )
      with st.expander(
          f"⏰ {row['date']} - 【{row['meal_type']}】{score_display}"
      ):
        st.write(row["content"])

# ------------------------------------------
# TAB 3: 當日總結與歷史統計圖表
# ------------------------------------------
with tab3:
  st.subheader("⊙ 歷史與當日飲食總結目錄")

  selected_date = st.date_input(
      "選擇查詢日期", value=datetime.now().date()
  )
  target_date_str = selected_date.strftime("%Y-%m-%d")

  df_sum = pd.DataFrame()
  try:
    conn = get_db_connection()
    df_sum = pd.read_sql(
        "SELECT summary, score FROM daily_summaries WHERE date = %s",
        conn,
        params=(target_date_str,),
    )
    conn.close()
  except Exception:
    df_sum = pd.DataFrame()

  if not df_sum.empty:
    day_score_text = (
        f" (總結評分: {int(df_sum.iloc[0]['score'])}分)"
        if pd.notnull(df_sum.iloc[0]["score"])
        else ""
    )
    st.success(f"📌 {target_date_str} 營養總結報告{day_score_text}：")
    st.markdown(df_sum.iloc[0]["summary"])
  else:
    st.info(f"📅 尚無 {target_date_str} 的保存總結。")

    conn = get_db_connection()
    df_today = pd.read_sql(
        "SELECT meal_type, content FROM food_logs WHERE date LIKE %s",
        conn,
        params=(f"{target_date_str}%",),
    )
    conn.close()

    if not df_today.empty:
      if st.button(f"📊 產出並永久保存 {target_date_str} 總結報告"):
        with st.spinner(f"AI 正在綜整 {target_date_str} 的飲食紀錄..."):
          try:
            p = get_user_profile()
            today_logs = [
                f"【{row['meal_type']}】\n{row['content']}"
                for _, row in df_today.iterrows()
            ]
            prompt = f"""
                        請扮演專業營養師，根據用戶資料 {p} 與以下【{target_date_str}】的所有飲食紀錄：
                        {today_logs}
                        
                        請務必在回覆最開頭明確給出當日的綜合健康評分，格式固定為：「[健康分數: 85分]」，接著提供：
                        1. 當日總熱量與三大營養素（蛋白質、脂肪、碳水化合物）的粗估加總。
                        2. 當日飲食的整體優缺點（是否有營養過剩或不足）。
                        3. 針對接下來的飲食調整建議。
                        """
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            summary_text = response.text
            summary_score = extract_score(summary_text)

            conn = get_db_connection()
            c = conn.cursor()
            c.execute(
                """INSERT INTO daily_summaries (date, summary, score) VALUES (%s, %s, %s)
                           ON CONFLICT (date) DO UPDATE SET summary = EXCLUDED.summary, score = EXCLUDED.score""",
                (target_date_str, summary_text, summary_score),
            )
            conn.commit()
            c.close()
            conn.close()

            # 總結產出時也觸發語音特效
            speak_score_feedback(summary_score)

            st.success(f"✅ {target_date_str} 總結報告已成功儲存！")
            st.rerun()
          except Exception as e:
            st.error(f"❌ 產生失敗：{e}")

  st.markdown("---")
  st.markdown("### 📈 每日健康分數趨勢圖")
  try:
    conn = get_db_connection()
    df_scores = pd.read_sql(
        "SELECT date, score FROM daily_summaries WHERE score IS NOT NULL ORDER BY"
        " date ASC",
        conn,
    )
    conn.close()

    if df_scores.empty:
      st.info("目前尚無足夠的每日總結分數來繪製趨勢圖。")
    else:
      df_scores["date"] = pd.to_datetime(df_scores["date"])
      df_scores.set_index("date", inplace=True)
      st.line_chart(df_scores["score"])
  except Exception:
    st.info("目前尚無趨勢圖資料。")

  st.markdown("---")
  st.markdown("### 📚 歷史總結目錄總覽")
  try:
    conn = get_db_connection()
    df_all_sums = pd.read_sql(
        "SELECT date, summary, score FROM daily_summaries ORDER BY date DESC",
        conn,
    )
    conn.close()

    if df_all_sums.empty:
      st.info("目前尚無任何歷史總結紀錄。")
    else:
      for _, row in df_all_sums.iterrows():
        s_txt = (
            f" - 綜合評分: {int(row['score'])}分"
            if pd.notnull(row["score"])
            else ""
        )
        with st.expander(f"📂 營養總結報告：{row['date']}{s_txt} (點擊展開)"):
          st.markdown(row["summary"])
  except Exception:
    st.info("目前尚無歷史總結目錄資料。")

# ------------------------------------------
# TAB 4: 個人設定
# ------------------------------------------
with tab4:
  st.subheader("⚙️ 個人檔案設定")
  p = get_user_profile()

  with st.form("profile_form"):
    h_val = st.number_input("身高 (cm)", value=float(p["height"]))
    w_val = st.number_input("體重 (kg)", value=float(p["weight"]))
    a_val = st.number_input("年齡", value=int(p["age"]))

    activities = ["久坐不動", "輕度運動", "中度運動", "高度運動"]
    act_idx = (
        activities.index(p["activity"]) if p["activity"] in activities else 2
    )
    act_val = st.selectbox("運動狀態", activities, index=act_idx)

    med_val = st.text_area("健康備註/過敏源", value=str(p["medical"]))

    submitted = st.form_submit_button("💾 儲存個人資料")
    if submitted:
      new_p = {
          "height": h_val,
          "weight": w_val,
          "age": a_val,
          "activity": act_val,
          "medical": med_val,
      }
      update_user_profile(new_p)
      st.success("✅ 個人資料已成功儲存！")