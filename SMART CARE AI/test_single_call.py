import time
from services.gemini_service import generate_health_response, get_model_name

print("Active model:", get_model_name())
t0 = time.perf_counter()
ok, resp = generate_health_response([{"role": "user", "content": "What is normal blood pressure?"}])
elapsed = time.perf_counter() - t0
print(f"Elapsed: {elapsed:.3f} s")
print(f"Success: {ok}")
print(f"Response: {resp[:200] if resp else None}")
