"""V2 replay driver ① — T1 NEGATIVE / benign-predicate (committed; NO secrets).

Real cross-account worker holds BOTH a benign (non-protected) and a protected handle.
Runs the P / N1 / N1b / N2 cases on the CURRENT predicate. Records (睫): for the controls
that appear, whether the value was OBSERVED (present in this run's enumeration) or
SKIPPED — not merely green/red.

Env: AFTERGLOW_WORKER_PASSWORD. Run:  D:\\Python\\python.exe v2_driver_t1neg.py <fixture_dir>
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
import q3_handle_audit as HA
from q3_reset_adapter import _direct_interpreter


def main(argv):
    if len(argv) != 2:
        print("usage: v2_driver_t1neg.py <fixture_dir>")
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
                  f"p=open(r'{protected}','rb')\n"
                  "hb=msvcrt.get_osfhandle(b.fileno())\n"
                  "hp=msvcrt.get_osfhandle(p.fileno())\n"
                  f"open(r'{hs}','w').write(json.dumps({{'pid':os.getpid(),'benign':hb,'prot':hp}}))\n"
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
    bh = int(rep["benign"]); ph = int(rep["prot"])
    seen = {int(hv) for hv, _tp, _acc in HA._iter_handles(pi.pid)}
    print("worker pid", pi.pid, "benign", bh, "protected", ph)

    tmap = V2._target_identities(str(protected))
    print("target identity APIs:", list(tmap.keys()))

    def show(tag, controls):
        obs = {c: (c in seen) for c in controls}
        print(f"[{tag}] controls={controls} observed_in_this_run={obs}")

    ev = V2.build_enumerator_evidence(pid=pi.pid, benign_handle_values=[bh],
                                      protected_path=str(protected), raw_ref="t1neg")
    show("P-benign", ev.benign_control_values)

    evN2 = V2.build_enumerator_evidence(pid=pi.pid, benign_handle_values=[ph],
                                        protected_path=str(protected), raw_ref="t1neg-prot")
    show("N2-protected-as-benign", evN2.benign_control_values)

    orig = V2._identity_from_handle
    try:
        V2._identity_from_handle = lambda dup, k: (None, "", {"forced": 1})
        v_unread = V2.verify_held_handle(pi.pid, bh, tmap)
    finally:
        V2._identity_from_handle = orig
    v_uncomp = V2.verify_held_handle(pi.pid, bh, target_identities={})
    print(json.dumps({
        "P_benign_controls": ev.benign_control_values,
        "P_all_benign_seen": ev.all_benign_seen,
        "N2_protected_controls": evN2.benign_control_values,
        "N1_identity_unreadable": {"identity_known": v_unread.get("identity_known"),
                                   "is_target": v_unread.get("is_target"),
                                   "is_non_target": v_unread.get("is_non_target")},
        "N1b_no_comparable_target": {"is_target": v_uncomp.get("is_target"),
                                     "is_non_target": v_uncomp.get("is_non_target")},
    }, indent=2, ensure_ascii=False))
    k32.TerminateProcess(pi.hp, 1); k32.CloseHandle(pi.hp); k32.CloseHandle(pi.ht)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
