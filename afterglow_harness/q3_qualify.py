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

Exit codes (知微 P1: state precisely — FAIL dominates SKIP):
  0  => ALL checks ran and passed (no SKIP counted as PASS).
  1  => at least one FAIL — REGARDLESS of any SKIP present.
  2  => at least one SKIP and NO fail (i.e. not fully evaluated) -> NOT a pass.
       NOTE: "no credential" does NOT guarantee exit 2; if any component FAILs,
       the exit is 1. exit 2 requires SKIP(s) AND zero FAIL(s).

Usage:
  set AFTERGLOW_WORKER_PASSWORD, then:  python q3_qualify.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

# 凌翼 Q3 STEP 3 / 知微 P1: the FULL_VALID artifact must be STRICTLY validated:
#   · exact schema (top-level types; a fixed, contract-derived gate set)
#   · every gate strictly `is True` (no truthy strings/numbers; no empty set)
#   · a REGISTERED, active profile (not just a printed name)
#   · bound to THIS run (run-id match) so a stale artifact cannot be consumed
from q3_contract import ACTIVE_HANDLE_PROFILE, PROFILE_VERSION
#: The frozen gate set the artifact MUST carry (exactly these keys, all True).
REQUIRED_FULL_VALID_GATES = (
    "clear_ok", "preserve_ok", "access_ok", "handle_ok",
    "identity_ok", "lifecycle_ok", "matrix_ok", "dacl_restore_ok",
)

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


def _run(script: str, extra_env: dict | None = None) -> tuple[str, str]:
    """Return (verdict, output). Verdict from the EXIT CODE (睫 BD-70):
      0 => PASS, 2 => SKIP (not-evaluated), anything else => FAIL.
    No substring guessing on the output text.
    """
    env = dict(os.environ)
    if extra_env:
        env.update(extra_env)
    p = subprocess.run([PY, str(HERE / script)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env)
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

    # 凌翼 STEP 3 / 知微 P1: generate a UNIQUE run id for THIS driver invocation and
    # pass it to every subprocess, so the emitted FULL_VALID artifact is bound to
    # this run (a stale artifact from a previous run cannot be consumed).
    run_id = uuid.uuid4().hex
    print(f"Q3_RUN_ID = {run_id}")
    child_env = {"AFTERGLOW_Q3_RUN_ID": run_id}

    results = []
    for mod in COMPONENT_MODULES:
        if not (HERE / mod).exists():
            results.append((mod, SKIP, "module missing"))
            continue
        # credential-dependent modules SKIP cleanly when no password
        if not has_cred and mod in ("win32_worker_process.py", "q3_reset_chain.py"):
            results.append((mod, SKIP, "no credential"))
            continue
        verdict, out = _run(mod, extra_env=child_env)
        results.append((mod, verdict, out.strip().splitlines()[-1] if out.strip() else ""))

    # 知微 P1: the FULL_VALID artifact CONSUMER has its own negative regression
    # suite (strict schema, boolean, profile, run-id binding). Run it as a
    # first-class component so a weakened consumer fails the driver.
    import subprocess as _sp
    _cp = _sp.run([PY, str(HERE / "q3_qualify.py"), "--selftest"],
                  capture_output=True, text=True, encoding="utf-8", errors="replace")
    _cout = (_cp.stdout or "") + (_cp.stderr or "")
    _cverdict = PASS if _cp.returncode == 0 else FAIL
    results.append(("q3_qualify.py --selftest", _cverdict,
                    _cout.strip().splitlines()[-1] if _cout.strip() else ""))

    any_fail = any(v == FAIL for _, v, _ in results)
    any_skip = any(v == SKIP for _, v, _ in results)
    for name, v, tail in results:
        print(f"[{v}] {name}  {tail}")

    # 凌翼 Q3 STEP 3 (P1·Blocking): the driver MUST consume a SEPARATE FULL_VALID
    # result. "All component selftests exit 0" does NOT imply the real valid path
    # passed (a selftest that only asserts correct REJECTIONS also exits 0).
    full_valid_verdict, full_valid_detail = _consume_full_valid(has_cred, run_id)
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


def _consume_full_valid(has_cred: bool, run_id: str | None = None) -> tuple[str, str]:
    """凌翼 Q3 STEP 3 + 知微 P1: STRICTLY consume the FULL_VALID_SUCCESS_PATH artifact.

    Rejects (all => FAIL when a credential was present):
      · missing artifact / unreadable / non-object JSON
      · non-"PASS" status field
      · missing / empty / wrong-type gates  (empty set is NOT all-true)
      · ANY gate not strictly `is True` (truthy strings/numbers rejected)
      · a profile that is not the REGISTERED active profile / version
      · Profile B: profile_b_ok must be strictly True and the proof fields present
      · a run-id that does not match THIS driver invocation (stale-artifact binding)
    Returns (verdict, detail). SKIP only when there is no credential.
    """
    art = HERE / "q3_full_valid_result.json"
    if not has_cred:
        return SKIP, "no credential (valid path not exercised)"
    if not art.exists():
        return FAIL, "artifact missing (valid path did not run)"
    try:
        raw = art.read_text(encoding="utf-8")
        d = json.loads(raw)
    except Exception as e:
        return FAIL, f"artifact unreadable: {type(e).__name__}: {e}"

    if not isinstance(d, dict):
        return FAIL, f"artifact is not a JSON object: {type(d).__name__}"

    # 1. status
    if d.get("FULL_VALID_SUCCESS_PATH") != "PASS":
        return FAIL, f"status={d.get('FULL_VALID_SUCCESS_PATH')!r}"

    # 2. run-id binding (this run only)
    if run_id is not None:
        if d.get("run_id") != run_id:
            return FAIL, (f"run_id mismatch (artifact {d.get('run_id')!r} != "
                          f"this run {run_id!r}) — stale artifact rejected")

    # 3. profile must be the registered ACTIVE profile + version
    if d.get("profile") != ACTIVE_HANDLE_PROFILE:
        return FAIL, (f"profile {d.get('profile')!r} != active "
                      f"{ACTIVE_HANDLE_PROFILE!r}")
    expected_pv = PROFILE_VERSION.get(ACTIVE_HANDLE_PROFILE)
    if expected_pv is not None and d.get("profile_version") != expected_pv:
        return FAIL, (f"profile_version {d.get('profile_version')!r} != "
                      f"{expected_pv!r}")

    # 4. gates: EXACT required set, every value strictly True
    gates = d.get("gates")
    if not isinstance(gates, dict):
        return FAIL, f"gates missing or not an object: {type(gates).__name__}"
    missing = [g for g in REQUIRED_FULL_VALID_GATES if g not in gates]
    if missing:
        return FAIL, f"gates missing required keys: {missing}"
    not_true = [g for g in REQUIRED_FULL_VALID_GATES if gates.get(g) is not True]
    if not_true:
        return FAIL, f"gates not strictly True: {not_true}"
    extra = [g for g in gates if g not in REQUIRED_FULL_VALID_GATES]
    if extra:
        return FAIL, f"gates has unexpected keys: {extra}"

    # 5. Profile B: the narrow-claim proof must itself be strictly True
    if ACTIVE_HANDLE_PROFILE == "API_NO_INHERIT_PROFILE":
        if d.get("profile_b_ok") is not True:
            return FAIL, f"Profile B not proven: profile_b_ok={d.get('profile_b_ok')!r}"

    return PASS, (f"profile={d.get('profile')} v={d.get('profile_version')} "
                  f"audit={d.get('runtime_handle_audit_status')} run_id={d.get('run_id')}")


def _selftest_full_valid_consumer() -> int:
    """知微 P1 negative regressions for the FULL_VALID artifact consumer.

    Each malformed/stale artifact MUST be rejected. A well-formed artifact for
    THIS run MUST be accepted. Pure; no OS privilege; no worker.
    """
    import tempfile
    results = []

    def chk(name, cond):
        results.append(bool(cond))
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    global HERE
    orig_here = HERE
    tmp = Path(tempfile.mkdtemp(prefix="q3_qualify_gate_"))
    HERE = tmp
    art = tmp / "q3_full_valid_result.json"
    rid = "run-abc-123"
    good_gates = {g: True for g in REQUIRED_FULL_VALID_GATES}
    good_pv = PROFILE_VERSION.get(ACTIVE_HANDLE_PROFILE, "")
    good = {"FULL_VALID_SUCCESS_PATH": "PASS", "run_id": rid,
            "profile": ACTIVE_HANDLE_PROFILE, "profile_version": good_pv,
            "profile_b_ok": True, "gates": dict(good_gates)}

    def consume(d, rid_=rid):
        art.write_text(__import__("json").dumps(d), encoding="utf-8")
        return _consume_full_valid(True, rid_)[0]

    try:
        chk("baseline good artifact -> PASS", consume(good) == PASS)
        # empty / missing gates
        chk("empty gates -> FAIL", consume({"FULL_VALID_SUCCESS_PATH": "PASS",
                                            "run_id": rid, "profile": ACTIVE_HANDLE_PROFILE,
                                            "profile_version": good_pv, "profile_b_ok": True,
                                            "gates": {}}) == FAIL)
        chk("missing gates -> FAIL", consume({"FULL_VALID_SUCCESS_PATH": "PASS",
                                             "run_id": rid, "profile": ACTIVE_HANDLE_PROFILE,
                                             "profile_version": good_pv, "profile_b_ok": True}) == FAIL)
        # one required gate missing
        g1 = dict(good); g1["gates"] = {k: v for k, v in good_gates.items() if k != "access_ok"}
        chk("one required gate missing -> FAIL", consume(g1) == FAIL)
        # truthy string / number / None
        for bad in ("UNEVALUATED", 1, None, "true"):
            g = dict(good); g["gates"] = dict(good_gates); g["gates"]["access_ok"] = bad
            chk(f"gate access_ok={bad!r} -> FAIL", consume(g) == FAIL)
        # non-bool False
        g2 = dict(good); g2["gates"] = dict(good_gates); g2["gates"]["access_ok"] = False
        chk("gate access_ok=False -> FAIL", consume(g2) == FAIL)
        # extra unexpected gate
        g3 = dict(good); g3["gates"] = dict(good_gates); g3["gates"]["surprise"] = True
        chk("extra unexpected gate -> FAIL", consume(g3) == FAIL)
        # wrong profile
        g4 = dict(good); g4["profile"] = "NOT_REGISTERED"
        chk("unregistered profile -> FAIL", consume(g4) == FAIL)
        # wrong profile version
        g5 = dict(good); g5["profile_version"] = "9.9"
        chk("wrong profile version -> FAIL", consume(g5) == FAIL)
        # Profile B proof failed
        g6 = dict(good); g6["profile_b_ok"] = False
        chk("Profile B not proven -> FAIL", consume(g6) == FAIL)
        # stale run id
        g7 = dict(good); g7["run_id"] = "old-run-999"
        chk("stale run_id -> FAIL", consume(g7) == FAIL)
        # status not PASS
        g8 = dict(good); g8["FULL_VALID_SUCCESS_PATH"] = "NOT_PASSED"
        chk("status NOT_PASSED -> FAIL", consume(g8) == FAIL)
        # no artifact at all
        art.unlink()
        chk("missing artifact -> FAIL", _consume_full_valid(True, rid)[0] == FAIL)
        # no credential -> SKIP
        chk("no credential -> SKIP", _consume_full_valid(False, rid)[0] == SKIP)
    finally:
        import shutil
        HERE = orig_here
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for r in results if r)
    print(f"\nq3_qualify(full-valid consumer) selftest: {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    import sys as _sys
    if "--selftest" in _sys.argv:
        raise SystemExit(_selftest_full_valid_consumer())
    raise SystemExit(main())
