"""C-feasibility: hardlink + non-DISK safety check (research only; NOT adopted).

凌翼 requires: POSITIVE TARGET / HARDLINK CONTROLS must be kept, so a classification
method that skips unknowns can never hide a real target.

This checks the CANDIDATE classification rule:
    "a handle classified by GetFileType as CHAR/UNKNOWN cannot be the protected
     regular disk file; only DISK handles need identity comparison"
against:
  · a REAL direct handle to the protected file (must be DISK, must be FOUND);
  · a HARDLINK handle to the same file (must ALSO classify DISK and be FOUND);
  · the unavoidable device handles (CHAR/UNKNOWN) — must NEVER equal the target.

If a hardlink handle were classified CHAR/UNKNOWN, the rule would be UNSAFE.
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
import q3_handle_audit as HA
import c_feasibility_probe as CFP


def main(argv):
    if len(argv) != 2:
        print("usage: c_hardlink_check.py <fixture_dir>")
        return 2
    pw = os.environ.get("AFTERGLOW_WORKER_PASSWORD")
    if not pw:
        print("need AFTERGLOW_WORKER_PASSWORD"); return 2
    acct = os.environ.get("AFTERGLOW_WORKER_ACCOUNT", "afterglow_worker")
    base = Path(argv[1]); base.mkdir(parents=True, exist_ok=True)
    subprocess.run(["icacls", str(base), "/grant", f"{acct}:(OI)(CI)M"], capture_output=True)
    protected = base / "protected.bin"; protected.write_bytes(b"protected")
    link = base / "protected_link.bin"
    try:
        if link.exists():
            link.unlink()
        os.link(protected, link)
        have_link = True
    except OSError:
        have_link = False
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

    from q3_reset_adapter import _direct_interpreter
    sc = base / "w.py"
    # worker opens the HARDLINK (same physical file) if available, else the direct file
    open_target = link if have_link else protected
    sc.write_text("import os,time,json,msvcrt\n"
                  f"p=open(r'{open_target}','rb')\n"
                  "hp=msvcrt.get_osfhandle(p.fileno())\n"
                  f"open(r'{hs}','w').write(json.dumps({{'pid':os.getpid(),'h':hp}}))\n"
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
    opened = json.loads(hs.read_text())
    print("worker pid", pi.pid, "opened", ("HARDLINK" if have_link else "DIRECT"), "handle", opened.get("h"))

    rep = CFP.probe(pi.pid, str(protected))
    ft_handles = rep["parts"]["file_type_handles"]
    # find the handle the worker opened (by value); check its GetFileType + identity
    wh = int(opened.get("h"))
    match = next((r for r in ft_handles if int(r.get("hv")) == wh), None)
    summary = {
        "hardlink_available": have_link,
        "worker_handle": wh,
        "worker_handle_record": match,
        "target_identity": rep["parts"]["target_identity"],
        "file_type_total": len(ft_handles),
        "non_disk_handles": [{"hv": r["hv"], "type": r.get("GetFileType", {}).get("name")}
                             for r in ft_handles
                             if r.get("GetFileType", {}).get("name") != "DISK"],
        "disk_handles_with_identity": [{"hv": r["hv"], "is_target": r.get("is_target_by_identity")}
                                       for r in ft_handles
                                       if r.get("GetFileType", {}).get("name") == "DISK"
                                       and r.get("file_identity")],
    }
    # SAFETY: does the worker's opened (target/hardlink) handle classify DISK & identify as target?
    safe = bool(match and match.get("GetFileType", {}).get("name") == "DISK"
                and match.get("is_target_by_identity") is True)
    summary["WORKER_TARGET_HANDLE_DISK_AND_IDENTIFIED"] = safe
    # SAFETY: none of the non-DISK handles is the target
    summary["NON_DISK_NONE_IS_TARGET"] = all(
        r.get("is_target_by_identity") is not True for r in ft_handles
        if r.get("GetFileType", {}).get("name") != "DISK")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    k32.TerminateProcess(pi.hp, 1); k32.CloseHandle(pi.hp); k32.CloseHandle(pi.ht)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
