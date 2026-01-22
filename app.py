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

# --- 頁面設定 ---
st.set_page_config(page_title="器材管理系統", layout="wide", page_icon="📦", initial_sidebar_state="collapsed")

# --- CSS 美化 (新增：背景霧化特效) ---
st.markdown("""
<style>
    .stButton>button {width: 100%; border-radius: 8px;}
    div[data-testid="stMetricValue"] {font-size: 28px;}
    .login-title {text-align: center; font-size: 40px; font-weight: bold; margin-bottom: 20px;}
    
    /* 🔥 關鍵特效：讓彈出視窗 (Dialog) 的背景變模糊 */
    div[data-testid="stDialog"] {
        backdrop-filter: blur(8px) !important;
        background-color: rgba(0, 0, 0, 0.4) !important; /* 讓背景稍微變暗 */
    }
</style>
""", unsafe_allow_html=True)

# --- 狀態管理 ---
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'current_page' not in st.session_state: st.session_state.current_page = "home"

def go_to_login(): st.session_state.current_page = "login"
def go_to_home(): st.session_state.current_page = "home"
def perform_logout():
    st.session_state.is_admin = False
    st.session_state.current_page = "home"

def perform_login():
    if st.session_state.password_input == st.secrets["ADMIN_PASSWORD"]:
        st.session_state.is_admin = True
        st.session_state.current_page = "home"
    else:
        st.error("密碼錯誤 ❌")

# ==========================================
#  獨立功能：新增器材的彈出視窗 (Modal)
# ==========================================
@st.dialog("➕ 新增一項器材") # 這是 Streamlit 的新功能，會自動置中
def show_add_modal(current_df):
    st.info("請填寫下方資訊，完成後點擊確認。")
    with st.form("add_form", clear_on_submit=True):
        new_name = st.text_input("器材名稱", placeholder="例如：Canon R6")
        new_uid = st.text_input("器材編號", placeholder="例如：CAM-002")
        
        c1, c2 = st.columns(2)
        new_cat = c1.selectbox("分類", ["攝影器材", "燈光音響", "線材耗材", "電腦週邊", "其他"])
        new_status = c2.selectbox("狀態", ["在庫", "借出中", "維修中", "報廢"])
        
        new_loc = st.text_input("存放位置", value="儲藏室")
        new_img = st.text_input("圖片網址 (選填)")
        
        if st.form_submit_button("確認新增", type="primary"):
            if new_name and new_uid:
                new_row = pd.DataFrame([{
                    "uid": new_uid, "name": new_name, "category": new_cat,
                    "status": new_status, "borrower": "", "location": new_loc,
                    "image_url": new_img,
                    "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }])
                # 更新資料
                updated_df = pd.concat([current_df, new_row], ignore_index=True)
                save_data(updated_df)
                st.toast(f"🎉 成功新增：{new_name}")
                st.rerun() # 重新整理畫面
            else:
                st.error("名稱與編號為必填欄位！")

# ==========================================
#  頁面 1：登入
# ==========================================
def login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<p class='login-title'>🔐 管理員登入</p>", unsafe_allow_html=True)
        with st.container(border=True):
            st.text_input("密碼", type="password", key="password_input")
            b1, b2 = st.columns(2)
            with b1: st.button("返回首頁", on_click=go_to_home)
            with b2: st.button("登入", type="primary", on_click=perform_login)

# ==========================================
#  頁面 2：主畫面
# ==========================================
def main_page():
    # 1. 載入資料
    with st.spinner('🔄 同步雲端資料中...'):
        df = load_data()
    if 'image_url' not in df.columns: df['image_url'] = ""
    df = df.astype(str)

    # --- 頂部導覽列 (Navbar) ---
    # 改為：左邊標題，右邊放「新增」與「登出」按鈕
    col_logo, col_space, col_actions = st.columns([6, 2, 2])
    
    with col_logo:
        st.title("📦 團隊器材管理系統")
    
    with col_actions:
        # 如果是管理員，顯示「新增」和「登出」兩個按鈕
        if st.session_state.is_admin:
            c_add, c_logout = st.columns(2)
            if c_add.button("➕ 新增", type="secondary"):
                show_add_modal(df) # 呼叫彈出視窗函數
            c_logout.button("登出", on_click=perform_logout)
        else:
            st.button("🔐 管理員登入", type="primary", on_click=go_to_login)

    if st.session_state.is_admin:
        st.success("目前身分：👨‍💻 管理員 (可編輯模式)")

    # --- 儀表板 ---
    st.divider()
    total = len(df)
    avail = len(df[df['status'] == '在庫'])
    mainten = len(df[df['status'] == '維修中'])
    borrow = len(df[df['status'] == '借出中'])

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 總數", total)
    m2.metric("✅ 可用", avail)
    m3.metric("🛠️ 維修", mainten)
    m4.metric("👤 借出", borrow)

    # --- 搜尋列 (獨立一行，更乾淨) ---
    st.markdown("### 🔎 器材查詢")
    search_query = st.text_input("搜尋關鍵字...", label_visibility="collapsed", placeholder="輸入名稱或編號...")

    # --- 卡片列表 ---
    if search_query:
        filtered_df = df[df['name'].str.contains(search_query, case=False) | df['uid'].str.contains(search_query, case=False)]
    else:
        filtered_df = df

    if not filtered_df.empty:
        st.write("") # 留點白
        cols = st.columns(3)
        for idx, row in filtered_df.iterrows():
            with cols[idx % 3]:
                with st.container(border=True):
                    # 圖片與資訊
                    img_link = row['image_url'] if row['image_url'].startswith('http') else "https://cdn-icons-png.flaticon.com/512/4992/4992482.png"
                    st.image(img_link, use_container_width=True)
                    st.markdown(f"### {row['name']}")
                    st.caption(f"編號: {row['uid']} | 位置: {row['location']}")
                    
                    status_color = "green" if row['status'] == "在庫" else "red" if row['status'] == "借出中" else "orange"
                    st.markdown(f":{status_color}[● {row['status']}]")
                    
                    # 管理功能
                    if st.session_state.is_admin:
                        with st.expander("⚙️ 管理"):
                            new_status_card = st.selectbox("狀態", ["在庫", "借出中", "維修中", "報廢"], key=f"s_{row['uid']}", index=["在庫", "借出中", "維修中", "報廢"].index(row['status']))
                            new_borrower = st.text_input("借用人", value=row['borrower'], key=f"b_{row['uid']}")
                            
                            b_up, b_del = st.columns(2)
                            if b_up.button("更新", key=f"btn_{row['uid']}"):
                                df.loc[df['uid'] == row['uid'], 'status'] = new_status_card
                                df.loc[df['uid'] == row['uid'], 'borrower'] = new_borrower
                                save_data(df)
                                st.rerun()
                            if b_del.button("刪除", key=f"del_{row['uid']}", type="primary"):
                                df = df[df['uid'] != row['uid']]
                                save_data(df)
                                st.rerun()
                    else:
                        if row['status'] == "借出中":
                            st.info(f"借用人: {row['borrower']}")
    else:
        st.info("沒有找到符合的器材 🐢")

# --- 路由 ---
if st.session_state.current_page == "login":
    login_page()
else:
    main_page()