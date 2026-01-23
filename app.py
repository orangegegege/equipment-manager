import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time

# ==========================================
# 🎨 [色彩與 Logo 設定] 改這裡！
# ==========================================
# 1. 你的 LOGO 圖片連結 (請換成你自己的)
# 如果沒有圖片，暫時用這個預設圖
LOGO_URL = "https://drive.google.com/file/d/1VeP-Dxdh6krNGThN9_cRNHGPHIv9-93z/view?usp=sharing" 

# 2. 導覽列設定
NAV_BACKGROUND = "#E89B00"  # 導覽列背景色 (參考圖是白色)
NAV_TEXT_COLOR = "#333333"  # 文字顏色 (深灰)

# 3. 網頁背景
PAGE_BACKGROUND = "#F8F9FA" # 淺灰底，凸顯白色的導覽列

# 4. 狀態標籤顏色
STATUS_COLORS = {
    "在庫":   {"bg": "#E6F4EA", "text": "#137333"},
    "借出中": {"bg": "#FCE8E6", "text": "#C5221F"},
    "維修中": {"bg": "#FEF7E0", "text": "#B06000"},
    "報廢":   {"bg": "#F1F3F4", "text": "#5F6368"}
}
# ==========================================

# --- 1. Supabase 連線 ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE"]["URL"]
        key = st.secrets["SUPABASE"]["KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase 連線失敗: {e}")
        return None

supabase: Client = init_connection()

# --- 2. 圖片上傳 ---
def upload_image(file):
    if not file: return None
    try:
        bucket_name = st.secrets["SUPABASE"]["BUCKET"]
        file_ext = file.name.split('.')[-1]
        file_name = f"{int(time.time())}_{file.name}"
        supabase.storage.from_(bucket_name).upload(file_name, file.getvalue(), file_options={"content-type": file.type})
        return supabase.storage.from_(bucket_name).get_public_url(file_name)
    except Exception as e:
        st.error(f"上傳失敗: {e}")
        return None

# --- 3. 資料庫 CRUD ---
def load_data():
    response = supabase.table("equipment").select("*").order("id", desc=True).execute()
    return pd.DataFrame(response.data)

def add_equipment_to_db(data): supabase.table("equipment").insert(data).execute()
def update_equipment_in_db(uid, updates): supabase.table("equipment").update(updates).eq("uid", uid).execute()
def delete_equipment_from_db(uid): supabase.table("equipment").delete().eq("uid", uid).execute()

# --- 頁面設定 ---
st.set_page_config(page_title="器材管理系統", layout="wide", page_icon="📦", initial_sidebar_state="collapsed")

# ==========================================
# 🛠️ CSS 樣式表 (Header 專用修復版)
# ==========================================
st.markdown(f"""
<style>
    /* 1. 隱藏 Streamlit 預設 Header */
    header[data-testid="stHeader"] {{ display: none; }}

    /* 2. 網頁背景 */
    .stApp, div[data-testid="stAppViewContainer"] {{
        background-color: {PAGE_BACKGROUND} !important;
    }}

    /* 3. ✨ 置頂導覽列 (Sticky Navbar) ✨ */
    /* 這次我們鎖定包含 'navbar-container' class 的區塊 */
    div[data-testid="stVerticalBlock"]:has(.navbar-marker) {{
        position: sticky;
        top: 0;
        z-index: 99999;
        background-color: {NAV_BACKGROUND} !important;
        
        /* 像你的參考圖一樣，加一點陰影 */
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        border-bottom: 1px solid #E5E7EB;
        
        /* 調整內距，讓它看起來像個 Header */
        padding: 10px 20px;
        margin-top: -60px; /* 把原本 Streamlit 上方的空白抵銷掉 */
    }}

    /* 4. 一般卡片 (內容區) */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}

    /* 5. 按鈕樣式 (仿照你的參考圖，圓角大一點) */
    .stButton > button {{
        border-radius: 50px !important; /* 膠囊形狀 */
        height: 40px !important;
        font-weight: 600 !important;
        border: 1px solid #ddd !important;
        background-color: white !important;
        color: #333 !important;
    }}
    /* 主要按鈕 (紅色/橘色) */
    .stButton > button[kind="primary"] {{
        background-color: #E85D04 !important; /* 類似你圖中的橘紅色 */
        color: white !important;
        border: none !important;
    }}

    /* 6. 手機版優化 */
    @media (max-width: 640px) {{
        /* 讓圖片不要太大 */
        img {{ max-width: 100% !important; }}
        /* 導覽列在手機上緊貼兩側 */
        div[data-testid="stVerticalBlock"]:has(.navbar-marker) {{
            padding: 10px 10px;
        }}
    }}
</style>
""", unsafe_allow_html=True)

# --- 狀態管理 ---
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'current_page' not in st.session_state: st.session_state.current_page = "home"
def go_to(page): st.session_state.current_page = page
def perform_logout(): 
    st.session_state.is_admin = False
    go_to("home")
def perform_login():
    if st.session_state.password_input == st.secrets["ADMIN_PASSWORD"]:
        st.session_state.is_admin = True
        go_to("home")
    else: st.error("密碼錯誤")

# ==========================================
# ✨ 導覽列組件 (Logo + Menu)
# ==========================================
def render_navbar():
    # 這裡使用普通的 container，但塞入一個標記讓 CSS 抓
    with st.container():
        st.markdown('<div class="navbar-marker"></div>', unsafe_allow_html=True)
        
        # 左右佈局：左邊 Logo，右邊選單
        # vertical_alignment="center" 讓 Logo 跟按鈕垂直置中對齊
        col_logo, col_menu = st.columns([1, 3], vertical_alignment="center")
        
        with col_logo:
            # 🔥 這裡顯示你的 LOGO！
            # width=150 可以調整 Logo 大小
            st.image(LOGO_URL, width=150) 
            
        with col_menu:
            # 使用 columns 把按鈕推到最右邊 (透過空的 col)
            _, buttons = st.columns([4, 2]) 
            
            with buttons:
                if st.session_state.is_admin:
                    b1, b2 = st.columns(2)
                    b1.button("➕ 新增器材", on_click=show_add_modal, use_container_width=True)
                    b2.button("登出", on_click=perform_logout, type="primary", use_container_width=True)
                else:
                    st.button("🔐 管理員登入", on_click=lambda: go_to("login"), type="primary", use_container_width=True)

# ==========================================
# 彈窗：新增器材
# ==========================================
@st.dialog("➕ 新增器材", width="small")
def show_add_modal():
    st.caption("填寫資訊並上傳照片")
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("名稱")
        uid = st.text_input("編號")
        c1, c2 = st.columns(2)
        cat = c1.selectbox("分類", ["攝影", "燈光", "線材", "電腦", "其他"])
        status = c2.selectbox("狀態", ["在庫", "借出中", "維修中", "報廢"])
        loc = st.text_input("位置", value="儲藏室")
        file = st.file_uploader("照片", type=['jpg','png'])
        if st.form_submit_button("新增", type="primary", use_container_width=True):
            if name and uid:
                url = upload_image(file) if file else None
                add_equipment_to_db({
                    "uid": uid, "name": name, "category": cat, "status": status,
                    "borrower": "", "location": loc, "image_url": url,
                    "updated_at": datetime.now().strftime("%Y-%m-%d")
                })
                st.toast("新增成功"); st.rerun()

# ==========================================
# 頁面：主控台
# ==========================================
def main_page():
    render_navbar() # 顯示置頂 Header
    
    # 為了不被 Header 擋住，加一點留白
    st.write("") 
    
    df = load_data()
    
    # 儀表板
    if not df.empty:
        total = len(df); avail = len(df[df['status']=='在庫'])
        m1, m2, m3, m4 = st.columns(4)
        with m1: 
            with st.container(border=True): st.metric("📦 總數", total)
        with m2: 
            with st.container(border=True): st.metric("✅ 可用", avail)
        with m3: 
            with st.container(border=True): st.metric("🛠️ 維修", len(df[df['status']=='維修中']))
        with m4: 
            with st.container(border=True): st.metric("👤 借出", len(df[df['status']=='借出中']))

    # 搜尋區
    st.write("")
    with st.container(border=True):
        search = st.text_input("🔍 搜尋器材...", placeholder="輸入關鍵字...", label_visibility="collapsed")

    # 列表區
    if not df.empty:
        res = df[df['name'].str.contains(search, case=False) | df['uid'].str.contains(search, case=False)] if search else df
        st.write("")
        cols = st.columns(3)
        for i, row in res.iterrows():
            with cols[i%3]:
                with st.container(border=True):
                    # 圖片區
                    img = row['image_url'] if row['image_url'] else "https://cdn-icons-png.flaticon.com/512/4992/4992482.png"
                    st.markdown(f'<div style="height:200px; overflow:hidden; border-radius:8px; display:flex; justify-content:center; background:#f0f2f6; margin-bottom:10px;"><img src="{img}" style="height:100%; width:100%; object-fit:cover;"></div>', unsafe_allow_html=True)
                    
                    st.markdown(f"#### {row['name']}")
                    st.caption(f"#{row['uid']} | 📍 {row['location']}")
                    
                    # 狀態標籤
                    style = STATUS_COLORS.get(row['status'], {"bg": "#eee", "text": "#000"})
                    st.markdown(f'<span style="background:{style["bg"]}; color:{style["text"]}; padding:4px 10px; border-radius:12px; font-weight:bold; font-size:12px">● {row['status']}</span>', unsafe_allow_html=True)

                    if row['status'] == '借出中': st.warning(f"👤 {row['borrower']}")

                    if st.session_state.is_admin:
                        st.markdown("---")
                        with st.expander("⚙️ 管理"):
                            ns = st.selectbox("狀態", ["在庫","借出中","維修中","報廢"], key=f"s{row['uid']}", index=["在庫","借出中","維修中","報廢"].index(row['status']))
                            nb = st.text_input("借用人", value=row['borrower'] or "", key=f"b{row['uid']}")
                            b1, b2 = st.columns(2)
                            if b1.button("更新", key=f"u{row['uid']}", use_container_width=True):
                                update_equipment_in_db(row['uid'], {"status":ns, "borrower":nb}); st.toast("更新成功"); st.rerun()
                            if b2.button("刪除", key=f"d{row['uid']}", type="primary", use_container_width=True):
                                delete_equipment_from_db(row['uid']); st.toast("已刪除"); st.rerun()
    else: st.info("尚無資料")

# ==========================================
# 頁面：登入
# ==========================================
def login_page():
    render_navbar()
    _, c, _ = st.columns([1,5,1])
    with c:
        st.write("")
        st.write("")
        with st.container(border=True):
            st.markdown("<h2 style='text-align:center'>🔐 管理員登入</h2>", unsafe_allow_html=True)
            st.text_input("密碼", type="password", key="password_input")
            b1, b2 = st.columns(2)
            b1.button("取消", on_click=lambda: go_to("home"), use_container_width=True)
            b2.button("登入", type="primary", on_click=perform_login, use_container_width=True)

if st.session_state.current_page == "login": login_page()
else: main_page()

