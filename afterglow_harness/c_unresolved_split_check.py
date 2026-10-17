"""睫 (2026-10-17) requested the two unresolved causes be counted SEPARATELY:

    unresolved_operational   -- we FAILED TO OPERATE (OpenProcess denied by ordinary
                                permissions, DuplicateHandle failed, enum error).
                                Environmental; fixable by granting privilege.
    unresolved_no_identity   -- we OPERATED but the object carries NO readable file
                                identity (device objects: \\Device\\ConDrv, KsecDD,
                                CNG). Ontological; no privilege makes it readable.

His point: if operational == 0 while no_identity > 0, "grant more permissions and
retry" is the WRONG remedy -- the conclusion does not hold on that object.

This driver does NOT touch a real worker. It drives `audit_business_worker_handles`
with the OS primitives FORCED to fail in each of the two ways, and asserts the split
lands in the correct bucket. Forced-failure injection only; nothing here is evidence
about a live process.

Expected:
    FORCED_OPENPROCESS_DENIED  -> unresolved_operational > 0, no_identity == 0
    FORCED_NO_IDENTITY         -> unresolved_operational == 0, no_identity > 0
                                  and detail carries CAUSE_IS_ONTOLOGICAL
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import q3_business_handle_audit_v2 as V

FAILURES: list[str] = []


def _check(name: str, cond: bool, detail: str = "") -> None:
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else ""))
    if not cond:
        FAILURES.append(name)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="c_split_"))
    target = tmp / "protected.bin"
    target.write_bytes(b"c-unresolved-split-check")

    # Take a real, live pid that we can enumerate but will refuse/park on. The
    # current process is enough: we force the failure, we never rely on permission.
    pid = __import__("os").getpid()

    # ---- Case 1: operation refused (ordinary-permission style) -------------------
    orig_open = V._k32

    class _DenyOpenProcess:
        """Wrapper: OpenProcess always fails, everything else delegates."""

        def __init__(self, real):
            self._real = real

        def OpenProcess(self, *a, **kw):
            return 0

        def GetLastError(self):
            return 5  # ERROR_ACCESS_DENIED

        def __getattr__(self, item):
            return getattr(self._real, item)

    real_k32 = V._k32

    def _k32_denied():
        return _DenyOpenProcess(real_k32())

    V._k32 = _k32_denied
    try:
        r1 = V.audit_business_worker_handles(pid, str(target))
    finally:
        V._k32 = real_k32
    c1 = r1.counts
    print("CASE1 forced OpenProcess denied ->", json.dumps(
        {k: c1[k] for k in ("unresolved", "unresolved_operational",
                            "unresolved_no_identity", "openprocess_fail")}))
    _check("C1 operational > 0", c1["unresolved_operational"] > 0,
           f"op={c1['unresolved_operational']}")
    _check("C1 no_identity == 0", c1["unresolved_no_identity"] == 0,
           f"no_id={c1['unresolved_no_identity']}")
    _check("C1 sum == unresolved",
           c1["unresolved_operational"] + c1["unresolved_no_identity"] == c1["unresolved"])

    # ---- Case 2: operated, but no identity readable ------------------------------
    orig_ident = V._identity_from_handle

    derr_real = real_k32()
    real_dup = derr_real.DuplicateHandle

    def _fake_identity(dup, k):                   # noqa: ANN001
        return None, "", {"forced_no_identity": 1}

    V._identity_from_handle = _fake_identity
    try:
        r2 = V.audit_business_worker_handles(pid, str(target))
    finally:
        V._identity_from_handle = orig_ident
    c2 = r2.counts
    print("CASE2 forced identity unreadable ->", json.dumps(
        {k: c2[k] for k in ("file_type_total", "unresolved",
                            "unresolved_operational", "unresolved_no_identity")}))
    if c2["file_type_total"] == 0:
        print("  SKIP  C2 (this pid holds 0 File-type handles; cannot drive the branch)")
    else:
        _check("C2 no_identity > 0", c2["unresolved_no_identity"] > 0,
               f"no_id={c2['unresolved_no_identity']}")
        _check("C2 operational == 0", c2["unresolved_operational"] == 0,
               f"op={c2['unresolved_operational']}")
        _check("C2 sum == unresolved",
               c2["unresolved_operational"] + c2["unresolved_no_identity"] == c2["unresolved"])
        _check("C2 detail flags ontological cause",
               "CAUSE_IS_ONTOLOGICAL" in (r2.detail or ""), (r2.detail or "")[:90])
    _ = real_dup

    print()
    if FAILURES:
        print(f"DISTINCT_RESULTS: FAIL={len(FAILURES)} {FAILURES}")
        return 1
    print("DISTINCT_RESULTS: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
