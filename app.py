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
# 🎨 UI/UX 工程：Card UI + 圖片統一修正
# ==========================================
st.markdown("""
<style>
    /* 1. 全域背景 */
    .stApp {
        background-color: #F1F5F9;
    }

    /* 2. 核心卡片樣式 */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #FFFFFF;
        border-radius: 16px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        padding: 24px;
        margin-bottom: 16px;
    }

    /* 3. 按鈕美化 */
    .stButton > button {
        border-radius: 10px;
        height: 48px;
        font-weight: 600;
        font-size: 16px;
        border: none;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    /* 4. 輸入框優化 */
    div[data-testid="stTextInput"] input {
        border-radius: 8px;
        height: 45px;
    }

    /* 5. 標題優化 */
    h1, h2, h3 {
        color: #1E293B;
        font-family: system-ui, -apple-system, sans-serif;
    }

    /* 6. 手機版優化 */
    @media (max-width: 640px) {
        .stApp { padding-top: 20px; }
        div[data-testid="stVerticalBlockBorderWrapper"] { padding: 16px; }
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
@st.dialog("➕ 新增器材", width="small")
def show_add_modal():
    st.caption("請填寫器材詳細資訊")
    with st.form("add_form", clear_on_submit=True):
        new_name = st.text_input("器材名稱", placeholder="例如：Sony A7M4")
        new_uid = st.text_input("器材編號", placeholder="例如：CAM-01")
        
        c1, c2 = st.columns(2)
        new_cat = c1.selectbox("分類", ["攝影器材", "燈光音響", "線材耗材", "電腦週邊", "其他"])
        new_status = c2.selectbox("狀態", ["在庫", "借出中", "維修中", "報廢"])
        
        new_loc = st.text_input("存放位置", value="儲藏室")
        uploaded_file = st.file_uploader("上傳照片 (JPG/PNG)", type=['jpg', 'png', 'jpeg'])
        
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
#  頁面 1：登入頁
# ==========================================
def login_page():
    _, center_col, _ = st.columns([1, 6, 1])
    with center_col:
        st.write("")
        st.write("")
        with st.container(border=True):
            st.markdown("<h2 style='text-align: center;'>🔐 管理員登入</h2>", unsafe_allow_html=True)
            st.markdown("---")
            st.text_input("請輸入密碼", type="password", key="password_input")
            st.caption("僅限幹部與管理人員登入")
            st.write("")
            b1, b2 = st.columns(2)
            with b1: st.button("返回首頁", on_click=go_to_home, use_container_width=True)
            with b2: st.button("登入系統", type="primary", on_click=perform_login, use_container_width=True)

# ==========================================
#  頁面 2：主控台
# ==========================================
def main_page():
    with st.spinner('同步資料中...'):
        df = load_data()
    
    # --- 導覽列 ---
    c_title, c_act = st.columns([2, 1]) 
    with c_title: st.title("📦 器材管理系統")
    with c_act:
        if st.session_state.is_admin:
            with st.container(border=True):
                st.caption(f"目前身分：管理員")
                ac1, ac2 = st.columns(2)
                ac1.button("➕ 新增", on_click=show_add_modal, use_container_width=True)
                ac2.button("登出", on_click=perform_logout, use_container_width=True)
        else:
            st.button("🔐 管理員登入", type="primary", on_click=go_to_login, use_container_width=True)

    # --- 儀表板 ---
    if not df.empty:
        total = len(df)
        avail = len(df[df['status'] == '在庫'])
        mainten = len(df[df['status'] == '維修中'])
        borrow = len(df[df['status'] == '借出中'])
    else:
        total = avail = mainten = borrow = 0

    st.write("")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        with st.container(border=True): st.metric("📦 總器材", total)
    with m2:
        with st.container(border=True): st.metric("✅ 可用", avail)
    with m3:
        with st.container(border=True): st.metric("🛠️ 維修中", mainten)
    with m4:
        with st.container(border=True): st.metric("👤 借出中", borrow)

    # --- 列表區 ---
    st.markdown("### 🔎 器材檢索")
    with st.container(border=True):
        search_query = st.text_input("快速搜尋", placeholder="輸入名稱、編號...", label_visibility="collapsed")

    if not df.empty:
        if search_query:
            filtered_df = df[df['name'].str.contains(search_query, case=False) | df['uid'].str.contains(search_query, case=False)]
        else:
            filtered_df = df

        if not filtered_df.empty:
            st.write("")
            cols = st.columns(3)
            
            for idx, row in filtered_df.iterrows():
                with cols[idx % 3]:
                    with st.container(border=True):
                        # 🔥🔥 關鍵修改：使用 HTML 強制固定圖片高度與裁切 🔥🔥
                        img_link = row['image_url'] if row['image_url'] else "https://cdn-icons-png.flaticon.com/512/4992/4992482.png"
                        
                        # 這裡我用 object-fit: cover; height: 200px;
                        # 意思是：高度強制 200px，寬度填滿，多餘的部分「裁切掉」(不會變形)
                        st.markdown(
                            f"""
                            <div style="width:100%; height:300px; overflow:hidden; border-radius:12px; margin-bottom:14px; background-color:#f0f2f6; display:flex; align-items:center; justify-content:center;">
                                <img src="{img_link}" style="width:100%; height:100%; object-fit: cover;">
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                        
                        st.markdown(f"#### {row['name']}")
                        st.caption(f"編號：{row['uid']}")
                        
                        # 狀態標籤
                        status_color = {
                            "在庫": "#E6F4EA", "借出中": "#FCE8E6", 
                            "維修中": "#FEF7E0", "報廢": "#F1F3F4"
                        }.get(row['status'], "#F1F3F4")
                        
                        text_color = {
                            "在庫": "#137333", "借出中": "#C5221F", 
                            "維修中": "#B06000", "報廢": "#5F6368"
                        }.get(row['status'], "#000")

                        st.markdown(
                            f"""<div style="background-color:{status_color}; color:{text_color}; padding:4px 12px; border-radius:12px; display:inline-block; font-weight:bold; font-size:14px; margin-bottom:8px;">● {row['status']}</div>""", 
                            unsafe_allow_html=True
                        )
                        
                        st.markdown(f"📍 **位置**: {row['location']}")
                        if row['status'] == "借出中":
                            st.info(f"👤 **{row['borrower']}** 使用中")

                        if st.session_state.is_admin:
                            st.markdown("---")
                            with st.expander("⚙️ 編輯/管理"):
                                new_status = st.selectbox("狀態", ["在庫", "借出中", "維修中", "報廢"], key=f"s_{row['uid']}", index=["在庫", "借出中", "維修中", "報廢"].index(row['status']))
                                current_b = row['borrower'] if row['borrower'] else ""
                                new_b = st.text_input("借用人", value=current_b, key=f"b_{row['uid']}")
                                
                                b1, b2 = st.columns(2)
                                b1.button("更新", key=f"up_{row['uid']}", use_container_width=True)
                                b2.button("刪除", key=f"del_{row['uid']}", type="primary", use_container_width=True)
                                
                                if st.session_state.get(f"up_{row['uid']}"):
                                    update_equipment_in_db(row['uid'], {"status": new_status, "borrower": new_b})
                                    st.toast("更新成功")
                                    st.rerun()
                                if st.session_state.get(f"del_{row['uid']}"):
                                    delete_equipment_from_db(row['uid'])
                                    st.toast("已刪除")
                                    st.rerun()
    else:
        st.info("目前沒有資料，請新增器材！")

# --- 路由 ---
if st.session_state.current_page == "login":
    login_page()
else:
    main_page()

