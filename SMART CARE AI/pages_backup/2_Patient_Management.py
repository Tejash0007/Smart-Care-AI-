"""
SmartCare AI – Page 2: Patient Management System
Handles patient registration, unique ID generation, profile viewing,
patient searching, record editing, and safe deletion using SQLite.
"""

import streamlit as st
import pandas as pd
from datetime import date

from database.db import (
    add_patient,
    get_all_patients,
    get_patient_by_id,
    search_patients,
    update_patient,
    delete_patient,
    get_health_records
)
from utils.helpers import load_css

# ==============================================================================
# PAGE CONFIGURATION
# ==============================================================================
st.set_page_config(
    page_title="Patient Management – SmartCare AI",
    page_icon="👥",
    layout="wide"
)

load_css()

# ==============================================================================
# SIDEBAR NAVIGATION
# ==============================================================================
with st.sidebar:
    st.markdown("### 📌 Navigation")
    st.page_link("app.py", label="Executive Dashboard", icon="🏥")
    st.page_link("pages/1_AI_Health_Assistant.py", label="AI Health Assistant", icon="🤖")
    st.page_link("pages/2_Patient_Management.py", label="Patient Management", icon="👥")
    st.page_link("pages/3_Health_Tracker.py", label="Health Tracker", icon="📈")
    st.page_link("pages/4_Health_Reports.py", label="Health Reports", icon="📑")
    st.markdown("---")
    st.caption("College Minor Project • B.Tech CSE\nPatient Database Operations")

# ==============================================================================
# HEADER
# ==============================================================================
st.markdown(
    """
    <div class="medical-header">
        <h1>👥 Patient Management System</h1>
        <p>Register new patients, manage clinical profiles, and maintain accurate demographic records.</p>
    </div>
    """,
    unsafe_allow_html=True
)

tab_view, tab_register, tab_manage = st.tabs(["📋 View & Search Patients", "➕ Register New Patient", "✏️ Edit / Delete Patient"])

# ==============================================================================
# TAB 1: VIEW & SEARCH PATIENTS
# ==============================================================================
with tab_view:
    st.markdown("### 🔍 Patient Registry")
    
    col_search, col_refresh = st.columns([4, 1])
    with col_search:
        search_query = st.text_input(
            "Search Patients by Name, ID, or Contact Number:",
            placeholder="e.g. SC-1001 or Aarav...",
            label_visibility="collapsed"
        )
    with col_refresh:
        if st.button("🔄 Refresh List", use_container_width=True):
            st.rerun()

    # Retrieve filtered or full patient list
    if search_query.strip():
        patient_list = search_patients(search_query)
        st.info(f"Showing {len(patient_list)} result(s) matching '{search_query}'.")
    else:
        patient_list = get_all_patients()

    if patient_list:
        df_display = pd.DataFrame(patient_list)
        df_display = df_display[[
            "patient_id", "name", "age", "gender", "contact", "blood_group", "registration_date", "notes"
        ]]
        df_display.columns = [
            "Patient ID", "Full Name", "Age", "Gender", "Contact", "Blood Group", "Reg Date", "Clinical Notes"
        ]
        st.dataframe(df_display, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("### 🪪 Individual Patient Profile Card")
        
        # Select patient to view profile in detail
        pt_options = [f"{p['patient_id']} - {p['name']}" for p in patient_list]
        selected_pt_str = st.selectbox("Select Patient to Inspect Profile:", pt_options)

        if selected_pt_str:
            selected_pt_id = selected_pt_str.split(" - ")[0]
            selected_patient = get_patient_by_id(selected_pt_id)
            
            if selected_patient:
                p_col1, p_col2 = st.columns([1.5, 2.5])
                with p_col1:
                    st.markdown(
                        f"""
                        <div class="feature-card" style="border-top: 4px solid #0f4c81;">
                            <h3>{selected_patient['name']}</h3>
                            <p><strong>Patient ID:</strong> <code>{selected_patient['patient_id']}</code></p>
                            <p><strong>Age / Gender:</strong> {selected_patient['age']} years • {selected_patient['gender']}</p>
                            <p><strong>Blood Group:</strong> {selected_patient['blood_group']}</p>
                            <p><strong>Contact:</strong> {selected_patient['contact']}</p>
                            <p><strong>Registration Date:</strong> {selected_patient['registration_date']}</p>
                            <p><strong>Clinical Notes:</strong> {selected_patient['notes'] or 'None recorded'}</p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    st.page_link("pages/3_Health_Tracker.py", label="📈 Record Vitals for this Patient", use_container_width=True)
                    st.page_link("pages/4_Health_Reports.py", label="📑 Generate Medical Report", use_container_width=True)

                with p_col2:
                    st.markdown("#### Recent Health Metric Records")
                    pt_records = get_health_records(patient_id=selected_pt_id)
                    if pt_records:
                        df_pt_rec = pd.DataFrame(pt_records)[[
                            "recording_date", "weight_kg", "height_cm", "bmi", "systolic_bp", "diastolic_bp", "blood_glucose", "heart_rate"
                        ]]
                        df_pt_rec.columns = ["Date", "Weight(kg)", "Height(cm)", "BMI", "Systolic", "Diastolic", "Glucose(mg/dL)", "Heart Rate(BPM)"]
                        st.dataframe(df_pt_rec, use_container_width=True, hide_index=True)
                    else:
                        st.caption("No biometric health measurements logged yet for this patient.")
                        st.info("💡 You can record vitals in the **Health Tracker** page.")
    else:
        st.warning("No registered patients found.")

# ==============================================================================
# TAB 2: REGISTER NEW PATIENT
# ==============================================================================
with tab_register:
    st.markdown("### ➕ Patient Registration Form")
    st.caption("All patient records are stored persistently in SQLite with parameterized queries.")

    with st.form("register_patient_form", clear_on_submit=True):
        col_name, col_age, col_gender = st.columns([2, 1, 1])
        with col_name:
            new_name = st.text_input("Patient Full Name *", placeholder="e.g. Ramesh Chandra")
        with col_age:
            new_age = st.number_input("Age (Years) *", min_value=1, max_value=120, value=30)
        with col_gender:
            new_gender = st.selectbox("Gender *", ["Male", "Female", "Other"])

        col_contact, col_blood, col_date = st.columns([1.5, 1, 1.5])
        with col_contact:
            new_contact = st.text_input("Contact Number *", placeholder="e.g. +91 98765 00000")
        with col_blood:
            new_blood = st.selectbox("Blood Group", ["Unknown", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"])
        with col_date:
            new_date = st.date_input("Registration Date", value=date.today())

        new_notes = st.text_area("Clinical Notes / Medical History Summary (Optional)", placeholder="e.g. No known drug allergies, non-smoker...")

        submit_patient = st.form_submit_button("Register Patient", type="primary")

        if submit_patient:
            if not new_name.strip():
                st.error("Please enter a valid patient name.")
            elif not new_contact.strip():
                st.error("Please enter a contact number.")
            else:
                assigned_id = add_patient(
                    name=new_name,
                    age=new_age,
                    gender=new_gender,
                    contact=new_contact,
                    blood_group=new_blood,
                    registration_date=new_date.isoformat(),
                    notes=new_notes
                )
                st.success(f"🎉 Patient successfully registered! Assigned Unique Patient ID: **{assigned_id}**")
                st.info("You can now view this patient in the registry or record their biometric vitals.")

# ==============================================================================
# TAB 3: EDIT / DELETE PATIENT
# ==============================================================================
with tab_manage:
    st.markdown("### ✏️ Manage Existing Patient Record")

    all_pts = get_all_patients()
    if not all_pts:
        st.warning("No patients currently available to edit.")
    else:
        edit_select_str = st.selectbox(
            "Select Patient to Edit or Delete:",
            [f"{p['patient_id']} - {p['name']}" for p in all_pts],
            key="edit_select"
        )
        target_id = edit_select_str.split(" - ")[0]
        curr_pt = get_patient_by_id(target_id)

        if curr_pt:
            col_edit_form, col_del_box = st.columns([2, 1])

            with col_edit_form:
                st.markdown("#### Update Patient Details")
                with st.form("update_patient_form"):
                    up_name = st.text_input("Full Name", value=curr_pt["name"])
                    up_col1, up_col2 = st.columns(2)
                    with up_col1:
                        up_age = st.number_input("Age", min_value=1, max_value=120, value=curr_pt["age"])
                    with up_col2:
                        gender_list = ["Male", "Female", "Other"]
                        gender_idx = gender_list.index(curr_pt["gender"]) if curr_pt["gender"] in gender_list else 0
                        up_gender = st.selectbox("Gender", gender_list, index=gender_idx)

                    up_contact = st.text_input("Contact Number", value=curr_pt["contact"])
                    
                    blood_list = ["Unknown", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
                    blood_idx = blood_list.index(curr_pt["blood_group"]) if curr_pt["blood_group"] in blood_list else 0
                    up_blood = st.selectbox("Blood Group", blood_list, index=blood_idx)

                    up_notes = st.text_area("Clinical Notes", value=curr_pt["notes"] or "")

                    save_changes = st.form_submit_button("Save Changes", type="primary")
                    if save_changes:
                        if not up_name.strip() or not up_contact.strip():
                            st.error("Name and Contact cannot be blank.")
                        else:
                            updated = update_patient(
                                patient_id=target_id,
                                name=up_name,
                                age=up_age,
                                gender=up_gender,
                                contact=up_contact,
                                blood_group=up_blood,
                                notes=up_notes
                            )
                            if updated:
                                st.success("Patient record updated successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to update patient record.")

            with col_del_box:
                st.markdown("#### 🗑️ Delete Patient Record")
                st.warning("⚠️ Warning: Deleting a patient will also permanently delete all associated biometric health records.")
                
                confirm_del = st.checkbox(f"I confirm deletion of **{curr_pt['patient_id']} ({curr_pt['name']})**")
                if st.button("Permanently Delete Patient", type="secondary", disabled=not confirm_del):
                    deleted = delete_patient(target_id)
                    if deleted:
                        st.success(f"Patient {target_id} and associated records removed.")
                        st.rerun()
                    else:
                        st.error("Could not delete patient record.")
