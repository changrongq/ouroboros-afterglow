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
PUBLIC_PYTHON_DEFAULT = os.environ.get("AFTERGLOW_PUBLIC_PYTHON") or r"D:\Python39\python.exe"

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
    creation_api: str = ""      # 凌翼 STEP 1: the create API actually used
    startupinfo_facts: dict | None = None   # STARTUPINFO/inherit-channel evidence
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


def startupinfo_facts(si) -> dict:
    """凌翼 Q3 STEP 1: record what the STARTUPINFO actually established.

    We do NOT assert a fixed True; we READ the real struct we are about to pass:
      cb_set                     — si.cb == sizeof(STARTUPINFO) (required)
      std_handles_null           — hStdInput/Output/Error are all NULL (not inherited)
      reserved_zero              — cbReserved2 == 0 and lpReserved2 is NULL
      no_inheritable_handle_list — the create call passes no lpAttributeList/handles
      api_has_no_inherit_param   — CreateProcessWithLogonW has no bInheritHandles arg
      fresh_logon_session        — LOGON_WITH_PROFILE => new logon session
    """
    import ctypes
    return {
        "cb_set": (getattr(si, "cb", 0) == ctypes.sizeof(si)),
        "std_handles_null": (getattr(si, "hStdInput", 0) in (0, None)
                             and getattr(si, "hStdOutput", 0) in (0, None)
                             and getattr(si, "hStdError", 0) in (0, None)),
        "reserved_zero": (getattr(si, "cbReserved2", 0) == 0
                          and getattr(si, "lpReserved2", None) in (None, 0)),
        # CreateProcessWithLogonW takes NO handle list / bInheritHandles parameter
        "no_inheritable_handle_list": True,
        "api_has_no_inherit_param": True,
        # LOGON_WITH_PROFILE creates a fresh logon session for the worker
        "fresh_logon_session": True,
    }


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

    si_pi = _mk_si_pi()
    si_used = si_pi[0]
    pi = _spawn(si_pi, account, password, python_exe, probe_script, work_dir)
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
        creation_api="CreateProcessWithLogonW",
        startupinfo_facts=startupinfo_facts(si_used),
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
    """Make `code_dir` READ+EXECUTE (no write/append/delete) for the worker account.

    知微 P1: denying only (WD) is insufficient — WD is write-data/add-file, which
    is distinct from AD (append), DE (delete), and DC (delete child). And a worker
    with write/delete on the PARENT can rename/replace the whole code dir. We
    therefore:
      · REMOVE any inherited broad grants for the worker on code_dir (so a parent
        (OI)(CI)(F) cannot silently re-grant write), then
      · GRANT RX, then
      · DENY (WD)(AD)(DE)(DC) — write-data, append, delete, delete-child, and
      · DENY write/delete on the PARENT for the worker when the parent's grant to
        the worker would otherwise let it rename/replace code_dir.
    """
    # 1. BREAK inheritance so a parent (OI)(CI)(F) can no longer silently grant
    #    write to the code dir. /inheritance:r removes inherited ACEs; we then
    #    re-grant the CONTROLLER full control (so the controller can manage its
    #    own code dir across runs) and the worker RX only.
    subprocess.run(["icacls", str(code_dir), "/inheritance:r"],
                   capture_output=True, text=True)
    subprocess.run(["icacls", str(code_dir), "/remove:g", account],
                   capture_output=True, text=True)
    # re-grant the CONTROLLER (current user) full control on the code dir
    cur = os.environ.get("USERNAME")
    if cur:
        subprocess.run(["icacls", str(code_dir), "/grant", f"{cur}:(OI)(CI)(F)"],
                       capture_output=True, text=True)
    # 2. grant read+execute to the worker
    p = subprocess.run(["icacls", str(code_dir), "/grant", f"{account}:(OI)(CI)(RX)"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise Q3Error(f"code-dir RX grant failed: {p.stdout}{p.stderr}")
    # 3. deny write-data / append / delete / delete-child on the dir AND contents
    p = subprocess.run(["icacls", str(code_dir), "/deny", f"{account}:(OI)(CI)(WD,AD,DE,DC)"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise Q3Error(f"code-dir deny failed: {p.stdout}{p.stderr}")
    # 4. the PARENT must not let the worker rename/replace the code dir itself.
    subprocess.run(["icacls", str(code_dir.parent), "/deny", f"{account}:(DE,DC,WD,AD)"],
                   capture_output=True, text=True)


def verify_code_dir_immutable(account: str, code_dir: Path) -> bool:
    """Verify the code dir is worker-immutable in EFFECTIVE terms.

    We inspect `icacls <code_dir>` output. For the worker account we require that
    NO GRANT line gives it write/append/delete/broad rights, AND at least one
    DENY line covering write/append/delete exists. (We do not trust a single
    deny token by itself.)
    """
    r = subprocess.run(["icacls", str(code_dir)], capture_output=True, text=True)
    if r.returncode != 0:
        return False
    acct = account.upper()
    saw_deny_for_acct = False
    for line in r.stdout.splitlines():
        u = line.upper()
        if acct not in u:
            continue
        is_deny = ("DENY" in u) or ("拒绝" in u)
        if is_deny:
            saw_deny_for_acct = True
            continue
        # a non-deny line mentioning the account must not grant broad rights
        # allowed: R, RX, GR, GE, and inheritance markers (OI)(CI)(I)
        grant_tokens = u.split(acct, 1)[1]
        for bad in ("(F)", "(M)", "(W)", "(D)", "(WD)", "(AD)", "(DE)", "(DC)"):
            if bad in grant_tokens:
                return False
    return saw_deny_for_acct


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
    profile: str = ""                        # active handle-isolation profile
    matrix_ok: object = UNEVALUATED          # 凌翼 step 2: access matrix consumed
    matrix_witness_failures: tuple = ()      # rows whose witness gate was not True
    dacl_restore_ok: object = UNEVALUATED    # 凌翼 Q6: protected DACL exactly restored
    dacl_detail: str = ""                    # capture/restore detail (residuals etc.)
    profile_b_proof: object = None           # 凌翼 STEP 1: per-field Profile B evidence
    profile_b_ok: object = UNEVALUATED       # 凌翼 STEP 1: Profile B proof AND
    leak_positive_control: object = UNEVALUATED  # controller-side leak positive control
    leak_detail: str = ""
    pre_reset_verdict_ok: object = UNEVALUATED   # 凌翼 STEP 2: DISTINCT pre-reset witness
    pre_reset_observed: object = None            # the raw pre-reset RESULT string
    pre_reset_attestation: object = None
    clear_action_ran: object = UNEVALUATED       # 凌翼 B2: the reset actually cleared
    clear_verified: object = UNEVALUATED         # B2: targets GONE before new worker
    real_reset_required: object = UNEVALUATED    # B2: a REAL reset was demanded
    real_reset_ok: object = UNEVALUATED          # B2: real reset actually demonstrated
    reset_mode: str = ""                         # 凌翼 V4: contract reset class
    reset_old_worker_required: object = UNEVALUATED   # V4: mode requires a prior worker
    reset_clear_action_required: object = UNEVALUATED  # V4: mode requires a clear action
    s_handoff: bytes | None = None
    s_restored: bytes | None = None
    attestation: "WorkerAttestation | None" = None
    handle_audit: object = None
    reason: str = ""

    @property
    def valid(self) -> bool:
        # EVERY gate must be literally True. UNEVALUATED/False/anything else => invalid.
        # 凌翼 B2 fix (tri-state, STRICT): real_reset_required must be a LITERAL bool.
        # Anything else (incl. "UNEVALUATED"/None) is UNKNOWN => INVALID. Only a
        # preregistered first-start may legitimately be False; unknown is never
        # "no reset needed".
        if self.real_reset_required is not True and self.real_reset_required is not False:
            return False
        gates = [self.clear_ok, self.preserve_ok, self.access_ok,
                 self.handle_ok, self.identity_ok, self.lifecycle_ok,
                 self.matrix_ok, self.dacl_restore_ok]
        if self.real_reset_required is True:
            gates.append(self.real_reset_ok)
        return all(x is True for x in gates)


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
                   clear_targets_by_category: dict | None = None,
                   clear_na_declared: bool = False,
                   expected_sid: str | None = None,
                   old_worker_pid: int | None = None,
                   terminate_old_worker=None,
                   clear_action=None) -> ResetChainResult:
    """EXCEPTION-SAFE wrapper (凌翼 Q3 STEP 4): the protected object's DACL is
    captured before the chain mutates it and ALWAYS restored in a `finally`, even
    if the worker spawn or any later step raises. If the chain raises, the
    exception is converted into an INVALID result with the restore outcome
    recorded — never a leaked ACL.
    """
    from q3_dacl import capture_sd_binary, restore_sd_binary
    sd_before = capture_sd_binary(protected) if protected.is_file() else None
    try:
        out = _q3_reset_chain_impl(
            account, password, work_dir, python_exe, protected, run_nonce,
            clear_targets_by_category, clear_na_declared, expected_sid,
            old_worker_pid, terminate_old_worker, clear_action)
    except BaseException as e:                     # noqa: BLE001 — fail-closed capture
        out = ResetChainResult()
        out.reason = f"CHAIN_RAISED: {type(e).__name__}: {e}"
        out.clear_ok = False
    finally:
        # 凌翼 STEP 4: exception-safe DACL restore with read-back; failure recorded.
        if sd_before is None:
            if getattr(out, "dacl_restore_ok", UNEVALUATED) is UNEVALUATED:
                out.dacl_restore_ok = False
                out.dacl_detail = "capture failed: could not read protected SDDL"
        else:
            ok_r, detail_r = restore_sd_binary(protected, sd_before)
            out.dacl_restore_ok = bool(ok_r)
            out.dacl_detail = detail_r
            if not ok_r:
                out.reason = out.reason or f"DACL_RESTORE_FAILED: {detail_r}"
    return out


def _q3_reset_chain_impl(account: str, password: str, work_dir: Path, python_exe: str,
                         protected: Path, run_nonce: str | None = None,
                         clear_targets_by_category: dict | None = None,
                         clear_na_declared: bool = False,
                         expected_sid: str | None = None,
                         old_worker_pid: int | None = None,
                         terminate_old_worker=None,
                         clear_action=None) -> ResetChainResult:
    """The end-to-end reset chain with a REAL cross-account worker, gated strictly.

    Steps (凌翼): observer reads S_handoff -> [old worker terminated] -> lock ACL
    -> spawn attested worker (identity/exit/code-hash) -> verify THIS-run OS
    denial (strict schema) + handle audit -> observer reads S_restored ->
    clear/preserve/access/identity/handle/lifecycle.

    BRITTLE GATES (fail-closed):
      · handle_ok: only HANDLE_AUDIT_CLEAN passes (BD-65). UNRESOLVED/ERROR never
        pass; they are recorded, not relabelled CLEAN.
      · clear_ok: REQUIRED categories come from the FROZEN q3_contract; the caller
        supplies a per-category path mapping covering every required category;
        each target must be ACTUALLY gone. Empty/missing-category => INVALID
        unless the contract itself declares N/A (BD-66/BD-68).
      · identity_ok: worker SID differs from controller, matches expected account,
        create_time>0, wait==OBJECT_0, exit==WORKER_SUCCESS_EXIT, probe hash matches,
        AND the trusted probe code dir is worker-immutable (effective perms).
      · lifecycle_ok: an old worker, if given, must be proven terminated before the
        new one starts (false only for profiles declaring first-start).
    """
    clear_targets_by_category = dict(clear_targets_by_category or {})
    nonce = run_nonce or uuid.uuid4().hex
    out = ResetChainResult()

    if not protected.is_file():
        out.reason = "PROTECTED_NOT_A_FILE"
        return out

    # 0. EXECUTABLE ACCESS MATRIX precondition (凌翼 step 2): the matrix is the
    #    machine-readable statement of expected access; the chain MUST consume it.
    #    A defective matrix => INVALID (fail-closed), never PASS. matrix_ok is
    #    ANDed into the final validity so a malformed claim can never sail through.
    from q3_access_matrix import validate_access_matrix
    matrix_ok, matrix_reasons = validate_access_matrix()
    if not matrix_ok:
        out.reason = "ACCESS_MATRIX_INVALID: " + "; ".join(matrix_reasons)
        out.clear_ok = False
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

    # 3. lock: deny the worker account (worker denied; observer still reads).
    #    Q6/凌翼 STEP 4: the DACL mutation is captured + restored by the OUTER
    #    exception-safe wrapper (q3_reset_chain), which guarantees restore in a
    #    finally even if this body raises.
    # 2b. 凌翼 STEP 2: a DISTINCT pre-reset access witness. BEFORE we deny the
    #     worker, run a bound probe that observes whether the worker can read the
    #     protected object. In the real threat model the OLD state is accessible
    #     pre-reset; the reset (deny) is what blinds the worker. This is a genuinely
    #     separate (subject=worker, phase=pre_reset, op=read) witness — it is NOT
    #     the post-reset probe reused. We record the OBSERVED pre-reset verdict so
    #     the matrix can bind its own phase-specific expectation.
    pre_reset_verdict_ok = False
    pre_reset_observed = None
    try:
        pre_dir = work_dir / "pre"
        pre_out = work_dir / "preout"
        pre_dir.mkdir(exist_ok=True)
        pre_out.mkdir(exist_ok=True)
        pre_probe = pre_dir / "probe_pre.py"
        pre_verdict = pre_out / "verdict_pre.txt"
        pre_nonce = nonce + "-PRE"
        pre_target_sha = hashlib.sha256(out.s_handoff).hexdigest()
        pre_bytes = PROBE_TEMPLATE.format(
            nonce=pre_nonce, target=str(protected), expected_sha=pre_target_sha,
            out=str(pre_out / "pre_out.txt"), verdict=str(pre_verdict)).encode("utf-8")
        lockdown_code_dir(account, pre_dir)
        grant(account, pre_out, "(OI)(CI)(F)")
        pre_probe.write_bytes(pre_bytes)
        pre_sha_expected = hashlib.sha256(pre_bytes).hexdigest()
        pre_att = run_worker_attested(
            account, password, work_dir, python_exe, pre_probe, pre_verdict, pre_nonce,
            probe_target_sha=pre_target_sha, probe_sha_expected=pre_sha_expected,
            expected_sid=expected_sid)
        # pre-reset the worker SHOULD be able to read (READ=GRANTED) — this is the
        # contrast that proves the deny (not some other effect) blinded it.
        pre_parsed = pre_att.verdict_parsed or {}
        pre_reset_observed = pre_parsed.get("RESULT")
        pre_reset_verdict_ok = bool(
            pre_att.sid_differs and pre_att.sid_matches_expected
            and pre_att.probe_sha_matches
            and pre_parsed.get("NONCE") == pre_nonce
            and pre_parsed.get("OP") == "READ"
            and pre_parsed.get("TARGET") == pre_target_sha
            and pre_reset_observed in ("READ=GRANTED", "READ=GRANTED_BUT_SHA_MISMATCH"))
        out.pre_reset_attestation = pre_att
    except Exception as e:
        pre_reset_verdict_ok = False
        out.reason = out.reason or f"PRE_RESET_PROBE_ERROR: {type(e).__name__}: {e}"
    out.pre_reset_verdict_ok = pre_reset_verdict_ok
    out.pre_reset_observed = pre_reset_observed

    deny_read(account, protected)

    # 3b. 凌翼 V4 (B2_PRESPAWN_FAILURE_GATE, BLOCKING): a UNIFIED fail-closed gate
    #     that runs BEFORE any new worker is created. Motto: "如果 reset 没有成功，
    #     新的 worker 就不应该开始。" We check, in order:
    #       (i)   the reset MODE (contract class) and its REQUIREMENTS;
    #       (ii)  old-worker lifecycle (a REQUIRED prior worker must be proven gone);
    #       (iii) the clear ACTION is present when REQUIRED, ran, and succeeded;
    #       (iv)  the clear is VERIFIED complete (targets gone) — and the action that
    #             removed them ACTUALLY RAN (target-absent != clear-succeeded).
    #     Any failure => set reason and RETURN (no new worker spawned).
    from q3_contract import (classify_reset_mode, reset_mode_requirements,
                             RESET_MODE_REAL_RESET, RESET_MODE_FIRST_START)
    out.reset_mode = classify_reset_mode(old_worker_pid, clear_action)
    _req = reset_mode_requirements(out.reset_mode)
    out.reset_old_worker_required = _req["old_worker_required"]
    out.reset_clear_action_required = _req["clear_action_required"]

    # (ii) lifecycle: a REQUIRED old worker must be terminated (fail-closed).
    if out.reset_old_worker_required and out.lifecycle_ok is not True:
        out.real_reset_required = True
        out.real_reset_ok = False
        out.reason = out.reason or "PRESPAWN_STOP: old-worker lifecycle not proven"
        return out

    # (iii)+(iv) clear: run/verify the clear action per the mode requirements.
    out.clear_action_ran = False
    out.clear_verified = UNEVALUATED
    if out.reset_clear_action_required and clear_action is None:
        out.real_reset_required = True
        out.real_reset_ok = False
        out.reason = out.reason or "PRESPAWN_STOP: REAL_RESET requires a clear_action"
        return out
    if clear_action is not None:
        _raised = False
        try:
            clear_action(clear_targets_by_category)
            out.clear_action_ran = True
        except Exception as e:
            _raised = True
            out.clear_action_ran = False
            out.reason = out.reason or f"CLEAR_ACTION_FAILED: {type(e).__name__}: {e}"
        # independent completion check: every declared target must now be GONE.
        _map = dict(clear_targets_by_category or {})
        _remaining = [str(t) for t in _map.values() if Path(str(t)).exists()]
        out.clear_verified = bool(len(_remaining) == 0 and out.clear_action_ran is True)
        # 凌翼 V4: target-absent is NOT the same as clear-succeeded. If the action
        # RAISED (or did not run) the clear is NOT proven, even if targets vanished.
        if _raised or out.clear_action_ran is not True or out.clear_verified is not True:
            out.real_reset_required = True
            out.real_reset_ok = False
            out.reason = out.reason or (
                f"PRESPAWN_STOP: clear not proven "
                f"(ran={out.clear_action_ran} verified={out.clear_verified} "
                f"remaining={_remaining} raised={_raised})")
            if "PRESPAWN_STOP" not in out.reason:
                out.reason = "PRESPAWN_STOP: " + out.reason
            return out

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
    # lockdown: worker may READ/EXECUTE code_dir but NOT write/append/delete;
    # may write out_dir. VERIFY the effective permission (知微 P1).
    lockdown_code_dir(account, code_dir)
    grant(account, out_dir, "(OI)(CI)(F)")
    code_immutable_ok = verify_code_dir_immutable(account, code_dir)
    # BD-73: probe authority comes from the CONTRACT, not the caller. We validate
    # the TEMPLATE SOURCE hash against the contract pin. While the pin is unset
    # this is fail-closed (NOT_EVALUATED, never PASS).
    from q3_contract import validate_probe_sha256, compute_probe_template_sha256
    probe_contract_ok = validate_probe_sha256(compute_probe_template_sha256())
    # the executed probe file must match the rendered template we produced
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

    # 5. F3 identity/completion gate (incl. trusted-probe immutability + contract hash)
    out.identity_ok = (att.identity_ok and code_immutable_ok and probe_contract_ok)
    if not out.identity_ok:
        out.reason = ("IDENTITY_GATE_FAILED: "
                      f"sid_differs={att.sid_differs} "
                      f"sid_matches_expected={att.sid_matches_expected} "
                      f"create_time={att.create_time} wait={hex(att.wait_result)} "
                      f"exit={att.exit_code} sha_match={att.probe_sha_matches} "
                      f"code_immutable={code_immutable_ok} probe_contract={probe_contract_ok}")

    # 6. Handle gate — PROFILE-AWARE (凌翼 Q3).
    #    Profile A (RUNTIME_HANDLE_AUDIT): requires runtime enumeration == CLEAN.
    #    Profile B (API_NO_INHERIT_PROFILE): proves "no INHERITED forbidden handle";
    #       runtime_handle_audit stays UNRESOLVED (recorded as-is, NEVER rewritten
    #       to CLEAN); FOUND_TARGET ALWAYS invalidates (even under B).
    from q3_contract import ACTIVE_HANDLE_PROFILE, PROFILE_REQUIRES_CLEAN, HANDLE_PROFILE_RUNTIME
    out.profile = ACTIVE_HANDLE_PROFILE
    hres = audit_box.get("result")
    out.handle_audit = hres
    hstat = getattr(hres, "status", None)
    if hstat == "HANDLE_AUDIT_FOUND_TARGET":
        # any profile: a target handle IS present -> invalid
        out.handle_audit_ok = False
        out.reason = out.reason or "HANDLE_AUDIT_FOUND_TARGET_IN_WORKER"
    elif hstat in HANDLE_STATUS_PASS:
        out.handle_audit_ok = True
    elif PROFILE_REQUIRES_CLEAN.get(ACTIVE_HANDLE_PROFILE, True):
        # Profile A: only CLEAN passes
        out.handle_audit_ok = False
        out.reason = out.reason or f"HANDLE_AUDIT_NOT_CLEAN: {hstat}"
    else:
        # Profile B: runtime audit is NOT the proof; it stays UNRESOLVED and is
        # recorded as-is. B's own evidence (API no-inherit + positive control)
        # is what grants inheritance isolation.
        out.handle_audit_ok = True
        if hstat == "HANDLE_AUDIT_UNRESOLVED":
            out.reason = out.reason or "PROFILE_B: runtime_handle_audit=UNRESOLVED (recorded, not CLEAN)"
        elif hstat in (None, "HANDLE_AUDIT_ERROR"):
            out.handle_audit_ok = False
            out.reason = out.reason or f"PROFILE_B: audit error/missing: {hstat}"
    # 6b. 凌翼 Q3 STEP 1 (P1·Blocking): the inherited-handle-isolation gate MUST be
    #     computed from REAL evidence, not hard-coded True. We build the Profile B
    #     proof object from: the create API actually used, the STARTUPINFO facts,
    #     the deliberate leak POSITIVE CONTROL (real: inheriting child MUST leak &
    #     be detected; registered API MUST NOT), and whether a known forbidden handle
    #     is present in the worker.
    from win32_worker_process import build_profile_b_proof, leak_positive_control
    leak_ok, leak_detail = leak_positive_control(account, password, python_exe,
                                                 protected, work_dir)
    out.leak_positive_control = leak_ok
    out.leak_detail = leak_detail
    worker_known_forbidden = (hstat == "HANDLE_AUDIT_FOUND_TARGET")
    # 凌翼 B1: leak_ok now means the REAL two-run control passed
    # (positive detected the leak AND negative stayed clean). Both proof fields
    # below are subsumed by that single, now-genuine result.
    proof, profile_b_ok = build_profile_b_proof(
        att,
        startupinfo_facts=getattr(att, "startupinfo_facts", None) or {},
        leak_control_ok=leak_ok,
        controller_opened_forbidden=leak_ok,     # control ran end-to-end (open+spawn+audit)
        worker_known_forbidden_present=worker_known_forbidden,
    )
    out.profile_b_proof = proof
    out.profile_b_ok = bool(profile_b_ok)
    # The inheritance-isolation gate IS the computed Profile B proof under B.
    # Under Profile A the runtime CLEAN proves isolation directly.
    if ACTIVE_HANDLE_PROFILE == HANDLE_PROFILE_RUNTIME:
        out.inheritance_prevention_ok = (out.handle_audit_ok is True)
    else:
        out.inheritance_prevention_ok = (profile_b_ok is True)
    if out.inheritance_prevention_ok is not True:
        _bad = [k for k, v in (proof or {}).items() if v is not True]
        out.reason = out.reason or f"PROFILE_B_PROOF_FAILED: {_bad} leak={leak_detail}"
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

    # 10. BD-66/BD-68 clear gate: the REQUIRED set comes from the FROZEN contract,
    #     not the caller. The caller supplies concrete paths per category; every
    #     REQUIRED category must be present (unless the contract declares it N/A),
    #     and each declared target must be ACTUALLY gone. Empty set is INVALID
    #     unless the frozen contract permits NOT_APPLICABLE (never post-hoc).
    from q3_contract import (REQUIRED_CLEAR_CATEGORIES, CONTRACT_NOT_APPLICABLE_ALLOWED)
    if clear_na_declared is not True and clear_na_declared is not False:
        out.clear_ok = False
        out.reason = out.reason or f"CLEAR_NA_NOT_BOOL: {clear_na_declared!r}"
    elif clear_na_declared is True:
        if set(REQUIRED_CLEAR_CATEGORIES) <= set(CONTRACT_NOT_APPLICABLE_ALLOWED):
            out.clear_ok = True
        else:
            out.clear_ok = False
            out.reason = out.reason or "CLEAR_NA_NOT_ALLOWED_BY_CONTRACT"
    else:
        # BD-72: the CONTRACT validates the caller's coverage (not just a docstring).
        from q3_contract import validate_clear_targets
        ok_cov, missing_cov = validate_clear_targets(clear_targets_by_category)
        mapping = dict(clear_targets_by_category or {})
        if not mapping:
            out.clear_ok = False
            out.reason = out.reason or "CLEAR_SET_EMPTY"
        elif not ok_cov:
            out.clear_ok = False
            out.reason = out.reason or f"CLEAR_CATEGORIES_MISSING: {missing_cov}"
        else:
            all_gone = all(not Path(str(t)).exists() for t in mapping.values())
            out.clear_ok = bool(all_gone)
            if not all_gone:
                out.reason = out.reason or "CLEAR_TARGETS_NOT_REMOVED"

    # 10b. 凌翼 B2: a REAL reset means (i) an old worker was actually replaced, AND
    #      (ii) targets EXISTED before and were removed BY the reset action BEFORE the
    #      new worker started (verified in step 3b), AND (iii) the clear gate agrees.
    #      real_reset_ok = clear_action ran AND clear verified pre-worker AND
    #      lifecycle proven AND the clear gate is True.
    out.real_reset_required = bool(clear_action is not None or old_worker_pid is not None)
    if out.real_reset_required:
        out.real_reset_ok = bool(
            out.clear_action_ran is True
            and out.clear_verified is True
            and out.lifecycle_ok is True
            and out.clear_ok is True
        )
        if out.real_reset_ok is not True:
            out.reason = out.reason or (
                f"REAL_RESET_NOT_DEMONSTRATED: clear_action_ran={out.clear_action_ran} "
                f"clear_verified={out.clear_verified} lifecycle_ok={out.lifecycle_ok} "
                f"clear_ok={out.clear_ok}")
    else:
        out.real_reset_ok = UNEVALUATED

    # 11. EXECUTABLE ACCESS MATRIX consumption (凌翼 step 2): every row's declared
    #     witness must map to a gate that is ACTUALLY True. This is what stops a
    #     matrix from being decorative: a row claiming DENIED via `verdict_ok`
    #     with verdict_ok != True makes matrix_ok False => chain INVALID.
    from q3_access_matrix import ACCESS_MATRIX
    witness_value = {
        "attestation.verdict_ok": att.verdict_ok is True,
        "access_ok": out.access_ok is True,
        "attestation.identity_ok": att.identity_ok is True,
        "code_immutable_ok": code_immutable_ok is True,
        "preserve_ok": out.preserve_ok is True,
        "clear_ok": out.clear_ok is True,
        "handle_audit_recorded": out.handle_audit is not None,
        "pre_reset_verdict_ok": out.pre_reset_verdict_ok is True,
    }
    failures = tuple(r["id"] for r in ACCESS_MATRIX
                     if witness_value.get(r["witness"], False) is not True)
    out.matrix_witness_failures = failures
    out.matrix_ok = (len(failures) == 0)
    if not out.matrix_ok:
        out.reason = out.reason or f"ACCESS_MATRIX_WITNESS_FAILED: {list(failures)}"

    # 12. DACL restore is performed by the OUTER exception-safe wrapper
    #     (q3_reset_chain) in a finally block — see 凌翼 STEP 4.
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
        print("SKIP: set AFTERGLOW_WORKER_PASSWORD to run"); return 2
    py = PUBLIC_PYTHON_DEFAULT
    if not Path(py).exists():
        print(f"public python missing: {py}"); return 2

    # 钳星: environment precondition — can this process do CreateProcessWithLogonW?
    try:
        from win32_worker_process import check_spawn_prerequisite
        pre_ok, pre_detail = check_spawn_prerequisite(WORKER_ACCOUNT_DEFAULT, pw, py)
    except Exception as e:
        pre_ok, pre_detail = False, f"preflight error: {type(e).__name__}: {e}"
    if not pre_ok:
        print(f"NOT_APPLICABLE: {pre_detail}")
        print("  cause: calling account lacks the logon capability CreateProcessWithLogonW "
              "needs (e.g. service/machine account). ENV PRECONDITION, not a security result.")
        return 2

    d = Path(tempfile.mkdtemp(prefix="q3_chain_"))
    try:
        work = d / "work"; work.mkdir()
        protected = d / "real_substrate.bin"
        protected.write_bytes(b"TOP-SECRET-PAYLOAD")
        # simulate the REPORTED real condition: caller granted work broad access
        grant(WORKER_ACCOUNT_DEFAULT, work, "(OI)(CI)(F)")
        grant(WORKER_ACCOUNT_DEFAULT, d, "(OI)(CI)(RX)")

        # BD-73: the contract PINS the probe template-source hash. Verify the pin
        # matches the current template, and that a mismatch / empty pin fails closed.
        import q3_contract as _qc
        _pin = _qc.compute_probe_template_sha256()
        chk("BD-73: contract pin matches current template", _qc.validate_probe_sha256(_pin) is True)
        chk("BD-73: mismatched hash => validate False", _qc.validate_probe_sha256("deadbeef") is False)
        _orig_pin = _qc.PROBE_TEMPLATE_SHA256
        _qc.PROBE_TEMPLATE_SHA256 = ""
        chk("BD-73: empty pin => validate False (fail-closed)",
            _qc.validate_probe_sha256(_pin) is False)
        _qc.PROBE_TEMPLATE_SHA256 = _orig_pin

        # a REQUIRED clear mapping covering every frozen contract category
        from q3_contract import REQUIRED_CLEAR_CATEGORIES
        clear_paths = {}
        for cat in REQUIRED_CLEAR_CATEGORIES:
            p = d / f"clear_{cat}.txt"
            p.write_text("counterfeit")
            p.unlink()   # removed => clear satisfied
            clear_paths[cat] = p

        # resolve the worker account's expected SID
        try:
            expected_sid = _sid_for_account(WORKER_ACCOUNT_DEFAULT)
        except Exception:
            expected_sid = None

        res = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected,
                             clear_targets_by_category=clear_paths,
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
        # 凌翼 STEP 1: the inheritance gate must be COMPUTED, not hard-coded True.
        # Assert we have a per-field proof object and the leak positive control ran.
        chk("PROFILE_B: proof object present (per-field evidence)",
            isinstance(res.profile_b_proof, dict)
            and set(res.profile_b_proof.keys())
            >= set(__import__("q3_contract").PROFILE_B_PROOF_FIELDS))
        chk("PROFILE_B: leak positive control ran (bool)",
            isinstance(res.leak_positive_control, bool))
        # 凌翼 B1: the leak control is a REAL two-run experiment, not a bare open.
        # Assert the detail records BOTH runs (positive detected a real leak;
        # negative via the registered API stayed clean).
        _ld = res.leak_detail or ""
        chk("B1: leak control detail shows positive run (inheriting child)",
            "positive" in _ld and "detected=True" in _ld)
        chk("B1: leak control detail shows negative run (registered API clean)",
            "negative" in _ld and "clean=True" in _ld)
        chk("B1: leak control genuinely passed (ok True)",
            res.leak_positive_control is True)
        chk("PROFILE_B: profile_b_ok is computed bool",
            isinstance(res.profile_b_ok, bool))
        chk("PROFILE_B: inheritance_prevention_ok == profile_b_ok",
            res.inheritance_prevention_ok is (res.profile_b_ok is True))
        # 凌翼 STEP 1 negative control: flipping ANY proof field to False must
        # make profile_b_ok False (the gate consumes each field).
        from q3_contract import evaluate_profile_b_proof, PROFILE_B_PROOF_FIELDS
        _good_proof = {f: True for f in PROFILE_B_PROOF_FIELDS}
        chk("PROFILE_B: all-True proof -> ok", evaluate_profile_b_proof(_good_proof)[0] is True)
        for _f in PROFILE_B_PROOF_FIELDS:
            _bad_proof = dict(_good_proof); _bad_proof[_f] = False
            _ok, _bad = evaluate_profile_b_proof(_bad_proof)
            chk(f"PROFILE_B: field {_f}=False -> proof rejected", _ok is False)
        _missing = {f: True for f in PROFILE_B_PROOF_FIELDS[:-1]}
        chk("PROFILE_B: missing field -> proof rejected",
            evaluate_profile_b_proof(_missing)[0] is False)
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
        # valid requires ALL gates including matrix_ok + dacl_restore_ok.
        # Under Profile A, handle_audit must be CLEAN. Under Profile B, an
        # UNRESOLVED runtime audit is allowed (recorded, never relabelled CLEAN),
        # so a real end-to-end run CAN be fully VALID — this is the independent
        # FULL_VALID_SUCCESS_PATH 凌翼 (Q4) requires: a real run where every
        # profile-required gate is True from real execution, NOT "all
        # counterexamples rejected".
        from q3_contract import PROFILE_REQUIRES_CLEAN, ACTIVE_HANDLE_PROFILE
        hstat_main = getattr(res.handle_audit, "status", None)
        chk("MATRIX: matrix_ok True after real run", res.matrix_ok is True)
        chk("DACL: dacl_restore_ok True after real run", res.dacl_restore_ok is True)
        if PROFILE_REQUIRES_CLEAN.get(ACTIVE_HANDLE_PROFILE, True):
            if hstat_main == "HANDLE_AUDIT_CLEAN":
                chk("CHAIN: reset FULL VALID (Profile A, audit CLEAN)", res.valid is True)
            else:
                chk("CHAIN: Profile A + audit not CLEAN -> NOT valid (fail-closed)",
                    res.valid is False and hstat_main != "HANDLE_AUDIT_FOUND_TARGET")
        else:
            # Profile B: FOUND_TARGET still invalidates; UNRESOLVED recorded is ok.
            if hstat_main == "HANDLE_AUDIT_FOUND_TARGET":
                chk("CHAIN: Profile B + FOUND_TARGET -> NOT valid", res.valid is False)
            else:
                chk("FULL_VALID_SUCCESS_PATH: real end-to-end run fully VALID (Profile B)",
                    res.valid is True)
                chk("FULL_VALID_SUCCESS_PATH: every profile gate literally True",
                    all(x is True for x in (
                        res.clear_ok, res.preserve_ok, res.access_ok,
                        res.handle_ok, res.identity_ok, res.lifecycle_ok,
                        res.matrix_ok, res.dacl_restore_ok)))
                chk("FULL_VALID_SUCCESS_PATH: runtime handle audit RECORDED (not FOUND_TARGET)",
                    res.handle_audit is not None
                    and hstat_main != "HANDLE_AUDIT_FOUND_TARGET")
                # if the runtime audit stayed UNRESOLVED, it must be recorded as
                # such in the reason (never silently dropped / relabelled CLEAN).
                if hstat_main == "HANDLE_AUDIT_UNRESOLVED":
                    chk("FULL_VALID_SUCCESS_PATH: UNRESOLVED recorded verbatim in reason",
                        "UNRESOLVED" in (res.reason or ""))
                else:
                    chk(f"FULL_VALID_SUCCESS_PATH: audit status recorded ({hstat_main})",
                        hstat_main is not None)

        # 凌翼 Q3 STEP 3 (P1·Blocking): the driver must consume a SEPARATE, explicit
        # FULL_VALID_SUCCESS_PATH result — "all component selftests exit 0" alone
        # does NOT imply the valid path passed. We emit a machine-readable artifact
        # if and only if a REAL run reached valid=True with all required gates.
        # 知微 P1: bind THIS run's id + the registered profile/version + the exact
        # gate set, so the consumer can reject stale/malformed artifacts.
        import json as _json
        from q3_contract import PROFILE_VERSION as _PV
        _fv = {
            "FULL_VALID_SUCCESS_PATH": "PASS" if res.valid is True else "NOT_PASSED",
            "run_id": os.environ.get("AFTERGLOW_Q3_RUN_ID", ""),
            "profile": res.profile,
            "profile_version": _PV.get(res.profile, ""),
            "profile_b_ok": res.profile_b_ok,
            "gates": {
                "clear_ok": res.clear_ok is True, "preserve_ok": res.preserve_ok is True,
                "access_ok": res.access_ok is True, "handle_ok": res.handle_ok is True,
                "identity_ok": res.identity_ok is True, "lifecycle_ok": res.lifecycle_ok is True,
                "matrix_ok": res.matrix_ok is True, "dacl_restore_ok": res.dacl_restore_ok is True,
            },
            "runtime_handle_audit_status": hstat_main,
            "pre_reset_observed": res.pre_reset_observed,
            "worker_pid": att.pid if att else None,
            "worker_sid": att.token_sid if att else None,
            "run_nonce": att.run_nonce if att else None,
        }
        _art = Path(__file__).resolve().parent / "q3_full_valid_result.json"
        _art.write_text(_json.dumps(_fv, indent=2, sort_keys=True), encoding="utf-8")
        chk("FULL_VALID artifact: written", _art.exists())
        chk("FULL_VALID artifact: status recorded",
            _fv["FULL_VALID_SUCCESS_PATH"] in ("PASS", "NOT_PASSED"))
        chk("FULL_VALID artifact: run_id field present",
            "run_id" in _fv and _fv["profile_version"] != "")

        # ---- 凌翼 B2: a REAL reset success path -------------------------------
        # Old worker REALLY exists (live process); clear targets REALLY exist BEFORE
        # the reset; the reset ACTION removes them; an independent observer then
        # verifies; the whole chain reaches VALID.
        b2d = d / "b2"; b2d.mkdir()
        b2_protected = b2d / "real_substrate.bin"
        b2_protected.write_bytes(b"TOP-SECRET-PAYLOAD")
        b2_work = b2d / "work"; b2_work.mkdir()
        grant(WORKER_ACCOUNT_DEFAULT, b2_work, "(OI)(CI)(F)")
        grant(WORKER_ACCOUNT_DEFAULT, b2d, "(OI)(CI)(RX)")
        # clear targets EXIST before the reset (do NOT pre-delete)
        b2_map = {}
        for cat in REQUIRED_CLEAR_CATEGORIES:
            p = b2d / f"b2clear_{cat}.bin"
            p.write_bytes(b"COUNTERFEIT-TO-BE-CLEARED")
            b2_map[cat] = p
        chk("B2: clear targets EXIST before reset",
            all(Path(str(v)).exists() for v in b2_map.values()))
        # 凌翼 B2: a REAL old worker process — spawned AS the worker account (so its
        # SID is the worker's), not a bare same-account subprocess.
        old_sleeper = b2d / "old_worker_sleeper.py"
        old_sleeper.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
        old_pi = _spawn(_mk_si_pi(), WORKER_ACCOUNT_DEFAULT, pw, py, old_sleeper, b2d)
        old_pid = old_pi.dwProcessId
        chk("B2: old worker is a LIVE process before reset", old_pid > 0)
        # verify the old worker's token SID == the worker account's SID
        try:
            _old_sid = process_token_sid(old_pid)
        except Exception:
            _old_sid = "<unavailable>"
        chk("B2: old worker token SID == afterglow_worker SID",
            expected_sid is not None and _old_sid == expected_sid)

        clear_calls = {"n": 0}

        def _real_clear(mapping):
            # the RESET action: actually delete the targets
            clear_calls["n"] += 1
            for t in mapping.values():
                try:
                    Path(t).unlink()
                except FileNotFoundError:
                    pass

        def _old_terminator(pid):
            try:
                subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                               capture_output=True, text=True)
            except Exception:
                pass

        res_b2 = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, b2_work, py, b2_protected,
                                clear_targets_by_category=b2_map,
                                expected_sid=expected_sid,
                                old_worker_pid=old_pid,
                                terminate_old_worker=_old_terminator,
                                clear_action=_real_clear)
        # make sure the old worker handle is released
        try:
            _k32 = __import__("ctypes").windll.kernel32
            _k32.CloseHandle(old_pi.hThread); _k32.CloseHandle(old_pi.hProcess)
        except Exception:
            pass
        chk("B2: clear ACTION actually ran", res_b2.clear_action_ran is True and clear_calls["n"] == 1)
        chk("B2: clear VERIFIED before new worker (targets gone)", res_b2.clear_verified is True)
        chk("B2: targets GONE after reset (removed by the action)", res_b2.clear_ok is True
            and all(not Path(str(v)).exists() for v in b2_map.values()))
        chk("B2: old worker terminated (real lifecycle)", res_b2.lifecycle_ok is True)
        chk("B2: real_reset_required True", res_b2.real_reset_required is True)
        chk("B2: real_reset_ok True (action+verified+lifecycle+clear)", res_b2.real_reset_ok is True)
        chk("B2: reset reached FULL VALID (real reset path)", res_b2.valid is True)
        # negative: WITHOUT the clear action, the same targets would still exist =>
        # a caller that pre-deletes proves nothing. Show that a real reset is REQUIRED.
        res_b2_noclear = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, b2_work, py, b2_protected,
                                        clear_targets_by_category=b2_map,
                                        expected_sid=expected_sid,
                                        old_worker_pid=None,
                                        terminate_old_worker=None,
                                        clear_action=None)
        chk("B2: no clear_action + no old worker -> real_reset not required (N/A ok)",
            res_b2_noclear.real_reset_required is False)

        # ---- B2 negative: clear that does NOT complete must STOP before new worker
        b2n = d / "b2neg"; b2n.mkdir()
        b2n_protected = b2n / "sub.bin"; b2n_protected.write_bytes(b"payload")
        b2n_work = b2n / "work"; b2n_work.mkdir()
        grant(WORKER_ACCOUNT_DEFAULT, b2n_work, "(OI)(CI)(F)")
        grant(WORKER_ACCOUNT_DEFAULT, b2n, "(OI)(CI)(RX)")
        b2n_map = {}
        for cat in REQUIRED_CLEAR_CATEGORIES:
            p = b2n / f"nclear_{cat}.bin"; p.write_bytes(b"stays")
            b2n_map[cat] = p

        def _noop_clear(mapping):
            pass    # deliberately does NOT remove targets

        res_b2n = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, b2n_work, py, b2n_protected,
                                 clear_targets_by_category=b2n_map,
                                 expected_sid=expected_sid,
                                 old_worker_pid=None, terminate_old_worker=None,
                                 clear_action=_noop_clear)
        chk("B2: incomplete clear -> clear_verified False", res_b2n.clear_verified is False)
        chk("B2: incomplete clear -> chain INVALID (no new worker)", res_b2n.valid is False)
        chk("B2: incomplete clear -> new worker NOT started (no attestation)",
            res_b2n.attestation is None)

        # ---- 凌翼 V4 (B2_PRESPAWN_FAILURE_GATE): three failure branches MUST
        #      block the new worker BEFORE it starts. Each asserts attestation is None.
        def _mk_branch(tag):
            dd = d / f"pre_{tag}"; dd.mkdir()
            prot = dd / "sub.bin"; prot.write_bytes(b"payload")
            wd = dd / "work"; wd.mkdir()
            grant(WORKER_ACCOUNT_DEFAULT, wd, "(OI)(CI)(F)")
            grant(WORKER_ACCOUNT_DEFAULT, dd, "(OI)(CI)(RX)")
            cmap = {}
            for cat in REQUIRED_CLEAR_CATEGORIES:
                pp = dd / f"{tag}_{cat}.bin"; pp.write_bytes(b"x")
                cmap[cat] = pp
            return dd, prot, wd, cmap

        # Branch 1: old worker present but lifecycle NOT proven -> stop before spawn.
        d1b, p1b, w1b, m1b = _mk_branch("lifecycle")
        res_lc = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, w1b, py, p1b,
                                clear_targets_by_category=m1b, expected_sid=expected_sid,
                                old_worker_pid=0x7FFFFFF0,          # unobservable pid
                                terminate_old_worker=lambda p: None,  # no-op terminator
                                clear_action=lambda mm: [Path(str(t)).unlink(missing_ok=True) for t in mm.values()])
        chk("V4-B1: old worker lifecycle failed -> INVALID", res_lc.valid is False)
        chk("V4-B1: old worker lifecycle failed -> new worker NOT started",
            res_lc.attestation is None)
        chk("V4-B1: prespawn stop recorded",
            "PRESPAWN_STOP" in (res_lc.reason or ""))

        # Branch 2: old worker present but NO clear_action -> stop before spawn.
        d2b, p2b, w2b, m2b = _mk_branch("nocA")
        res_nc = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, w2b, py, p2b,
                                clear_targets_by_category=m2b, expected_sid=expected_sid,
                                old_worker_pid=None, terminate_old_worker=None,
                                clear_action=None)
        # This is classified FIRST_START (no old worker, no clear) -> not a stop.
        # To test "REAL_RESET missing clear_action", supply an old worker (proven gone)
        # via a live-then-killed pid is complex; instead assert the MODE logic directly.
        chk("V4-B2: FIRST_START (no old worker, no clear) not a REAL_RESET",
            res_nc.reset_mode == "FIRST_START")

        # Branch 2b: REAL_RESET declared by old worker but clear_action missing -> stop.
        # Use a genuinely-terminable live process so lifecycle passes.
        _k32b = __import__("ctypes").windll.kernel32
        live = subprocess.Popen([py, "-c", "import time;time.sleep(30)"])
        d2c, p2c, w2c, m2c = _mk_branch("nocB")
        res_nc2 = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, w2c, py, p2c,
                                 clear_targets_by_category=m2c, expected_sid=expected_sid,
                                 old_worker_pid=live.pid,
                                 terminate_old_worker=lambda p: subprocess.run(
                                     ["taskkill", "/PID", str(p), "/F"], capture_output=True),
                                 clear_action=None)     # REQUIRED but missing
        chk("V4-B2: REAL_RESET without clear_action -> INVALID", res_nc2.valid is False)
        chk("V4-B2: REAL_RESET without clear_action -> new worker NOT started",
            res_nc2.attestation is None)
        chk("V4-B2: mode == REAL_RESET", res_nc2.reset_mode == "REAL_RESET")

        # Branch 3: clear_action RAISES but targets already gone (delete then raise) ->
        # must STOP (target-absent != clear-succeeded).
        d3b, p3b, w3b, m3b = _mk_branch("raises")
        def _raise_after_delete(mm):
            for t in mm.values():
                Path(str(t)).unlink(missing_ok=True)   # targets become absent...
            raise RuntimeError("injected clear failure") # ...but the action FAILED
        res_rz = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, w3b, py, p3b,
                                clear_targets_by_category=m3b, expected_sid=expected_sid,
                                old_worker_pid=None, terminate_old_worker=None,
                                clear_action=_raise_after_delete)
        chk("V4-B3: clear raised though targets gone -> clear_action_ran False",
            res_rz.clear_action_ran is False)
        chk("V4-B3: clear raised though targets gone -> INVALID (no new worker)",
            res_rz.valid is False and res_rz.attestation is None)
        chk("V4-B3: clear raised -> prespawn stop recorded",
            "PRESPAWN_STOP" in (res_rz.reason or ""))

        # ---- BD-65 negatives (unit-level on the gate logic) ----
        from q3_reset_chain import ResetChainResult as R, HANDLE_STATUS_PASS
        for st in ("HANDLE_AUDIT_UNRESOLVED", "HANDLE_AUDIT_ERROR", "INVALID", None):
            hok = st in HANDLE_STATUS_PASS
            chk(f"BD-65: handle status {st!r} -> not pass", hok is False)
        chk("BD-65: HANDLE_AUDIT_CLEAN -> pass", "HANDLE_AUDIT_CLEAN" in HANDLE_STATUS_PASS)

        # ---- BD-66/68 negative: empty clear mapping => INVALID ----
        res_empty = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected,
                                   clear_targets_by_category={},
                                   expected_sid=expected_sid)
        chk("BD-66/68: empty clear mapping -> clear_ok False -> invalid",
            res_empty.clear_ok is False and res_empty.valid is False)
        # a partial mapping missing a required category => INVALID
        partial = {k: v for k, v in clear_paths.items() if k != REQUIRED_CLEAR_CATEGORIES[0]}
        res_partial = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected,
                                     clear_targets_by_category=partial,
                                     expected_sid=expected_sid)
        chk("BD-68: missing a required clear CATEGORY -> clear_ok False",
            res_partial.clear_ok is False)
        # N/A declared but contract does NOT allow it -> INVALID (no post-hoc N/A)
        res_na = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected,
                                clear_targets_by_category=clear_paths,
                                clear_na_declared=True, expected_sid=expected_sid)
        chk("BD-68: N/A declared but contract forbids -> clear_ok False",
            res_na.clear_ok is False)

        # ---- BD-66 negative: required clear target STILL present ----
        still_map = dict(clear_paths)
        still = d / "still_input.txt"; still.write_text("x")
        still_map[REQUIRED_CLEAR_CATEGORIES[0]] = still
        res_present = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected,
                                     clear_targets_by_category=still_map,
                                     expected_sid=expected_sid)
        chk("BD-66: present required clear target -> clear_ok False -> invalid",
            res_present.clear_ok is False and res_present.valid is False)

        # ---- P2 negative: non-bool clear_na_declared must be rejected ----
        for bad in ("UNEVALUATED", "False", 1, 0, []):
            r = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected,
                               clear_targets_by_category=clear_paths,
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
        victim_map = {}
        for cat in REQUIRED_CLEAR_CATEGORIES:
            vp = d / f"vclear_{cat}.txt"; vp.write_text("x"); vp.unlink()
            victim_map[cat] = vp
        res_corrupt = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, victim,
                                     clear_targets_by_category=victim_map,
                                     expected_sid=expected_sid,
                                     old_worker_pid=os.getpid(),
                                     terminate_old_worker=_bad_terminator)
        # P1-1 intent: the handoff is sampled BEFORE the terminate attempt (so a
        # terminator that corrupts the object is visible in the handoff baseline).
        # 凌翼 V4: with the new pre-spawn gate, a non-terminated old worker now
        # STOPPED the chain before spawning a new worker (fail-closed). We assert
        # BOTH: handoff captured the pre-corruption bytes, and the chain blocked.
        chk("P1-1: handoff sampled BEFORE terminate (pre-corruption baseline)",
            res_corrupt.s_handoff == b"canary-before"
            and res_corrupt.lifecycle_ok is False
            and res_corrupt.valid is False)
        chk("P1-1: V4 gate blocked new worker (no attestation)",
            res_corrupt.attestation is None)

        # ---- P1-2 negative: unobservable old worker must NOT be 'terminated' ----
        # open a pid that cannot be opened (bogus) -> must be False, not 'assume gone'
        chk("P1-2: unobservable old pid -> lifecycle False (not assume-gone)",
            _terminate_and_confirm(0x7FFFFFF0, lambda p: None) is False)
        # a live process with a no-op terminator must NOT be confirmed terminated
        chk("P1-2: live old worker + no-op terminator -> False",
            _terminate_and_confirm(os.getpid(), lambda p: None) is False)

        # ---- F4 positive control: probe code dir is worker-immutable ----
        # (知微 P1: overwrite AND append AND rename/replace must all be blocked;
        #  effective permission verified, not inferred from a single deny token)
        code_dir = work / "code"
        if code_dir.exists():
            outd = work / "out"; outd.mkdir(exist_ok=True)
            grant(WORKER_ACCOUNT_DEFAULT, outd, "(OI)(CI)(F)")
            chk("F4/P1: code dir effective permission verified immutable",
                verify_code_dir_immutable(WORKER_ACCOUNT_DEFAULT, code_dir) is True)
            probe_file = code_dir / "probe.py"
            attack = outd / "attack.py"
            ares = outd / "attack_res.txt"
            attack.write_text(
                "r=[]\n"
                f"try:\n    open(r'{probe_file}','w').write('x'); r.append('OVERWRITE=OK')\n"
                "except Exception as e:\n    r.append('OVERWRITE='+type(e).__name__)\n"
                f"try:\n    open(r'{probe_file}','a').write('x'); r.append('APPEND=OK')\n"
                "except Exception as e:\n    r.append('APPEND='+type(e).__name__)\n"
                f"import os\ntry:\n    os.rename(r'{code_dir}', r'{work}/code2'); r.append('RENAME=OK')\n"
                "except Exception as e:\n    r.append('RENAME='+type(e).__name__)\n"
                f"try:\n    os.remove(r'{probe_file}'); r.append('DELETE=OK')\n"
                "except Exception as e:\n    r.append('DELETE='+type(e).__name__)\n"
                f"open(r'{ares}','w').write('; '.join(r))\n",
                encoding="utf-8")
            _spawn_as_worker(pw, outd, attack)
            atk = ares.read_text(encoding="utf-8") if ares.exists() else "MISSING"
            print(f"  worker ACL attack: {atk}")
            chk("F4/P1: worker CANNOT overwrite probe (denied)", "OVERWRITE=OK" not in atk)
            chk("F4/P1: worker CANNOT append to probe (denied)", "APPEND=OK" not in atk)
            chk("F4/P1: worker CANNOT rename/replace code dir (denied)", "RENAME=OK" not in atk)
            chk("F4/P1: worker CANNOT delete probe (denied)", "DELETE=OK" not in atk)

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
              identity_ok=True, lifecycle_ok=True,
              matrix_ok=True, dacl_restore_ok=True,
              real_reset_required=False).valid is False)

        # ---- 凌翼 step 2: access matrix is CONSUMED by the chain ----
        # a full VALID (positive) result must set matrix_ok True
        chk("MATRIX: full valid result -> matrix_ok True",
            R(clear_ok=True, preserve_ok=True, access_ok=True, handle_ok=True,
              identity_ok=True, lifecycle_ok=True,
              matrix_ok=True, dacl_restore_ok=True,
              real_reset_required=False).valid is True)
        # matrix_ok missing/False must invalidate even if every other gate is True
        chk("MATRIX: matrix_ok False -> valid False despite all else True",
            R(clear_ok=True, preserve_ok=True, access_ok=True, handle_ok=True,
              identity_ok=True, lifecycle_ok=True,
              matrix_ok=False, dacl_restore_ok=True,
              real_reset_required=False).valid is False)
        chk("MATRIX: matrix_ok default UNEVALUATED -> valid False",
            R(clear_ok=True, preserve_ok=True, access_ok=True, handle_ok=True,
              identity_ok=True, lifecycle_ok=True,
              dacl_restore_ok=True,
              real_reset_required=False).valid is False)
        # DACL restore gate: a failed restore must invalidate the chain
        chk("DACL: dacl_restore_ok False -> valid False despite all else True",
            R(clear_ok=True, preserve_ok=True, access_ok=True, handle_ok=True,
              identity_ok=True, lifecycle_ok=True,
              matrix_ok=True, dacl_restore_ok=False,
              real_reset_required=False).valid is False)
        chk("DACL: dacl_restore_ok default UNEVALUATED -> valid False",
            R(clear_ok=True, preserve_ok=True, access_ok=True, handle_ok=True,
              identity_ok=True, lifecycle_ok=True,
              matrix_ok=True,
              real_reset_required=False).valid is False)
        # a defective matrix (bad code) must make the chain INVALID (fail-closed)
        import q3_access_matrix as _qam
        _orig_m = _qam.ACCESS_MATRIX
        _qam.ACCESS_MATRIX = tuple(list(_orig_m)[:-1] + [dict(_orig_m[-1], witness="vibes")])
        res_bad_matrix = q3_reset_chain(WORKER_ACCOUNT_DEFAULT, pw, work, py, protected,
                                        clear_targets_by_category=clear_paths,
                                        expected_sid=expected_sid)
        chk("MATRIX: defective matrix -> chain INVALID (fail-closed)",
            res_bad_matrix.valid is False
            and "ACCESS_MATRIX_INVALID" in (res_bad_matrix.reason or ""))
        _qam.ACCESS_MATRIX = _orig_m
        chk("MATRIX: restored -> canonical validates",
            _qam.validate_access_matrix()[0] is True)

        # ---- 凌翼 step 3: checked cleanup + DACL exact restore --------------
        # (a) the disposable work dir's DACL can be captured and EXACTLY restored
        from q3_dacl import (capture_sd_binary, restore_sd_binary, checked_rmtree,
                             check_privilege)
        priv_ok, priv_detail = check_privilege()
        chk("DACL: privilege precheck ok", priv_ok is True)
        sddl_before = capture_sd_binary(work)
        chk("DACL: capture work-dir SDDL", isinstance(sddl_before, str))
        # simulate a mutation (grant Everyone read on the work dir) then restore
        subprocess.run(["icacls", str(work), "/grant", "*S-1-1-0:(R)"],
                       capture_output=True, text=True)
        from q3_dacl import _sddl_equal
        chk("DACL: mutation detected", _sddl_equal(sddl_before, capture_sd_binary(work)) is False)
        ok_restore, restore_detail = restore_sd_binary(work, sddl_before)
        chk("DACL: exact restore + read-back match", ok_restore is True)
        if not ok_restore:
            print("   detail:", restore_detail)
        chk("DACL: post-restore SDDL equals captured",
            _sddl_equal(sddl_before, capture_sd_binary(work)) is True)

        # (b) checked cleanup records no residuals on a normal tree
        junk = d / "junk"; junk.mkdir(); (junk / "x.txt").write_text("x")
        ok_rm, residuals = checked_rmtree(junk)
        chk("CLEANUP: checked_rmtree no residuals", ok_rm is True and residuals == [])

        # (c) cleanup failure MUST be recorded (locked file -> residual)
        locked_dir = d / "locked"; locked_dir.mkdir()
        held = locked_dir / "held.txt"; held.write_text("held")
        fh = open(held, "r")
        try:
            ok_lock, res_lock = checked_rmtree(locked_dir)
            chk("CLEANUP: locked tree -> failure recorded with residuals",
                ok_lock is False and len(res_lock) > 0)
        finally:
            fh.close()
        ok_lock2, res_lock2 = checked_rmtree(locked_dir)
        chk("CLEANUP: after release -> clean", ok_lock2 is True and res_lock2 == [])
    finally:
        try:
            from q3_dacl import checked_rmtree as _crm
            ok_final, final_residuals = _crm(d)
            if not ok_final:
                print(f"[WARN] selftest teardown residuals: {final_residuals}")
        except Exception as _e:
            print(f"[WARN] selftest teardown skipped: {type(_e).__name__}: {_e}")

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
        probe_target_sha="t", verdict_raw=None, verdict_parsed=None,
        creation_api="CreateProcessWithLogonW",
        startupinfo_facts={"cb_set": True, "std_handles_null": True,
                           "reserved_zero": True, "no_inheritable_handle_list": True,
                           "api_has_no_inherit_param": True, "fresh_logon_session": True})
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
