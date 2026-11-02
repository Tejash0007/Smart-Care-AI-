"""
SmartCare AI – AI-Powered Smart Healthcare System
Master Application Router & Role-Based Portal Controller.
Dynamically orchestrates Patient Portal and Healthcare Provider Portal using st.navigation.
"""

import os
import sys

# Ensure application root directory is prioritized in sys.path (supports nested folder deployment)
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import streamlit as st
from database.db import init_db, seed_sample_data
from services.auth_service import get_current_user, logout_user
from services.gemini_service import check_api_key_configured, get_model_name
from utils.helpers import load_css

# ==============================================================================
# GLOBAL PAGE CONFIGURATION & THEME
# ==============================================================================
st.set_page_config(
    page_title="SmartCare AI – Smart Healthcare System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load global SaaS healthcare stylesheet
load_css()

# Initialize SQLite database and populate initial demo accounts (guaranteed once-only)
init_db()
seed_sample_data()

# ==============================================================================
# SESSION AUTHENTICATION & ROUTING
# ==============================================================================
user = get_current_user()

# Sidebar Brand Header
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand-box">
            <h2 class="sidebar-brand-title">🏥 SmartCare AI</h2>
            <div class="sidebar-brand-caption">Healthcare Intelligence Platform</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if user:
        role_label = "Patient Portal" if user["role"] == "patient" else "Provider Portal"
        badge_class = "badge-patient-portal" if user["role"] == "patient" else "badge-provider-portal"
        id_display = user.get("patient_id") or user.get("provider_id") or user.get("username")
        user_display_name = user.get('name') or user['username'].title()

        st.markdown(
            f"""
            <div class="user-profile-badge">
                <div class="user-name-label">{user_display_name}</div>
                <div class="user-role-label">Identifier: <strong>{id_display}</strong></div>
                <span class="sidebar-portal-badge {badge_class}">{role_label}</span>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("🚪 Sign Out", key="sidebar_logout_btn", use_container_width=True):
            logout_user()

        st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1.5px solid #E2E8F0;'>", unsafe_allow_html=True)

    # API Status Indicator
    api_ready = check_api_key_configured()
    if api_ready:
        st.markdown(
            """
            <div style="background-color:#EFF9F5; border:1px solid #B8E8D5; border-left:4px solid #20A779; border-radius:8px; padding:8px 12px; margin-bottom:10px;">
                <span style="font-size:0.86rem; font-weight:700; color:#0D5E43;">🟢 Gemini AI: Active</span>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="background-color:#FEF9EE; border:1px solid #FAEFCF; border-left:4px solid #E5A000; border-radius:8px; padding:8px 12px; margin-bottom:10px;">
                <span style="font-size:0.86rem; font-weight:700; color:#B87B00;">🟠 AI Setup Needed</span>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.caption(f"🧠 Engine: `{get_model_name()}`")
    st.markdown("<hr style='margin: 12px 0; border: none; border-top: 1.5px solid #E2E8F0;'>", unsafe_allow_html=True)
    st.caption("🎓 B.Tech CSE Minor Project\nNon-diagnostic Healthcare System")


# ==============================================================================
# ROLE-BASED NAVIGATION ORCHESTRATION
# ==============================================================================
if not user:
    # Unauthenticated: Show Login & Registration Portal
    auth_page = st.Page("views/auth_view.py", title="Sign In & Portal Access", icon="🔐", default=True)
    pg = st.navigation([auth_page])
    pg.run()

elif user["role"] == "patient":
    # Patient Portal: Authenticated personal health maintenance
    p_dash = st.Page("views/patient_dashboard.py", title="Dashboard", icon="🏠", default=True)
    p_ai = st.Page("views/patient_ai_assistant.py", title="AI Health Assistant", icon="🤖")
    p_reports = st.Page("views/patient_reports.py", title="My Medical Reports", icon="📁")
    p_tracker = st.Page("views/patient_tracker.py", title="Health Tracker", icon="📈")
    p_history = st.Page("views/patient_history.py", title="My Health History", icon="📜")
    p_profile = st.Page("views/patient_profile.py", title="My Profile", icon="👤")

    pg = st.navigation({
        "Patient Portal": [p_dash, p_ai, p_reports, p_tracker, p_history, p_profile]
    })
    pg.run()

elif user["role"] == "provider":
    # Healthcare Provider Portal: Clinical records & administrative workflows
    doc_dash = st.Page("views/provider_dashboard.py", title="Dashboard", icon="🏥", default=True)
    doc_registry = st.Page("views/provider_registry.py", title="Patient Registry", icon="👥")
    doc_register = st.Page("views/provider_register_patient.py", title="Register Patient", icon="➕")
    doc_records = st.Page("views/provider_patient_records.py", title="Patient Records", icon="📋")
    doc_reports = st.Page("views/provider_medical_reports.py", title="Medical Reports", icon="📑")
    doc_ai = st.Page("views/provider_ai_support.py", title="AI Clinical Support", icon="🩺")
    doc_summaries = st.Page("views/provider_health_summaries.py", title="Health Summaries", icon="📊")
    doc_profile = st.Page("views/provider_profile.py", title="Provider Profile", icon="👨‍⚕️")

    pg = st.navigation({
        "Healthcare Provider Portal": [
            doc_dash, doc_registry, doc_register, doc_records,
            doc_reports, doc_ai, doc_summaries, doc_profile
        ]
    })
    pg.run()
