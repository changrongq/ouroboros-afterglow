"""UNREADABLE_TARGET_CONTROL — T1 negative test (凌翼 `LINGYI — C STOP / T1 / PROOF
SEMANTICS RULING`, 2026-10-17, item 2).

AUTHORIZATION
    EXISTING_T1_NEGATIVE_TEST           = AUTHORIZED
    C_STOP_DOES_NOT_BLOCK_THIS_TEST     = true
    UNREADABLE_TARGET_CONTROL_EXECUTION = AUTHORIZED_IN_T1

THE ONE QUESTION THIS ANSWERS (deliberately narrow)
    "A handle that an INDEPENDENT controller has confirmed points at the protected
    object -- if the auditor cannot read its identity, will the auditor wrongly call it
    non-target, or wrongly reach CLEAN?"

    It does NOT ask whether the enumerator covers every handle at every instant, so it
    needs no observation boundary and is unaffected by the C stop.

METHOD
    Real cross-account worker opens a handle to the protected file and reports the
    handle VALUE. This driver independently confirms the value refers to the protected
    object by reading its identity through DuplicateHandle. THEN the identity-read path
    is made to fail, and the audit is run.

    The injection is CONTROLLED and LOCAL: only `_identity_from_handle` is replaced, so
    "the handle is known to be the target" and "the identity read fails" hold together.
    That conjunction is exactly the case under test.

EXPECTED (凌翼)
    KNOWN_TARGET + IDENTITY_FAILURE => UNRESOLVED
    != CLEAN
    SIMULATION != COMPLETENESS_PROOF

So this proves ONLY that the failure branch refuses to let a known target through. It
proves NOTHING about handle-set completeness on a real Windows run and must not be cited
as if it did. It does NOT reopen OPTION C.

Requires AFTERGLOW_WORKER_PASSWORD.
"""
from __future__ import annotations

import ctypes
import json
import os
import secrets
import sys
import time
from ctypes import wintypes
from pathlib import Path

import q3_business_handle_audit_v2 as V
from q3_reset_adapter import _direct_interpreter

RESULTS: list = []
# 知微 2026-10-18: set by main()'s finally block when the worker could not be confirmed
# exited. Read by the entry point so a cleanup failure becomes a non-zero exit status
# instead of a printed line that nobody acts on.
CLEANUP_FAILED: bool = False
EXIT_CLEANUP_FAILED = 3
# Structured cleanup record. PENDING_PID is non-zero exactly when the worker's exit was
# NOT confirmed; the run must then not be reported as a clean pass, and the pid is
# recorded as still pending disposal rather than described as exited.
PENDING_PID: int = 0
CLEANUP_DETAIL: str = ""
CHECK_RESULT: int = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def _spawn(data_dir: Path, protected: Path, hs: Path, acct: str, pw: str):
    adv = ctypes.windll.advapi32
    adv.CreateProcessWithLogonW.restype = wintypes.BOOL
    adv.CreateProcessWithLogonW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD, ctypes.c_void_p,
        wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p]

    class SI(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("r", wintypes.LPWSTR), ("d", wintypes.LPWSTR),
                    ("t", wintypes.LPWSTR), ("x", wintypes.DWORD), ("y", wintypes.DWORD),
                    ("xs", wintypes.DWORD), ("ys", wintypes.DWORD), ("xc", wintypes.DWORD),
                    ("yc", wintypes.DWORD), ("fa", wintypes.DWORD), ("fl", wintypes.DWORD),
                    ("sw", wintypes.WORD), ("cr2", wintypes.WORD), ("r2", ctypes.c_void_p),
                    ("hi", wintypes.HANDLE), ("ho", wintypes.HANDLE), ("he", wintypes.HANDLE)]

    class PI(ctypes.Structure):
        _fields_ = [("hp", wintypes.HANDLE), ("ht", wintypes.HANDLE),
                    ("pid", wintypes.DWORD), ("tid", wintypes.DWORD)]

    sc = data_dir / "worker_prot.py"
    sc.write_text(
        "import os,time,json,msvcrt\n"
        f"f=open(r'{protected}','rb')\n"
        "h=msvcrt.get_osfhandle(f.fileno())\n"
        f"open(r'{hs}','w').write(json.dumps({{'pid':os.getpid(),'prot':h}}))\n"
        "while True: time.sleep(0.2)\n", encoding="utf-8")
    si = SI(); si.cb = ctypes.sizeof(si); pi = PI()
    cmd = ctypes.create_unicode_buffer(f'"{_direct_interpreter()}" "{sc}"')
    ok = adv.CreateProcessWithLogonW(acct, ".", pw, 1, None, cmd, 0x08000000, None,
                                     str(data_dir), ctypes.byref(si), ctypes.byref(pi))
    return ok, pi, ctypes.windll.kernel32.GetLastError()


def _terminate_and_confirm(pi, pid: int, timeout_s: float = 10.0) -> tuple:
    """Terminate the worker and WAIT until the OS says it is gone.

    知微 2026-10-18: the original driver terminated the process and immediately closed
    the handles, without waiting for exit confirmation -- so a still-running worker could
    outlive the test. It also had four early `return 2` paths that fired AFTER the spawn
    and never cleaned up at all, leaking an orphaned cross-account process.

    知微 2026-10-18 (second pass) found three more holes, all fixed here:
      (a) the wait itself was OUTSIDE any try, so if WaitForSingleObject raised, every
          following CloseHandle was skipped -- handles leaked;
      (b) CloseHandle calls were wrapped in a single `except: pass`, so a failure on the
          first handle skipped the second;
      (c) the caller merely PRINTED the result, so a worker that failed to exit still
          produced exit status 0.
    Each step is now individually guarded and the return value tells the caller whether
    cleanup actually succeeded, so a cleanup failure can be promoted into the process
    exit status instead of being printed and ignored.

    Returns (exited: bool, detail: str). Never raises.

    Win32 prototypes are set explicitly (知微 2026-10-18): without them ctypes truncates
    64-bit HANDLE returns to 32 bits, which is how I previously produced a bogus
    "OpenProcessToken failed 6". A truncated handle also makes CloseHandle close the
    WRONG value.
    """
    k32 = ctypes.windll.kernel32

    def _proto(name: str, restype, argtypes) -> None:
        """Set a Win32 prototype if the object allows it.

        知微 2026-10-18 asked for explicit prototypes so 64-bit HANDLE returns are not
        truncated. They must be set defensively: a test double may legitimately not
        support attribute assignment, and cleanup must not CRASH just because a
        prototype cannot be installed -- a crash here would leak the very handles this
        function exists to release.
        """
        fn = getattr(k32, name, None)
        if fn is None:
            return
        try:
            fn.restype = restype
            fn.argtypes = argtypes
        except (AttributeError, TypeError):
            pass

    _proto("WaitForSingleObject", wintypes.DWORD, [wintypes.HANDLE, wintypes.DWORD])
    _proto("TerminateProcess", wintypes.BOOL, [wintypes.HANDLE, wintypes.UINT])
    _proto("OpenProcess", wintypes.HANDLE,
           [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD])
    _proto("GetExitCodeProcess", wintypes.BOOL,
           [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)])
    _proto("CloseHandle", wintypes.BOOL, [wintypes.HANDLE])
    detail = ""

    def _close(h, label: str) -> None:
        nonlocal detail
        try:
            k32.CloseHandle(h)
        except Exception as e:                                   # noqa: BLE001
            detail += f"; CloseHandle({label}) raised {type(e).__name__}"

    try:
        k32.TerminateProcess(pi.hp, 1)
    except Exception as e:                                       # noqa: BLE001
        detail += f"; TerminateProcess raised {type(e).__name__}"

    # WaitForSingleObject(handle, ms): 0 = signalled (exited), 0x102 = timeout.
    # Guarded individually: if the wait itself throws, we must STILL release handles.
    WAIT_OBJECT_0 = 0x00000000
    exited = False
    try:
        waited = k32.WaitForSingleObject(pi.hp, int(timeout_s * 1000))
        exited = (waited == WAIT_OBJECT_0)
        if not exited:
            detail += f"; wait returned {waited:#x} (not signalled within {timeout_s}s)"
    except Exception as e:                                       # noqa: BLE001
        detail += f"; WaitForSingleObject raised {type(e).__name__}"

    # Verify from the OS that the pid no longer resolves.
    #
    # 知微 2026-10-18 (third pass): OpenProcess failing does NOT mean the process is
    # gone. It may be a permission problem, or the PID may have been reused. Treating a
    # failed open as proof of exit would let us close the handles of a STILL-RUNNING
    # worker and then report success. Exit confirmation therefore prefers the STABLE
    # process handle from the spawn, and a failed open is recorded as UNKNOWN, never as
    # "gone".
    PROCESS_QUERY_LIMITED = 0x1000
    STILL_ACTIVE = 259
    try:
        hp2 = k32.OpenProcess(PROCESS_QUERY_LIMITED, False, pid)
        if hp2:
            code = wintypes.DWORD(0)
            ok_code = k32.GetExitCodeProcess(hp2, ctypes.byref(code))
            _close(hp2, "query")
            if not ok_code:
                # we could not read the exit code: do NOT infer exit from this
                detail += ("; GetExitCodeProcess failed -- exit NOT verified via pid "
                           "(reason unknown, NOT 'gone')")
            elif code.value == STILL_ACTIVE:
                exited = False
                detail += f"; pid {pid} still reports STILL_ACTIVE"
            else:
                detail += f"; exit code {code.value:#x}"
        else:
            err = k32.GetLastError()
            # Unknown, not gone: could be access denied, or the pid may be reused.
            detail += (f"; OpenProcess(PROCESS_QUERY_LIMITED) failed err={err} -- "
                       f"pid state UNKNOWN, NOT interpreted as gone")
    except Exception as e:                                       # noqa: BLE001
        exited = False
        detail += f"; exit verification raised {type(e).__name__}"

    # Release BOTH handles independently -- never let the first failure skip the second.
    # NOTE: releasing the controller's handles does not mean the worker exited. If
    # `exited` is False the caller must record the pid as STILL PENDING.
    _close(pi.hp, "process")
    _close(pi.ht, "thread")
    return exited, detail


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: c_unreadable_target_control.py <fixture_dir>")
        return 2
    pw = os.environ.get("AFTERGLOW_WORKER_PASSWORD", "")
    if not pw:
        print("need AFTERGLOW_WORKER_PASSWORD")
        return 2
    acct = "afterglow_worker"

    work = Path(sys.argv[1]) / "unreadable_target_control"
    work.mkdir(parents=True, exist_ok=True)
    protected = work / f"protected_{secrets.token_hex(4)}.bin"
    protected.write_bytes(b"UNREADABLE_TARGET_CONTROL")
    hs = work / "h.json"
    if hs.exists():
        hs.unlink()

    print("== spawn cross-account worker holding a handle to protected ==")
    ok, pi, err = _spawn(work, protected, hs, acct, pw)
    if not ok:
        print("spawn failed", err)
        return 2

    # From here on a worker exists, so EVERY exit path must go through the finally block.
    #
    # 知微 2026-10-18 (third pass): collect the check result, run cleanup, THEN merge.
    # The previous shape returned the check value directly and only printed the cleanup
    # outcome, so a worker that never exited still produced status 0. His required rule:
    # overall success must INCLUDE cleanup success; an unconfirmed exit is never a full
    # PASS, and the pending pid must be recorded rather than described as exited.
    pid_for_cleanup = int(pi.pid)
    check_result = 0
    check_reached = False
    try:
        for _ in range(100):
            if hs.exists() and hs.stat().st_size:
                break
            time.sleep(0.1)
        if not (hs.exists() and hs.stat().st_size):
            print("worker did not report a handle")
            check_result = 2
            return check_result
        time.sleep(0.3)
        rep = json.loads(hs.read_text())
        hv = int(rep["prot"])
        pid = int(rep["pid"])
        pid_for_cleanup = pid
        print("worker pid", pid, "(spawned pid", pi.pid, ") protected handle", hv)
        check_result = _run_checks(pi, pid, hv, protected)
        check_reached = True
        return check_result
    finally:
        exited, cleanup_detail = _terminate_and_confirm(pi, pid_for_cleanup)
        print()
        print(f"CLEANUP: worker exit confirmed = {exited}  [{cleanup_detail}]")
        global CLEANUP_FAILED, PENDING_PID, CLEANUP_DETAIL, CHECK_RESULT
        CLEANUP_DETAIL = cleanup_detail
        CHECK_RESULT = check_result
        if not exited:
            CLEANUP_FAILED = True
            PENDING_PID = pid_for_cleanup
            # 知微: record the pid still PENDING disposal. Do NOT describe a worker whose
            # exit we could not confirm as exited, even though our handles are released.
            print(f"CLEANUP_WARNING: worker exit NOT confirmed -- pid {pid_for_cleanup} "
                  f"is STILL PENDING disposal. Do not report this run as a clean pass.")


def _run_checks(pi, pid: int, hv: int, protected: Path) -> int:
    print("== independent controller: confirm the handle IS the target ==")
    tmap, treason = V._target_identities(str(protected))
    print("target identity reason:", treason, "APIs:", list(tmap.keys()))
    v_real = V.verify_held_handle(pid, hv, tmap)
    print("independent confirmation:", json.dumps(
        {"identity_known": v_real.get("identity_known"),
         "is_target": v_real.get("is_target")}, ensure_ascii=False))
    check("controller confirms the handle IS the target",
          v_real.get("identity_known") is True and v_real.get("is_target") is True,
          f"known={v_real.get('identity_known')} target={v_real.get('is_target')}")

    print("== controlled identity failure (identity-read path only) ==")
    orig_ident = V._identity_from_handle

    def _fake_identity(dup, k):                   # noqa: ANN001
        return None, "", {"injected": "identity_unreadable"}

    V._identity_from_handle = _fake_identity
    try:
        res = V.audit_business_worker_handles(pid, str(protected))
    finally:
        V._identity_from_handle = orig_ident

    print("audit status:", res.status)
    print("audit reason:", res.target_identity_reason or "(none)")
    print("audit counts:", json.dumps(
        {k: res.counts.get(k) for k in
         ("file_type_total", "found_target", "non_target_proven", "unresolved",
          "unresolved_operational", "unresolved_no_identity",
          "unresolved_incomparable")}, ensure_ascii=False))
    print("audit detail:", (res.detail or "")[:220])

    check("STATUS IS NOT CLEAN", res.status != V.V2_CLEAN, res.status)
    check("STATUS IS NOT FOUND_TARGET (identity was unreadable)",
          res.status != V.V2_FOUND_TARGET, res.status)
    check("STATUS IS UNRESOLVED", res.status == V.V2_UNRESOLVED, res.status)
    check("status is within the four-status contract",
          res.status in V.V2_CONTRACT_STATUSES, str(V.V2_CONTRACT_STATUSES))
    check("known target was NOT reclassified as proven non-target",
          (res.counts.get("non_target_proven") or 0) == 0,
          f"non_target_proven={res.counts.get('non_target_proven')}")
    check("unresolved > 0", (res.counts.get("unresolved") or 0) > 0,
          f"unresolved={res.counts.get('unresolved')}")
    check("must NOT claim an ontological cause",
          "CAUSE_IS_ONTOLOGICAL" not in (res.detail or ""), (res.detail or "")[:60])
    check("must NOT claim privilege cannot help",
          "cannot move this to CLEAN" not in (res.detail or ""), (res.detail or "")[:60])

    # ---- 凌翼 2026-10-18: the SPECIFIC known-target handle must be traceable --------
    # The ruling noted a real gap: the earlier run asserted only AGGREGATE counts, so it
    # supported "the fail-closed branch fired" but did NOT demonstrate that the one
    # handle we independently confirmed to be the target appeared in the per-handle
    # records. Aggregate zeros can be satisfied without that handle ever being examined.
    # This asserts the per-handle trail explicitly, so the scope limit stops being prose.
    per_handle = [r for r in res.records if int(getattr(r, "handle_value", -1)) == hv]
    print("per-handle record for the known target:", json.dumps(
        [{k: getattr(r, k, None) for k in
          ("handle_value", "classification", "unresolved_kind", "name")}
         for r in per_handle], ensure_ascii=False, default=str)[:300])
    check("known-target handle APPEARS in the per-handle records",
          len(per_handle) >= 1, f"matches={len(per_handle)} handle={hv:#x}")
    if per_handle:
        rec = per_handle[0]
        check("that record is classified unresolved (not non_target)",
              rec.classification == "unresolved", str(rec.classification))
        check("that record did NOT become proven non-target",
              rec.classification != "non_target_proven", str(rec.classification))
        check("that record carries an unresolved_kind",
              rec.unresolved_kind in (V.UNRESOLVED_KIND_OPERATIONAL,
                                      V.UNRESOLVED_KIND_NO_IDENTITY,
                                      V.UNRESOLVED_KIND_INCOMPARABLE),
              str(rec.unresolved_kind))

    print()
    print("SCOPE: proves the failure BRANCH refuses to let a known target through when its")
    print("identity is unreadable. Proves NOTHING about handle-set completeness on a real")
    print("Windows run, and does NOT reopen OPTION C. SIMULATION != COMPLETENESS_PROOF")

    # NOTE: process cleanup is deliberately NOT here. It lives in main()'s finally block
    # so that every return path -- including early failures and exceptions -- releases the
    # worker. 知微 2026-10-18: the previous inline termination skipped on error paths and
    # never waited for exit confirmation.
    fails = [n for n, ok_, _ in RESULTS if not ok_]
    print()
    if fails:
        print(f"DISTINCT_RESULTS: FAIL={len(fails)} {fails}")
        return 1
    print("DISTINCT_RESULTS: PASS")
    return 0


if __name__ == "__main__":
    rc = main()
    # 知微 2026-10-18: a cleanup failure must be visible in the process exit status, and
    # overall success must INCLUDE cleanup success. The check verdict and the cleanup
    # verdict are separate facts, so both are reported and neither masks the other.
    print()
    print("CLEANUP_SUMMARY: " + json.dumps({
        "check_result": CHECK_RESULT,
        "cleanup_failed": CLEANUP_FAILED,
        "pending_pid": PENDING_PID,
        "cleanup_detail": CLEANUP_DETAIL,
    }, ensure_ascii=False))
    if CLEANUP_FAILED:
        print("EXIT_STATUS: cleanup NOT confirmed -- this run is NOT a clean pass.")
        if rc == 0:
            sys.exit(EXIT_CLEANUP_FAILED)
        print(f"EXIT_STATUS: check result was {rc}; cleanup ALSO failed.")
        sys.exit(rc)
    sys.exit(rc)
