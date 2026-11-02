"""
SmartCare AI – Healthcare Provider Portal: Patient Records.
Comprehensive clinical records browser for authorized patients.
Inspect vitals trajectories, historical diagnostic logs, and uploaded reports.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date

from services.auth_service import require_auth
from database.db import (
    get_patients_for_provider,
    get_patient_by_id,
    get_health_records,
    get_medical_reports,
    add_health_record,
    calculate_bmi
)
from utils.helpers import (
    load_css,
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

# Header Banner
st.markdown(
    """
    <div class="portal-header-provider">
        <h1 class="portal-header-title">📋 Clinical Patient Records</h1>
        <p class="portal-header-subtitle">Review authorized patient charts, longitudinal vitals measurements, and laboratory diagnostics.</p>
    </div>
    """,
    unsafe_allow_html=True
)

patients = get_patients_for_provider(provider_id)
if not patients:
    st.warning("No patients currently enrolled under your authorized clinical purview.")
    st.stop()

# Select Patient
pt_map = {f"{p['patient_id']} - {p['name']}": p['patient_id'] for p in patients}
selected_key = st.selectbox("Select Patient Chart to Open:", list(pt_map.keys()), key="doc_records_sel")
active_pid = pt_map[selected_key]
patient = get_patient_by_id(active_pid)
records = get_health_records(patient_id=active_pid)
reports = get_medical_reports(patient_id=active_pid)

# Patient Banner
st.markdown(
    f"""
    <div class="saas-metric-card card-blue" style="margin-bottom: 20px; padding: 18px 22px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <h3 style="color:#243447; margin:0 0 4px 0; font-size:1.35rem;">{patient['name']}</h3>
                <p style="color:#64748B; font-size:0.9rem; margin:0;">
                    Patient ID: <strong>{patient['patient_id']}</strong> • Age: {patient['age']} • Sex: {patient['gender']} • Blood Group: <span class="badge-pill purple">{patient['blood_group']}</span> • Contact: {patient['contact']}
                </p>
            </div>
            <div style="text-align:right;">
                <span class="badge-pill info">Authorized Record</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

tab_vitals_charts, tab_history_table, tab_reports_list, tab_quick_vitals = st.tabs([
    "📈 Vitals Analytics & Trends",
    "📋 Complete Measurement Log",
    "📁 Uploaded Diagnostic Reports",
    "➕ Record Clinic Vitals"
])

# ------------------------------------------------------------------------------
# TAB 1: VITALS CHARTS
# ------------------------------------------------------------------------------
with tab_vitals_charts:
    st.markdown("#### Longitudinal Physiological Trajectory")

    if records:
        df_rec = pd.DataFrame(records)
        df_rec['recording_date'] = pd.to_datetime(df_rec['recording_date'])
        df_rec = df_rec.sort_values('recording_date')

        # Latest Vitals Cards
        latest = df_rec.iloc[-1]
        c1, c2, c3, c4 = st.columns(4)
        
        with c1:
            bp_c = get_bp_classification(int(latest['systolic_bp']), int(latest['diastolic_bp']))
            st.markdown(
                render_metric_card(
                    title="Latest Blood Pressure",
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
                    subtitle=f"{latest['glucose_context']} ({glu_c['status']})",
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

        # Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df_rec['recording_date'],
            y=df_rec['systolic_bp'],
            mode='lines+markers',
            name='Systolic BP (mmHg)',
            line=dict(color='#E45B65', width=2.5),
            marker=dict(size=7, color='#E45B65')
        ))
        fig.add_trace(go.Scatter(
            x=df_rec['recording_date'],
            y=df_rec['diastolic_bp'],
            mode='lines+markers',
            name='Diastolic BP (mmHg)',
            line=dict(color='#3498DB', width=2.5),
            marker=dict(size=7, color='#3498DB')
        ))
        fig.add_trace(go.Scatter(
            x=df_rec['recording_date'],
            y=df_rec['blood_glucose'],
            mode='lines+markers',
            name='Blood Glucose (mg/dL)',
            line=dict(color='#8064D8', width=2, dash='dot'),
            marker=dict(size=6, color='#8064D8')
        ))

        fig = style_plotly_fig(fig, title=f"Vitals Longitudinal Trajectory for {patient['name']}", height=340)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No biometric measurements logged yet for this patient.")

# ------------------------------------------------------------------------------
# TAB 2: MEASUREMENT LOG TABLE
# ------------------------------------------------------------------------------
with tab_history_table:
    st.markdown("#### Tabular Vitals & Biometrics")
    if records:
        df_show = pd.DataFrame(records)[[
            "id", "recording_date", "weight_kg", "height_cm", "bmi",
            "systolic_bp", "diastolic_bp", "blood_glucose", "glucose_context", "heart_rate", "notes"
        ]]
        df_show.columns = ["Entry #", "Date", "Weight(kg)", "Height(cm)", "BMI", "Systolic", "Diastolic", "Glucose", "Context", "Pulse", "Notes"]
        st.dataframe(df_show, use_container_width=True, hide_index=True)
    else:
        st.info("No records recorded yet.")

# ------------------------------------------------------------------------------
# TAB 3: DIAGNOSTIC REPORTS
# ------------------------------------------------------------------------------
with tab_reports_list:
    st.markdown("#### Patient's Uploaded Diagnostic Reports")
    if reports:
        for rep in reports:
            st.markdown(
                f"""
                <div class="saas-metric-card card-purple" style="margin-bottom:12px; padding:16px 20px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#243447; font-size:1.05rem;">📄 {rep['report_name']}</span>
                        <span class="badge-pill purple">{rep['report_type']}</span>
                    </div>
                    <div style="font-size:0.86rem; color:#64748B; margin-top:4px;">
                        Uploaded: {rep['upload_date'][:16]} • File Size: {rep['file_size_kb']} KB
                    </div>
                    {f'<div style="font-size:0.88rem; color:#243447; margin-top:6px;"><strong>Clinical Notes:</strong> {rep["notes"]}</div>' if rep["notes"] else ''}
                </div>
                """,
                unsafe_allow_html=True
            )
            with st.expander(f"🔍 Click to Read Extracted Text Preview (#{rep['id']})"):
                st.text_area("Extracted Content:", value=rep["extracted_text"][:2500], height=200, disabled=True, key=f"doc_prev_{rep['id']}")
    else:
        st.info("No diagnostic laboratory reports on file for this patient.")

# ------------------------------------------------------------------------------
# TAB 4: CLINICAL VITALS INTAKE
# ------------------------------------------------------------------------------
with tab_quick_vitals:
    st.markdown("#### ➕ Log Clinic Biometrics for this Patient")
    st.caption("Record vitals taken during consultation or triage.")

    with st.form(f"clinic_vitals_form_{active_pid}", clear_on_submit=True):
        f_w, f_h, f_d = st.columns(3)
        with f_w:
            q_w = st.number_input("Weight (kg) *", min_value=10.0, max_value=300.0, value=70.0, step=0.1)
        with f_h:
            q_h = st.number_input("Height (cm) *", min_value=50.0, max_value=250.0, value=170.0, step=0.5)
        with f_d:
            q_d = st.date_input("Measurement Date", value=date.today())

        f_sys, f_dia, f_hr = st.columns(3)
        with f_sys:
            q_sys = st.number_input("Systolic BP (mmHg) *", min_value=60, max_value=250, value=120)
        with f_dia:
            q_dia = st.number_input("Diastolic BP (mmHg) *", min_value=40, max_value=160, value=80)
        with f_hr:
            q_hr = st.number_input("Heart Rate (BPM) *", min_value=30, max_value=220, value=72)

        f_glu, f_ctx = st.columns(2)
        with f_glu:
            q_glu = st.number_input("Blood Glucose (mg/dL) *", min_value=20.0, max_value=600.0, value=95.0)
        with f_ctx:
            q_ctx = st.selectbox("Glucose Context", ["Fasting", "Post-Prandial", "Random", "Bedtime"])

        q_notes = st.text_input("Physician Consultation Notes", placeholder="e.g. Follow-up consultation, patient asymptomatic...")

        submit_clinic_vitals = st.form_submit_button("Save Patient Biometrics", type="primary", use_container_width=True)

        if submit_clinic_vitals:
            if q_sys <= q_dia:
                st.error("Systolic pressure must be strictly greater than diastolic pressure.")
            else:
                try:
                    add_health_record(
                        patient_id=active_pid,
                        weight_kg=q_w,
                        height_cm=q_h,
                        systolic_bp=q_sys,
                        diastolic_bp=q_dia,
                        blood_glucose=q_glu,
                        glucose_context=q_ctx,
                        heart_rate=q_hr,
                        recording_date=q_d.isoformat(),
                        notes=q_notes
                    )
                    st.success(f"Vitals record saved for {patient['name']}!")
                    st.rerun()
                except ValueError as val_err:
                    st.error(str(val_err))
