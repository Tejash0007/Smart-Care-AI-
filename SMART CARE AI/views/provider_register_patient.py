"""
SmartCare AI – Healthcare Provider Portal: Register Patient.
Clinical enrollment form for physicians and hospital staff.
Assigns sequential unique patient IDs and grants immediate clinical access.
"""

import streamlit as st
from datetime import date

from services.auth_service import require_auth
from database.db import add_patient
from utils.validators import validate_name, validate_mobile
from utils.helpers import load_css

load_css()
user = require_auth(allowed_roles=["provider"])
provider_id = user.get("provider_id", "DOC-101")

# Header Hero Banner
st.markdown(
    """
    <div class="portal-header-provider">
        <h1 class="portal-header-title">➕ Clinical Patient Registration</h1>
        <p class="portal-header-subtitle">Enroll a new patient into the hospital registry with automated sequential ID sequencing and instant clinical access.</p>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;">
            <span class="badge-pill info" style="background:#FFFFFF; color:#243447; border:none; font-weight:700;">Atomic Database Enrollment</span>
            <span class="badge-pill purple" style="background:#FFFFFF; color:#8064D8; border:none; font-weight:700;">Automatic Provider Authorization</span>
            <span class="badge-pill success" style="background:#FFFFFF; color:#20A779; border:none; font-weight:700;">Sequential ID (SC-XXXX)</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("### 📋 Patient Intake Form")
st.caption(f"Registering Physician / Attending Provider: **{user.get('name', 'Dr. Ramesh Sharma')}** (`{provider_id}`)")

with st.form("clinical_patient_reg_form", clear_on_submit=True):
    c1, c2 = st.columns(2)
    with c1:
        new_name = st.text_input("Patient Full Legal Name *", placeholder="e.g. Meera Joshi")
        new_age = st.number_input("Age in Years *", min_value=1, max_value=120, value=30)
        new_gender = st.selectbox("Biological Sex / Gender *", ["Male", "Female", "Other"])
    with c2:
        new_contact = st.text_input("Primary Contact Phone Number *", placeholder="e.g. +91 98765 11122")
        new_blood = st.selectbox("Blood Group", ["Unknown", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
        new_reg_date = st.date_input("Clinical Registration Date", value=date.today())

    new_notes = st.text_area("Initial Clinical Assessment / Triage Notes (Optional)", placeholder="e.g. Referred for cardiac evaluation, no known drug allergies...")

    submit_enrollment = st.form_submit_button("Complete Hospital Enrollment", type="primary", use_container_width=True)

    if submit_enrollment:
        v_name, err_name, clean_name = validate_name(new_name, "Patient Legal Name")
        v_mob, err_mob, norm_contact = validate_mobile(new_contact, required=True)

        if not v_name:
            st.error(err_name)
        elif not v_mob:
            st.error(err_mob)
        else:
            try:
                assigned_id = add_patient(
                    name=clean_name,
                    age=new_age,
                    gender=new_gender,
                    contact=norm_contact,
                    blood_group=new_blood,
                    registration_date=new_reg_date.isoformat(),
                    notes=new_notes,
                    is_demo=0,
                    created_by_provider_id=provider_id
                )
                st.success(f"🎉 Patient **{clean_name}** successfully enrolled in hospital registry! Assigned Unique Patient ID: **{assigned_id}**")
                st.info("Clinical access permissions have been granted automatically. You can now view this patient in Patient Records or Patient Registry.")
            except ValueError as val_err:
                st.error(str(val_err))
            except Exception as e:
                st.error(f"Failed to enroll patient: {e}")
