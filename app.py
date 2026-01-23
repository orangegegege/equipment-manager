# ==========================================
# ✨ 純裝飾 Header (只放圖，絕對垂直置中版)
# ==========================================
def render_deco_header():
    # 我們在這裡直接寫死 CSS，確保它一定會聽話
    st.markdown(f"""
    <div id="my-deco-header" style="
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: {NAV_HEIGHT};
        background-color: {NAV_BG_COLOR};
        z-index: 9999999;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        
        /* 👇👇👇 這三行就是「垂直置中」的關鍵魔法 👇👇👇 */
        display: flex;              /* 1. 開啟排版模式 */
        align-items: center;        /* 2. 垂直方向：置中對齊 */
        padding-left: 20px;         /* 3. 靠左邊留一點空隙 */
    ">
        <img src="{LOGO_URL}" style="height: 70%; object-fit: contain;">
    </div>
    """, unsafe_allow_html=True)
