"""V2 replay driver ③ — PRODUCER positive/forged (committed; NO secrets).

Runs against the CURRENT code (observation_trusted / benign semantics). Spawns a real
cross-account worker that holds a handle to the target, then the TRUSTED PRODUCER does
its own OS verification. Records: observation_trusted, positive verified handles, and
whether the positive case is still detected (FOUND_TARGET via a full audit).

Env: AFTERGLOW_WORKER_PASSWORD (worker credential), AFTERGLOW_WORKER_ACCOUNT (optional).
Run:  D:\\Python\\python.exe v2_driver_producer.py <fixture_dir>
  fixture_dir must contain target.bin (the protected/target object).
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import q3_business_handle_audit_v2 as V2
from q3_reset_adapter import _direct_interpreter


def _spawn_holding(account, pw, script, base):
    adv = ctypes.windll.advapi32
    k32 = ctypes.windll.kernel32
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

    si = SI(); si.cb = ctypes.sizeof(si); pi = PI()
    cmd = ctypes.create_unicode_buffer(f'"{_direct_interpreter()}" "{script}"')
    ok = adv.CreateProcessWithLogonW(account, ".", pw, 1, None, cmd, 0x08000000, None,
                                     str(base), ctypes.byref(si), ctypes.byref(pi))
    return ok, pi, k32


def main(argv):
    if len(argv) != 2:
        print("usage: v2_driver_producer.py <fixture_dir>")
        return 2
    pw = os.environ.get("AFTERGLOW_WORKER_PASSWORD")
    if not pw:
        print("need AFTERGLOW_WORKER_PASSWORD")
        return 2
    acct = os.environ.get("AFTERGLOW_WORKER_ACCOUNT", "afterglow_worker")
    base = Path(argv[1]); base.mkdir(parents=True, exist_ok=True)
    subprocess.run(["icacls", str(base), "/grant", f"{acct}:(OI)(CI)M"], capture_output=True)
    target = base / "target.bin"; target.write_bytes(b"the-target")
    hs = base / "h.json"
    sc = base / "w.py"
    sc.write_text("import os,time,json,msvcrt\n"
                  f"a=open(r'{target}','rb')\n"
                  "ha=msvcrt.get_osfhandle(a.fileno())\n"
                  f"open(r'{hs}','w').write(json.dumps({{'pid':os.getpid(),'ha':ha}}))\n"
                  "while True: time.sleep(0.2)\n", encoding="utf-8")
    ok, pi, k32 = _spawn_holding(acct, pw, sc, base)
    if not ok:
        print("spawn failed", k32.GetLastError()); return 2
    for _ in range(80):
        if hs.exists():
            break
        time.sleep(0.1)
    time.sleep(0.3)
    rep = json.loads(hs.read_text())
    real_hv = int(rep["ha"])
    print("worker pid", pi.pid, "reported handle", real_hv)

    ev = V2.build_enumerator_evidence(pid=pi.pid, benign_handle_values=[real_hv],
                                      protected_path=str(target), raw_ref="driver-producer")
    # NOTE: against protected_path, a target handle is NOT benign; product of the
    # full audit is the FOUND_TARGET check.
    audit = V2.audit_business_worker_handles(pi.pid, str(target),
                                             enumerator_evidence=ev)
    print(json.dumps({
        "worker_pid": pi.pid, "reported_handle": real_hv,
        "observation_trusted": ev.observation_trusted,
        "benign_controls": ev.benign_control_values,
        "all_benign_seen": ev.all_benign_seen,
        "audit_status": audit.status,           # expect FOUND_TARGET
        "audit_matched": audit.matched,
        "audit_counts": audit.counts,
    }, indent=2, ensure_ascii=False))
    k32.TerminateProcess(pi.hp, 1); k32.CloseHandle(pi.hp); k32.CloseHandle(pi.ht)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
