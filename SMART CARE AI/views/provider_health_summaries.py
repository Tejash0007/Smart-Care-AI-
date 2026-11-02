"""
SmartCare AI – Healthcare Provider Portal: Health Summaries.
Generate, preview, and download structured clinical summary reports for any authorized patient.
Uses ReportLab to produce vector PDF medical summaries.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from services.auth_service import require_auth
from database.db import (
    get_patients_for_provider,
    get_patient_by_id,
    get_health_records
)
from utils.helpers import (
    load_css,
    generate_pdf_report,
    get_bmi_category,
    get_bp_classification,
    get_glucose_classification,
    get_heart_rate_classification,
    render_metric_card,
    style_plotly_fig
)

load_css()
user = require_auth(allowed_roles=["provider"])
provider_id = user.get("provider_id", "DOC-101")

# Header Hero Banner
st.markdown(
    """
    <div class="portal-header-provider">
        <h1 class="portal-header-title">📊 Clinical Health Summaries & Documentation</h1>
        <p class="portal-header-subtitle">Generate exportable PDF medical documentation and longitudinal vitals trajectories for authorized patients.</p>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;">
            <span class="badge-pill info" style="background:#FFFFFF; color:#243447; border:none; font-weight:700;">Vector PDF Engine (ReportLab)</span>
            <span class="badge-pill purple" style="background:#FFFFFF; color:#8064D8; border:none; font-weight:700;">Clinical Demographics</span>
            <span class="badge-pill success" style="background:#FFFFFF; color:#20A779; border:none; font-weight:700;">Longitudinal Physiological Table</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

patients = get_patients_for_provider(provider_id)
if not patients:
    st.warning("No patients currently authorized.")
    st.stop()

# Select Patient
pt_map = {f"{p['patient_id']} - {p['name']}": p['patient_id'] for p in patients}
selected_pt = st.selectbox("Select Patient to Generate Clinical Summary:", list(pt_map.keys()), key="doc_sum_pt_sel")
pid = pt_map[selected_pt]
patient = get_patient_by_id(pid)
records = get_health_records(patient_id=pid)

# Action Bar: Download PDF
top_c1, top_c2 = st.columns([3, 1])
with top_c1:
    st.markdown(f"### Summary for **{patient['name']}** (`{patient['patient_id']}`)")
    st.caption(f"Age: {patient['age']} • Sex: {patient['gender']} • Blood Group: **{patient['blood_group']}** • Enrolled: {patient['registration_date']}")
with top_c2:
    try:
        pdf_bytes = generate_pdf_report(patient, records)
        fname = f"SmartCare_Clinical_Summary_{pid}_{datetime.now().strftime('%Y%m%d')}.pdf"
        st.download_button(
            label="📥 Download Clinical PDF Summary",
            data=pdf_bytes,
            file_name=fname,
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"PDF note: {e}")

st.markdown("<hr style='border:none; border-top:1.5px solid #E2E8F0; margin:16px 0;'>", unsafe_allow_html=True)

if records:
    df_rec = pd.DataFrame(records)
    df_rec['recording_date'] = pd.to_datetime(df_rec['recording_date'])
    df_rec = df_rec.sort_values('recording_date', ascending=False)
    latest = df_rec.iloc[0]

    st.markdown("#### 🩺 Baseline Physiological Indicators")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        bp_c = get_bp_classification(int(latest['systolic_bp']), int(latest['diastolic_bp']))
        st.markdown(
            render_metric_card(
                title="Blood Pressure",
                value=f"{latest['systolic_bp']}/{latest['diastolic_bp']} mmHg",
                subtitle=bp_c['status'],
                category="blue",
                icon="💓"
            ),
            unsafe_allow_html=True
        )
    with c2:
        glu_c = get_glucose_classification(float(latest['blood_glucose']), str(latest['glucose_context']))
        st.markdown(
            render_metric_card(
                title="Blood Glucose",
                value=f"{latest['blood_glucose']} mg/dL",
                subtitle=glu_c['status'],
                category="teal",
                icon="🩸"
            ),
            unsafe_allow_html=True
        )
    with c3:
        bmi_c = get_bmi_category(float(latest['bmi']))
        st.markdown(
            render_metric_card(
                title="Body Mass Index",
                value=f"{latest['bmi']} kg/m²",
                subtitle=bmi_c['category'],
                category="green",
                icon="⚖️"
            ),
            unsafe_allow_html=True
        )
    with c4:
        hr_c = get_heart_rate_classification(int(latest['heart_rate']))
        st.markdown(
            render_metric_card(
                title="Resting Pulse",
                value=f"{latest['heart_rate']} BPM",
                subtitle=hr_c['status'],
                category="purple",
                icon="🫀"
            ),
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Historical Measurements Table
    st.markdown("#### 📋 Recorded Clinical Vitals Log")
    df_table = df_rec[[
        "recording_date", "weight_kg", "height_cm", "bmi", "systolic_bp",
        "diastolic_bp", "blood_glucose", "glucose_context", "heart_rate", "notes"
    ]].copy()
    df_table['recording_date'] = df_table['recording_date'].dt.strftime('%Y-%m-%d')
    df_table.columns = ["Date", "Weight(kg)", "Height(cm)", "BMI", "Systolic", "Diastolic", "Glucose", "Context", "Pulse", "Notes"]
    st.dataframe(df_table, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Chart
    st.markdown("#### 📈 Longitudinal Vitals Trajectory")
    df_chron = df_rec.sort_values('recording_date', ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_chron['recording_date'],
        y=df_chron['systolic_bp'],
        mode='lines+markers',
        name='Systolic BP (mmHg)',
        line=dict(color='#E45B65', width=2.5),
        marker=dict(size=7, color='#E45B65')
    ))
    fig.add_trace(go.Scatter(
        x=df_chron['recording_date'],
        y=df_chron['diastolic_bp'],
        mode='lines+markers',
        name='Diastolic BP (mmHg)',
        line=dict(color='#3498DB', width=2.5),
        marker=dict(size=7, color='#3498DB')
    ))
    fig.add_trace(go.Scatter(
        x=df_chron['recording_date'],
        y=df_chron['blood_glucose'],
        mode='lines+markers',
        name='Blood Glucose (mg/dL)',
        line=dict(color='#8064D8', width=2, dash='dot'),
        marker=dict(size=6, color='#8064D8')
    ))

    fig = style_plotly_fig(fig, title=f"Vitals Longitudinal Trajectory for {patient['name']}", height=320)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No biometric measurements logged yet for this patient.")
