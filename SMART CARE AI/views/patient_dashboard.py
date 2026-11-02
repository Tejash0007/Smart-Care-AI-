"""
SmartCare AI – Patient Portal: Personal Health Dashboard.
Displays personalized health overview, latest vitals, uploaded lab reports,
longitudinal trend charts, and 1-click personal health summary export.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from services.auth_service import require_auth
from database.db import (
    get_patient_dashboard_metrics,
    get_patient_by_id,
    get_health_records
)
from utils.helpers import (
    load_css,
    get_bmi_category,
    get_bp_classification,
    get_glucose_classification,
    get_heart_rate_classification,
    generate_pdf_report,
    render_metric_card,
    style_plotly_fig
)

load_css()
user = require_auth(allowed_roles=["patient"])
patient_id = user.get("patient_id")

if not patient_id:
    st.error("Patient profile not linked to this account. Please contact clinic administration.")
    st.stop()

patient = get_patient_by_id(patient_id)
metrics = get_patient_dashboard_metrics(patient_id)
latest = metrics["latest_vital"]

# Header Hero Banner
st.markdown(
    f"""
    <div class="portal-header-patient">
        <h1 class="portal-header-title">Welcome back, {patient['name']} 👋</h1>
        <p class="portal-header-subtitle">Your personal health overview and longitudinal biometric tracking hub.</p>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:12px;">
            <span class="badge-pill info" style="background:#FFFFFF; color:#087F8C; border:none; font-weight:700;">ID: {patient_id}</span>
            <span class="badge-pill info" style="background:#FFFFFF; color:#243447; border:none; font-weight:600;">Age: {patient['age']} Years</span>
            <span class="badge-pill purple" style="background:#FFFFFF; color:#8064D8; border:none; font-weight:700;">Blood: {patient['blood_group']}</span>
            <span class="badge-pill success" style="background:#FFFFFF; color:#20A779; border:none; font-weight:600;">Sex: {patient['gender']}</span>
            <span class="badge-pill info" style="background:#FFFFFF; color:#1D72B8; border:none; font-weight:600;">📞 {patient['contact']}</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Clinical Safety Notice
st.markdown(
    """
    <div class="clinical-disclaimer">
        🛡️ <strong>Personal Wellness Notice:</strong> SmartCare AI provides self-monitoring data organization and educational assistance. 
        Measurements and AI outputs do <strong>not</strong> constitute a clinical diagnosis or prescription. 
        In medical emergencies, call local emergency services immediately (112 / 108 / 911).
    </div>
    """,
    unsafe_allow_html=True
)

# Top Stat Cards (Using Modern SaaS Category Colors)
col1, col2, col3, col4 = st.columns(4)

with col1:
    bp_text = f"{latest['systolic_bp']}/{latest['diastolic_bp']} mmHg" if latest else "No data"
    bp_sub = get_bp_classification(latest['systolic_bp'], latest['diastolic_bp'])['status'] if latest else "Log vitals to start"
    st.markdown(
        render_metric_card(
            title="Blood Pressure",
            value=bp_text,
            subtitle=bp_sub,
            category="blue",
            icon="💓"
        ),
        unsafe_allow_html=True
    )

with col2:
    glu_text = f"{latest['blood_glucose']} mg/dL" if latest else "No data"
    glu_sub = f"{latest['glucose_context']} Reading" if latest else "Metabolic monitoring"
    st.markdown(
        render_metric_card(
            title="Blood Glucose",
            value=glu_text,
            subtitle=glu_sub,
            category="teal",
            icon="🩸"
        ),
        unsafe_allow_html=True
    )

with col3:
    bmi_text = f"{latest['bmi']} kg/m²" if latest else "No data"
    bmi_sub = get_bmi_category(latest['bmi'])['category'] if latest else "Height & weight check"
    st.markdown(
        render_metric_card(
            title="Body Mass Index",
            value=bmi_text,
            subtitle=bmi_sub,
            category="green",
            icon="⚖️"
        ),
        unsafe_allow_html=True
    )

with col4:
    rep_count = metrics["total_reports"]
    st.markdown(
        render_metric_card(
            title="Lab Reports",
            value=f"{rep_count} Files",
            subtitle="Digital PDF records on file",
            category="purple",
            icon="📑"
        ),
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# Main Dashboard Content
dash_left, dash_right = st.columns([1.6, 1.2])

with dash_left:
    st.markdown("### 📈 My Vitals Trajectory")
    all_vitals = metrics["all_vitals"]

    if all_vitals:
        df_v = pd.DataFrame(all_vitals)
        df_v['recording_date'] = pd.to_datetime(df_v['recording_date'])
        df_v = df_v.sort_values('recording_date')

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_v['recording_date'],
            y=df_v['systolic_bp'],
            mode='lines+markers',
            name='Systolic BP (mmHg)',
            line=dict(color='#E45B65', width=3),
            marker=dict(size=8, color='#E45B65')
        ))
        fig.add_trace(go.Scatter(
            x=df_v['recording_date'],
            y=df_v['diastolic_bp'],
            mode='lines+markers',
            name='Diastolic BP (mmHg)',
            line=dict(color='#3498DB', width=3),
            marker=dict(size=8, color='#3498DB')
        ))
        fig.add_trace(go.Scatter(
            x=df_v['recording_date'],
            y=df_v['heart_rate'],
            mode='lines+markers',
            name='Pulse (BPM)',
            line=dict(color='#087F8C', width=2.5, dash='dot'),
            marker=dict(size=7, color='#087F8C')
        ))

        fig = style_plotly_fig(fig, title="Longitudinal Blood Pressure & Pulse Trends", height=330)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No vitals measurements logged yet. Use the Health Tracker to log your first reading!")

    # Quick Feature Modules Overview
    st.markdown("### 🚀 Personal Health Services")
    m1, m2 = st.columns(2)
    with m1:
        st.markdown(
            """
            <div class="saas-metric-card card-teal" style="margin-bottom:14px; padding:18px 20px;">
                <div style="font-size:1.1rem; font-weight:700; color:#087F8C; margin-bottom:4px;">🤖 AI Health Assistant</div>
                <p style="font-size:0.88rem; color:#64748B; margin:0;">Ask questions about medical terms, lab results, hydration, or prepare questions for your doctor.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            """
            <div class="saas-metric-card card-blue" style="margin-bottom:14px; padding:18px 20px;">
                <div style="font-size:1.1rem; font-weight:700; color:#3498DB; margin-bottom:4px;">📈 Health Tracker</div>
                <p style="font-size:0.88rem; color:#64748B; margin:0;">Record daily blood pressure, weight, glucose, and heart rate with interactive graphs.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with m2:
        st.markdown(
            """
            <div class="saas-metric-card card-purple" style="margin-bottom:14px; padding:18px 20px;">
                <div style="font-size:1.1rem; font-weight:700; color:#8064D8; margin-bottom:4px;">📁 My Medical Reports</div>
                <p style="font-size:0.88rem; color:#64748B; margin:0;">Upload and view PDF lab reports. Ask Gemini questions to translate complex medical terms.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            """
            <div class="saas-metric-card card-green" style="margin-bottom:14px; padding:18px 20px;">
                <div style="font-size:1.1rem; font-weight:700; color:#20A779; margin-bottom:4px;">📜 My Health History</div>
                <p style="font-size:0.88rem; color:#64748B; margin:0;">Review your complete chronological medical records history and export your printable PDF summary.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

with dash_right:
    # Recent Uploaded Reports
    st.markdown("### 📁 Recent Lab Reports")
    recent_reps = metrics["recent_reports"]
    if recent_reps:
        for rep in recent_reps:
            st.markdown(
                f"""
                <div class="saas-metric-card card-purple" style="margin-bottom:12px; padding:16px 18px;">
                    <div style="font-weight:700; color:#243447; font-size:1rem;">📄 {rep['report_name']}</div>
                    <div style="font-size:0.84rem; color:#64748B; margin-top:4px;">
                        Uploaded: {rep['upload_date'][:16]} • {rep['file_size_kb']} KB
                    </div>
                    <div style="margin-top:8px;">
                        <span class="badge-pill purple">{rep['report_type']}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.caption("No lab reports uploaded yet. Upload your first PDF in **My Medical Reports**.")

    st.markdown("<br>", unsafe_allow_html=True)

    # 1-Click PDF Export
    st.markdown("### 📑 Personal Health Summary")
    records = get_health_records(patient_id=patient_id)
    try:
        pdf_bytes = generate_pdf_report(patient, records)
        fname = f"SmartCare_Summary_{patient_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
        st.download_button(
            label="📥 Download My Health Summary PDF",
            data=pdf_bytes,
            file_name=fname,
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
        st.caption("Structured, vector PDF summary prepared for physician consultations.")
    except Exception as e:
        st.error(f"PDF note: {e}")
