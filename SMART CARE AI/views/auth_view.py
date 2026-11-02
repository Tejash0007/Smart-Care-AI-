"""
SmartCare AI – Authentication & Portal Selection View.
Provides separate login interfaces for Patients and Healthcare Providers,
new patient self-registration, controlled healthcare provider registration,
and 1-click demo logins for evaluation.
"""

import streamlit as st
from services.auth_service import login_user, register_patient_account, register_provider_account
from utils.helpers import load_css

load_css()

# Display account deletion / deactivation / logout notices if present in session
if "logout_notice" in st.session_state:
    notice_msg = st.session_state.pop("logout_notice")
    st.success(notice_msg)

# Header Hero Banner with Vibrant Healthcare SaaS Gradient
st.markdown(
    """
    <div class="portal-header-patient">
        <h1 class="portal-header-title">🏥 SmartCare AI – Portal Gateway</h1>
        <p class="portal-header-subtitle">
            AI-powered smart healthcare intelligence platform for personal wellness tracking and authorized clinical decision support.
        </p>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:12px;">
            <span class="badge-pill info" style="background:#FFFFFF; color:#087F8C; border:none; font-weight:700;">🛡️ Non-Diagnostic Medical AI</span>
            <span class="badge-pill info" style="background:#FFFFFF; color:#8064D8; border:none; font-weight:700;">🤖 Official Google Gemini Powered</span>
            <span class="badge-pill info" style="background:#FFFFFF; color:#20A779; border:none; font-weight:700;">🔒 Role-Isolated Portals</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Demo Credentials Banner for College Evaluation
st.markdown(
    """
    <div class="banner-success" style="margin-bottom: 22px;">
        <h4 style="color: #0D5E43; margin: 0 0 6px 0; font-size: 1.05rem;">🎓 College Viva & Demonstration Quick-Access:</h4>
        <p style="color: #16845F; margin: 0; font-size: 0.94rem;">
            Click either card below for instant 1-click authentication into pre-loaded evaluation accounts:
        </p>
    </div>
    """,
    unsafe_allow_html=True
)

demo_col1, demo_col2 = st.columns(2)
with demo_col1:
    st.markdown(
        """
        <div class="saas-metric-card card-purple" style="margin-bottom:12px; padding:18px 20px;">
            <div style="font-size:0.82rem; font-weight:700; color:#8064D8; text-transform:uppercase; letter-spacing:0.6px;">Healthcare Provider Portal</div>
            <div style="font-size:1.25rem; font-weight:800; color:#243447; margin:6px 0;">🩺 Dr. Ramesh Sharma, MD</div>
            <div style="font-size:0.88rem; color:#64748B; line-height:1.4;">Chief Cardiologist • Full Hospital Records Access & Clinical AI</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("🩺 Enter as Demo Doctor (Dr. Ramesh Sharma)", use_container_width=True, type="primary", key="quick_doc_btn"):
        ok, msg, user = login_user("dr.sharma", "Provider@123", required_role="provider")
        if ok:
            st.success("Signed in as Dr. Ramesh Sharma!")
            st.rerun()
        else:
            st.error(msg)
    st.caption("Manual login: `dr.sharma@smartcare.ai` • Password: `Provider@123`")

with demo_col2:
    st.markdown(
        """
        <div class="saas-metric-card card-teal" style="margin-bottom:12px; padding:18px 20px;">
            <div style="font-size:0.82rem; font-weight:700; color:#087F8C; text-transform:uppercase; letter-spacing:0.6px;">Personal Patient Portal</div>
            <div style="font-size:1.25rem; font-weight:800; color:#243447; margin:6px 0;">👤 Aarav Sharma (SC-1001)</div>
            <div style="font-size:0.88rem; color:#64748B; line-height:1.4;">Pre-loaded vitals trajectory, digital lab reports & AI chat</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    if st.button("👤 Enter as Demo Patient (Aarav Sharma)", use_container_width=True, key="quick_pat_btn"):
        ok, msg, user = login_user("aarav", "Patient@123", required_role="patient")
        if ok:
            st.success("Signed in as Aarav Sharma!")
            st.rerun()
        else:
            st.error(msg)
    st.caption("Manual login: `aarav.sharma@example.com` • Password: `Patient@123`")

st.markdown("<hr style='border:none; border-top:1.5px solid #E2E8F0; margin:24px 0;'>", unsafe_allow_html=True)

# Authentication Tabs
tab_patient_login, tab_patient_reg, tab_provider_login, tab_provider_reg = st.tabs([
    "👤 Patient Sign In",
    "➕ New Patient Registration",
    "🩺 Healthcare Provider Sign In",
    "🏥 Healthcare Provider Registration"
])

# ------------------------------------------------------------------------------
# TAB 1: PATIENT LOGIN
# ------------------------------------------------------------------------------
with tab_patient_login:
    st.markdown("### 👤 Patient Portal Sign In")
    st.caption("Access your personal biometric vitals, uploaded lab reports, and AI health assistant.")

    with st.form("patient_login_form"):
        p_user = st.text_input("Username or Email Address *", placeholder="e.g. aarav or aarav.sharma@example.com", key="pat_login_user")
        p_pass = st.text_input("Password *", type="password", placeholder="Enter your password", key="pat_login_pass")
        p_submit = st.form_submit_button("Sign In to Patient Portal", type="primary", use_container_width=True)

        if p_submit:
            success, msg, user = login_user(p_user, p_pass, required_role="patient")
            if success:
                st.success("Welcome back! Redirecting to Patient Portal...")
                st.rerun()
            else:
                st.error(msg)

# ------------------------------------------------------------------------------
# TAB 2: PATIENT REGISTRATION
# ------------------------------------------------------------------------------
with tab_patient_reg:
    st.markdown("### ➕ Create a Personal Patient Account")
    st.caption("Register your account to securely monitor vitals and maintain your personal health records.")

    with st.form("patient_reg_form"):
        r_col1, r_col2 = st.columns(2)
        with r_col1:
            reg_username = st.text_input("Choose Username (letters, numbers, underscore) *", placeholder="e.g. rahul_verma", key="pat_reg_user")
            reg_email = st.text_input("Email Address *", placeholder="e.g. rahul@example.com", key="pat_reg_email")
            reg_pass = st.text_input("Password (min 6 characters) *", type="password", key="pat_reg_pass")
            reg_confirm_pass = st.text_input("Confirm Password *", type="password", key="pat_reg_conf_pass")
        with r_col2:
            reg_name = st.text_input("Full Legal Name *", placeholder="e.g. Rahul Verma", key="pat_reg_name")
            reg_contact = st.text_input("Indian Mobile Number (+91) *", placeholder="e.g. +91 98765 43210", key="pat_reg_contact")
            reg_age = st.number_input("Age in Years *", min_value=1, max_value=120, value=25, key="pat_reg_age")
            reg_gender = st.selectbox("Biological Sex / Gender *", ["Male", "Female", "Other"], key="pat_reg_gender")

        reg_blood = st.selectbox("Blood Group", ["Unknown", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"], key="pat_reg_blood")

        reg_submit = st.form_submit_button("Complete Patient Registration", type="primary", use_container_width=True)

        if reg_submit:
            success, msg, user = register_patient_account(
                username=reg_username,
                email=reg_email,
                password_plain=reg_pass,
                name=reg_name,
                age=reg_age,
                gender=reg_gender,
                contact=reg_contact,
                blood_group=reg_blood,
                confirm_password=reg_confirm_pass
            )
            if success:
                st.success(f"🎉 {msg}")
                st.info("You are now signed in. Accessing your patient dashboard...")
                st.rerun()
            else:
                st.error(msg)

# ------------------------------------------------------------------------------
# TAB 3: HEALTHCARE PROVIDER LOGIN
# ------------------------------------------------------------------------------
with tab_provider_login:
    st.markdown("### 🩺 Healthcare Provider Portal Sign In")
    st.caption("Authorized access for licensed physicians, clinical specialists, and hospital staff.")

    with st.form("provider_login_form"):
        doc_user = st.text_input("Doctor Username or Email *", placeholder="e.g. dr.sharma or dr.sharma@smartcare.ai", key="prov_login_user")
        doc_pass = st.text_input("Doctor Password *", type="password", placeholder="Enter provider password", key="prov_login_pass")
        doc_submit = st.form_submit_button("Sign In to Provider Portal", type="primary", use_container_width=True)

        if doc_submit:
            success, msg, user = login_user(doc_user, doc_pass, required_role="provider")
            if success:
                st.success("Welcome, Doctor! Initializing clinical dashboard...")
                st.rerun()
            else:
                st.error(msg)

    st.markdown("<hr style='border:none; border-top:1.5px solid #E2E8F0; margin:16px 0;'>", unsafe_allow_html=True)
    st.caption("🔒 *Security Notice: Provider accounts have authorized access to electronic health records. Unapproved or deactivated providers are strictly restricted from accessing patient charts.*")

# ------------------------------------------------------------------------------
# TAB 4: HEALTHCARE PROVIDER REGISTRATION (Controlled with Admin Authorization)
# ------------------------------------------------------------------------------
with tab_provider_reg:
    st.markdown("### 🏥 Healthcare Provider Registration")
    st.caption("Controlled clinical registration for physicians and hospital specialists. Requires administrator authorization.")

    st.markdown(
        """
        <div class="banner-info" style="margin-bottom:16px;">
            <strong>🔐 Controlled Provider Access:</strong> Unrestricted public registration for clinical roles is prohibited to maintain patient confidentiality and HIPAA-aligned data governance. You must supply a valid Administrator Authorization Code.
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.form("provider_registration_form"):
        doc_col1, doc_col2 = st.columns(2)
        with doc_col1:
            new_doc_name = st.text_input("Full Physician Name *", placeholder="e.g. Dr. Priya Nair", key="prov_reg_name")
            new_doc_username = st.text_input("Doctor Username *", placeholder="e.g. dr.priya", key="prov_reg_user")
            new_doc_email = st.text_input("Clinical Email *", placeholder="e.g. dr.priya@smartcare.ai", key="prov_reg_email")
            new_doc_phone = st.text_input("Indian Mobile Number (+91) *", placeholder="e.g. +91 98111 22334", key="prov_reg_phone")
            new_doc_pass = st.text_input("Password (min 6 characters) *", type="password", key="prov_reg_pass")
            new_doc_conf_pass = st.text_input("Confirm Password *", type="password", key="prov_reg_conf_pass")

        with doc_col2:
            new_doc_spec = st.text_input("Clinical Specialty *", placeholder="e.g. Internal Medicine, Cardiology", key="prov_reg_spec")
            new_doc_hosp = st.text_input("Hospital / Clinic Affiliation *", placeholder="e.g. SmartCare Apex Hospital", key="prov_reg_hosp")
            new_doc_lic = st.text_input("Medical Registration / License # *", placeholder="e.g. MCI-REG-2026-4401", key="prov_reg_lic")
            
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            new_doc_code = st.text_input(
                "Administrator Authorization Code *",
                placeholder="Enter admin invite code",
                help="Supplied by hospital administration. Evaluation demo code: SMARTCARE-DOC-2026",
                key="prov_reg_code"
            )
            st.caption("💡 *Demo Evaluation Invite Code:* `SMARTCARE-DOC-2026`")

        doc_reg_submit = st.form_submit_button("Submit Provider Clinical Registration", type="primary", use_container_width=True)

        if doc_reg_submit:
            doc_ok, doc_msg, doc_user_obj = register_provider_account(
                username=new_doc_username,
                email=new_doc_email,
                password_plain=new_doc_pass,
                confirm_password=new_doc_conf_pass,
                name=new_doc_name,
                mobile=new_doc_phone,
                specialty=new_doc_spec,
                hospital=new_doc_hosp,
                license_number=new_doc_lic,
                invite_code=new_doc_code
            )
            if doc_ok:
                st.success(f"🎉 {doc_msg}")
                st.info("Your clinical account is active. Please switch to the **'🩺 Healthcare Provider Sign In'** tab above to access the provider portal.")
            else:
                st.error(doc_msg)
