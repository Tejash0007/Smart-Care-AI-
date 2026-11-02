"""
Detailed Diagnostic Script to inspect Gemini response pipeline:
1. Exact prompt: "Explain blood pressure in 3 simple sentences."
2. Synchronous generate_content() call
3. Inspect complete response object, response.text, candidates, content parts, finish reason, prompt feedback
4. Inspect streaming generate_content_stream() and why it might yield empty/None
"""

import os
import sys
import time
import json
from dotenv import load_dotenv

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

load_dotenv()

def run_diagnostic():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

    print("=" * 70)
    print("🔬 STEP 1: INITIALIZE CLIENT & CHECK CREDENTIALS")
    print(f"Model: {model}")
    print(f"API Key present: {bool(api_key)}")
    print("=" * 70)

    from google import genai
    from google.genai import types

    http_opts = types.HttpOptions(timeout=30000)
    client = genai.Client(api_key=api_key, http_options=http_opts)

    from services.gemini_service import SYSTEM_INSTRUCTION, _build_contents_from_messages

    # Simulated messages exactly as passed from views/patient_ai_assistant.py
    messages = [
        {
            "role": "assistant",
            "content": "Hello! I am your SmartCare AI Health Assistant. How may I support your health learning today?"
        },
        {
            "role": "user",
            "content": "Explain blood pressure in 3 simple sentences."
        }
    ]

    print("\n--- Inspecting _build_contents_from_messages(messages) ---")
    contents = _build_contents_from_messages(messages)
    print(f"Contents count: {len(contents)}")
    for i, c in enumerate(contents):
        print(f"Content[{i}]: role={c.role}, parts={[p.text for p in c.parts]}")

    print("\n" + "=" * 70)
    print("🔬 STEP 2: SYNCHRONOUS generate_content() CALL")
    print("=" * 70)

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        temperature=0.3,
        max_output_tokens=1500,
    )

    t0 = time.perf_counter()
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=config,
    )
    elapsed = time.perf_counter() - t0

    print(f"Call finished in {elapsed:.3f} seconds.")
    print(f"Type of response: {type(response)}")

    # Step 3 & 4: Inspect complete response object
    print("\n--- Inspecting Complete Response Object ---")
    print(f"response.text: {repr(response.text)}")
    print(f"hasattr text: {hasattr(response, 'text')}")
    print(f"len(response.text) if text: {len(response.text) if response.text else 0}")

    print("\n--- Inspecting candidates ---")
    candidates = getattr(response, "candidates", None)
    print(f"Candidates present: {bool(candidates)} (count: {len(candidates) if candidates else 0})")
    if candidates:
        for idx, cand in enumerate(candidates):
            print(f"\nCandidate {idx}:")
            print(f"  finish_reason: {getattr(cand, 'finish_reason', None)}")
            content = getattr(cand, "content", None)
            if content:
                print(f"  content.role: {getattr(content, 'role', None)}")
                parts = getattr(content, "parts", None)
                print(f"  content.parts count: {len(parts) if parts else 0}")
                if parts:
                    for p_idx, part in enumerate(parts):
                        print(f"    part[{p_idx}].text: {repr(getattr(part, 'text', None))}")
            else:
                print("  content: None")
            safety = getattr(cand, "safety_ratings", None)
            print(f"  safety_ratings: {safety}")

    print("\n--- Inspecting prompt_feedback ---")
    pf = getattr(response, "prompt_feedback", None)
    print(f"prompt_feedback: {pf}")

    print("\n--- Inspecting usage_metadata ---")
    usage = getattr(response, "usage_metadata", None)
    print(f"usage_metadata: {usage}")

    print("\n" + "=" * 70)
    print("🔬 STEP 3: TESTING STREAMING generate_content_stream() BEHAVIOR")
    print("=" * 70)
    t0_st = time.perf_counter()
    stream_resp = client.models.generate_content_stream(
        model=model,
        contents=contents,
        config=config,
    )
    print("Stream generator created. Iterating chunks:")
    chunk_list = []
    for c_idx, chunk in enumerate(stream_resp):
        c_text = getattr(chunk, "text", None)
        chunk_list.append(c_text)
        print(f"  Chunk {c_idx}: type={type(chunk)} | text={repr(c_text)}")
    elapsed_st = time.perf_counter() - t0_st
    print(f"Streaming total elapsed: {elapsed_st:.3f}s | Total chunks: {len(chunk_list)}")
    print(f"Joined chunks: {repr(''.join([c for c in chunk_list if c]))}")

if __name__ == "__main__":
    run_diagnostic()
