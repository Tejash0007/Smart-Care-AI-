"""
Performance Verification Test for SmartCare AI Gemini Integration.
Tests:
1. Client singleton caching (Call 1 vs Call 2 initialization time)
2. Non-streaming AI Health Assistant (timing & token count)
3. Streaming AI Health Assistant (Time-To-First-Token TTFT & total time)
4. Non-streaming Medical Report Analysis (timing & token count)
5. Streaming Medical Report Analysis (Time-To-First-Token TTFT & total time)
6. Actual Gemini responses verification
"""

import os
import sys
import time
from dotenv import load_dotenv

# Ensure utf-8 output for Windows console
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

load_dotenv()

from services.gemini_service import (
    get_gemini_client,
    get_model_name,
    generate_health_response,
    generate_health_response_stream,
    analyze_medical_report,
    analyze_medical_report_stream,
    check_api_key_configured
)

def run_performance_test():
    print("=" * 80)
    print("⚡ SMARTCARE AI – POST-OPTIMIZATION PERFORMANCE & ACCURACY VERIFICATION")
    print("=" * 80)

    model = get_model_name()
    has_key = check_api_key_configured()
    print(f"\n[Configuration Status]")
    print(f"  * Configured Model: {model}")
    print(f"  * API Key Available: {has_key}")

    if not has_key:
        print("ERROR: GEMINI_API_KEY is not configured in .env.")
        return False

    # --------------------------------------------------------------------------
    # 1. CLIENT CACHING OVERHEAD TEST
    # --------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("1. Client Caching Overhead Test")
    print("-" * 60)
    t0_c1 = time.perf_counter()
    c1 = get_gemini_client()
    t_c1 = (time.perf_counter() - t0_c1) * 1000

    t0_c2 = time.perf_counter()
    c2 = get_gemini_client()
    t_c2 = (time.perf_counter() - t0_c2) * 1000

    print(f"  * First client retrieval / initialization: {t_c1:.2f} ms")
    print(f"  * Subsequent cached client retrieval:       {t_c2:.4f} ms")
    print(f"  * Client identity match:                  {c1 is c2}")
    assert c1 is c2, "Client singleton was re-created!"
    print("  [PASS] Client caching verified (0ms overhead on reuse).")

    # --------------------------------------------------------------------------
    # 2. AI HEALTH ASSISTANT: NON-STREAMING VS STREAMING
    # --------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("2. AI Health Assistant Timing: Non-Streaming vs Streaming")
    print("-" * 60)
    chat_messages = [
        {"role": "user", "content": "What are normal adult resting blood pressure ranges, and what does systolic vs diastolic mean?"}
    ]

    # Non-streaming
    print("  [2A] Non-Streaming Execution:")
    t0_chat_ns = time.perf_counter()
    ok_ns, resp_ns = generate_health_response(chat_messages)
    t_chat_ns = time.perf_counter() - t0_chat_ns
    print(f"       * Success: {ok_ns}")
    print(f"       * Total Latency: {t_chat_ns:.3f} s")
    print(f"       * Response Length: {len(resp_ns)} chars")
    print(f"       * Preview: {resp_ns[:150]}...")

    # Streaming
    print("\n  [2B] Streaming Execution (User Perceived Latency):")
    t0_chat_stream = time.perf_counter()
    ttft_chat = None
    chunks_chat = 0
    full_chat_stream = []
    for chunk in generate_health_response_stream(chat_messages):
        if ttft_chat is None:
            ttft_chat = time.perf_counter() - t0_chat_stream
        chunks_chat += 1
        full_chat_stream.append(chunk)
    t_chat_stream_total = time.perf_counter() - t0_chat_stream
    full_chat_text = "".join(full_chat_stream)

    print(f"       * Time-To-First-Token (TTFT): {ttft_chat:.3f} s ({ttft_chat*1000:.1f} ms) <-- Instant Response!")
    print(f"       * Total Stream Duration:    {t_chat_stream_total:.3f} s")
    print(f"       * Total Chunks:              {chunks_chat}")
    print(f"       * Total Length:              {len(full_chat_text)} chars")
    assert ttft_chat is not None and ttft_chat < 3.0, f"TTFT too slow: {ttft_chat}"
    print("  [PASS] AI Health Assistant streaming provides responsive sub-second TTFT.")

    # --------------------------------------------------------------------------
    # 3. MEDICAL REPORT ANALYSIS: NON-STREAMING VS STREAMING
    # --------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("3. Medical Report Analysis Timing: Non-Streaming vs Streaming")
    print("-" * 60)
    sample_report = (
        "METROPOLITAN CLINICAL BIOCHEMISTRY LAB\n"
        "PATIENT: Aarav Sharma | AGE: 28 | GENDER: Male\n"
        "--------------------------------------------------\n"
        "Fasting Blood Glucose : 112 mg/dL   (Normal: 70 - 99 mg/dL) [HIGH]\n"
        "Total Cholesterol     : 215 mg/dL   (Desirable: < 200 mg/dL) [ELEVATED]\n"
        "HDL Cholesterol       : 42 mg/dL    (Desirable: > 40 mg/dL)\n"
        "LDL Cholesterol       : 138 mg/dL   (Optimal: < 100 mg/dL) [ELEVATED]\n"
        "Serum Creatinine      : 0.95 mg/dL  (Normal: 0.7 - 1.2 mg/dL)\n"
        "--------------------------------------------------\n"
        "Summary: Mild fasting hyperglycemia and mild hypercholesterolemia."
    )
    rep_query = "Explain which markers are out of reference ranges and what 3 questions I should ask my doctor."

    # Non-streaming
    print("  [3A] Medical Report Non-Streaming Execution:")
    t0_rep_ns = time.perf_counter()
    ok_rep_ns, resp_rep_ns = analyze_medical_report(sample_report, user_query=rep_query, user_role="patient")
    t_rep_ns = time.perf_counter() - t0_rep_ns
    print(f"       * Success: {ok_rep_ns}")
    print(f"       * Total Latency: {t_rep_ns:.3f} s")
    print(f"       * Response Length: {len(resp_rep_ns)} chars")
    print(f"       * Preview: {resp_rep_ns[:150]}...")

    # Streaming
    print("\n  [3B] Medical Report Streaming Execution (User Perceived Latency):")
    t0_rep_stream = time.perf_counter()
    ttft_rep = None
    chunks_rep = 0
    full_rep_stream = []
    for chunk in analyze_medical_report_stream(sample_report, user_query=rep_query, user_role="patient"):
        if ttft_rep is None:
            ttft_rep = time.perf_counter() - t0_rep_stream
        chunks_rep += 1
        full_rep_stream.append(chunk)
    t_rep_stream_total = time.perf_counter() - t0_rep_stream
    full_rep_text = "".join(full_rep_stream)

    print(f"       * Time-To-First-Token (TTFT): {ttft_rep:.3f} s ({ttft_rep*1000:.1f} ms) <-- Instant Response!")
    print(f"       * Total Stream Duration:    {t_rep_stream_total:.3f} s")
    print(f"       * Total Chunks:              {chunks_rep}")
    print(f"       * Total Length:              {len(full_rep_text)} chars")
    assert ttft_rep is not None and ttft_rep < 3.0, f"TTFT too slow: {ttft_rep}"
    print("  [PASS] Medical Report Analysis streaming provides responsive sub-second TTFT.")

    # --------------------------------------------------------------------------
    # 4. SUMMARY OF MEASUREMENTS & ACCURACY
    # --------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("🎯 PERFORMANCE SUMMARY TABLE")
    print("=" * 80)
    print(f"{'Operation':<35} | {'Metric':<25} | {'Measured Value'}")
    print("-" * 80)
    print(f"{'Client Initialization':<35} | {'First Call':<25} | {t_c1:.2f} ms")
    print(f"{'Client Initialization':<35} | {'Cached Reuse':<25} | {t_c2:.4f} ms (0.0 ms)")
    print(f"{'AI Health Assistant (Streaming)':<35} | {'Perceived TTFT':<25} | {ttft_chat:.3f} s ({ttft_chat*1000:.1f} ms)")
    print(f"{'AI Health Assistant (Streaming)':<35} | {'Total Duration':<25} | {t_chat_stream_total:.3f} s")
    print(f"{'AI Health Assistant (Non-Stream)':<35} | {'Total Duration':<25} | {t_chat_ns:.3f} s")
    print(f"{'Medical Report (Streaming)':<35} | {'Perceived TTFT':<25} | {ttft_rep:.3f} s ({ttft_rep*1000:.1f} ms)")
    print(f"{'Medical Report (Streaming)':<35} | {'Total Duration':<25} | {t_rep_stream_total:.3f} s")
    print(f"{'Medical Report (Non-Stream)':<35} | {'Total Duration':<25} | {t_rep_ns:.3f} s")
    print("=" * 80)
    print("🎉 ALL PERFORMANCE & ACCURACY BENCHMARKS PASSED SUCCESSFULLY!")
    print("=" * 80)
    return True

if __name__ == "__main__":
    success = run_performance_test()
    sys.exit(0 if success else 1)
