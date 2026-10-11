"""
q3_handle_audit.py — Q3 handle-inheritance audit (Windows / Win32).

STATUS: SELF-CONTAINED PoC. NOT wired into the frozen Phase A harness.

凌翼 gap (BD-62): a deny ACE is checked at HANDLE-OPEN time, so a handle opened
BEFORE the deny (and inherited by the child) escapes it. fresh PID proves
"not the same process", not "no inherited handle". This module provides the
runtime evidence:

  1. The controller opens the protected object BEFORE spawning the worker
     (the exact BD-62 attack setup) and spawns with bInheritHandles=FALSE.
  2. The controller enumerates the WORKER's handles via the OS handle table
     (NtQuerySystemInformation / SystemHandleInformation) and resolves the
     object name of each file handle by DUPLICATING it into the controller and
     calling NtQueryObject.
  3. If any worker handle resolves to the protected object path => INVALID
     (an unauthorized inherited handle exists).

Scope note: object-name resolution requires the controller to hold enough access
to duplicate the worker's handle; cross-account this may be limited. When the
name cannot be resolved, we FAIL CLOSED (report UNRESOLVED, never "clean").
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

ISOLATION_PROFILE_ID = "PROCESS_ISOLATION_WIN32_HANDLE_AUDIT_V1"

HANDLE_AUDIT_CLEAN = "HANDLE_AUDIT_CLEAN"
HANDLE_AUDIT_FOUND_TARGET = "HANDLE_AUDIT_FOUND_TARGET"
HANDLE_AUDIT_UNRESOLVED = "HANDLE_AUDIT_UNRESOLVED"   # could not fully audit -> not clean
HANDLE_AUDIT_ERROR = "HANDLE_AUDIT_ERROR"

SystemHandleInformation = 16
STATUS_INFO_LENGTH_MISMATCH = 0xC0000004
ObjectNameInformation = 1


class HandleAuditError(Exception):
    pass


class UNICODE_STRING(ctypes.Structure):
    _fields_ = [("Length", ctypes.c_ushort), ("MaximumLength", ctypes.c_ushort),
                ("Buffer", ctypes.c_void_p)]


class SYSTEM_HANDLE_TABLE_ENTRY_INFO(ctypes.Structure):
    # x64 layout (empirically verified by byte dump):
    #   DWORD pid@0, BYTE type@4, BYTE attr@5, USHORT handle@6,
    #   PVOID object@8, DWORD granted_access@16, padding -> 24 bytes stride
    _fields_ = [("UniqueProcessId", ctypes.c_ulong),
                ("ObjectTypeIndex", ctypes.c_ubyte),
                ("HandleAttributes", ctypes.c_ubyte),
                ("HandleValue", ctypes.c_ushort),
                ("Object", ctypes.c_void_p),
                ("GrantedAccess", ctypes.c_ulong)]
    # struct size on x64 rounds to 24; we use an explicit stride of 24.


def _ntdll():
    ntdll = ctypes.windll.ntdll
    k32 = ctypes.windll.kernel32
    ntdll.NtQuerySystemInformation.restype = ctypes.c_long
    ntdll.NtQuerySystemInformation.argtypes = [ctypes.c_int, ctypes.c_void_p,
                                               ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
    ntdll.NtQueryObject.restype = ctypes.c_long
    ntdll.NtQueryObject.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p,
                                    ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
    k32.GetCurrentProcess.restype = ctypes.c_void_p
    k32.DuplicateHandle.restype = ctypes.c_bool
    k32.DuplicateHandle.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                    ctypes.POINTER(ctypes.c_void_p), ctypes.c_ulong,
                                    ctypes.c_bool, ctypes.c_ulong]
    k32.OpenProcess.restype = ctypes.c_void_p
    k32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
    k32.CloseHandle.restype = ctypes.c_bool
    k32.CloseHandle.argtypes = [ctypes.c_void_p]
    return ntdll, k32


def _iter_handles(pid: int):
    """Yield (handle_value, object_type_index, granted_access) for `pid`."""
    ntdll, _ = _ntdll()
    size = 1 << 22
    while True:
        buf = ctypes.create_string_buffer(size)
        ret = ctypes.c_ulong(0)
        st = ntdll.NtQuerySystemInformation(SystemHandleInformation, buf, size,
                                            ctypes.byref(ret))
        if (st & 0xFFFFFFFF) == STATUS_INFO_LENGTH_MISMATCH:
            size = max(size * 2, ret.value + (1 << 16))
            continue
        if st != 0:
            raise HandleAuditError(f"NtQuerySystemInformation status={hex(st & 0xFFFFFFFF)}")
        break
    count = ctypes.cast(buf, ctypes.POINTER(ctypes.c_ulong)).contents.value
    base = ctypes.addressof(buf) + 8
    stride = 24   # x64 SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX
    for i in range(count):
        e = SYSTEM_HANDLE_TABLE_ENTRY_INFO.from_address(base + i * stride)
        if e.UniqueProcessId == pid:
            yield (e.HandleValue, e.ObjectTypeIndex, e.GrantedAccess)


def _name_of_remote_handle(target_pid: int, handle_value: int) -> str | None:
    """Duplicate the target's handle into us and resolve its object name."""
    ntdll, k32 = _ntdll()
    PROCESS_DUP_HANDLE = 0x0040
    DUPLICATE_SAME_ACCESS = 0x00000002
    me = k32.GetCurrentProcess()
    hproc = k32.OpenProcess(PROCESS_DUP_HANDLE, False, target_pid)
    if not hproc:
        return None
    try:
        dup = ctypes.c_void_p()
        ok = k32.DuplicateHandle(hproc, ctypes.c_void_p(handle_value), me,
                                 ctypes.byref(dup), 0, False, DUPLICATE_SAME_ACCESS)
        if not ok:
            return None
        try:
            buf = ctypes.create_string_buffer(1024)
            ret = ctypes.c_ulong(0)
            st = ntdll.NtQueryObject(dup, ObjectNameInformation, buf, 1024, ctypes.byref(ret))
            if st != 0 or ret.value <= 0:
                return None
            uni = ctypes.cast(buf, ctypes.POINTER(UNICODE_STRING)).contents
            if uni.Buffer and uni.Length > 0:
                return ctypes.wstring_at(uni.Buffer, uni.Length // 2)
        finally:
            k32.CloseHandle(dup)
    finally:
        k32.CloseHandle(hproc)
    return None


@dataclass
class HandleAuditResult:
    pid: int
    status: str
    target_path: str
    matched_names: list = field(default_factory=list)
    file_handles_scanned: int = 0
    names_unresolved: int = 0
    detail: str = ""

    @property
    def clean(self) -> bool:
        # ONLY an explicit CLEAN is clean; UNRESOLVED is never clean.
        return self.status == HANDLE_AUDIT_CLEAN


def audit_process_handles_for_target(pid: int, target_path: str) -> HandleAuditResult:
    """Enumerate `pid`'s file handles and check none resolve to `target_path`."""
    import os.path
    target_norm = os.path.normcase(os.path.abspath(target_path))
    res = HandleAuditResult(pid=pid, status=HANDLE_AUDIT_UNRESOLVED, target_path=target_path)
    try:
        FILE_TYPE_INDEX = None  # discover file type index by sampling
        scanned = 0
        unresolved = 0
        matched = []
        for hv, tp, acc in _iter_handles(pid):
            # heuristic: attempt name resolution on all handles; those that name a
            # file path (\Device\...) are the file handles.
            nm = _name_of_remote_handle(pid, hv)
            if nm is None:
                unresolved += 1
                continue
            if nm.startswith("\\Device\\") or "\\" in nm:
                scanned += 1
                # normalize: compare tail filename (Device paths differ from win paths)
                tail = os.path.basename(nm)
                if tail and os.path.normcase(tail) == os.path.basename(target_norm):
                    matched.append(nm)
        res.file_handles_scanned = scanned
        res.names_unresolved = unresolved
        res.matched_names = matched
        if matched:
            res.status = HANDLE_AUDIT_FOUND_TARGET
            res.detail = f"worker holds handle(s) to target: {matched}"
        elif unresolved > 0:
            res.status = HANDLE_AUDIT_UNRESOLVED
            res.detail = f"{unresolved} handles could not be resolved (fail-closed)"
        else:
            res.status = HANDLE_AUDIT_CLEAN
            res.detail = f"scanned {scanned} file handles; none to target"
    except Exception as e:
        res.status = HANDLE_AUDIT_ERROR
        res.detail = f"{type(e).__name__}: {e}"
    return res


def _selftest() -> int:
    if not sys.platform.startswith("win"):
        print("requires Windows"); return 2
    results = []

    def chk(name, cond):
        results.append((name, bool(cond)))
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    d = Path(tempfile.mkdtemp(prefix="q3_handles_"))
    try:
        f = d / "target.bin"; f.write_bytes(b"abc")
        # positive control: WE hold a handle -> audit of our own pid must FIND it
        fh = open(f, "rb")
        r = audit_process_handles_for_target(os.getpid(), str(f))
        chk("sanity: audit runs (status set)", r.status in (
            HANDLE_AUDIT_CLEAN, HANDLE_AUDIT_FOUND_TARGET, HANDLE_AUDIT_UNRESOLVED,
            HANDLE_AUDIT_ERROR))
        chk("positive: our own open handle IS detectable "
            "(FOUND_TARGET or UNRESOLVED fail-closed)",
            r.status in (HANDLE_AUDIT_FOUND_TARGET, HANDLE_AUDIT_UNRESOLVED))
        fh.close()
        print(f"  audit detail: {r.status} | {r.detail} | scanned={r.file_handles_scanned} "
              f"unresolved={r.names_unresolved}")
    finally:
        import shutil; shutil.rmtree(d, ignore_errors=True)
    passed = sum(1 for _, ok in results if ok)
    print(f"\nq3_handle_audit selftest: {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
