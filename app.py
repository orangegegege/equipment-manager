import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time

# ==========================================
# 🎨 [色彩控制台] 改這裡，顏色一定會變！
# ==========================================
# 1. 網頁背景 (推薦淺灰 F1F5F9 或純白 FFFFFF)
PAGE_BG = "#F8F9FA"

# 2. 頂部導覽列 (黑色膠囊)
NAV_BG = "#E89B00"       # 背景色 (深灰)
NAV_TEXT = "#FFFFFF"     # 文字色 (白)

# 3. 內容卡片 (顯示器材/數據的地方)
CARD_BG = "#FFFFFF"      # 背景色 (白)
CARD_BORDER = "#E5E7EB"  # 邊框色 (淺灰)

# 4. 狀態標籤顏色 (背景色, 文字色)
STATUS_COLORS = {
    "在庫":   {"bg": "#E6F4EA", "text": "#137333"}, # 綠
    "借出中": {"bg": "#FCE8E6", "text": "#C5221F"}, # 紅
    "維修中": {"bg": "#FEF7E0", "text": "#B06000"}, # 黃
    "報廢":   {"bg": "#F1F3F4", "text": "#5F6368"}  # 灰
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
# 🛠️ CSS 強制注入 (使用 !important 覆蓋預設值)
# ==========================================
st.markdown(f"""
<style>
    /* 1. 隱藏預設 Header */
    header[data-testid="stHeader"] {{ display: none; }}

    /* 2. 強制設定全頁背景顏色 */
    .stApp, div[data-testid="stAppViewContainer"] {{
        background-color: {PAGE_BG} !important;
    }}

    /* 3. 置頂導覽列樣式 (Sticky Header) */
    /* 我們稍後會在 HTML 裡埋入一個 id="sticky-header" */
    /* CSS 選擇器：找到包含 #sticky-header 的父層容器 */
    div[data-testid="stVerticalBlock"]:has(#sticky-header) {{
        position: sticky;
        top: 10px;
        z-index: 9999;
        background-color: {NAV_BG} !important;
        color: {NAV_TEXT} !important;
        border-radius: 50px;
        padding: 15px 25px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        margin-bottom: 30px;
        border: 1px solid rgba(255,255,255,0.1);
    }}

    /* 強制讓導覽列裡的文字變色 */
    div[data-testid="stVerticalBlock"]:has(#sticky-header) h3,
    div[data-testid="stVerticalBlock"]:has(#sticky-header) span,
    div[data-testid="stVerticalBlock"]:has(#sticky-header) p {{
        color: {NAV_TEXT} !important;
    }}

    /* 4. 一般內容卡片 (Card) */
    /* 選擇器：針對有 .custom-card 標記的容器 */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {CARD_BG} !important;
        border: 1px solid {CARD_BORDER} !important;
        border-radius: 16px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02) !important;
        padding: 20px !important;
    }}

    /* 5. 按鈕樣式 (加強高度，好按) */
    .stButton > button {{
        height: 48px !important;
        border-radius: 10px !important;
        font-weight: bold !important;
        border: none !important;
    }}

    /* 6. 手機版面修復 (避免縮小) */
    @media (max-width: 640px) {{
        /* 讓導覽列貼頂，變成長方形 */
        div[data-testid="stVerticalBlock"]:has(#sticky-header) {{
            top: 0 !important;
            border-radius: 0 0 15px 15px !important;
            margin: 0 -1rem 20px -1rem !important; /* 拉寬填滿 */
            padding: 15px !important;
        }}
        /* 避免圖片撐開版面 */
        img {{ max-width: 100% !important; }}
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
# 組件：置頂導覽列 (純淨版，無 border=True)
# ==========================================
def render_navbar():
    # 這裡不要用 border=True，避免產生黑框
    # 我們用 CSS 的 :has(#sticky-header) 來幫它上色
    with st.container():
        # 這是一個隱形鉤子，用來讓 CSS 抓到這個區塊
        st.markdown('<div id="sticky-header"></div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns([3, 2], vertical_alignment="center")
        with c1:
            st.markdown("### 📦 團隊器材中心")
        with c2:
            if st.session_state.is_admin:
                b1, b2 = st.columns(2)
                b1.button("➕ 新增", on_click=show_add_modal, use_container_width=True, type="secondary")
                b2.button("登出", on_click=perform_logout, use_container_width=True, type="primary")
            else:
                _, b_log = st.columns([1, 2])
                b_log.button("🔐 管理員登入", on_click=lambda: go_to("login"), use_container_width=True)

# ==========================================
# 組件：新增視窗
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
    render_navbar() # 顯示置頂導覽列
    df = load_data()
    
    # 儀表板 (使用 container(border=True) 產生卡片，CSS 會負責美化它)
    if not df.empty:
        total = len(df); avail = len(df[df['status']=='在庫'])
        st.write("")
        m1, m2, m3, m4 = st.columns(4)
        with m1: 
            with st.container(border=True): st.metric("📦 總數", total)
        with m2: 
            with st.container(border=True): st.metric("✅ 可用", avail)
        with m3: 
            with st.container(border=True): st.metric("🛠️ 維修", len(df[df['status']=='維修中']))
        with m4: 
            with st.container(border=True): st.metric("👤 借出", len(df[df['status']=='借出中']))

    # 搜尋區 (卡片化)
    st.write("")
    with st.container(border=True):
        search = st.text_input("🔍 搜尋", placeholder="輸入關鍵字...", label_visibility="collapsed")

    # 列表區
    if not df.empty:
        res = df[df['name'].str.contains(search, case=False) | df['uid'].str.contains(search, case=False)] if search else df
        st.write("")
        cols = st.columns(3)
        for i, row in res.iterrows():
            with cols[i%3]:
                # 這裡的 border=True 會被 CSS 抓到，並套用 CARD_BG 顏色
                with st.container(border=True):
                    # 圖片固定高度
                    img = row['image_url'] if row['image_url'] else "https://cdn-icons-png.flaticon.com/512/4992/4992482.png"
                    st.markdown(f'<div style="height:200px; overflow:hidden; border-radius:8px; display:flex; justify-content:center; background:#f0f2f6; margin-bottom:10px;"><img src="{img}" style="height:100%; width:100%; object-fit:cover;"></div>', unsafe_allow_html=True)
                    
                    st.markdown(f"#### {row['name']}")
                    st.caption(f"#{row['uid']} | 📍 {row['location']}")
                    
                    # 狀態標籤 (使用上面的變數)
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
        with st.container(border=True):
            st.markdown("<h2 style='text-align:center'>🔐 管理員登入</h2>", unsafe_allow_html=True)
            st.text_input("密碼", type="password", key="password_input")
            b1, b2 = st.columns(2)
            b1.button("取消", on_click=lambda: go_to("home"), use_container_width=True)
            b2.button("登入", type="primary", on_click=perform_login, use_container_width=True)

if st.session_state.current_page == "login": login_page()
else: main_page()
