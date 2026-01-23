import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time

# ==========================================
# 🎨 [色彩控制台] 這裡設定顏色 (保證分開！)
# ==========================================

# 1. LOGO 設定
LOGO_URL = "https://cdn-icons-png.flaticon.com/512/2504/2504929.png"

# 2. 網頁大背景 (最底層的顏色)
# 建議：淺灰 (#F8F9FA) 或 純白 (#FFFFFF)
PAGE_BG_COLOR = "#E89B00"

# 3. 導覽列 (Header) 配色
# 建議：深色 (#2D3436) 或 品牌色 (#E89B00)
NAV_BG_COLOR = "#2D3436"
NAV_TEXT_COLOR = "#FFFFFF"

# 4. 內容卡片 (Card) 配色
# 建議：白色 (#FFFFFF)，這樣才像卡片
CARD_BG_COLOR = "#FFFFFF"
CARD_BORDER_COLOR = "#E5E7EB"

# 5. 狀態標籤顏色
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
# 🛠️ CSS 樣式表 (外科手術級隔離版)
# ==========================================
st.markdown(f"""
<style>
    /* 1. 隱藏預設 Header */
    header[data-testid="stHeader"] {{ display: none; }}

    /* 2. 設定「網頁大背景」顏色 */
    .stApp, [data-testid="stAppViewContainer"] {{
        background-color: {PAGE_BG_COLOR} !important;
    }}

    /* 3. ✨ [導覽列] 專屬樣式 (Fixed Header) ✨ */
    /* 我們鎖定包含 navbar-marker 的那個 borderWrapper */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.navbar-marker) {{
        position: fixed !important;  /* 強制固定在視窗頂部 */
        top: 0;
        left: 0;
        width: 100%;                 /* 橫跨整個螢幕 */
        z-index: 999999;             /* 確保在最上層 */
        
        background-color: {NAV_BG_COLOR} !important; /* 這裡只會改導覽列背景 */
        border: none !important;     /* 移除醜框線 */
        border-bottom: 1px solid rgba(0,0,0,0.1) !important;
        border-radius: 0 !important; /* 變成直角的長條 */
        
        padding: 0.5rem 2rem !important;
        margin: 0 !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }}

    /* 導覽列裡的文字顏色 */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.navbar-marker) * {{
        color: {NAV_TEXT_COLOR} !important;
    }}

    /* 4. ✨ [內容卡片] 專屬樣式 ✨ */
    /* 鎖定沒有 navbar-marker 的 borderWrapper -> 這就是下面的卡片 */
    div[data-testid="stVerticalBlockBorderWrapper"]:not(:has(.navbar-marker)) {{
        background-color: {CARD_BG_COLOR} !important; /* 這裡只會改卡片背景 */
        border: 1px solid {CARD_BORDER_COLOR} !important;
        border-radius: 12px !important;
        padding: 20px !important;
        margin-bottom: 16px !important;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }}

    /* 5. 按鈕樣式 */
    .stButton > button {{
        border-radius: 50px !important;
        height: 40px !important;
        font-weight: 600 !important;
        border: 1px solid #ddd !important;
    }}
    .stButton > button[kind="primary"] {{
        background-color: #E85D04 !important;
        color: white !important;
        border: none !important;
    }}
    
    /* 6. 手機版優化 */
    @media (max-width: 640px) {{
        /* 導覽列左右內距縮小 */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.navbar-marker) {{
            padding: 0.5rem 1rem !important;
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
# ✨ 導覽列組件 (Fixed Header)
# ==========================================
def render_navbar():
    # 使用 container(border=True) 創造一個獨立的 DOM 元素
    # CSS 會抓到它，把它變成 fixed header
    with st.container(border=True):
        st.markdown('<div class="navbar-marker"></div>', unsafe_allow_html=True)
        
        col_brand, col_menu = st.columns([2, 2], vertical_alignment="center")
        
        with col_brand:
            c1, c2 = st.columns([1, 4], vertical_alignment="center")
            with c1:
                st.image(LOGO_URL, width=40)
            with c2:
                # 標題 (強制不換行，避免被擠下去)
                st.markdown(f"<h3 style='margin:0; padding:0; color:inherit; white-space:nowrap;'>團隊器材中心</h3>", unsafe_allow_html=True)
        
        with col_menu:
            _, buttons = st.columns([1, 3])
            with buttons:
                if st.session_state.is_admin:
                    b1, b2 = st.columns(2)
                    b1.button("➕ 新增", on_click=show_add_modal, use_container_width=True)
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
    # 1. 渲染導覽列 (這會浮在最上面)
    render_navbar()
    
    # 🔥 關鍵修正：隱形墊片 (Spacer)
    # 這是一個 100px 高的空區塊，專門用來把內容往下推
    # 這樣你的第一排卡片才不會被導覽列擋住！
    st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)
    
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
                # 這裡的 container(border=True) 裡面沒有 navbar-marker
                # 所以 CSS 會把它當作「卡片」來上色 (白色背景)
                with st.container(border=True):
                    img = row['image_url'] if row['image_url'] else "https://cdn-icons-png.flaticon.com/512/4992/4992482.png"
                    st.markdown(f'<div style="height:200px; overflow:hidden; border-radius:8px; display:flex; justify-content:center; background:#f0f2f6; margin-bottom:10px;"><img src="{img}" style="height:100%; width:100%; object-fit:cover;"></div>', unsafe_allow_html=True)
                    
                    st.markdown(f"#### {row['name']}")
                    st.caption(f"#{row['uid']} | 📍 {row['location']}")
                    
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
    # 同樣需要墊片，不然登入框會被擋住
    st.markdown('<div style="height: 100px;"></div>', unsafe_allow_html=True)
    
    _, c, _ = st.columns([1,5,1])
    with c:
        with st.container(border=True):
            st.markdown("<h2 style='text-align:center'>🔐 管理員登入</h2>", unsafe_allow_html=True)
            st.text_input("密碼", type="password", key="password_input")
            b1, b2 = st.columns(2)
            b1.button("取消", on_click=lambda: go_to("home"), use_container_width=True)
            b2.button("登入", type="primary", on_click=perform_login, use_container_width=True)

if st.session_state.current_page == "login": login_page()
else: main_page()



