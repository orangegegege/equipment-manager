import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time

# --- 1. Supabase 連線設定 ---
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
    if not file: return None
    try:
        bucket_name = st.secrets["SUPABASE"]["BUCKET"]
        file_ext = file.name.split('.')[-1]
        file_name = f"{int(time.time())}_{file.name}"
        
        supabase.storage.from_(bucket_name).upload(
            path=file_name,
            file=file.getvalue(),
            file_options={"content-type": file.type}
        )
        return supabase.storage.from_(bucket_name).get_public_url(file_name)
    except Exception as e:
        st.error(f"圖片上傳失敗: {e}")
        return None

# --- 3. 資料庫操作 (CRUD) ---
def load_data():
    response = supabase.table("equipment").select("*").order("id", desc=True).execute()
    return pd.DataFrame(response.data)

def add_equipment_to_db(data_dict):
    supabase.table("equipment").insert(data_dict).execute()

def update_equipment_in_db(uid, updates):
    supabase.table("equipment").update(updates).eq("uid", uid).execute()

def delete_equipment_from_db(uid):
    supabase.table("equipment").delete().eq("uid", uid).execute()

# --- 頁面設定 ---
st.set_page_config(page_title="器材管理系統", layout="wide", page_icon="📦", initial_sidebar_state="collapsed")

# ==========================================
# 🎨 UI/UX 核心：App 質感 CSS 工程
# ==========================================
st.markdown("""
<style>
    /* 1. 背景色調調整：讓背景變淺灰，凸顯白色卡片 */
    .stApp {
        background-color: #F5F7F9;
    }

    /* 2. 「卡片化」設計核心 */
    /* 針對所有設定 border=True 的 container 進行美化 */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: white;
        border-radius: 12px; /* 圓角 */
        border: 1px solid #E0E0E0; /* 淡淡的邊框 */
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); /* App 質感陰影 */
        padding: 20px; /* 內距，讓內容不要貼邊 */
        margin-bottom: 20px; /* 卡片之間的距離 */
    }

    /* 3. 按鈕美化 */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        border: none;
        height: 45px; /* 增加按鈕高度，手機好按 */
        transition: all 0.2s;
    }
    /* 主要按鈕 (紅色/主色) */
    div[data-testid="stButton"] button[kind="primary"] {
        box-shadow: 0 2px 4px rgba(255, 75, 75, 0.2);
    }

    /* 4. 標題與文字優化 */
    h1, h2, h3 {
        color: #1F2937; /* 深灰黑色，比純黑更有質感 */
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* 5. 圖片圓角 */
    img {
        border-radius: 8px;
    }

    /* 6. 手機版優化 (Mobile Responsive) */
    @media (max-width: 640px) {
        /* 在手機上，讓左右並排的按鈕強制保持並排，增加操作便利性 */
        div[data-testid="stHorizontalBlock"]:has(button) {
            flex-wrap: nowrap !important;
            gap: 10px !important;
        }
        /* 修正手機字體大小，避免縮太小 */
        div[data-testid="stMarkdownContainer"] p {
            font-size: 16px !important;
        }
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
#  彈出視窗：新增器材
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
        uploaded_file = st.file_uploader("上傳器材照片", type=['jpg', 'png', 'jpeg'])
        
        if st.form_submit_button("確認新增", type="primary", use_container_width=True):
            if new_name and new_uid:
                img_url = None
                if uploaded_file:
                    with st.spinner("上傳中..."):
                        img_url = upload_image(uploaded_file)
                
                new_data = {
                    "uid": new_uid, "name": new_name, "category": new_cat,
                    "status": new_status, "borrower": "", "location": new_loc,
                    "image_url": img_url,
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
                }
                try:
                    add_equipment_to_db(new_data)
                    st.toast(f"🎉 成功新增：{new_name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"錯誤: {e}")
            else:
                st.error("名稱與編號為必填！")

# ==========================================
#  頁面 1：登入頁 (卡片化)
# ==========================================
def login_page():
    # 使用 columns 把內容擠到中間，且垂直置中
    _, center_col, _ = st.columns([1, 4, 1]) # 手機上這會自動調整
    
    with center_col:
        st.markdown("<br><br>", unsafe_allow_html=True) # 上方留白
        
        # 🟦 登入卡片開始
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center;'>🔐 管理員登入</h2>", unsafe_allow_html=True)
            st.markdown("---")
            st.text_input("請輸入密碼", type="password", key="password_input")
            st.markdown("<br>", unsafe_allow_html=True)
            
            # 按鈕並排
            b1, b2 = st.columns(2)
            with b1: st.button("返回首頁", on_click=go_to_home, use_container_width=True)
            with b2: st.button("登入系統", type="primary", on_click=perform_login, use_container_width=True)
        # 🟦 登入卡片結束

# ==========================================
#  頁面 2：主控台 (卡片化列表)
# ==========================================
def main_page():
    # 讀取資料
    with st.spinner('連線中...'):
        df = load_data()
    
    # --- 頂部導覽列 (Navbar) ---
    c_title, c_act = st.columns([7, 3])
    with c_title:
        st.title("📦 器材管理系統")
    with c_act:
        if st.session_state.is_admin:
            c1, c2 = st.columns(2)
            c1.button("➕ 新增", on_click=show_add_modal, use_container_width=True)
            c2.button("登出", on_click=perform_logout, use_container_width=True)
        else:
            st.button("🔐 管理員登入", type="primary", on_click=go_to_login, use_container_width=True)

    if st.session_state.is_admin:
        st.info("👋 歡迎回來，管理員！")

    # --- 數據儀表板 (獨立卡片區) ---
    if not df.empty:
        total = len(df)
        avail = len(df[df['status'] == '在庫'])
        mainten = len(df[df['status'] == '維修中'])
        borrow = len(df[df['status'] == '借出中'])
    else:
        total = avail = mainten = borrow = 0

    # 每個數據都是一個小卡片
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        with st.container(border=True): # 🟦 卡片
            st.metric("📦 總器材", total)
    with m2:
        with st.container(border=True): # 🟦 卡片
            st.metric("✅ 可用", avail)
    with m3:
        with st.container(border=True): # 🟦 卡片
            st.metric("🛠️ 維修中", mainten)
    with m4:
        with st.container(border=True): # 🟦 卡片
            st.metric("👤 借出中", borrow)

    # --- 搜尋列 ---
    st.markdown("### 🔎 搜尋器材")
    search_query = st.text_input("search", label_visibility="collapsed", placeholder="輸入關鍵字 (如：相機、CAM-01)...")

    # --- 器材列表 (網格卡片) ---
    if not df.empty:
        if search_query:
            filtered_df = df[df['name'].str.contains(search_query, case=False) | df['uid'].str.contains(search_query, case=False)]
        else:
            filtered_df = df

        if not filtered_df.empty:
            st.markdown("<br>", unsafe_allow_html=True)
            
            # 使用 container 來排版
            cols = st.columns(3) # 電腦版 3 欄，手機會自動變成 1 欄
            
            for idx, row in filtered_df.iterrows():
                with cols[idx % 3]:
                    # 🟦 這裡就是「每一項器材」的卡片
                    with st.container(border=True):
                        # 圖片區
                        img_link = row['image_url'] if row['image_url'] else "https://cdn-icons-png.flaticon.com/512/4992/4992482.png"
                        st.image(img_link, use_container_width=True)
                        
                        # 標題與標籤
                        st.subheader(row['name'])
                        
                        # 狀態標籤 (Badge)
                        status_map = {"在庫": "green", "借出中": "red", "維修中": "orange", "報廢": "grey"}
                        s_color = status_map.get(row['status'], "blue")
                        st.markdown(f":{s_color}-background[{row['status']}]　<span style='color:grey; font-size:0.9em'>#{row['uid']}</span>", unsafe_allow_html=True)
                        
                        st.markdown(f"**位置**: {row['location']}")
                        
                        # 若借出中，顯示醒目的借用人
                        if row['status'] == "借出中":
                            st.warning(f"👤 借用人: {row['borrower']}")

                        # 管理區塊
                        if st.session_state.is_admin:
                            st.markdown("---") # 分隔線
                            with st.expander("⚙️ 編輯/管理"):
                                new_status = st.selectbox("狀態", ["在庫", "借出中", "維修中", "報廢"], key=f"s_{row['uid']}", index=["在庫", "借出中", "維修中", "報廢"].index(row['status']))
                                current_b = row['borrower'] if row['borrower'] else ""
                                new_b = st.text_input("借用人", value=current_b, key=f"b_{row['uid']}")
                                
                                b_up, b_del = st.columns(2)
                                with b_up:
                                    if st.button("更新", key=f"up_{row['uid']}", use_container_width=True):
                                        update_equipment_in_db(row['uid'], {"status": new_status, "borrower": new_b})
                                        st.toast("更新成功")
                                        st.rerun()
                                with b_del:
                                    if st.button("刪除", key=f"del_{row['uid']}", type="primary", use_container_width=True):
                                        delete_equipment_from_db(row['uid'])
                                        st.toast("已刪除")
                                        st.rerun()
    else:
        st.info("資料庫目前是空的，請點擊右上角新增器材！")

# --- 路由 ---
if st.session_state.current_page == "login":
    login_page()
else:
    main_page()
