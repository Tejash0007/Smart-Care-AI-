"""
SmartCare AI – Patient Portal: AI Health Assistant.
Interactive health information assistant powered by the official Google Gemini API (google-genai SDK).
Configured via server-side .env credentials (no user-facing API key input).
Provides plain-English explanations of medical terms, lab reference ranges, and doctor visit question preparation.
"""

import streamlit as st
from services.auth_service import require_auth
from services.gemini_service import (
    generate_health_response,
    generate_health_response_stream,
    check_api_key_configured,
    get_model_name
)
from database.db import log_ai_interaction
from utils.helpers import load_css

load_css()
user = require_auth(allowed_roles=["patient"])

# Header Hero Banner
st.markdown(
    """
    <div class="portal-header-patient">
        <h1 class="portal-header-title">🤖 AI Health & Wellness Assistant</h1>
        <p class="portal-header-subtitle">Educational medical intelligence powered by Google Gemini. Ask questions about lab reference ranges, healthy habits, and doctor visit preparation.</p>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;">
            <span class="badge-pill info" style="background:#FFFFFF; color:#087F8C; border:none; font-weight:700;">Plain-English Explanations</span>
            <span class="badge-pill purple" style="background:#FFFFFF; color:#8064D8; border:none; font-weight:700;">Lab Range Decoding</span>
            <span class="badge-pill success" style="background:#FFFFFF; color:#20A779; border:none; font-weight:700;">Non-Diagnostic Guidance</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Mandatory Safety Disclaimer Banner
st.markdown(
    """
    <div class="chat-banner">
        ℹ️ <strong>Educational Notice:</strong> SmartCare AI provides general medical information and wellness guidance. 
        It is <strong>not a diagnostic tool</strong> and does <strong>not prescribe medications or replace your doctor</strong>. 
        In case of severe chest pain, shortness of breath, or medical emergencies, contact emergency medical services immediately (112 / 108 / 911).
    </div>
    """,
    unsafe_allow_html=True
)

# Check Server Gemini API Key Status
api_configured = check_api_key_configured()

# Sidebar Settings & Clear Conversation
with st.sidebar:
    st.markdown("### 🤖 Assistant Options")
    
    if api_configured:
        st.markdown(
            """
            <div style="background-color:#EFF9F5; border:1px solid #B8E8D5; border-left:4px solid #20A779; border-radius:8px; padding:10px 14px; margin-bottom:12px;">
                <span style="font-size:0.88rem; font-weight:700; color:#0D5E43;">🟢 Gemini AI: Active</span>
                <div style="font-size:0.78rem; color:#16845F; margin-top:2px;">Server-side API key verified</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            """
            <div style="background-color:#FEF9EE; border:1px solid #FAEFCF; border-left:4px solid #E5A000; border-radius:8px; padding:10px 14px; margin-bottom:12px;">
                <span style="font-size:0.88rem; font-weight:700; color:#B87B00;">🟠 AI Setup Required</span>
                <div style="font-size:0.78rem; color:#7D5200; margin-top:2px;">Administrator must set GEMINI_API_KEY in server .env</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.caption(f"🧠 Engine: `{get_model_name()}`")
    st.markdown("---")

    if st.button("🗑️ Clear Conversation", use_container_width=True):
        st.session_state["patient_chat_messages"] = [
            {
                "role": "assistant",
                "content": (
                    f"Hello **{user.get('name', 'there')}**! 👋\n\n"
                    "I am your **SmartCare AI Health Assistant**. I can help you:\n"
                    "- Understand complex medical terminology\n"
                    "- Explain what common blood test reference ranges mean\n"
                    "- Provide guidance on balanced nutrition, hydration, and exercise habits\n"
                    "- Prepare thoughtful questions to ask your physician during your next visit\n\n"
                    "How may I support your health learning today?"
                )
            }
        ]
        st.rerun()

# Initialize Chat History
if "patient_chat_messages" not in st.session_state or not st.session_state["patient_chat_messages"]:
    st.session_state["patient_chat_messages"] = [
        {
            "role": "assistant",
            "content": (
                f"Hello **{user.get('name', 'there')}**! 👋\n\n"
                "I am your **SmartCare AI Health Assistant**. I can help you:\n"
                "- Understand complex medical terminology\n"
                "- Explain what common blood test reference ranges mean\n"
                "- Provide guidance on balanced nutrition, hydration, and exercise habits\n"
                "- Prepare thoughtful questions to ask your physician during your next visit\n\n"
                "How may I support your health learning today?"
            )
        }
    ]

# Sanitize chat history: remove any stale error notices from failed requests
st.session_state["patient_chat_messages"] = [
    m for m in st.session_state["patient_chat_messages"]
    if not (
        m.get("role") == "assistant"
        and any(m.get("content", "").strip().startswith(p) for p in ["⏱️", "❌", "⚠️", "🌐", "🔍", "⏳", "🛡️"])
    )
]

# Helper to identify error responses
def _is_error_response(text: str) -> bool:
    if not text:
        return True
    return any(text.strip().startswith(p) for p in ["⏱️", "❌", "⚠️", "🌐", "🔍", "⏳", "🛡️"])

# Display Quick Starter Chips if conversation is fresh
if len(st.session_state["patient_chat_messages"]) <= 1:
    st.markdown("##### 💡 Suggested Questions (Click to Ask):")
    s1, s2, s3, s4 = st.columns(4)
    starters = [
        ("🫀 Systolic vs Diastolic", "What is the difference between systolic and diastolic blood pressure in simple terms?"),
        ("🧪 Fasting Glucose Range", "What does a fasting blood glucose reading represent, and why do reference ranges vary?"),
        ("🥗 Daily Hydration & Diet", "What are evidence-backed tips for daily hydration and dietary fiber intake?"),
        ("📋 Questions for Doctor", "What are 3 important questions I should ask my doctor about routine lipid panel test results?")
    ]

    selected_prompt = None
    with s1:
        if st.button(starters[0][0], key="pat_sug_0", use_container_width=True):
            selected_prompt = starters[0][1]
    with s2:
        if st.button(starters[1][0], key="pat_sug_1", use_container_width=True):
            selected_prompt = starters[1][1]
    with s3:
        if st.button(starters[2][0], key="pat_sug_2", use_container_width=True):
            selected_prompt = starters[2][1]
    with s4:
        if st.button(starters[3][0], key="pat_sug_3", use_container_width=True):
            selected_prompt = starters[3][1]

    if selected_prompt:
        st.session_state["patient_chat_messages"].append({"role": "user", "content": selected_prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(selected_prompt)
        with st.chat_message("assistant", avatar="🩺"):
            with st.spinner("SmartCare AI is analyzing your inquiry..."):
                ok_start, full_response = generate_health_response(st.session_state["patient_chat_messages"])
            if ok_start and full_response:
                st.markdown(full_response)
                st.session_state["patient_chat_messages"].append({"role": "assistant", "content": full_response})
                log_ai_interaction("Suggested Health Starter", user_id=user["id"])
            else:
                err_text = full_response or "The AI assistant returned an empty response. Please try again."
                st.error(err_text)
                if st.session_state["patient_chat_messages"] and st.session_state["patient_chat_messages"][-1]["role"] == "user":
                    st.session_state["patient_chat_messages"].pop()
        st.rerun()

# Render Message History
for msg in st.session_state["patient_chat_messages"]:
    if msg["role"] == "user":
        with st.chat_message("user", avatar="👤"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🩺"):
            st.markdown(msg["content"])

# User Chat Input
user_query = st.chat_input("Type your general health question here (e.g., 'What is resting heart rate?')...")

if user_query:
    st.session_state["patient_chat_messages"].append({"role": "user", "content": user_query})
    
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_query)

    with st.chat_message("assistant", avatar="🩺"):
        with st.spinner("SmartCare AI is analyzing your inquiry..."):
            ok_res, full_response = generate_health_response(st.session_state["patient_chat_messages"])
        if ok_res and full_response:
            st.markdown(full_response)
            st.session_state["patient_chat_messages"].append({"role": "assistant", "content": full_response})
            log_ai_interaction("Patient General Health Inquiry", user_id=user["id"])
        else:
            err_text = full_response or "The AI assistant returned an empty response. Please rephrase your query."
            st.error(err_text)
            # Do not persist error response in dialogue context; remove the failed prompt
            if st.session_state["patient_chat_messages"] and st.session_state["patient_chat_messages"][-1]["role"] == "user":
                st.session_state["patient_chat_messages"].pop()
