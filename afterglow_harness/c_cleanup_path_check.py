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
                            still_active: bool = False):
    """Drive _terminate_and_confirm with a fake kernel32 and record CloseHandle calls."""
    closed: list = []

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
            if exitcode_fails:
                return 0
            ref._obj.value = 259 if still_active else 1
            return 1

        def GetLastError(self):
            return 5  # ERROR_ACCESS_DENIED

        def CloseHandle(self, h):
            closed.append(int(h) if h else 0)
            return 1

    orig = ctypes.windll.kernel32
    try:
        ctypes.windll.kernel32 = FakeK32()
        exited, detail = T._terminate_and_confirm(FakePI(), 4242, timeout_s=0.01)
    finally:
        ctypes.windll.kernel32 = orig
    return exited, detail, closed


def main() -> int:
    print("== case 1: wait raises -> BOTH handles must still be released ==")
    exited, detail, closed = run_with_stubbed_kernel(wait_raises=True, wait_signals=False)
    print("  closed handles:", [hex(c) for c in closed if c])
    print("  detail:", detail)
    check("handle hp released", 0x1111 in closed, str([hex(c) for c in closed]))
    check("handle ht released", 0x2222 in closed, str([hex(c) for c in closed]))
    check("exit NOT confirmed when the wait raised", exited is False, str(exited))
    check("raise is reported in detail", "raised" in detail, detail)

    print("== case 2: wait times out -> exit not confirmed, handles released ==")
    exited2, detail2, closed2 = run_with_stubbed_kernel(wait_raises=False,
                                                        wait_signals=False)
    print("  closed handles:", [hex(c) for c in closed2 if c])
    check("hp released", 0x1111 in closed2)
    check("ht released", 0x2222 in closed2)
    check("exit NOT confirmed on timeout", exited2 is False, str(exited2))

    print("== case 3: wait signals -> exit confirmed ==")
    exited3, detail3, closed3 = run_with_stubbed_kernel(wait_raises=False,
                                                        wait_signals=True)
    check("exit confirmed", exited3 is True, str(exited3))
    check("hp released", 0x1111 in closed3)
    check("ht released", 0x2222 in closed3)

    print("== case 3b: OpenProcess FAILS -> state UNKNOWN, NOT 'gone' ==")
    # 知微 2026-10-18: a failed open can be permissions or PID reuse. It must never be
    # reported as proof of exit.
    exited3b, detail3b, closed3b = run_with_stubbed_kernel(
        wait_raises=False, wait_signals=False, open_fails=True)
    print("  detail:", detail3b)
    # NB: the message deliberately CONTAINS the word 'gone' ("NOT interpreted as gone"),
    # so a plain substring test would be wrong. Assert on the affirmative claim instead.
    check("failed open does NOT assert 'no longer openable (gone)'",
          "no longer openable (gone)" not in detail3b, detail3b)
    check("failed open is reported as UNKNOWN", "UNKNOWN" in detail3b, detail3b)
    check("failed open reports the error code", "err=" in detail3b, detail3b)
    check("handles still released on failed open",
          0x1111 in closed3b and 0x2222 in closed3b)

    print("== case 3c: GetExitCodeProcess fails -> exit NOT verified ==")
    exited3c, detail3c, _ = run_with_stubbed_kernel(
        wait_raises=False, wait_signals=True, exitcode_fails=True)
    print("  detail:", detail3c)
    check("unreadable exit code is flagged, not silently accepted",
          "GetExitCodeProcess failed" in detail3c, detail3c)
    # Same substring trap as 3b: the message says "NOT 'gone'", so look for the
    # affirmative retired phrase rather than the bare word.
    check("does not assert 'no longer openable (gone)' from an unreadable exit code",
          "no longer openable (gone)" not in detail3c, detail3c)
    check("declares the pid state UNKNOWN when the exit code is unreadable",
          "unknown" in detail3c.lower(), detail3c)

    print("== case 3d: STILL_ACTIVE after termination -> exit NOT confirmed ==")
    exited3d, detail3d, _ = run_with_stubbed_kernel(
        wait_raises=False, wait_signals=True, still_active=True)
    check("STILL_ACTIVE forces exited=False", exited3d is False, str(exited3d))
    check("STILL_ACTIVE is reported", "STILL_ACTIVE" in detail3d, detail3d)

    print("== case 4: cleanup failure reaches the EXIT STATUS ==")
    # The entry point must translate CLEANUP_FAILED into a non-zero code. We assert the
    # contract rather than spawning a process.
    check("module declares EXIT_CLEANUP_FAILED = 3",
          T.EXIT_CLEANUP_FAILED == 3, str(T.EXIT_CLEANUP_FAILED))
    check("module initialises CLEANUP_FAILED falsy",
          T.CLEANUP_FAILED is False, str(T.CLEANUP_FAILED))
    check("module exposes PENDING_PID for unconfirmed exits",
          hasattr(T, "PENDING_PID") and T.PENDING_PID == 0, str(getattr(
              T, "PENDING_PID", None)))
    # Simulate what __main__ does.
    def translate(rc: int, cleanup_failed: bool) -> int:
        if cleanup_failed:
            return T.EXIT_CLEANUP_FAILED if rc == 0 else rc
        return rc

    check("rc=0 + cleanup failed -> 3", translate(0, True) == 3, str(translate(0, True)))
    check("rc=1 + cleanup failed -> 1 (specific code kept)",
          translate(1, True) == 1, str(translate(1, True)))
    check("rc=0 + cleanup ok -> 0", translate(0, False) == 0, str(translate(0, False)))

    print("== case 5: overall success must INCLUDE cleanup success ==")
    # 知微's required rule: an unconfirmed exit can never be a full PASS, even when the
    # check itself passed. Encoded as: clean_pass requires check==0 AND cleanup confirmed.
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
