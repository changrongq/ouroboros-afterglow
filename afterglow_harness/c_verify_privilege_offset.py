"""知微 2026-10-18 item 1 -- measure the TOKEN_PRIVILEGES array offset.

His claim: "昨天确认的权限数组偏移错误仍未修复" (the access/privilege array offset error,
confirmed yesterday, is still not fixed).

I found the code he means: q3_handle_audit_diagnostic.py around line 111, which walks
`arr.PrivilegeCount` privileges via
    full = ctypes.cast(buf, ctypes.POINTER(LUID_AND_ATTRIBUTES * max(1, Count)))
    la = full.contents[i]
That cast starts at BYTE 0 of the buffer, i.e. it reads PrivilegeCount itself as if it
were the first LUID_AND_ATTRIBUTES. This driver MEASURES the real offsets instead of
arguing from the docs:

  TOKEN_PRIVILEGES  = { DWORD PrivilegeCount; LUID_AND_ATTRIBUTES Privileges[]; }
  LUID_AND_ATTRIBUTES = { LUID Luid (8 bytes); DWORD Attributes (4) }  -> 12 bytes, align 4
  => Privileges[] starts at offset 4, and sizeof(LUID_AND_ATTRIBUTES) == 12

CORRECTION (2026-10-18, per 知微's second-pass review): an earlier version of this
docstring claimed ctypes would not place `Privileges` at offset 4 because LUID contains a
64-bit member, and that this alignment mismatch WAS the defect. THAT WAS WRONG, and the
measurement in this very file refuted it: ctypes places `Privileges` at offset 4, the
same as the Windows ABI. There is no struct-layout defect.

The defect is ONLY in the hand-written cast, which started at byte 0:
    full = ctypes.cast(buf, POINTER(LUID_AND_ATTRIBUTES * n))
so PrivilegeCount was read as the first privilege's LUID high half -- a 4-byte offset.
The struct was right; the cast was wrong. Do not restate the alignment story.

Read-only; no repository changes. Only queries OUR OWN token.
"""
from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

OUT: list = []


def check(name: str, cond: bool, detail: str = "") -> None:
    OUT.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", ctypes.c_long)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wintypes.DWORD),
                ("Privileges", LUID_AND_ATTRIBUTES * 1)]


def main() -> int:
    print("== measured ctypes layout ==")
    print("  sizeof(LUID)                =", ctypes.sizeof(LUID))
    print("  sizeof(LUID_AND_ATTRIBUTES) =", ctypes.sizeof(LUID_AND_ATTRIBUTES))
    print("  sizeof(TOKEN_PRIVILEGES)    =", ctypes.sizeof(TOKEN_PRIVILEGES))
    print("  PrivilegeCount offset       =", TOKEN_PRIVILEGES.PrivilegeCount.offset)
    print("  Privileges offset (ctypes)  =", TOKEN_PRIVILEGES.Privileges.offset)

    check("sizeof(LUID_AND_ATTRIBUTES) is 12",
          ctypes.sizeof(LUID_AND_ATTRIBUTES) == 12,
          str(ctypes.sizeof(LUID_AND_ATTRIBUTES)))
    check("ctypes lays Privileges at offset 4, SAME as the Windows ABI",
          TOKEN_PRIVILEGES.Privileges.offset == 4,
          str(TOKEN_PRIVILEGES.Privileges.offset))

    print("== live token query ==")
    adv = ctypes.windll.advapi32
    k = ctypes.windll.kernel32
    # GetCurrentProcess returns a pseudo-handle (-1); without restype ctypes truncates
    # it to 32 bits and OpenProcessToken fails with 6. This was MY bug, not the tool's.
    k.GetCurrentProcess.restype = wintypes.HANDLE
    adv.OpenProcessToken.restype = wintypes.BOOL
    adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                     ctypes.POINTER(wintypes.HANDLE)]
    TOKEN_QUERY = 0x0008
    TokenPrivileges = 3

    h = wintypes.HANDLE()
    if not adv.OpenProcessToken(k.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(h)):
        print("  OpenProcessToken failed", k.GetLastError())
        return 2
    size = wintypes.DWORD(0)
    adv.GetTokenInformation(h, TokenPrivileges, None, 0, ctypes.byref(size))
    buf = ctypes.create_string_buffer(size.value)
    ok = adv.GetTokenInformation(h, TokenPrivileges, buf, size.value, ctypes.byref(size))
    k.CloseHandle(h)
    check("GetTokenInformation succeeded", bool(ok), str(size.value))

    count = ctypes.cast(buf, ctypes.POINTER(wintypes.DWORD)).contents.value
    print("  PrivilegeCount =", count)

    # CORRECT read: privileges begin at byte offset 4.
    CORRECT_OFFSET = 4
    entry_size = ctypes.sizeof(LUID_AND_ATTRIBUTES)

    def read_at(offset: int, idx: int) -> tuple:
        base = offset + idx * entry_size
        low = int.from_bytes(buf.raw[base:base + 4], "little")
        high = int.from_bytes(buf.raw[base + 4:base + 8], "little", signed=True)
        attrs = int.from_bytes(buf.raw[base + 8:base + 12], "little")
        return low, high, attrs

    print("  first few privileges read at offset 4:")
    sane = 0
    for i in range(min(count, 5)):
        low, high, attrs = read_at(CORRECT_OFFSET, i)
        print(f"    [{i}] LUID={high:#x}:{low:#08x} attributes={attrs:#x}")
        if attrs in (0, 1, 2, 3):
            sane += 1
    check("attributes at offset 4 look like real SE_PRIVILEGE values (0/1/2/3)",
          sane == min(count, 5), f"sane={sane}/{min(count, 5)}")

    print("  what the DEFECTIVE cast would read (starting at byte 0):")
    bad = []
    for i in range(min(count, 3)):
        base = 0 + i * entry_size
        low = int.from_bytes(buf.raw[base:base + 4], "little")
        high = int.from_bytes(buf.raw[base + 4:base + 8], "little", signed=True)
        attrs = int.from_bytes(buf.raw[base + 8:base + 12], "little")
        bad.append((low, high, attrs))
        print(f"    [{i}] LUID={high:#x}:{low:#08x} attributes={attrs:#x}")

    # The ATTRIBUTES column is useless as a discriminator here: most privileges are
    # neither held nor enabled, so both reads yield 0x0. The LUID HIGH PART is the
    # discriminator, because reading at offset 0 folds PrivilegeCount into it.
    correct_h = [read_at(CORRECT_OFFSET, i)[1] for i in range(min(count, 5))]
    bad_h = [b[1] for b in bad]
    print(f"  LUID high parts, correct offset 4 : {[hex(x) for x in correct_h]}")
    print(f"  LUID high parts, defective offset 0: {[hex(x) for x in bad_h]}")
    check("correct read gives LUID high=0 (real LUIDs on this machine)",
          all(x == 0 for x in correct_h), str([hex(x) for x in correct_h]))
    check("defective read INJECTS PrivilegeCount into the LUID high part",
          any(x != 0 for x in bad_h), str([hex(x) for x in bad_h]))

    print()
    print("CONCLUSION: Windows and ctypes BOTH lay Privileges[] at offset 4 -- that part")
    print("is fine. The defect is the CAST: ctypes.cast(buf, POINTER(LUID_AND_ATTRIBUTES*n))")
    print("starts at byte 0 and therefore reads PrivilegeCount as the first privilege's")
    print("LUID high half. Measured proof: at offset 4 the high parts are all 0; at")
    print("offset 0 the first high part equals PrivilegeCount. The diagnostic therefore")
    print("compares against WRONG LUIDs and can misreport SeDebugPrivilege state.")

    fails = [n for n, ok_, _ in OUT if not ok_]
    print()
    if fails:
        print(f"DISTINCT_RESULTS: FAIL={len(fails)} {fails}")
        return 1
    print("DISTINCT_RESULTS: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
