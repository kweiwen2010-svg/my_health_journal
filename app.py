import streamlit as st
import google.generativeai as genai
from datetime import datetime
import pandas as pd
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
import json

# 3. Google 試算表連線設定（直接從 Secrets 讀取字典，免除檔案依賴）
@st.cache_resource
def init_gspread():
    try:
        # 從 st.secrets 讀取憑證字串並轉回字典
        creds_json_str = st.secrets["GOOGLE_SHEETS_CREDENTIALS"]
        if isinstance(creds_json_str, str):
            creds_dict = json.loads(creds_json_str)
        else:
            creds_dict = creds_json_str
            
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        sheet_url = st.secrets.get("GOOGLE_SHEETS_URL")
        if not sheet_url:
            st.error("❌ 找不到 GOOGLE_SHEETS_URL！")
            st.stop()
            
        spreadsheet = client.open_by_url(sheet_url)
        return spreadsheet
    except Exception as e:
        st.error(f"❌ Google 試算表連線失敗: {e}")
        st.stop()