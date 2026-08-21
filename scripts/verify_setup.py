"""Self-check setup for course 69-1.

Run: python scripts/verify_setup.py
Exit 0 if all OK, 1 if any FAIL.
"""

import os
import sys
import threading
import time

try:
    from dotenv import load_dotenv, find_dotenv
    load_dotenv(find_dotenv(), override=True)
except ImportError:
    pass

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def check_python_version():
    """Check Python is 3.11 or higher."""
    if sys.version_info >= (3, 11):
        return True, f"Python {sys.version_info.major}.{sys.version_info.minor}"
    return False, f"Python {sys.version_info.major}.{sys.version_info.minor} (need 3.11+)"


def check_env_var(name: str, hint: str) -> tuple[bool, str]:
    """Check env var is set and non-empty."""
    value = os.environ.get(name, "")
    if value and not value.startswith("AIzaSy...your"):
        masked = value[:6] + "..." + value[-4:] if len(value) > 10 else "***"
        return True, f"{name} is set ({masked})"
    return False, f"{name} missing or placeholder : {hint}"


def check_gemini_reachable() -> tuple[bool, str]:
    """Try to import google-genai and ping Gemini API."""
    api_key = os.environ.get("GOOGLE_API_KEY", "")
    if not api_key or api_key.startswith("AIzaSy...your"):
        return False, "Skipped (GOOGLE_API_KEY not set)"
    try:
        from google import genai
    except ImportError:
        return False, "google-genai not installed : run pip install -r requirements.txt"

    result_container = []

    def _worker():
        try:
            client = genai.Client(api_key=api_key)
            models_to_try = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]
            last_err = ""
            for m in models_to_try:
                try:
                    response = client.models.generate_content(
                        model=m,
                        contents="ping",
                    )
                    if response and response.text:
                        result_container.append((True, f"Gemini API reachable (model: {m})"))
                        return
                except Exception as e:
                    last_err = str(e)
                    if "429" in last_err or "RESOURCE_EXHAUSTED" in last_err:
                        result_container.append((True, f"Gemini API key verified & authenticated! (Rate limit 429 on free tier)"))
                        return
                    continue

            result_container.append((False, f"Gemini API connectivity error: {last_err[:120]}"))
        except Exception as exc:
            err_str = str(exc)
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                result_container.append((True, "Gemini API key verified & authenticated! (Rate limit 429 on free tier)"))
            else:
                result_container.append((False, f"Gemini API call failed: {type(exc).__name__}: {exc}"))

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout=10.0)

    if result_container:
        return result_container[0]
    return False, "Gemini API request timed out (10s) - โปรดตรวจสอบ GOOGLE_API_KEY ใน .env หรือการเชื่อมต่อเน็ต"


def main() -> int:
    """Run all checks, print summary, return exit code."""
    checks = [
        ("Python version", check_python_version()),
        ("GOOGLE_API_KEY", check_env_var("GOOGLE_API_KEY", "ดู Quickstart ขั้นที่ 4")),
        ("Gemini API connectivity", check_gemini_reachable()),
    ]

    all_pass = True
    for label, (ok, msg) in checks:
        marker = "[OK]  " if ok else "[FAIL]"
        print(f"{marker} {label}: {msg}")
        if not ok:
            all_pass = False

    print()
    if all_pass:
        print("All checks passed. Ready for Session 1.")
        return 0
    print("Some checks failed. แก้แล้วรันใหม่ ถ้าติดถามใน cohort/อาจารย์")
    return 1


if __name__ == "__main__":
    sys.exit(main())
