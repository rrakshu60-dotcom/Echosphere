"""
Comprehensive Test Suite for EchoSphere AI Microservices & Multi-Model Routing
Tests all AI endpoints:
  1. GET  /api/v1/ai/status
  2. GET  /api/v1/ai/router/status
  3. POST /api/v1/ai/expand (AI Expand Text)
  4. POST /api/v1/ai/draft (AI Announcement Draft)
  5. POST /api/v1/ai/grammar (AI Tone & Grammar Polish)
  6. POST /api/v1/ai/summarize (AI Summarizer)
  7. POST /api/v1/ai/priority (Campus ML Priority & Category)
  8. POST /api/v1/ai/spam (Institutional Spam Guardrails)
  9. POST /api/v1/ai/validate (Announcement Completeness Checklist)
  10. Direct AIService Python Unit Tests
"""

import sys
import os
import time
import json
import requests

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BACKEND_URL = "http://127.0.0.1:8000"
QWEN_URL = "http://127.0.0.1:8009"

passed = 0
failed = 0

def test(name, condition, extra=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {name} {extra}")
    else:
        failed += 1
        print(f"  [FAIL] {name} {extra}")

def wait_for_services(timeout=45):
    print("Waiting for Qwen (port 8009) and Backend (port 8000) services to be ready...")
    t0 = time.time()
    qwen_ready = False
    backend_ready = False

    while time.time() - t0 < timeout:
        if not qwen_ready:
            try:
                r = requests.get(f"{QWEN_URL}/health", timeout=1.0)
                if r.status_code == 200 and r.json().get("status") == "ready":
                    qwen_ready = True
                    print(f"  -> Qwen 2.5 3B GPU ready in {time.time()-t0:.1f}s")
            except Exception:
                pass

        if not backend_ready:
            try:
                r = requests.get(f"{BACKEND_URL}/health", timeout=1.0)
                if r.status_code == 200:
                    backend_ready = True
                    print(f"  -> Backend API ready in {time.time()-t0:.1f}s")
            except Exception:
                pass

        if qwen_ready and backend_ready:
            break
        time.sleep(1.5)

    if not backend_ready:
        print("  [WARN] Backend not reachable at http://127.0.0.1:8000, continuing with direct Python service tests.")

def run_tests():
    global passed, failed

    wait_for_services(timeout=45)

    print("\n" + "=" * 65)
    print("  ECHOSPHERE AI MICROSERVICES VERIFICATION SUITE")
    print("=" * 65)

    # -------------------------------------------------------------
    # SUITE 1: AI Engine & Router Status
    # -------------------------------------------------------------
    print("\n--- SUITE 1: System Status & Model Availability ---")
    try:
        r = requests.get(f"{BACKEND_URL}/api/v1/ai/status", timeout=5)
        test("Status endpoint returned 200", r.status_code == 200)
        data = r.json()
        test("Qwen model recognized", "Qwen 2.5 3B" in data.get("engine", "") or data.get("is_qwen_available") is True)
        test("Cloudflare LLaMA available or configured", "is_cloudflare_available" in data)
        test("Campus ML local engine available", data.get("local_ml_available") is True)
        print(f"       Engine: {data.get('engine')}")
        print(f"       Qwen GPU Active: {data.get('is_qwen_available')}, CF Active: {data.get('is_cloudflare_available')}")
    except Exception as e:
        test("Status endpoint accessible", False, str(e))

    try:
        r = requests.get(f"{BACKEND_URL}/api/v1/ai/router/status", timeout=5)
        test("Router status returned 200", r.status_code == 200)
        r_data = r.json()
        providers = r_data.get("active_providers", {})
        test("fine_tuned_qwen registered in router", "fine_tuned_qwen" in providers)
        test("cloudflare registered in router", "cloudflare" in providers)
    except Exception as e:
        test("Router status endpoint accessible", False, str(e))

    # -------------------------------------------------------------
    # SUITE 2: AI Expand Text (/api/v1/ai/expand)
    # -------------------------------------------------------------
    print("\n--- SUITE 2: AI Text Expand Microservice ---")
    memo = "fee payment deadline extended to march 25 with no penalty"
    try:
        t0 = time.time()
        r = requests.post(
            f"{BACKEND_URL}/api/v1/ai/expand",
            json={"text": memo, "category": "Examinations"},
            timeout=10
        )
        duration = time.time() - t0
        test("Expand endpoint returned 200", r.status_code == 200)
        exp_data = r.json()
        expanded_text = exp_data.get("expanded_text", "")
        test("Expanded text is descriptive (> 80 chars)", len(expanded_text) > 80, f"({len(expanded_text)} chars)")
        test("Expanded text completes under 4.0 seconds", duration < 4.0, f"({duration:.2f}s)")
        test("Clean Markdown (no literal **** clutter)", "****" not in expanded_text)
        print(f"       Generated Notice Sample:\n       {expanded_text[:140]}...")
    except Exception as e:
        test("Expand endpoint accessible", False, str(e))

    # -------------------------------------------------------------
    # SUITE 3: AI Announcement Draft (/api/v1/ai/draft)
    # -------------------------------------------------------------
    print("\n--- SUITE 3: AI Announcement Draft Microservice ---")
    topic = "Campus Placement Drive for Google and Microsoft"
    try:
        t0 = time.time()
        r = requests.post(
            f"{BACKEND_URL}/api/v1/ai/draft",
            json={"topic": topic, "category": "Placements", "target_role": "STUDENT", "department": "CSE"},
            timeout=10
        )
        duration = time.time() - t0
        test("Draft endpoint returned 200", r.status_code == 200)
        draft_data = r.json()
        test("Draft returns non-empty title", bool(draft_data.get("title")))
        test("Draft returns formal content (> 100 chars)", len(draft_data.get("content", "")) > 100)
        test("Draft returns valid suggested_priority", draft_data.get("suggested_priority") in ["NORMAL", "HIGH", "EMERGENCY"])
        test("Draft completes in reasonable time (< 7.0s)", duration < 7.0, f"({duration:.2f}s)")
        print(f"       Draft Title: {draft_data.get('title')}")
        print(f"       Suggested Priority: {draft_data.get('suggested_priority')}")
    except Exception as e:
        test("Draft endpoint accessible", False, str(e))

    # -------------------------------------------------------------
    # SUITE 4: AI Grammar & Tone Polish (/api/v1/ai/grammar)
    # -------------------------------------------------------------
    print("\n--- SUITE 4: AI Grammar & Tone Polish Microservice ---")
    raw_bad_grammar = "all student must submit project tomorrow or else you fail"
    try:
        t0 = time.time()
        r = requests.post(
            f"{BACKEND_URL}/api/v1/ai/grammar",
            json={"text": raw_bad_grammar},
            timeout=10
        )
        duration = time.time() - t0
        test("Grammar endpoint returned 200", r.status_code == 200)
        gram_data = r.json()
        corrected = gram_data.get("corrected_text", "")
        improvements = gram_data.get("improvements", [])
        test("Grammar correction produced", bool(corrected) and corrected != raw_bad_grammar)
        test("Improvements listed", isinstance(improvements, list) and len(improvements) > 0)
        test("Grammar check completes under 4.0 seconds", duration < 4.0, f"({duration:.2f}s)")
        print(f"       Corrected: {corrected}")
        print(f"       Improvements: {improvements}")
    except Exception as e:
        test("Grammar endpoint accessible", False, str(e))

    # -------------------------------------------------------------
    # SUITE 5: AI Summarizer (/api/v1/ai/summarize)
    # -------------------------------------------------------------
    print("\n--- SUITE 5: AI Summarize Microservice ---")
    long_circular = (
        "All eighth semester computer science and engineering students are hereby informed that the final year "
        "major project phase-2 viva voce examinations will be conducted from October 15 to October 18 in the Turing Lab. "
        "External examiners from premier research institutions will evaluate the working prototypes. "
        "Students must bring three hard-bound copies of their dissertation thesis along with verified guide signatures."
    )
    try:
        t0 = time.time()
        r = requests.post(
            f"{BACKEND_URL}/api/v1/ai/summarize",
            json={"content": long_circular},
            timeout=10
        )
        duration = time.time() - t0
        test("Summarize endpoint returned 200", r.status_code == 200)
        sum_data = r.json()
        summary = sum_data.get("summary", "")
        test("Summary is concise (< 260 chars)", len(summary) < 260 and len(summary) > 15, f"({len(summary)} chars)")
        test("Summary completes under 3.0 seconds", duration < 3.0, f"({duration:.2f}s)")
        try:
            print(f"       Summary: {summary}")
        except Exception:
            print(f"       Summary: {summary.encode('ascii', errors='replace').decode('ascii')}")
    except Exception as e:
        test("Summarize endpoint accessible", False, str(e))

    # -------------------------------------------------------------
    # SUITE 6: Priority & Category Recommendation (/api/v1/ai/priority)
    # -------------------------------------------------------------
    print("\n--- SUITE 6: Campus ML Priority & Category Classifier ---")
    prio_payload = {
        "title": "Severe Rain Alert - Campus Closed Today",
        "content": "Due to torrential rainfall and flooding, college will remain closed today.",
        "user_role": "HOD"
    }
    try:
        t0 = time.time()
        r = requests.post(f"{BACKEND_URL}/api/v1/ai/priority", json=prio_payload, timeout=5)
        duration = time.time() - t0
        test("Priority endpoint returned 200", r.status_code == 200)
        p_data = r.json()
        test("Emergency detected accurately", p_data.get("priority") == "EMERGENCY")
        test("Predicted in sub-100ms", duration < 0.1, f"({duration*1000:.1f}ms)")
        print(f"       Classified: Priority={p_data.get('priority')}, Category={p_data.get('category')}")
    except Exception as e:
        test("Priority endpoint accessible", False, str(e))

    # -------------------------------------------------------------
    # SUITE 7: Spam & Content Validation Guardrails
    # -------------------------------------------------------------
    print("\n--- SUITE 7: AI Guardrails & Validation ---")
    spam_payload = {"text": "Click here to win free cash and get free iphone subscribe now!"}
    try:
        r = requests.post(f"{BACKEND_URL}/api/v1/ai/spam", json=spam_payload, timeout=5)
        test("Spam endpoint returned 200", r.status_code == 200)
        s_data = r.json()
        test("Spam correctly flagged", s_data.get("is_spam") is True)
    except Exception as e:
        test("Spam endpoint accessible", False, str(e))

    val_payload = {"title": "Fest", "text": "Come to the fest."}
    try:
        r = requests.post(f"{BACKEND_URL}/api/v1/ai/validate", json=val_payload, timeout=5)
        test("Validate endpoint returned 200", r.status_code == 200)
        v_data = r.json()
        test("Incomplete notice detected", v_data.get("is_valid") is False)
        test("Missing fields identified", len(v_data.get("missing_fields", [])) >= 2)
    except Exception as e:
        test("Validate endpoint accessible", False, str(e))

    # -------------------------------------------------------------
    # SUITE 8: Direct AIService Multi-Tier Unit Verification
    # -------------------------------------------------------------
    print("\n--- SUITE 8: Direct Python AIService Integration ---")
    try:
        # Import directly to verify Python-level execution
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)

        from app.services.ai_service import AIService
        from app.services.model_router import ModelRouter

        # Test expand_text directly
        t0 = time.time()
        direct_exp = AIService.expand_text("library books return deadline on monday")
        d_exp_time = time.time() - t0
        test("Direct AIService.expand_text succeeds", len(direct_exp) > 50)
        test("Direct expand_text fast (< 7.0s)", d_exp_time < 7.0, f"({d_exp_time:.2f}s)")

        # Test summarize directly
        t0 = time.time()
        direct_sum = AIService.summarize("All students must pay semester registration fee before Friday evening to avoid late penalty charges.")
        d_sum_time = time.time() - t0
        test("Direct AIService.summarize succeeds", len(direct_sum) > 10)
        test("Direct summarize fast (< 3.0s)", d_sum_time < 3.0, f"({d_sum_time:.2f}s)")

        # Test grammar directly
        t0 = time.time()
        direct_gram = AIService.check_grammar("every student have to attend practicals")
        d_gram_time = time.time() - t0
        test("Direct AIService.check_grammar succeeds", "corrected_text" in direct_gram)
        test("Direct check_grammar fast (< 4.0s)", d_gram_time < 4.0, f"({d_gram_time:.2f}s)")

        # Test get_status directly
        status_dict = AIService.get_status()
        test("Direct AIService.get_status includes Qwen", "Qwen" in status_dict.get("engine", ""))
        test("Router status includes fine_tuned_qwen", "fine_tuned_qwen" in status_dict.get("router_metrics", {}).get("active_providers", {}))

    except Exception as e:
        test("Direct AIService unit execution", False, str(e))

    print("\n" + "=" * 65)
    print(f"  TOTAL TESTS: {passed + failed} | PASSED: {passed} | FAILED: {failed}")
    print("=" * 65)

    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    run_tests()
