import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import os  # <--- 記得要加上這個！

# --- 設定與連線 (改良版：優先讀取本地檔案) ---
SCOPE = ['https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
SHEET_ID = '1oa6qhkVlCxM0gK6JNgcXwlPv6XfQK0ExcjApmwOzNhw' # 🔴 記得確認這裡還是你的 ID！

def connect_google_sheet():
    """連線到 Google Sheets (自動偵測環境)"""
    try:
        # 情況 A：優先檢查本地有沒有 'service_account.json'
        if os.path.exists('service_account.json'):
            creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', SCOPE)
        
        # 情況 B：如果本地找不到，才去讀取雲端 Secrets
        elif "GCP_KEY" in st.secrets:
            key_dict = json.loads(st.secrets["GCP_KEY"])
            creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, SCOPE)
            
        else:
            raise Exception("找不到鑰匙！請確認本地有 json 檔，或雲端有設定 Secrets。")
            
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1
        return sheet
    except Exception as e:
        st.error(f"連線失敗！錯誤訊息: {e}")
        raise e
# --- 核心邏輯函數 ---
def load_data():
    """從 Google Sheets 讀取資料"""
    try:
        sheet = connect_google_sheet()
        data = sheet.get_all_records() 
        if not data: 
            return pd.DataFrame(columns=["uid", "name", "category", "status", "borrower", "location", "update_time"])
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"讀取資料失敗: {e}")
        return pd.DataFrame()

def save_data(df):
    """將資料寫回 Google Sheets"""
    try:
        sheet = connect_google_sheet()
        sheet.clear() 
        sheet.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        st.error(f"儲存失敗: {e}")

# --- 頁面配置 ---
st.set_page_config(page_title="雲端器材管理系統", layout="wide")
st.title("☁️ 團隊器材管理中心 (ID 連線版)")

menu = st.sidebar.radio("功能選單", ["🔍 前台：器材查詢", "🛠️ 後台：庫存管理", "➕ 後台：新增器材"])

# 載入資料
with st.spinner('正在連線至雲端資料庫...'):
    df = load_data()

# 確保欄位格式
if not df.empty:
    df = df.astype(str)

# --- 功能 1：前台查詢 ---
if menu == "🔍 前台：器材查詢":
    st.header("器材總覽")
    col1, col2 = st.columns(2)
    with col1:
        search_term = st.text_input("搜尋器材名稱...")
    with col2:
        filter_status = st.selectbox("狀態篩選", ["全部", "在庫", "借出中", "維修中", "報廢"])

    view_df = df.copy()
    if not view_df.empty:
        if search_term:
            view_df = view_df[view_df['name'].str.contains(search_term, case=False)]
        if filter_status != "全部":
            view_df = view_df[view_df['status'] == filter_status]

    st.dataframe(view_df, use_container_width=True, hide_index=True)

# --- 功能 2：後台庫存管理 ---
elif menu == "🛠️ 後台：庫存管理":
    st.header("庫存狀態調整")
    st.warning("⚠️ 此處更動將直接同步至 Google Sheets。")

    if not df.empty:
        edited_df = st.data_editor(
            df,
            column_config={
                "status": st.column_config.SelectboxColumn("狀態", options=["在庫", "借出中", "維修中", "報廢"], required=True),
                "category": st.column_config.SelectboxColumn("分類", options=["攝影器材", "燈光音響", "線材耗材", "其他"], required=True),
            },
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True
        )

        if st.button("💾 儲存變更至雲端"):
            edited_df['update_time'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with st.spinner('正在寫入...'):
                save_data(edited_df)
            st.success("更新成功！")
            st.rerun()

# --- 功能 3：後台新增器材 ---
elif menu == "➕ 後台：新增器材":
    st.header("器材入庫登記")
    with st.form("add_equipment_form"):
        col1, col2 = st.columns(2)
        new_uid = col1.text_input("器材編號 (UID)")
        new_name = col2.text_input("器材名稱")
        new_cat = col1.selectbox("分類", ["攝影器材", "燈光音響", "線材耗材", "其他"])
        new_loc = col2.text_input("存放位置", value="器材室")
        
        submitted = st.form_submit_button("確認入庫")
        
        if submitted:
            if new_uid and new_name:
                new_data = pd.DataFrame([{
                    "uid": new_uid,
                    "name": new_name,
                    "category": new_cat,
                    "status": "在庫",
                    "borrower": "",
                    "location": new_loc,
                    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                df = pd.concat([df, new_data], ignore_index=True)
                with st.spinner('正在上傳...'):
                    save_data(df)
                st.success(f"已新增：{new_name}")
            else:
                st.error("請填寫完整資訊！")