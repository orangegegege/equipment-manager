import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time

# --- 1. Supabase 連線設定 ---
# 使用 st.cache_resource 確保連線只會建立一次，不會重複連線
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE"]["URL"]
        key = st.secrets["SUPABASE"]["KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase 連線失敗，請檢查 secrets 設定: {e}")
        return None

supabase: Client = init_connection()

# --- 2. 核心功能：圖片上傳與處理 ---
def upload_image(file):
    """將圖片上傳至 Supabase Storage 並回傳公開連結"""
    if not file:
        return None
    try:
        bucket_name = st.secrets["SUPABASE"]["BUCKET"]
        # 為了避免檔名重複，加上時間戳記
        file_ext = file.name.split('.')[-1]
        file_name = f"{int(time.time())}_{file.name}"
        
        # 上傳檔案 (讀取二進位資料)
        supabase.storage.from_(bucket_name).upload(
            path=file_name,
            file=file.getvalue(),
            file_options={"content-type": file.type}
        )
        
        # 取得公開網址
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        return public_url
    except Exception as e:
        st.error(f"圖片上傳失敗: {e}")
        return None

# --- 3. 資料庫操作 (CRUD) ---
def load_data():
    """讀取所有資料"""
    # 這裡對應你在 Supabase 建立的 table 名稱 'equipment'
    response = supabase.table("equipment").select("*").order("id", desc=True).execute()
    return pd.DataFrame(response.data)

def add_equipment_to_db(data_dict):
    """新增資料"""
    supabase.table("equipment").insert(data_dict).execute()

def update_equipment_in_db(uid, updates):
    """更新資料 (根據 uid)"""
    supabase.table("equipment").update(updates).eq("uid", uid).execute()

def delete_equipment_from_db(uid):
    """刪除資料 (根據 uid)"""
    supabase.table("equipment").delete().eq("uid", uid).execute()

# --- 頁面設定 ---
st.set_page_config(page_title="器材管理系統", layout="wide", page_icon="📦", initial_sidebar_state="collapsed")

# --- CSS 美化 ---
st.markdown("""
<style>
    .stButton>button {width: 100%; border-radius: 8px;}
    div[data-testid="stMetricValue"] {font-size: 28px;}
    div[data-testid="stDialog"] {backdrop-filter: blur(8px) !important; background-color: rgba(0, 0, 0, 0.4) !important;}
    .login-title {text-align: center; font-size: 40px; font-weight: bold; margin-bottom: 20px;}
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
#  彈出視窗：新增器材 (支援圖片上傳！)
# ==========================================
@st.dialog("➕ 新增一項器材")
def show_add_modal():
    st.info("填寫資訊並上傳圖片 (支援 JPG/PNG)")
    
    with st.form("add_form", clear_on_submit=True):
        new_name = st.text_input("器材名稱", placeholder="例如：Canon R6")
        new_uid = st.text_input("器材編號", placeholder="例如：CAM-002")
        
        c1, c2 = st.columns(2)
        new_cat = c1.selectbox("分類", ["攝影器材", "燈光音響", "線材耗材", "電腦週邊", "其他"])
        new_status = c2.selectbox("狀態", ["在庫", "借出中", "維修中", "報廢"])
        
        new_loc = st.text_input("存放位置", value="儲藏室")
        
        # 🔥 這裡就是你要的：直接上傳檔案！
        uploaded_file = st.file_uploader("上傳器材照片", type=['jpg', 'png', 'jpeg'])
        
        submitted = st.form_submit_button("確認新增", type="primary")
        
        if submitted:
            if new_name and new_uid:
                img_url = None
                # 如果有上傳圖片，先處理上傳
                if uploaded_file:
                    with st.spinner("正在上傳圖片至雲端..."):
                        img_url = upload_image(uploaded_file)
                
                # 準備寫入資料庫的內容
                new_data = {
                    "uid": new_uid,
                    "name": new_name,
                    "category": new_cat,
                    "status": new_status,
                    "borrower": "",
                    "location": new_loc,
                    "image_url": img_url, # 存入剛產生的網址
                    # 如果你資料庫欄位叫 updated_at
		    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S") 

		    # 或者如果你剛剛去資料庫新增了 update_time 欄位，那就不用改程式碼
                }
                
                try:
                    add_equipment_to_db(new_data)
                    st.toast(f"🎉 成功新增：{new_name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"寫入資料庫失敗: {e}")
            else:
                st.error("名稱與編號為必填欄位！")

# ==========================================
#  頁面邏輯 (Login & Main)
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

def main_page():
    # 讀取資料 (從 Supabase)
    with st.spinner('🔄 同步雲端資料中...'):
        df = load_data()
    
    # 頂部導覽
    col_logo, col_space, col_actions = st.columns([6, 2, 2])
    with col_logo: st.title("📦 團隊器材管理系統")
    with col_actions:
        if st.session_state.is_admin:
            c_add, c_logout = st.columns(2)
            if c_add.button("➕ 新增", type="secondary"):
                show_add_modal()
            c_logout.button("登出", on_click=perform_logout)
        else:
            st.button("🔐 管理員登入", type="primary", on_click=go_to_login)

    if st.session_state.is_admin: st.success("目前身分：👨‍💻 管理員")

    # 儀表板
    st.divider()
    if not df.empty:
        total = len(df)
        avail = len(df[df['status'] == '在庫'])
        mainten = len(df[df['status'] == '維修中'])
        borrow = len(df[df['status'] == '借出中'])
    else:
        total, avail, mainten, borrow = 0, 0, 0, 0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📦 總數", total)
    m2.metric("✅ 可用", avail)
    m3.metric("🛠️ 維修", mainten)
    m4.metric("👤 借出", borrow)

    # 搜尋與列表
    st.markdown("### 🔎 器材查詢")
    search_query = st.text_input("搜尋關鍵字...", label_visibility="collapsed", placeholder="輸入名稱或編號...")

    if not df.empty:
        if search_query:
            # Pandas 篩選
            filtered_df = df[df['name'].str.contains(search_query, case=False) | df['uid'].str.contains(search_query, case=False)]
        else:
            filtered_df = df

        if not filtered_df.empty:
            st.write("")
            cols = st.columns(3)
            for idx, row in filtered_df.iterrows():
                with cols[idx % 3]:
                    with st.container(border=True):
                        # 圖片顯示 (處理 None 的情況)
                        img_link = row['image_url'] if row['image_url'] else "https://cdn-icons-png.flaticon.com/512/4992/4992482.png"
                        st.image(img_link, use_container_width=True)
                        
                        st.markdown(f"### {row['name']}")
                        st.caption(f"編號: {row['uid']} | 位置: {row['location']}")
                        
                        status_color = "green" if row['status'] == "在庫" else "red" if row['status'] == "借出中" else "orange"
                        st.markdown(f":{status_color}[● {row['status']}]")
                        
                        # 管理功能 (更新 Supabase)
                        if st.session_state.is_admin:
                            with st.expander("⚙️ 管理"):
                                new_status_card = st.selectbox("狀態", ["在庫", "借出中", "維修中", "報廢"], key=f"s_{row['uid']}", index=["在庫", "借出中", "維修中", "報廢"].index(row['status']))
                                # 處理 borrower 為 None 的情況
                                current_borrower = row['borrower'] if row['borrower'] else ""
                                new_borrower = st.text_input("借用人", value=current_borrower, key=f"b_{row['uid']}")
                                
                                b_up, b_del = st.columns(2)
                                if b_up.button("更新", key=f"btn_{row['uid']}"):
                                    update_equipment_in_db(row['uid'], {"status": new_status_card, "borrower": new_borrower})
                                    st.toast("更新成功！")
                                    st.rerun()
                                if b_del.button("刪除", key=f"del_{row['uid']}", type="primary"):
                                    delete_equipment_from_db(row['uid'])
                                    st.toast("已刪除")
                                    st.rerun()
                        else:
                            if row['status'] == "借出中":
                                st.info(f"借用人: {row['borrower']}")
    else:
        st.info("目前資料庫是空的，請新增器材！")

# --- 路由 ---
if st.session_state.current_page == "login":
    login_page()
else:
    main_page()