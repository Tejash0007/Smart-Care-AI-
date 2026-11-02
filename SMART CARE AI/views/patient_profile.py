"""
SmartCare AI – Patient Portal: My Profile.
View and update personal demographic information, emergency contact details,
manage account security settings, and permanently delete account with re-authentication.
"""

import streamlit as st
from services.auth_service import require_auth, delete_current_patient_account
from database.db import (
    get_patient_by_id,
    update_patient,
    update_user_password,
    verify_password,
    get_user_by_id
)
from utils.validators import validate_name, validate_mobile, validate_password
from utils.helpers import load_css

load_css()
user = require_auth(allowed_roles=["patient"])
patient_id = user["patient_id"]
patient = get_patient_by_id(patient_id)

# Header Hero Banner
st.markdown(
    """
    <div class="portal-header-patient">
        <h1 class="portal-header-title">👤 My Profile & Account Settings</h1>
        <p class="portal-header-subtitle">Manage personal clinical demographics, emergency contact details, credentials, and data retention.</p>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;">
            <span class="badge-pill info" style="background:#FFFFFF; color:#087F8C; border:none; font-weight:700;">Biometric Demographics</span>
            <span class="badge-pill purple" style="background:#FFFFFF; color:#8064D8; border:none; font-weight:700;">Account Confidentiality</span>
            <span class="badge-pill success" style="background:#FFFFFF; color:#20A779; border:none; font-weight:700;">SHA-256 PBKDF2 Password Security</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

if not patient:
    st.error("Patient record could not be loaded. Please re-authenticate.")
    st.stop()

# Patient Card Summary
st.markdown(
    f"""
    <div class="saas-metric-card card-teal" style="margin-bottom: 20px; padding: 18px 22px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="font-size:1.3rem; font-weight:800; color:#243447;">{patient['name']}</div>
                <div style="font-size:0.88rem; color:#64748B; margin-top:2px;">Patient ID: <strong>{patient['patient_id']}</strong> • Enrolled: {patient['registration_date']}</div>
            </div>
            <div style="display:flex; gap:8px;">
                <span class="badge-pill info">Age: {patient['age']}</span>
                <span class="badge-pill purple">Blood: {patient['blood_group']}</span>
                <span class="badge-pill success">{patient['gender']}</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

tab_demographics, tab_security, tab_delete = st.tabs([
    "🪪 Demographic Profile",
    "🔐 Account Security",
    "🗑️ Delete Account"
])

# ------------------------------------------------------------------------------
# TAB 1: DEMOGRAPHIC INFORMATION
# ------------------------------------------------------------------------------
with tab_demographics:
    st.markdown("### 🪪 Personal Demographic Information")
    st.caption("Update your primary contact information and known clinical notes.")

    with st.form("update_profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            up_name = st.text_input("Full Legal Name *", value=patient["name"])
            up_age = st.number_input("Age in Years *", min_value=1, max_value=120, value=int(patient["age"]))
            
            gender_options = ["Male", "Female", "Other"]
            g_idx = gender_options.index(patient["gender"]) if patient["gender"] in gender_options else 0
            up_gender = st.selectbox("Gender *", gender_options, index=g_idx)

        with col2:
            up_contact = st.text_input("Primary Contact Phone (Indian Mobile) *", value=patient["contact"])
            
            blood_options = ["Unknown", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
            b_idx = blood_options.index(patient["blood_group"]) if patient["blood_group"] in blood_options else 0
            up_blood = st.selectbox("Blood Group", blood_options, index=b_idx)

        up_notes = st.text_area("Personal Health Remarks / Known Allergies", value=patient["notes"] or "")

        save_btn = st.form_submit_button("Update Demographic Profile", type="primary", use_container_width=True)

        if save_btn:
            v_name, err_name, clean_name = validate_name(up_name, "Full Legal Name")
            v_mob, err_mob, norm_contact = validate_mobile(up_contact, required=True)

            if not v_name:
                st.error(err_name)
            elif not v_mob:
                st.error(err_mob)
            else:
                try:
                    ok = update_patient(
                        patient_id=patient_id,
                        name=clean_name,
                        age=up_age,
                        gender=up_gender,
                        contact=norm_contact,
                        blood_group=up_blood,
                        notes=up_notes
                    )
                    if ok:
                        # Update session if name changed
                        st.session_state["user"]["name"] = clean_name
                        st.session_state["user"]["contact"] = norm_contact
                        st.session_state["user"]["blood_group"] = up_blood
                        st.session_state["user"]["age"] = up_age
                        st.session_state["user"]["gender"] = up_gender
                        st.success("Your demographic profile has been updated successfully!")
                        st.rerun()
                    else:
                        st.error("Could not update profile in database.")
                except Exception as e:
                    st.error(f"Error updating profile: {e}")

# ------------------------------------------------------------------------------
# TAB 2: ACCOUNT SECURITY
# ------------------------------------------------------------------------------
with tab_security:
    st.markdown("### 🔐 Change Account Password")
    st.caption(f"Account Username: `{user['username']}` • Email: `{user['email']}`")

    with st.form("change_password_form"):
        curr_pass = st.text_input("Current Password *", type="password")
        new_pass = st.text_input("New Password (min 6 characters) *", type="password")
        confirm_pass = st.text_input("Confirm New Password *", type="password")

        pwd_submit = st.form_submit_button("Update Password", type="primary", use_container_width=True)

        if pwd_submit:
            db_user = get_user_by_id(user["id"])

            if not db_user or not verify_password(curr_pass, db_user["password_hash"]):
                st.error("Current password is incorrect.")
            else:
                v_pwd, err_pwd = validate_password(new_pass, confirm_pass)
                if not v_pwd:
                    st.error(err_pwd)
                else:
                    ok = update_user_password(user["id"], new_pass)
                    if ok:
                        st.success("Password updated successfully!")
                    else:
                        st.error("Could not update password.")

# ------------------------------------------------------------------------------
# TAB 3: PERMANENT ACCOUNT DELETION
# ------------------------------------------------------------------------------
with tab_delete:
    st.markdown("### 🗑️ Permanent Patient Account Deletion")
    st.caption("Permanently close your account, purge all personal health telemetry, and delete stored medical reports.")

    st.markdown(
        """
        <div class="banner-alert" style="margin-bottom:20px;">
            <h4 style="color:#A8232F; margin:0 0 8px 0; font-size:1.05rem;">⚠️ Irreversible Action & Complete Clinical Purge:</h4>
            <p style="color:#781A22; font-size:0.92rem; margin:0 0 8px 0; line-height:1.5;">
                When you delete your patient account, SmartCare AI initiates a total cascade purge:
            </p>
            <ul style="color:#781A22; font-size:0.90rem; margin:0; padding-left:20px; line-height:1.6;">
                <li>All biometric vitals, blood pressure trajectories, and glucose records are permanently deleted.</li>
                <li>All uploaded laboratory PDF report files on the server disk and database metadata are destroyed.</li>
                <li>All active healthcare provider permissions and links are revoked.</li>
                <li>Your user account, login credentials, and session are permanently erased.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.form("delete_patient_account_form"):
        confirm_check = st.checkbox(
            "I understand that this action is irreversible and permanently purges all my personal health records from SmartCare AI."
        )
        del_password = st.text_input(
            "Re-enter Your Current Account Password to Authenticate Deletion *",
            type="password",
            placeholder="Enter password"
        )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        del_submit = st.form_submit_button(
            "⚠️ Permanently Delete My Patient Account",
            type="primary",
            use_container_width=True
        )

        if del_submit:
            if not confirm_check:
                st.error("Please confirm that you understand this action is permanent by checking the box above.")
            elif not del_password.strip():
                st.error("Current password re-authentication is required to authorize account deletion.")
            else:
                ok, msg = delete_current_patient_account(del_password.strip())
                if not ok:
                    st.error(f"Deletion failed: {msg}")
