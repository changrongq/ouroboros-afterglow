"""Verify the M-1 API premise that 凌翼 asked to be revised.

His ruling says: "同时修订 M-1 的 bInheritHandles API 前提."

The draft's M-1 said:
    bInheritHandles=FALSE + PROC_THREAD_ATTRIBUTE_HANDLE_LIST

The technical question is whether those two are combinable at all, because the
documented behaviour is:

    HANDLE_LIST requires bInheritHandles=TRUE.
    If HANDLE_LIST is supplied with bInheritHandles=FALSE, CreateProcess fails with
    ERROR_INVALID_PARAMETER (87).

If that is true, my draft's M-1 was WRONG AS WRITTEN: "bInheritHandles=FALSE +
HANDLE_LIST" is not a real configuration. The correct statements would be either
    (a) bInheritHandles=FALSE, no list  -> nothing inherited at all, or
    (b) bInheritHandles=TRUE + HANDLE_LIST -> exactly the listed handles inherit.

This driver MEASURES the behaviour on this machine instead of quoting docs.

DESIGN-ANALYSIS SUPPORT ONLY. It creates a short-lived inert child process, inherits
nothing sensitive, and proves nothing about isolation. It does not open, test, or touch
any protected object and it does not start a business worker.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

RESULTS: list = []


def check(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


EXTENDED_STARTUPINFO_PRESENT = 0x00080000
CREATE_NO_WINDOW = 0x08000000
PROC_THREAD_ATTRIBUTE_HANDLE_LIST = 0x00020002
ERROR_INVALID_PARAMETER = 87


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
                ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                ("dwXCountChars", wintypes.DWORD),
                ("dwYCountChars", wintypes.DWORD),
                ("dwFillAttribute", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("wShowWindow", wintypes.WORD),
                ("cbReserved2", wintypes.WORD),
                ("lpReserved2", ctypes.c_void_p),
                ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE),
                ("hStdError", wintypes.HANDLE)]


class STARTUPINFOEXW(ctypes.Structure):
    _fields_ = [("StartupInfo", STARTUPINFOW),
                ("lpAttributeList", ctypes.c_void_p)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]


def try_spawn(inherit: bool, with_list: bool):
    """Attempt CreateProcess with the requested handle-inheritance configuration.

    Returns (ok: bool, err: int). Spawns a trivial child that exits immediately when it
    succeeds, and closes it.
    """
    k32 = ctypes.windll.kernel32
    k32.CreateProcessW.restype = wintypes.BOOL
    k32.CreateProcessW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
        wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
        ctypes.c_void_p, ctypes.c_void_p]

    si = STARTUPINFOEXW()
    si.StartupInfo.cb = ctypes.sizeof(si)
    pi = PROCESS_INFORMATION()
    flags = EXTENDED_STARTUPINFO_PRESENT | CREATE_NO_WINDOW

    attr_buf = None
    if with_list:
        # build an attribute list containing one harmless inheritable handle (stdin NUL)
        size = ctypes.c_size_t(0)
        k32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
        attr_buf = ctypes.create_string_buffer(size.value)
        ok = k32.InitializeProcThreadAttributeList(
            ctypes.cast(attr_buf, ctypes.c_void_p), 1, 0, ctypes.byref(size))
        if not ok:
            return False, k32.GetLastError()
        # an EMPTY list is not allowed; provide the std input handle
        h_in = k32.GetStdHandle(-10)
        arr = (wintypes.HANDLE * 1)(h_in)
        ok = k32.UpdateProcThreadAttribute(
            ctypes.cast(attr_buf, ctypes.c_void_p), 0,
            PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
            ctypes.cast(arr, ctypes.c_void_p),
            ctypes.sizeof(arr), None, None)
        if not ok:
            return False, k32.GetLastError()
        si.lpAttributeList = ctypes.cast(attr_buf, ctypes.c_void_p)

    cmd = ctypes.create_unicode_buffer('cmd.exe /c exit 0')
    ok = k32.CreateProcessW(None, cmd, None, None, inherit, flags, None, None,
                            ctypes.byref(si.StartupInfo), ctypes.byref(pi))
    err = 0 if ok else k32.GetLastError()
    if ok:
        k32.WaitForSingleObject(pi.hProcess, 10000)
        k32.CloseHandle(pi.hProcess)
        k32.CloseHandle(pi.hThread)
    if with_list and attr_buf is not None:
        try:
            k32.DeleteProcThreadAttributeList(ctypes.cast(attr_buf, ctypes.c_void_p))
        except Exception:                                        # noqa: BLE001
            pass
    return bool(ok), err


def main() -> int:
    print("== M-1 API premise: is 'bInheritHandles=FALSE + HANDLE_LIST' a real config? ==")

    ok_a, err_a = try_spawn(inherit=False, with_list=False)
    print(f"  (a) inherit=False, no list      -> ok={ok_a} err={err_a}")
    check("(a) inherit=False without a list is VALID", ok_a, f"err={err_a}")

    ok_b, err_b = try_spawn(inherit=True, with_list=True)
    print(f"  (b) inherit=True,  with list    -> ok={ok_b} err={err_b}")
    check("(b) inherit=True with HANDLE_LIST is VALID", ok_b, f"err={err_b}")

    ok_c, err_c = try_spawn(inherit=False, with_list=True)
    print(f"  (c) inherit=False, WITH list    -> ok={ok_c} err={err_c}")
    check("(c) inherit=False + HANDLE_LIST FAILS with ERROR_INVALID_PARAMETER",
          (not ok_c) and err_c == ERROR_INVALID_PARAMETER,
          f"ok={ok_c} err={err_c}")

    print()
    if ok_c or err_c != ERROR_INVALID_PARAMETER:
        print("INTERPRETATION: combination (c) did NOT fail the documented way on this")
        print("machine. Re-read the result before writing anything into the draft.")
    else:
        print("INTERPRETATION: my draft's M-1 premise was WRONG AS WRITTEN.")
        print("  'bInheritHandles=FALSE + PROC_THREAD_ATTRIBUTE_HANDLE_LIST' is not a")
        print("  valid configuration on this Windows build: it fails with 87.")
        print("  The two correct options are:")
        print("    (a) inherit=FALSE, no list      -> nothing inherits at all")
        print("    (b) inherit=TRUE  + HANDLE_LIST -> exactly the listed handles inherit")
        print("  This is a DESIGN-ANALYSIS correction, not an isolation result.")

    fails = [n for n, ok_, _ in RESULTS if not ok_]
    print()
    if fails:
        print(f"DISTINCT_RESULTS: FAIL={len(fails)} {fails}")
        return 1
    print("DISTINCT_RESULTS: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
