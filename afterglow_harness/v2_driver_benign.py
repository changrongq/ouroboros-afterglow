"""V2 replay driver ② — BENIGN control only (committed; NO secrets).

Real cross-account worker holds ONLY a benign (non-protected) handle. Records the
CURRENT (pre-addition) values of observation_trusted / benign_control_values /
all_benign_seen.

Env: AFTERGLOW_WORKER_PASSWORD. Run:  D:\\Python\\python.exe v2_driver_benign.py <fixture_dir>
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


def main(argv):
    if len(argv) != 2:
        print("usage: v2_driver_benign.py <fixture_dir>")
        return 2
    pw = os.environ.get("AFTERGLOW_WORKER_PASSWORD")
    if not pw:
        print("need AFTERGLOW_WORKER_PASSWORD"); return 2
    acct = os.environ.get("AFTERGLOW_WORKER_ACCOUNT", "afterglow_worker")
    base = Path(argv[1]); base.mkdir(parents=True, exist_ok=True)
    subprocess.run(["icacls", str(base), "/grant", f"{acct}:(OI)(CI)M"], capture_output=True)
    protected = base / "protected.bin"; protected.write_bytes(b"protected")
    benign = base / "benign.txt"; benign.write_bytes(b"benign")
    hs = base / "h.json"

    adv = ctypes.windll.advapi32; k32 = ctypes.windll.kernel32
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

    sc = base / "w.py"
    sc.write_text("import os,time,json,msvcrt\n"
                  f"b=open(r'{benign}','rb')\n"
                  "hb=msvcrt.get_osfhandle(b.fileno())\n"
                  f"open(r'{hs}','w').write(json.dumps({{'pid':os.getpid(),'benign':hb}}))\n"
                  "while True: time.sleep(0.2)\n", encoding="utf-8")
    si = SI(); si.cb = ctypes.sizeof(si); pi = PI()
    cmd = ctypes.create_unicode_buffer(f'"{_direct_interpreter()}" "{sc}"')
    ok = adv.CreateProcessWithLogonW(acct, ".", pw, 1, None, cmd, 0x08000000, None, str(base),
                                     ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print("spawn failed", k32.GetLastError()); return 2
    for _ in range(80):
        if hs.exists():
            break
        time.sleep(0.1)
    time.sleep(0.3)
    rep = json.loads(hs.read_text())
    bh = int(rep["benign"])
    print("worker pid", pi.pid, "benign handle", bh)

    ev = V2.build_enumerator_evidence(pid=pi.pid, benign_handle_values=[bh],
                                      protected_path=str(protected), raw_ref="driver-benign")
    print(json.dumps({
        "worker_pid": pi.pid, "benign_handle": bh,
        "observation_trusted": ev.observation_trusted,
        "benign_control_values": ev.benign_control_values,
        "all_benign_seen": ev.all_benign_seen,
    }, indent=2, ensure_ascii=False))
    k32.TerminateProcess(pi.hp, 1); k32.CloseHandle(pi.hp); k32.CloseHandle(pi.ht)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
