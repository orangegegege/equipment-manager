import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json
import os

# --- 設定與連線 (保持不變) ---
SCOPE = ['https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
# 🔴 請確認這裡還是你的 ID
SHEET_ID = '1oa6qhkVlCxM0gK6JNgcXwlPv6XfQK0ExcjApmwOzNhw' 

def connect_google_sheet():
    """連線到 Google Sheets"""
    try:
        if os.path.exists('service_account.json'):
            creds = ServiceAccountCredentials.from_json_keyfile_name('service_account.json', SCOPE)
        elif "private_key" in st.secrets:
            creds_dict = dict(st.secrets)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        else:
            return None
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID).sheet1
        return sheet
    except Exception as e:
        st.error(f"連線錯誤: {e}")
        return None

def load_data():
    """讀取資料"""
    sheet = connect_google_sheet()
    if sheet:
        data = sheet.get_all_records()
        if not data:
            return pd.DataFrame(columns=["uid", "name", "category", "status", "borrower", "location", "image_url", "update_time"])
        return pd.DataFrame(data)
    return pd.DataFrame()

def save_data(df):
    """儲存資料"""
    sheet = connect_google_sheet()
    if sheet:
        sheet.clear()
        sheet.update([df.columns.values.tolist()] + df.values.tolist())

# --- 頁面設定 (預設隱藏側邊欄，讓畫面更乾淨) ---
st.set_page_config(page_title="器材管理系統", layout="wide", page_icon="📦", initial_sidebar_state="collapsed")

# CSS 美化 (讓按鈕更好看，並微調排版)
st.markdown("""
<style>
    .stButton>button {width: 100%; border-radius: 8px;}
    div[data-testid="stMetricValue"] {font-size: 28px;}
    /* 讓登入頁面的標題置中 */
    .login-title {text-align: center; font-size: 40px; font-weight: bold; margin-bottom: 20px;}
</style>
""", unsafe_allow_html=True)

# --- 🔐 狀態管理核心 (Session State) ---
# 初始化狀態
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'current_page' not in st.session_state:
    st.session_state.current_page = "home" # 預設在首頁

def go_to_login():
    """切換到登入頁"""
    st.session_state.current_page = "login"

def go_to_home():
    """切換回首頁"""
    st.session_state.current_page = "home"

def perform_login():
    """執行登入驗證"""
    password = st.session_state.password_input
    if password == st.secrets["ADMIN_PASSWORD"]:
        st.session_state.is_admin = True
        st.session_state.current_page = "home" # 登入成功跳回首頁
    else:
        st.error("密碼錯誤，請重試 ❌")

def perform_logout():
    """執行登出"""
    st.session_state.is_admin = False
    st.session_state.current_page = "home"

# ==========================================
#  頁面 1：獨立登入畫面 (Login Page)
# ==========================================
def login_page():
    # 使用 columns 讓內容置中 (左右留白)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<p class='login-title'>🔐 管理員登入</p>", unsafe_allow_html=True)
        st.info("請輸入管理員密碼以進入後台模式")
        
        with st.container(border=True):
            st.text_input("密碼", type="password", key="password_input")
            
            b1, b2 = st.columns(2)
            with b1:
                st.button("返回首頁", on_click=go_to_home)
            with b2:
                st.button("登入", type="primary", on_click=perform_login)

# ==========================================
#  頁面 2：主儀表板畫面 (Main Dashboard)
# ==========================================
def main_page():
    # --- 頂部導覽列 (Navbar) ---
    # 利用 columns 做出「左邊標題，右邊按鈕」的效果
    col_logo, col_space, col_login = st.columns([6, 3, 1])
    
    with col_logo:
        st.title("📦 團隊器材管理系統")
    
    with col_login:
        # 根據是否登入，顯示不同按鈕
        if st.session_state.is_admin:
            st.button("登出", on_click=perform_logout)
        else:
            st.button("🔐 管理員登入", type="primary", on_click=go_to_login)

    # 顯示目前身分提示
    if st.session_state.is_admin:
        st.success("目前身分：👨‍💻 管理員 (可編輯模式)")
    
    # --- 以下是原本的器材邏輯 ---
    # 1. 載入資料
    with st.spinner('🔄 同步雲端資料中...'):
        df = load_data()

    if 'image_url' not in df.columns: df['image_url'] = ""
    df = df.astype(str)

    # --- 區塊 1：儀表板 ---
    total_items = len(df)
    available_items = len(df[df['status'] == '在庫'])
    maintenance_items = len(df[df['status'] == '維修中'])
    borrowed_items = len(df[df['status'] == '借出中'])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 總器材數", total_items)
    col2.metric("✅ 可用器材", available_items)
    col3.metric("🛠️ 維修中", maintenance_items)
    col4.metric("👤 借出中", borrowed_items)

    st.divider()

    # --- 區塊 2：搜尋與新增 ---
    col_search, col_add = st.columns([3, 1])

    with col_search:
        search_query = st.text_input("🔍 搜尋器材 (名稱/編號)", placeholder="輸入關鍵字...")

    with col_add:
        # 🔒 只有管理員看得到「新增按鈕」
        if st.session_state.is_admin:
            with st.popover("➕ 新增器材", use_container_width=True):
                st.subheader("新增一項器材")
                with st.form("add_form", clear_on_submit=True):
                    new_name = st.text_input("器材名稱")
                    new_uid = st.text_input("器材編號")
                    c1, c2 = st.columns(2)
                    new_cat = c1.selectbox("分類", ["攝影器材", "燈光音響", "線材耗材", "電腦週邊", "其他"])
                    new_status = c2.selectbox("狀態", ["在庫", "借出中", "維修中", "報廢"])
                    new_loc = st.text_input("存放位置", value="儲藏室")
                    new_img = st.text_input("圖片網址 (選填)")
                    
                    if st.form_submit_button("確認新增"):
                        if new_name and new_uid:
                            new_row = pd.DataFrame([{
                                "uid": new_uid, "name": new_name, "category": new_cat,
                                "status": new_status, "borrower": "", "location": new_loc,
                                "image_url": new_img,
                                "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }])
                            df = pd.concat([df, new_row], ignore_index=True)
                            save_data(df)
                            st.toast(f"已新增：{new_name}", icon="✅")
                            st.rerun()
                        else:
                            st.error("請填寫必要資訊")

    # --- 區塊 3：卡片列表 ---
    st.subheader("器材列表")

    if search_query:
        filtered_df = df[df['name'].str.contains(search_query, case=False) | df['uid'].str.contains(search_query, case=False)]
    else:
        filtered_df = df

    if not filtered_df.empty:
        cols = st.columns(3)
        for idx, row in filtered_df.iterrows():
            with cols[idx % 3]:
                with st.container(border=True):
                    img_link = row['image_url'] if row['image_url'].startswith('http') else "https://cdn-icons-png.flaticon.com/512/4992/4992482.png"
                    st.image(img_link, use_container_width=True)
                    
                    st.markdown(f"### {row['name']}")
                    st.caption(f"編號: {row['uid']} | 位置: {row['location']}")
                    
                    status_color = "green" if row['status'] == "在庫" else "red" if row['status'] == "借出中" else "orange"
                    st.markdown(f":{status_color}[● {row['status']}]")
                    
                    # 🔒 管理權限
                    if st.session_state.is_admin:
                        with st.expander("⚙️ 管理"):
                            new_status_card = st.selectbox("更新狀態", ["在庫", "借出中", "維修中", "報廢"], key=f"s_{row['uid']}", index=["在庫", "借出中", "維修中", "報廢"].index(row['status']))
                            new_borrower = st.text_input("借用人", value=row['borrower'], key=f"b_{row['uid']}")
                            
                            col_up, col_del = st.columns(2)
                            if col_up.button("更新", key=f"btn_{row['uid']}"):
                                df.loc[df['uid'] == row['uid'], 'status'] = new_status_card
                                df.loc[df['uid'] == row['uid'], 'borrower'] = new_borrower
                                save_data(df)
                                st.rerun()
                            if col_del.button("刪除", key=f"del_{row['uid']}", type="primary"):
                                df = df[df['uid'] != row['uid']]
                                save_data(df)
                                st.rerun()
                    else:
                        if row['status'] == "借出中":
                            st.info(f"借用人: {row['borrower']}")
    else:
        st.info("沒有找到符合的器材 🐢")

# ==========================================
#  主程式邏輯：決定顯示哪一頁 (Router)
# ==========================================
if st.session_state.current_page == "login":
    login_page()
else:
    main_page()