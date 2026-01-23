import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time

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
# 🎨 CSS 樣式表 (這裡調整顏色！)
# ==========================================
st.markdown("""
<style>
    /* 1. 隱藏 Streamlit 預設的醜 Header */
    header[data-testid="stHeader"] {
        display: none;
    }

    /* 2. 整頁背景顏色 */
    .stApp {
        /* 👇 [調整點 1] 這裡是「整頁背景」的顏色 */
        /* #F8F9FA 是淺灰白，你可以改成 #FFFFFF (純白) 或 #000000 (黑) */
        background-color: #F8F9FA; 
    }

    /* 3. 置頂導覽列 (那個黑色的膠囊條) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.navbar-marker) {
        position: sticky;
        top: 15px; 
        z-index: 999;
        
        /* 👇 [調整點 2] 這裡是「導覽列」的背景顏色 */
        /* #2D3436 是深灰色，你可以改成任何你喜歡的顏色 */
        background-color: #2D3436; 
        
        border-radius: 50px;
        padding: 10px 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        border: 1px solid #444;
        margin-bottom: 20px;
    }

    /* 導覽列裡面的文字顏色 (強制變色) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.navbar-marker) h3,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.navbar-marker) span,
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.navbar-marker) p {
        /* 👇 [調整點 3] 這裡是「導覽列文字」的顏色 */
        color: #FFFFFF !important; 
        margin: 0;
    }

    /* 4. 白色卡片樣式 (儀表板、搜尋框、器材列表) */
    div[data-testid="stVerticalBlockBorderWrapper"]:not(:has(.navbar-marker)) {
        /* 👇 [調整點 4] 這裡是「白色卡片」的背景顏色 */
        background-color: #FFFFFF; 
        
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border: 1px solid #E2E8F0;
    }
    
    /* 5. 按鈕與輸入框優化 */
    .stButton > button { border-radius: 10px; height: 45px; font-weight: bold; border:none; }
    div[data-testid="stTextInput"] input { border-radius: 8px; height: 45px; }
    
    /* 手機版優化 */
    @media (max-width: 640px) {
        div[data-testid="stHorizontalBlock"]:has(button) { flex-wrap: nowrap !important; gap: 8px !important; }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.navbar-marker) {
            border-radius: 12px; top: 0px; margin: 0px -10px 20px -10px;
        }
    }
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
# 導覽列組件 (Sticky Navbar)
# ==========================================
def render_navbar():
    # 這是導覽列容器
    with st.container(border=True):
        st.markdown('<div class="navbar-marker"></div>', unsafe_allow_html=True)
        
        c_logo, c_menu = st.columns([1, 1])
        with c_logo:
            st.markdown("### 📦 團隊器材中心") 
        with c_menu:
            if st.session_state.is_admin:
                b1, b2 = st.columns(2)
                b1.button("➕ 新增", on_click=show_add_modal, use_container_width=True, type="secondary")
                b2.button("登出", on_click=perform_logout, use_container_width=True, type="primary")
            else:
                _, b_login = st.columns([1, 2])
                b_login.button("🔐 管理員登入", on_click=lambda: go_to("login"), use_container_width=True)

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
        status = c2.selectbox("狀態", ["在庫", "借出中", "維修", "報廢"])
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

    # 搜尋
    st.write("")
    with st.container(border=True):
        search = st.text_input("🔍 搜尋", placeholder="輸入關鍵字...", label_visibility="collapsed")

    # 列表
    if not df.empty:
        res = df[df['name'].str.contains(search, case=False) | df['uid'].str.contains(search, case=False)] if search else df
        st.write("")
        cols = st.columns(3)
        for i, row in res.iterrows():
            with cols[i%3]:
                with st.container(border=True):
                    # 統一圖片高度 200px
                    img = row['image_url'] if row['image_url'] else "https://cdn-icons-png.flaticon.com/512/4992/4992482.png"
                    st.markdown(f'<div style="height:200px; overflow:hidden; border-radius:8px; display:flex; justify-content:center; background:#f0f2f6; margin-bottom:10px;"><img src="{img}" style="height:100%; width:100%; object-fit:cover;"></div>', unsafe_allow_html=True)
                    
                    st.markdown(f"#### {row['name']}")
                    st.caption(f"#{row['uid']} | 📍 {row['location']}")
                    
                    # 👇 [調整點 5] 狀態標籤的顏色設定
                    # 你可以在這裡修改背景色 (如 #E6F4EA) 和文字色 (如 green)
                    status_config = {
                        "在庫":   {"bg": "#E6F4EA", "color": "green"},
                        "借出中": {"bg": "#FCE8E6", "color": "red"},
                        "維修":   {"bg": "#FEF7E0", "color": "orange"},
                        "報廢":   {"bg": "#F1F3F4", "color": "grey"}
                    }
                    
                    # 取得目前狀態的顏色，如果找不到就用預設灰色
                    s_conf = status_config.get(row['status'], {"bg": "#eee", "color": "black"})
                    
                    st.markdown(f'<span style="background:{s_conf["bg"]}; color:{s_conf["color"]}; padding:4px 10px; border-radius:12px; font-weight:bold; font-size:12px">● {row['status']}</span>', unsafe_allow_html=True)

                    if row['status'] == '借出中': st.warning(f"👤 {row['borrower']}")

                    if st.session_state.is_admin:
                        st.markdown("---")
                        with st.expander("⚙️ 管理"):
                            ns = st.selectbox("狀態", ["在庫","借出中","維修","報廢"], key=f"s{row['uid']}", index=["在庫","借出中","維修","報廢"].index(row['status']))
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
