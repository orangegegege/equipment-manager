import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime, timedelta 
import time
import os
import io 
from fpdf import FPDF 

# Word 處理套件
from docx import Document
from docx.shared import Mm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.section import WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ==========================================
# 1. 頁面設定 (必須放在最第一行，不能斷行)
# ==========================================
st.set_page_config(page_title="器材管理系統", layout="wide", page_icon="📦", initial_sidebar_state="collapsed")

# ==========================================
# 🎨 [色彩與基本設定]
# ==========================================
NAV_HEIGHT = "80px"
NAV_BG_COLOR = "#E88B00"
PAGE_BG_COLOR = "#F5F5F5"
LOGO_URL = "https://obmikwclquacitrwzdfc.supabase.co/storage/v1/object/public/logos/logo.png"

CATEGORY_OPTIONS = ["手工具", "一般器材", "廚具", "清潔用品", "文具用品", "其他"]
FONT_FILE = "TaipeiSansTCBeta-Regular.ttf"

# --- Supabase 連線 ---
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

# --- 圖片上傳 ---
def upload_image(file):
    if not file: return None
    try:
        bucket_name = st.secrets["SUPABASE"]["BUCKET"]
        file_ext = file.name.split('.')[-1]
        file_name = f"{int(time.time())}_{file.name}"
        supabase.storage.from_(bucket_name).upload(file_name, file.getvalue(), file_options={"content-type": file.type})
        return supabase.storage.from_(bucket_name).get_public_url(file_name)
    except Exception as e: return None

# ==========================================
# 資料庫 CRUD 與 邏輯函式
# ==========================================
def load_data():
    response = supabase.table("equipment").select("*").order("id", desc=True).execute()
    df = pd.DataFrame(response.data)
    if 'borrowed' not in df.columns and not df.empty: df['borrowed'] = 0
    return df

def add_equipment_to_db(data):
    supabase.table("equipment").insert(data).execute()

def update_equipment_in_db(uid, updates):
    supabase.table("equipment").update(updates).eq("uid", uid).execute()

def delete_equipment_from_db(uid):
    supabase.table("equipment").delete().eq("uid", uid).execute()

def add_borrow_record(uid, name, borrower, contact, qty):
    data = {
        "equipment_uid": uid, "equipment_name": name,
        "borrower_name": borrower, "contact_info": contact,
        "borrow_qty": qty, "is_returned": False,
        "borrow_date": datetime.utcnow().isoformat()
    }
    supabase.table("borrow_records").insert(data).execute()

def load_active_borrows():
    res = supabase.table("borrow_records").select("*").eq("is_returned", False).order("borrow_date", desc=True).execute()
    return pd.DataFrame(res.data)

def return_equipment_transaction(record_id, uid, qty_to_return):
    eq_res = supabase.table("equipment").select("borrowed").eq("uid", uid).execute()
    if eq_res.data:
        current = eq_res.data[0]['borrowed']
        new_borrowed = max(0, current - qty_to_return)
        supabase.table("equipment").update({"borrowed": new_borrowed}).eq("uid", uid).execute()
        supabase.table("borrow_records").update({"is_returned": True, "return_date": datetime.utcnow().isoformat()}).eq("id", record_id).execute()
        return True
    return False

def get_taiwan_time_str():
    return (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M')

def get_today_str():
    return (datetime.utcnow() + timedelta(hours=8)).strftime('%Y-%m-%d')

def get_status_display(row):
    manual = row.get('status', '在庫')
    if manual in ['維修中', '報廢']: return manual, "grey"
    
    total = row.get('quantity', 1)
    borrowed = row.get('borrowed', 0)
    avail = total - borrowed
    
    if avail <= 0: return "🔴 已借完 / 暫無庫存", "red"
    elif borrowed > 0: return f"⚠️ 部分在庫 (剩 {avail})", "orange"
    else: return f"✅ 足額在庫 ({avail}/{total})", "green"

# ==========================================
# PDF 生成模組
# ==========================================
class PDFReport(FPDF):
    def __init__(self):
        super().__init__(orientation='L', unit='mm', format='A4')
        self.set_auto_page_break(auto=False) 
    def header(self):
        if os.path.exists(FONT_FILE):
            try: self.add_font('ChineseFont', '', FONT_FILE); self.set_font('ChineseFont', '', 12)
            except: self.set_font("Helvetica", size=12)
        self.set_font_size(24); self.cell(0, 15, txt="團隊器材借用 / 清點單", ln=1, align='C')
        self.set_font_size(10); self.cell(0, 8, txt=f"製表日期: {get_taiwan_time_str()}", ln=1, align='R')
        self.line(10, self.get_y(), 287, self.get_y()); self.ln(2)
        self.set_font_size(12); self.set_fill_color(232, 139, 0); self.set_text_color(255, 255, 255); self.set_line_width(0.3)
        headers = ["分類項目", "編號", "器材名稱", "借用數量", "營前清點", "離營清點", "營後清點"]
        col_w = [35, 30, 80, 20, 37, 37, 37] 
        for i, h in enumerate(headers): self.cell(col_w[i], 10, h, border=1, align='C', fill=True)
        self.ln(); self.set_text_color(0, 0, 0) 
    def footer(self):
        self.set_y(-25)
        if os.path.exists(FONT_FILE): self.set_font('ChineseFont', '', 12)
        self.cell(90, 10, "器材負責人：__________________", align='L')
        self.cell(90, 10, "活動負責人：__________________", align='C')
        self.cell(90, 10, "指導老師：__________________", align='R')

def create_pdf(cart_data, text_display_map):
    pdf = PDFReport(); pdf.add_page()
    if os.path.exists(FONT_FILE): pdf.set_font('ChineseFont', '', 11)
    else: pdf.set_font("Helvetica", size=11)
    col_w = [35, 30, 80, 20, 37, 37, 37] 
    total_rows = len(cart_data); fill = False; pdf.set_fill_color(245, 245, 245)
    for i in range(total_rows):
        if pdf.get_y() > 170: pdf.add_page(); force_new = True 
        else: force_new = False
        item = cart_data[i]; cat = item['category']
        draw_top = (i == 0 or cart_data[i-1]['category'] != cat or force_new)
        draw_bottom = (i == total_rows - 1 or cart_data[i+1]['category'] != cat or (pdf.get_y() + 10 > 170))
        cat_border = 'LR' + ('T' if draw_top else '') + ('B' if draw_bottom else '')
        cat_disp = cat if (text_display_map.get(i) or force_new) else ""
        pdf.cell(col_w[0], 10, cat_disp, border=cat_border, align='C', fill=False)
        pdf.cell(col_w[1], 10, str(item['uid']), border=1, align='C', fill=fill)
        name = str(item['name']); 
        if pdf.get_string_width(name) > col_w[2]-2: name = name[:14]+"..."
        pdf.cell(col_w[2], 10, name, border=1, align='C', fill=fill)
        pdf.cell(col_w[3], 10, str(item['borrow_qty']), border=1, align='C', fill=fill)
        for _ in range(3): pdf.cell(col_w[4], 10, "", border=1, align='C', fill=fill)
        pdf.ln(); fill = not fill 
    return pdf.output()

# ==========================================
# Word 生成模組
# ==========================================
def set_cell_bg(cell, color_hex):
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:val'), 'clear'); shading_elm.set(qn('w:color'), 'auto'); shading_elm.set(qn('w:fill'), color_hex)
    cell._tc.get_or_add_tcPr().append(shading_elm)

def create_word(cart_data):
    doc = Document(); section = doc.sections[0]; section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width = Mm(297); section.page_height = Mm(210)
    section.left_margin = Mm(12); section.right_margin = Mm(12)
    heading = doc.add_paragraph("團隊器材借用 / 清點單"); heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = heading.runs[0]; run.font.size = Pt(24); run.bold = True
    run.font.name = "Microsoft JhengHei"; run.element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft JhengHei')
    date_para = doc.add_paragraph(f"製表日期: {get_taiwan_time_str()}"); date_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    table = doc.add_table(rows=1, cols=7); table.style = 'Table Grid'; table.autofit = False 
    headers = ["分類項目", "編號", "器材名稱", "借用數量", "營前清點", "離營清點", "營後清點"]
    widths = [12, 10, 30, 8, 13, 13, 13]; total_width_mm = 273 
    hdr_row = table.rows[0]
    for i, text in enumerate(headers):
        cell = hdr_row.cells[i]; cell.text = text; set_cell_bg(cell, "E88B00")
        para = cell.paragraphs[0]; para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = para.runs[0]; run.font.color.rgb = RGBColor(255, 255, 255); run.font.bold = True
        run.font.size = Pt(12); run.font.name = "Microsoft JhengHei"; run.element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft JhengHei')
        cell.width = Mm(total_width_mm * widths[i] / 100)
    for idx, item in enumerate(cart_data):
        row_cells = table.add_row().cells
        row_cells[0].text = item['category']; row_cells[1].text = str(item['uid'])
        row_cells[2].text = str(item['name']); row_cells[3].text = str(item['borrow_qty'])
        for i, cell in enumerate(row_cells):
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER; cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            cell.width = Mm(total_width_mm * widths[i] / 100)
            run = cell.paragraphs[0].runs[0] if cell.paragraphs[0].runs else cell.paragraphs[0].add_run()
            run.font.name = "Microsoft JhengHei"; run.element.rPr.rFonts.set(qn('w:eastAsia'), 'Microsoft JhengHei')
    col_idx = 0; start_row = 1 
    while start_row < len(table.rows):
        cat_text = table.rows[start_row].cells[col_idx].text; end_row = start_row + 1
        while end_row < len(table.rows) and table.rows[end_row].cells[col_idx].text == cat_text:
            table.rows[end_row].cells[col_idx].text = ""; end_row += 1
        if end_row > start_row + 1: table.rows[start_row].cells[col_idx].merge(table.rows[end_row - 1].cells[col_idx])
        start_row = end_row
    doc.add_paragraph("\n"); sig_table = doc.add_table(rows=1, cols=3); sig_table.autofit = True; sig_table.width = Mm(273)
    sig_cells = sig_table.rows[0].cells
    sig_cells[0].text = "器材負責人：__________________"; sig_cells[1].text = "活動負責人：__________________"
    sig_cells[2].text = "指導老師：__________________"
    for cell in sig_cells: cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    sig_cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT; sig_cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    f = io.BytesIO(); doc.save(f); f.seek(0); return f

# ==========================================
# 介面定義 (Header & Modals) - 修正：移到主邏輯之前
# ==========================================
def render_header():
    st.markdown(f"""<div id="my-fixed-header"><img src="{LOGO_URL}" style="height: 50px;"></div>""", unsafe_allow_html=True)
    st.markdown("""<style>.header-buttons { position: fixed; top: 20px; right: 30px; z-index: 9999999; }</style>""", unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="header-buttons">', unsafe_allow_html=True)
        if not st.session_state.is_admin:
            cnt = len(st.session_state.cart)
            if st.button(f"📋 借用清單 ({cnt})", type="primary"): show_cart_modal(load_data())
        st.markdown('</div>', unsafe_allow_html=True)

# 🔥 修正：加回 @st.dialog 標籤
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
        
        status_opts = ["在庫", "維修中", "報廢"]
        try: status_idx = status_opts.index(item['status'])
        except: status_idx = 0
        new_status = c2.selectbox("狀態", status_opts, index=status_idx)
        
        c3, c4 = st.columns(2)
        new_qty = c3.number_input("總數量", min_value=1, value=item.get('quantity', 1))
        # 管理員手動校正借出量
        new_borrowed = c4.number_input("已借出", min_value=0, max_value=new_qty, value=item.get('borrowed', 0))
        
        new_loc = st.text_input("位置", value=item['location'] or "")
        new_file = st.file_uploader("更換照片", type=['jpg','png'])
        
        col_up, col_del = st.columns(2)
        submitted = col_up.form_submit_button("💾 儲存更新", type="primary", use_container_width=True)
        delete = col_del.checkbox("刪除此器材")

        if submitted:
            if delete:
                delete_equipment_from_db(item['uid'])
                st.toast("🗑️ 已刪除")
                time.sleep(1); st.rerun()
            else:
                url = upload_image(new_file) if new_file else item['image_url']
                updates = {
                    "name": new_name, "category": new_cat, "status": new_status,
                    "quantity": new_qty, "borrowed": new_borrowed,
                    "location": new_loc, "image_url": url,
                    "updated_at": datetime.now().strftime("%Y-%m-%d")
                }
                update_equipment_in_db(item['uid'], updates)
                st.toast("✅ 更新成功！")
                time.sleep(1); st.rerun()

@st.dialog("➕ 新增器材", width="small")
def show_add_modal():
    st.caption("填寫資訊")
    with st.form("add_form", clear_on_submit=True):
        name = st.text_input("名稱"); uid = st.text_input("編號")
        c1, c2 = st.columns(2); cat = c1.selectbox("分類", CATEGORY_OPTIONS); status = c2.selectbox("狀態", ["在庫", "維修中", "報廢"])
        c3, c4 = st.columns(2); qty = c3.number_input("總數", 1); loc = c4.text_input("位置")
        file = st.file_uploader("照片")
        if st.form_submit_button("新增", type="primary", use_container_width=True):
            url = upload_image(file)
            add_equipment_to_db({"uid": uid, "name": name, "category": cat, "status": status, "location": loc, "quantity": qty, "borrowed": 0, "image_url": url, "updated_at": datetime.now().strftime("%Y-%m-%d")})
            st.rerun()

@st.dialog("📋 借用清單確認", width="large")
def show_cart_modal(df):
    if st.session_state.borrow_success:
        st.success("🎉 借用申請已送出！庫存已更新。")
        final_list = st.session_state.last_borrow_data
        today_date = get_today_str(); file_prefix = f"equipment_list_{today_date}"
        
        text_map = {}
        s_idx = 0; t_rows = len(final_list)
        for i in range(t_rows + 1):
            if i == t_rows or final_list[i]['category'] != final_list[s_idx]['category']:
                text_map[s_idx + (i - s_idx)//2] = final_list[s_idx]['category']
                s_idx = i

        c1, c2 = st.columns(2)
        with c1:
            try:
                # 🔥 修正：正確傳入 text_map
                pdf_data = create_pdf(final_list, text_map)
                st.download_button("📄 下載 PDF", data=bytes(pdf_data), file_name=f"{file_prefix}.pdf", mime="application/pdf", type="primary", use_container_width=True)
            except Exception as e: st.error(f"PDF 錯誤: {e}")
        with c2:
            try:
                word_data = create_word(final_list)
                st.download_button("📝 下載 Word", data=word_data, file_name=f"{file_prefix}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
            except Exception as e: st.error(f"Word 錯誤: {e}")
            
        if st.button("關閉視窗", use_container_width=True):
            st.session_state.borrow_success = False; st.rerun()
        return

    if not st.session_state.cart:
        st.info("清單目前是空的。"); 
        if st.button("關閉"): st.rerun()
        return

    st.info("💡 請填寫借用人資訊，並確認數量。")
    with st.container(border=True):
        c_name, c_contact = st.columns(2)
        borrower_name = c_name.text_input("借用人姓名 (必填)", placeholder="王小明")
        contact_info = c_contact.text_input("聯絡方式 (電話/系級)", placeholder="0912-345-678")

    cart_uids = list(st.session_state.cart.keys())
    cart_rows = df[df['uid'].isin(cart_uids)].copy().sort_values(by=['category', 'uid'])
    final_borrow_list = []
    
    for i, row in cart_rows.iterrows():
        c1, c2, c3, c4 = st.columns([2, 3, 2, 2])
        with c1: st.write(f"**{row['category']}**")
        with c2: st.write(f"{row['name']}")
        avail = row['quantity'] - row.get('borrowed', 0)
        with c3: st.caption(f"剩餘: {avail}")
        with c4:
            max_val = max(1, avail) 
            borrow_qty = st.number_input("數量", 1, max_val, st.session_state.cart.get(row['uid'], 1), key=f"qty_{row['uid']}", label_visibility="collapsed")
            st.session_state.cart[row['uid']] = borrow_qty
            item_dict = row.to_dict(); item_dict['borrow_qty'] = borrow_qty
            final_borrow_list.append(item_dict)

    st.markdown("---")
    if st.button("✅ 確認借用 (送出申請)", type="primary", use_container_width=True):
        if not borrower_name: st.error("⚠️ 請填寫借用人姓名！")
        else:
            try:
                for item in final_borrow_list:
                    new_borrowed = item.get('borrowed', 0) + item['borrow_qty']
                    update_equipment_in_db(item['uid'], {'borrowed': new_borrowed})
                    add_borrow_record(item['uid'], item['name'], borrower_name, contact_info, item['borrow_qty'])
                st.session_state.last_borrow_data = final_borrow_list
                st.session_state.borrow_success = True
                st.session_state.cart = {}
                for key in st.session_state.keys():
                    if key.startswith("check_"): st.session_state[key] = False
                st.rerun() 
            except Exception as e: st.error(f"系統錯誤: {e}")

    if st.button("🗑️ 清空清單", use_container_width=True):
        st.session_state.cart = {}
        for key in list(st.session_state.keys()):
            if key.startswith("check_"): st.session_state[key] = False
        st.rerun()

def admin_return_page():
    st.markdown("### 📋 借還紀錄 / 歸還管理")
    active_borrows = load_active_borrows()
    if active_borrows.empty: st.info("目前沒有未歸還的器材。")
    else:
        for i, row in active_borrows.iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 3, 2, 2])
                with c1: st.write(f"**{row['borrower_name']}**"); st.caption(f"📞 {row['contact_info']}")
                with c2: st.write(f"📦 {row['equipment_name']}"); st.caption(f"#{row['equipment_uid']}")
                with c3: 
                    b_date = datetime.fromisoformat(row['borrow_date']).strftime('%Y-%m-%d %H:%M')
                    st.write(f"借用數量: **{row['borrow_qty']}**"); st.caption(f"🕒 {b_date}")
                with c4:
                    if st.button("↩️ 歸還", key=f"ret_{row['id']}", type="primary", use_container_width=True):
                        if return_equipment_transaction(row['id'], row['equipment_uid'], row['borrow_qty']):
                            st.toast(f"✅ {row['equipment_name']} 已歸還！"); time.sleep(1); st.rerun()
                        else: st.error("歸還失敗")

def render_inventory_view():
    df = load_data()
    if not df.empty:
        total = df['quantity'].sum(); borrowed = df['borrowed'].sum()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("📦 器材種類", len(df)); m2.metric("📊 庫存總數", int(total))
        m3.metric("✅ 剩餘可用", int(total - borrowed)); m4.metric("👤 目前借出", int(borrowed))

    st.write(""); search_query = st.text_input("🔍 搜尋...", label_visibility="collapsed")
    st.write(""); selected_cat = st.pills("分類", ["全部顯示"] + CATEGORY_OPTIONS, default="全部顯示")

    if not df.empty:
        filtered = df
        if selected_cat != "全部顯示": filtered = df[df['category'] == selected_cat]
        if search_query: filtered = filtered[filtered['name'].str.contains(search_query, case=False) | filtered['uid'].str.contains(search_query, case=False)]
        
        if not filtered.empty:
            st.write("")
            cols = st.columns(3)
            for i, (idx, row) in enumerate(filtered.iterrows()):
                with cols[i % 3]:
                    with st.container(border=True):
                        img = row['image_url'] if row['image_url'] else "https://cdn-icons-png.flaticon.com/512/4992/4992482.png"
                        st.markdown(f'<div style="height:200px;overflow:hidden;border-radius:4px;display:flex;justify-content:center;background:#f0f2f6;margin-bottom:12px;"><img src="{img}" style="height:100%;width:100%;object-fit:cover;"></div>', unsafe_allow_html=True)
                        st.markdown(f"#### {row['name']}")
                        
                        stat_txt, stat_col = get_status_display(row)
                        st.caption(f"#{row['uid']} | 📍 {row['location']}")
                        st.markdown(f':{stat_col}[**{stat_txt}**]')
                        st.markdown("---")
                        
                        if st.session_state.is_admin:
                            if st.button("⚙️ 管理", key=f"btn_{row['uid']}", use_container_width=True): show_edit_modal(row)
                        else:
                            avail = row['quantity'] - row.get('borrowed', 0)
                            dis = (avail <= 0) or (row.get('status') in ['維修中', '報廢'])
                            sel = row['uid'] in st.session_state.cart
                            if st.checkbox("加入借用清單", key=f"check_{row['uid']}", value=sel, disabled=dis):
                                if not sel: st.session_state.cart[row['uid']] = 1; st.rerun()
                            elif sel:
                                del st.session_state.cart[row['uid']]; st.rerun()
        else: st.info("無資料")
    else: st.info("無資料")

# ==========================================
# 狀態與 CSS
# ==========================================
if 'cart' not in st.session_state: st.session_state.cart = {}
if 'borrow_success' not in st.session_state: st.session_state.borrow_success = False
if 'last_borrow_data' not in st.session_state: st.session_state.last_borrow_data = []
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'current_page' not in st.session_state: st.session_state.current_page = "home"

st.markdown(f"""
<style>
    header[data-testid="stHeader"] {{ display: none; }}
    .stApp {{ background-color: {PAGE_BG_COLOR} !important; }}
    .main .block-container {{ padding-top: 100px !important; max-width: 1200px !important; }}
    #my-fixed-header {{ position: fixed; top: 0; left: 0; width: 100%; height: {NAV_HEIGHT}; background-color: {NAV_BG_COLOR}; z-index: 999999; display: flex; align-items: center; padding: 0 30px; }}
    div[data-testid="stVerticalBlockBorderWrapper"] {{ background-color: white !important; border: 1px solid #ddd !important; border-radius: 8px !important; padding: 20px !important; }}
    .stButton>button {{ border-radius: 6px; background-color: white; color: #333; border: 1px solid #ccc; }}
    .stButton>button[kind="primary"] {{ background-color: {NAV_BG_COLOR} !important; color: white !important; border: none !important; }}
</style>
""", unsafe_allow_html=True)

def go_to(page): st.session_state.current_page = page
def perform_logout(): 
    st.session_state.is_admin = False; st.session_state.cart = {}; st.session_state.borrow_success = False
    for k in list(st.session_state.keys()): 
        if k.startswith("check_"): del st.session_state[k]
    go_to("home")
def perform_login():
    if st.session_state.password_input == st.secrets["ADMIN_PASSWORD"]: st.session_state.is_admin = True; go_to("home")
    else: st.error("密碼錯誤")

# ==========================================
# 主執行邏輯 (放在檔案最下方)
# ==========================================
if st.session_state.current_page == "login":
    render_header(); _, c, _ = st.columns([1,5,1])
    with c:
        with st.container(border=True):
            st.markdown("<h2 style='text-align:center'>🔐 管理員登入</h2>", unsafe_allow_html=True)
            st.text_input("密碼", type="password", key="password_input")
            b1, b2 = st.columns(2)
            b1.button("取消", on_click=lambda: go_to("home"), use_container_width=True)
            b2.button("登入", type="primary", on_click=perform_login, use_container_width=True)
else:
    render_header()
    c_title, c_actions = st.columns([3, 1], vertical_alignment="bottom")
    with c_title: st.title("團隊器材中心")
    with c_actions:
        if st.session_state.is_admin:
            b1, b2 = st.columns(2, gap="small")
            b1.button("➕ 新增", on_click=show_add_modal, use_container_width=True)
            b2.button("登出", on_click=perform_logout, type="primary", use_container_width=True)
        else:
            st.button("🔐 管理員登入", on_click=lambda: go_to("login"), type="primary", use_container_width=True)

    if st.session_state.is_admin:
        tab1, tab2 = st.tabs(["📦 器材庫存管理", "📋 借還紀錄 / 歸還"])
        with tab1: render_inventory_view()
        with tab2: admin_return_page()
    else:
        render_inventory_view()
