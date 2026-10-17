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
    for _ in range(100):
        if hs.exists() and hs.stat().st_size:
            break
        time.sleep(0.1)
    if not (hs.exists() and hs.stat().st_size):
        print("worker did not report a handle")
        return 2
    time.sleep(0.3)
    rep = json.loads(hs.read_text())
    hv = int(rep["prot"])
    pid = int(rep["pid"])
    print("worker pid", pid, "(spawned pid", pi.pid, ") protected handle", hv)

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

    print()
    print("SCOPE: proves the failure BRANCH refuses to let a known target through when its")
    print("identity is unreadable. Proves NOTHING about handle-set completeness on a real")
    print("Windows run, and does NOT reopen OPTION C. SIMULATION != COMPLETENESS_PROOF")

    k32 = ctypes.windll.kernel32
    k32.TerminateProcess(pi.hp, 1)
    k32.CloseHandle(pi.hp)
    k32.CloseHandle(pi.ht)

    fails = [n for n, ok_, _ in RESULTS if not ok_]
    print()
    if fails:
        print(f"DISTINCT_RESULTS: FAIL={len(fails)} {fails}")
        return 1
    print("DISTINCT_RESULTS: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
