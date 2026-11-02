"""
SmartCare AI – Healthcare Provider Portal: Clinical Dashboard.
Executive clinical overview of authorized patient population,
vitals trajectories, reports requiring review, and rapid workflow navigation.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from services.auth_service import require_auth
from database.db import (
    get_dashboard_metrics,
    get_patients_for_provider,
    get_health_records,
    get_provider_by_id
)
from utils.helpers import load_css, render_metric_card, style_plotly_fig

load_css()
user = require_auth(allowed_roles=["provider"])
provider_id = user.get("provider_id", "DOC-101")
provider_info = get_provider_by_id(provider_id)

provider_name = provider_info["name"] if provider_info else user["name"]
specialty = provider_info["specialty"] if provider_info else "Cardiologist"
hospital = provider_info["hospital"] if provider_info else "SmartCare Apex Healthcare Center"

# Header Hero Banner with Deep Navy/Teal Gradient
st.markdown(
    f"""
    <div class="portal-header-provider">
        <h1 class="portal-header-title">Welcome, {provider_name} 🩺</h1>
        <p class="portal-header-subtitle">Clinical population surveillance, diagnostic panel reviews, and AI decision support.</p>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:12px;">
            <span class="badge-pill info" style="background:#FFFFFF; color:#243447; border:none; font-weight:700;">ID: {provider_id}</span>
            <span class="badge-pill purple" style="background:#FFFFFF; color:#8064D8; border:none; font-weight:700;">Specialty: {specialty}</span>
            <span class="badge-pill success" style="background:#FFFFFF; color:#20A779; border:none; font-weight:600;">🏥 {hospital}</span>
            <span class="badge-pill info" style="background:#FFFFFF; color:#087F8C; border:none; font-weight:700;">Active Clinical Privileges</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Clinical Practice Notice
st.markdown(
    """
    <div class="clinical-disclaimer">
        ⚖️ <strong>Clinical Practice Notice:</strong> SmartCare AI is an administrative and clinical decision support system. 
        Biometric visualizations and AI summaries are designed to assist consultation prep and medical record keeping. 
        They do <strong>not</strong> substitute for independent professional diagnosis, clinical laboratory testing, or physical examination.
    </div>
    """,
    unsafe_allow_html=True
)

# Fetch aggregate metrics for this authorized provider
metrics = get_dashboard_metrics(provider_id=provider_id)

# Top Stat Cards (Using Modern SaaS Category Colors)
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(
        render_metric_card(
            title="Authorized Patients",
            value=f"{metrics['total_patients']} Patients",
            subtitle="Under active clinical purview",
            category="blue",
            icon="👥"
        ),
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        render_metric_card(
            title="Total Vitals Logged",
            value=f"{metrics['total_records']} Logs",
            subtitle="Longitudinal biometrics",
            category="teal",
            icon="📈"
        ),
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        render_metric_card(
            title="Lab Reports on File",
            value=f"{metrics['total_reports']} Reports",
            subtitle="Digital PDF diagnostics",
            category="purple",
            icon="📁"
        ),
        unsafe_allow_html=True
    )

with col4:
    st.markdown(
        render_metric_card(
            title="AI Inquiries Logged",
            value=f"{metrics['total_ai_consultations']} Queries",
            subtitle="Clinical synthesis runs",
            category="green",
            icon="🤖"
        ),
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# Main Body
col_left, col_right = st.columns([1.6, 1.2])

with col_left:
    st.markdown("### 📊 Population Vitals Trajectory")
    records = get_health_records(provider_id=provider_id)

    if records:
        df_r = pd.DataFrame(records)
        df_r['recording_date'] = pd.to_datetime(df_r['recording_date'])
        df_r = df_r.sort_values('recording_date')

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_r['recording_date'],
            y=df_r['systolic_bp'],
            mode='lines+markers',
            name='Systolic BP (mmHg)',
            line=dict(color='#E45B65', width=3),
            marker=dict(size=8, color='#E45B65')
        ))
        fig.add_trace(go.Scatter(
            x=df_r['recording_date'],
            y=df_r['diastolic_bp'],
            mode='lines+markers',
            name='Diastolic BP (mmHg)',
            line=dict(color='#3498DB', width=3),
            marker=dict(size=8, color='#3498DB')
        ))
        fig.add_trace(go.Scatter(
            x=df_r['recording_date'],
            y=df_r['heart_rate'],
            mode='lines+markers',
            name='Pulse (BPM)',
            line=dict(color='#087F8C', width=2.5, dash='dot'),
            marker=dict(size=7, color='#087F8C')
        ))

        fig = style_plotly_fig(fig, title="Longitudinal Vitals Trend Across Registered Patients", height=330)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No biometric health records logged yet.")

    # Clinical Navigation Quick Actions
    st.markdown("### 🚀 Clinical Workflows")
    w1, w2 = st.columns(2)
    with w1:
        st.markdown(
            """
            <div class="saas-metric-card card-blue" style="margin-bottom:14px; padding:18px 20px;">
                <div style="font-size:1.1rem; font-weight:700; color:#3498DB; margin-bottom:4px;">👥 Patient Registry</div>
                <p style="font-size:0.88rem; color:#64748B; margin:0;">Search patient directory, inspect demographic profiles, and update or delete records securely.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            """
            <div class="saas-metric-card card-teal" style="margin-bottom:14px; padding:18px 20px;">
                <div style="font-size:1.1rem; font-weight:700; color:#087F8C; margin-bottom:4px;">➕ Register Patient</div>
                <p style="font-size:0.88rem; color:#64748B; margin:0;">Enroll a new patient with unique ID sequencing and instant clinical access granting.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with w2:
        st.markdown(
            """
            <div class="saas-metric-card card-purple" style="margin-bottom:14px; padding:18px 20px;">
                <div style="font-size:1.1rem; font-weight:700; color:#8064D8; margin-bottom:4px;">🩺 AI Clinical Support</div>
                <p style="font-size:0.88rem; color:#64748B; margin:0;">Analyze lab tests with Gemini, highlight out-of-range markers, and generate structured clinical summaries.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            """
            <div class="saas-metric-card card-green" style="margin-bottom:14px; padding:18px 20px;">
                <div style="font-size:1.1rem; font-weight:700; color:#20A779; margin-bottom:4px;">📊 Health Summaries</div>
                <p style="font-size:0.88rem; color:#64748B; margin:0;">Generate and download formatted PDF clinical summary documents for medical consultations.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

with col_right:
    # Recent Patient Registrations
    st.markdown("### 👥 Recent Patients")
    recent_pts = metrics["recent_patients"]
    if recent_pts:
        df_p_show = pd.DataFrame(recent_pts)[[
            "patient_id", "name", "age", "gender", "contact", "registration_date"
        ]]
        df_p_show.columns = ["ID", "Name", "Age", "Sex", "Contact", "Registered"]
        st.dataframe(df_p_show, use_container_width=True, hide_index=True)
    else:
        st.caption("No registered patients found.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Recent Clinical Inquiries
    st.markdown("### 💬 Recent AI Clinical Inquiries")
    recent_ai = metrics["recent_interactions"]
    if recent_ai:
        df_ai = pd.DataFrame(recent_ai)[["category", "interaction_date"]]
        df_ai.columns = ["Topic Category", "Timestamp"]
        st.dataframe(df_ai, use_container_width=True, hide_index=True)
    else:
        st.caption("No AI consultations logged yet.")
