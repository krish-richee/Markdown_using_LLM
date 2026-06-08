import streamlit as st
import os

# ── Page config — must be first ────────────────────────────────────────────
st.set_page_config(
    page_title     = "RetailAI — Markdown Intelligence",
    page_icon      = "🏪",
    layout         = "wide",
    initial_sidebar_state = "expanded",
)

# ── Load theme CSS ─────────────────────────────────────────────────────────
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), "styles", "theme.css")
    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# ── Session state defaults ─────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "dashboard"

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:

    # Brand header
    st.markdown("""
    <div class="sidebar-brand">
        <div class="sidebar-brand-name">🏪 RetailAI</div>
        <div class="sidebar-brand-sub">Decision Intelligence</div>
    </div>
    """, unsafe_allow_html=True)

    # ── Price IQ section ───────────────────────────────────────────────────
    st.markdown(
        '<div class="nav-section-label">💲 Price IQ</div>',
        unsafe_allow_html=True
    )

    pages = {
        "dashboard":   ("📊", "Dashboard",             ""),
        "planner":     ("📋", "Markdown Planner",       ""),
        "actions":     ("✅", "Actions",                ""),
        "insights":    ("🧠", "Agent Insights",         ""),
        "reports":     ("📈", "Reports",                ""),
    }

    for key, (icon, label, badge) in pages.items():
        is_active  = st.session_state.page == key
        active_cls = "active" if is_active else ""
        badge_html = f'<span class="nav-badge">{badge}</span>' if badge else ""

        st.markdown(
            f"""<div class="nav-item {active_cls}"
                onclick="window.location.href='?page={key}'">
                {icon} {label}{badge_html}
            </div>""",
            unsafe_allow_html=True,
        )

        # Use actual buttons for navigation
        if st.button(
            f"{icon} {label}",
            key        = f"nav_{key}",
            use_container_width = True,
        ):
            st.session_state.page = key
            st.rerun()

    st.divider()

    # ── Tenant admin ───────────────────────────────────────────────────────
    st.markdown(
        '<div class="nav-section-label">⚙️ Admin</div>',
        unsafe_allow_html=True
    )

    if st.button("🔌 Data Connections", use_container_width=True):
        st.session_state.page = "connections"
        st.rerun()

    if st.button("⚙️ Settings", use_container_width=True):
        st.session_state.page = "settings"
        st.rerun()

    st.divider()

    # ── Data status ────────────────────────────────────────────────────────
    st.markdown("""
    <div style="padding: 0.5rem 0.75rem; background: #f8f9fb;
                border-radius: 8px; font-size: 0.75rem; color: #6b7280;">
        📦 <b>Data:</b> Excel (local)<br>
        🤖 <b>LLM:</b> Groq / Llama 3.1<br>
        🔍 <b>Search:</b> Tavily
    </div>
    """, unsafe_allow_html=True)

# ── Page routing ───────────────────────────────────────────────────────────
page = st.session_state.page

if page == "dashboard":
    from pages.dashboard import render
    render()

elif page == "planner":
    from pages.planner import render
    render()

elif page == "actions":
    from pages.actions import render
    render()

elif page == "insights":
    from pages.insights import render
    render()

elif page == "reports":
    from pages.reports import render
    render()

else:
    st.info("🚧 Page coming soon")
