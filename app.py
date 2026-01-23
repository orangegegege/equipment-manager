import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time

# ==========================================
# 🎨 [色彩控制台]
# ==========================================

# 1. 導覽列 (Top Bar) 設定 - [只放 Logo]
NAV_BG_COLOR = "#EE4D2D"       # 蝦皮橘
NAV_HEIGHT = "60px"            # 導覽列高度

# 2. 網頁大背景
PAGE_BG_COLOR = "#F5F5F5"      # 淺灰底

# 3. 內容卡片
CARD_BG_COLOR = "#FFFFFF"
CARD_BORDER_COLOR = "#E0E0E0"

# 4. LOGO (建議用橫式的圖，或者單純圖示)
LOGO_URL = "https://cdn-icons-png.flaticon.com/512/2504/2504929.png"

# 5. 狀態顏色
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
# 🛠️ CSS 核心工程 (純裝飾 Header 版)
# ==========================================
st.markdown(f"""
<style>
    /* 1. 隱藏預設 Header */
    header[data-testid="stHeader"] {{ display: none; }}

    /* 2. 網頁背景顏色 */
    .stApp {{
        background-color: {PAGE_BG_COLOR} !important;
    }}

    /* 3. 內容補償 (Padding)
       因為上面有 60px 的 Header，我們要把內容往下推 80px
       這樣標題才不會被橘色Bar擋住
    */
    .main .block-container {{
        padding-top: 80px !important;
        max-width: 1200px !important;
    }}

    /* 4. ✨ [純裝飾導覽列] CSS ✨ 
       這是一個純 HTML/CSS 的區塊，只負責顯示橘色背景和 Logo
    */
    #my-deco-header {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: {NAV_HEIGHT};
        background-color: {NAV_BG_COLOR};
        z-index: 9999999;
        
        display: flex;
        align_items: center; /* 垂直置中 */
        padding-left: 20px;  /* Logo 距離左邊的距離 */
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }}

    /* 5. 內容卡片樣式 */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {CARD_BG_COLOR} !important;
        border: 1px solid {CARD_BORDER_COLOR} !important;
        border-radius: 8px !important;
        padding: 20px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}

    /* 6. 按鈕樣式 (一般按鈕) */
    .stButton > button {{
        border-radius: 6px !important;
        height: 42px !important;
        font-weight: 500 !important;
        border: 1px solid #ddd !important;
        background-color: #fff;
        color: #333;
    }}
    
    /* 7. 主要按鈕 (登入/刪除 - 紅橘色系) */
    .stButton > button[kind="primary"] {{
        background-color: {NAV_BG_COLOR} !important; /* 跟導覽列同色 */
        color: white !important;
        border: none !important;
    }}
    
    /* 8. 手機版圖片限制 */
    @media (max-width: 640px) {{
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
# ✨ 純裝飾 Header (只放圖)
# ==========================================
def render_deco_header():
    # 直接注入 HTML，不使用 Streamlit 容器
    # 這樣它就是一個單純的、不會動的、純視覺的頂部 Bar
    st.markdown(f"""
    <div id="my-deco-header">
        <img src="{LOGO_URL}" style="height: 36px;">
    </div>
    """, unsafe_allow_html=True)

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
    # 1. 顯示純裝飾 Header (橘色那條)
    render_deco_header()
    
    # 2. 標題與操作區 (回到白色內容區)
    # 使用 columns 把標題放左邊，按鈕放右邊
    c_title, c_actions = st.columns([3, 1], vertical_alignment="center")
    
    with c_title:
        # 頁面標題
        st.title("團隊器材中心")
        
    with c_actions:
        # 這裡就是「原本的地方」 (內容區的右上角)
        if st.session_state.is_admin:
            b1, b2 = st.columns(2, gap="small")
            b1.button("➕ 新增", on_click=show_add_modal, use_container_width=True)
            b2.button("登出", on_click=perform_logout, type="primary", use_container_width=True)
        else:
            # 登入按鈕
            st.button("🔐 管理員登入", on_click=lambda: go_to("login"), type="primary", use_container_width=True)

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
                    # 圖片
                    img = row['image_url'] if row['image_url'] else "https://cdn-icons-png.flaticon.com/512/4992/4992482.png"
                    st.markdown(f'<div style="height:200px; overflow:hidden; border-radius:4px; display:flex; justify-content:center; background:#f0f2f6; margin-bottom:12px;"><img src="{img}" style="height:100%; width:100%; object-fit:cover;"></div>', unsafe_allow_html=True)
                    
                    st.markdown(f"#### {row['name']}")
                    st.caption(f"#{row['uid']} | 📍 {row['location']}")
                    
                    # 狀態
                    style = STATUS_COLORS.get(row['status'], {"bg": "#eee", "text": "#000"})
                    st.markdown(f'<span style="background:{style["bg"]}; color:{style["text"]}; padding:2px 8px; border-radius:4px; font-weight:bold; font-size:12px">● {row['status']}</span>', unsafe_allow_html=True)

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
    render_deco_header()
    
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
