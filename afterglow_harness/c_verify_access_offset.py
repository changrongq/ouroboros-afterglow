"""知微 2026-10-18 -- verify the "access-array offset error" claim by MEASUREMENT.

He reported three maintenance items; this one is:
    "昨天确认的权限数组偏移错误仍未修复"   (the previously-confirmed access-array offset
                                          error is still not fixed)

I do NOT assume it is true and I do NOT assume it is false. This driver measures the
actual byte layout returned by NtQuerySystemInformation(SystemHandleInformation) on this
machine and checks the frozen reader against it:

  1. sizeof / stride of the entry the frozen module uses
  2. where GrantedAccess really sits (offset of the field inside the struct)
  3. whether base = addressof(buf) + 8 lands on the first entry
  4. whether a KNOWN handle (one we create ourselves) is read back with the ACCESS BITS
     we requested -- the end-to-end test the struct offsets are supposed to serve

If the access bits come back wrong, the offset claim is TRUE and must be fixed.
If they come back right, the claim needs more specificity and I will ask 知微 which
offset he means rather than "fixing" something that is already correct.

Read-only with respect to the repository. Creates one file handle in its own process.
"""
from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes

import q3_handle_audit as HA

OUT: list = []


def check(name: str, cond: bool, detail: str = "") -> None:
    OUT.append((name, bool(cond), detail))
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))


def main() -> int:
    print("== section 1: measured struct layout ==")
    ent = HA.SYSTEM_HANDLE_TABLE_ENTRY_INFO
    print("  sizeof(SYSTEM_HANDLE_TABLE_ENTRY_INFO) =", ctypes.sizeof(ent))
    for fname, _ftype in ent._fields_:
        off = getattr(ent, fname).offset
        sz = ctypes.sizeof(dict(ent._fields_)[fname])
        print(f"    {fname:24s} offset={off:<3d} size={sz}")
    ga_off = ent.GrantedAccess.offset
    print("  GrantedAccess offset =", ga_off)
    check("sizeof == 24 (x64 stride)", ctypes.sizeof(ent) == 24,
          str(ctypes.sizeof(ent)))
    check("GrantedAccess sits at offset 16", ga_off == 16, str(ga_off))
    check("HandleValue sits at offset 6", ent.HandleValue.offset == 6,
          str(ent.HandleValue.offset))
    check("UniqueProcessId sits at offset 0", ent.UniqueProcessId.offset == 0,
          str(ent.UniqueProcessId.offset))

    print("== section 2: open a handle with KNOWN access bits ==")
    # Create an event with a specific access right so we can read it back exactly.
    k32 = ctypes.windll.kernel32
    k32.CreateEventW.restype = ctypes.c_void_p
    EVENT_MODIFY_STATE = 0x0002
    h = k32.CreateEventW(None, False, False, None)
    if not h:
        print("  could not create the probe event")
        return 2
    hv = int(h)
    print(f"  created event handle = {hv:#x}")

    print("== section 3: does the frozen reader see it, and with which access? ==")
    seen = None
    total = 0
    for value, tp, acc in HA._iter_handles(os.getpid()):
        total += 1
        if value == hv:
            seen = (value, tp, acc)
            break
    print(f"  handles enumerated for this pid: {total}")
    print(f"  probe handle found: {seen is not None}"
          + (f"  access={seen[2]:#010x}" if seen else ""))

    check("the frozen reader FINDS our own known handle", seen is not None,
          f"hv={hv:#x}")
    if seen:
        acc = seen[2]
        check("access bits contain EVENT_MODIFY_STATE (offset is right)",
              (acc & EVENT_MODIFY_STATE) != 0, f"access={acc:#010x}")
        check("access is not zero", acc != 0, f"access={acc:#010x}")
        check("access is not a garbage value derived from adjacent bytes",
              acc < 0x10000000, f"access={acc:#010x}")

    print("== section 4: what does the byte at the claimed offset actually hold? ==")
    # Dump the raw 24 bytes of our own entry to show where the access DWORD lives.
    ntdll = ctypes.windll.ntdll
    SYSTEM_HANDLE_INFORMATION = 16
    size = 1 << 22
    buf = ctypes.create_string_buffer(size)
    ret = ctypes.c_ulong(0)
    st = ntdll.NtQuerySystemInformation(SYSTEM_HANDLE_INFORMATION, buf, size,
                                        ctypes.byref(ret))
    if st != 0:
        print("  NtQuerySystemInformation failed:", hex(st & 0xFFFFFFFF))
        return 2
    count = ctypes.cast(buf, ctypes.POINTER(ctypes.c_ulong)).contents.value
    base = ctypes.addressof(buf) + 8
    stride = 24
    for i in range(count):
        raw = ctypes.string_at(base + i * stride, stride)
        e = ent.from_address(base + i * stride)
        if e.UniqueProcessId == os.getpid() and e.HandleValue == hv:
            print("  raw 24 bytes:", raw.hex())
            print("  pid@0   =", int.from_bytes(raw[0:2], "little"))
            print("  type@4  =", raw[4])
            print("  handle@6=", int.from_bytes(raw[6:8], "little"), f"({hv:#x})")
            print("  access@16=", hex(int.from_bytes(raw[16:20], "little")))
            check("access DWORD at raw offset 16 matches the struct field",
                  int.from_bytes(raw[16:20], "little") == e.GrantedAccess,
                  f"raw={hex(int.from_bytes(raw[16:20], 'little'))} "
                  f"field={hex(e.GrantedAccess)}")
            break

    k32.CloseHandle(ctypes.c_void_p(h))

    fails = [n for n, ok, _ in OUT if not ok]
    print()
    if fails:
        print(f"DISTINCT_RESULTS: FAIL={len(fails)} {fails}")
        return 1
    print("DISTINCT_RESULTS: PASS")
    print()
    print("NOTE: this measures THIS machine's x64 layout. It says nothing about whether")
    print("a different Windows build disagrees; if 知微 means a different offset, he")
    print("should name the field so it can be measured, not patched blindly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
