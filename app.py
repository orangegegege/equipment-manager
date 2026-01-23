import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time

# ==========================================
# 🎨 [設定區] 請在這裡調整顏色！ (改這裡一定會變)
# ==========================================
# 1. 整個網頁的背景顏色 (預設淺灰)
PAGE_BACKGROUND_COLOR = "#F8F9FA"

# 2. 置頂導覽列 (Header) 的背景顏色 (預設深灰)
HEADER_BG_COLOR = "#E89B00"

# 3. 導覽列文字顏色 (預設白)
HEADER_TEXT_COLOR = "#FFFFFF"

# 4. 卡片 (內容區塊) 的背景顏色 (預設白)
CARD_BG_COLOR = "#FFFFFF"

# 5. 狀態標籤的顏色設定 (背景色, 文字色)
STATUS_COLORS = {
    "在庫":   {"bg": "#E6F4EA", "text": "#137333"}, # 綠底綠字
    "借出中": {"bg": "#FCE8E6", "text": "#C5221F"}, # 紅底紅字
    "維修中": {"bg": "#FEF7E0", "text": "#B06000"}, # 黃底橘字
    "報廢":   {"bg": "#F1F3F4", "text": "#5F6368"}  # 灰底灰字
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
# 🛠️ CSS 注入 (自動讀取上面的設定)
# ==========================================
css_code = f"""
<style>
    /* 1. 隱藏預設 Header */
    header[data-testid="stHeader"] {{
        display: none;
    }}

    /* 2. 網頁背景設定 */
    .stApp {{
        background-color: {PAGE_BACKGROUND_COLOR};
    }}

    /* 3. 置頂導覽列 (Sticky Header) */
    /* 我們使用一個特殊的屬性選擇器來鎖定導覽列 */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.navbar-marker) {{
        position: sticky;
        top: 10px;
        z-index: 1000;
        background-color: {HEADER_BG_COLOR};
        border-radius: 12px;
        padding: 15px 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        margin-bottom: 20px;
        border: 1px solid rgba(255,255,255,0.1);
    }}

    /* 強制導覽列文字顏色 */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.navbar-marker) * {{
        color: {HEADER_TEXT_COLOR} !important;
    }}
    
    /* 4. 一般內容卡片 */
    div[data-testid="stVerticalBlockBorderWrapper"]:not(:has(.navbar-marker)) {{
        background-color: {CARD_BG_COLOR};
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid #E5E7EB;
    }}

    /* 5. 手機版面修復工程 (Critical Mobile Fix) */
    @media (max-width: 640px) {{
        /* 強制重置容器寬度，防止手機變成電腦版縮圖 */
        .stApp {{
            overflow-x: hidden; 
        }}
        
        /* 讓導覽列在手機上貼頂，不要浮空，節省空間 */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.navbar-marker) {{
            top: 0;
            margin: 0 -1rem 1rem -1rem; /* 拉寬填滿 */
            border-radius: 0 0 12px 12px;
            padding: 10px 15px;
        }}
        
        /* 確保按鈕在手機上好按，並保持並排 (如果空間允許) */
        div[data-testid="stHorizontalBlock"] {{
            gap: 0.5rem !important;
        }}
        
        /* 圖片容器寬度限制，防止撐開頁面 */
        img {{
            max-width: 100% !important;
        }}
    }}

    /* 6. 按鈕樣式優化 */
    .stButton > button {{
        border-radius: 8px;
        font-weight: 600;
        height: 45px;
        border: none;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }}
    
    /* 輸入框優化 */
    div[data-testid="stTextInput"] input {{
        border-radius: 8px;
    }}
</style>
"""
st.markdown(css_code, unsafe_allow_html=True)

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
# 組件：置頂導覽列
# ==========================================
def render_navbar():
    with st.container(border=True):
        # 標記：讓 CSS 抓到這個 container
        st.markdown('<div class="navbar-marker"></div>', unsafe_allow_html=True)
        
        # 使用 columns，電腦左右排，手機會自動變成適合的大小
        c_logo, c_menu = st.columns([3, 2], vertical_alignment="center")
        
        with c_logo:
            st.markdown("### 📦 團隊器材中心")
            
        with c_menu:
            if st.session_state.is_admin:
                b1, b2 = st.columns(2)
                b1.button("➕ 新增", on_click=show_add_modal, use_container_width=True, type="secondary")
                b2.button("登出", on_click=perform_logout, use_container_width=True, type="primary")
            else:
                # 靠右排版
                _, b_login = st.columns([1, 2])
                b_login.button("🔐 管理員登入", on_click=lambda: go_to("login"), use_container_width=True)

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
    # 1. 渲染置頂導覽列
    render_navbar()

    df = load_data()
    
    # 2. 數據儀表板 (在手機上會自動直排，因為我們移除了強制 CSS)
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

    # 3. 搜尋區
    st.write("")
    with st.container(border=True):
        search = st.text_input("🔍 搜尋", placeholder="輸入關鍵字...", label_visibility="collapsed")

    # 4. 列表區
    if not df.empty:
        res = df[df['name'].str.contains(search, case=False) | df['uid'].str.contains(search, case=False)] if search else df
        st.write("")
        cols = st.columns(3) # 電腦3欄，手機1欄 (Streamlit 預設行為)
        
        for i, row in res.iterrows():
            with cols[i%3]:
                with st.container(border=True):
                    # 圖片固定高度 200px
                    img = row['image_url'] if row['image_url'] else "https://cdn-icons-png.flaticon.com/512/4992/4992482.png"
                    st.markdown(f'<div style="height:200px; overflow:hidden; border-radius:8px; display:flex; justify-content:center; background:#f0f2f6; margin-bottom:10px;"><img src="{img}" style="height:100%; width:100%; object-fit:cover;"></div>', unsafe_allow_html=True)
                    
                    st.markdown(f"#### {row['name']}")
                    st.caption(f"#{row['uid']} | 📍 {row['location']}")
                    
                    # 狀態標籤 (使用上面的 STATUS_COLORS 設定)
                    status = row['status']
                    style = STATUS_COLORS.get(status, {"bg": "#eee", "text": "#000"})
                    
                    st.markdown(f'<span style="background:{style["bg"]}; color:{style["text"]}; padding:4px 10px; border-radius:12px; font-weight:bold; font-size:12px">● {status}</span>', unsafe_allow_html=True)

                    if status == '借出中': st.warning(f"👤 {row['borrower']}")

                    if st.session_state.is_admin:
                        st.markdown("---")
                        with st.expander("⚙️ 管理"):
                            ns = st.selectbox("狀態", ["在庫","借出中","維修中","報廢"], key=f"s{row['uid']}", index=["在庫","借出中","維修中","報廢"].index(status))
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
        with st.container(border=True):
            st.markdown("<h2 style='text-align:center'>🔐 管理員登入</h2>", unsafe_allow_html=True)
            st.text_input("密碼", type="password", key="password_input")
            b1, b2 = st.columns(2)
            b1.button("取消", on_click=lambda: go_to("home"), use_container_width=True)
            b2.button("登入", type="primary", on_click=perform_login, use_container_width=True)

# 路由
if st.session_state.current_page == "login": login_page()
else: main_page()
