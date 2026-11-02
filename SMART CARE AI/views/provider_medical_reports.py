"""
SmartCare AI – Healthcare Provider Portal: Medical Reports Management.
Review diagnostic reports uploaded by authorized patients,
inspect extracted digital findings, download files, and initiate AI clinical summaries.
"""

import os
import streamlit as st
import pandas as pd

from services.auth_service import require_auth
from database.db import (
    get_patients_for_provider,
    get_medical_reports,
    get_report_by_id
)
from utils.helpers import load_css

load_css()
user = require_auth(allowed_roles=["provider"])
provider_id = user.get("provider_id", "DOC-101")

# Header Banner
st.markdown(
    """
    <div class="portal-header-provider">
        <h1 class="portal-header-title">📑 Diagnostic Medical Reports</h1>
        <p class="portal-header-subtitle">Review patient diagnostic panels, inspect extracted text data, and perform clinical investigations.</p>
    </div>
    """,
    unsafe_allow_html=True
)

patients = get_patients_for_provider(provider_id)
if not patients:
    st.warning("No patients currently authorized.")
    st.stop()

# Filter by Patient option
pt_options = {"All Authorized Patients": None}
for p in patients:
    pt_options[f"{p['patient_id']} - {p['name']}"] = p['patient_id']

selected_pt_label = st.selectbox("Filter Reports by Patient:", list(pt_options.keys()), key="doc_filter_pt")
filtered_pid = pt_options[selected_pt_label]

reports = get_medical_reports(patient_id=filtered_pid, provider_id=provider_id)

if reports:
    st.markdown(f"### Showing {len(reports)} Report(s) on File")
    
    for rep in reports:
        with st.container():
            st.markdown(
                f"""
                <div class="saas-metric-card card-purple" style="margin-bottom:14px; padding:18px 22px;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div>
                            <div style="font-weight:700; color:#243447; font-size:1.15rem; margin-bottom:4px;">📄 {rep['report_name']}</div>
                            <p style="color:#64748B; font-size:0.88rem; margin:0 0 6px 0;">
                                Patient: <strong>{rep['patient_name']}</strong> (<code>{rep['patient_id']}</code>) • 
                                Date: {rep['upload_date'][:16]} • 
                                Size: {rep['file_size_kb']} KB
                            </p>
                            <p style="color:#243447; font-size:0.88rem; margin:0;">
                                <strong>Clinical Remarks:</strong> {rep['notes'] or 'None recorded'}
                            </p>
                        </div>
                        <span class="badge-pill purple">{rep['report_type']}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

            col1, col2 = st.columns([3, 1])
            with col1:
                with st.expander(f"🔍 Inspect Extracted Text for #{rep['id']}"):
                    st.text_area("Extracted Report Content:", value=rep["extracted_text"][:3500], height=240, disabled=True, key=f"doc_exp_{rep['id']}")
            with col2:
                if rep["file_path"] and os.path.exists(rep["file_path"]):
                    with open(rep["file_path"], "rb") as f_down:
                        st.download_button(
                            label="📥 Download PDF",
                            data=f_down.read(),
                            file_name=rep["report_name"],
                            mime="application/pdf",
                            key=f"doc_down_{rep['id']}",
                            use_container_width=True
                        )

            st.markdown("<hr style='border:none; border-top:1.5px solid #E2E8F0; margin:16px 0;'>", unsafe_allow_html=True)
else:
    st.info("No medical reports found for the selected patient.")
