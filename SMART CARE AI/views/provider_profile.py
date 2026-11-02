"""
SmartCare AI – Healthcare Provider Portal: Provider Profile.
Manage clinical credentials, specialty information, hospital affiliation,
account security settings, and provider deactivation/deletion with medico-legal data protection.
"""

import streamlit as st
from services.auth_service import require_auth, delete_current_provider_account
from database.db import (
    get_provider_by_id,
    get_user_by_id,
    update_user_password,
    verify_password,
    get_connection
)
from utils.validators import validate_name, validate_mobile, validate_password, validate_provider_fields
from utils.helpers import load_css

load_css()
user = require_auth(allowed_roles=["provider"])
provider_id = user.get("provider_id", "DOC-101")
provider = get_provider_by_id(provider_id)

# Header Hero Banner
st.markdown(
    """
    <div class="portal-header-provider">
        <h1 class="portal-header-title">👨‍⚕️ Healthcare Provider Profile</h1>
        <p class="portal-header-subtitle">Manage medical credentials, institutional affiliations, account security, and provider status.</p>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;">
            <span class="badge-pill info" style="background:#FFFFFF; color:#243447; border:none; font-weight:700;">Verified Physician Credentials</span>
            <span class="badge-pill purple" style="background:#FFFFFF; color:#8064D8; border:none; font-weight:700;">Institutional Hospital Affiliation</span>
            <span class="badge-pill success" style="background:#FFFFFF; color:#20A779; border:none; font-weight:700;">Clinical Administrative Privileges</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

p_name = provider["name"] if provider else user["name"]
p_spec = provider["specialty"] if provider else "General Medicine"
p_contact = provider["contact"] if provider else "+91 98111 22233"
p_lic = provider["license_number"] if provider else "MCI-REG-2024-9081"
p_hosp = provider["hospital"] if provider else "SmartCare Apex Healthcare Center"
p_status = provider.get("status", "approved") if provider else "approved"

# Provider Card Summary
st.markdown(
    f"""
    <div class="saas-metric-card card-purple" style="margin-bottom: 20px; padding: 18px 22px;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="font-size:1.3rem; font-weight:800; color:#243447;">{p_name}</div>
                <div style="font-size:0.88rem; color:#64748B; margin-top:2px;">Specialty: <strong>{p_spec}</strong> • Affiliation: {p_hosp}</div>
            </div>
            <div style="display:flex; gap:8px;">
                <span class="badge-pill purple">ID: {provider_id}</span>
                <span class="badge-pill info">Lic: {p_lic}</span>
                <span class="badge-pill success">Status: {p_status.upper()}</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

tab_creds, tab_security, tab_deactivate = st.tabs([
    "🪪 Clinical Credentials",
    "🔐 Account Security",
    "🗑️ Deactivate / Delete Account"
])

# ------------------------------------------------------------------------------
# TAB 1: CLINICAL CREDENTIALS
# ------------------------------------------------------------------------------
with tab_creds:
    st.markdown("### 🪪 Physician & Institutional Information")

    with st.form("update_provider_profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            u_name = st.text_input("Physician Full Name *", value=p_name)
            u_spec = st.text_input("Clinical Specialty *", value=p_spec)
            u_lic = st.text_input("Medical Registration / License #", value=p_lic, disabled=True, help="License numbers are locked to credentialed registration.")
        with col2:
            u_hosp = st.text_input("Hospital / Clinic Affiliation *", value=p_hosp)
            u_contact = st.text_input("Clinical Contact Phone (Indian Mobile) *", value=p_contact)
            st.text_input("Provider Identifier", value=provider_id, disabled=True)

        save_p_btn = st.form_submit_button("Update Credentials & Contact", type="primary", use_container_width=True)

        if save_p_btn:
            v_name, err_name, clean_p_name = validate_name(u_name, "Physician Name")
            v_mob, err_mob, norm_contact = validate_mobile(u_contact, required=True)
            v_cred, err_cred = validate_provider_fields(u_spec, u_hosp, p_lic)

            if not v_name:
                st.error(err_name)
            elif not v_mob:
                st.error(err_mob)
            elif not v_cred:
                st.error(err_cred)
            else:
                with get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        UPDATE providers
                        SET name = ?, specialty = ?, hospital = ?, contact = ?
                        WHERE provider_id = ?
                        """,
                        (clean_p_name, u_spec.strip(), u_hosp.strip(), norm_contact, provider_id)
                    )
                    conn.commit()

                st.session_state["user"]["name"] = clean_p_name
                st.success("Provider credentials updated successfully!")
                st.rerun()

# ------------------------------------------------------------------------------
# TAB 2: ACCOUNT SECURITY
# ------------------------------------------------------------------------------
with tab_security:
    st.markdown("### 🔐 Provider Account Password")
    st.caption(f"Account: `{user['username']}` • Clinical Email: `{user['email']}`")

    with st.form("doc_change_pass_form"):
        old_p = st.text_input("Current Password *", type="password")
        new_p = st.text_input("New Password (min 6 characters) *", type="password")
        conf_p = st.text_input("Confirm New Password *", type="password")

        change_btn = st.form_submit_button("Update Password", type="primary", use_container_width=True)

        if change_btn:
            db_u = get_user_by_id(user["id"])
            if not db_u or not verify_password(old_p, db_u["password_hash"]):
                st.error("Current password is incorrect.")
            else:
                v_pwd, err_pwd = validate_password(new_p, conf_p)
                if not v_pwd:
                    st.error(err_pwd)
                else:
                    update_user_password(user["id"], new_p)
                    st.success("🎉 Provider password updated successfully!")

# ------------------------------------------------------------------------------
# TAB 3: DEACTIVATE / DELETE PROVIDER ACCOUNT
# ------------------------------------------------------------------------------
with tab_deactivate:
    st.markdown("### 🗑️ Deactivate / Close Provider Account")
    st.caption("Manage physician departure, clinical account deactivation, and regulatory record retention.")

    st.markdown(
        """
        <div class="banner-warning" style="margin-bottom:20px;">
            <h4 style="color:#785400; margin:0 0 8px 0; font-size:1.05rem;">⚖️ Healthcare Regulatory & Medico-Legal Retention Policy:</h4>
            <p style="color:#523900; font-size:0.92rem; margin:0 0 8px 0; line-height:1.5;">
                In compliance with clinical electronic health record (EHR) governance:
            </p>
            <ul style="color:#523900; font-size:0.90rem; margin:0; padding-left:20px; line-height:1.6;">
                <li><strong>Associated Patient Records:</strong> If this provider account is associated with patient registrations or clinical records, deleting the doctor must not delete or corrupt patient medical charts. SmartCare AI safely <strong>deactivates</strong> the account (<code>status = 'deactivated'</code>), revoking all system privileges and barring future logins while preserving patient medical charts.</li>
                <li><strong>Zero Linked Records:</strong> If this provider profile has zero linked patient records or charts, the account is completely purged.</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.form("deactivate_provider_form"):
        confirm_doc_check = st.checkbox(
            "I acknowledge the medico-legal retention policy and confirm that I wish to close/deactivate this healthcare provider account."
        )
        doc_del_password = st.text_input(
            "Re-enter Your Current Provider Password to Authenticate *",
            type="password",
            placeholder="Enter password"
        )

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        deact_submit = st.form_submit_button(
            "⚠️ Deactivate / Close Provider Account",
            type="primary",
            use_container_width=True
        )

        if deact_submit:
            if not confirm_doc_check:
                st.error("Please confirm your intent by checking the acknowledgment box above.")
            elif not doc_del_password.strip():
                st.error("Current password re-authentication is required to deactivate your account.")
            else:
                ok, msg = delete_current_provider_account(doc_del_password.strip())
                if not ok:
                    st.error(f"Action failed: {msg}")
