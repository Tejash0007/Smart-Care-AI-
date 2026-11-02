"""
Gemini AI Service Module for SmartCare AI.
Integrates with Google Gemini API using the official `google-genai` SDK.
Centralized server-side configuration via .env (no user-facing key inputs).
Optimized for performance: cached client singleton, streaming support,
bounded conversation history, and sub-second Time-To-First-Token (TTFT).
Includes comprehensive diagnostic logging for latency and exception inspection.
"""

import os
import time
import sys
import socket
from typing import List, Dict, Optional, Tuple, Generator
from dotenv import load_dotenv

# Ensure IPv4 resolution priority to avoid Windows IPv6 black-hole routing stalls (~170s)
_original_getaddrinfo = socket.getaddrinfo

def _ipv4_preferred_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """
    Ensure IPv4 addresses are prioritized for Google API endpoints.
    On Windows systems with inactive IPv6 routing, default getaddrinfo returns
    unreachable IPv6 addresses first, causing TCP connection attempts to stall
    for 170+ seconds before falling back to IPv4.
    """
    try:
        if "googleapis.com" in str(host) and family in (0, socket.AF_UNSPEC):
            return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
    except Exception:
        pass
    return _original_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = _ipv4_preferred_getaddrinfo

# Load server-side environment variables from .env
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_path):
    load_dotenv(_env_path)
else:
    load_dotenv()

SYSTEM_INSTRUCTION = """
You are SmartCare AI, an empathetic, knowledgeable, and safety-focused AI Health Information and Educational Assistant.
Your mission is to help users understand general health topics, medical terminology, wellness habits, nutrition, and lifestyle guidance in simple, clear, and reassuring language.

CRITICAL MEDICAL SAFETY RULES:
1. NON-DIAGNOSTIC: You must NOT diagnose diseases, conditions, or illnesses. Do not claim to provide a medical diagnosis.
2. NO PRESCRIBING: You must NOT prescribe medications, adjust dosages, or recommend stopping/starting prescribed drugs.
3. NOT A DOCTOR SUBSTITUTE: Always emphasize that your information is for educational and guidance purposes only and never replaces a qualified doctor or healthcare professional.
4. EMERGENCY CARE: If a user mentions potential medical emergencies (e.g., severe chest pain, shortness of breath, sudden numbness or paralysis, heavy bleeding, loss of consciousness), immediately advise them in bold text to seek urgent medical care or call local emergency services (e.g. 112 / 108 / 911).
5. DOCTOR DISCUSSION SUGGESTIONS: When appropriate, provide 2 to 3 practical, thoughtful questions the user can ask their doctor during a consultation.
6. NO FABRICATION: Never fabricate medical facts, lab references, or clinical predictions. Communicate uncertainty clearly when information is nuanced or not established.
7. CLEAR FORMATTING: Use structured formatting with clean bullet points, headings, and easy-to-understand definitions.
"""

# Centralized Gemini Model Configuration
DEFAULT_MODEL = "gemini-3.5-flash-lite"
SUPPORTED_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]

# Client timeout in milliseconds (30,000 ms = 30.0 seconds).
# NOTE: The official google-genai SDK explicitly calculates: timeout_in_seconds = timeout / 1000.0.
# A millisecond value of 30000 ensures a realistic 30-second socket timeout rather than sub-second cutoffs.
API_TIMEOUT_MS = 30000

# Module-level client singleton for non-Streamlit environments (tests, scripts)
_module_client = None


def get_api_key() -> Optional[str]:
    """
    Retrieve Gemini API key strictly server-side.
    Checks Streamlit Secrets first (for Streamlit Community Cloud deployment),
    then falls back to environment variables / .env (for local development).
    Never exposes or accepts keys from patient/provider UI inputs.
    """
    # 1. Streamlit Secrets (Cloud Deployment)
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "GEMINI_API_KEY" in st.secrets:
                val = str(st.secrets["GEMINI_API_KEY"]).strip()
                if val and val not in ["your_api_key_here", "your_gemini_api_key"]:
                    return val
            if "gemini" in st.secrets and isinstance(st.secrets["gemini"], dict):
                val = str(st.secrets["gemini"].get("api_key", "")).strip()
                if val and val not in ["your_api_key_here", "your_gemini_api_key"]:
                    return val
    except Exception:
        pass

    # 2. Local Environment Variable (.env or system env)
    key_from_env = os.getenv("GEMINI_API_KEY", "").strip()
    if key_from_env and key_from_env not in ["your_api_key_here", "your_gemini_api_key"]:
        return key_from_env
    return None


def get_model_name() -> str:
    """Get the centralized Gemini model name from Streamlit Secrets, environment, or default."""
    configured = ""
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            if "GEMINI_MODEL" in st.secrets:
                configured = str(st.secrets["GEMINI_MODEL"]).strip()
            elif "gemini" in st.secrets and isinstance(st.secrets["gemini"], dict):
                configured = str(st.secrets["gemini"].get("model", "")).strip()
    except Exception:
        pass

    if not configured:
        configured = os.getenv("GEMINI_MODEL", "").strip()

    if configured == "gemini-2.0-flash-lite":
        return DEFAULT_MODEL
    if configured and configured in SUPPORTED_MODELS:
        return configured
    return DEFAULT_MODEL


def check_api_key_configured(*args, **kwargs) -> bool:
    """Check if a valid server-side API key is available in .env."""
    key = get_api_key()
    return bool(key and len(key) > 5)


def get_masked_api_key() -> str:
    """Return a masked representation of the configured key for diagnostic logs only."""
    key = get_api_key()
    if not key:
        return "Not Configured"
    if len(key) <= 8:
        return "****"
    return f"{key[:4]}...{key[-4:]}"


def _create_raw_client(api_key: str):
    """Instantiate a google-genai Client with configured 30,000ms (30.0s) timeout."""
    from google import genai
    from google.genai import types
    http_opts = types.HttpOptions(timeout=API_TIMEOUT_MS)
    return genai.Client(api_key=api_key, http_options=http_opts)


# Streamlit resource cache for client singleton
try:
    import streamlit as st
    @st.cache_resource(show_spinner=False)
    def _get_st_cached_client(api_key: str):
        return _create_raw_client(api_key)
except Exception:
    _get_st_cached_client = None


def get_gemini_client():
    """
    Retrieve the cached Gemini Client singleton.
    Eliminates ~500ms repeated client initialization overhead per request.
    Does NOT cache any private patient data or responses.
    """
    global _module_client
    api_key = get_api_key()
    if not api_key:
        return None

    # Use Streamlit resource cache if running inside Streamlit
    if _get_st_cached_client is not None:
        try:
            return _get_st_cached_client(api_key)
        except Exception:
            pass

    # Fallback to module singleton
    if _module_client is None:
        _module_client = _create_raw_client(api_key)
    return _module_client


def _log_diagnostic(stage: str, details: str):
    """Log structured diagnostic telemetry to stdout without exposing keys or patient data."""
    timestamp = time.strftime("%H:%M:%S")
    print(f"[Gemini Diagnostic {timestamp}] [{stage}] {details}", file=sys.stderr, flush=True)


def _format_gemini_error(e: Exception, model_name: str, elapsed_sec: Optional[float] = None) -> str:
    """
    Standardized error formatting across all generation paths.
    Properly classifies network drops, auth errors, rate limits, and genuine timeouts.
    """
    err_msg = str(e)
    err_lower = err_msg.lower()
    elapsed_info = f" after {elapsed_sec:.2f}s" if elapsed_sec is not None else ""

    elapsed_str = f"{elapsed_sec:.4f}s" if elapsed_sec is not None else "N/A"
    # Diagnostic logging of exception details
    _log_diagnostic(
        "ERROR_CAUGHT",
        f"Class: {e.__class__.__module__}.{e.__class__.__name__} | Elapsed: {elapsed_str} | Message: {err_msg[:200]}"
    )

    # 1. Connection / Network errors (Must be checked before 'timeout' to avoid misclassifying ConnectError as Timeout)
    if any(term in err_lower for term in [
        "failed to establish a new connection", "getaddrinfo failed", "connecterror",
        "connection refused", "network is unreachable", "connection error"
    ]):
        return (
            "🌐 **Internet Connection Issue**\n\n"
            f"Unable to connect to Google Gemini servers{elapsed_info}. Please verify that the system has an active internet connection."
        )

    # 2. Authentication Errors
    elif any(term in err_lower for term in ["api_key_invalid", "401", "invalid api key", "permission_denied", "api key not valid"]):
        return (
            "❌ **Invalid Server Gemini API Key**\n\n"
            "The server-side API key configured in `.env` was rejected by Google AI Studio. Please verify that the server administrator has supplied a valid, active API key."
        )

    # 3. Model Not Found / Discontinued (404)
    elif any(term in err_lower for term in ["404", "not_found", "model not found", "no longer available", "does not exist", "is not supported"]):
        return (
            f"🔍 **Gemini Model 404 Error (Model Not Found)**\n\n"
            f"The requested Gemini model `{model_name}` is not available or has been discontinued by Google AI.\n\n"
            f"**Details:** `{err_msg}`\n\n"
            f"Please verify `GEMINI_MODEL=gemini-3.5-flash-lite` in your server `.env` file."
        )

    # 4. Quota / Rate Limits (429)
    elif any(term in err_lower for term in ["resource_exhausted", "429", "quota"]):
        return (
            "⏳ **API Rate Limit Exceeded**\n\n"
            "The Google Gemini API rate limit or quota has momentarily been reached. Please wait approximately 60 seconds before submitting your next question."
        )

    # 5. Genuine Timeout Errors
    elif any(term in err_lower for term in ["timeout", "timed out", "readtimeout", "pooltimeout"]):
        return (
            f"⏱️ **Request Timed Out**\n\n"
            f"The request to Google Gemini API timed out{elapsed_info}. Please check your internet connection and retry."
        )

    # 6. Safety Filters
    elif "blocked" in err_lower or "safety" in err_lower:
        return (
            "🛡️ **Safety Guideline Notice**\n\n"
            "The query triggered Gemini safety filters and could not be answered. Please ask general health and wellness questions."
        )

    # 7. Generic Fallback
    else:
        return f"⚠️ **AI Assistant Encountered an Error:**\n\n`{err_msg}`\n\nPlease check network connectivity or contact the clinic administrator."


def _build_contents_from_messages(messages: List[Dict[str, str]]):
    """Convert conversational message list into types.Content objects with alternating turns."""
    from google.genai import types

    # Optimize conversation history: retain at most the last 10 messages (5 turn pairs)
    active_msgs = messages[-10:] if len(messages) > 10 else messages

    contents = []
    last_role = None

    for msg in active_msgs:
        raw_role = msg.get("role", "")
        role = "model" if raw_role in ["assistant", "model"] else "user"
        content = msg.get("content", "").strip()

        if not content:
            continue

        # Skip leading model turns so conversation starts with user turn
        if not contents and role == "model":
            continue

        # Merge consecutive turns with the same role
        if role == last_role and contents:
            prev_text = contents[-1].parts[0].text
            contents[-1] = types.Content(
                role=role,
                parts=[types.Part.from_text(text=f"{prev_text}\n\n{content}")]
            )
        else:
            contents.append(
                types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=content)]
                )
            )
            last_role = role

    return contents


def generate_health_response(
    messages: List[Dict[str, str]],
    *args,
    **kwargs
) -> Tuple[bool, str]:
    """
    Generate an AI response (non-streaming) using the official google-genai SDK.
    Uses centralized server-side GEMINI_API_KEY from .env.
    """
    client = get_gemini_client()
    if not client:
        return (
            False,
            "⚠️ **Gemini AI Service Unavailable**\n\n"
            "The system administrator has not configured the server-side `GEMINI_API_KEY` in the application environment (`.env`).\n\n"
            "Please contact clinic administration or check the server `.env` configuration file."
        )

    model = get_model_name()
    t0 = time.perf_counter()
    _log_diagnostic("START_REQUEST", f"API generate_health_response initiated | Model: {model}")

    try:
        from google.genai import types

        contents = _build_contents_from_messages(messages)
        if not contents:
            return False, "Please enter a valid health question to begin."

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.3,
            max_output_tokens=1500,
        )

        response = client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

        elapsed = time.perf_counter() - t0
        if response and response.text:
            _log_diagnostic("SUCCESS", f"generate_health_response completed in {elapsed:.3f}s | Output: {len(response.text)} chars")
            return True, response.text.strip()

        # Detailed candidate inspection if response.text is empty
        diag_details = []
        if hasattr(response, "candidates") and response.candidates:
            for idx, cand in enumerate(response.candidates):
                fr = getattr(cand, "finish_reason", "UNKNOWN")
                diag_details.append(f"Candidate[{idx}] finish_reason={fr}")
        if hasattr(response, "prompt_feedback") and response.prompt_feedback:
            diag_details.append(f"prompt_feedback={response.prompt_feedback}")

        diag_str = " | ".join(diag_details) if diag_details else "No candidate details returned"
        _log_diagnostic("EMPTY_RESPONSE", f"generate_health_response returned empty text in {elapsed:.3f}s | {diag_str}")
        return False, f"⚠️ The AI assistant returned an empty response ({diag_str}). Please rephrase your query."

    except Exception as e:
        elapsed = time.perf_counter() - t0
        _log_diagnostic("EXCEPTION", f"generate_health_response failed in {elapsed:.4f}s: {e}")
        return False, _format_gemini_error(e, model, elapsed_sec=elapsed)


def generate_health_response_stream(
    messages: List[Dict[str, str]],
    *args,
    **kwargs
) -> Generator[str, None, None]:
    """
    Stream an AI health assistant response chunk-by-chunk.
    Provides sub-second Time-To-First-Token (TTFT) for responsive UI.
    """
    client = get_gemini_client()
    if not client:
        yield "⚠️ **Gemini AI Service Unavailable**: `GEMINI_API_KEY` is not configured in `.env`."
        return

    model = get_model_name()
    t0 = time.perf_counter()
    _log_diagnostic("START_STREAM", f"API generate_health_response_stream initiated | Model: {model}")

    try:
        from google.genai import types

        contents = _build_contents_from_messages(messages)
        if not contents:
            yield "Please enter a valid health question to begin."
            return

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.3,
            max_output_tokens=1500,
        )

        response_stream = client.models.generate_content_stream(
            model=model,
            contents=contents,
            config=config,
        )

        has_yielded = False
        ttft = None
        for chunk in response_stream:
            if ttft is None:
                ttft = time.perf_counter() - t0
                _log_diagnostic("TTFT", f"First token chunk received in {ttft:.3f}s")
            if chunk.text:
                has_yielded = True
                yield chunk.text

        total_elapsed = time.perf_counter() - t0
        ttft_str = f"{ttft:.3f}s" if ttft is not None else "N/A"
        _log_diagnostic("STREAM_COMPLETE", f"Total streaming duration: {total_elapsed:.3f}s (TTFT: {ttft_str})")

        if not has_yielded:
            yield "The AI assistant returned an empty response. Please rephrase your query."

    except Exception as e:
        elapsed = time.perf_counter() - t0
        _log_diagnostic("STREAM_EXCEPTION", f"Stream failed in {elapsed:.4f}s: {e}")
        yield _format_gemini_error(e, model, elapsed_sec=elapsed)


def _build_report_prompt_and_config(report_text: str, user_query: str, user_role: str):
    """Build standardized report analysis prompt and configuration."""
    from google.genai import types

    safe_max_chars = 8000
    if len(report_text) > safe_max_chars:
        truncated_text = report_text[:safe_max_chars] + "\n\n[...Report text truncated for processing safety...]"
    else:
        truncated_text = report_text

    if user_role == "provider":
        report_instruction = (
            "You are SmartCare AI, an advanced Clinical Decision Support and Diagnostic Synthesis Assistant. "
            "You are assisting an authorized healthcare professional (physician, clinical specialist, or hospital staff). "
            "Your purpose is to provide structured clinical synthesis, highlight abnormal/out-of-range screening markers, "
            "and suggest differential discussion topics. "
            "MANDATORY CLINICAL RULES: Emphasize that the attending physician retains sole diagnostic and prescriptive authority. "
            "Never replace official clinical judgment."
        )
    else:
        report_instruction = (
            "You are SmartCare AI, an empathetic, safety-focused health information assistant. "
            "Your task is to help a patient understand their laboratory test results and diagnostic findings in plain, accessible, reassuring language. "
            "Structure your response: "
            "1. Plain-English Summary (what test this is) "
            "2. Values Outside Stated Reference Ranges (explain what the marker measures, clarify that reference ranges differ between labs, and that out-of-range does NOT automatically mean disease) "
            "3. Plain definitions of confusing medical jargon "
            "4. Thoughtful questions the patient can ask their doctor. "
            "MANDATORY SAFETY RULES: Do NOT diagnose illnesses. Do NOT prescribe or modify medication. Remind the patient that only their doctor can evaluate test results in the context of their full medical history."
        )

    prompt = (
        f"EXTRACTED MEDICAL REPORT TEXT:\n"
        f"```\n{truncated_text}\n```\n\n"
        f"USER INQUIRY: {user_query.strip()}\n\n"
        f"Please provide structured educational guidance following your medical safety rules."
    )

    config = types.GenerateContentConfig(
        system_instruction=report_instruction,
        temperature=0.3,
        max_output_tokens=1800,
    )

    return prompt, config


def analyze_medical_report(
    report_text: str,
    user_query: str = "Please provide an educational overview of this medical laboratory report.",
    user_role: str = "patient",
    *args,
    **kwargs
) -> Tuple[bool, str]:
    """
    Analyze extracted PDF medical report text using Google Gemini with role-specific framing.
    Non-streaming execution for programmatic and batch calls.
    """
    client = get_gemini_client()
    if not client:
        return False, "⚠️ Gemini AI service unavailable: API key not configured in `.env`."

    model = get_model_name()
    t0 = time.perf_counter()
    _log_diagnostic("START_REPORT_ANALYSIS", f"analyze_medical_report initiated | Model: {model} | Role: {user_role}")

    try:
        prompt, config = _build_report_prompt_and_config(report_text, user_query, user_role)

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

        elapsed = time.perf_counter() - t0
        if response and response.text:
            _log_diagnostic("SUCCESS_REPORT", f"analyze_medical_report completed in {elapsed:.3f}s | Output: {len(response.text)} chars")
            return True, response.text.strip()

        # Detailed candidate inspection if response.text is empty
        diag_details = []
        if hasattr(response, "candidates") and response.candidates:
            for idx, cand in enumerate(response.candidates):
                fr = getattr(cand, "finish_reason", "UNKNOWN")
                diag_details.append(f"Candidate[{idx}] finish_reason={fr}")
        if hasattr(response, "prompt_feedback") and response.prompt_feedback:
            diag_details.append(f"prompt_feedback={response.prompt_feedback}")

        diag_str = " | ".join(diag_details) if diag_details else "No candidate details returned"
        _log_diagnostic("EMPTY_REPORT", f"analyze_medical_report returned empty text in {elapsed:.3f}s | {diag_str}")
        return False, f"⚠️ Could not generate analysis from the report text ({diag_str}). Please try asking a specific question."

    except Exception as e:
        elapsed = time.perf_counter() - t0
        _log_diagnostic("EXCEPTION_REPORT", f"analyze_medical_report failed in {elapsed:.4f}s: {e}")
        return False, _format_gemini_error(e, model, elapsed_sec=elapsed)


def analyze_medical_report_stream(
    report_text: str,
    user_query: str = "Please provide an educational overview of this medical laboratory report.",
    user_role: str = "patient",
    *args,
    **kwargs
) -> Generator[str, None, None]:
    """
    Stream an AI medical report analysis chunk-by-chunk for responsive user experience.
    Provides sub-second Time-To-First-Token (TTFT).
    """
    client = get_gemini_client()
    if not client:
        yield "⚠️ Gemini AI service unavailable: API key not configured in `.env`."
        return

    model = get_model_name()
    t0 = time.perf_counter()
    _log_diagnostic("START_REPORT_STREAM", f"analyze_medical_report_stream initiated | Model: {model} | Role: {user_role}")

    try:
        prompt, config = _build_report_prompt_and_config(report_text, user_query, user_role)

        response_stream = client.models.generate_content_stream(
            model=model,
            contents=prompt,
            config=config,
        )

        has_yielded = False
        ttft = None
        for chunk in response_stream:
            if ttft is None:
                ttft = time.perf_counter() - t0
                _log_diagnostic("TTFT_REPORT", f"First report chunk received in {ttft:.3f}s")
            if chunk.text:
                has_yielded = True
                yield chunk.text

        total_elapsed = time.perf_counter() - t0
        ttft_str = f"{ttft:.3f}s" if ttft is not None else "N/A"
        _log_diagnostic("STREAM_REPORT_COMPLETE", f"Report stream completed in {total_elapsed:.3f}s (TTFT: {ttft_str})")

        if not has_yielded:
            yield "Could not generate analysis from the report text. Please try asking a specific question."

    except Exception as e:
        elapsed = time.perf_counter() - t0
        _log_diagnostic("STREAM_REPORT_EXCEPTION", f"Report stream failed in {elapsed:.4f}s: {e}")
        yield _format_gemini_error(e, model, elapsed_sec=elapsed)
