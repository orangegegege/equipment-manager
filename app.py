import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time

# ==========================================
# 🎨 [色彩與基本設定]
# ==========================================
NAV_HEIGHT = "60px"
NAV_BG_COLOR = "#EE4D2D"       # 蝦皮橘
PAGE_BG_COLOR = "#F5F5F5"      # 淺灰底
LOGO_URL = "https://cdn-icons-png.flaticon.com/512/2504/2504929.png" # 你的 Logo

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

def add_equipment_to_db(data):
    supabase.table("equipment").insert(data).execute()

def update_equipment_in_db(uid, updates):
    supabase.table("equipment").update(updates).eq("uid", uid).execute()

def delete_equipment_from_db(uid):
    supabase.table("equipment").delete().eq("uid", uid).execute()

# --- 頁面設定 ---
st.set_page_config(page_title="器材管理系統", layout="wide", page_icon="📦", initial_sidebar_state="collapsed")

# ==========================================
# 🛠️ CSS 樣式表
# ==========================================
st.markdown(f"""
<style>
    /* 1. 隱藏預設 Header */
    header[data-testid="stHeader"] {{ display: none; }}

    /* 2. 背景顏色 */
    .stApp {{ background-color: {PAGE_BG_COLOR} !important; }}

    /* 3. 內容防擋 (往下推 100px) */
    .main .block-container {{
        padding-top: 100px !important; 
        max-width: 1200px !important;
    }}

    /* 4. 固定導覽列 */
    #my-fixed-header {{
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: {NAV_HEIGHT};
        background-color: {NAV_BG_COLOR};
        z-index: 999999;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        display: flex;
        align-items: center;
        padding-left: 30px;
    }}

    /* 5. 卡片美化 */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: white !important;
        border: 1px solid #ddd !important;
        border-radius: 8px !important;
        padding: 20px !important;
    }}
    .stButton > button {{
        border-radius: 6px;
        background-color: white;
        color: #333;
        border: 1px solid #ccc;
    }}
    .stButton > button[kind="primary"] {{
        background-color: {NAV_BG_COLOR} !important;
        color: white !important;
        border: none !important;
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
# Header 組件
# ==========================================
def render_header():
    st.markdown(f"""
    <div id="my-fixed-header">
        <img src="{LOGO_URL}" style="height: 60%; object-fit: contain;">
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 🔥 彈窗：新增器材 (這裡更新了！)
# ==========================================
@st.dialog("➕ 新增器材", width="small")
def show_add_modal():
    st.caption("填寫詳細資訊")
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("名稱", placeholder="例如：無線麥克風")
        uid = st.text_input("編號", placeholder="例如：MIC-001")
        
        # 使用 columns 排版
        c1, c2 = st.columns(2)
        
        # 🔥 修改點 1：加入 placeholder="--請選擇--" 和 index=None (預設不選)
        cat = c1.selectbox(
            "分類", 
            ["攝影", "燈光", "線材", "電腦", "其他"], 
            index=None, 
            placeholder="--請選擇--"
        )
        status = c2.selectbox(
            "狀態", 
            ["在庫", "借出中", "維修中", "報廢"], 
            index=None, 
            placeholder="--請選擇--"
        )
        
        c3, c4 = st.columns(2)
        # 🔥 修改點 2：新增「數量」欄位
        qty = c3.number_input("數量", min_value=1, value=1, step=1)
        loc = c4.text_input("位置", value="儲藏室")
        
        file = st.file_uploader("照片", type=['jpg','png'])
        
        if st.form_submit_button("新增", type="primary", use_container_width=True):
            # 🔥 修改點 3：增加防呆檢查，確保使用者有選分類和狀態
            if name and uid and cat and status:
                url = upload_image(file) if file else None
                
                # 準備寫入資料庫的資料
                data_payload = {
                    "uid": uid, 
                    "name": name, 
                    "category": cat, 
                    "status": status,
                    "borrower": "", 
                    "location": loc, 
                    "quantity": qty,  # 記得在資料庫新增這個欄位！
                    "image_url": url,
                    "updated_at": datetime.now().strftime("%Y-%m-%d")
                }
                
                try:
                    add_equipment_to_db(data_payload)
                    st.toast(f"🎉 成功新增：{name} (數量: {qty})")
                    time.sleep(1) # 讓 toast 顯示一下
                    st.rerun()
                except Exception as e:
                    st.error(f"寫入失敗，請檢查資料庫是否有 'quantity' 欄位！錯誤訊息: {e}")
            else:
                # 如果有欄位沒填，跳出警告
                st.warning("⚠️ 請完整填寫名稱、編號，並選擇分類與狀態！")

# ==========================================
# 主頁面
# ==========================================
def main_page():
    render_header()
    
    # 標題與操作
    c_title, c_actions = st.columns([3, 1], vertical_alignment="bottom")
    with c_title:
        st.title("團隊器材中心")
    with c_actions:
        if st.session_state.is_admin:
            b1, b2 = st.columns(2, gap="small")
            b1.button("➕ 新增", on_click=show_add_modal, use_container_width=True)
            b2.button("登出", on_click=perform_logout, type="primary", use_container_width=True)
        else:
            st.button("🔐 管理員登入", on_click=lambda: go_to("login"), type="primary", use_container_width=True)

    # 讀取資料
    df = load_data()
    
    # 儀表板
    if not df.empty:
        total = len(df)
        avail = len(df[df['status']=='在庫'])
        
        m1, m2, m3, m4 = st.columns(4)
        with m1: 
            with st.container(border=True): st.metric("📦 總項目", total)
        with m2: 
            with st.container(border=True): st.metric("✅ 可用", avail)
        with m3: 
            with st.container(border=True): st.metric("🛠️ 維修", len(df[df['status']=='維修中']))
        with m4: 
            with st.container(border=True): st.metric("👤 借出", len(df[df['status']=='借出中']))

    # 搜尋
    st.write("")
    with st.container(border=True):
        search = st.text_input("🔍 搜尋器材...", placeholder="輸入關鍵字...", label_visibility="collapsed")

    # 列表
    if not df.empty:
        res = df[df['name'].str.contains(search, case=False) | df['uid'].str.contains(search, case=False)] if search else df
        st.write("") 
        cols = st.columns(3)
        for i, row in res.iterrows():
            with cols[i%3]:
                with st.container(border=True):
                    img = row['image_url'] if row['image_url'] else "https://cdn-icons-png.flaticon.com/512/4992/4992482.png"
                    st.markdown(f'<div style="height:200px; overflow:hidden; border-radius:4px; display:flex; justify-content:center; background:#f0f2f6; margin-bottom:12px;"><img src="{img}" style="height:100%; width:100%; object-fit:cover;"></div>', unsafe_allow_html=True)
                    st.markdown(f"#### {row['name']}")
                    
                    # 顯示數量 (如果資料庫有這個欄位且大於1)
                    qty_display = f" | 數量: {row.get('quantity', 1)}" if row.get('quantity') else ""
                    st.caption(f"#{row['uid']} {qty_display} | 📍 {row['location']}")
                    
                    status_map = {"在庫":"green", "借出中":"red", "維修中":"orange", "報廢":"grey"}
                    color = status_map.get(row['status'], "black")
                    st.markdown(f':{color}[● {row["status"]}]')

                    if row['status'] == '借出中': st.warning(f"👤 {row['borrower']}")

                    if st.session_state.is_admin:
                        st.markdown("---")
                        with st.expander("⚙️ 管理"):
                            # 為了安全，這裡加個 try except，怕舊資料沒有 quantity
                            try:
                                current_status_idx = ["在庫","借出中","維修中","報廢"].index(row['status'])
                            except:
                                current_status_idx = 0
                                
                            ns = st.selectbox("狀態", ["在庫","借出中","維修中","報廢"], key=f"s{row['uid']}", index=current_status_idx)
                            nb = st.text_input("借用人", value=row['borrower'] or "", key=f"b{row['uid']}")
                            
                            b1, b2 = st.columns(2)
                            if b1.button("更新", key=f"u{row['uid']}", use_container_width=True):
                                update_equipment_in_db(row['uid'], {"status":ns, "borrower":nb}); st.toast("更新成功"); st.rerun()
                            if b2.button("刪除", key=f"d{row['uid']}", type="primary", use_container_width=True):
                                delete_equipment_from_db(row['uid']); st.toast("已刪除"); st.rerun()
    else: st.info("尚無資料")

# ==========================================
# 登入頁
# ==========================================
def login_page():
    render_header()
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
