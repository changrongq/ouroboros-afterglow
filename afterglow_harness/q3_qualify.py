"""
q3_qualify.py — THE single Q3 qualification driver (Windows / Win32).

STATUS: SELF-CONTAINED Q3 driver. NOT wired into the frozen Phase A harness.

凌翼 R3 / 睫 BD-69: all Q3 checks (component selftests + adversarial negatives +
permission matrix + clear/preserve/access + cleanup + DACL) must run in ONE entry,
with PASS / FAIL / **SKIP** distinguished. A SKIP (e.g. no credential) MUST NOT be
counted as PASS (exit code 0 alone must not imply success).

凌翼 Q3 step 5: the unified driver also runs the ADVERSARIAL REGRESSION suite
(q3_adversarial.py) — injected defects must be rejected, else the green run is
meaningless. The EXECUTABLE ACCESS MATRIX (q3_access_matrix.py) and DACL/cleanup
(q3_dacl.py) are consumed as first-class checks (凌翼 Q3 steps 2-3).

Exit codes:
  0  => ALL checks ran and passed (no SKIP counted as PASS).
  1  => at least one FAIL.
  2  => at least one SKIP and NO fail (i.e. not fully evaluated) -> NOT a pass.

Usage:
  set AFTERGLOW_WORKER_PASSWORD, then:  python q3_qualify.py
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

# Modules that emit a "<name> selftest: N/N PASS" line. Suffix unknown until run.
COMPONENT_MODULES = (
    "q3_access_matrix.py",
    "q3_dacl.py",
    "q3_adversarial.py",
    "q3_provenance.py",
    "win32_isolation.py",
    "win32_worker_process.py",
    "q3_handle_audit.py",
    "q3_reset_chain.py",
)


def _run(script: str) -> tuple[str, str]:
    """Return (verdict, output). Verdict from the EXIT CODE (睫 BD-70):
      0 => PASS, 2 => SKIP (not-evaluated), anything else => FAIL.
    No substring guessing on the output text.
    """
    p = subprocess.run([PY, str(HERE / script)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    if p.returncode == 2:
        return SKIP, out
    if p.returncode == 0:
        return PASS, out
    return FAIL, out


def main() -> int:
    print("=" * 72)
    print("Q3 QUALIFICATION — single driver")
    print("=" * 72)
    has_cred = bool(os.environ.get("AFTERGLOW_WORKER_PASSWORD"))
    if not has_cred:
        print("NOTE: AFTERGLOW_WORKER_PASSWORD not set; credential-dependent "
              "modules will SKIP (NOT counted as PASS).")

    results = []
    for mod in COMPONENT_MODULES:
        if not (HERE / mod).exists():
            results.append((mod, SKIP, "module missing"))
            continue
        # credential-dependent modules SKIP cleanly when no password
        if not has_cred and mod in ("win32_worker_process.py", "q3_reset_chain.py"):
            results.append((mod, SKIP, "no credential"))
            continue
        verdict, out = _run(mod)
        results.append((mod, verdict, out.strip().splitlines()[-1] if out.strip() else ""))

    any_fail = any(v == FAIL for _, v, _ in results)
    any_skip = any(v == SKIP for _, v, _ in results)
    for name, v, tail in results:
        print(f"[{v}] {name}  {tail}")

    # 凌翼 Q3 STEP 3 (P1·Blocking): the driver MUST consume a SEPARATE FULL_VALID
    # result. "All component selftests exit 0" does NOT imply the real valid path
    # passed (a selftest that only asserts correct REJECTIONS also exits 0).
    full_valid_verdict, full_valid_detail = _consume_full_valid(has_cred)
    print(f"[{full_valid_verdict}] FULL_VALID_SUCCESS_PATH  {full_valid_detail}")
    print("=" * 72)
    if full_valid_verdict == FAIL:
        print("Q3_QUALIFICATION = FAIL (FULL_VALID_SUCCESS_PATH not achieved)")
        return 1
    if any_fail:
        print("Q3_QUALIFICATION = FAIL")
        return 1
    if any_skip or full_valid_verdict == SKIP:
        print("Q3_QUALIFICATION = NOT_EVALUATED (SKIP present; NOT a pass)")
        print("  A SKIP here usually means an ENVIRONMENT PRECONDITION was not met")
        print("  (no credential, or the calling account cannot CreateProcessWithLogonW")
        print("  e.g. running as nt authority\\system). This is NOT a security result.")
        return 2
    print("Q3_QUALIFICATION = PASS")
    return 0


def _consume_full_valid(has_cred: bool) -> tuple[str, str]:
    """凌翼 Q3 STEP 3: independently consume the FULL_VALID_SUCCESS_PATH artifact.

    Reads q3_full_valid_result.json (emitted by the reset-chain selftest ONLY when a
    REAL end-to-end run reached valid=True with all required gates). Returns
    (verdict, detail). Missing artifact or a non-PASS status => FAIL when a
    credential was present (the path was expected to run); SKIP without credential.
    """
    import json
    art = HERE / "q3_full_valid_result.json"
    if not has_cred:
        return SKIP, "no credential (valid path not exercised)"
    if not art.exists():
        return FAIL, "artifact missing (valid path did not run)"
    try:
        d = json.loads(art.read_text(encoding="utf-8"))
    except Exception as e:
        return FAIL, f"artifact unreadable: {type(e).__name__}: {e}"
    if d.get("FULL_VALID_SUCCESS_PATH") != "PASS":
        return FAIL, f"status={d.get('FULL_VALID_SUCCESS_PATH')!r}"
    gates = d.get("gates", {})
    if not all(gates.values()):
        return FAIL, f"not all gates True: {gates}"
    return PASS, f"profile={d.get('profile')} audit={d.get('runtime_handle_audit_status')}"


if __name__ == "__main__":
    raise SystemExit(main())
