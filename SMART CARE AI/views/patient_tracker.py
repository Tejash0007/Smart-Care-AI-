"""
SmartCare AI – Patient Portal: Personal Health Tracker.
Log personal biometric vitals (Weight, Height, BMI, BP, Blood Glucose, Heart Rate).
Displays historical trends with interactive Plotly visual charts and clinical screening reference classifications.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, datetime

from services.auth_service import require_auth
from database.db import (
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
    get_heart_rate_classification,
    style_plotly_fig
)

load_css()
user = require_auth(allowed_roles=["patient"])
patient_id = user["patient_id"]

# Header Hero Banner
st.markdown(
    """
    <div class="portal-header-patient">
        <h1 class="portal-header-title">📈 Personal Biometric Health Tracker</h1>
        <p class="portal-header-subtitle">Record daily physiological observations, visualize longitudinal trends, and track biometric markers over time.</p>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;">
            <span class="badge-pill info" style="background:#FFFFFF; color:#087F8C; border:none; font-weight:700;">Reactive BMI Engine</span>
            <span class="badge-pill purple" style="background:#FFFFFF; color:#8064D8; border:none; font-weight:700;">AHA Blood Pressure Ranges</span>
            <span class="badge-pill success" style="background:#FFFFFF; color:#20A779; border:none; font-weight:700;">WHO Nutritional Reference</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="clinical-disclaimer">
        ⚠️ <strong>Screening Guidelines Notice:</strong> Measurements recorded reflect routine self-monitoring. 
        Individual readings vary with hydration, exertion, caffeine, and stress. 
        Calculated categories are general population screening reference points, <strong>not</strong> medical diagnoses.
    </div>
    """,
    unsafe_allow_html=True
)

tab_log, tab_trends, tab_history = st.tabs([
    "📝 Log New Vitals",
    "📊 Trend Charts & Visuals",
    "📜 Vitals History Log"
])

# ------------------------------------------------------------------------------
# TAB 1: LOG NEW MEASUREMENTS
# ------------------------------------------------------------------------------
with tab_log:
    st.markdown("### 📝 Record Today's Vitals")
    st.caption("Enter your biometric measurements. Body Mass Index (BMI) is calculated automatically in real time.")

    c_w, c_h, c_d = st.columns(3)
    with c_w:
        weight = st.number_input("Weight in Kilograms (kg) *", min_value=10.0, max_value=300.0, value=72.0, step=0.1, key="pat_w")
    with c_h:
        height = st.number_input("Height in Centimeters (cm) *", min_value=50.0, max_value=250.0, value=172.0, step=0.5, key="pat_h")
    with c_d:
        rec_date = st.date_input("Measurement Date *", value=date.today(), key="pat_d")

    # Real-time reactive calculated BMI
    live_bmi = calculate_bmi(weight, height)
    bmi_info = get_bmi_category(live_bmi)
    
    # Render BMI Card
    bmi_card_cat = "green" if "Normal" in bmi_info["category"] else ("amber" if "Overweight" in bmi_info["category"] else "coral")
    st.markdown(
        f"""
        <div class="saas-metric-card card-{bmi_card_cat}" style="margin: 12px 0 20px 0; padding: 18px 22px;">
            <div style="font-size:0.82rem; font-weight:700; text-transform:uppercase; letter-spacing:0.6px; color:#64748B;">Reactive Body Mass Index Calculation</div>
            <div style="display:flex; align-items:baseline; gap:14px; margin:6px 0;">
                <span style="font-size:2rem; font-weight:800; color:#243447;">{live_bmi} kg/m²</span>
                <span class="badge-pill {bmi_info['badge']}">{bmi_info['category']}</span>
            </div>
            <div style="font-size:0.90rem; color:#64748B;">{bmi_info['info']}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    c_sys, c_dia, c_hr = st.columns(3)
    with c_sys:
        systolic = st.number_input("Systolic BP (top number, mmHg) *", min_value=60, max_value=250, value=120, step=1, key="pat_sys")
    with c_dia:
        diastolic = st.number_input("Diastolic BP (bottom number, mmHg) *", min_value=40, max_value=160, value=80, step=1, key="pat_dia")
    with c_hr:
        heart_rate = st.number_input("Resting Pulse (BPM) *", min_value=30, max_value=220, value=72, step=1, key="pat_hr")

    c_glu, c_glu_ctx = st.columns(2)
    with c_glu:
        glucose = st.number_input("Blood Glucose (mg/dL) *", min_value=20.0, max_value=600.0, value=95.0, step=1.0, key="pat_glu")
    with c_glu_ctx:
        glucose_context = st.selectbox(
            "Measurement Context *",
            ["Fasting (before breakfast)", "Post-Prandial (2h after meal)", "Random / Casual", "Bedtime"],
            key="pat_ctx"
        )

    notes = st.text_area("Measurement Observations (Optional)", placeholder="e.g. Measured at morning rest, feel well...", key="pat_notes")

    if st.button("Save Biometric Record", type="primary", use_container_width=True):
        if weight <= 0 or height <= 0:
            st.error("Please enter valid positive numbers for height and weight.")
        elif systolic <= diastolic:
            st.error("Systolic pressure must be higher than diastolic pressure.")
        else:
            try:
                add_health_record(
                    patient_id=patient_id,
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
                st.success("✅ Vitals record saved successfully!")
                st.rerun()
            except ValueError as val_err:
                st.error(str(val_err))

# ------------------------------------------------------------------------------
# TAB 2: VISUAL TRENDS & CHARTS
# ------------------------------------------------------------------------------
with tab_trends:
    st.markdown("### 📊 My Health Measurement Trends")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        f_start = st.date_input("From Date:", value=date(2026, 1, 1), key="pat_f_start")
    with col_f2:
        f_end = st.date_input("To Date:", value=date.today(), key="pat_f_end")

    if f_start > f_end:
        st.warning("⚠️ 'From Date' cannot be later than 'To Date'. Please adjust.")

    records = get_health_records(
        patient_id=patient_id,
        start_date=f_start.isoformat(),
        end_date=f_end.isoformat()
    )

    if records:
        df = pd.DataFrame(records)
        df['recording_date'] = pd.to_datetime(df['recording_date'])
        df = df.sort_values('recording_date')

        # Chart 1: Blood Pressure Trend
        fig_bp = go.Figure()
        fig_bp.add_trace(go.Scatter(
            x=df['recording_date'],
            y=df['systolic_bp'],
            mode='lines+markers',
            name='Systolic (mmHg)',
            line=dict(color='#E45B65', width=3),
            marker=dict(size=8, color='#E45B65')
        ))
        fig_bp.add_trace(go.Scatter(
            x=df['recording_date'],
            y=df['diastolic_bp'],
            mode='lines+markers',
            name='Diastolic (mmHg)',
            line=dict(color='#3498DB', width=3),
            marker=dict(size=8, color='#3498DB')
        ))
        fig_bp.add_hline(y=120, line_dash="dash", line_color="#20A779", annotation_text="Standard Normal Systolic (120)", annotation_position="top right")
        fig_bp.add_hline(y=80, line_dash="dash", line_color="#3498DB", annotation_text="Standard Normal Diastolic (80)", annotation_position="bottom right")
        fig_bp = style_plotly_fig(fig_bp, title="Blood Pressure Trajectory (Systolic vs Diastolic)", height=320)
        st.plotly_chart(fig_bp, use_container_width=True)

        # Chart 2: Blood Glucose Trend
        fig_glu = go.Figure()
        fig_glu.add_trace(go.Scatter(
            x=df['recording_date'],
            y=df['blood_glucose'],
            mode='lines+markers',
            name='Glucose (mg/dL)',
            line=dict(color='#087F8C', width=3),
            marker=dict(size=8, color='#087F8C')
        ))
        fig_glu.add_hline(y=100, line_dash="dash", line_color="#20A779", annotation_text="Fasting Normal Upper Bound (100)", annotation_position="top right")
        fig_glu = style_plotly_fig(fig_glu, title="Blood Glucose Trajectory", height=300)
        st.plotly_chart(fig_glu, use_container_width=True)

        # Chart 3: BMI & Weight Trend
        fig_bmi = go.Figure()
        fig_bmi.add_trace(go.Scatter(
            x=df['recording_date'],
            y=df['bmi'],
            mode='lines+markers',
            name='BMI (kg/m²)',
            line=dict(color='#8064D8', width=3),
            marker=dict(size=8, color='#8064D8')
        ))
        fig_bmi = style_plotly_fig(fig_bmi, title="Body Mass Index (BMI) Trajectory", height=300)
        st.plotly_chart(fig_bmi, use_container_width=True)
    else:
        st.info("No biometric records found within the selected date range.")

# ------------------------------------------------------------------------------
# TAB 3: VITALS HISTORY LOG
# ------------------------------------------------------------------------------
with tab_history:
    st.markdown("### 📜 Recorded Vitals History")
    all_recs = get_health_records(patient_id=patient_id)

    if all_recs:
        for r in all_recs:
            with st.container():
                bp_info = get_bp_classification(r['systolic_bp'], r['diastolic_bp'])
                bmi_cat = get_bmi_category(r['bmi'])
                
                st.markdown(
                    f"""
                    <div class="saas-metric-card card-teal" style="margin-bottom:12px; padding:16px 20px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <span style="font-weight:800; font-size:1.15rem; color:#243447;">📅 {r['recording_date']}</span>
                                <span style="color:#64748B; font-size:0.86rem; margin-left:12px;">Pulse: <strong>{r['heart_rate']} BPM</strong></span>
                            </div>
                            <div style="display:flex; gap:8px;">
                                <span class="badge-pill {bmi_cat['badge']}">BMI: {r['bmi']} ({bmi_cat['category']})</span>
                                <span class="badge-pill info">BP: {r['systolic_bp']}/{r['diastolic_bp']} mmHg</span>
                            </div>
                        </div>
                        <p style="color:#243447; font-size:0.92rem; margin:8px 0 0 0;">
                            Glucose: <strong>{r['blood_glucose']} mg/dL</strong> ({r['glucose_context']}) • Weight: <strong>{r['weight_kg']} kg</strong> (Height: {r['height_cm']} cm)
                        </p>
                        {f'<p style="color:#64748B; font-size:0.86rem; margin:4px 0 0 0;">Notes: {r["notes"]}</p>' if r["notes"] else ''}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                if st.button("🗑️ Delete This Record", key=f"del_rec_{r['id']}", type="secondary"):
                    delete_health_record(r['id'], patient_id=patient_id)
                    st.success("Record deleted successfully.")
                    st.rerun()

                st.markdown("<hr style='border:none; border-top:1.5px solid #E2E8F0; margin:14px 0;'>", unsafe_allow_html=True)
    else:
        st.info("No vitals recorded yet. Use the **Log New Vitals** tab to record your first measurements.")
