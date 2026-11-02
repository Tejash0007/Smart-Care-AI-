"""
SmartCare AI – Page 1: AI Health Assistant
Interactive conversational health information assistant powered by the official Google Gemini API (google-genai SDK).
Follows strict non-diagnostic, educational, and patient safety protocols.
"""

import streamlit as st
from services.gemini_service import (
    generate_health_response,
    check_api_key_configured,
    get_model_name
)
from database.db import log_ai_interaction
from utils.helpers import load_css

# ==============================================================================
# PAGE CONFIGURATION & THEME
# ==============================================================================
st.set_page_config(
    page_title="AI Health Assistant – SmartCare AI",
    page_icon="🤖",
    layout="wide"
)

load_css()

# ==============================================================================
# SIDEBAR CONTROLS & API CONFIGURATION
# ==============================================================================
with st.sidebar:
    st.markdown("### 📌 Navigation")
    st.page_link("app.py", label="Executive Dashboard", icon="🏥")
    st.page_link("pages/1_AI_Health_Assistant.py", label="AI Health Assistant", icon="🤖")
    st.page_link("pages/2_Patient_Management.py", label="Patient Management", icon="👥")
    st.page_link("pages/3_Health_Tracker.py", label="Health Tracker", icon="📈")
    st.page_link("pages/4_Health_Reports.py", label="Health Reports", icon="📑")

    st.markdown("---")
    st.markdown("### 🤖 Assistant Controls")
    
    # Optional runtime key input for flexibility during viva/demo
    current_key_val = st.session_state.get("runtime_gemini_key", "")
    runtime_key_input = st.text_input(
        "Gemini API Key (Optional Override):",
        type="password",
        value=current_key_val,
        help="If not set in .env, you can paste your Google AI Studio API key here directly.",
        key="api_key_override_input"
    )
    # Sync runtime key into session state immediately
    st.session_state["runtime_gemini_key"] = runtime_key_input.strip()

    has_valid_key = check_api_key_configured(st.session_state.get("runtime_gemini_key"))
    
    if has_valid_key:
        st.success("🟢 API Status: Connected")
    else:
        st.warning("🟠 API Status: Key Required")
        st.caption("Obtain a free API key at [Google AI Studio](https://aistudio.google.com/).")

    st.info(f"🧠 Model: `{get_model_name()}`")
    st.markdown("---")

    # Clear chat button
    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state["chat_messages"] = [
            {
                "role": "assistant",
                "content": (
                    "Hello! I am your **SmartCare AI Health Assistant**. 👋\n\n"
                    "I can help explain common medical terms, healthy lifestyle practices, nutrition principles, "
                    "and suggest thoughtful questions you might ask your doctor during your next visit.\n\n"
                    "How may I assist your health learning today?"
                )
            }
        ]
        st.rerun()

    st.markdown("---")
    st.markdown("### 💡 Recommended Topics")
    st.markdown("- Explain medical abbreviations (e.g. ECG, HbA1c)")
    st.markdown("- Understanding blood pressure readings")
    st.markdown("- Healthy hydration & nutrition tips")
    st.markdown("- Preparing questions for your physician")

# ==============================================================================
# HEADER & CLINICAL DISCLAIMER
# ==============================================================================
st.markdown(
    """
    <div class="medical-header">
        <h1>🤖 AI Health & Wellness Assistant</h1>
        <p>Ask health questions, demystify medical terminology, and receive wellness guidance powered by Google Gemini AI.</p>
    </div>
    """,
    unsafe_allow_html=True
)

# Mandatory prominent disclaimer
st.markdown(
    """
    <div class="chat-disclaimer">
        ℹ️ <strong>Clinical Safety Notice:</strong> This AI assistant provides general health information and educational guidance. 
        It is <strong>not a medical diagnostic tool</strong> and does <strong>not replace professional medical advice</strong>, diagnosis, or treatment. 
        In case of chest pain, severe breathlessness, or medical emergencies, please contact emergency medical services immediately.
    </div>
    """,
    unsafe_allow_html=True
)

# Initialize conversation history in session state
if "chat_messages" not in st.session_state or not st.session_state["chat_messages"]:
    st.session_state["chat_messages"] = [
        {
            "role": "assistant",
            "content": (
                "Hello! I am your **SmartCare AI Health Assistant**. 👋\n\n"
                "I can help explain common medical terms, healthy lifestyle practices, nutrition principles, "
                "and suggest thoughtful questions you might ask your doctor during your next visit.\n\n"
                "How may I assist your health learning today?"
            )
        }
    ]

# Display quick suggestion buttons if only the greeting exists
if len(st.session_state["chat_messages"]) <= 1:
    st.markdown("##### 🔍 Quick Starters:")
    sug_col1, sug_col2, sug_col3, sug_col4 = st.columns(4)
    starter_prompts = [
        ("🫀 Systolic vs Diastolic", "Can you explain the difference between systolic and diastolic blood pressure in simple terms?"),
        ("🥗 Balanced Diet Habits", "What are general science-backed tips for maintaining healthy daily nutrition and hydration?"),
        ("📋 Questions for Doctor", "What are good questions I should ask my doctor during a routine annual health checkup?"),
        ("🧪 Understanding BMI", "What does Body Mass Index (BMI) measure, and why is it considered a screening tool rather than a diagnosis?")
    ]

    selected_starter = None
    with sug_col1:
        if st.button(starter_prompts[0][0], key="btn_sug_0", use_container_width=True):
            selected_starter = starter_prompts[0][1]
    with sug_col2:
        if st.button(starter_prompts[1][0], key="btn_sug_1", use_container_width=True):
            selected_starter = starter_prompts[1][1]
    with sug_col3:
        if st.button(starter_prompts[2][0], key="btn_sug_2", use_container_width=True):
            selected_starter = starter_prompts[2][1]
    with sug_col4:
        if st.button(starter_prompts[3][0], key="btn_sug_3", use_container_width=True):
            selected_starter = starter_prompts[3][1]

    if selected_starter:
        st.session_state["chat_messages"].append({"role": "user", "content": selected_starter})
        with st.spinner("SmartCare AI is generating guidance..."):
            success, response_text = generate_health_response(
                st.session_state["chat_messages"],
                runtime_api_key=st.session_state.get("runtime_gemini_key")
            )
            st.session_state["chat_messages"].append({"role": "assistant", "content": response_text})
            if success:
                log_ai_interaction("Suggested Health Starter")
        st.rerun()

# Render chat history
for msg in st.session_state["chat_messages"]:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🩺"):
            st.markdown(msg["content"])

# User Chat Input
user_query = st.chat_input("Type your general health question here (e.g., 'What is resting heart rate?')...")

if user_query:
    # Append user question
    st.session_state["chat_messages"].append({"role": "user", "content": user_query})
    
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_query)

    # Generate response
    with st.chat_message("assistant", avatar="🩺"):
        with st.spinner("Analyzing with Google Gemini AI..."):
            success, response_text = generate_health_response(
                st.session_state["chat_messages"],
                runtime_api_key=st.session_state.get("runtime_gemini_key")
            )
            st.markdown(response_text)

    # Save assistant response to state
    st.session_state["chat_messages"].append({"role": "assistant", "content": response_text})

    # Log interaction anonymously in SQLite for the dashboard
    if success:
        # Determine broad topic category
        query_lower = user_query.lower()
        if any(w in query_lower for w in ["pressure", "bp", "heart", "pulse"]):
            cat = "Cardiovascular Vitals"
        elif any(w in query_lower for w in ["food", "diet", "nutrition", "water", "hydrate", "vitamin"]):
            cat = "Nutrition & Hydration"
        elif any(w in query_lower for w in ["sugar", "glucose", "diabetes"]):
            cat = "Blood Glucose & Metabolism"
        elif any(w in query_lower for w in ["doctor", "ask", "test", "report", "question"]):
            cat = "Doctor Visit Preparation"
        else:
            cat = "General Health Guidance"
        
        log_ai_interaction(cat)
