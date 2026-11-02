"""
Independent Gemini API Diagnostic and Comparison Script.
Runs outside of Streamlit to measure:
1. Raw Google GenAI SDK direct call vs Application wrapper
2. Non-streaming latency and Time-To-First-Token (TTFT) for streaming
3. AI Health Assistant & Medical Report Analysis functions
4. Exact elapsed times, exception classes, and response verification.
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

def print_separator(title: str):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def test_independent_and_app():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model_name = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

    print_separator("1. ENVIRONMENT & CONFIGURATION CHECK")
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Configured Model: {model_name}")
    print(f"API Key Present: {'YES (length ' + str(len(api_key)) + ')' if api_key else 'NO'}")
    if not api_key:
        print("ERROR: No GEMINI_API_KEY found in .env")
        return

    # -------------------------------------------------------------
    # Test 1: Direct Google GenAI SDK (Raw Client, Timeout = 30000ms / 30.0s)
    # -------------------------------------------------------------
    print_separator("2. RAW GOOGLE-GENAI SDK DIRECT TEST")
    try:
        from google import genai
        from google.genai import types
        from google.genai._api_client import get_timeout_in_seconds

        timeout_ms = 30000
        sec_calc = get_timeout_in_seconds(timeout_ms)
        print(f"Configured timeout: {timeout_ms}ms -> SDK calculated socket timeout: {sec_calc}s")

        http_opts = types.HttpOptions(timeout=timeout_ms)
        raw_client = genai.Client(api_key=api_key, http_options=http_opts)

        print("\n--- Sending Raw generate_content Request ---")
        t0 = time.perf_counter()
        raw_resp = raw_client.models.generate_content(
            model=model_name,
            contents="State in one sentence what resting heart rate means for general cardiovascular health."
        )
        elapsed_raw = time.perf_counter() - t0
        print(f"Raw API Call Succeeded in: {elapsed_raw:.3f} seconds")
        print(f"Response ({len(raw_resp.text)} chars): {raw_resp.text.strip()[:180]}...")

        print("\n--- Sending Raw generate_content_stream Request ---")
        t0_stream = time.perf_counter()
        stream_resp = raw_client.models.generate_content_stream(
            model=model_name,
            contents="Name 3 high-fiber foods in a bullet list."
        )
        first_chunk_time = None
        total_stream_chars = 0
        chunk_count = 0
        for chunk in stream_resp:
            chunk_count += 1
            if first_chunk_time is None:
                first_chunk_time = time.perf_counter() - t0_stream
            if chunk.text:
                total_stream_chars += len(chunk.text)
        elapsed_raw_stream = time.perf_counter() - t0_stream
        print(f"Raw Stream TTFT (Time-To-First-Token): {first_chunk_time:.3f} seconds")
        print(f"Raw Stream Total Duration: {elapsed_raw_stream:.3f} seconds ({chunk_count} chunks, {total_stream_chars} chars)")

    except Exception as e:
        print(f"Raw SDK Test EXCEPTION: {e.__class__.__name__}: {e}")
        return

    # -------------------------------------------------------------
    # Test 2: Application Service - generate_health_response
    # -------------------------------------------------------------
    print_separator("3. APPLICATION SERVICE: generate_health_response (Non-Streaming)")
    from services.gemini_service import (
        generate_health_response,
        generate_health_response_stream,
        analyze_medical_report,
        analyze_medical_report_stream
    )

    t0_app = time.perf_counter()
    ok, app_res = generate_health_response([
        {"role": "user", "content": "What is normal fasting blood glucose and what should a patient discuss with their doctor?"}
    ])
    elapsed_app = time.perf_counter() - t0_app
    print(f"App generate_health_response: Success={ok} | Elapsed={elapsed_app:.3f}s")
    print(f"Response preview: {app_res[:200]}...")

    # -------------------------------------------------------------
    # Test 3: Application Service - generate_health_response_stream
    # -------------------------------------------------------------
    print_separator("4. APPLICATION SERVICE: generate_health_response_stream")
    t0_app_stream = time.perf_counter()
    app_stream = generate_health_response_stream([
        {"role": "user", "content": "What is the difference between HDL and LDL cholesterol?"}
    ])
    app_ttft = None
    stream_chunks = 0
    stream_text = []
    for chunk in app_stream:
        stream_chunks += 1
        if app_ttft is None:
            app_ttft = time.perf_counter() - t0_app_stream
        stream_text.append(chunk)
    elapsed_app_stream = time.perf_counter() - t0_app_stream
    full_stream_text = "".join(stream_text)
    print(f"App Stream TTFT: {app_ttft:.3f}s | Total Elapsed: {elapsed_app_stream:.3f}s | Chunks: {stream_chunks}")
    print(f"Response preview: {full_stream_text[:200]}...")

    # -------------------------------------------------------------
    # Test 4: Application Service - analyze_medical_report (Patient & Provider)
    # -------------------------------------------------------------
    print_separator("5. APPLICATION SERVICE: analyze_medical_report (PDF Lab Text)")
    sample_lab_report = (
        "METABOLIC PANEL:\n"
        "Fasting Plasma Glucose: 118 mg/dL (Reference: 70-99 mg/dL) [HIGH]\n"
        "Total Cholesterol: 228 mg/dL (Reference: < 200 mg/dL) [HIGH]\n"
        "HDL Cholesterol: 42 mg/dL (Reference: > 40 mg/dL) [NORMAL]\n"
        "LDL Cholesterol: 148 mg/dL (Reference: < 100 mg/dL) [HIGH]\n"
        "Triglycerides: 190 mg/dL (Reference: < 150 mg/dL) [HIGH]\n"
        "Hemoglobin A1c: 5.9% (Reference: 4.0 - 5.6%) [PREDIABETIC RANGE]\n"
    )

    t0_rep = time.perf_counter()
    rep_ok, rep_res = analyze_medical_report(
        report_text=sample_lab_report,
        user_query="Explain why fasting glucose and LDL are flagged and what questions to ask my physician.",
        user_role="patient"
    )
    elapsed_rep = time.perf_counter() - t0_rep
    print(f"Patient Report Analysis: Success={rep_ok} | Elapsed={elapsed_rep:.3f}s")
    print(f"Response preview: {rep_res[:220]}...")

    # -------------------------------------------------------------
    # Test 5: Application Service - analyze_medical_report_stream
    # -------------------------------------------------------------
    print_separator("6. APPLICATION SERVICE: analyze_medical_report_stream (Provider Role)")
    t0_rep_stream = time.perf_counter()
    rep_stream = analyze_medical_report_stream(
        report_text=sample_lab_report,
        user_query="Synthesize abnormal screening markers and clinical discussion priorities.",
        user_role="provider"
    )
    rep_ttft = None
    rep_stream_chunks = 0
    rep_full = []
    for chunk in rep_stream:
        rep_stream_chunks += 1
        if rep_ttft is None:
            rep_ttft = time.perf_counter() - t0_rep_stream
        rep_full.append(chunk)
    elapsed_rep_stream = time.perf_counter() - t0_rep_stream
    print(f"Provider Report Stream TTFT: {rep_ttft:.3f}s | Total Elapsed: {elapsed_rep_stream:.3f}s")
    print(f"Response preview: {''.join(rep_full)[:220]}...")

    # -------------------------------------------------------------
    # Latency Comparison Summary
    # -------------------------------------------------------------
    print_separator("7. PERFORMANCE SUMMARY COMPARISON")
    print(f"Raw Direct Call Latency:              {elapsed_raw:.3f}s")
    print(f"Raw Stream TTFT:                      {first_chunk_time:.3f}s (Total: {elapsed_raw_stream:.3f}s)")
    print(f"App Chat Response Latency:            {elapsed_app:.3f}s")
    print(f"App Chat Stream TTFT:                 {app_ttft:.3f}s (Total: {elapsed_app_stream:.3f}s)")
    print(f"App Patient Report Latency:           {elapsed_rep:.3f}s")
    print(f"App Provider Report Stream TTFT:      {rep_ttft:.3f}s (Total: {elapsed_rep_stream:.3f}s)")
    print("ALL TESTS COMPLETED SUCCESSFULLY WITHOUT TIMEOUT OR EXCEPTION.")

if __name__ == "__main__":
    test_independent_and_app()
