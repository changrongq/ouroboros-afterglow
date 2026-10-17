"""C-FEASIBILITY PROBE (unfrozen, research only) — NOT an implementation, NOT adopted.

凌翼 2026-10-17 ruling: OPTION_C = LIMITED FEASIBILITY AUTHORIZED.
  Required to research:
    (1) INDEPENDENT COVERAGE EVIDENCE for same PID/create_time/controlled interval
        (count equality ALONE is insufficient);
    (2) OS-BACKED RELEVANT-HANDLE CLASSIFICATION for device handles that fail
        GetFileInformationByHandle(Ex) — e.g. \\Device\\ConDrv, \\Device\\KsecDD,
        \\Device\\CNG.
  Must keep positive-target / hardlink controls. Must NOT turn unknown into CLEAN.

This script only OBSERVES and REPORTS FEASIBILITY. It makes NO verdict and adopts
nothing. Output is a feasibility report, not a proof design yet.

Questions this answers:
  A. Can GetProcessHandleCount be read for a cross-account worker? Does it AGREE with
     the enumerator count? (It is a cross-check, not proof of set equality.)
  B. For the device handles we cannot file-identify, can we obtain a RELIABLE OS object
     attribute that proves "this handle is NOT the protected file" — e.g.
     GetFileType() (FILE_TYPE_CHAR/DISK/PIPE), or the object TYPE name?
  C. Is there a second independent enumeration path (e.g. NtQuerySystemInformation
     class 16 vs 64) that agrees with the primary enumerator on the SAME set?
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
import q3_t0_enumerator_experiment as T0  # reuse class16/class64 enumerators


def _k32():
    k = ctypes.windll.kernel32
    k.GetProcessHandleCount.restype = wintypes.BOOL
    k.GetProcessHandleCount.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.GetFileType.restype = wintypes.DWORD
    k.GetFileType.argtypes = [wintypes.HANDLE]
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    k.DuplicateHandle.restype = wintypes.BOOL
    k.DuplicateHandle.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.HANDLE,
                                  ctypes.POINTER(ctypes.c_void_p), wintypes.DWORD,
                                  wintypes.BOOL, wintypes.DWORD]
    k.GetCurrentProcess.restype = wintypes.HANDLE
    return k


FILE_TYPE_UNKNOWN = 0x0000
FILE_TYPE_DISK = 0x0001
FILE_TYPE_CHAR = 0x0002
FILE_TYPE_PIPE = 0x0003
FILE_TYPE_REMOTE = 0x8000


def _file_type_name(t: int) -> str:
    base = t & 0x7FFF
    return {FILE_TYPE_UNKNOWN: "UNKNOWN", FILE_TYPE_DISK: "DISK",
            FILE_TYPE_CHAR: "CHAR", FILE_TYPE_PIPE: "PIPE"}.get(base, f"OTHER({t:#x})")


def probe(pid: int, target_path: str) -> dict:
    k = _k32()
    PROCESS_DUP_HANDLE = 0x0040
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    me = k.GetCurrentProcess()
    out = {"pid": pid, "target_path": str(Path(target_path).resolve()), "parts": {}}

    # A. GetProcessHandleCount (independent total) vs enumerator total
    hq = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if hq:
        cnt = wintypes.DWORD(0)
        got = bool(k.GetProcessHandleCount(hq, ctypes.byref(cnt)))
        out["parts"]["handle_count"] = {"ok": got, "count": int(cnt.value) if got else None}
        k.CloseHandle(hq)
    else:
        out["parts"]["handle_count"] = {"ok": False, "err": k.GetLastError()}

    all_handles = list(HA._iter_handles(pid))
    out["parts"]["enum16_total"] = len(all_handles)
    try:
        out["parts"]["enum64_total"] = len(T0.enumerate_class64(pid))
    except Exception as e:                                        # noqa: BLE001
        out["parts"]["enum64_total"] = f"ERR:{type(e).__name__}"

    target_id = HA.file_identity(target_path)
    out["parts"]["target_identity"] = list(target_id) if target_id else None
    ftype = HA._file_type_index(target_path)
    out["parts"]["file_type_index"] = ftype

    # B. For file-type handles: file identity OR GetFileType / name classification
    detail = []
    for hv, tp, acc in all_handles:
        if tp != ftype:
            continue
        rec = {"hv": hv, "acc": acc}
        hproc = k.OpenProcess(PROCESS_DUP_HANDLE, False, pid)
        if not hproc:
            rec["openprocess_err"] = k.GetLastError()
            detail.append(rec)
            continue
        try:
            dup = ctypes.c_void_p()
            if not k.DuplicateHandle(hproc, ctypes.c_void_p(hv), me, ctypes.byref(dup),
                                     0, False, 0x00000002):
                rec["dup_err"] = k.GetLastError()
                detail.append(rec)
                continue
            try:
                fid = HA.handle_file_identity(dup)
                rec["file_identity"] = list(fid) if fid else None
                rec["is_target_by_identity"] = (fid is not None and fid == target_id)
                # OS object-type signal for handles without a file identity
                ft = k.GetFileType(dup)
                rec["GetFileType"] = {"raw": int(ft), "name": _file_type_name(int(ft))}
                try:
                    nm = HA._name_of_remote_handle(pid, hv)
                except Exception:                                 # noqa: BLE001
                    nm = None
                rec["name"] = nm
            finally:
                k.CloseHandle(dup)
        finally:
            k.CloseHandle(hproc)
        detail.append(rec)
    out["parts"]["file_type_handles"] = detail

    # summarise feasibility signals
    id_known = [r for r in detail if r.get("file_identity")]
    no_id = [r for r in detail if not r.get("file_identity")]
    out["parts"]["summary"] = {
        "file_type_total": len(detail),
        "identity_known": len(id_known),
        "identity_unknown": len(no_id),
        "unknown_filetypes": sorted({r.get("GetFileType", {}).get("name", "?")
                                     for r in no_id}),
        "count_matches_enum16": (out["parts"].get("handle_count", {}).get("count")
                                 == out["parts"]["enum16_total"]),
        "enum16_matches_enum64": (out["parts"]["enum16_total"]
                                  == out["parts"].get("enum64_total")),
    }
    return out


def main(argv):
    if len(argv) != 2:
        print("usage: c_feasibility_probe.py <fixture_dir>")
        return 2
    pw = os.environ.get("AFTERGLOW_WORKER_PASSWORD")
    if not pw:
        print("need AFTERGLOW_WORKER_PASSWORD"); return 2
    acct = os.environ.get("AFTERGLOW_WORKER_ACCOUNT", "afterglow_worker")
    base = Path(argv[1]); base.mkdir(parents=True, exist_ok=True)
    subprocess.run(["icacls", str(base), "/grant", f"{acct}:(OI)(CI)M"], capture_output=True)
    protected = base / "protected.bin"; protected.write_bytes(b"protected")
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
    sc.write_text("import os,time,json,msvcrt\n"
                  f"p=open(r'{protected}','rb')\n"
                  "hp=msvcrt.get_osfhandle(p.fileno())\n"
                  f"open(r'{hs}','w').write(json.dumps({{'pid':os.getpid(),'prot':hp}}))\n"
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
    print("worker pid", pi.pid, "protected handle", rep.get("prot"))
    out = probe(pi.pid, str(protected))
    print(json.dumps(out, indent=2, ensure_ascii=False))
    k32.TerminateProcess(pi.hp, 1); k32.CloseHandle(pi.hp); k32.CloseHandle(pi.ht)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
