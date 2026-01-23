import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time

# ==========================================
# 🎨 [色彩控制台] 請在這裡調整！
# ==========================================

# 1. 導覽列 (Header) 設定 - [仿蝦皮風格]
# 這裡改成橘色看看效果，或者你可以改回白色 #FFFFFF
NAV_BG_COLOR = "#EE4D2D"       # 蝦皮橘 (你可以改成 #FFFFFF)
NAV_TEXT_COLOR = "#FFFFFF"     # 文字顏色 (白)
NAV_HEIGHT = "70px"            # 導覽列高度

# 2. 網頁大背景
PAGE_BG_COLOR = "#F5F5F5"      # 淺灰底

# 3. 內容卡片
CARD_BG_COLOR = "#FFFFFF"
CARD_BORDER_COLOR = "#E0E0E0"

# 4. LOGO
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
# 🛠️ CSS 核心工程 (蝦皮架構版)
# ==========================================
st.markdown(f"""
<style>
    /* 1. 隱藏預設 Header */
    header[data-testid="stHeader"] {{ display: none; }}

    /* 2. 網頁背景顏色 */
    .stApp {{
        background-color: {PAGE_BG_COLOR} !important;
    }}

    /* 3. 【關鍵】內容補償 (Padding)
       我們強迫主內容區域往下退 90px，
       這樣第一排內容才不會被你的 Header 擋住！
    */
    .main .block-container {{
        padding-top: 90px !important;
        padding-bottom: 50px !important;
        max-width: 1200px !important;
    }}

    /* 4. ✨ [自定義導覽列] CSS ✨ 
       我們不依賴 Streamlit 的容器，而是直接用 CSS 創造一個固定層
       這裡的 #my-custom-header 會對應到下面 HTML 裡的 ID
    */
    #my-custom-header {{
        position: fixed;       /* 釘死在視窗上 */
        top: 0;
        left: 0;
        width: 100%;
        height: {NAV_HEIGHT};
        background-color: {NAV_BG_COLOR};
        z-index: 9999999;      /* 確保在最上層，比 Streamlit 的任何東西都高 */
        
        display: flex;         /* 彈性排版 */
        align_items: center;   /* 垂直置中 */
        justify-content: space-between; /* 左右推開 */
        padding: 0 2rem;       /* 左右內距 */
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        color: {NAV_TEXT_COLOR};
        border-bottom: 1px solid rgba(0,0,0,0.05);
    }}

    /* 5. 內容卡片樣式 */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {CARD_BG_COLOR} !important;
        border: 1px solid {CARD_BORDER_COLOR} !important;
        border-radius: 8px !important;
        padding: 20px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}

    /* 6. 按鈕樣式 */
    .stButton > button {{
        border-radius: 4px !important;
        height: 40px !important;
        font-weight: 500 !important;
        border: 1px solid #ddd !important;
        background-color: #fff;
        color: #333;
    }}
    /* 主要按鈕 (橘色/紅色) */
    .stButton > button[kind="primary"] {{
        background-color: #EE4D2D !important; /* 蝦皮橘 */
        color: white !important;
        border: none !important;
    }}
    
    /* 7. 手機版優化 */
    @media (max-width: 640px) {{
        #my-custom-header {{ padding: 0 1rem; }}
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
# ✨ 導覽列組件 (HTML Injection)
# ==========================================
def render_navbar():
    # 這次我們不只用 container，而是直接插入一段 HTML 結構
    # 這段 HTML 會被上面的 CSS #my-custom-header 抓去變成 Header
    
    # 這裡我們用一個技巧：雖然 HTML 渲染出來了，但按鈕的互動還是需要 Streamlit
    # 所以我們用一個隱形的 container 來佔位，把按鈕放在裡面
    # 但視覺上我們用 CSS 把它「搬」到 Header 的位置 (這比較複雜，我們換個簡單的)
    
    # 修正策略：我們還是用 Streamlit 的容器，但用 CSS 強制把它變成 Header
    # 這是最穩定的做法，可以同時保有互動性
    
    with st.container():
        # 這個空的 div 是為了讓 CSS 抓到這裡，把整個 container 變成 Header
        st.markdown(f'<div id="my-custom-header"></div>', unsafe_allow_html=True)
        
        # ⚠️ 注意：因為 CSS 把這個 container 設為 fixed，它會浮起來
        # 這裡面的內容會自動變成 Header 的內容
        
        # 我們需要手動調整這裡的排版，因為 st.columns 在 fixed container 裡有時候會怪怪的
        # 但為了按鈕功能，我們還是得用 columns
        
        c1, c2 = st.columns([1, 1], vertical_alignment="center")
        
        with c1:
            # 這裡因為 CSS 設了 color，所以文字會自動變色
            # 我們用 HTML 來控制 Logo 和標題的排版，比較漂亮
            st.markdown(f"""
            <div style="display:flex; align-items:center; gap:10px; height: {NAV_HEIGHT};">
                <img src="{LOGO_URL}" style="height: 35px;">
                <h3 style="margin:0; padding:0; color:inherit; font-size:1.2rem; white-space:nowrap;">團隊器材中心</h3>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            # 按鈕區 (靠右)
            # 因為這是在 Fixed Header 裡，我們需要把這區塊往右推
            # 這裡用一個空的 column 來佔位是不夠的，我們直接在 columns 裡操作
            
            # 使用 CSS hack 讓這一塊浮動到右邊
            st.markdown('<style>div[data-testid="column"]:nth-of-type(2) { display: flex; justify-content: flex-end; }</style>', unsafe_allow_html=True)
            
            if st.session_state.is_admin:
                b1, b2 = st.columns(2, gap="small")
                b1.button("➕ 新增", on_click=show_add_modal)
                b2.button("登出", on_click=perform_logout, type="primary")
            else:
                st.button("🔐 管理員登入", on_click=lambda: go_to("login"), type="primary")

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
    # 1. 渲染導覽列 (它會自動飛到最上面變成 Header)
    render_navbar()
    
    # 2. 內容開始
    # CSS 已經設定了 padding-top: 90px，所以這裡不用擔心被擋住
    
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
    render_navbar()
    
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
