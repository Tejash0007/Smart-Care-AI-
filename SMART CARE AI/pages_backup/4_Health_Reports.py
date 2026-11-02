"""
SmartCare AI – Page 4: Health Reports
Generates structured patient health summaries, interactive visual reports,
and downloadable PDF medical summaries via ReportLab.
Clearly distinguishes recorded measurements from AI educational explanations.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from database.db import (
    get_all_patients,
    get_patient_by_id,
    get_health_records,
    log_ai_interaction
)
from services.gemini_service import (
    generate_health_response,
    check_api_key_configured
)
from utils.helpers import (
    load_css,
    generate_pdf_report,
    get_bmi_category,
    get_bp_classification,
    get_glucose_classification,
    get_heart_rate_classification
)

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Health Reports – SmartCare AI",
    page_icon="📑",
    layout="wide"
)

load_css()

# ==============================================================================
# SIDEBAR NAVIGATION
# ==============================================================================
with st.sidebar:
    st.markdown("### 📌 Navigation")
    st.page_link("app.py", label="Executive Dashboard", icon="🏥")
    st.page_link("pages/1_AI_Health_Assistant.py", label="AI Health Assistant", icon="🤖")
    st.page_link("pages/2_Patient_Management.py", label="Patient Management", icon="👥")
    st.page_link("pages/3_Health_Tracker.py", label="Health Tracker", icon="📈")
    st.page_link("pages/4_Health_Reports.py", label="Health Reports", icon="📑")
    st.markdown("---")
    
    api_ready = check_api_key_configured(st.session_state.get("runtime_gemini_key"))
    if api_ready:
        st.success("🟢 AI Summaries: Enabled")
    else:
        st.warning("🟠 AI Summaries: Key Needed")

    st.caption("College Minor Project • B.Tech CSE\nClinical Report Documentation")

# ==============================================================================
# HEADER
# ==============================================================================
st.markdown(
    """
    <div class="medical-header">
        <h1>📑 Clinical Health Reports & Summaries</h1>
        <p>Comprehensive patient health profiles, longitudinal vitals tracking, and exportable PDF medical summaries.</p>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="disclaimer-banner">
        ⚖️ <strong>Clarity & Non-Diagnostic Notice:</strong> Recorded biometric measurements (Blood Pressure, BMI, Blood Glucose, Heart Rate) 
        are observational data stored directly in the local database. Any AI-generated explanations provided below are strictly 
        for educational guidance to facilitate informed discussions with your licensed healthcare provider.
    </div>
    """,
    unsafe_allow_html=True
)

patients = get_all_patients()
if not patients:
    st.warning("No patients currently registered in the system.")
    st.page_link("pages/2_Patient_Management.py", label="Register a Patient First", icon="👥")
    st.stop()

# Patient Selector
pt_map = {f"{p['patient_id']} - {p['name']}": p['patient_id'] for p in patients}
selected_pt_key = st.selectbox("Select Patient to Generate Report:", list(pt_map.keys()))
current_id = pt_map[selected_pt_key]
patient = get_patient_by_id(current_id)
records = get_health_records(patient_id=current_id)

# ==============================================================================
# REPORT ACTIONS BAR: PDF EXPORT & PRINT
# ==============================================================================
act_col1, act_col2 = st.columns([3, 1])
with act_col1:
    st.markdown(f"### Report for **{patient['name']}** (`{patient['patient_id']}`)")
with act_col2:
    # Generate PDF in memory using ReportLab
    try:
        pdf_bytes = generate_pdf_report(patient, records)
        filename = f"SmartCare_Report_{patient['patient_id']}_{datetime.now().strftime('%Y%m%d')}.pdf"
        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_bytes,
            file_name=filename,
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"PDF generation note: {e}")

# ==============================================================================
# PATIENT PROFILE DEMOGRAPHICS CARD
# ==============================================================================
st.markdown("#### 🪪 Patient Profile Summary")
d_col1, d_col2, d_col3, d_col4 = st.columns(4)

with d_col1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Full Name / ID</div>
            <div class="metric-value" style="font-size: 1.25rem;">{patient['name']}</div>
            <div class="metric-desc">ID: <code>{patient['patient_id']}</code></div>
        </div>
        """,
        unsafe_allow_html=True
    )
with d_col2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Demographics</div>
            <div class="metric-value" style="font-size: 1.25rem;">{patient['age']} yrs • {patient['gender']}</div>
            <div class="metric-desc">Blood Group: <strong>{patient['blood_group']}</strong></div>
        </div>
        """,
        unsafe_allow_html=True
    )
with d_col3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Contact & Record</div>
            <div class="metric-value" style="font-size: 1.1rem;">{patient['contact']}</div>
            <div class="metric-desc">Registered: {patient['registration_date']}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
with d_col4:
    rec_count = len(records)
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Total Records Logged</div>
            <div class="metric-value">{rec_count}</div>
            <div class="metric-desc">Vitals measurements on file</div>
        </div>
        """,
        unsafe_allow_html=True
    )

st.markdown("<br>", unsafe_allow_html=True)

# ==============================================================================
# LATEST MEASUREMENTS & HISTORICAL VITALS
# ==============================================================================
if records:
    df_rec = pd.DataFrame(records)
    df_rec['recording_date'] = pd.to_datetime(df_rec['recording_date'])
    df_rec = df_rec.sort_values('recording_date', ascending=False)
    latest = df_rec.iloc[0]

    st.markdown("#### 🩺 Most Recent Vitals (Baseline)")
    m1, m2, m3, m4 = st.columns(4)
    
    with m1:
        bp_info = get_bp_classification(int(latest['systolic_bp']), int(latest['diastolic_bp']))
        st.markdown(
            f"""
            <div class="metric-card" style="border-left-color: {bp_info['color']};">
                <div class="metric-title">Blood Pressure</div>
                <div class="metric-value">{int(latest['systolic_bp'])}/{int(latest['diastolic_bp'])} <span style="font-size:0.9rem;">mmHg</span></div>
                <div class="metric-desc" style="color:{bp_info['color']}; font-weight:600;">{bp_info['status']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with m2:
        glu_info = get_glucose_classification(float(latest['blood_glucose']), str(latest['glucose_context']))
        st.markdown(
            f"""
            <div class="metric-card" style="border-left-color: {glu_info['color']};">
                <div class="metric-title">Blood Glucose</div>
                <div class="metric-value">{latest['blood_glucose']} <span style="font-size:0.9rem;">mg/dL</span></div>
                <div class="metric-desc" style="color:{glu_info['color']}; font-weight:600;">{latest['glucose_context']} • {glu_info['status']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with m3:
        bmi_info = get_bmi_category(float(latest['bmi']))
        st.markdown(
            f"""
            <div class="metric-card" style="border-left-color: {bmi_info['color']};">
                <div class="metric-title">Body Mass Index (BMI)</div>
                <div class="metric-value">{latest['bmi']} <span style="font-size:0.9rem;">kg/m²</span></div>
                <div class="metric-desc" style="color:{bmi_info['color']}; font-weight:600;">{bmi_info['category']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with m4:
        hr_info = get_heart_rate_classification(int(latest['heart_rate']))
        st.markdown(
            f"""
            <div class="metric-card" style="border-left-color: {hr_info['color']};">
                <div class="metric-title">Heart Rate</div>
                <div class="metric-value">{int(latest['heart_rate'])} <span style="font-size:0.9rem;">BPM</span></div>
                <div class="metric-desc" style="color:{hr_info['color']}; font-weight:600;">{hr_info['status']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Historical Measurements Table
    st.markdown("#### 📋 Recorded Vitals Log")
    display_cols = ["recording_date", "weight_kg", "height_cm", "bmi", "systolic_bp", "diastolic_bp", "blood_glucose", "glucose_context", "heart_rate", "notes"]
    df_show = df_rec[display_cols].copy()
    df_show['recording_date'] = df_show['recording_date'].dt.strftime('%Y-%m-%d')
    df_show.columns = ["Date", "Weight (kg)", "Height (cm)", "BMI", "Systolic", "Diastolic", "Glucose (mg/dL)", "Context", "Pulse (BPM)", "Clinical Notes"]
    st.dataframe(df_show, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Health Trajectory Visual Chart
    st.markdown("#### 📈 Longitudinal Vitals Trajectory")
    df_chron = df_rec.sort_values('recording_date', ascending=True)

    fig_rep = go.Figure()
    fig_rep.add_trace(go.Scatter(
        x=df_chron['recording_date'],
        y=df_chron['systolic_bp'],
        mode='lines+markers',
        name='Systolic BP (mmHg)',
        line=dict(color='#dc3545', width=2)
    ))
    fig_rep.add_trace(go.Scatter(
        x=df_chron['recording_date'],
        y=df_chron['diastolic_bp'],
        mode='lines+markers',
        name='Diastolic BP (mmHg)',
        line=dict(color='#0f4c81', width=2)
    ))
    fig_rep.add_trace(go.Scatter(
        x=df_chron['recording_date'],
        y=df_chron['blood_glucose'],
        mode='lines+markers',
        name='Blood Glucose (mg/dL)',
        line=dict(color='#ff9f1c', width=2, dash='dot')
    ))

    fig_rep.update_layout(
        title="Patient Vitals Trajectory Over Time",
        title_font=dict(size=14, color="#0f4c81"),
        xaxis_title="Date of Measurement",
        yaxis_title="Reading Value",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        height=320,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    fig_rep.update_xaxes(showgrid=True, gridcolor="#f1f5f9")
    fig_rep.update_yaxes(showgrid=True, gridcolor="#f1f5f9")
    st.plotly_chart(fig_rep, use_container_width=True)

    # ==========================================================================
    # OPTIONAL AI EDUCATIONAL REPORT SUMMARY (CLEARLY DISTINGUISHED)
    # ==========================================================================
    st.markdown("---")
    st.markdown("#### 🤖 AI Educational Report Insights (Optional)")
    st.caption("Generate an educational interpretation of these recorded trends to help formulate questions for your doctor.")

    api_configured = check_api_key_configured(st.session_state.get("runtime_gemini_key"))

    if not api_configured:
        st.info("💡 To generate an AI educational explanation, ensure your Gemini API key is configured in `.env` or the Assistant page.")
    else:
        if st.button("Generate AI Educational Summary & Doctor Discussion Points", type="secondary"):
            # Construct a safe, de-identified prompt with ONLY numeric measurements and zero personal identifiers
            vitals_summary_text = (
                f"Biometric measurements recorded for educational review:\n"
                f"- Age: {patient['age']}, Gender: {patient['gender']}\n"
                f"- Latest Blood Pressure: {latest['systolic_bp']}/{latest['diastolic_bp']} mmHg\n"
                f"- Latest Blood Glucose: {latest['blood_glucose']} mg/dL ({latest['glucose_context']})\n"
                f"- Body Mass Index: {latest['bmi']} kg/m²\n"
                f"- Resting Pulse: {latest['heart_rate']} BPM\n"
                f"- Total records logged across time: {len(records)}\n\n"
                "Please provide:\n"
                "1. A plain-English educational explanation of what these measurements reflect in general physiological terms.\n"
                "2. General lifestyle and nutrition principles related to these values.\n"
                "3. Exactly 3 thoughtful questions the patient could ask their doctor during their next routine checkup.\n"
                "Remember: Do not diagnose, do not prescribe, and state clearly that this is educational guidance."
            )

            with st.spinner("Generating educational summary with Google Gemini..."):
                success, ai_summary = generate_health_response(
                    [{"role": "user", "content": vitals_summary_text}],
                    runtime_api_key=st.session_state.get("runtime_gemini_key")
                )

                if success:
                    log_ai_interaction("Educational Report Explanation")
                    st.markdown(
                        """
                        <div style="background-color: #f0fdf4; border: 1px solid #bbf7d0; border-left: 5px solid #22c55e; border-radius: 8px; padding: 16px; margin-top: 12px;">
                            <h4 style="color: #166534; margin: 0 0 8px 0;">🌿 AI Educational Insights (Non-Diagnostic)</h4>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    st.markdown(ai_summary)
                else:
                    st.error(ai_summary)

else:
    st.info("No biometric measurements recorded for this patient yet. Log measurements in the Health Tracker to view charts and generate reports.")
