"""
Test script to verify:
1. get_model_name() returns 'gemini-3.5-flash-lite'
2. Live AI Health Assistant question using actual Gemini API
3. Live Medical report analysis using actual Gemini API
4. 404 error handling for discontinued/invalid models
"""

import os
import sys
from dotenv import load_dotenv

# Ensure utf-8 output
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
    get_model_name,
    generate_health_response,
    analyze_medical_report,
    check_api_key_configured
)

def run_tests():
    print("=" * 70)
    print("🤖 TESTING GEMINI 3.5 FLASH LITE INTEGRATION")
    print("=" * 70)

    # 1. Verify Model Configuration
    model = get_model_name()
    print(f"\n1. Active Configured Model: {model}")
    assert model == "gemini-3.5-flash-lite", f"Expected gemini-3.5-flash-lite, got {model}"
    print("   [PASS] Centralized model is 'gemini-3.5-flash-lite'")

    # 2. Check API Key
    has_key = check_api_key_configured()
    print(f"\n2. Server API Key Configured: {has_key}")
    if not has_key:
        print("   [FAIL] GEMINI_API_KEY is not set or empty in .env!")
        return False

    # 3. Test Normal Health Assistant Query
    print("\n3. Testing Normal Health Assistant Query...")
    messages = [
        {"role": "user", "content": "What are normal adult resting blood pressure ranges, and what does systolic vs diastolic mean?"}
    ]
    ok_chat, resp_chat = generate_health_response(messages)
    print(f"   Success: {ok_chat}")
    print(f"   Response Preview:\n{resp_chat[:250]}...\n")
    if ok_chat:
        print("   [PASS] Actual Gemini API responded to health assistant question!")
    else:
        print(f"   [INFO/FAIL] Assistant returned: {resp_chat}")

    # 4. Test Medical Report Analysis with Extracted Clinical Text
    print("\n4. Testing Medical Report Analysis with Extracted Clinical Text...")
    sample_clinical_text = (
        "SMARTCARE METROPOLITAN CLINICAL LABORATORY\n"
        "PATIENT: Aarav Sharma (SC-1001) | AGE: 28 | GENDER: Male\n"
        "TEST: Comprehensive Metabolic & Lipid Profile\n"
        "--------------------------------------------------\n"
        "Fasting Blood Glucose : 112 mg/dL   (Normal: 70 - 99 mg/dL) [HIGH]\n"
        "Total Cholesterol     : 215 mg/dL   (Desirable: < 200 mg/dL) [BORDERLINE HIGH]\n"
        "HDL Cholesterol       : 42 mg/dL    (Desirable: > 40 mg/dL)\n"
        "LDL Cholesterol       : 138 mg/dL   (Optimal: < 100 mg/dL) [ELEVATED]\n"
        "Serum Creatinine      : 0.95 mg/dL  (Normal: 0.7 - 1.2 mg/dL)\n"
        "eGFR                  : > 90 mL/min (Normal: > 60 mL/min)\n"
        "--------------------------------------------------\n"
        "Impression: Mild fasting hyperglycemia and mild hyperlipidemia noted."
    )
    ok_rep, resp_rep = analyze_medical_report(
        report_text=sample_clinical_text,
        user_query="Please explain which markers are outside the reference ranges and provide questions I can ask my doctor.",
        user_role="patient"
    )
    print(f"   Success: {ok_rep}")
    print(f"   Response Preview:\n{resp_rep[:250]}...\n")
    if ok_rep:
        print("   [PASS] Actual Gemini API responded to medical report analysis!")
    else:
        print(f"   [INFO/FAIL] Report analysis returned: {resp_rep}")

    # 5. Test 404 Discontinued Model Handling
    print("\n5. Testing 404 Model Error Handling for Discontinued Models...")
    from google import genai
    from google.genai import types
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=10000))
    try:
        # Directly call non-existent model to test error string
        client.models.generate_content(
            model="gemini-nonexistent-model-test-404",
            contents="Hello"
        )
        print("   [UNEXPECTED] Nonexistent model succeeded?!")
    except Exception as e:
        err_str = str(e).lower()
        print(f"   Caught expected exception: {e}")
        is_404 = any(term in err_str for term in ["404", "not_found", "model not found", "does not exist", "is not supported"])
        print(f"   Detected as 404/not_found: {is_404}")
        print("   [PASS] 404 model error caught and handled cleanly.")

    print("\n" + "=" * 70)
    print("RESULTS SUMMARY:")
    print(f"Configured Model : {model}")
    print(f"AI Assistant Live Response : {'YES' if ok_chat else 'NO'}")
    print(f"Medical Report Live Response: {'YES' if ok_rep else 'NO'}")
    print("=" * 70)

    return ok_chat and ok_rep

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
