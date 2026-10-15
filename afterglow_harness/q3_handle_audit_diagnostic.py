"""Q3 business-worker handle-audit DIAGNOSTIC (unfrozen observer layer).

知微 (11eeb65 admin replay, 2026-10-15): `audit_process_handles_for_target()` returns
HANDLE_AUDIT_UNRESOLVED with file_handles_scanned=0 / names_unresolved=11 even UNDER
an elevated token. The frozen audit MERGES 4 distinct failure points into None/unknown
WITHOUT keeping GetLastError:

  · q3_handle_audit.py:210  OpenProcess(PROCESS_DUP_HANDLE) failed
  · q3_handle_audit.py:214  DuplicateHandle(...) failed
  · q3_handle_audit.py:168  GetFileInformationByHandle(...) failed

This module does NOT modify the frozen q3_handle_audit.py. It REIMPLEMENTS the loop in
an unfrozen observer that records, per FILE-type handle of the target process:

  · handle value, granted access, type index
  · OpenProcess(PROCESS_DUP_HANDLE) return + GetLastError
  · DuplicateHandle(...) return + GetLastError
  · GetFileInformationByHandle(...) return + GetLastError   (via the duplicated handle)
  · the resolved file identity (if any)

and ALSO records the CONTROLLER token's relevant privilege state (SeDebugPrivilege)
presence + enabled-ness — so we can tell "call failed" from "privilege absent".

Usage:
    python q3_handle_audit_diagnostic.py <target_pid> <target_path>

This is a DIAGNOSTIC; it makes NO verdict and changes NO ACL.
"""

from __future__ import annotations

import ctypes
import json
import sys
from ctypes import wintypes
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import q3_handle_audit as HA  # frozen module, read-only use of its helpers


def _k32():
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.DuplicateHandle.restype = wintypes.BOOL
    k.DuplicateHandle.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p),
        wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.GetFileInformationByHandle.restype = wintypes.BOOL
    k.GetFileInformationByHandle.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(HA.BY_HANDLE_FILE_INFORMATION)]
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    k.GetCurrentProcess.restype = wintypes.HANDLE
    return k


def _token_privileges() -> dict:
    """Record whether SeDebugPrivilege (and SeBackup/SeRestore) are present/enabled
    in the CURRENT (controller) token — 知微's 'record privilege presence' request."""
    adv = ctypes.windll.advapi32
    k = ctypes.windll.kernel32
    TOKEN_QUERY = 0x0008
    TokenPrivileges = 3
    adv.OpenProcessToken.restype = wintypes.BOOL
    adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                     ctypes.POINTER(wintypes.HANDLE)]
    adv.LookupPrivilegeValueW.restype = wintypes.BOOL
    adv.LookupPrivilegeValueW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR,
                                          ctypes.c_void_p]
    adv.GetTokenInformation.restype = wintypes.BOOL
    adv.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.GetCurrentProcess.argtypes = []
    k.CloseHandle.argtypes = [wintypes.HANDLE]

    class LUID(ctypes.Structure):
        _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]

    class LUID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]

    class TOKEN_PRIVILEGES(ctypes.Structure):
        _fields_ = [("PrivilegeCount", wintypes.DWORD),
                    ("Privileges", LUID_AND_ATTRIBUTES * 1)]

    out = {}
    h = wintypes.HANDLE()
    if not adv.OpenProcessToken(k.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(h)):
        return {"error": f"OpenProcessToken failed ({k.GetLastError()})"}
    try:
        for name in ("SeDebugPrivilege", "SeBackupPrivilege", "SeRestorePrivilege"):
            luid = LUID()
            if not adv.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
                out[name] = "lookup-failed"
                continue
            tp = TOKEN_PRIVILEGES()
            size = wintypes.DWORD(0)
            adv.GetTokenInformation(h, TokenPrivileges, None, 0, ctypes.byref(size))
            buf = ctypes.create_string_buffer(size.value)
            if not adv.GetTokenInformation(h, TokenPrivileges, buf, size.value, ctypes.byref(size)):
                out[name] = "query-failed"
                continue
            # scan returned privileges for this LUID
            arr = ctypes.cast(buf, ctypes.POINTER(TOKEN_PRIVILEGES)).contents
            found = None
            full = ctypes.cast(buf, ctypes.POINTER(LUID_AND_ATTRIBUTES * max(1, arr.PrivilegeCount)))
            for i in range(arr.PrivilegeCount):
                la = full.contents[i]
                if la.Luid.LowPart == luid.LowPart and la.Luid.HighPart == luid.HighPart:
                    found = la.Attributes
                    break
            if found is None:
                out[name] = "absent"
            else:
                SE_PRIVILEGE_ENABLED = 0x00000002
                out[name] = ("enabled" if (found & SE_PRIVILEGE_ENABLED) else "present-disabled")
    finally:
        k.CloseHandle(h)
    return out


def diagnose(target_pid: int, target_path: str) -> dict:
    k = _k32()
    PROCESS_DUP_HANDLE = 0x0040
    DUPLICATE_SAME_ACCESS = 0x00000002
    me = k.GetCurrentProcess()

    report = {
        "target_pid": target_pid,
        "target_path": str(Path(target_path).resolve()),
        "target_file_identity": HA.file_identity(target_path),
        "controller_token_privileges": _token_privileges(),
        "file_type_index": None,
        "handles": [],
        "summary": {},
    }
    try:
        file_type = HA._file_type_index(target_path)
    except Exception as e:  # noqa: BLE001
        report["file_type_index_error"] = f"{type(e).__name__}: {e}"
        file_type = None
    report["file_type_index"] = file_type

    counts = {"file_type_total": 0, "openprocess_fail": 0, "duplicate_fail": 0,
              "getfileinfo_fail": 0, "resolved": 0, "non_file_skipped": 0}
    for hv, tp, acc in HA._iter_handles(target_pid):
        if tp != file_type:
            counts["non_file_skipped"] += 1
            continue
        counts["file_type_total"] += 1
        rec = {"handle_value": hv, "type_index": tp, "granted_access": acc}
        # (1) OpenProcess(PROCESS_DUP_HANDLE)
        hproc = k.OpenProcess(PROCESS_DUP_HANDLE, False, target_pid)
        if not hproc:
            rec["openprocess"] = {"ok": False, "GetLastError": k.GetLastError()}
            counts["openprocess_fail"] += 1
            report["handles"].append(rec)
            continue
        rec["openprocess"] = {"ok": True}
        try:
            # (2) DuplicateHandle
            dup = ctypes.c_void_p()
            ok = k.DuplicateHandle(hproc, ctypes.c_void_p(hv), me, ctypes.byref(dup),
                                   0, False, DUPLICATE_SAME_ACCESS)
            if not ok:
                rec["duplicate"] = {"ok": False, "GetLastError": k.GetLastError()}
                counts["duplicate_fail"] += 1
                report["handles"].append(rec)
                continue
            rec["duplicate"] = {"ok": True, "dup_handle": dup.value}
            try:
                # (3) GetFileInformationByHandle
                info = HA.BY_HANDLE_FILE_INFORMATION()
                ok2 = k.GetFileInformationByHandle(dup, ctypes.byref(info))
                if not ok2:
                    rec["getfileinformation"] = {"ok": False, "GetLastError": k.GetLastError()}
                    counts["getfileinfo_fail"] += 1
                    # ALSO try the NAME path (NtQueryObject) to see if it works where
                    # identity fails — this gives 凌翼 a concrete fix direction.
                    try:
                        nm = HA._name_of_remote_handle(target_pid, hv)
                        rec["name_via_ntqueryobject"] = nm
                    except Exception as e:  # noqa: BLE001
                        rec["name_via_ntqueryobject"] = f"ERROR:{type(e).__name__}"
                else:
                    fid = (info.dwVolumeSerialNumber, info.nFileIndexHigh, info.nFileIndexLow)
                    rec["getfileinformation"] = {"ok": True, "file_identity": list(fid),
                                                 "is_target": fid == report["target_file_identity"]}
                    counts["resolved"] += 1
            finally:
                k.CloseHandle(dup)
        finally:
            k.CloseHandle(hproc)
        report["handles"].append(rec)

    report["summary"] = counts
    return report


def main(argv) -> int:
    if len(argv) != 3:
        print("usage: q3_handle_audit_diagnostic.py <target_pid> <target_path>")
        return 2
    rep = diagnose(int(argv[1]), argv[2])
    print(json.dumps(rep, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
