"""
Authentication and Role-Based Access Control (RBAC) Service for SmartCare AI.
Manages user authentication, registration, session persistence, role validation,
route-level authorization guards, and account lifecycle management (deletion/deactivation).
"""

import os
from typing import Optional, Dict, Any, Tuple, List
import streamlit as st

from database.db import (
    create_user,
    get_user_by_username_or_email,
    get_user_by_id,
    verify_password,
    hash_password,
    add_patient,
    get_patient_by_user_id,
    get_provider_by_user_id,
    create_provider,
    generate_provider_id,
    grant_provider_access,
    delete_patient_account,
    deactivate_or_delete_provider_account,
    get_connection
)
from utils.validators import (
    validate_name,
    validate_mobile,
    validate_email,
    validate_password,
    validate_provider_fields
)


def get_current_user() -> Optional[Dict[str, Any]]:
    """Retrieve the currently authenticated user from Streamlit session state."""
    return st.session_state.get("user")


def is_authenticated() -> bool:
    """Check if a user is currently authenticated."""
    return bool(st.session_state.get("user"))


def is_patient() -> bool:
    """Check if the current authenticated user has the 'patient' role."""
    user = get_current_user()
    return bool(user and user.get("role") == "patient")


def is_provider() -> bool:
    """Check if the current authenticated user has the 'provider' role."""
    user = get_current_user()
    return bool(user and user.get("role") == "provider")


def login_user(
    username_or_email: str,
    password_plain: str,
    required_role: Optional[str] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Authenticate user credentials and initialize session state upon success.
    Enforces role separation and checks provider approval/activation status.
    """
    if not username_or_email or not str(username_or_email).strip() or not password_plain:
        return False, "Please enter both username/email and password.", None

    user = get_user_by_username_or_email(username_or_email.strip())
    if not user:
        return False, "Invalid credentials. No user found with that identifier.", None

    if user["password_hash"] == "ACCOUNT_DEACTIVATED" or user.get("role") == "deactivated":
        return False, "❌ This account has been deactivated. Login is no longer permitted.", None

    if user.get("role") == "provider":
        prov = get_provider_by_user_id(user["id"])
        if prov and prov.get("status") == "deactivated":
            return False, "❌ This Healthcare Provider account has been deactivated. Access is no longer permitted.", None
        elif prov and prov.get("status") == "pending_approval":
            return False, "⏳ Your Healthcare Provider account is Pending Administrator Verification. Access to patient records is restricted until verification is complete.", None

    if not verify_password(password_plain, user["password_hash"]):
        return False, "Invalid credentials. Incorrect password.", None

    if required_role and user["role"] != required_role:
        return (
            False,
            f"Role mismatch: This account is registered as '{user['role'].title()}'. Please use the {user['role'].title()} portal to sign in.",
            None
        )

    # Attach profile-specific identifiers to the user session
    session_user = {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "role": user["role"],
        "created_at": user["created_at"],
    }

    if user["role"] == "patient":
        pt = get_patient_by_user_id(user["id"])
        if pt:
            session_user["patient_id"] = pt["patient_id"]
            session_user["name"] = pt["name"]
            session_user["age"] = pt["age"]
            session_user["gender"] = pt["gender"]
            session_user["blood_group"] = pt["blood_group"]
            session_user["contact"] = pt["contact"]
        else:
            session_user["patient_id"] = None
            session_user["name"] = user["username"].title()

    elif user["role"] == "provider":
        doc = get_provider_by_user_id(user["id"])
        if doc:
            # Check approval status
            doc_status = doc.get("status", "approved")
            if doc_status == "pending_approval":
                return False, "⏳ Your Healthcare Provider account is Pending Administrator Verification. Access to patient records is restricted until verification is complete.", None
            elif doc_status == "deactivated":
                return False, "❌ This Healthcare Provider account has been deactivated. Access is no longer permitted.", None

            session_user["provider_id"] = doc["provider_id"]
            session_user["name"] = doc["name"]
            session_user["specialty"] = doc["specialty"]
            session_user["hospital"] = doc["hospital"]
            session_user["status"] = doc_status
        else:
            session_user["provider_id"] = "DOC-101"
            session_user["name"] = user["username"].title()
            session_user["status"] = "approved"

    st.session_state["user"] = session_user
    return True, "Login successful!", session_user


def register_patient_account(
    username: str,
    email: str,
    password_plain: str,
    name: str,
    age: int,
    gender: str,
    contact: str,
    blood_group: str = "Unknown",
    confirm_password: Optional[str] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Register a new patient user account with strict input validation on all fields.
    Automatically links to primary clinic provider for authorized clinical support.
    """
    # 1. Validate Username
    cleaned_username = username.strip().lower()
    if len(cleaned_username) < 3 or len(cleaned_username) > 30:
        return False, "Username must be between 3 and 30 characters.", None
    if not cleaned_username.isalnum() and "_" not in cleaned_username:
        return False, "Username can only contain letters, numbers, and underscores.", None

    # 2. Validate Name
    v_name, err_name, clean_name = validate_name(name, "Full Legal Name")
    if not v_name:
        return False, err_name, None

    # 3. Validate Mobile Number (Indian standards)
    v_mob, err_mob, norm_contact = validate_mobile(contact, required=True)
    if not v_mob:
        return False, err_mob, None

    # 4. Validate Email
    v_email, err_email, clean_email = validate_email(email)
    if not v_email:
        return False, err_email, None

    # 5. Validate Password
    v_pass, err_pass = validate_password(password_plain, confirm_password)
    if not v_pass:
        return False, err_pass, None

    # 6. Validate Age
    if not (1 <= int(age) <= 120):
        return False, "Age must be between 1 and 120 years.", None

    # 7. Check Duplicate Identifiers
    existing = get_user_by_username_or_email(cleaned_username)
    if existing:
        return False, "This username is already taken. Please choose another.", None
    
    existing_email = get_user_by_username_or_email(clean_email)
    if existing_email:
        return False, "This email address is already associated with an account.", None

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM patients WHERE contact = ?", (norm_contact,))
        if cursor.fetchone():
            return False, "This mobile number is already registered to an existing patient profile.", None

    user_id = create_user(cleaned_username, clean_email, password_plain, role="patient")
    if not user_id:
        return False, "Failed to create user account. Please try again.", None

    # Register patient profile
    try:
        patient_id = add_patient(
            name=clean_name,
            age=int(age),
            gender=gender,
            contact=norm_contact,
            blood_group=blood_group,
            user_id=user_id,
            is_demo=0
        )
    except Exception as e:
        return False, f"Could not create patient record: {e}", None

    # Automatically grant access to primary clinical provider DOC-101
    grant_provider_access("DOC-101", patient_id)

    # Initialize user session
    session_user = {
        "id": user_id,
        "username": cleaned_username,
        "email": clean_email,
        "role": "patient",
        "patient_id": patient_id,
        "name": clean_name,
        "age": int(age),
        "gender": gender,
        "blood_group": blood_group,
        "contact": norm_contact
    }
    st.session_state["user"] = session_user
    return True, f"Registration successful! Your Patient ID is {patient_id}.", session_user


def register_provider_account(
    username: str,
    email: str,
    password_plain: str,
    confirm_password: str,
    name: str,
    mobile: str,
    specialty: str,
    hospital: str,
    license_number: str,
    invite_code: str
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Register a new healthcare provider account with administrator invitation code validation.
    Unapproved providers or invalid invite codes are strictly rejected from clinical access.
    """
    # 1. Validate Username
    cleaned_username = username.strip().lower()
    if len(cleaned_username) < 3 or len(cleaned_username) > 30:
        return False, "Username must be between 3 and 30 characters.", None
    if not cleaned_username.isalnum() and "_" not in cleaned_username:
        return False, "Username can only contain letters, numbers, and underscores.", None

    # 2. Validate Name
    v_name, err_name, clean_name = validate_name(name, "Physician / Provider Full Name")
    if not v_name:
        return False, err_name, None

    # 3. Validate Mobile
    v_mob, err_mob, norm_mobile = validate_mobile(mobile, required=True)
    if not v_mob:
        return False, err_mob, None

    # 4. Validate Email
    v_email, err_email, clean_email = validate_email(email)
    if not v_email:
        return False, err_email, None

    # 5. Validate Password
    v_pass, err_pass = validate_password(password_plain, confirm_password)
    if not v_pass:
        return False, err_pass, None

    # 6. Validate Clinical Credentials
    v_cred, err_cred = validate_provider_fields(specialty, hospital, license_number)
    if not v_cred:
        return False, err_cred, None

    # 7. Controlled Healthcare Provider Security Check: Administrator Authorization Code
    admin_invite_code = os.getenv("PROVIDER_INVITE_CODE", "SMARTCARE-DOC-2026").strip()
    provided_code = invite_code.strip()

    if not provided_code or provided_code != admin_invite_code:
        return (
            False,
            "⛔ **Clinical Authorization Code Invalid**\n\n"
            "Unrestricted public provider self-registration is strictly disallowed to protect patient record privacy.\n\n"
            "Please obtain an administrator registration key from clinic administration (Demo code: `SMARTCARE-DOC-2026`).",
            None
        )

    # 8. Check Duplicate Accounts
    if get_user_by_username_or_email(cleaned_username):
        return False, "This username is already taken. Please choose another.", None
    
    if get_user_by_username_or_email(clean_email):
        return False, "This clinical email address is already registered.", None

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM providers WHERE contact = ?", (norm_mobile,))
        if cursor.fetchone():
            return False, "This mobile number is already registered to a provider profile.", None

    # 9. Create User and Provider Account
    user_id = create_user(cleaned_username, clean_email, password_plain, role="provider")
    if not user_id:
        return False, "Failed to create user account. Please try again.", None

    new_provider_id = generate_provider_id()
    create_provider(
        user_id=user_id,
        provider_id=new_provider_id,
        name=clean_name,
        email=clean_email,
        specialty=specialty.strip(),
        contact=norm_mobile,
        license_number=license_number.strip(),
        hospital=hospital.strip(),
        status="approved",
        registration_code=provided_code
    )

    session_user = {
        "id": user_id,
        "username": cleaned_username,
        "email": clean_email,
        "role": "provider",
        "provider_id": new_provider_id,
        "name": clean_name,
        "specialty": specialty.strip(),
        "hospital": hospital.strip(),
        "status": "approved"
    }

    return (
        True,
        f"🎉 Provider account registered successfully! Assigned Provider ID: **{new_provider_id}**. You can now sign in.",
        session_user
    )


def delete_current_patient_account(password_plain: str) -> Tuple[bool, str]:
    """Execute patient account deletion with re-authentication and session invalidation."""
    user = get_current_user()
    if not user or user.get("role") != "patient":
        return False, "Unauthorized action. You must be signed in as a patient."

    success, msg = delete_patient_account(user["id"], password_plain)
    if success:
        logout_user(notice=f"✅ {msg}")
    return success, msg


def delete_current_provider_account(password_plain: str) -> Tuple[bool, str]:
    """Execute provider account deactivation/deletion with re-authentication and session invalidation."""
    user = get_current_user()
    if not user or user.get("role") != "provider":
        return False, "Unauthorized action. You must be signed in as a healthcare provider."

    success, msg = deactivate_or_delete_provider_account(user["id"], password_plain)
    if success:
        logout_user(notice=f"✅ {msg}")
    return success, msg


def require_auth(allowed_roles: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Route-level authorization guard.
    Stops page execution and prompts the user if they are unauthenticated
    or lack the required role permissions.
    """
    user = get_current_user()

    if not user:
        st.warning("🔒 **Authentication Required**\nPlease log in to access this portal page.")
        if st.button("⬅️ Return to Sign In", type="primary"):
            st.session_state["user"] = None
            st.rerun()
        st.stop()

    if allowed_roles and user.get("role") not in allowed_roles:
        st.error(
            f"⛔ **Access Denied (Role Restriction)**\n\n"
            f"You are logged in as **{user.get('role', 'unknown').title()}** (`{user.get('username')}`). "
            f"This section is restricted to: {', '.join(r.title() for r in allowed_roles)}."
        )
        st.caption("You cannot access pages outside your authorized portal.")
        if st.button("⬅️ Back to My Dashboard"):
            st.rerun()
        st.stop()

    return user


def logout_user(notice: Optional[str] = None):
    """Clear session authentication state and restart the application."""
    st.session_state.clear()
    if notice:
        st.session_state["logout_notice"] = notice
    st.rerun()
