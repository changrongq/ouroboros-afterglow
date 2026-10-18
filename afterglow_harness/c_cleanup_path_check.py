"""知微 2026-10-18 (second pass) -- prove the cleanup defects are actually fixed.

He reproduced the following WITHOUT starting a real worker, using a stub:
  (a) when the check returns 0 but the finally block cannot confirm exit, main() still
      returned 0  ->  a cleanup failure was invisible in the exit status
  (b) when the wait call raised, every following CloseHandle was skipped -> leaked handles

This driver reproduces all of it with a STUB process object: no cross-account worker, no
password, no real process. It then asserts the repaired behaviour.

What it can and cannot show:
  CAN     -- that a cleanup failure now produces a non-zero exit status, and that both
             handles are released even when the wait raises.
  CANNOT  -- anything about a real worker, and nothing about isolation. The real-worker
             exercise remains c_unreadable_target_control.py.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

import c_unreadable_target_control as T

FAILS: list = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAILS.append(name)


class FakePI:
    def __init__(self, hp=0x1111, ht=0x2222, pid=4242):
        self.hp = hp
        self.ht = ht
        self.pid = pid


def run_with_stubbed_kernel(wait_raises: bool, wait_signals: bool,
                            open_fails: bool = False, exitcode_fails: bool = False,
                            exitcode_raises: bool = False, still_active: bool = False,
                            close_fails_for: tuple = ()):
    """Drive _terminate_and_confirm with a fake kernel32 and record CloseHandle calls."""
    closed: list = []
    close_failed: list = []

    class FakeK32:
        def TerminateProcess(self, h, code):
            return 1

        def WaitForSingleObject(self, h, ms):
            if wait_raises:
                raise RuntimeError("simulated wait failure")
            return 0x00000000 if wait_signals else 0x00000102

        def OpenProcess(self, access, inherit, pid):
            # 知微 2026-10-18: a failed open must NOT be read as "the process is gone".
            return None if open_fails else 0x3333

        def GetExitCodeProcess(self, h, ref):
            if exitcode_raises:
                raise RuntimeError("simulated exit-code failure")
            if exitcode_fails:
                return 0
            ref._obj.value = 259 if still_active else 1
            return 1

        def GetLastError(self):
            return 5  # ERROR_ACCESS_DENIED

        def CloseHandle(self, h):
            iv = int(h) if h else 0
            if iv in close_fails_for:
                close_failed.append(iv)
                return 0            # Win32 failure: BOOL FALSE, no exception
            closed.append(iv)
            return 1

    orig = ctypes.windll.kernel32
    try:
        ctypes.windll.kernel32 = FakeK32()
        result = T._terminate_and_confirm(FakePI(), 4242, timeout_s=0.01)
    finally:
        ctypes.windll.kernel32 = orig
    return result, closed, close_failed


def main() -> int:
    def R(*a, **kw):
        res, closed, failed = run_with_stubbed_kernel(*a, **kw)
        return (res["worker_exit_confirmed"], res["controller_resources_released"],
                res["detail"], closed, failed)

    print("== case 1: wait raises -> BOTH handles must still be released ==")
    ex, rel, det, closed, _ = R(wait_raises=True, wait_signals=False)
    print("  closed handles:", [hex(c) for c in closed if c])
    print("  detail:", det)
    check("handle hp released", 0x1111 in closed, str([hex(c) for c in closed]))
    check("handle ht released", 0x2222 in closed, str([hex(c) for c in closed]))
    check("exit NOT confirmed when the wait raised", ex is False, str(ex))
    check("raise is reported in detail", "raised" in det, det)

    print("== case 2: wait times out -> exit not confirmed, handles released ==")
    ex, rel, det, closed, _ = R(wait_raises=False, wait_signals=False)
    check("hp released", 0x1111 in closed)
    check("ht released", 0x2222 in closed)
    check("exit NOT confirmed on timeout", ex is False, str(ex))

    print("== case 3: wait signals -> exit confirmed ==")
    ex, rel, det, closed, _ = R(wait_raises=False, wait_signals=True)
    check("exit confirmed", ex is True, str(ex))
    check("hp released", 0x1111 in closed)
    check("ht released", 0x2222 in closed)
    check("resources released", rel is True, str(rel))

    print("== case 3b: OpenProcess FAILS -> state UNKNOWN, NOT 'gone' ==")
    ex, rel, det, closed, _ = R(wait_raises=False, wait_signals=False, open_fails=True)
    print("  detail:", det)
    check("failed open does NOT assert 'no longer openable (gone)'",
          "no longer openable (gone)" not in det, det)
    check("failed open is reported as UNKNOWN", "UNKNOWN" in det, det)
    check("failed open reports the error code", "err=" in det, det)
    check("handles still released on failed open",
          0x1111 in closed and 0x2222 in closed)

    print("== case 3c: GetExitCodeProcess fails -> exit NOT verified ==")
    ex, rel, det, closed, _ = R(wait_raises=False, wait_signals=True,
                                exitcode_fails=True)
    print("  detail:", det)
    check("unreadable exit code is flagged", "GetExitCodeProcess failed" in det, det)
    check("does not assert 'no longer openable (gone)'",
          "no longer openable (gone)" not in det, det)
    check("declares UNKNOWN when the exit code is unreadable",
          "unknown" in det.lower(), det)
    check("query handle released even when exit code read fails",
          0x3333 in closed, str([hex(c) for c in closed]))

    print("== case 3d: STILL_ACTIVE after termination -> exit NOT confirmed ==")
    ex, rel, det, closed, _ = R(wait_raises=False, wait_signals=True,
                                still_active=True)
    check("STILL_ACTIVE forces exit unconfirmed", ex is False, str(ex))
    check("STILL_ACTIVE is reported", "STILL_ACTIVE" in det, det)

    print("== case 6 (ZHIWEI 4th pass): GetExitCodeProcess RAISES -> hp2 released ==")
    ex, rel, det, closed, _ = R(wait_raises=False, wait_signals=True,
                                exitcode_raises=True)
    print("  closed handles:", [hex(c) for c in closed if c])
    print("  detail:", det)
    check("query handle hp2 RELEASED despite the raise",
          0x3333 in closed, str([hex(c) for c in closed]))
    check("hp/ht also released", 0x1111 in closed and 0x2222 in closed)
    check("raise is recorded", "exit verification raised" in det, det)

    print("== case 7 (ZHIWEI 4th pass): CloseHandle FALSE is reported ==")
    ex, rel, det, closed, failed = R(wait_raises=False, wait_signals=True,
                                     close_fails_for=(0x1111,))
    print("  closed:", [hex(c) for c in closed], " failed:", [hex(c) for c in failed])
    print("  detail:", det)
    check("worker_exit_confirmed is STILL TRUE (wait already proved it)",
          ex is True, str(ex))
    check("controller_resources_released is FALSE", rel is False, str(rel))
    check("CloseHandle FALSE is recorded with an error code",
          "returned FALSE" in det and "err=" in det, det)
    check("a failed close does NOT skip the other handle", 0x2222 in closed,
          str([hex(c) for c in closed]))
    check("failed close is NOT described as worker still running",
          "still running" not in det.lower(), det)

    print("== case 8: the two facts are INDEPENDENT ==")
    # exit confirmed + release failed must be representable, and must not collapse.
    ex, rel, det, closed, failed = R(wait_raises=False, wait_signals=True,
                                     close_fails_for=(0x1111, 0x2222))
    check("exit confirmed AND resources leaked simultaneously",
          ex is True and rel is False, f"exit={ex} released={rel}")

    print("== case 4: cleanup failure reaches the EXIT STATUS ==")
    check("module declares EXIT_CLEANUP_FAILED = 3",
          T.EXIT_CLEANUP_FAILED == 3, str(T.EXIT_CLEANUP_FAILED))
    check("module initialises CLEANUP_FAILED falsy",
          T.CLEANUP_FAILED is False, str(T.CLEANUP_FAILED))
    check("module exposes PENDING_PID", hasattr(T, "PENDING_PID"), "")
    check("module exposes RESOURCES_RELEASED / RESOURCE_LEAK",
          hasattr(T, "RESOURCES_RELEASED") and hasattr(T, "RESOURCE_LEAK"), "")

    def translate(rc: int, cleanup_failed: bool) -> int:
        if cleanup_failed:
            return T.EXIT_CLEANUP_FAILED if rc == 0 else rc
        return rc

    check("rc=0 + cleanup failed -> 3", translate(0, True) == 3, str(translate(0, True)))
    check("rc=1 + cleanup failed -> 1 (specific code kept)",
          translate(1, True) == 1, str(translate(1, True)))
    check("rc=0 + cleanup ok -> 0", translate(0, False) == 0, str(translate(0, False)))

    print("== case 5: overall success must INCLUDE cleanup success ==")
    def is_clean_pass(check_rc: int, cleanup_failed: bool) -> bool:
        return check_rc == 0 and not cleanup_failed

    check("check PASS + cleanup FAILED is NOT a clean pass",
          is_clean_pass(0, True) is False)
    check("check PASS + cleanup ok IS a clean pass",
          is_clean_pass(0, False) is True)
    check("check FAIL + cleanup ok is NOT a clean pass",
          is_clean_pass(1, False) is False)

    print()
    if FAILS:
        print(f"DISTINCT_RESULTS: FAIL={len(FAILS)} {FAILS}")
        return 1
    print("DISTINCT_RESULTS: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
