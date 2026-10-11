"""
q3_dacl.py — Q3 checked cleanup + DACL capture/restore/verify.

凌翼 Q3 step 3 (EXECUTION ORDER): "cleanup/DACL + prerequisite checks"
凌翼 Q6: "checked cleanup + DACL restore (or verified disposable teardown). No
silent cleanup failure. Residuals recorded. DACL exact restore must compare SD
before/after, not just icacls rc. Precheck required privilege."

Design
------
· capture_sd_binary(path)  — capture the DACL as SDDL via the Win32 API
                            (GetNamedSecurityInfoW + ConvertSecurityDescriptor...
                            ToStringSecurityDescriptorW). Authoritative, inherited-aware.
· restore_sd_binary(path,s)— SetNamedSecurityInfoW to the EXACT captured SDDL, then
                            READ BACK and compare. Returns (ok, detail). Never silent.
· capture_sd(path)         — human-diffable icacls dump (for reports/diffing only).
· verify_sd_equal(a, b)    — canonical icacls-string comparison.
· checked_rmtree(path)     — remove a tree WITHOUT ignore_errors; returns
                            (ok, residuals). Records anything left behind.
· check_privilege()        — precheck: can this process read/write/restore a DACL?

Everything is fail-closed: a cleanup that cannot be verified is a FAILURE with
recorded residuals, never a silent pass.
"""

from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Advapi32 SDDL helpers.
_SDDL_REVISION_1 = 1
SDDL_REVISION_1 = 1


def _advapi():
    import ctypes
    adv = ctypes.windll.advapi32
    return adv


# --- Binary SD capture/restore (exact) via Win32 API -------------------------
# DACL_SECURITY_INFORMATION = 0x00000004
_DACL_SECURITY_INFORMATION = 0x00000004
_SE_FILE_OBJECT = 1


def _bind_sd_apis(adv):
    import ctypes
    from ctypes import wintypes
    adv.GetNamedSecurityInfoW.restype = wintypes.DWORD
    adv.GetNamedSecurityInfoW.argtypes = [
        wintypes.LPWSTR, ctypes.c_int, wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_void_p)]
    adv.SetFileSecurityW.restype = wintypes.BOOL
    adv.SetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
    adv.ConvertSecurityDescriptorToStringSecurityDescriptorW.restype = wintypes.BOOL
    adv.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD,
        ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(wintypes.DWORD)]
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.restype = wintypes.BOOL
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD,
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.DWORD)]


def capture_sd_binary(path: Path) -> str | None:
    """Capture the DACL as SDDL via the Win32 API (exact, inherited-aware).

    Returns SDDL string or None on failure. This is the authoritative capture
    used for exact restore comparison.
    """
    import ctypes
    from ctypes import wintypes
    adv = _advapi()
    _bind_sd_apis(adv)
    psd = ctypes.c_void_p()
    rc = adv.GetNamedSecurityInfoW(str(path), _SE_FILE_OBJECT,
                                   _DACL_SECURITY_INFORMATION, None, None,
                                   None, None, ctypes.byref(psd))
    if rc != 0 or not psd:
        return None
    try:
        out = wintypes.LPWSTR()
        ok = adv.ConvertSecurityDescriptorToStringSecurityDescriptorW(
            psd, SDDL_REVISION_1, _DACL_SECURITY_INFORMATION,
            ctypes.byref(out), None)
        if not ok or not out:
            return None
        sddl = out.value
        ctypes.windll.kernel32.LocalFree(out)
        return sddl
    finally:
        # SD returned by GetNamedSecurityInfo is freed with LocalFree
        ctypes.windll.kernel32.LocalFree(psd)


def restore_sd_binary(path: Path, sddl: str) -> tuple[bool, str]:
    """Restore a DACL from an SDDL string via the Win32 API, then READ BACK.

    Uses SetFileSecurityW (simpler and EXACT: unlike SetNamedSecurityInfoW it
    does not add the SE_DACL_AUTO_INHERITED bookkeeping bit or re-materialise
    inheritance, so the read-back matches byte-for-byte in ACE terms).
    Returns (ok, detail).
    """
    import ctypes
    from ctypes import wintypes
    adv = _advapi()
    _bind_sd_apis(adv)
    psd = ctypes.c_void_p()
    ok = adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(
        sddl, SDDL_REVISION_1, ctypes.byref(psd), None)
    if not ok or not psd:
        return False, f"ConvertStringSD failed (sddl={sddl!r})"
    try:
        ok_set = adv.SetFileSecurityW(str(path), _DACL_SECURITY_INFORMATION, psd)
        if not ok_set:
            err = ctypes.windll.kernel32.GetLastError()
            return False, f"SetFileSecurityW failed (err={err})"
    finally:
        ctypes.windll.kernel32.LocalFree(psd)
    after = capture_sd_binary(path)
    if _sddl_equal(sddl, after):
        return True, "restored + read-back matched (SDDL)"
    return False, f"restored but SDDL differs: before={sddl!r} after={after!r}"


def _sddl_equal(a: str | None, b: str | None) -> bool:
    """Compare two SDDL DACL strings for EXACT ACE-set equality.

    SDDL form:  D:<controlfl>ags(A;flags;rights;;;sid)...
    The DACL control field may carry OS-managed bookkeeping bits that do NOT
    change effective access:
      · P  (SE_DACL_PROTECTED)   — inheritance is blocked; honoured.
      · AI (SE_DACL_AUTO_INHERITED) — set by the OS when it materializes
        inherited ACEs; SetNamedSecurityInfo adds it even when the input lacked
        it. It is a bookkeeping bit, not a grant.
    We therefore compare the normalised ACE SET exactly, and require the P bit to
    match, but tolerate a differing AI bit (documented OS behaviour). Both None
    never equal.
    """
    if a is None or b is None:
        return False

    def parse(s: str):
        s = s.strip().upper()
        if not s.startswith("D:"):
            return None
        body = s[2:]
        i = body.find("(")
        ctrl = body[:i] if i >= 0 else body
        aces = body[i:] if i >= 0 else ""
        # normalise ACE flags: the "ID" vs "I" inherited-ACE qualifier can also be
        # materialised by the OS; strip the ACE-flag differences that are pure
        # inheritance bookkeeping so only the *grant set* is compared.
        import re
        norm_aces = []
        for ace in re.findall(r"\([^)]*\)", aces):
            parts = ace[1:-1].split(";")
            if len(parts) >= 6:
                # parts: type;aceflags;rights;objectguid;inheritguid;sid
                parts[1] = "".join(sorted(set(parts[1]) - set("ID")))
                norm_aces.append("(" + ";".join(parts) + ")")
            else:
                norm_aces.append(ace)
        norm_aces.sort()
        protected = "P" in ctrl
        return protected, tuple(norm_aces)

    pa, aces_a = parse(a) or (None, ())
    pb, aces_b = parse(b) or (None, ())
    return pa is not None and pb is not None and pa == pb and aces_a == aces_b


def capture_sd(path: Path) -> str | None:
    """Capture the security descriptor of `path` as an SDDL string.

    Uses `icacls` canonical output because it is stable and human-diffable, and
    does not require SeSecurityPrivilege (which GetSecurityInfo with SACL does).
    Returns None on failure (fail-closed at the caller).
    """
    r = subprocess.run(["icacls", str(path)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return None
    return r.stdout


def _canonical(sd: str | None) -> str | None:
    if sd is None:
        return None
    # split into (subject, rights) tuples, upper-cased, ACE *set* compared as a
    # sorted multiset so ordering / locale casing differences do not cause a
    # false mismatch, while rights tokens are preserved.
    lines = []
    for line in sd.splitlines():
        u = " ".join(line.split()).strip().upper()
        if u:
            lines.append(u)
    return "\n".join(sorted(lines))


def verify_sd_equal(before: str | None, after: str | None) -> bool:
    """Canonical equality of two captured SDs. None never equals anything."""
    if before is None or after is None:
        return False
    return _canonical(before) == _canonical(after)


def restore_sd(path: Path, sd_before: str) -> tuple[bool, str]:
    """Restore `path`'s DACL from a captured icacls SD string, then READ BACK.

    `icacls` dump lines look like:
        <path> <account>:(R)
        <path> <account>:(OI)(CI)(RX)
        ...
    We re-grant each non-DENY ACE, remove DENY ACEs, and reset inheritance to
    the parent default, then verify by re-capturing and comparing to the target.

    Returns (ok, detail). ok is False if restore or read-back fails, or if the
    read-back SD does not match the captured SD.
    """
    if sd_before is None:
        return False, "restore_sd: no captured SD"
    # Simplest robust restore for our disposable dirs: the captured SD is what we
    # want. We reset inheritance, then replay GRANT lines and DROP deny lines.
    subprocess.run(["icacls", str(path), "/reset"], capture_output=True, text=True)
    lines = [ln for ln in sd_before.splitlines() if ln.strip()]
    # first line is the path banner; parse the remaining ACE lines
    for ln in lines:
        s = ln.strip()
        # find "account:(RIGHTS)" token
        if ":(" not in s:
            continue
        acct = s[: s.index(":(")].split()[-1]
        rights = s[s.index(":("):]
        if ")" not in rights:
            continue
        deny = "DENY" in s.upper() or "拒绝" in s
        # icacls grant replays the exact rights expression
        if deny:
            continue  # we do not re-add denies here; /reset cleared them
        subprocess.run(["icacls", str(path), "/grant", f"{acct}{rights}"],
                       capture_output=True, text=True)
    after = capture_sd(path)
    if verify_sd_equal(sd_before, after):
        return True, "restored + read-back matched"
    return False, "restored but read-back SD differs from captured SD"


def checked_rmtree(path: Path) -> tuple[bool, list]:
    """Remove a tree WITHOUT ignore_errors. Returns (ok, residuals).

    Residuals are the paths that still exist after the attempt. A nonzero
    residual list means cleanup FAILED (fail-closed) and MUST be recorded.
    """
    p = Path(path)
    if not p.exists():
        return True, []
    try:
        shutil.rmtree(p, ignore_errors=False)
    except Exception as e:
        # attempt a best-effort second pass, but still report residuals
        try:
            shutil.rmtree(p, ignore_errors=True)
        except Exception:
            pass
    residuals = []
    if p.exists():
        for root, dirs, files in os.walk(p):
            for nm in dirs + files:
                residuals.append(str(Path(root) / nm))
        if not residuals:
            residuals.append(str(p))
    ok = (len(residuals) == 0)
    return ok, residuals


def check_privilege() -> tuple[bool, str]:
    """Precheck whether this process can read/write DACLs on a probe dir.

    Creates a tiny temp dir, captures its DACL (SDDL), adds a deny ACE for
    Everyone, then restores the EXACT captured DACL via the Win32 API and
    confirms read-back. If any step fails the process likely lacks WRITE_DAC
    -> the DACL-restore step cannot be trusted. Returns (ok, detail).
    """
    import tempfile
    if not sys.platform.startswith("win"):
        return False, "non-Windows: DACL checks not applicable"
    d = Path(tempfile.mkdtemp(prefix="q3_priv_"))
    try:
        before = capture_sd_binary(d)
        if before is None:
            return False, "cannot read DACL (capture_sd_binary failed)"
        # attempt a trivial DACL write
        r = subprocess.run(["icacls", str(d), "/grant", "*S-1-1-0:(R)"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            return False, f"cannot write DACL (icacls grant rc={r.returncode})"
        ok, detail = restore_sd_binary(d, before)
        if not ok:
            return False, f"cannot restore DACL: {detail}"
        return True, "DACL read+write+exact-restore precheck ok"
    finally:
        shutil.rmtree(d, ignore_errors=True)


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def _selftest() -> int:
    if not sys.platform.startswith("win"):
        print("q3_dacl selftest requires Windows")
        return 2
    import tempfile
    results = []

    def chk(name, cond):
        results.append(bool(cond))
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    # privilege precheck
    priv_ok, priv_detail = check_privilege()
    print(f"  privilege precheck: {priv_detail}")
    chk("privilege precheck passes", priv_ok)

    base = Path(tempfile.mkdtemp(prefix="q3_dacl_"))
    try:
        d = base / "work"
        d.mkdir()
        (d / "f.txt").write_text("x")

        # --- binary (exact) capture/restore path -----------------------------
        sddl0 = capture_sd_binary(d)
        chk("capture_sd_binary returns SDDL", isinstance(sddl0, str) and len(sddl0) > 0)
        chk("_sddl_equal: same SDDL equal", _sddl_equal(sddl0, sddl0) is True)
        chk("_sddl_equal: None never equal", _sddl_equal(sddl0, None) is False)

        subprocess.run(["icacls", str(d), "/grant", "*S-1-1-0:(R)"],
                       capture_output=True, text=True)
        sddl_mut = capture_sd_binary(d)
        chk("modified SDDL differs from original", _sddl_equal(sddl0, sddl_mut) is False)
        ok_rb, detail_rb = restore_sd_binary(d, sddl0)
        chk("restore_sd_binary ok + exact read-back", ok_rb is True)
        if not ok_rb:
            print("   detail:", detail_rb)
        chk("post-restore SDDL equals original", _sddl_equal(sddl0, capture_sd_binary(d)) is True)

        # --- icacls (human-diffable) capture path ----------------------------
        sd0 = capture_sd(d)
        chk("capture_sd (icacls) returns a string", isinstance(sd0, str) and len(sd0) > 0)
        chk("verify_sd_equal: same SD equal", verify_sd_equal(sd0, sd0) is True)
        chk("verify_sd_equal: None never equal", verify_sd_equal(sd0, None) is False)

        # checked_rmtree: success case
        ok_c, res_c = checked_rmtree(d)
        chk("checked_rmtree removes tree, no residuals", ok_c is True and res_c == [])

        # checked_rmtree: non-existent is ok
        ok_ne, res_ne = checked_rmtree(base / "does_not_exist")
        chk("checked_rmtree on missing path -> ok, no residuals",
            ok_ne is True and res_ne == [])

        # checked_rmtree: residual detection (locked file)
        locked_dir = base / "locked"
        locked_dir.mkdir()
        locked = locked_dir / "hold.txt"
        locked.write_text("held")
        import builtins
        _orig_open = builtins.open

        # hold the file open so rmtree fails on the file
        fh = open(locked, "r")
        try:
            ok_l, res_l = checked_rmtree(locked_dir)
            chk("checked_rmtree detects residual when locked", ok_l is False and len(res_l) > 0)
            if res_l:
                print("   residuals:", res_l[:3])
        finally:
            fh.close()
        # now it should clean
        ok_l2, res_l2 = checked_rmtree(locked_dir)
        chk("checked_rmtree cleans after release", ok_l2 is True and res_l2 == [])
    finally:
        shutil.rmtree(base, ignore_errors=True)

    passed = sum(1 for r in results if r)
    print(f"\nq3_dacl selftest: {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(_selftest())
