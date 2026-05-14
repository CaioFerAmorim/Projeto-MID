import streamlit as st

st.set_page_config(
    page_title="MID TI – 2025",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS global
st.markdown("""
<style>
    /* Fonte e fundo geral */
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
    .main { background-color: #f4f6f9; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #002b5b 0%, #004a8d 100%);
    }
    [data-testid="stSidebar"] * { color: white !important; }
    [data-testid="stSidebar"] .stRadio label { font-size: 15px; padding: 6px 0; }

    /* Esconde o menu padrão de páginas do Streamlit */
    [data-testid="stSidebarNav"] { display: none; }

    /* Header */
    .header-bar {
        background: linear-gradient(90deg, #002b5b, #004a8d);
        color: white;
        padding: 16px 24px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    .header-bar h1 { margin: 0; font-size: 1.6rem; font-weight: 700; letter-spacing: 1px; }
    .header-bar p  { margin: 2px 0 0; font-size: 0.9rem; opacity: 0.85; }

    /* KPI Cards */
    .kpi-card {
        background: white;
        border-radius: 10px;
        padding: 18px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        border-left: 5px solid #004a8d;
        height: 100%;
    }
    .kpi-card .kpi-label { font-size: 0.75rem; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-card .kpi-value { font-size: 2rem; font-weight: 700; color: #002b5b; margin: 4px 0; }
    .kpi-card .kpi-delta { font-size: 0.8rem; }
    .kpi-card .kpi-sub   { font-size: 0.75rem; color: #888; margin-top: 4px; }
    .kpi-green { border-left-color: #16a34a; }
    .kpi-green .kpi-value { color: #16a34a; }
    .kpi-red   { border-left-color: #dc2626; }
    .kpi-red   .kpi-value { color: #dc2626; }

    /* Status badges */
    .badge-green { background:#dcfce7; color:#166534; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .badge-red   { background:#fee2e2; color:#991b1b; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .badge-gray  { background:#f1f5f9; color:#475569; padding:3px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }

    /* Tabela de desempenho */
    .perf-table { width:100%; border-collapse: collapse; font-size: 0.88rem; }
    .perf-table th { background:#002b5b; color:white; padding:10px 12px; text-align:center; font-weight:600; }
    .perf-table th.left { text-align:left; }
    .perf-table td { padding:10px 12px; border-bottom:1px solid #e2e8f0; text-align:center; }
    .perf-table td.left { text-align:left; font-weight:600; }
    .perf-table tr:hover td { background:#f8fafc; }
    .val-green { color:#16a34a; font-weight:700; font-size:1.0rem; }
    .val-red   { color:#dc2626; font-weight:700; font-size:1.0rem; }
    .trend-up   { color:#16a34a; }
    .trend-down { color:#dc2626; }
    .trend-flat { color:#64748b; }

    /* Section titles */
    .section-title {
        font-size: 1rem;
        font-weight: 700;
        color: #002b5b;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        margin: 24px 0 12px;
        padding-bottom: 6px;
        border-bottom: 2px solid #004a8d;
    }

    /* SLA por Área */
    .area-wrap { border: 1px solid #004a8d; border-radius: 6px; margin-bottom: 20px; overflow: hidden; }
    .area-header { background: #cce0f1; color: #002b5b; text-align: center; padding: 9px; font-weight: 700; font-size: 1rem; text-transform: uppercase; letter-spacing: 0.5px; }
    .sub-header  { background: #004a8d; color: white; text-align: center; padding: 7px; font-weight: 600; font-size: 0.92rem; text-transform: uppercase; }
    .sla-row-head { display:flex; background:#e3effa; font-weight:700; font-size:0.8rem; color:#002b5b; border-bottom:1px solid #004a8d; }
    .sla-row      { display:flex; background:white; border-bottom:1px solid #e2e8f0; align-items:center; }
    .sla-row:last-child { border-bottom: none; }
    .sla-col-ind { flex:2.5; padding:9px 12px; border-right:1px solid #c8d9ec; font-size:0.85rem; }
    .sla-col-val { flex:1;   padding:9px 8px;  border-right:1px solid #c8d9ec; text-align:center; font-size:0.85rem; }
    .sla-col-sta { flex:0.7; padding:9px 8px;  text-align:center; }
    .dot { height:14px; width:14px; border-radius:50%; display:inline-block; }
    .dot-g { background:#8bc34a; box-shadow:0 0 4px #8bc34a; }
    .dot-r { background:#dc2626; box-shadow:0 0 4px #dc2626; }
    .dot-x { background:#cbd5e1; }

    /* Projetos */
    .proj-table { width:100%; border-collapse:collapse; font-size:0.83rem; }
    .proj-table th { background:#002b5b; color:white; padding:9px 10px; text-align:center; font-weight:600; position:sticky; top:0; z-index:1; }
    .proj-table th.left { text-align:left; }
    .proj-table td { padding:8px 10px; border:1px solid #e2e8f0; text-align:center; vertical-align:middle; }
    .proj-table td.left { text-align:left; }
    .proj-table tr.meta-row  td { background:#f0f4f8; }
    .proj-table tr.real-row  td { background:#f8fafc; }
    .proj-table tr.acum-row  td { background:#fffbf0; }
    .proj-table tr.meta-row  td:first-child { font-weight:700; color:#004a8d; }
    .proj-table tr.real-row  td:first-child { font-weight:700; color:#16a34a; }
    .proj-table tr.acum-row  td:first-child { font-weight:700; color:#d97706; }
    .proj-table td.has-val   { color:#002b5b; font-weight:600; }
    .proj-table td.empty     { color:#cbd5e1; }
    .proj-group-header td    { background:#cce0f1 !important; color:#002b5b !important; font-weight:700; text-align:left; font-size:0.82rem; }

    /* Progress bar inline */
    .prog-bar-wrap { background:#e2e8f0; border-radius:4px; height:8px; width:100%; margin-top:4px; }
    .prog-bar-fill { height:8px; border-radius:4px; }
</style>
""", unsafe_allow_html=True)

# ── Navegação na sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📊 MID TI – 2025")
    st.markdown("---")
    pagina = st.radio(
        "Navegação",
        ["🏠 Visão Geral", "📋 SLA por Área", "🗂️ Projetos"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.caption("Fonte: mid.xlsx\nAtualizado automaticamente")

# ── Roteamento ────────────────────────────────────────────────────────────────
if pagina == "🏠 Visão Geral":
    import pages.visao_geral as pg
    pg.render()
elif pagina == "📋 SLA por Área":
    import pages.sla_por_area as pg
    pg.render()
elif pagina == "🗂️ Projetos":
    import pages.projetos as pg
    pg.render()