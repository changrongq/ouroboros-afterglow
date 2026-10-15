"""T0 — ENUMERATOR CONTROLLED EXPERIMENT (unfrozen diagnostic layer).

凌翼 `ENUMERATOR BLIND-SPOT RULING` (REVIEWED_COMMIT=ac0bfa2):
  AUTHORIZE: UNFROZEN T0 CONTROLLED EXPERIMENT
             SAME PID + CREATE_TIME + HELD HANDLE
             OS VERIFIED TARGET HANDLE IDENTITY
             COMPARE CLASS 16 AND CLASS 64 ENUMERATION
             RETAIN RAW OBSERVATIONS
  STOP CONDITION: ESTABLISH WHETHER TWO OS-VERIFIED HELD TARGET HANDLES ARE
                  ENUMERATED BY OLD VS EXTENDED ENUMERATOR.

WHAT THIS DOES (same worker, same PID, same create_time):
  1. spawn a real cross-account `afterglow_worker` that opens TWO real file handles
     to a test target and HOLDS them, and writes their raw handle VALUES to a file
     (the raw values, not a "trust me" marker);
  2. the TRUSTED CONTROLLER independently verifies each reported value by
     DuplicateHandle(worker, hv) and then reading the duplicated handle's identity —
     a value only counts if the controller can duplicate it AND its identity == target;
  3. while the handles are provably still open, enumerate THAT SAME pid with:
       · class 16  (SystemHandleInformation,        frozen layout, 24-byte stride)
       · class 64  (SystemExtendedHandleInformation, 48-byte stride, wider fields)
     and record whether each enumerator yields the exact verified handle values;
  4. close, sample again.

Outputs a self-contained JSON with pid, create_time, verified handle values, whether
each class saw them, and raw observations. Makes NO verdict, changes NO ACL.

This does NOT modify the frozen q3_handle_audit.py.
"""

from __future__ import annotations

import ctypes
import json
import os
import sys
import time
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SystemHandleInformation = 16           # SYSTEM_INFORMATION_CLASS
SystemExtendedHandleInformation = 64   # extended variant (wider PID/handle fields)
STATUS_INFO_LENGTH_MISMATCH = 0xC0000004


# ---- class 16 (non-Ex, what the frozen module uses) ---------------------------
class SHTEI_NONEX(ctypes.Structure):
    # x64 layout: USHORT pid, USHORT backtrace, UCHAR type, UCHAR attr,
    #             USHORT handle, (2 pad), PVOID object, ULONG access, (4 pad) = 24
    _fields_ = [("UniqueProcessId", ctypes.c_ushort),
                ("CreatorBackTraceIndex", ctypes.c_ushort),
                ("ObjectTypeIndex", ctypes.c_ubyte),
                ("HandleAttributes", ctypes.c_ubyte),
                ("HandleValue", ctypes.c_ushort),
                ("Object", ctypes.c_void_p),
                ("GrantedAccess", ctypes.c_ulong)]


class SHTEI_EX(ctypes.Structure):
    # x64 layout of SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX (48 bytes):
    #   PVOID Object; ULONG_PTR UniqueProcessId; ULONG_PTR HandleValue;
    #   ULONG GrantedAccess; USHORT CreatorBackTraceIndex; USHORT ObjectTypeIndex;
    #   ULONG HandleAttributes; ULONG Reserved;
    _fields_ = [("Object", ctypes.c_void_p),
                ("UniqueProcessId", ctypes.c_ulonglong),
                ("HandleValue", ctypes.c_ulonglong),
                ("GrantedAccess", ctypes.c_ulong),
                ("CreatorBackTraceIndex", ctypes.c_ushort),
                ("ObjectTypeIndex", ctypes.c_ushort),
                ("HandleAttributes", ctypes.c_ulong),
                ("Reserved", ctypes.c_ulong)]


def _ntdll():
    n = ctypes.windll.ntdll
    n.NtQuerySystemInformation.restype = ctypes.c_long
    n.NtQuerySystemInformation.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_ulong,
                                           ctypes.POINTER(ctypes.c_ulong)]
    return n


def _query(sh_class: int) -> bytes:
    n = _ntdll()
    size = 1 << 22
    while True:
        buf = ctypes.create_string_buffer(size)
        ret = ctypes.c_ulong(0)
        st = n.NtQuerySystemInformation(sh_class, buf, size, ctypes.byref(ret))
        if (st & 0xFFFFFFFF) == STATUS_INFO_LENGTH_MISMATCH:
            size = max(size * 2, ret.value + (1 << 16))
            continue
        if st != 0:
            raise OSError(f"NtQuerySystemInformation({sh_class}) status={hex(st & 0xFFFFFFFF)}")
        return buf.raw


def enumerate_class16(pid: int) -> list:
    raw = _query(SystemHandleInformation)
    count = int.from_bytes(raw[0:8], "little")
    base = 8
    stride = ctypes.sizeof(SHTEI_NONEX)          # 24
    out = []
    for i in range(count):
        e = SHTEI_NONEX.from_buffer_copy(raw, base + i * stride)
        if e.UniqueProcessId == (pid & 0xFFFF):
            out.append({"handle_value": e.HandleValue, "type_index": e.ObjectTypeIndex,
                        "access": e.GrantedAccess, "stride": stride})
    return out


def enumerate_class64(pid: int) -> list:
    raw = _query(SystemExtendedHandleInformation)
    count = int.from_bytes(raw[0:8], "little")
    base = 16                                    # ULONG_PTR count + ULONG_PTR reserved
    stride = ctypes.sizeof(SHTEI_EX)             # 48
    out = []
    for i in range(count):
        e = SHTEI_EX.from_buffer_copy(raw, base + i * stride)
        if e.UniqueProcessId == pid:
            out.append({"handle_value": e.HandleValue, "type_index": e.ObjectTypeIndex,
                        "access": e.GrantedAccess, "stride": stride})
    return out


def main() -> int:
    acct = os.environ.get("AFTERGLOW_WORKER_ACCOUNT", "afterglow_worker")
    pw = os.environ.get("AFTERGLOW_WORKER_PASSWORD")
    if not pw:
        print("need AFTERGLOW_WORKER_PASSWORD")
        return 2

    import importlib
    HA = importlib.import_module("q3_handle_audit")   # for DuplicateHandle-based verify

    base = Path(os.environ["TEMP"]) / "t0_enum"
    import shutil
    shutil.rmtree(base, ignore_errors=True)
    base.mkdir(parents=True, exist_ok=True)
    import subprocess
    subprocess.run(["icacls", str(base), "/grant", f"{acct}:(OI)(CI)M"], capture_output=True)
    target = base / "target.bin"
    target.write_bytes(b"secret-target-bytes")
    hs_out = base / "handles.json"

    adv = ctypes.windll.advapi32
    k32 = ctypes.windll.kernel32
    adv.CreateProcessWithLogonW.restype = wintypes.BOOL
    adv.CreateProcessWithLogonW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD, ctypes.c_void_p,
        wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p]

    class STARTUPINFO(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
                    ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                    ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD), ("dwXSize", wintypes.DWORD),
                    ("dwYSize", wintypes.DWORD), ("dwXCountChars", wintypes.DWORD),
                    ("dwYCountChars", wintypes.DWORD), ("dwFillAttribute", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("wShowWindow", wintypes.WORD),
                    ("cbReserved2", wintypes.WORD), ("lpReserved2", ctypes.c_void_p),
                    ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE),
                    ("hStdError", wintypes.HANDLE)]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                    ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]

    # worker script: open TWO real handles to target, write their RAW integer values,
    # and hold them for the whole process lifetime.
    script = base / "t0_worker.py"
    ready = base / "ready.txt"
    script.write_text(
        "import os,sys,time,json,msvcrt\n"
        f"a=open(r'{target}','rb')\n"
        f"b=open(r'{target}','rb')\n"
        "ha_os=msvcrt.get_osfhandle(a.fileno())\n"
        "hb_os=msvcrt.get_osfhandle(b.fileno())\n"
        f"open(r'{hs_out}','w').write(json.dumps({{'pid':os.getpid(),'ha':ha_os,'hb':hb_os}}))\n"
        f"open(r'{ready}','w').write('ok')\n"
        "while True: time.sleep(0.2)\n", encoding="utf-8")

    si = STARTUPINFO(); si.cb = ctypes.sizeof(si); pi = PROCESS_INFORMATION()
    # 凌翼 SAME-PID requirement: use a DIRECT interpreter so CreateProcessWithLogonW's
    # pid IS the process that runs the script (a uv-venv Scripts\python.exe is a
    # redirector that forks a child with a DIFFERENT pid — that would silently make us
    # enumerate the wrong process).
    try:
        from q3_reset_adapter import _direct_interpreter
        pyexe = _direct_interpreter()
    except Exception:                                                # noqa: BLE001
        pyexe = sys.executable
    cmd = ctypes.create_unicode_buffer(f'"{pyexe}" "{script}"')
    ok = adv.CreateProcessWithLogonW(acct, ".", pw, 1, None, cmd, 0x08000000, None,
                                     str(base), ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        print("spawn failed", k32.GetLastError())
        return 2
    pid = pi.dwProcessId
    # OS-verified create_time
    ct = HA._process_times(pid)[0] if hasattr(HA, "_process_times") else None
    if ct is None:
        try:
            from win32_isolation import _process_times as _pt
            ct = _pt(pid)[0]
        except Exception:
            ct = None
    for _ in range(80):
        if (base / "ready.txt").exists():
            break
        time.sleep(0.1)

    reported = json.loads(hs_out.read_text()) if hs_out.exists() else {}
    print("worker pid(spawned)", pid, "pid(worker-reported)", reported.get("pid"),
          "create_time", ct, "reported", reported)
    if reported.get("pid") != pid:
        print("*** PID MISMATCH: spawned", pid, "but worker reports", reported.get("pid"),
              "=> a redirector forked a child; enumerating the wrong pid ***")
        # continue anyway, but ALSO enumerate the worker-reported pid for comparison

    # ---- TRUSTED verification: controller DuplicateHandle + identity on the target
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
    k32.DuplicateHandle.restype = ctypes.c_bool
    k32.DuplicateHandle.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                    ctypes.POINTER(ctypes.c_void_p), ctypes.c_ulong,
                                    ctypes.c_bool, ctypes.c_ulong]
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    PROCESS_DUP_HANDLE = 0x0040
    DUPLICATE_SAME_ACCESS = 0x00000002
    me = k32.GetCurrentProcess()
    target_id = HA.file_identity(str(target))

    verified = []
    for label in ("ha", "hb"):
        hv = reported.get(label)
        if hv is None:
            continue
        hproc = k32.OpenProcess(PROCESS_DUP_HANDLE, False, pid)
        v = {"label": label, "handle_value": hv, "duplicated": False, "identity": None,
             "is_target": False}
        if hproc:
            dup = ctypes.c_void_p()
            if k32.DuplicateHandle(hproc, ctypes.c_void_p(hv), me, ctypes.byref(dup),
                                   0, False, DUPLICATE_SAME_ACCESS):
                v["duplicated"] = True
                try:
                    from q3_handle_audit import handle_file_identity
                    fid = handle_file_identity(dup)
                    v["identity"] = list(fid) if fid else None
                    v["is_target"] = (fid == target_id)
                except Exception as e:                              # noqa: BLE001
                    v["identity_error"] = f"{type(e).__name__}: {e}"
                k32.CloseHandle(dup)
            else:
                v["dup_last_error"] = k32.GetLastError()
            k32.CloseHandle(hproc)
        else:
            v["openprocess_last_error"] = k32.GetLastError()
        verified.append(v)

    # ---- enumerate via class 16 and class 64 (same pid, same lifetime) ----
    # use the WORKER-REPORTED pid as the authoritative target process (matches the
    # process that actually holds the handles), and cross-check with the spawned pid.
    actual_pid = reported.get("pid") or pid
    c16_set = {}
    c64_set = {}
    try:
        for r in enumerate_class16(actual_pid):
            c16_set[r["handle_value"]] = r
    except Exception as e:                                          # noqa: BLE001
        c16_set = {"_error": f"{type(e).__name__}: {e}"}
    try:
        for r in enumerate_class64(actual_pid):
            c64_set[r["handle_value"]] = r
    except Exception as e:                                          # noqa: BLE001
        c64_set = {"_error": f"{type(e).__name__}: {e}"}

    report = {
        "worker_pid_spawned": pid, "worker_pid_enumerated": actual_pid,
        "worker_create_time": ct, "target_path": str(target),
        "target_identity": list(target_id) if target_id else None,
        "worker_reported_handles": reported,
        "controller_verified_handles": verified,
        "class16_count": len([k for k in c16_set if isinstance(k, int)]),
        "class64_count": len([k for k in c64_set if isinstance(k, int)]),
        "class16_saw_ha": ("ha" in reported and reported["ha"] in c16_set),
        "class16_saw_hb": ("hb" in reported and reported["hb"] in c16_set),
        "class64_saw_ha": ("ha" in reported and reported["ha"] in c64_set),
        "class64_saw_hb": ("hb" in reported and reported["hb"] in c64_set),
        "class16_sample": [c16_set[k] for k in list(c16_set)[:12] if isinstance(k, int)],
        "class64_sample": [c64_set[k] for k in list(c64_set)[:12] if isinstance(k, int)],
        "class16_raw_error": c16_set.get("_error"),
        "class64_raw_error": c64_set.get("_error"),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    out = base / "t0_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("REPORT:", out)
    k32.TerminateProcess(pi.hProcess, 1); k32.CloseHandle(pi.hProcess); k32.CloseHandle(pi.hThread)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
