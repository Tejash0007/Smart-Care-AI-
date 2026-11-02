"""
Isolated Gemini Performance Diagnostic Tool for SmartCare AI.
Bypasses Streamlit and SQLite to isolate:
- Client initialization overhead
- Model resolution and availability
- Prompt / System instruction overhead
- Time to first chunk (TTFT) vs total generation time (streaming vs non-streaming)
- Token counts (input/output)
- PDF extraction timing
- Exact number of API calls made (identifying fallback retries)
"""

import os
import sys
import time
import io
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
    get_api_key,
    get_model_name,
    SYSTEM_INSTRUCTION,
    SUPPORTED_MODELS,
    DEFAULT_MODEL
)
from services.pdf_service import extract_text_from_pdf
from reportlab.pdfgen import canvas

def run_diagnostic():
    print("=" * 80)
    print("🔬 SMARTCARE AI – ISOLATED GEMINI PERFORMANCE & TIMING DIAGNOSTIC")
    print("=" * 80)

    api_key = get_api_key()
    configured_model = get_model_name()
    print(f"\n[Environment Diagnostic]")
    print(f"  * Configured Model in .env: {os.getenv('GEMINI_MODEL')}")
    print(f"  * Active Model from get_model_name(): {configured_model}")
    print(f"  * Candidate Models in fallback list: {SUPPORTED_MODELS}")
    print(f"  * API Key configured: {'YES (Valid Length)' if api_key and len(api_key) > 10 else 'NO'}")

    if not api_key:
        print("ERROR: GEMINI_API_KEY is not configured in .env.")
        return

    from google import genai
    from google.genai import types

    # --------------------------------------------------------------------------
    # 1. CLIENT INITIALIZATION TIMING
    # --------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("TEST 1: Client Initialization Timing")
    print("-" * 60)
    t0_client = time.perf_counter()
    http_opts = types.HttpOptions(timeout=15000)
    client = genai.Client(api_key=api_key, http_options=http_opts)
    t_client_init = (time.perf_counter() - t0_client) * 1000
    print(f"  * Client Initialization Time: {t_client_init:.2f} ms")

    # --------------------------------------------------------------------------
    # 2. MODEL AVAILABILITY AUDIT
    # --------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("TEST 2: Model Availability & Listing")
    print("-" * 60)
    try:
        t0_models = time.perf_counter()
        available_models = []
        for m in client.models.list():
            # Only collect relevant generative models
            m_name = m.name.replace("models/", "") if hasattr(m, 'name') else str(m)
            if "flash" in m_name or "gemini" in m_name:
                available_models.append(m_name)
        t_models_fetch = (time.perf_counter() - t0_models) * 1000
        print(f"  * Models List API Call Time: {t_models_fetch:.2f} ms")
        print(f"  * Total Gemini models found: {len(available_models)}")
        
        # Check our models
        for check_m in [configured_model] + SUPPORTED_MODELS:
            is_avail = check_m in available_models or any(check_m in x for x in available_models)
            print(f"    - '{check_m}': {'AVAILABLE' if is_avail else 'NOT IN MODELS LIST'}")
    except Exception as e:
        print(f"  * Could not list models: {e}")

    # --------------------------------------------------------------------------
    # 3. TEST A: SIMPLE SHORT TEXT PROMPT (Direct model test)
    # --------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print(f"TEST 3: Simple Short Text Prompt ('Hello, respond with ONE word: OK')")
    print(f"Target Model: {configured_model}")
    print("-" * 60)

    for test_model in [configured_model, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]:
        print(f"\n  >> Probing Model: '{test_model}'...")
        req_start = time.perf_counter()
        try:
            resp = client.models.generate_content(
                model=test_model,
                contents="Hello, respond with ONE word: OK",
                config=types.GenerateContentConfig(max_output_tokens=10)
            )
            elapsed = time.perf_counter() - req_start
            text = resp.text.strip() if resp and resp.text else "(empty)"
            in_tokens = resp.usage_metadata.prompt_token_count if hasattr(resp, 'usage_metadata') and resp.usage_metadata else "N/A"
            out_tokens = resp.usage_metadata.candidates_token_count if hasattr(resp, 'usage_metadata') and resp.usage_metadata else "N/A"
            print(f"     [SUCCESS] Response: '{text}'")
            print(f"     Elapsed Time: {elapsed:.3f} s ({elapsed*1000:.1f} ms)")
            print(f"     Input Tokens: {in_tokens} | Output Tokens: {out_tokens}")
            break
        except Exception as e:
            elapsed = time.perf_counter() - req_start
            print(f"     [FAILED] in {elapsed:.3f} s: {e}")

    # --------------------------------------------------------------------------
    # 4. TEST B: NORMAL HEALTHCARE QUESTION (With Full System Instruction)
    # --------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("TEST 4: Normal Healthcare Question (Non-Streaming vs Streaming)")
    print("Prompt: 'What are normal adult resting blood pressure ranges, and what does systolic vs diastolic mean?'")
    print("-" * 60)

    # 4A. Non-Streaming
    print("\n  [4A] Non-Streaming Request:")
    t_req_start = time.perf_counter()
    try:
        config_full = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.3,
            max_output_tokens=1500,
        )
        resp_full = client.models.generate_content(
            model=configured_model,
            contents="What are normal adult resting blood pressure ranges, and what does systolic vs diastolic mean?",
            config=config_full
        )
        t_nonstream_total = time.perf_counter() - t_req_start
        in_tok = resp_full.usage_metadata.prompt_token_count if hasattr(resp_full, 'usage_metadata') and resp_full.usage_metadata else "N/A"
        out_tok = resp_full.usage_metadata.candidates_token_count if hasattr(resp_full, 'usage_metadata') and resp_full.usage_metadata else "N/A"
        print(f"     Total Non-Streaming Time: {t_nonstream_total:.3f} s")
        print(f"     Input Tokens: {in_tok} | Output Tokens: {out_tok}")
        print(f"     Output Length: {len(resp_full.text)} chars")
    except Exception as e:
        t_nonstream_total = time.perf_counter() - t_req_start
        print(f"     Failed in {t_nonstream_total:.3f} s: {e}")

    # 4B. Streaming (Measuring TTFT - Time To First Token)
    print("\n  [4B] Streaming Request (Measuring TTFT vs Total Time):")
    t_stream_start = time.perf_counter()
    ttft = None
    chunks_count = 0
    total_chars = 0
    try:
        stream_resp = client.models.generate_content_stream(
            model=configured_model,
            contents="What are normal adult resting blood pressure ranges, and what does systolic vs diastolic mean?",
            config=config_full
        )
        for chunk in stream_resp:
            if ttft is None:
                ttft = time.perf_counter() - t_stream_start
            chunks_count += 1
            if chunk.text:
                total_chars += len(chunk.text)
        t_stream_total = time.perf_counter() - t_stream_start
        print(f"     Time to First Chunk (TTFT): {ttft:.3f} s ({ttft*1000:.1f} ms) <-- Perceived Latency!")
        print(f"     Total Streaming Time     : {t_stream_total:.3f} s")
        print(f"     Total Chunks Received     : {chunks_count}")
        print(f"     Total Output Chars        : {total_chars}")
    except Exception as e:
        t_stream_total = time.perf_counter() - t_stream_start
        print(f"     Streaming Failed in {t_stream_total:.3f} s: {e}")

    # --------------------------------------------------------------------------
    # 5. TEST C: PDF EXTRACTION TIMING
    # --------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("TEST 5: PDF Text Extraction Overhead Timing")
    print("-" * 60)
    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf)
    c.drawString(100, 750, "SmartCare Clinical Diagnostic Report")
    c.drawString(100, 730, "Patient: Aarav Sharma | Age: 28 | Gender: Male")
    c.drawString(100, 710, "Fasting Blood Glucose: 112 mg/dL (Normal: 70 - 99 mg/dL) [HIGH]")
    c.drawString(100, 690, "Total Cholesterol: 215 mg/dL (Desirable: < 200 mg/dL)")
    c.drawString(100, 670, "HDL Cholesterol: 42 mg/dL (Desirable: > 40 mg/dL)")
    c.drawString(100, 650, "Serum Creatinine: 0.95 mg/dL (Normal: 0.7 - 1.2 mg/dL)")
    c.save()
    pdf_buf.seek(0)
    pdf_buf.name = "Test_Report.pdf"
    pdf_buf.size = len(pdf_buf.getvalue())

    t0_pdf = time.perf_counter()
    pdf_ok, extracted_txt, p_cnt = extract_text_from_pdf(pdf_buf)
    t_pdf = (time.perf_counter() - t0_pdf) * 1000
    print(f"  * PDF Local Extraction Time: {t_pdf:.2f} ms")
    print(f"  * Characters Extracted: {len(extracted_txt)} across {p_cnt} page(s)")

    # --------------------------------------------------------------------------
    # 6. TEST D: MEDICAL REPORT ANALYSIS TIMING (Non-Streaming vs Streaming)
    # --------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("TEST 6: Medical Report Analysis Timing")
    print("-" * 60)
    report_instruction = (
        "You are SmartCare AI, an empathetic, safety-focused medical educational assistant. "
        "Explain test results in clear, accessible language without diagnosing or prescribing."
    )
    report_prompt = (
        f"EXTRACTED MEDICAL REPORT TEXT:\n```\n{extracted_txt}\n```\n\n"
        f"USER INQUIRY: Explain which markers are out of range and give 3 questions for my doctor.\n\n"
        f"Please provide structured educational guidance following medical safety rules."
    )
    config_rep = types.GenerateContentConfig(
        system_instruction=report_instruction,
        temperature=0.3,
        max_output_tokens=1800,
    )

    # 6A. Non-streaming
    print("\n  [6A] Medical Report Non-Streaming:")
    t_rep_start = time.perf_counter()
    try:
        rep_resp = client.models.generate_content(
            model=configured_model,
            contents=report_prompt,
            config=config_rep
        )
        t_rep_nonstream = time.perf_counter() - t_rep_start
        in_tok_rep = rep_resp.usage_metadata.prompt_token_count if hasattr(rep_resp, 'usage_metadata') and rep_resp.usage_metadata else "N/A"
        out_tok_rep = rep_resp.usage_metadata.candidates_token_count if hasattr(rep_resp, 'usage_metadata') and rep_resp.usage_metadata else "N/A"
        print(f"     Total Non-Streaming Report Time: {t_rep_nonstream:.3f} s")
        print(f"     Input Tokens: {in_tok_rep} | Output Tokens: {out_tok_rep}")
        print(f"     Output Length: {len(rep_resp.text)} chars")
    except Exception as e:
        t_rep_nonstream = time.perf_counter() - t_rep_start
        print(f"     Report Analysis Failed in {t_rep_nonstream:.3f} s: {e}")

    # 6B. Streaming
    print("\n  [6B] Medical Report Streaming (TTFT):")
    t_rep_stream_start = time.perf_counter()
    ttft_rep = None
    rep_chunks = 0
    try:
        stream_rep_resp = client.models.generate_content_stream(
            model=configured_model,
            contents=report_prompt,
            config=config_rep
        )
        for chunk in stream_rep_resp:
            if ttft_rep is None:
                ttft_rep = time.perf_counter() - t_rep_stream_start
            rep_chunks += 1
        t_rep_stream_total = time.perf_counter() - t_rep_stream_start
        print(f"     Time to First Chunk (TTFT): {ttft_rep:.3f} s ({ttft_rep*1000:.1f} ms) <-- Perceived Latency!")
        print(f"     Total Streaming Time     : {t_rep_stream_total:.3f} s")
        print(f"     Total Chunks Received     : {rep_chunks}")
    except Exception as e:
        t_rep_stream_total = time.perf_counter() - t_rep_stream_start
        print(f"     Streaming Failed in {t_rep_stream_total:.3f} s: {e}")

    # --------------------------------------------------------------------------
    # 7. PROBING THE APPLICATION's EXACT `generate_health_response` FUNCTION
    # --------------------------------------------------------------------------
    print("\n" + "-" * 60)
    print("TEST 7: Probing the application's actual generate_health_response()")
    print("-" * 60)
    from services.gemini_service import generate_health_response
    t_app_start = time.perf_counter()
    app_ok, app_resp = generate_health_response([
        {"role": "user", "content": "What are normal adult blood pressure ranges?"}
    ])
    t_app_total = time.perf_counter() - t_app_start
    print(f"  * Application Function Execution Time: {t_app_total:.3f} s")
    print(f"  * Success: {app_ok}")
    print(f"  * Response Length: {len(app_resp)} characters")

    print("\n" + "=" * 80)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    run_diagnostic()
