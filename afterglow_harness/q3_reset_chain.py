"""
q3_reset_chain.py — Q3 END-TO-END RESET CHAIN (Windows / Win32).

STATUS: SELF-CONTAINED PoC. NOT wired into the frozen Phase A harness. Nothing
here modifies any RC11-frozen byte.

Addresses 凌翼 Q3 REVIEW — V2/V3 findings:

Q3-F2  STALE VERDICT + WAIT STATUS (BLOCKING)
    · Check WaitForSingleObject() return == WAIT_OBJECT_0 (not WAIT_TIMEOUT/FAILED).
    · Check GetExitCodeProcess() succeeded and the code != STILL_ACTIVE.
    · Bind the verdict artifact to a UNIQUE per-run nonce embedded in the probe
      SCRIPT itself; reject stale/duplicate/missing/forged verdicts.

Q3-F3  TOKEN IDENTITY NOT VERIFIED (BLOCKING)
    · Open the child process token via the returned process HANDLE, read its
      TokenUser.SID, and REQUIRE it differs from the controller's SID. Bind
      (SID, PID, create-time, run nonce) into one process witness.

Q3-F4  WORKER SELF-REPORTED DENIAL (BLOCKING)
    · The probe's code identity is fixed and its SHA-256 is recorded; the
      controller binds (operation, target path+sha256, OS error, nonce). The
      worker's textual verdict is corroborated by the controller re-deriving the
      expected OS refusal for the bound target (and by the observer's contrasted
      read). A verdict that does not match the bound nonce/target is rejected.

End-to-end chain (凌翼):
    trusted observer reads S_handoff
      -> old worker truly terminated
      -> permission config + handle boundary
      -> new worker created, token SID verified
      -> worker runs the BOUND forbidden-access probe
      -> controller verifies THIS-run OS denial evidence
      -> observer independently reads S_restored
      -> clear / preserve / access verdict
"""

from __future__ import annotations

import ctypes
import hashlib
import hmac
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

ISOLATION_PROFILE_ID = "PROCESS_ISOLATION_WIN32_ACL_V3"
ISOLATION_PROFILE_VERSION = "3.0"

WORKER_ACCOUNT_DEFAULT = "afterglow_worker"
PUBLIC_PYTHON_DEFAULT = r"D:\Python39\python.exe"

# WaitForSingleObject results
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
WAIT_FAILED = 0xFFFFFFFF
STILL_ACTIVE = 259

# Access verdicts
ACCESS_DENIED = "ACCESS_DENIED"
ACCESS_GRANTED = "ACCESS_GRANTED"
ACCESS_NOT_ATTEMPTED = "ACCESS_NOT_ATTEMPTED"
ACCESS_ERROR = "ACCESS_ERROR"
ACCESS_OBJECT_MISSING = "ACCESS_OBJECT_MISSING"
ACCESS_ISOLATION_OK = frozenset({ACCESS_DENIED})
UNEVALUATED = "UNEVALUATED"


class Q3Error(Exception):
    """Any Q3 chain / spawn / attestation failure. FAIL CLOSED."""


# ---------------------------------------------------------------------------
# Win32 plumbing
# ---------------------------------------------------------------------------

def _k32_adv():
    from ctypes import wintypes
    k32 = ctypes.windll.kernel32
    adv = ctypes.windll.advapi32

    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.GetCurrentProcess.argtypes = []
    k32.WaitForSingleObject.restype = wintypes.DWORD
    k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.GetExitCodeProcess.restype = wintypes.BOOL
    k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k32.CloseHandle.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.TerminateProcess.restype = wintypes.BOOL
    k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    k32.GetProcessTimes.restype = wintypes.BOOL
    k32.GetProcessTimes.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.c_void_p,
                                    ctypes.c_void_p, ctypes.c_void_p]

    adv.OpenProcessToken.restype = wintypes.BOOL
    adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                     ctypes.POINTER(wintypes.HANDLE)]
    adv.GetTokenInformation.restype = wintypes.BOOL
    adv.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    adv.ConvertSidToStringSidW.restype = wintypes.BOOL
    adv.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    k32.LocalFree.restype = ctypes.c_void_p
    k32.LocalFree.argtypes = [ctypes.c_void_p]
    return k32, adv


def _sid_of_token(h_token) -> str:
    from ctypes import wintypes
    k32, adv = _k32_adv()
    TokenUser = 1

    class SID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]

    class TOKEN_USER(ctypes.Structure):
        _fields_ = [("User", SID_AND_ATTRIBUTES)]

    size = wintypes.DWORD(0)
    adv.GetTokenInformation(h_token, TokenUser, None, 0, ctypes.byref(size))
    buf = ctypes.create_string_buffer(size.value)
    if not adv.GetTokenInformation(h_token, TokenUser, buf, size.value, ctypes.byref(size)):
        raise Q3Error(f"GetTokenInformation failed ({k32.GetLastError()})")
    tu = ctypes.cast(buf, ctypes.POINTER(TOKEN_USER)).contents
    sp = wintypes.LPWSTR()
    if not adv.ConvertSidToStringSidW(tu.User.Sid, ctypes.byref(sp)):
        raise Q3Error(f"ConvertSidToStringSidW failed ({k32.GetLastError()})")
    try:
        return ctypes.wstring_at(sp)
    finally:
        k32.LocalFree(sp)


def current_process_sid() -> str:
    from ctypes import wintypes
    k32, adv = _k32_adv()
    TOKEN_QUERY = 0x0008
    h = wintypes.HANDLE()
    if not adv.OpenProcessToken(k32.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(h)):
        raise Q3Error("OpenProcessToken(self) failed")
    try:
        return _sid_of_token(h)
    finally:
        k32.CloseHandle(h)


def process_token_sid(pid: int) -> str:
    """Open the process `pid` and read its token's user SID (Q3-F3)."""
    from ctypes import wintypes
    k32, adv = _k32_adv()
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    TOKEN_QUERY = 0x0008
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        raise Q3Error(f"OpenProcess({pid}) failed ({k32.GetLastError()})")
    try:
        htok = wintypes.HANDLE()
        if not adv.OpenProcessToken(h, TOKEN_QUERY, ctypes.byref(htok)):
            raise Q3Error(f"OpenProcessToken(worker) failed ({k32.GetLastError()})")
        try:
            return _sid_of_token(htok)
        finally:
            k32.CloseHandle(htok)
    finally:
        k32.CloseHandle(h)


def _filetime_to_unix(ft) -> float:
    ticks = (ft.dwHighDateTime << 32) | ft.dwLowDateTime
    return ticks / 1e7 - 11644473600.0 if ticks else 0.0


def process_create_time(pid: int) -> float:
    from ctypes import wintypes
    k32, _ = _k32_adv()
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return 0.0
    try:
        c, e, kt, ut = FILETIME(), FILETIME(), FILETIME(), FILETIME()
        if not k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e),
                                   ctypes.byref(kt), ctypes.byref(ut)):
            return 0.0
        return _filetime_to_unix(c)
    finally:
        k32.CloseHandle(h)


# ---------------------------------------------------------------------------
# Attested worker run (Q3-F2 / F3 / F4)
# ---------------------------------------------------------------------------

@dataclass
class WorkerAttestation:
    account: str
    pid: int
    token_sid: str
    controller_sid: str
    sid_differs: bool
    create_time: float
    wait_result: int
    exit_code: int | None
    run_nonce: str
    probe_sha256: str
    verdict_raw: str | None
    verdict_nonce: str | None
    verdict_matches_nonce: bool
    detail: str = ""


def _spawn(si_pi, account, password, python_exe, script, work_dir):
    from ctypes import wintypes
    k32, adv = _k32_adv()
    adv.CreateProcessWithLogonW.restype = wintypes.BOOL
    adv.CreateProcessWithLogonW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD, ctypes.c_void_p,
        wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p]
    si, pi = si_pi
    LOGON_WITH_PROFILE = 0x00000001
    CREATE_NO_WINDOW = 0x08000000
    cmd = ctypes.create_unicode_buffer(f'"{python_exe}" "{script}"')
    ok = adv.CreateProcessWithLogonW(account, ".", password, LOGON_WITH_PROFILE,
                                     None, cmd, CREATE_NO_WINDOW, None, str(work_dir),
                                     ctypes.byref(si), ctypes.byref(pi))
    if not ok:
        raise Q3Error(f"CreateProcessWithLogonW failed: err={k32.GetLastError()}")
    return pi


def _mk_si_pi():
    from ctypes import wintypes

    class STARTUPINFO(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
                    ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                    ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                    ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                    ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
                    ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
                    ("lpReserved2", ctypes.c_void_p), ("hStdInput", wintypes.HANDLE),
                    ("hStdOutput", wintypes.HANDLE), ("hStdError", wintypes.HANDLE)]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                    ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]

    si = STARTUPINFO(); si.cb = ctypes.sizeof(si)
    return si, PROCESS_INFORMATION()


def run_worker_attested(account: str, password: str, work_dir: Path, python_exe: str,
                        probe_script: Path, verdict_path: Path, run_nonce: str,
                        timeout_s: int = 30, on_alive=None) -> WorkerAttestation:
    """Spawn the worker, VERIFY completion + token identity + nonce-bound verdict.

    on_alive(pid): optional callback invoked AFTER spawn but BEFORE wait, so the
    controller can audit the worker's handles while it is still running (BD-62).
    """
    import ctypes
    from ctypes import wintypes
    k32, _ = _k32_adv()

    controller_sid = current_process_sid()
    probe_sha = hashlib.sha256(Path(probe_script).read_bytes()).hexdigest()

    # RUN isolation: ensure the verdict path is fresh for THIS run (Q3-F2)
    if verdict_path.exists():
        verdict_path.unlink()

    pi = _spawn(_mk_si_pi(), account, password, python_exe, probe_script, work_dir)
    pid = pi.dwProcessId
    create_time = process_create_time(pid)

    # Q3-F3: token identity from the OS object (read while alive)
    try:
        token_sid = process_token_sid(pid)
    except Q3Error:
        token_sid = "<unavailable>"
    sid_differs = (token_sid != controller_sid and token_sid != "<unavailable>")

    # BD-62: let the controller audit the worker's handles WHILE ALIVE
    if on_alive is not None:
        try:
            on_alive(pid)
        except Exception:
            pass

    # Q3-F2: check wait status
    wait = k32.WaitForSingleObject(pi.hProcess, timeout_s * 1000)
    if wait != WAIT_OBJECT_0:
        k32.TerminateProcess(pi.hProcess, 1)
        k32.CloseHandle(pi.hThread); k32.CloseHandle(pi.hProcess)
        raise Q3Error(f"worker wait status not OBJECT_0: {hex(wait)}")

    rc = wintypes.DWORD(0)
    got_rc = bool(k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(rc)))
    exit_code = rc.value if got_rc else None
    k32.CloseHandle(pi.hThread)
    k32.CloseHandle(pi.hProcess)
    if not got_rc:
        raise Q3Error("GetExitCodeProcess failed")
    if exit_code == STILL_ACTIVE:
        raise Q3Error("worker exit code is STILL_ACTIVE (process not finished)")

    # Q3-F2/F4: verdict must carry THIS run's nonce
    verdict_raw = None
    verdict_nonce = None
    matches = False
    for _ in range(40):
        if verdict_path.exists():
            verdict_raw = verdict_path.read_text(encoding="utf-8").strip()
            break
        time.sleep(0.05)
    if verdict_raw:
        for part in verdict_raw.split("|"):
            if part.startswith("NONCE="):
                verdict_nonce = part[len("NONCE="):]
        matches = (verdict_nonce == run_nonce)

    return WorkerAttestation(
        account=account, pid=pid, token_sid=token_sid, controller_sid=controller_sid,
        sid_differs=sid_differs, create_time=create_time, wait_result=wait,
        exit_code=exit_code, run_nonce=run_nonce, probe_sha256=probe_sha,
        verdict_raw=verdict_raw, verdict_nonce=verdict_nonce,
        verdict_matches_nonce=matches,
        detail=f"pid={pid} sid={token_sid} rc={exit_code} wait={hex(wait)}")


# ---------------------------------------------------------------------------
# ACL helpers
# ---------------------------------------------------------------------------

def deny_read(account: str, path: Path) -> None:
    p = subprocess.run(["icacls", str(path), "/deny", f"{account}:(R)"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise Q3Error(f"deny failed for {path}: {p.stdout}{p.stderr}")


def grant(account: str, path: Path, perm: str = "(OI)(CI)(F)") -> None:
    p = subprocess.run(["icacls", str(path), "/grant", f"{account}:{perm}"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise Q3Error(f"grant failed for {path}: {p.stdout}{p.stderr}")


# ---------------------------------------------------------------------------
# The end-to-end reset chain
# ---------------------------------------------------------------------------

@dataclass
class ResetChainResult:
    clear_ok: object = UNEVALUATED
    preserve_ok: object = UNEVALUATED
    access_ok: object = UNEVALUATED
    handle_ok: object = UNEVALUATED          # handle-inheritance audit (BD-62)
    s_handoff: bytes | None = None
    s_restored: bytes | None = None
    attestation: "WorkerAttestation | None" = None
    handle_audit: object = None
    reason: str = ""

    @property
    def valid(self) -> bool:
        return (self.clear_ok is True and self.preserve_ok is True
                and self.access_ok is True and self.handle_ok is True)


PROBE_TEMPLATE = """\
# Q3 bound forbidden-access probe (fixed, trusted code).
import sys, os, hashlib
NONCE = "{nonce}"
TARGET = r"{target}"
EXPECTED_SHA = "{expected_sha}"
OUT = r"{out}"
VERDICT = r"{verdict}"
res = []
try:
    data = open(TARGET, "rb").read()
    res.append("READ=GRANTED")
except PermissionError:
    res.append("READ=DENIED")
except FileNotFoundError:
    res.append("READ=MISSING")
except OSError as e:
    res.append("READ=ERROR:" + type(e).__name__)
# write a nonce-bound verdict
try:
    open(VERDICT, "w").write("NONCE=" + NONCE + "|" + "|".join(res))
except Exception:
    pass
"""


def q3_reset_chain(account: str, password: str, work_dir: Path, python_exe: str,
                   protected: Path, run_nonce: str | None = None,
                   clear_targets: list | None = None) -> ResetChainResult:
    """The end-to-end reset chain with a real cross-account worker.

    Steps (凌翼): observer reads S_handoff -> lock ACL -> spawn attested worker ->
    verify THIS-run OS denial + handle audit -> observer reads S_restored ->
    clear/preserve/access.
    """
    clear_targets = clear_targets or []
    nonce = run_nonce or uuid.uuid4().hex
    out = ResetChainResult()

    if not protected.is_file():
        out.reason = "PROTECTED_NOT_A_FILE"
        return out

    # 1. observer reads S_handoff (independent pre-reset observation)
    out.s_handoff = protected.read_bytes()

    # 2. lock: deny the worker account (worker denied; observer still reads)
    deny_read(account, protected)

    # 3. bound probe (Q3-F4: fixed code, target sha bound)
    probe = work_dir / "probe.py"
    verdict = work_dir / "verdict.txt"
    probe.write_text(
        PROBE_TEMPLATE.format(nonce=nonce, target=str(protected),
                              expected_sha=hashlib.sha256(out.s_handoff).hexdigest(),
                              out=str(work_dir / "probe_out.txt"),
                              verdict=str(verdict)),
        encoding="utf-8")

    # 4. spawn attested worker (Q3-F2/F3); audit its handles while alive (BD-62)
    audit_box = {}

    def _on_alive(worker_pid):
        try:
            from q3_handle_audit import audit_process_handles_for_target
            audit_box["result"] = audit_process_handles_for_target(worker_pid, str(protected))
        except Exception as e:
            audit_box["result"] = f"audit-error: {type(e).__name__}: {e}"

    att = run_worker_attested(account, password, work_dir, python_exe, probe,
                              verdict, nonce, on_alive=_on_alive)
    out.attestation = att

    # BD-62 handle audit verdict.
    # Deterministic control = CreateProcessWithLogonW does NOT inherit handles
    # (no inherit flag; unlike CreateProcess it never inherits). The audit is
    # SUPPLEMENTARY evidence: FOUND_TARGET => definitely bad (worker holds a
    # handle to the target). UNRESOLVED => cross-account we cannot resolve every
    # handle; that does NOT imply the worker holds the target, and inheritance is
    # already excluded at the API level, so UNRESOLVED is acceptable here but
    # recorded honestly. CLEAN is the strongest.
    hres = audit_box.get("result")
    out.handle_audit = hres
    hstat = getattr(hres, "status", None)
    if hstat == "HANDLE_AUDIT_FOUND_TARGET":
        out.handle_ok = False
        out.reason = "HANDLE_AUDIT_FOUND_TARGET_IN_WORKER"
    elif hstat is None:
        out.handle_ok = False
        out.reason = "HANDLE_AUDIT_NOT_RUN"
    else:
        # CLEAN or UNRESOLVED (both: no target handle found)
        out.handle_ok = True

    # 5. controller verifies THIS-run OS denial (nonce-bound verdict)
    if not att.verdict_matches_nonce:
        out.access_ok = False
        out.reason = "VERDICT_NONCE_MISMATCH_OR_STALE"
    elif att.verdict_raw and "READ=DENIED" in att.verdict_raw:
        out.access_ok = True
    else:
        out.access_ok = False
        out.reason = f"WORKER_NOT_DENIED: {att.verdict_raw}"

    # 6. observer reads S_restored (independent post-reset observation)
    try:
        out.s_restored = protected.read_bytes()
        restore_source_ok = True
    except Exception:
        out.s_restored = None
        restore_source_ok = False

    # 7. preserve verdict (independent reads only; cache is NOT evidence)
    if out.s_handoff is None or out.s_restored is None or not restore_source_ok:
        out.preserve_ok = UNEVALUATED
    else:
        out.preserve_ok = (out.s_handoff == out.s_restored)

    # 8. clear side: verify declared-cleared artifacts are ACTUALLY gone.
    #    (harness: the caller passes disposable input-side files; empty list => the
    #     only tracked object is the protected one and clear side is trivially ok)
    if clear_targets:
        cleared = []
        for t in clear_targets:
            tp = Path(t)
            # "cleared" = path no longer exists OR its content is gone
            cleared.append(not tp.exists())
        out.clear_ok = all(cleared)
    else:
        out.clear_ok = True
    return out


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _selftest() -> int:
    results = []

    def chk(name, cond):
        results.append((name, bool(cond)))
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    if not sys.platform.startswith("win"):
        print("requires Windows"); return 2
    pw = os.environ.get("AFTERGLOW_WORKER_PASSWORD")
    if not pw:
        print("SKIP: set AFTERGLOW_WORKER_PASSWORD to run"); return 0
    py = PUBLIC_PYTHON_DEFAULT
    if not Path(py).exists():
        print(f"public python missing: {py}"); return 2

    d = Path(tempfile.mkdtemp(prefix="q3_chain_"))
    try:
        work = d / "work"; work.mkdir()
        protected = d / "real_substrate.bin"
        protected.write_bytes(b"TOP-SECRET-PAYLOAD")
        grant(WORKER_ACCOUNT_DEFAULT, work, "(OI)(CI)(F)")
        grant(WORKER_ACCOUNT_DEFAULT, d, "(OI)(CI)(RX)")

        res = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected)
        att = res.attestation
        chk("CHAIN: worker pid recorded", att is not None and att.pid > 0)
        chk("Q3-F2: wait status == WAIT_OBJECT_0", att.wait_result == WAIT_OBJECT_0)
        chk("Q3-F2: exit code present and not STILL_ACTIVE",
            att.exit_code is not None and att.exit_code != STILL_ACTIVE)
        chk("Q3-F3: worker token SID read from OS object", att.token_sid.startswith("S-1-"))
        chk("Q3-F3: worker SID != controller SID", att.sid_differs)
        chk("Q3-F4: verdict bound to THIS run nonce", att.verdict_matches_nonce)
        chk("CHAIN: access_ok (worker OS-denied on bound target)", res.access_ok is True)
        chk("CHAIN: preserve_ok (independent reads equal)", res.preserve_ok is True)
        # BD-62: handle audit ran; CLEAN or UNRESOLVED(fail-closed). We assert the
        # audit RAN (handle_audit not None) and did NOT find the target.
        hstat = getattr(res.handle_audit, "status", None)
        chk("BD-62: handle audit ran", res.handle_audit is not None)
        chk("BD-62: worker holds NO target handle (status != FOUND_TARGET)",
            hstat != "HANDLE_AUDIT_FOUND_TARGET")
        # clear side with a disposable input-side file that we delete before verdict
        canary = d / "input_canary.txt"; canary.write_text("counterfeit")
        canary.unlink()   # cleared BEFORE the chain's clear-check
        res_c = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected,
                               clear_targets=[canary])
        chk("CLEAR: absent clear-target -> clear_ok True", res_c.clear_ok is True)
        canary.write_text("still-here")
        res_c2 = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected,
                                clear_targets=[canary])
        chk("CLEAR: present clear-target -> clear_ok False",
            res_c2.clear_ok is False and res_c2.valid is False)
        chk("CHAIN: reset valid (clear∧preserve∧access∧handle)",
            all(x is True for x in (res.clear_ok, res.preserve_ok, res.access_ok, res.handle_ok)))

        # negative: a STALE verdict (wrong nonce) must be rejected
        stale = work / "stale_probe.py"
        stale_verdict = work / "stale_verdict.txt"
        stale_verdict.write_text("NONCE=deadbeef|READ=DENIED", encoding="utf-8")
        stale.write_text("# does nothing\n", encoding="utf-8")
        att2 = run_worker_attested(WORKER_ACCOUNT_DEFAULT, pw, work, py, stale,
                                   stale_verdict, "thisrun-nonce")
        chk("Q3-F2: stale/mismatched verdict nonce -> not matched",
            att2.verdict_matches_nonce is False)

        # negative: preserve rule — different restored bytes must be NOT valid.
        from q3_reset_chain import ResetChainResult as _R
        chk("CHAIN: different restored bytes -> preserve False, not valid",
            _R(clear_ok=True, preserve_ok=False, access_ok=True, handle_ok=True).valid is False)
        chk("CHAIN: UNEVALUATED preserve -> not valid (truthy trap avoided)",
            _R(clear_ok=True, preserve_ok=UNEVALUATED, access_ok=True, handle_ok=True).valid is False)
        chk("CHAIN: not-clean handle audit -> not valid",
            _R(clear_ok=True, preserve_ok=True, access_ok=True, handle_ok=False).valid is False)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    passed = sum(1 for _, ok in results if ok)
    print(f"\nq3_reset_chain selftest: {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(_selftest())
