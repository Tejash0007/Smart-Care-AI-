"""
SmartCare AI – Patient Portal: My Health History.
Displays consolidated chronological medical history across vitals and reports,
with date filters and 1-click PDF clinical report generation.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date

from services.auth_service import require_auth
from database.db import (
    get_patient_by_id,
    get_health_records,
    get_medical_reports
)
from utils.helpers import (
    load_css,
    generate_pdf_report,
    get_bmi_category,
    get_bp_classification,
    get_glucose_classification,
    get_heart_rate_classification
)

load_css()
user = require_auth(allowed_roles=["patient"])
patient_id = user["patient_id"]
patient = get_patient_by_id(patient_id)
records = get_health_records(patient_id=patient_id)
reports = get_medical_reports(patient_id=patient_id)

# Header Hero Banner
st.markdown(
    """
    <div class="portal-header-patient">
        <h1 class="portal-header-title">📜 My Comprehensive Health History</h1>
        <p class="portal-header-subtitle">Chronological timeline of all recorded vitals, medical test reports, and downloadable PDF clinical summaries.</p>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;">
            <span class="badge-pill info" style="background:#FFFFFF; color:#087F8C; border:none; font-weight:700;">Unified Longitudinal Timeline</span>
            <span class="badge-pill purple" style="background:#FFFFFF; color:#8064D8; border:none; font-weight:700;">Diagnostic Lab Archives</span>
            <span class="badge-pill success" style="background:#FFFFFF; color:#20A779; border:none; font-weight:700;">1-Click ReportLab Export</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Actions Bar: PDF Export
col_top_info, col_top_pdf = st.columns([3, 1])
with col_top_info:
    st.markdown(f"#### Profile Record: **{patient['name']}** (`{patient['patient_id']}`)")
    st.caption(f"Member since: {patient['registration_date']} • Blood Group: **{patient['blood_group']}** • Contact: {patient['contact']}")
with col_top_pdf:
    try:
        pdf_bytes = generate_pdf_report(patient, records)
        fname = f"SmartCare_History_{patient_id}_{datetime.now().strftime('%Y%m%d')}.pdf"
        st.download_button(
            label="📥 Download Full PDF Summary",
            data=pdf_bytes,
            file_name=fname,
            mime="application/pdf",
            type="primary",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"PDF note: {e}")

st.markdown("<hr style='border:none; border-top:1.5px solid #E2E8F0; margin:16px 0;'>", unsafe_allow_html=True)

tab_timeline, tab_table_view = st.tabs(["🕒 Unified Health Timeline", "📊 Tabular Records View"])

with tab_timeline:
    st.markdown("### 🕒 Chronological Health Events")
    
    # Build combined timeline items
    timeline_items = []
    for r in records:
        bp_c = get_bp_classification(r["systolic_bp"], r["diastolic_bp"])
        bmi_c = get_bmi_category(r["bmi"])
        timeline_items.append({
            "date": r["recording_date"],
            "type": "Biometric Measurement",
            "title": f"💓 Vitals Log: BP {r['systolic_bp']}/{r['diastolic_bp']} mmHg • Pulse {r['heart_rate']} BPM",
            "details": f"Glucose: {r['blood_glucose']} mg/dL ({r['glucose_context']}) | BMI: {r['bmi']} kg/m² ({bmi_c['category']}) | Weight: {r['weight_kg']} kg",
            "notes": r["notes"],
            "card_class": "card-blue",
            "badge_class": "info",
            "badge_label": "Biometrics"
        })

    for rep in reports:
        timeline_items.append({
            "date": rep["upload_date"][:10],
            "type": "Medical Lab Report",
            "title": f"📑 Report Upload: {rep['report_name']}",
            "details": f"Category: {rep['report_type']} | File Size: {rep['file_size_kb']} KB",
            "notes": rep["notes"],
            "card_class": "card-purple",
            "badge_class": "purple",
            "badge_label": "Lab Report"
        })

    # Sort descending by date
    timeline_items.sort(key=lambda x: x["date"], reverse=True)

    if timeline_items:
        for item in timeline_items:
            st.markdown(
                f"""
                <div class="saas-metric-card {item['card_class']}" style="margin-bottom:12px; padding:16px 20px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#243447; font-size:1.02rem;">{item['title']}</span>
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span class="badge-pill {item['badge_class']}">{item['badge_label']}</span>
                            <span style="font-size:0.82rem; color:#64748B; font-weight:600;">{item['date']}</span>
                        </div>
                    </div>
                    <div style="color:#243447; font-size:0.9rem; margin-top:6px; font-weight:500;">
                        {item['details']}
                    </div>
                    {f'<div style="color:#64748B; font-size:0.84rem; margin-top:4px; font-style:italic;">Notes: {item["notes"]}</div>' if item["notes"] else ''}
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("No timeline events logged yet. Record vitals or upload lab reports to populate your medical history.")

with tab_table_view:
    st.markdown("### 📋 Tabular Vitals & Biometrics")
    if records:
        df_rec = pd.DataFrame(records)[[
            "recording_date", "weight_kg", "height_cm", "bmi", "systolic_bp",
            "diastolic_bp", "blood_glucose", "glucose_context", "heart_rate", "notes"
        ]]
        df_rec.columns = [
            "Date", "Weight(kg)", "Height(cm)", "BMI", "Systolic", "Diastolic",
            "Glucose(mg/dL)", "Context", "Pulse(BPM)", "Clinical Notes"
        ]
        st.dataframe(df_rec, use_container_width=True, hide_index=True)
    else:
        st.info("No vitals records available.")
