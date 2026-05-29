"""
Startup self-test for LoanEase.

Validates that all critical components (XGBoost model, OCR engine,
Groq connectivity, blockchain ledger) are functional before the
server begins accepting requests.

Called at the end of the FastAPI lifespan startup phase.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger("loanease.selftest")


async def run_startup_selftest(app: Any) -> Dict[str, str]:
    """Run self-tests on all critical components and print a report.

    Args:
        app: The FastAPI application instance (to access app.state).

    Returns:
        Dict mapping component name → status string.
    """
    results: Dict[str, str] = {}

    # ── Test 1: XGBoost model ────────────────────────────────────
    try:
        from agents.underwriting_agent.main import load_model, model_loaded, predict_credit_score

        if not model_loaded():
            load_model()
        test_features = {
            "cibil_score": 750,
            "loan_amount": 150000,
            "tenure_years": 5,
            "age": 30,
            "income_estimated": 500000,
        }
        score = predict_credit_score(test_features)
        assert 300 <= score <= 900, f"Score out of range: {score}"
        results["xgboost"] = "✅ PASS"
    except Exception as e:
        results["xgboost"] = f"❌ FAIL: {e}"

    # ── Test 2: OCR engine ───────────────────────────────────────
    try:
        from services.ocr import init_ocr, ocr_ready

        if not ocr_ready():
            init_ocr()
        if ocr_ready():
            results["ocr"] = "✅ PASS"
        else:
            results["ocr"] = "⚠️ DEGRADED: engine not available"
    except Exception as e:
        results["ocr"] = f"❌ FAIL: {e}"

    # ── Test 3: Groq connectivity ────────────────────────────────
    try:
        groq_service = getattr(app.state, "groq_service", None)
        if groq_service is not None:
            connected = await groq_service.verify_connection()
            if connected:
                results["groq"] = "✅ PASS"
            else:
                results["groq"] = "⚠️ FALLBACK: connection failed but service initialized"
        else:
            results["groq"] = "⚠️ FALLBACK: GroqService not in app state"
    except Exception as e:
        results["groq"] = f"⚠️ FALLBACK: {e}"

    # ── Test 4: Blockchain ledger ────────────────────────────────
    try:
        from blockchain import ledger

        test_block = ledger.add_transaction({
            "test": True,
            "transaction_id": "SELFTEST-001",
        })
        assert ledger.is_chain_valid(), "Chain validation failed"
        # Remove the test block so it doesn't pollute real data
        ledger.chain.pop()
        results["blockchain"] = "✅ PASS"
    except Exception as e:
        results["blockchain"] = f"❌ FAIL: {e}"

    # ── Print startup report ─────────────────────────────────────
    from core.config import settings

    print("\n" + "=" * 44)
    print("   LOANEASE STARTUP SELF-TEST")
    print("=" * 44)
    for component, status in results.items():
        print(f"   {component.upper():15s} {status}")
    print("-" * 44)
    if settings.DEMO_MODE:
        print("   📌 DEMO_MODE = ON")
    print("-" * 44)

    failed = [k for k, v in results.items() if "FAIL" in v]
    if failed:
        print(f"   ⚠️  {len(failed)} component(s) need attention: {failed}")
    else:
        print("   🎯 ALL SYSTEMS GO — Demo ready")
    print("=" * 44 + "\n")

    return results
