"""
SmartCare AI – Page 3: Health Tracker
Logs biometric and vital measurements (Weight, Height, BMI, BP, Blood Glucose, Heart Rate).
Displays historical trends with interactive Plotly visual charts and clinical screening reference classifications.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime

from database.db import (
    get_all_patients,
    get_patient_by_id,
    add_health_record,
    get_health_records,
    delete_health_record,
    calculate_bmi
)
from utils.helpers import (
    load_css,
    get_bmi_category,
    get_bp_classification,
    get_glucose_classification,
    get_heart_rate_classification
)

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Health Tracker – SmartCare AI",
    page_icon="📈",
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
    st.caption("College Minor Project • B.Tech CSE\nBiometric Vitals & Analytics")

# ==============================================================================
# HEADER
# ==============================================================================
st.markdown(
    """
    <div class="medical-header">
        <h1>📈 Biometric Health Tracker</h1>
        <p>Log longitudinal vital measurements, track physiological trends, and review educational screening ranges.</p>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="disclaimer-banner">
        ⚠️ <strong>Non-Diagnostic Screening Notice:</strong> Health measurements recorded here reflect self-monitoring 
        and routine clinic vitals. Individual numbers vary with hydration, caffeine, exertion, and stress. 
        Classifications are general screening guidelines only and do <strong>not</strong> constitute a clinical diagnosis.
    </div>
    """,
    unsafe_allow_html=True
)

# Ensure patients exist
patients = get_all_patients()
if not patients:
    st.warning("⚠️ No patients registered in the system yet. Please register a patient first in the Patient Management section.")
    st.page_link("pages/2_Patient_Management.py", label="Go to Patient Management", icon="👥")
    st.stop()

# ==============================================================================
# PATIENT SELECTION & DATE FILTER BAR
# ==============================================================================
patient_options = {f"{p['patient_id']} - {p['name']}": p['patient_id'] for p in patients}

col_sel_pt, col_start_date, col_end_date = st.columns([2, 1, 1])

with col_sel_pt:
    selected_label = st.selectbox("Select Patient to Track:", list(patient_options.keys()))
    current_pt_id = patient_options[selected_label]
    current_pt = get_patient_by_id(current_pt_id)

with col_start_date:
    filter_start = st.date_input("From Date:", value=date(2026, 1, 1))

with col_end_date:
    filter_end = st.date_input("To Date:", value=date.today())

# Date validation
if filter_start > filter_end:
    st.warning("⚠️ 'From Date' cannot be later than 'To Date'. Please adjust date filters above.")

tab_log, tab_trends, tab_history = st.tabs(["📝 Log New Measurements", "📊 Visual Trends & Charts", "📜 Historical Records Table"])

# ==============================================================================
# TAB 1: LOG NEW MEASUREMENTS
# ==============================================================================
with tab_log:
    st.markdown(f"### 📝 Record Health Vitals for **{current_pt['name']}** (`{current_pt_id}`)")

    col_w, col_h, col_date = st.columns(3)
    with col_w:
        weight = st.number_input("Weight (kg) *", min_value=10.0, max_value=300.0, value=70.0, step=0.1, key="log_w")
    with col_h:
        height = st.number_input("Height (cm) *", min_value=50.0, max_value=250.0, value=170.0, step=0.5, key="log_h")
    with col_date:
        rec_date = st.date_input("Recording Date *", value=date.today(), key="log_d")

    # Dynamic Live Calculated BMI Preview
    live_bmi = calculate_bmi(weight, height)
    bmi_info = get_bmi_category(live_bmi)
    st.info(f"💡 Calculated Body Mass Index (BMI): **{live_bmi} kg/m²** — Categorized as **{bmi_info['category']}** ({bmi_info['info']})")

    col_sys, col_dia, col_hr = st.columns(3)
    with col_sys:
        systolic = st.number_input("Systolic BP (mmHg) *", min_value=60, max_value=250, value=120, step=1,
                                   help="Pressure during heartbeat contraction (top number).", key="log_sys")
    with col_dia:
        diastolic = st.number_input("Diastolic BP (mmHg) *", min_value=40, max_value=160, value=80, step=1,
                                    help="Pressure between beats when resting (bottom number).", key="log_dia")
    with col_hr:
        heart_rate = st.number_input("Resting Heart Rate (BPM) *", min_value=30, max_value=220, value=72, step=1, key="log_hr")

    col_glu, col_glu_ctx = st.columns(2)
    with col_glu:
        glucose = st.number_input("Blood Glucose (mg/dL) *", min_value=20.0, max_value=600.0, value=95.0, step=1.0, key="log_glu")
    with col_glu_ctx:
        glucose_context = st.selectbox(
            "Measurement Context *",
            ["Fasting (before breakfast)", "Post-Prandial (2h after meal)", "Random / Casual", "Bedtime"],
            key="log_ctx"
        )

    notes = st.text_area("Measurement Observations / Clinical Notes", placeholder="e.g. Measured at morning rest, after light morning walk...", key="log_notes")

    if st.button("Save Biometric Record", type="primary", use_container_width=True):
        if weight <= 0 or height <= 0:
            st.error("Please enter valid positive numbers for height and weight.")
        elif systolic <= diastolic:
            st.error("Systolic blood pressure (top number) must be greater than diastolic (bottom number).")
        else:
            add_health_record(
                patient_id=current_pt_id,
                weight_kg=weight,
                height_cm=height,
                systolic_bp=systolic,
                diastolic_bp=diastolic,
                blood_glucose=glucose,
                glucose_context=glucose_context.split(" ")[0],
                heart_rate=heart_rate,
                recording_date=rec_date.isoformat(),
                notes=notes
            )
            st.success(f"✅ Vitals successfully recorded for patient {current_pt['name']} ({current_pt_id})!")
            st.rerun()

# ==============================================================================
# TAB 2: VISUAL TRENDS & CHARTS (PLOTLY)
# ==============================================================================
with tab_trends:
    st.markdown(f"### 📈 Biometric Trends for **{current_pt['name']}**")

    # Fetch patient's records filtered by date
    records = get_health_records(
        patient_id=current_pt_id,
        start_date=filter_start.isoformat(),
        end_date=filter_end.isoformat()
    )

    if records:
        df = pd.DataFrame(records)
        df['recording_date'] = pd.to_datetime(df['recording_date'])
        df = df.sort_values('recording_date')

        # Latest Vitals Metric Cards
        latest = df.iloc[-1]
        latest_bmi_cat = get_bmi_category(float(latest['bmi']))
        latest_bp_cat = get_bp_classification(int(latest['systolic_bp']), int(latest['diastolic_bp']))
        latest_glu_cat = get_glucose_classification(float(latest['blood_glucose']), str(latest['glucose_context']))

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f"""
                <div class="metric-card" style="border-left-color: {latest_bp_cat['color']};">
                    <div class="metric-title">Blood Pressure</div>
                    <div class="metric-value">{int(latest['systolic_bp'])}/{int(latest['diastolic_bp'])} <span style="font-size:0.9rem; color:#64748b;">mmHg</span></div>
                    <div class="metric-desc" style="color: {latest_bp_cat['color']}; font-weight:600;">{latest_bp_cat['status']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c2:
            st.markdown(
                f"""
                <div class="metric-card" style="border-left-color: {latest_glu_cat['color']};">
                    <div class="metric-title">Blood Glucose</div>
                    <div class="metric-value">{latest['blood_glucose']} <span style="font-size:0.9rem; color:#64748b;">mg/dL</span></div>
                    <div class="metric-desc" style="color: {latest_glu_cat['color']}; font-weight:600;">{latest['glucose_context']} • {latest_glu_cat['status']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c3:
            st.markdown(
                f"""
                <div class="metric-card" style="border-left-color: {latest_bmi_cat['color']};">
                    <div class="metric-title">Body Mass Index</div>
                    <div class="metric-value">{latest['bmi']} <span style="font-size:0.9rem; color:#64748b;">kg/m²</span></div>
                    <div class="metric-desc" style="color: {latest_bmi_cat['color']}; font-weight:600;">{latest_bmi_cat['category']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with c4:
            hr_cat = get_heart_rate_classification(int(latest['heart_rate']))
            st.markdown(
                f"""
                <div class="metric-card" style="border-left-color: {hr_cat['color']};">
                    <div class="metric-title">Heart Rate</div>
                    <div class="metric-value">{int(latest['heart_rate'])} <span style="font-size:0.9rem; color:#64748b;">BPM</span></div>
                    <div class="metric-desc" style="color: {hr_cat['color']}; font-weight:600;">{hr_cat['status']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Chart 1: Blood Pressure Trend
        fig_bp = go.Figure()
        fig_bp.add_trace(go.Scatter(
            x=df['recording_date'],
            y=df['systolic_bp'],
            mode='lines+markers',
            name='Systolic (mmHg)',
            line=dict(color='#dc3545', width=3),
            marker=dict(size=8)
        ))
        fig_bp.add_trace(go.Scatter(
            x=df['recording_date'],
            y=df['diastolic_bp'],
            mode='lines+markers',
            name='Diastolic (mmHg)',
            line=dict(color='#0f4c81', width=3),
            marker=dict(size=8)
        ))
        # Add normal threshold line
        fig_bp.add_hline(y=120, line_dash="dash", line_color="#28a745", annotation_text="Systolic Normal (<120)", annotation_position="top left")
        fig_bp.add_hline(y=80, line_dash="dot", line_color="#17a2b8", annotation_text="Diastolic Normal (<80)", annotation_position="bottom left")
        
        fig_bp.update_layout(
            title="Blood Pressure Longitudinal Trajectory",
            title_font=dict(size=15, color="#0f4c81"),
            xaxis_title="Date",
            yaxis_title="Pressure (mmHg)",
            plot_bgcolor="#ffffff",
            paper_bgcolor="#ffffff",
            height=340,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        fig_bp.update_xaxes(showgrid=True, gridcolor="#f1f5f9")
        fig_bp.update_yaxes(showgrid=True, gridcolor="#f1f5f9")
        st.plotly_chart(fig_bp, use_container_width=True)

        # Charts 2 & 3: Blood Glucose & Weight/BMI in two columns
        col_g, col_w_chart = st.columns(2)

        with col_g:
            fig_glu = px.line(
                df,
                x='recording_date',
                y='blood_glucose',
                markers=True,
                title="Blood Glucose Trend (mg/dL)",
                color_discrete_sequence=['#ff9f1c']
            )
            fig_glu.add_hline(y=100, line_dash="dash", line_color="#28a745", annotation_text="Fasting Upper Normal (99 mg/dL)")
            fig_glu.update_layout(
                title_font=dict(size=14, color="#0f4c81"),
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
                height=300,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            fig_glu.update_xaxes(showgrid=True, gridcolor="#f1f5f9")
            fig_glu.update_yaxes(showgrid=True, gridcolor="#f1f5f9")
            st.plotly_chart(fig_glu, use_container_width=True)

        with col_w_chart:
            fig_bmi = px.line(
                df,
                x='recording_date',
                y='bmi',
                markers=True,
                title="Body Mass Index (BMI kg/m²)",
                color_discrete_sequence=['#20a39e']
            )
            fig_bmi.add_hrect(y0=18.5, y1=24.9, fillcolor="#28a745", opacity=0.1, line_width=0, annotation_text="Normal BMI Range")
            fig_bmi.update_layout(
                title_font=dict(size=14, color="#0f4c81"),
                plot_bgcolor="#ffffff",
                paper_bgcolor="#ffffff",
                height=300,
                margin=dict(l=20, r=20, t=40, b=20)
            )
            fig_bmi.update_xaxes(showgrid=True, gridcolor="#f1f5f9")
            fig_bmi.update_yaxes(showgrid=True, gridcolor="#f1f5f9")
            st.plotly_chart(fig_bmi, use_container_width=True)

    else:
        st.info("No records match the selected date range for this patient.")

# ==============================================================================
# TAB 3: HISTORICAL RECORDS TABLE & RECORD MANAGEMENT
# ==============================================================================
with tab_history:
    st.markdown(f"### 📜 Historical Log for **{current_pt['name']}**")
    all_pt_records = get_health_records(patient_id=current_pt_id)

    if all_pt_records:
        df_all = pd.DataFrame(all_pt_records)
        df_table = df_all[[
            "id", "recording_date", "weight_kg", "height_cm", "bmi", "systolic_bp", "diastolic_bp", "blood_glucose", "glucose_context", "heart_rate", "notes"
        ]]
        df_table.columns = ["Record ID", "Date", "Weight(kg)", "Height(cm)", "BMI", "Systolic", "Diastolic", "Glucose", "Context", "Pulse(BPM)", "Notes"]
        st.dataframe(df_table, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 🗑️ Delete Specific Record Entry")
        del_col1, del_col2 = st.columns([3, 1])
        with del_col1:
            record_choices = {f"ID #{r['id']} ({r['recording_date']} - BP {r['systolic_bp']}/{r['diastolic_bp']})": r['id'] for r in all_pt_records}
            target_rec_label = st.selectbox("Select Record Entry to Delete:", list(record_choices.keys()))
            target_rec_id = record_choices[target_rec_label]
        with del_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Delete Entry", type="secondary"):
                if delete_health_record(target_rec_id):
                    st.success("Record entry deleted successfully.")
                    st.rerun()
                else:
                    st.error("Failed to delete record.")
    else:
        st.info("No health records recorded for this patient yet.")
