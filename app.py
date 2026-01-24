import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import time
import os
from fpdf import FPDF # 確保 requirements.txt 裡寫的是 fpdf2

# ==========================================
# 🎨 [色彩與基本設定]
# ==========================================
NAV_HEIGHT = "80px"
NAV_BG_COLOR = "#E88B00"       # 你的橘色
PAGE_BG_COLOR = "#F5F5F5"      # 淺灰底
LOGO_URL = "https://obmikwclquacitrwzdfc.supabase.co/storage/v1/object/public/logos/logo.png"

# 🔥 統一管理的分類清單
CATEGORY_OPTIONS = ["手工具", "一般器材", "廚具", "清潔用品", "文具用品", "其他"]

# ⚠️ 字體設定：這裡已經改成你上傳的檔名了！
FONT_FILE = "TaipeiSansTCBeta-Regular.ttf"

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

# --- 4. PDF 生成功能 (使用你上傳的字體) ---
def create_pdf(selected_items):
    pdf = FPDF()
    pdf.add_page()
    
    # 檢查字體檔是否存在
    if os.path.exists(FONT_FILE):
        try:
            # 註冊字體 (fpdf2 語法)
            pdf.add_font('ChineseFont', '', FONT_FILE)
            pdf.set_font('ChineseFont', '', 14)
        except Exception as e:
            # 如果字體載入失敗，回退英文以免當機
            pdf.set_font("Helvetica", size=12)
            pdf.cell(0, 10, txt=f"Font Error: {e}", ln=1, align='C')
    else:
        # 如果找不到檔案
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 10, txt="Error: TaipeiSansTCBeta-Regular.ttf not found.", ln=1, align='C')

    # 標題
    pdf.set_font_size(20)
    pdf.cell(0, 15, txt="團隊器材借用清單", ln=1, align='C')
    
    # 日期
    pdf.set_font_size(10)
    pdf.cell(0, 10, txt=f"匯出日期: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=1, align='C')
    pdf.ln(10)

    # 表格標頭
    pdf.set_font_size(12)
    pdf.set_fill_color(232, 139, 0) # 橘色背景
    pdf.set_text_color(255, 255, 255) # 白色文字
    
    col_w = [30, 70, 30, 30, 30] 
    headers = ["編號", "名稱", "分類", "狀態", "位置"]
    
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 10, h, border=1, align='C', fill=True)
    pdf.ln()

    # 表格內容
    pdf.set_text_color(0, 0, 0) # 黑色文字
    
    for item in selected_items:
        uid = str(item.get('uid', ''))
        name = str(item.get('name', ''))
        cat = str(item.get('category', ''))
        status = str(item.get('status', ''))
        loc = str(item.get('location', ''))
        
        pdf.cell(col_w[0], 10, uid, border=1, align='C')
        
        # 處理名稱過長截斷
        # 注意：如果名稱包含中文字，get_string_width 有時會誤判，這裡做簡單截斷
        display_name = name if len(name) < 12 else name[:11] + "..."
            
        pdf.cell(col_w[1], 10, display_name, border=1, align='C')
        pdf.cell(col_w[2], 10, cat, border=1, align='C')
        pdf.cell(col_w[3], 10, status, border=1, align='C')
        pdf.cell(col_w[4], 10, loc, border=1, align='C')
        pdf.ln()
    
    # 簽名區
    pdf.ln(20)
    pdf.cell(0, 10, "借用人簽名: _________________________", ln=1)
    pdf.cell(0, 10, "管理員核准: _________________________", ln=1)

    return pdf.output()

# --- 頁面設定 ---
st.set_page_config(page_title="器材管理系統", layout="wide", page_icon="📦", initial_sidebar_state="collapsed")

# 初始化購物車 Session
if 'cart' not in st.session_state:
    st.session_state.cart = set() 

# ==========================================
# 🛠️ CSS 樣式表
# ==========================================
st.markdown(f"""
<style>
    header[data-testid="stHeader"] {{ display: none; }}
    .stApp {{ background-color: {PAGE_BG_COLOR} !important; }}
    .main .block-container {{
        padding-top: 100px !important; 
        max-width: 1200px !important;
    }}
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
        padding-right: 30px;
        justify-content: space-between; 
    }}
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
    div[data-testid="stPills"] button[aria-selected="true"] {{
        background-color: {NAV_BG_COLOR} !important;
        color: white !important;
        border-color: {NAV_BG_COLOR} !important;
    }}
</style>
""", unsafe_allow_html=True)

# --- 狀態管理 ---
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'current_page' not in st.session_state: st.session_state.current_page = "home"
def go_to(page): st.session_state.current_page = page
def perform_logout(): 
    st.session_state.is_admin = False
    st.session_state.cart = set()
    go_to("home")
def perform_login():
    if st.session_state.password_input == st.secrets["ADMIN_PASSWORD"]:
        st.session_state.is_admin = True
        go_to("home")
    else: st.error("密碼錯誤")

# ==========================================
# 彈窗：檢視清單與匯出 PDF
# ==========================================
@st.dialog("📋 借用清單預覽", width="large")
def show_cart_modal(df):
    if not st.session_state.cart:
        st.info("清單目前是空的，請先勾選器材！")
        if st.button("關閉"): st.rerun()
    else:
        cart_items = df[df['uid'].isin(st.session_state.cart)]
        st.write(f"目前已選擇 {len(cart_items)} 項器材：")
        st.dataframe(
            cart_items[['uid', 'name', 'category', 'status', 'location']], 
            hide_index=True,
            use_container_width=True
        )
        col1, col2 = st.columns([1, 1])
        if col1.button("🗑️ 清空清單", use_container_width=True):
            st.session_state.cart = set()
            st.rerun()
        
        # 產生 PDF
        try:
            pdf_bytes = create_pdf(cart_items.to_dict('records'))
            if pdf_bytes:
                col2.download_button(
                    label="📄 下載 PDF 清單",
                    data=bytes(pdf_bytes), 
                    file_name=f"equipment_list_{int(time.time())}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True
                )
        except Exception as e:
            st.error(f"PDF 產生失敗: {e}")

# ==========================================
# Header 組件
# ==========================================
def render_header(df_for_count=None):
    st.markdown(f"""
    <div id="my-fixed-header">
        <div style="display:flex; align-items:center;">
            <img src="{LOGO_URL}" style="height: 50px; object-fit: contain;">
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 彈窗：新增/編輯
# ==========================================
@st.dialog("➕ 新增器材", width="small")
def show_add_modal():
    st.caption("填寫詳細資訊")
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("名稱", placeholder="例如：活動扳手")
        uid = st.text_input("編號", placeholder="例如：TOOL-001")
        c1, c2 = st.columns(2)
        cat = c1.selectbox("分類", CATEGORY_OPTIONS, index=None, placeholder="--請選擇--")
        status = c2.selectbox("狀態", ["在庫", "借出中", "維修中", "報廢"], index=None, placeholder="--請選擇--")
        c3, c4 = st.columns(2)
        qty = c3.number_input("數量", min_value=1, value=1, step=1)
        loc = c4.text_input("位置", value="儲藏室")
        file = st.file_uploader("照片", type=['jpg','png'])
        if st.form_submit_button("新增", type="primary", use_container_width=True):
            if name and uid and cat and status:
                url = upload_image(file) if file else None
                data_payload = {"uid": uid, "name": name, "category": cat, "status": status, "borrower": "", "location": loc, "quantity": qty, "image_url": url, "updated_at": datetime.now().strftime("%Y-%m-%d")}
                try:
                    add_equipment_to_db(data_payload)
                    st.toast(f"🎉 成功新增：{name}"); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"寫入失敗: {e}")
            else: st.warning("⚠️ 請完整填寫名稱、編號，並選擇分類與狀態！")

@st.dialog("⚙️ 編輯/管理器材", width="small")
def show_edit_modal(item):
    st.caption(f"正在編輯：{item['name']} (#{item['uid']})")
    if item['image_url']: st.image(item['image_url'], width=100)
    with st.form("edit_form"):
        new_name = st.text_input("名稱", value=item['name'])
        c1, c2 = st.columns(2)
        try: cat_idx = CATEGORY_OPTIONS.index(item['category'])
        except: cat_idx = 0
        new_cat = c1.selectbox("分類", CATEGORY_OPTIONS, index=cat_idx)
        try: status_idx = ["在庫", "借出中", "維修中", "報廢"].index(item['status'])
        except: status_idx = 0
        new_status = c2.selectbox("狀態", ["在庫", "借出中", "維修中", "報廢"], index=status_idx)
        c3, c4 = st.columns(2)
        new_qty = c3.number_input("數量", min_value=1, value=item.get('quantity', 1), step=1)
        new_loc = c4.text_input("位置", value=item['location'] or "")
        new_borrower = st.text_input("借用人 (若借出請填寫)", value=item['borrower'] or "")
        new_file = st.file_uploader("更換照片", type=['jpg','png'])
        col_update, col_delete = st.columns([1, 1])
        submitted = col_update.form_submit_button("💾 儲存更新", type="primary", use_container_width=True)
        delete_confirm = col_delete.checkbox("確認刪除此器材")
        if submitted:
            if delete_confirm:
                delete_equipment_from_db(item['uid']); st.toast("🗑️ 已刪除"); time.sleep(1); st.rerun()
            else:
                final_url = upload_image(new_file) if new_file else item['image_url']
                updates = {"name": new_name, "category": new_cat, "status": new_status, "quantity": new_qty, "location": new_loc, "borrower": new_borrower, "image_url": final_url, "updated_at": datetime.now().strftime("%Y-%m-%d")}
                update_equipment_in_db(item['uid'], updates); st.toast("✅ 更新成功"); time.sleep(1); st.rerun()

# ==========================================
# 主頁面
# ==========================================
def main_page():
    render_header()
    
    st.markdown("""
        <style>
        .header-buttons {
            position: fixed;
            top: 20px;
            right: 30px;
            z-index: 9999999;
        }
        </style>
    """, unsafe_allow_html=True)
    
    df = load_data()
    
    with st.container():
        st.markdown('<div class="header-buttons">', unsafe_allow_html=True)
        if not st.session_state.is_admin:
            cart_count = len(st.session_state.cart)
            if st.button(f"📋 借用清單 ({cart_count})", type="primary"):
                show_cart_modal(df)
        st.markdown('</div>', unsafe_allow_html=True)

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

    st.write("")
    with st.container(border=True):
        search_query = st.text_input("🔍 搜尋器材...", placeholder="輸入關鍵字 (名稱、編號)...", label_visibility="collapsed")
        st.write("") 
        filter_options = ["全部顯示"] + CATEGORY_OPTIONS
        selected_category = st.pills("快速分類篩選", filter_options, default="全部顯示", label_visibility="collapsed")

    if not df.empty:
        if selected_category and selected_category != "全部顯示":
            filtered_df = df[df['category'] == selected_category]
        else:
            filtered_df = df

        if search_query:
            filtered_df = filtered_df[
                filtered_df['name'].str.contains(search_query, case=False) | 
                filtered_df['uid'].str.contains(search_query, case=False)
            ]
        
        if not filtered_df.empty:
            st.write("") 
            cols = st.columns(3)
            for i, (index, row) in enumerate(filtered_df.iterrows()):
                with cols[i % 3]:
                    with st.container(border=True):
                        img = row['image_url'] if row['image_url'] else "https://cdn-icons-png.flaticon.com/512/4992/4992482.png"
                        st.markdown(f'<div style="height:200px; overflow:hidden; border-radius:4px; display:flex; justify-content:center; background:#f0f2f6; margin-bottom:12px;"><img src="{img}" style="height:100%; width:100%; object-fit:cover;"></div>', unsafe_allow_html=True)
                        st.markdown(f"#### {row['name']}")
                        qty_display = f" | 數量: {row.get('quantity', 1)}" if row.get('quantity') else ""
                        st.caption(f"#{row['uid']} {qty_display} | 📍 {row['location']}")
                        status_map = {"在庫":"green", "借出中":"red", "維修中":"orange", "報廢":"grey"}
                        color = status_map.get(row['status'], "black")
                        st.markdown(f':{color}[● {row["status"]}]')

                        if row['status'] == '借出中': st.warning(f"👤 {row['borrower']}")

                        st.markdown("---")
                        if st.session_state.is_admin:
                            if st.button("⚙️ 編輯 / 管理", key=f"btn_{row['uid']}", use_container_width=True):
                                show_edit_modal(row)
                        else:
                            is_selected = row['uid'] in st.session_state.cart
                            if st.checkbox("加入借用清單", key=f"check_{row['uid']}", value=is_selected):
                                if not is_selected:
                                    st.session_state.cart.add(row['uid'])
                                    st.rerun() 
                            else:
                                if is_selected:
                                    st.session_state.cart.remove(row['uid'])
                                    st.rerun()
                                    
        else:
            if selected_category != "全部顯示":
                st.info(f"📂 「{selected_category}」分類下目前沒有器材。")
            else:
                st.info("尚無符合搜尋條件的資料。")
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
