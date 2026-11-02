"""
SmartCare AI – Patient Portal: My Medical Reports.
Upload PDF lab reports, view extracted text, analyze findings with Google Gemini,
and manage digital medical records with strict data privacy.
Server-side Gemini configuration (no client-side API key inputs).
"""

import os
import streamlit as st
import pandas as pd

from services.auth_service import require_auth
from services.pdf_service import (
    validate_pdf_upload,
    extract_text_from_pdf,
    save_pdf_to_storage
)
from services.gemini_service import (
    analyze_medical_report,
    analyze_medical_report_stream,
    check_api_key_configured
)
from database.db import (
    add_medical_report,
    get_medical_reports,
    get_report_by_id,
    delete_medical_report,
    log_ai_interaction
)
from utils.helpers import load_css

load_css()
user = require_auth(allowed_roles=["patient"])
patient_id = user["patient_id"]

# Header Hero Banner
st.markdown(
    """
    <div class="portal-header-patient">
        <h1 class="portal-header-title">📁 My Medical Reports & Lab Files</h1>
        <p class="portal-header-subtitle">Securely store digital PDF lab test results, inspect extracted biomedical parameters, and ask Gemini for educational translations.</p>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;">
            <span class="badge-pill info" style="background:#FFFFFF; color:#087F8C; border:none; font-weight:700;">Local PDF Parsing</span>
            <span class="badge-pill purple" style="background:#FFFFFF; color:#8064D8; border:none; font-weight:700;">Encrypted Document Storage</span>
            <span class="badge-pill success" style="background:#FFFFFF; color:#20A779; border:none; font-weight:700;">On-Demand AI Translation</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

tab_upload, tab_view_reports, tab_ai_analysis = st.tabs([
    "📤 Upload New Report",
    "📑 My Saved Reports",
    "🤖 Ask Gemini About a Report"
])

# ------------------------------------------------------------------------------
# TAB 1: UPLOAD NEW PDF REPORT
# ------------------------------------------------------------------------------
with tab_upload:
    st.markdown("### 📤 Upload Digital PDF Medical Report")
    st.caption("Upload clinical lab results, metabolic panels, or pathology summaries (PDF format, max 10 MB).")

    uploaded_pdf = st.file_uploader("Select a PDF Document:", type=["pdf"], key="patient_pdf_uploader")

    if uploaded_pdf is not None:
        valid, msg = validate_pdf_upload(uploaded_pdf)
        if not valid:
            st.error(msg)
        else:
            file_size_kb = round(uploaded_pdf.size / 1024.0, 1)
            st.success(f"✅ Valid PDF file: **{uploaded_pdf.name}** ({file_size_kb} KB)")

            report_type = st.selectbox(
                "Select Report Category *",
                ["Biochemical Lab Panel", "Complete Blood Count (CBC)", "Lipid Profile", "Liver/Renal Function", "Imaging Summary", "Other Diagnostic Report"]
            )
            report_notes = st.text_input("Personal Notes (Optional):", placeholder="e.g. Annual routine test at City Lab...")

            # Local Text Extraction (cached in session_state per uploaded file to avoid repeated extraction)
            pdf_cache_key = f"pdf_extract_{uploaded_pdf.name}_{uploaded_pdf.size}"
            if pdf_cache_key in st.session_state:
                extract_ok, extracted_content, page_count = st.session_state[pdf_cache_key]
            else:
                with st.spinner("Extracting digital text locally using pypdf..."):
                    extract_ok, extracted_content, page_count = extract_text_from_pdf(uploaded_pdf)
                st.session_state[pdf_cache_key] = (extract_ok, extracted_content, page_count)

            has_usable_text = extract_ok and len(extracted_content.strip()) >= 20

            if extract_ok and has_usable_text:
                st.info(f"📄 Successfully extracted digital text from **{page_count} page(s)** ({len(extracted_content)} characters).")
                with st.expander("🔍 Click to Preview Extracted Report Text", expanded=False):
                    st.text_area("Extracted Content:", value=extracted_content, height=220, disabled=True)
            elif extract_ok and not has_usable_text:
                st.warning(
                    "⚠️ **Scanned or Empty Document Detected**\n\n"
                    "The uploaded PDF contains little or no extractable digital text. It appears to be an image-only scan or empty document.\n\n"
                    "You may still save the file to your profile for records keeping, but AI text analysis requires digital text."
                )

            if st.button("💾 Save Report to My Profile", type="primary", use_container_width=True):
                # Save PDF file to storage
                save_ok, path_or_err, saved_size = save_pdf_to_storage(uploaded_pdf, patient_id)
                if save_ok:
                    rep_id = add_medical_report(
                        patient_id=patient_id,
                        report_name=uploaded_pdf.name,
                        file_path=path_or_err,
                        file_size_kb=saved_size,
                        extracted_text=extracted_content if has_usable_text else "Scanned / Image-only PDF (no digital text)",
                        report_type=report_type,
                        uploaded_by_user_id=user["id"],
                        notes=report_notes
                    )
                    st.success(f"🎉 Report **{uploaded_pdf.name}** has been saved to your personal records! (Report ID #{rep_id})")
                    st.rerun()
                else:
                    st.error(f"Failed to save file: {path_or_err}")

# ------------------------------------------------------------------------------
# TAB 2: MY SAVED REPORTS
# ------------------------------------------------------------------------------
with tab_view_reports:
    st.markdown("### 📑 My Saved Medical Reports")
    my_reports = get_medical_reports(patient_id=patient_id)

    if my_reports:
        for rep in my_reports:
            with st.container():
                st.markdown(
                    f"""
                    <div class="saas-metric-card card-purple" style="margin-bottom:14px; padding:18px 22px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <h4 style="color:#243447; margin:0; font-size:1.15rem;">📄 {rep['report_name']}</h4>
                            <span class="badge-pill purple">{rep['report_type']}</span>
                        </div>
                        <p style="color:#64748B; font-size:0.86rem; margin:6px 0 10px 0;">
                            <strong>Uploaded:</strong> {rep['upload_date'][:16]} • 
                            <strong>File Size:</strong> {rep['file_size_kb']} KB • 
                            <strong>Report ID:</strong> #{rep['id']}
                        </p>
                        <p style="color:#243447; font-size:0.92rem; margin:0;">
                            <strong>Notes:</strong> {rep['notes'] or 'None recorded'}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                col_a1, col_a2, col_a3 = st.columns([1.5, 1.5, 1])
                with col_a1:
                    with st.expander(f"👁️ Read Text Preview (#{rep['id']})"):
                        st.text_area("Extracted Report Text:", value=rep["extracted_text"][:2500], height=200, disabled=True, key=f"prev_{rep['id']}")
                with col_a2:
                    if rep["file_path"] and os.path.exists(rep["file_path"]):
                        with open(rep["file_path"], "rb") as f_down:
                            st.download_button(
                                label="📥 Download PDF",
                                data=f_down.read(),
                                file_name=rep["report_name"],
                                mime="application/pdf",
                                key=f"down_{rep['id']}",
                                use_container_width=True
                            )
                with col_a3:
                    if st.button("🗑️ Remove", key=f"del_rep_{rep['id']}", type="secondary", use_container_width=True):
                        delete_medical_report(rep["id"], patient_id=patient_id)
                        st.success(f"Report '{rep['report_name']}' removed.")
                        st.rerun()

                st.markdown("<hr style='border:none; border-top:1.5px solid #E2E8F0; margin:16px 0;'>", unsafe_allow_html=True)
    else:
        st.info("You haven't saved any medical reports yet. Upload your first PDF in the **Upload New Report** tab!")

# ------------------------------------------------------------------------------
# TAB 3: ASK GEMINI ABOUT A REPORT (EXPLICIT USER-SUBMITTED ANALYSIS ONLY)
# ------------------------------------------------------------------------------
with tab_ai_analysis:
    st.markdown("### 🤖 Ask Gemini About Your Uploaded Report")
    st.caption("Translate complex laboratory numbers into plain English, highlight out-of-range screening values, and prepare doctor questions.")

    if not my_reports:
        st.warning("Please upload a medical report first to enable AI analysis.")
    else:
        rep_dict = {f"#{r['id']} - {r['report_name']} ({r['upload_date'][:10]})": r['id'] for r in my_reports}
        sel_rep_key = st.selectbox("Select Report to Analyze:", list(rep_dict.keys()), key="pt_rep_sel_box")
        selected_rep = get_report_by_id(rep_dict[sel_rep_key])

        # Check if selected report has extractable text
        rep_text = selected_rep.get("extracted_text", "").strip()
        is_scanned_or_empty = not rep_text or "scanned" in rep_text.lower() or len(rep_text) < 20

        if is_scanned_or_empty:
            st.warning(
                "⚠️ **This report does not contain extractable digital text.**\n\n"
                "The file appears to be a scanned image or photo without embedded digital characters. "
                "SmartCare AI analyzes text documents; image scans cannot be processed. Please upload a digital PDF."
            )
        else:
            # Privacy & Consent Notice
            st.markdown(
                """
                <div class="chat-banner" style="border-left-color: #087F8C;">
                    🔒 <strong>Privacy & Consent Notice:</strong> This document's extracted text is transmitted to Google Gemini 
                    <strong>only after you explicitly submit a question</strong> below. SmartCare AI never automatically transmits reports without your command.
                </div>
                """,
                unsafe_allow_html=True
            )

            # Session state management for report inquiry
            if "report_analysis_query" not in st.session_state:
                st.session_state["report_analysis_query"] = ""

            st.markdown("##### 💡 Suggested Directives (Click to Auto-Fill):")
            q_col1, q_col2, q_col3 = st.columns(3)
            with q_col1:
                if st.button("📊 Explain in Simple English", use_container_width=True, key="btn_q1"):
                    st.session_state["report_analysis_query"] = "Explain this medical report in simple, reassuring English. What tests were performed?"
                    st.rerun()
            with q_col2:
                if st.button("⚠️ Check Out-of-Range Markers", use_container_width=True, key="btn_q2"):
                    st.session_state["report_analysis_query"] = "Which laboratory markers are outside standard reference ranges, and what do those tests measure?"
                    st.rerun()
            with q_col3:
                if st.button("🩺 Questions for My Doctor", use_container_width=True, key="btn_q3"):
                    st.session_state["report_analysis_query"] = "What are 3 thoughtful questions I should ask my physician about these test results?"
                    st.rerun()

            custom_q = st.text_input(
                "Your inquiry about this report:",
                value=st.session_state.get("report_analysis_query", ""),
                placeholder="e.g. Explain fasting blood glucose and lipid values...",
                key="rep_analysis_input"
            )

            if st.button("🚀 Analyze Report with Gemini AI", type="primary", use_container_width=True, key="submit_rep_ai"):
                if not custom_q.strip():
                    st.error("Please enter or select a question to analyze this report.")
                else:
                    with st.spinner("Analyzing report with Gemini AI..."):
                        ok_rep, ai_res = analyze_medical_report(
                            report_text=rep_text,
                            user_query=custom_q.strip(),
                            user_role="patient"
                        )
                    if ok_rep and ai_res:
                        st.session_state["last_report_analysis"] = {
                            "report_id": selected_rep["id"],
                            "report_name": selected_rep["report_name"],
                            "query": custom_q.strip(),
                            "success": True,
                            "response": ai_res
                        }
                        log_ai_interaction("Patient Report Q&A", user_id=user["id"])
                    else:
                        st.session_state["last_report_analysis"] = {
                            "report_id": selected_rep["id"],
                            "report_name": selected_rep["report_name"],
                            "query": custom_q.strip(),
                            "success": False,
                            "response": ai_res or "Could not generate analysis from this document. Please verify the report text."
                        }

            # Display Analysis Result if available in session state
            saved_analysis = st.session_state.get("last_report_analysis")
            if saved_analysis and saved_analysis.get("report_id") == selected_rep["id"]:
                if saved_analysis["success"]:
                    st.markdown(
                        f"""
                        <div class="banner-success" style="margin: 18px 0 10px 0;">
                            <h4 style="color: #0D5E43; margin: 0 0 4px 0;">🌿 AI Educational Insights: {saved_analysis['report_name']}</h4>
                            <p style="color: #16845F; margin: 0; font-size: 0.88rem;">Inquiry: "<em>{saved_analysis['query']}</em>"</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    st.markdown(saved_analysis["response"])
                else:
                    st.error(saved_analysis["response"])
