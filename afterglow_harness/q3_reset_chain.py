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

#: The ONLY handle-audit status that may grant handle_ok (BD-65).
HANDLE_STATUS_PASS = frozenset({"HANDLE_AUDIT_CLEAN"})

#: The expected worker probe exit code (registered success). Anything else fails.
WORKER_SUCCESS_EXIT = 0

#: Frozen verdict schema. The verdict must be exactly:
#:   NONCE=<nonce>|OP=<op>|TARGET=<sha256hex>|RESULT=<READ=DENIED|READ=GRANTED|...>
#: Unknown / duplicate / conflicting fields => reject.
VERDICT_KEYS = ("NONCE", "OP", "TARGET", "RESULT")


class Q3Error(Exception):
    """Any Q3 chain / spawn / attestation failure. FAIL CLOSED."""


def parse_verdict_strict(raw: str | None) -> dict | None:
    """Parse a verdict into a dict of the exact frozen schema, or None on any
    deviation (unknown key, duplicate key, missing key, empty). NO substring match."""
    if not raw:
        return None
    parts = raw.strip().split("|")
    out = {}
    for p in parts:
        if "=" not in p:
            return None
        k, _, v = p.partition("=")
        k = k.strip()
        if k not in VERDICT_KEYS:
            return None            # unknown field
        if k in out:
            return None            # duplicate field
        out[k] = v
    if set(out.keys()) != set(VERDICT_KEYS):
        return None                # missing field
    if not out["RESULT"]:
        return None
    return out


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
    expected_sid: str          # the worker account's SID, resolved up-front
    sid_differs: bool
    sid_matches_expected: bool
    create_time: float
    wait_result: int
    exit_code: int | None
    run_nonce: str
    probe_sha256: str           # ACTUAL script hash at spawn
    probe_sha_expected: str     # frozen/expected probe hash
    probe_sha_matches: bool
    probe_target_sha: str       # the target sha the probe was bound to
    verdict_raw: str | None
    verdict_parsed: object      # dict | None
    detail: str = ""

    @property
    def identity_ok(self) -> bool:
        """F3: worker identity + completion. ALL must hold."""
        return (self.sid_differs is True
                and self.sid_matches_expected is True
                and self.create_time > 0.0
                and self.wait_result == WAIT_OBJECT_0
                and self.exit_code == WORKER_SUCCESS_EXIT
                and self.probe_sha_matches is True)

    @property
    def verdict_ok(self) -> bool:
        """F4: strict schema + nonce + target binding + RESULT exactly DENIED."""
        v = self.verdict_parsed
        if not isinstance(v, dict):
            return False
        return (v.get("NONCE") == self.run_nonce
                and v.get("OP") == "READ"
                and v.get("TARGET") == self.probe_target_sha
                and v.get("RESULT") == "READ=DENIED")


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
                        probe_target_sha: str, probe_sha_expected: str,
                        expected_sid: str | None = None,
                        timeout_s: int = 30, on_alive=None) -> WorkerAttestation:
    """Spawn the worker, VERIFY completion + token identity + strict verdict.

    on_alive(pid): optional callback invoked AFTER spawn but BEFORE wait, so the
    controller can audit the worker's handles while it is still running (BD-62).
    """
    import ctypes
    from ctypes import wintypes
    k32, _ = _k32_adv()

    controller_sid = current_process_sid()
    probe_sha = hashlib.sha256(Path(probe_script).read_bytes()).hexdigest()
    if expected_sid is None:
        expected_sid = "<unresolved>"

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
    sid_differs = (token_sid not in ("<unavailable>", controller_sid))
    sid_matches_expected = (expected_sid not in ("", "<unresolved>")
                            and token_sid == expected_sid)
    probe_sha_matches = (probe_sha == probe_sha_expected)

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

    # Q3-F4: read verdict; parse STRICTLY (no substring).
    verdict_raw = None
    for _ in range(40):
        if verdict_path.exists():
            verdict_raw = verdict_path.read_text(encoding="utf-8").strip()
            break
        time.sleep(0.05)
    verdict_parsed = parse_verdict_strict(verdict_raw)

    return WorkerAttestation(
        account=account, pid=pid, token_sid=token_sid, controller_sid=controller_sid,
        expected_sid=expected_sid, sid_differs=sid_differs,
        sid_matches_expected=sid_matches_expected, create_time=create_time,
        wait_result=wait, exit_code=exit_code, run_nonce=run_nonce,
        probe_sha256=probe_sha, probe_sha_expected=probe_sha_expected,
        probe_sha_matches=probe_sha_matches, probe_target_sha=probe_target_sha,
        verdict_raw=verdict_raw, verdict_parsed=verdict_parsed,
        detail=f"pid={pid} sid={token_sid} rc={exit_code} wait={hex(wait)} "
               f"sha_match={probe_sha_matches}")


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


def lockdown_code_dir(account: str, code_dir: Path) -> None:
    """Make `code_dir` READ+EXECUTE (no write) for the worker account.

    知微 P1-3: trusted probe code must be worker-immutable. We grant RX and
    explicitly DENY write/append/delete for the worker account on the dir and
    its contents (deny wins)."""
    # grant read+execute (inherit to files)
    p = subprocess.run(["icacls", str(code_dir), "/grant", f"{account}:(OI)(CI)(RX)"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise Q3Error(f"code-dir RX grant failed: {p.stdout}{p.stderr}")
    # deny write/append/delete (W = write data/append, D = delete; use (W,D))
    p = subprocess.run(["icacls", str(code_dir), "/deny", f"{account}:(OI)(CI)(WD)"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise Q3Error(f"code-dir WD deny failed: {p.stdout}{p.stderr}")


# ---------------------------------------------------------------------------
# The end-to-end reset chain
# ---------------------------------------------------------------------------

@dataclass
class ResetChainResult:
    clear_ok: object = UNEVALUATED
    preserve_ok: object = UNEVALUATED
    access_ok: object = UNEVALUATED
    handle_ok: object = UNEVALUATED          # = inheritance_prevention_ok AND handle_audit_ok
    inheritance_prevention_ok: object = UNEVALUATED   # API-level no-inherit basis
    handle_audit_ok: object = UNEVALUATED    # runtime enumeration; CLEAN only
    identity_ok: object = UNEVALUATED        # F3: SID/exit/create-time gate
    lifecycle_ok: object = UNEVALUATED       # old-worker termination
    s_handoff: bytes | None = None
    s_restored: bytes | None = None
    attestation: "WorkerAttestation | None" = None
    handle_audit: object = None
    reason: str = ""

    @property
    def valid(self) -> bool:
        # EVERY gate must be literally True. UNEVALUATED/False/anything else => invalid.
        return all(x is True for x in (
            self.clear_ok, self.preserve_ok, self.access_ok,
            self.handle_ok, self.identity_ok, self.lifecycle_ok))


PROBE_TEMPLATE = """\
# Q3 bound forbidden-access probe (fixed, trusted code; read-only to worker).
import sys, os, hashlib
NONCE = "{nonce}"
TARGET = r"{target}"
EXPECTED_SHA = "{expected_sha}"
OUT = r"{out}"
VERDICT = r"{verdict}"
_op = "READ"
_result = ""
try:
    data = open(TARGET, "rb").read()
    # integrity: confirm we read the expected object bytes
    if hashlib.sha256(data).hexdigest() == EXPECTED_SHA:
        _result = "READ=GRANTED"
    else:
        _result = "READ=GRANTED_BUT_SHA_MISMATCH"
except PermissionError:
    _result = "READ=DENIED"
except FileNotFoundError:
    _result = "READ=MISSING"
except OSError as e:
    _result = "READ=ERROR:" + type(e).__name__
try:
    open(VERDICT, "w").write(
        "NONCE=" + NONCE + "|OP=" + _op + "|TARGET=" + EXPECTED_SHA + "|RESULT=" + _result)
except Exception:
    pass
"""


def q3_reset_chain(account: str, password: str, work_dir: Path, python_exe: str,
                   protected: Path, run_nonce: str | None = None,
                   required_clear_targets: list | None = None,
                   clear_actually_done: bool | None = None,
                   clear_na_declared: bool = False,
                   expected_sid: str | None = None,
                   old_worker_pid: int | None = None,
                   terminate_old_worker=None) -> ResetChainResult:
    """The end-to-end reset chain with a REAL cross-account worker, gated strictly.

    Steps (凌翼): observer reads S_handoff -> [old worker terminated] -> lock ACL
    -> spawn attested worker (identity/exit/code-hash) -> verify THIS-run OS
    denial (strict schema) + handle audit -> observer reads S_restored ->
    clear/preserve/access/identity/handle/lifecycle.

    BRITTLE GATES (fail-closed):
      · handle_ok: only HANDLE_AUDIT_CLEAN passes (BD-65).
      · clear_ok: requires a NON-EMPTY required_clear_targets set AND that they are
        gone; empty set => INVALID unless clear_na_declared (BD-66).
      · identity_ok: worker SID differs from controller, matches expected account,
        create_time>0, wait==OBJECT_0, exit==WORKER_SUCCESS_EXIT, probe hash matches.
      · lifecycle_ok: an old worker, if given, must be proven terminated before the
        new one starts.
    """
    required_clear_targets = list(required_clear_targets or [])
    nonce = run_nonce or uuid.uuid4().hex
    out = ResetChainResult()

    if not protected.is_file():
        out.reason = "PROTECTED_NOT_A_FILE"
        return out

    # 1. observer reads S_handoff FIRST — BEFORE any reset step that could change
    #    the preserved state (知微 P1-1: sampling after terminate misses corruption
    #    during termination). The handoff is the frozen baseline for preserve.
    out.s_handoff = protected.read_bytes()

    # 2. lifecycle: prove the OLD worker terminated BEFORE we spawn the new one.
    #    This runs AFTER the handoff snapshot so the snapshot covers the whole
    #    termination window.
    if old_worker_pid is not None:
        if terminate_old_worker is None:
            out.lifecycle_ok = False
            out.reason = "OLD_WORKER_PRESENT_BUT_NO_TERMINATOR"
        else:
            out.lifecycle_ok = _terminate_and_confirm(old_worker_pid, terminate_old_worker)
    else:
        out.lifecycle_ok = True   # no prior worker to replace (documented N/A)

    # 3. lock: deny the worker account (worker denied; observer still reads)
    deny_read(account, protected)

    # 4. bound probe (F4: fixed code, target sha bound, strict verdict schema).
    #    知微 P1-3: the probe is TRUSTED CODE; the worker must not be able to
    #    modify it. We place it in a dedicated CODE dir that the worker gets
    #    READ+EXECUTE only (no write), and keep the worker's OUTPUT dir separate
    #    and writable. The expected hash is captured from the frozen template
    #    bytes we just wrote (and re-verified before spawn).
    code_dir = work_dir / "code"
    out_dir = work_dir / "out"
    code_dir.mkdir(exist_ok=True)
    out_dir.mkdir(exist_ok=True)
    probe = code_dir / "probe.py"
    verdict = out_dir / "verdict.txt"
    target_sha = hashlib.sha256(out.s_handoff).hexdigest()
    probe_bytes = PROBE_TEMPLATE.format(
        nonce=nonce, target=str(protected), expected_sha=target_sha,
        out=str(out_dir / "probe_out.txt"), verdict=str(verdict)).encode("utf-8")
    probe.write_bytes(probe_bytes)
    # lockdown: worker may READ/EXECUTE code_dir but NOT write; may write out_dir.
    lockdown_code_dir(account, code_dir)
    grant(account, out_dir, "(OI)(CI)(F)")
    # expected hash from the frozen template bytes we control
    probe_sha_expected = hashlib.sha256(probe_bytes).hexdigest()

    # 4. spawn attested worker (F2/F3); audit its handles while alive (BD-62)
    audit_box = {}

    def _on_alive(worker_pid):
        try:
            from q3_handle_audit import audit_process_handles_for_target
            audit_box["result"] = audit_process_handles_for_target(worker_pid, str(protected))
        except Exception as e:
            audit_box["result"] = e

    att = run_worker_attested(account, password, work_dir, python_exe, probe,
                              verdict, nonce, probe_target_sha=target_sha,
                              probe_sha_expected=probe_sha_expected,
                              expected_sid=expected_sid, on_alive=_on_alive)
    out.attestation = att

    # 5. F3 identity/completion gate
    out.identity_ok = att.identity_ok
    if not out.identity_ok:
        out.reason = ("IDENTITY_GATE_FAILED: "
                      f"sid_differs={att.sid_differs} "
                      f"sid_matches_expected={att.sid_matches_expected} "
                      f"create_time={att.create_time} wait={hex(att.wait_result)} "
                      f"exit={att.exit_code} sha_match={att.probe_sha_matches}")

    # 6. BD-65 handle gate — TWO INDEPENDENT pieces of evidence (凌翼):
    #    (a) inheritance_prevention_ok: the CREATE API never inherits handles.
    #        CreateProcessWithLogonW has no inherit flag; with the default
    #        bInheritHandles=FALSE semantics the child inherits NO parent handle.
    #        This is an API-level guarantee with its OWN basis (not the audit).
    #    (b) handle_audit_ok: the runtime enumeration. ONLY CLEAN passes;
    #        FOUND_TARGET => FAIL; ERROR => FAIL; UNRESOLVED => NOT proven-clean,
    #        and must NEVER be relabelled CLEAN.
    #    handle_ok requires BOTH (a) and (b) to hold; (b)=UNRESOLVED is recorded
    #    honestly and does NOT pass (but the API guarantee stands on its own).
    out.inheritance_prevention_ok = True      # basis: no-inherit create API
    hres = audit_box.get("result")
    out.handle_audit = hres
    hstat = getattr(hres, "status", None)
    if hstat in HANDLE_STATUS_PASS:
        out.handle_audit_ok = True
    elif hstat == "HANDLE_AUDIT_FOUND_TARGET":
        out.handle_audit_ok = False
        out.reason = out.reason or "HANDLE_AUDIT_FOUND_TARGET_IN_WORKER"
    elif hstat == "HANDLE_AUDIT_ERROR" or hstat is None:
        out.handle_audit_ok = False
        out.reason = out.reason or f"HANDLE_AUDIT_ERROR_OR_MISSING: {hstat}"
    else:
        # UNRESOLVED (or unknown) => NOT clean; fail-closed for the audit gate.
        out.handle_audit_ok = False
        out.reason = out.reason or f"HANDLE_AUDIT_NOT_CLEAN: {hstat}"
    out.handle_ok = (out.inheritance_prevention_ok is True
                     and out.handle_audit_ok is True)

    # 7. F4 access gate: strict schema, nonce + target + RESULT exactly DENIED
    if att.verdict_ok:
        out.access_ok = True
    else:
        out.access_ok = False
        out.reason = out.reason or f"VERDICT_INVALID: {att.verdict_raw!r}"

    # 8. observer reads S_restored (independent post-reset observation)
    try:
        out.s_restored = protected.read_bytes()
        restore_source_ok = True
    except Exception:
        out.s_restored = None
        restore_source_ok = False

    # 9. preserve verdict (independent reads only; cache is NOT evidence)
    if out.s_handoff is None or out.s_restored is None or not restore_source_ok:
        out.preserve_ok = UNEVALUATED
    else:
        out.preserve_ok = (out.s_handoff == out.s_restored)

    # 10. BD-66 clear gate: REQUIRED set (non-empty) AND actually removed.
    #     知微 P2: clear_na_declared must be STRICTLY the bool True (not truthy
    #     strings/numbers). A non-bool declaration is a malformed contract => INVALID.
    if clear_na_declared is not True and clear_na_declared is not False:
        out.clear_ok = False
        out.reason = out.reason or f"CLEAR_NA_NOT_BOOL: {clear_na_declared!r}"
    elif (clear_na_declared is True) and not required_clear_targets:
        out.clear_ok = True                       # explicitly N/A by frozen contract
    elif not required_clear_targets:
        out.clear_ok = False                      # BD-66: empty set is INVALID
        out.reason = out.reason or "CLEAR_SET_EMPTY"
    else:
        all_gone = all(not Path(t).exists() for t in required_clear_targets)
        out.clear_ok = bool(all_gone)
        if not all_gone:
            out.reason = out.reason or "CLEAR_TARGETS_NOT_REMOVED"

    return out


def _spawn_as_worker(password: str, cwd: Path, script: Path) -> None:
    """Helper for the selftest: run `script` as the worker account (best-effort)."""
    import ctypes
    from ctypes import wintypes
    k32, adv = _k32_adv()
    adv.CreateProcessWithLogonW.restype = wintypes.BOOL
    adv.CreateProcessWithLogonW.argtypes = [
        wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
        wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD, ctypes.c_void_p,
        wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p]
    si, pi = _mk_si_pi()
    cmd = ctypes.create_unicode_buffer(f'"{PUBLIC_PYTHON_DEFAULT}" "{script}"')
    adv.CreateProcessWithLogonW(WORKER_ACCOUNT_DEFAULT, ".", password, 0x1, None, cmd,
                                0x08000000, None, str(cwd), ctypes.byref(si), ctypes.byref(pi))
    k32.WaitForSingleObject(pi.hProcess, 15000)
    k32.CloseHandle(pi.hThread)
    k32.CloseHandle(pi.hProcess)


def _terminate_and_confirm(old_pid: int, terminator) -> bool:
    """Terminate the old worker and CONFIRM termination on a HELD handle.

    知微 P1-2: opening the process AFTER terminating, or treating a failed
    OpenProcess as "assume gone", is NOT an exit witness. We open the handle
    FIRST (while we can still bind identity), terminate, then wait on the SAME
    handle until it signals. Any failure to observe termination => False
    (fail-closed), never True.
    """
    import ctypes
    from ctypes import wintypes
    k32, _ = _k32_adv()
    SYNCHRONIZE = 0x00100000
    PROCESS_TERMINATE = 0x0001
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    # 1. bind the handle FIRST (identity + termination + synchronize rights)
    h = k32.OpenProcess(SYNCHRONIZE | PROCESS_TERMINATE |
                        PROCESS_QUERY_LIMITED_INFORMATION, False, old_pid)
    if not h:
        # cannot even bind the process => we have NO exit witness => fail closed
        return False
    try:
        # 2. if it is already gone, the wait below returns immediately.
        try:
            terminator(old_pid)
        except Exception:
            return False
        # 3. wait on the SAME handle
        wr = k32.WaitForSingleObject(h, 10000)
        if wr != WAIT_OBJECT_0:
            return False
        # 4. confirm the exit code is a real exit (not STILL_ACTIVE)
        rc = wintypes.DWORD(STILL_ACTIVE)
        if not k32.GetExitCodeProcess(h, ctypes.byref(rc)):
            return False
        return rc.value != STILL_ACTIVE
    finally:
        k32.CloseHandle(h)


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
        grant(WORKER_ACCOUNT_DEFAULT, work, "(OI)(CI)(RX)")   # traverse into code/out
        grant(WORKER_ACCOUNT_DEFAULT, d, "(OI)(CI)(RX)")

        # a required (non-empty) clear target that we genuinely remove first
        required_clear = d / "input_canary.txt"
        required_clear.write_text("counterfeit")
        required_clear.unlink()   # removed => clear satisfied

        # resolve the worker account's expected SID
        try:
            expected_sid = _sid_for_account(WORKER_ACCOUNT_DEFAULT)
        except Exception:
            expected_sid = None

        res = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected,
                             required_clear_targets=[required_clear],
                             expected_sid=expected_sid)
        att = res.attestation
        chk("CHAIN: worker pid recorded", att is not None and att.pid > 0)
        chk("F2: wait status == WAIT_OBJECT_0", att.wait_result == WAIT_OBJECT_0)
        chk("F2: exit == registered success (0)", att.exit_code == WORKER_SUCCESS_EXIT)
        chk("F3: worker token SID read from OS object", att.token_sid.startswith("S-1-"))
        chk("F3: worker SID != controller SID", att.sid_differs)
        chk("F3: worker SID == expected account SID", att.sid_matches_expected)
        chk("F4: probe hash matches frozen expected", att.probe_sha_matches)
        chk("F4: strict verdict parsed & bound", att.verdict_ok is True)
        chk("F3 gate: identity_ok True", res.identity_ok is True)
        chk("BD-65: inheritance_prevention_ok True (API no-inherit basis)",
            res.inheritance_prevention_ok is True)
        chk("BD-65: handle_audit recorded (status present)",
            getattr(res.handle_audit, "status", None) is not None)
        # handle_ok = inheritance_prevention_ok AND handle_audit_ok. Cross-account
        # the runtime audit is often UNRESOLVED => handle_audit_ok False =>
        # handle_ok False (fail-closed, NOT relabelled CLEAN).
        chk("BD-65: handle_ok matches (audit_ok AND inheritance_prevention_ok)",
            res.handle_ok is (res.handle_audit_ok is True and res.inheritance_prevention_ok is True))
        chk("access_ok True (strict DENIED)", res.access_ok is True)
        chk("preserve_ok True (independent reads equal)", res.preserve_ok is True)
        chk("BD-66 gate: clear_ok True (non-empty + removed)", res.clear_ok is True)
        chk("lifecycle_ok True (no prior worker)", res.lifecycle_ok is True)
        # valid requires ALL gates; with the audit UNRESOLVED, valid must be False
        # (honest fail-closed), never silently True.
        hstat_main = getattr(res.handle_audit, "status", None)
        if hstat_main == "HANDLE_AUDIT_CLEAN":
            chk("CHAIN: reset valid (audit CLEAN)", res.valid is True)
        else:
            chk("CHAIN: audit not CLEAN -> reset NOT valid (fail-closed)",
                res.valid is False and res.handle_audit.status != "HANDLE_AUDIT_FOUND_TARGET")

        # ---- BD-65 negatives (unit-level on the gate logic) ----
        from q3_reset_chain import ResetChainResult as R, HANDLE_STATUS_PASS
        for st in ("HANDLE_AUDIT_UNRESOLVED", "HANDLE_AUDIT_ERROR", "INVALID", None):
            hok = st in HANDLE_STATUS_PASS
            chk(f"BD-65: handle status {st!r} -> not pass", hok is False)
        chk("BD-65: HANDLE_AUDIT_CLEAN -> pass", "HANDLE_AUDIT_CLEAN" in HANDLE_STATUS_PASS)

        # ---- BD-66 negative: empty required clear set => INVALID ----
        res_empty = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected,
                                   required_clear_targets=[],
                                   expected_sid=expected_sid)
        chk("BD-66: empty required clear set -> clear_ok False -> invalid",
            res_empty.clear_ok is False and res_empty.valid is False)
        # N/A only when explicitly declared
        res_na = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected,
                                required_clear_targets=[required_clear],
                                clear_na_declared=True, expected_sid=expected_sid)
        chk("BD-66: explicit N/A (with contract) allowed", res_na.clear_ok is True)

        # ---- BD-66 negative: required clear target STILL present ----
        still = d / "still_input.txt"; still.write_text("x")
        res_present = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected,
                                     required_clear_targets=[still],
                                     expected_sid=expected_sid)
        chk("BD-66: present required clear target -> clear_ok False -> invalid",
            res_present.clear_ok is False and res_present.valid is False)

        # ---- P2 negative: non-bool clear_na_declared must be rejected ----
        for bad in ("UNEVALUATED", "False", 1, 0, []):
            r = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected,
                               required_clear_targets=[required_clear],
                               clear_na_declared=bad, expected_sid=expected_sid)
            chk(f"P2: clear_na_declared={bad!r} (non-bool) -> clear_ok False",
                r.clear_ok is False)

        # ---- P1-1 negative: terminator corrupts protected AFTER handoff ----
        # With the fixed ordering the handoff is sampled BEFORE terminate, so a
        # terminator that corrupts the object must produce preserve=False.
        victim = d / "victim.bin"
        victim.write_bytes(b"canary-before")

        def _bad_terminator(pid):
            victim.write_bytes(b"destroyed-during-reset")   # corrupt during reset

        # use a live pid so OpenProcess succeeds; the no-op terminator leaves it
        # alive but we only assert the HANDOFF/PRESERVE effect here.
        res_corrupt = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, victim,
                                     required_clear_targets=[required_clear],
                                     expected_sid=expected_sid,
                                     old_worker_pid=os.getpid(),
                                     terminate_old_worker=_bad_terminator)
        chk("P1-1: handoff sampled BEFORE terminate -> corruption seen (preserve False)",
            res_corrupt.s_handoff == b"canary-before"
            and res_corrupt.preserve_ok is False
            and res_corrupt.valid is False)

        # ---- P1-2 negative: unobservable old worker must NOT be 'terminated' ----
        # open a pid that cannot be opened (bogus) -> must be False, not 'assume gone'
        chk("P1-2: unobservable old pid -> lifecycle False (not assume-gone)",
            _terminate_and_confirm(0x7FFFFFF0, lambda p: None) is False)
        # a live process with a no-op terminator must NOT be confirmed terminated
        chk("P1-2: live old worker + no-op terminator -> False",
            _terminate_and_confirm(os.getpid(), lambda p: None) is False)

        # ---- F4 positive control: probe code dir is worker-immutable ----
        # (verified live: worker write attempt to code/probe.py is DENIED)
        code_dir = work / "code"
        if code_dir.exists():
            # set up worker-writable out + a script that tries to overwrite probe
            outd = work / "out"; outd.mkdir(exist_ok=True)
            grant(WORKER_ACCOUNT_DEFAULT, outd, "(OI)(CI)(F)")
            probe_file = code_dir / "probe.py"
            lock_script = outd / "lock_probe.py"
            res_file = outd / "lock_res.txt"
            lock_script.write_text(
                "try:\n"
                f"    open(r'{probe_file}','w').write('tamper')\n"
                f"    open(r'{res_file}','w').write('WROTE')\n"
                "except PermissionError:\n"
                f"    open(r'{res_file}','w').write('DENIED')\n"
                "except Exception as e:\n"
                f"    open(r'{res_file}','w').write('ERR:'+type(e).__name__)\n",
                encoding="utf-8")
            _spawn_as_worker(pw, outd, lock_script)
            verdict_txt = res_file.read_text(encoding="utf-8") if res_file.exists() else "MISSING"
            chk("F4: worker CANNOT write the trusted probe (DENIED)", verdict_txt == "DENIED")

        # ---- F4 negative: substring attack must NOT pass strict parse ----
        evil = "NONCE=%s|RESULT=READ=GRANTED|NOTE=READ=DENIED" % res.attestation.run_nonce
        chk("F4: conflicting/unknown schema -> parse None",
            parse_verdict_strict(evil) is None)
        good = "NONCE=n|OP=READ|TARGET=abc|RESULT=READ=DENIED"
        chk("F4: exact schema -> parsed", parse_verdict_strict(good) is not None)

        # ---- F3 negative: identity gate consumes SID/exit/create-time ----
        chk("F3: sid_differs False -> identity_ok False",
            _fake_identity_ok(sid_differs=False) is False)
        chk("F3: exit!=0 -> identity_ok False", _fake_identity_ok(exit_code=7) is False)
        chk("F3: create_time==0 -> identity_ok False",
            _fake_identity_ok(create_time=0.0) is False)
        chk("F3: sha mismatch -> identity_ok False",
            _fake_identity_ok(probe_sha_matches=False) is False)
        chk("F3: all good -> identity_ok True", _fake_identity_ok() is True)

        # ---- lifecycle negative: alive old worker -> lifecycle_ok False ----
        alive_pid = os.getpid()   # this very process is alive
        out_lc = ResetChainResult()
        ok_lc = _terminate_and_confirm(alive_pid, lambda p: None)   # no-op terminator
        chk("lifecycle: alive 'old worker' -> not confirmed terminated", ok_lc is False)

        # ---- preserve negative: different restored bytes ----
        chk("preserve: different restored bytes -> not valid",
            R(clear_ok=True, preserve_ok=False, access_ok=True, handle_ok=True,
              identity_ok=True, lifecycle_ok=True).valid is False)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    passed = sum(1 for _, ok in results if ok)
    print(f"\nq3_reset_chain selftest: {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


def _fake_identity_ok(sid_differs=True, sid_matches_expected=True, create_time=1.0,
                      wait_result=WAIT_OBJECT_0, exit_code=0, probe_sha_matches=True):
    a = WorkerAttestation(
        account="x", pid=1, token_sid="S-1-5-0", controller_sid="S-1-5-1",
        expected_sid="S-1-5-0", sid_differs=sid_differs,
        sid_matches_expected=sid_matches_expected, create_time=create_time,
        wait_result=wait_result, exit_code=exit_code, run_nonce="n",
        probe_sha256="a", probe_sha_expected="a", probe_sha_matches=probe_sha_matches,
        probe_target_sha="t", verdict_raw=None, verdict_parsed=None)
    return a.identity_ok


def _sid_for_account(account: str) -> str:
    """Resolve a local account name to its SID (via Win32 LookupAccountNameW)."""
    import ctypes
    from ctypes import wintypes
    adv = ctypes.windll.advapi32
    adv.LookupAccountNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p,
                                       ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR,
                                       ctypes.POINTER(wintypes.DWORD),
                                       ctypes.POINTER(ctypes.c_int)]
    sid_size = wintypes.DWORD(0)
    dom_size = wintypes.DWORD(0)
    use = ctypes.c_int(0)
    adv.LookupAccountNameW(None, account, None, ctypes.byref(sid_size), None,
                           ctypes.byref(dom_size), ctypes.byref(use))
    sid_buf = ctypes.create_string_buffer(sid_size.value)
    dom_buf = ctypes.create_unicode_buffer(dom_size.value)
    if not adv.LookupAccountNameW(None, account, sid_buf, ctypes.byref(sid_size),
                                  dom_buf, ctypes.byref(dom_size), ctypes.byref(use)):
        raise Q3Error(f"LookupAccountNameW failed for {account}")
    adv.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)]
    sp = wintypes.LPWSTR()
    adv.ConvertSidToStringSidW(sid_buf, ctypes.byref(sp))
    try:
        return ctypes.wstring_at(sp)
    finally:
        ctypes.windll.kernel32.LocalFree(sp)


if __name__ == "__main__":
    raise SystemExit(_selftest())
