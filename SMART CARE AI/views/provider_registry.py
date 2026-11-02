"""
SmartCare AI – Healthcare Provider Portal: Patient Registry.
Search and view authorized patient records, edit demographics, inspect profiles,
and permanently delete patient records with complete cascade cleanup.
"""

import streamlit as st
import pandas as pd

from services.auth_service import require_auth
from database.db import (
    get_patients_for_provider,
    get_patient_by_id,
    search_patients,
    update_patient,
    delete_patient,
    get_health_records,
    get_medical_reports
)
from utils.helpers import load_css

load_css()
user = require_auth(allowed_roles=["provider"])
provider_id = user.get("provider_id", "DOC-101")

# Header Hero Banner
st.markdown(
    """
    <div class="portal-header-provider">
        <h1 class="portal-header-title">👥 Authorized Patient Directory & Registry</h1>
        <p class="portal-header-subtitle">Search, inspect clinical profiles, update patient records, and manage hospital registrations with atomic consistency.</p>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;">
            <span class="badge-pill info" style="background:#FFFFFF; color:#243447; border:none; font-weight:700;">Multi-Parameter Search</span>
            <span class="badge-pill purple" style="background:#FFFFFF; color:#8064D8; border:none; font-weight:700;">Demographic Management</span>
            <span class="badge-pill danger" style="background:#FFFFFF; color:#E45B65; border:none; font-weight:700;">Cascade Purge Safety</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Display Deletion Success Message if flag is present in session state
if "patient_deleted_success_msg" in st.session_state:
    st.success(st.session_state.pop("patient_deleted_success_msg"))

tab_view, tab_edit, tab_delete = st.tabs([
    "📋 Search & View Patients",
    "✏️ Edit Patient Details",
    "🗑️ Permanent Patient Deletion"
])

# ------------------------------------------------------------------------------
# TAB 1: SEARCH & VIEW PATIENTS
# ------------------------------------------------------------------------------
with tab_view:
    st.markdown("### 🔍 Patient Directory")
    
    col_s1, col_s2 = st.columns([4, 1])
    with col_s1:
        s_query = st.text_input("Search by Name, Patient ID, or Phone:", placeholder="e.g. SC-1001 or Aarav...", key="doc_search_input")
    with col_s2:
        if st.button("🔄 Refresh Directory", use_container_width=True):
            st.rerun()

    if s_query.strip():
        patient_list = search_patients(s_query, provider_id=provider_id)
        st.info(f"Showing {len(patient_list)} result(s) matching '{s_query}'.")
    else:
        patient_list = get_patients_for_provider(provider_id)

    if patient_list:
        df_display = pd.DataFrame(patient_list)[[
            "patient_id", "name", "age", "gender", "contact", "blood_group", "registration_date", "notes"
        ]]
        df_display.columns = [
            "Patient ID", "Full Name", "Age", "Gender", "Contact", "Blood Group", "Reg Date", "Clinical Notes"
        ]
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🪪 Detailed Patient Clinical Profile")

        choices = [f"{p['patient_id']} - {p['name']}" for p in patient_list]
        sel_str = st.selectbox("Select Patient to Inspect:", choices, key="doc_inspect_sel")

        if sel_str:
            target_pid = sel_str.split(" - ")[0]
            target_pt = get_patient_by_id(target_pid)

            if target_pt:
                c_p1, c_p2 = st.columns([1.5, 2.5])
                with c_p1:
                    st.markdown(
                        f"""
                        <div class="saas-metric-card card-blue" style="margin-bottom:14px; padding:20px;">
                            <div style="font-size:1.3rem; font-weight:800; color:#243447; margin-bottom:8px;">{target_pt['name']}</div>
                            <p style="margin:4px 0; font-size:0.92rem;"><strong>Patient ID:</strong> <code>{target_pt['patient_id']}</code></p>
                            <p style="margin:4px 0; font-size:0.92rem;"><strong>Demographics:</strong> {target_pt['age']} yrs • {target_pt['gender']}</p>
                            <p style="margin:4px 0; font-size:0.92rem;"><strong>Blood Group:</strong> <span class="badge-pill purple">{target_pt['blood_group']}</span></p>
                            <p style="margin:4px 0; font-size:0.92rem;"><strong>Contact:</strong> {target_pt['contact']}</p>
                            <p style="margin:4px 0; font-size:0.92rem;"><strong>Enrolled:</strong> {target_pt['registration_date']}</p>
                            <div style="margin-top:12px; padding-top:10px; border-top:1.5px solid #D6EAF8; font-size:0.88rem; color:#64748B;">
                                <strong>Clinical Notes:</strong> {target_pt['notes'] or 'None recorded'}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                with c_p2:
                    st.markdown("#### Recent Biometric Measurements")
                    pt_recs = get_health_records(patient_id=target_pid)
                    if pt_recs:
                        df_recs = pd.DataFrame(pt_recs)[[
                            "recording_date", "weight_kg", "height_cm", "bmi", "systolic_bp", "diastolic_bp", "blood_glucose", "heart_rate"
                        ]]
                        df_recs.columns = ["Date", "Weight(kg)", "Height(cm)", "BMI", "Systolic", "Diastolic", "Glucose", "Pulse"]
                        st.dataframe(df_recs, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No biometric measurements logged yet for this patient.")

                    st.markdown("#### Uploaded Diagnostic Reports")
                    pt_reps = get_medical_reports(patient_id=target_pid)
                    if pt_reps:
                        df_reps = pd.DataFrame(pt_reps)[["report_name", "report_type", "upload_date", "file_size_kb"]]
                        df_reps.columns = ["Report Name", "Type", "Upload Date", "Size (KB)"]
                        st.dataframe(df_reps, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No lab reports on file for this patient.")
    else:
        st.warning("No authorized patients found matching the criteria.")

# ------------------------------------------------------------------------------
# TAB 2: EDIT PATIENT DETAILS
# ------------------------------------------------------------------------------
with tab_edit:
    st.markdown("### ✏️ Edit Patient Demographic Record")

    all_authorized = get_patients_for_provider(provider_id)
    if not all_authorized:
        st.warning("No patients currently available to edit.")
    else:
        edit_choices = [f"{p['patient_id']} - {p['name']}" for p in all_authorized]
        selected_edit_str = st.selectbox("Select Patient to Edit:", edit_choices, key="doc_edit_sel")
        edit_pid = selected_edit_str.split(" - ")[0]
        curr_pt = get_patient_by_id(edit_pid)

        if curr_pt:
            with st.form("edit_patient_form"):
                e_name = st.text_input("Full Legal Name *", value=curr_pt["name"])
                
                ec1, ec2 = st.columns(2)
                with ec1:
                    e_age = st.number_input("Age in Years *", min_value=1, max_value=120, value=int(curr_pt["age"]))
                    g_opts = ["Male", "Female", "Other"]
                    g_i = g_opts.index(curr_pt["gender"]) if curr_pt["gender"] in g_opts else 0
                    e_gender = st.selectbox("Gender *", g_opts, index=g_i)
                with ec2:
                    e_contact = st.text_input("Primary Contact Phone *", value=curr_pt["contact"])
                    b_opts = ["Unknown", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
                    b_i = b_opts.index(curr_pt["blood_group"]) if curr_pt["blood_group"] in b_opts else 0
                    e_blood = st.selectbox("Blood Group", b_opts, index=b_i)

                e_notes = st.text_area("Clinical Notes & Medical History", value=curr_pt["notes"] or "")

                save_btn = st.form_submit_button("Save Patient Changes", type="primary", use_container_width=True)

                if save_btn:
                    from utils.validators import validate_name, validate_mobile
                    v_name, err_name, clean_name = validate_name(e_name, "Patient Legal Name")
                    v_mob, err_mob, norm_contact = validate_mobile(e_contact, required=True)

                    if not v_name:
                        st.error(err_name)
                    elif not v_mob:
                        st.error(err_mob)
                    else:
                        try:
                            ok = update_patient(
                                patient_id=edit_pid,
                                name=clean_name,
                                age=e_age,
                                gender=e_gender,
                                contact=norm_contact,
                                blood_group=e_blood,
                                notes=e_notes
                            )
                            if ok:
                                st.success(f"Patient {edit_pid} updated successfully!")
                                st.rerun()
                            else:
                                st.error("Update failed.")
                        except ValueError as v_err:
                            st.error(str(v_err))

# ------------------------------------------------------------------------------
# TAB 3: PERMANENT PATIENT DELETION (PERMANENT FIX FOR DELETION BUG)
# ------------------------------------------------------------------------------
with tab_delete:
    st.markdown("### 🗑️ Permanent Patient Deletion")
    st.markdown(
        """
        <div class="banner-alert" style="margin-bottom:18px;">
            <h4 style="color:#8B1E26; margin:0 0 6px 0;">⚠️ Irreversible Clinical Action</h4>
            <p style="color:#C9323D; margin:0; font-size:0.92rem;">
                Deleting a patient permanently purges their hospital registration record, all associated biometric health vitals,
                all uploaded PDF diagnostic reports, and provider permissions in a single atomic transaction.
                <strong>This action cannot be undone.</strong>
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    all_for_del = get_patients_for_provider(provider_id)
    if not all_for_del:
        st.info("No patient records available for deletion.")
    else:
        del_choices = [f"{p['patient_id']} - {p['name']}" for p in all_for_del]
        sel_del_str = st.selectbox("Select Patient to Permanently Delete:", del_choices, key="doc_del_sel")
        del_pid = sel_del_str.split(" - ")[0]
        patient_to_delete = get_patient_by_id(del_pid)

        if patient_to_delete:
            st.markdown(f"**Target Patient:** `{patient_to_delete['patient_id']}` — **{patient_to_delete['name']}** (Registered: {patient_to_delete['registration_date']})")
            
            # Double Confirmation Checkbox
            confirm_box = st.checkbox(
                f"I verify and confirm permanent deletion of patient **{patient_to_delete['name']} ({patient_to_delete['patient_id']})** and all associated clinical vitals and lab reports.",
                key=f"confirm_del_{patient_to_delete['patient_id']}"
            )

            if st.button("Permanently Delete Patient Record", type="secondary", disabled=not confirm_box):
                # Execute deletion in SQLite
                deleted = delete_patient(del_pid)
                if deleted:
                    st.session_state["patient_deleted_success_msg"] = f"✅ Patient {patient_to_delete['name']} ({del_pid}) has been permanently deleted from SQLite database."
                    st.rerun()
                else:
                    st.error("Deletion operation encountered a database error.")
