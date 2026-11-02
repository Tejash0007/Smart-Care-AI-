"""
SmartCare AI – Healthcare Provider Portal: AI Clinical Support.
Generative AI decision-support module powered by Google Gemini.
Summarizes diagnostic reports, identifies out-of-range markers, and organizes clinical findings.
Centralized server-side configuration via .env.
"""

import streamlit as st
from services.auth_service import require_auth
from services.gemini_service import (
    analyze_medical_report,
    analyze_medical_report_stream,
    check_api_key_configured,
    get_model_name
)
from database.db import (
    get_patients_for_provider,
    get_medical_reports,
    get_report_by_id,
    log_ai_interaction
)
from utils.helpers import load_css

load_css()
user = require_auth(allowed_roles=["provider"])
provider_id = user.get("provider_id", "DOC-101")

# Header Hero Banner
st.markdown(
    """
    <div class="portal-header-provider">
        <h1 class="portal-header-title">🩺 AI-Assisted Clinical Decision Support</h1>
        <p class="portal-header-subtitle">Rapid report summarization, laboratory anomaly highlighting, and structured findings organization via Google Gemini.</p>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;">
            <span class="badge-pill info" style="background:#FFFFFF; color:#243447; border:none; font-weight:700;">Multi-Modal Document Intelligence</span>
            <span class="badge-pill purple" style="background:#FFFFFF; color:#8064D8; border:none; font-weight:700;">Anomaly Highlighting</span>
            <span class="badge-pill success" style="background:#FFFFFF; color:#20A779; border:none; font-weight:700;">Physician-Supervised AI</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Mandatory Clinical Responsibility Notice
st.markdown(
    """
    <div class="clinical-disclaimer">
        ⚖️ <strong>Physician Responsibility Disclaimer:</strong> This decision support tool is powered by Generative AI for 
        informational and synthesis assistance. It does <strong>not</strong> substitute for professional medical judgment, 
        clinical diagnosis, or official laboratory verification. The attending healthcare provider retains sole clinical responsibility for patient care.
    </div>
    """,
    unsafe_allow_html=True
)

patients = get_patients_for_provider(provider_id)
if not patients:
    st.warning("No authorized patients available under your clinical purview.")
    st.stop()

# 1. Select Patient
pt_map = {f"{p['patient_id']} - {p['name']}": p['patient_id'] for p in patients}
selected_pt = st.selectbox("1. Select Patient:", list(pt_map.keys()), key="doc_ai_pt_sel")
pid = pt_map[selected_pt]

# 2. Select Report
reports = get_medical_reports(patient_id=pid, provider_id=provider_id)
if not reports:
    st.info(f"No diagnostic reports currently on file for patient {selected_pt}.")
    st.stop()

rep_map = {f"#{r['id']} - {r['report_name']} ({r['upload_date'][:10]})": r['id'] for r in reports}
selected_rep_label = st.selectbox("2. Select Medical Report to Analyze:", list(rep_map.keys()), key="doc_ai_rep_sel")
report = get_report_by_id(rep_map[selected_rep_label])

rep_text = report.get("extracted_text", "").strip()
is_empty = not rep_text or "scanned" in rep_text.lower() or len(rep_text) < 20

if is_empty:
    st.warning("⚠️ This report contains no digital extractable text. Scanned images cannot be analyzed by text-based AI models.")
    st.stop()

with st.expander("📄 View Extracted Document Content"):
    st.text_area("Extracted Text:", value=rep_text[:3500], height=200, disabled=True)

st.markdown("### 🤖 Clinical Analysis Directives")

if "doc_analysis_query" not in st.session_state:
    st.session_state["doc_analysis_query"] = ""

c_col1, c_col2, c_col3 = st.columns(3)
with c_col1:
    if st.button("📋 Comprehensive Clinical Synthesis", use_container_width=True, key="doc_dir_1"):
        st.session_state["doc_analysis_query"] = "Provide a comprehensive clinical synthesis of this report: key findings, normal vs abnormal markers, and potential lifestyle associations."
        st.rerun()
with c_col2:
    if st.button("⚠️ Highlight Out-of-Range Markers", use_container_width=True, key="doc_dir_2"):
        st.session_state["doc_analysis_query"] = "Highlight all laboratory values outside standard reference ranges with their stated units, and specify potential physiological significance."
        st.rerun()
with c_col3:
    if st.button("❓ Patient History Follow-Up Questions", use_container_width=True, key="doc_dir_3"):
        st.session_state["doc_analysis_query"] = "Suggest 3-4 structured follow-up questions the physician should explore with the patient regarding these diagnostic findings."
        st.rerun()

clinical_query = st.text_input(
    "Or type specific clinical query:",
    value=st.session_state.get("doc_analysis_query", ""),
    placeholder="e.g. Analyze liver enzymes and lipid parameters in this panel...",
    key="doc_clinical_input"
)

if st.button("Generate AI Clinical Insights", type="primary", use_container_width=True, key="doc_submit_ai"):
    if not clinical_query.strip():
        st.error("Please enter or select a clinical directive.")
    else:
        with st.spinner("Analyzing diagnostic document with Gemini AI..."):
            ok_doc, response_text = analyze_medical_report(
                report_text=rep_text,
                user_query=clinical_query.strip(),
                user_role="provider"
            )
        if ok_doc and response_text:
            st.session_state["last_doc_analysis"] = {
                "report_id": report["id"],
                "query": clinical_query.strip(),
                "success": True,
                "response": response_text
            }
            log_ai_interaction("Provider Clinical Decision Support", user_id=user["id"])
        else:
            st.session_state["last_doc_analysis"] = {
                "report_id": report["id"],
                "query": clinical_query.strip(),
                "success": False,
                "response": response_text or "Could not generate clinical synthesis from document."
            }

# Display result if present in session state
last_doc = st.session_state.get("last_doc_analysis")
if last_doc and last_doc.get("report_id") == report["id"]:
    if last_doc["success"]:
        st.markdown(
            f"""
            <div class="banner-info" style="margin: 18px 0 10px 0;">
                <h4 style="color:#185587; margin:0 0 4px 0;">🩺 Gemini Clinical Decision Support Findings</h4>
                <p style="color:#1D72B8; margin:0; font-size:0.88rem;">Directive: "<em>{last_doc['query']}</em>"</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(last_doc["response"])
    else:
        st.error(last_doc["response"])
