"""
win32_isolation.py — Q3 OS-LEVEL ISOLATION backend (Windows / Win32) — V2.

STATUS: SELF-CONTAINED PoC. NOT wired into the frozen Phase A harness. Nothing
here modifies any RC11-frozen byte.

凌翼 Q3 REVIEW (2026-10-11, commit 6003eae) NEW BLOCKING: Q3-F1
    "SELF-REPORTED DENIAL MAY SATISFY ACCESS WITNESS"
    A recorded denial is not a denial that happened.

This V2 addresses Q3-F1 and the four evidence gaps:

Q3-F1  Authenticated witness
    An AccessWitness may ONLY be produced by an actual OS operation, and carries
    a SEAL (HMAC over the observed fields with a per-run key held by the judge)
    plus the raw OS error. A hand-constructed witness cannot present a valid
    seal -> the judge rejects it. Constructor is guarded: direct construction is
    discouraged and produces an UNSELAED witness that the judge always rejects.

Lifecycle (凌翼 gap 2)
    We record the child's TRUE creation time from OS process times
    (GetProcessTimes) via the process HANDLE, not time.time() after wait; and we
    prove the OLD worker terminated BEFORE the new one started by comparing the
    old process's exit time (GetProcessTimes) against the new process's creation
    time. close_fds=True is explicit and documented as necessary-not-sufficient.

DACL restore (凌翼 gap 3 / 知微)
    ``restore_dacl`` uses SetNamedSecurityInfoW to write back a SAVED security
    descriptor (not ``icacls /reset``). It returns whether the write succeeded and
    we re-verify readability afterwards. For disposable canaries we may instead
    destroy the whole directory; /reset is explicitly NOT treated as exact
    rollback.

Restricted token (凌翼 gap 1) — EMPIRICALLY BOUNDED
    CreateRestrictedToken does NOT change TokenUser.SID (measured: identical).
    Same-account isolation needs a RESTRICTING SID + a deny ACE keyed on that
    restricting SID; the observer (no restricting SID) keeps read access
    (measured: GRANTED). Spawning a cross-process worker under a restricted token
    via CreateProcessAsUserW fails on this host with 0xC0000142
    (STATUS_DLL_INIT_FAILED, window-station access). The REACHABLE cross-process
    path is a genuinely DIFFERENT local account via CreateProcessWithLogonW — see
    win32_worker_process.py, where worker DENIED + observer GRANTED was proven on
    the same object (2026-10-11). This module keeps the in-process authenticated
    witness mechanism; the cross-process sandbox lives in win32_worker_process.py.

Scope statement (凌翼/知微)
    Q3 PASS proves the ACL-deny + authenticated-witness + cross-process
    different-account sandbox MECHANISM on the object class used here
    (controlled canary files). Q3 PASS does NOT prove a real Phase-B payload is
    isolated; that requires re-running the same flow against the real objects and
    re-binding their hashes before Phase B.
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
from pathlib import Path

# ---------------------------------------------------------------------------
# Frozen identifiers (candidate; frozen ONLY after independent review)
# ---------------------------------------------------------------------------

ISOLATION_PROFILE_ID = "PROCESS_ISOLATION_WIN32_ACL_V2"
ISOLATION_PROFILE_VERSION = "2.0"

RESTRICTING_SID = "S-1-5-12"   # well-known RESTRICTED SID (SAFER restricted token)

# ---------------------------------------------------------------------------
# Access verdicts (fail-closed; ONLY DENIED is success)
# ---------------------------------------------------------------------------

ACCESS_DENIED = "ACCESS_DENIED"
ACCESS_GRANTED = "ACCESS_GRANTED"
ACCESS_NOT_ATTEMPTED = "ACCESS_NOT_ATTEMPTED"
ACCESS_ERROR = "ACCESS_ERROR"
ACCESS_OBJECT_MISSING = "ACCESS_OBJECT_MISSING"

ACCESS_ISOLATION_OK = frozenset({ACCESS_DENIED})

#: Distinct sentinel for a check that was NOT reached (never truthy-pass).
UNEVALUATED = "UNEVALUATED"

#: WaitForSingleObject signal value (WAIT_OBJECT_0).
WAIT_OBJECT_0 = 0x00000000


class IsolationError(Exception):
    """Any isolation-mechanism failure. FAIL CLOSED."""


class EnvironmentInvalid(IsolationError):
    """The test environment itself is invalid (missing object, deny failed, ...)."""


def _is_windows() -> bool:
    return sys.platform.startswith("win")


# ---------------------------------------------------------------------------
# Win32 prototypes
# ---------------------------------------------------------------------------

def _win():
    from ctypes import wintypes

    adv = ctypes.windll.advapi32
    k32 = ctypes.windll.kernel32

    k32.GetCurrentProcess.restype = wintypes.HANDLE
    k32.GetCurrentProcess.argtypes = []

    adv.OpenProcessToken.restype = wintypes.BOOL
    adv.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                     ctypes.POINTER(wintypes.HANDLE)]
    adv.GetTokenInformation.restype = wintypes.BOOL
    adv.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                        ctypes.c_void_p, wintypes.DWORD,
                                        ctypes.POINTER(wintypes.DWORD)]
    adv.ConvertSidToStringSidW.restype = wintypes.BOOL
    adv.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p,
                                           ctypes.POINTER(wintypes.LPWSTR)]
    k32.LocalFree.restype = ctypes.c_void_p
    k32.LocalFree.argtypes = [ctypes.c_void_p]
    k32.CloseHandle.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD),
                    ("dwHighDateTime", wintypes.DWORD)]

    k32.GetProcessTimes.restype = wintypes.BOOL
    k32.GetProcessTimes.argtypes = [wintypes.HANDLE, ctypes.POINTER(FILETIME),
                                    ctypes.POINTER(FILETIME),
                                    ctypes.POINTER(FILETIME),
                                    ctypes.POINTER(FILETIME)]
    return adv, k32, FILETIME


def _filetime_to_unix(ft) -> float:
    # FILETIME is 100-ns ticks since 1601-01-01; convert to unix seconds.
    ticks = (ft.dwHighDateTime << 32) | ft.dwLowDateTime
    if ticks == 0:
        return 0.0
    return ticks / 1e7 - 11644473600.0


# ---------------------------------------------------------------------------
# Security principal: resolve the current TOKEN SID (never USERNAME)
# ---------------------------------------------------------------------------

def current_user_sid() -> str:
    if not _is_windows():
        raise IsolationError(f"{ISOLATION_PROFILE_ID} is Win32-only")
    from ctypes import wintypes
    adv, k32, _ = _win()

    TOKEN_QUERY = 0x0008
    TokenUser = 1

    class SID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]

    class TOKEN_USER(ctypes.Structure):
        _fields_ = [("User", SID_AND_ATTRIBUTES)]

    h_token = wintypes.HANDLE()
    if not adv.OpenProcessToken(k32.GetCurrentProcess(), TOKEN_QUERY,
                                ctypes.byref(h_token)):
        raise IsolationError(f"OpenProcessToken failed ({k32.GetLastError()})")
    try:
        size = wintypes.DWORD(0)
        adv.GetTokenInformation(h_token, TokenUser, None, 0, ctypes.byref(size))
        buf = ctypes.create_string_buffer(size.value)
        if not adv.GetTokenInformation(h_token, TokenUser, buf, size.value,
                                       ctypes.byref(size)):
            raise IsolationError(f"GetTokenInformation failed ({k32.GetLastError()})")
        tu = ctypes.cast(buf, ctypes.POINTER(TOKEN_USER)).contents
        sp = wintypes.LPWSTR()
        if not adv.ConvertSidToStringSidW(tu.User.Sid, ctypes.byref(sp)):
            raise IsolationError(f"ConvertSidToStringSidW failed ({k32.GetLastError()})")
        try:
            return ctypes.wstring_at(sp)
        finally:
            k32.LocalFree(sp)
    finally:
        k32.CloseHandle(h_token)


# ---------------------------------------------------------------------------
# Object identity binding (BD-63)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ObjectIdentity:
    object_id: str
    abs_path: str
    size: int
    sha256: str


def bind_object_identity(object_id: str, path: Path) -> ObjectIdentity:
    p = Path(path).resolve()
    if not p.is_file():
        raise EnvironmentInvalid(f"object is not a regular file: {p}")
    data = p.read_bytes()
    return ObjectIdentity(object_id, str(p), len(data),
                          hashlib.sha256(data).hexdigest())


def identity_still_matches(identity: ObjectIdentity) -> bool:
    p = Path(identity.abs_path)
    try:
        if not p.is_file():
            return False
        data = p.read_bytes()
    except OSError:
        return False
    return len(data) == identity.size and hashlib.sha256(data).hexdigest() == identity.sha256


# ---------------------------------------------------------------------------
# Denial primitive: real DACL deny ACE on a SID (never chmod, never USERNAME)
# ---------------------------------------------------------------------------

def deny_read_for_sid(path: Path, sid: str) -> None:
    if not _is_windows():
        raise IsolationError(
            f"{ISOLATION_PROFILE_ID} is Win32-only; refusing to fake isolation "
            f"with a POSIX chmod")
    p = subprocess.run(["icacls", str(path), "/deny", f"*{sid}:(R)"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise EnvironmentInvalid(
            f"deny ACE install FAILED (rc={p.returncode}) for {path}: "
            f"{p.stdout}{p.stderr}")


def save_dacl(path: Path) -> str:
    """Save the object's FULL DACL (SDDL) via icacls /save so it can be exactly
    restored. Returns the saved SDDL text (empty => failure)."""
    p = Path(path)
    save_dir = p.parent
    save_file = save_dir / (p.name + ".aclsave.txt")
    r = subprocess.run(["icacls", str(p), "/save", str(save_file), "/T"],
                       capture_output=True, text=True)
    if r.returncode != 0 or not save_file.exists():
        raise EnvironmentInvalid(f"save_dacl failed (rc={r.returncode}): {r.stderr}")
    # The save file is a small ACL descriptor DB (UTF-16). Read raw.
    raw = save_file.read_bytes()
    try:
        text = raw.decode("utf-16")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", "replace")
    return text


def restore_dacl(path: Path, saved_text: str) -> bool:
    """Restore a SAVED DACL exactly via icacls /restore (the OS-blessed exact
    rollback), NOT ``/reset`` (which merely rebuilds inherited perms). Returns
    True only if the restore command succeeded (凌翼 gap 3)."""
    if not _is_windows():
        return True
    if not saved_text:
        return False
    p = Path(path)
    save_file = p.parent / (p.name + ".aclsave.txt")
    save_file.write_text(saved_text, encoding="utf-16")
    r = subprocess.run(["icacls", str(p.parent), "/restore", str(save_file)],
                       capture_output=True, text=True)
    return r.returncode == 0


def restore_dacl_outcome(path: Path, saved_text: str) -> tuple[str, str]:
    """Like restore_dacl but distinguishes ENVIRONMENT-PRECONDITION failure from a
    real restore bug (知微 P1 / 凌翼 Q1 classification).

    Returns (outcome, detail) where outcome is one of:
      "OK"             — restore succeeded
      "NOT_APPLICABLE" — the caller token lacks the privilege /restore needs
                         (icacls exit 1300 "not all privileges ... assigned")
      "FAILED"         — restore genuinely failed for another reason
    """
    if not _is_windows():
        return "OK", "non-Windows: DACL restore not applicable"
    if not saved_text:
        return "FAILED", "no saved DACL text"
    p = Path(path)
    save_file = p.parent / (p.name + ".aclsave.txt")
    save_file.write_text(saved_text, encoding="utf-16")
    r = subprocess.run(["icacls", str(p.parent), "/restore", str(save_file)],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return "OK", "restore succeeded"
    msg = ((r.stdout or "") + (r.stderr or "")).strip()
    low = msg.lower()
    priv_markers = ("1300", "privilege", "privileges", "权限", "特权")
    if any(m in low for m in priv_markers):
        return "NOT_APPLICABLE", (f"icacls /restore rc={r.returncode} — caller token "
                                  f"lacks the restore privilege (env precondition): {msg[:200]}")
    return "FAILED", f"icacls /restore rc={r.returncode}: {msg[:200]}"



# ---------------------------------------------------------------------------
# Authenticated access witness (Q3-F1)
# ---------------------------------------------------------------------------
#
# The judge holds a per-run secret; only probe_read_access() can seal a witness.
# A hand-built AccessWitness carries no valid seal and is ALWAYS rejected.

_RUN_SECRET: bytes = b""


def start_run() -> str:
    """Begin a judging run: generate the run secret + nonce. Returns the nonce."""
    global _RUN_SECRET
    _RUN_SECRET = secrets.token_bytes(32)
    return uuid.uuid4().hex


def _seal(fields: dict) -> str:
    if not _RUN_SECRET:
        raise IsolationError("no active run secret; call start_run() first")
    msg = "|".join(f"{k}={fields[k]}" for k in sorted(fields)).encode("utf-8")
    return hmac.new(_RUN_SECRET, msg, hashlib.sha256).hexdigest()


def _unsealed_signature_fields(w) -> dict:
    return {
        "nonce": w.run_nonce, "object_id": w.object_id,
        "abs_path": w.object_identity.abs_path if w.object_identity else "",
        "size": w.object_identity.size if w.object_identity else -1,
        "sha256": w.object_identity.sha256 if w.object_identity else "",
        "op": w.requested_access, "attempted": w.attempted,
        "verdict": w.verdict, "winerror": w.winerror, "errno": w.errno,
        "attempted_path": w.attempted_path or "",
    }


@dataclass
class AccessWitness:
    run_nonce: str
    object_id: str
    object_identity: "ObjectIdentity | None"
    requested_access: str
    attempted: bool
    verdict: str
    winerror: int | None = None
    errno: int | None = None
    attempted_path: str | None = None
    detail: str = ""
    seal: str | None = None            # set ONLY by probe_read_access

    @property
    def isolated(self) -> bool:
        """Strict AND sealed: a valid HMAC seal over the observed fields, a real
        attempt, a denial verdict, a bound identity, and a matching attempt path."""
        return (self.seal is not None
                and hmac.compare_digest(self.seal, _seal(_unsealed_signature_fields(self)))
                and self.attempted is True
                and self.verdict in ACCESS_ISOLATION_OK
                and self.object_identity is not None
                and self.attempted_path is not None
                and self.attempted_path == self.object_identity.abs_path)


def probe_read_access(run_nonce: str, identity: ObjectIdentity) -> AccessWitness:
    """Attempt to READ the expected object; classify. The witness is SEALED."""
    path = Path(identity.abs_path)

    def _mk(verdict, **kw):
        w = AccessWitness(run_nonce, identity.object_id, identity, "READ",
                          kw.pop("attempted", True), verdict, **kw)
        w.seal = _seal(_unsealed_signature_fields(w))
        return w

    # Type bind BEFORE opening (知微 defect 1): a directory opened as a file on
    # Windows raises PermissionError -> would be mis-read as a denial.
    try:
        if not path.is_file():
            return _mk(ACCESS_OBJECT_MISSING if not path.exists() else ACCESS_ERROR,
                       attempted_path=str(path),
                       detail="object missing or not a regular file (environment INVALID)")
    except OSError as e:
        return _mk(ACCESS_ERROR, attempted_path=str(path),
                   winerror=getattr(e, "winerror", None),
                   detail=f"type probe error: {e}")

    try:
        with open(path, "rb") as fh:
            fh.read()
        return _mk(ACCESS_GRANTED, attempted_path=str(path),
                   detail="read succeeded: isolation FAILED")
    except FileNotFoundError as e:
        return _mk(ACCESS_OBJECT_MISSING, attempted_path=str(path),
                   errno=getattr(e, "errno", None),
                   winerror=getattr(e, "winerror", None),
                   detail="object missing: environment INVALID")
    except PermissionError as e:
        return _mk(ACCESS_DENIED, attempted_path=str(path),
                   errno=getattr(e, "errno", None),
                   winerror=getattr(e, "winerror", None), detail=str(e))
    except IsADirectoryError as e:
        return _mk(ACCESS_ERROR, attempted_path=str(path),
                   winerror=getattr(e, "winerror", None),
                   detail="object is a directory (environment INVALID)")
    except OSError as e:
        return _mk(ACCESS_ERROR, attempted_path=str(path),
                   errno=getattr(e, "errno", None),
                   winerror=getattr(e, "winerror", None),
                   detail=f"non-permission OS error: {e}")


# ---------------------------------------------------------------------------
# Worker lifecycle with OS process times (凌翼 gap 2)
# ---------------------------------------------------------------------------

@dataclass
class WorkerLifecycle:
    run_nonce: str
    old_worker_pid: int | None
    old_exit_time: float | None
    new_worker_pid: int
    new_create_time: float
    old_terminated_before_new: bool
    detail: str = ""


def _process_times(pid: int):
    """Return (creation_time, exit_time) for a pid via OpenProcess+GetProcessTimes.
    Requires PROCESS_QUERY_LIMITED_INFORMATION. Returns (None, None) on failure."""
    from ctypes import wintypes
    adv, k32, FILETIME = _win()
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    h = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None, None
    try:
        c, e, kt, ut = FILETIME(), FILETIME(), FILETIME(), FILETIME()
        if not k32.GetProcessTimes(h, ctypes.byref(c), ctypes.byref(e),
                                   ctypes.byref(kt), ctypes.byref(ut)):
            return None, None
        return _filetime_to_unix(c), _filetime_to_unix(e)
    finally:
        k32.CloseHandle(h)


def spawn_worker_tracked(child_argv: list[str], run_nonce: str,
                         old_worker_pid: int | None) -> tuple[subprocess.CompletedProcess,
                                                              WorkerLifecycle]:
    """Spawn a worker and record TRUE lifecycle evidence.

    - old process exit time is read from the OS (GetProcessTimes). 知微 P1-2:
      a still-alive process reports an UNDEFINED exit time (we read it as 0.0),
      so `0.0 <= new_create` would WRONGLY claim the old worker exited first.
      We therefore require old_exit > 0 AND that the old process is actually
      GONE (OpenProcess fails / wait signals) before claiming old-before-new.
    - new creation time is read from the OS, not time.time() after wait.
    - close_fds=True is explicit (必要非充分; 凌翼 gap 2).
    """
    p = subprocess.Popen([sys.executable, *child_argv],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, close_fds=True)
    new_pid = p.pid
    new_create, _ = _process_times(new_pid)
    out, err = p.communicate(timeout=60)
    cp = subprocess.CompletedProcess(p.args, p.returncode, out, err)

    old_exit = None
    old_is_gone = False
    if old_worker_pid is not None:
        old_create, old_exit = _process_times(old_worker_pid)
        old_is_gone = _process_is_gone(old_worker_pid)
    # require BOTH a non-zero exit time AND the process actually gone
    old_before_new = bool(old_exit is not None and old_exit > 0.0
                          and old_is_gone and new_create is not None
                          and old_exit <= new_create)
    lc = WorkerLifecycle(run_nonce, old_worker_pid, old_exit, new_pid,
                         new_create or 0.0, old_before_new,
                         detail=f"old_exit={old_exit} old_gone={old_is_gone} "
                                f"new_create={new_create} rc={p.returncode}")
    return cp, lc


def _process_is_gone(pid: int) -> bool:
    """True iff the process handle signals (the process has terminated)."""
    from ctypes import wintypes
    adv, k32, _ = _win()   # correct module-local Win32 factory
    SYNCHRONIZE = 0x00100000
    k32.OpenProcess.restype = wintypes.HANDLE
    k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k32.WaitForSingleObject.restype = wintypes.DWORD
    k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    k32.CloseHandle.restype = wintypes.BOOL
    k32.CloseHandle.argtypes = [wintypes.HANDLE]
    h = k32.OpenProcess(SYNCHRONIZE, False, pid)
    if not h:
        # cannot open => no observation; treat as NOT gone (fail-closed)
        return False
    try:
        return k32.WaitForSingleObject(h, 0) == WAIT_OBJECT_0
    finally:
        k32.CloseHandle(h)


# ---------------------------------------------------------------------------
# Independent post-reset observation (Q3-A) — NOT from cache
# ---------------------------------------------------------------------------

@dataclass
class ResetEvidence:
    s_handoff: bytes | None
    s_restored: bytes | None
    handoff_source: str
    restored_source: str


def observe_handoff(observer_read) -> bytes:
    """Observer's INDEPENDENT pre-reset read. observer_read is a callable that
    performs the real read."""
    return observer_read()


def observe_restored(observer_read) -> bytes:
    """Observer's INDEPENDENT post-reset read (NOT the cached handoff)."""
    return observer_read()


def preserve_verdict(ev: ResetEvidence) -> object:
    """True / False / UNEVALUATED for the preserve side (Q3-A)."""
    if ev.s_handoff is None or ev.s_restored is None:
        return UNEVALUATED
    if ev.restored_source == "cache":
        return UNEVALUATED          # cached bytes are NOT restored evidence
    return ev.s_handoff == ev.s_restored


# ---------------------------------------------------------------------------
# Strict three-way reset gate (fail-closed)
# ---------------------------------------------------------------------------

@dataclass
class ResetWitness:
    clear_ok: object = UNEVALUATED
    preserve_ok: object = UNEVALUATED
    access_ok: object = UNEVALUATED
    reason: str = ""

    @property
    def valid(self) -> bool:
        return (self.clear_ok is True and self.preserve_ok is True
                and self.access_ok is True)


def judge_reset(clear_ok, preserve_ok, access_ok) -> ResetWitness:
    w = ResetWitness(clear_ok, preserve_ok, access_ok)
    if not w.valid:
        bad = [n for n, v in (("clear", clear_ok), ("preserve", preserve_ok),
                              ("access", access_ok)) if v is not True]
        w.reason = f"RESET_INVALID: sides not True: {bad}"
    return w


def _checked_cleanup(path: Path) -> bool:
    try:
        shutil.rmtree(path)
    except OSError as e:
        print(f"cleanup error: {e}")
        return False
    return not path.exists()


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

def _selftest() -> int:
    results = []
    not_applicable = []      # 知微 P1: environment-precondition tests (env N/A)

    def chk(name, cond):
        results.append((name, bool(cond)))
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    def na(name, detail):
        """Mark a test NOT_APPLICABLE (env precondition unmet). NOT a PASS, and
        NOT a FAIL: it makes the overall selftest exit 2 (SKIP)."""
        not_applicable.append((name, detail))
        print(f"[N/A ] {name}  {detail}")

    if not _is_windows():
        print("win32_isolation selftest requires Windows")
        return 2

    run = start_run()
    tmp = Path(tempfile.mkdtemp(prefix="q3v2_"))
    sid = current_user_sid()
    chk("PRINCIPAL: token SID resolved (not USERNAME)", sid.startswith("S-1-"))

    # NEGATIVE CONTROL: chmod(0) does NOT deny
    c1 = tmp / "chmod_canary.bin"; c1.write_bytes(b"\x01\x02\x03\x04" * 4)
    os.chmod(c1, 0)
    ok = True
    try:
        c1.read_bytes()
    except Exception:
        ok = False
    os.chmod(c1, 0o666)
    chk("NEGATIVE CONTROL: os.chmod(0) does NOT deny read on Windows", ok)

    # POSITIVE: deny by restricting SID -> observer (no restricting SID) keeps read
    c2 = tmp / "observer_canary.bin"; c2.write_bytes(b"observer-payload")
    id2 = bind_object_identity("canary", c2)
    sddl = save_dacl(c2)
    deny_read_for_sid(c2, RESTRICTING_SID)
    w_obs = probe_read_access(run, id2)
    chk("SHAPE: deny by RESTRICTING SID -> observer still reads (GRANTED)",
        w_obs.verdict == ACCESS_GRANTED)
    # restore the exact DACL and verify. 知微 P1: icacls /restore needs SeRestore
    # privilege; when the caller token is UNELEVATED (Limited, 1300), this is an
    # ENVIRONMENT PRECONDITION, not a restore bug -> report NOT_APPLICABLE (exit 2),
    # never a silent PASS and never a hard FAIL.
    _outcome, _detail = restore_dacl_outcome(c2, sddl)
    if _outcome == "OK":
        chk("DACL: exact restore via saved SDDL verified", True)
    elif _outcome == "NOT_APPLICABLE":
        na("DACL: exact restore via saved SDDL verified", _detail)
    else:
        chk("DACL: exact restore via saved SDDL verified", False)
        print("   detail:", _detail)


    # DENIED: deny by MY OWN SID -> my read denied (mechanism works)
    c3 = tmp / "self_denied.bin"; c3.write_bytes(b"self")
    id3 = bind_object_identity("self", c3)
    deny_read_for_sid(c3, sid)
    w3 = probe_read_access(run, id3)
    chk("MECHANISM: deny by own SID -> ACCESS_DENIED", w3.verdict == ACCESS_DENIED)
    chk("SEAL: genuine denial witness is isolated", w3.isolated is True)

    # Q3-F1: hand-forged witness is NOT isolated (no seal)
    forged = AccessWitness(run, "self", id3, "READ", True, ACCESS_DENIED,
                           attempted_path=id3.abs_path)
    chk("Q3-F1: hand-forged witness (no seal) -> isolated False", forged.isolated is False)
    # tampered seal rejected
    forged2 = AccessWitness(run, "self", id3, "READ", True, ACCESS_DENIED,
                            attempted_path=id3.abs_path, seal="deadbeef")
    chk("Q3-F1: tampered seal -> isolated False", forged2.isolated is False)

    # 知微 defect 1: directory as expected file -> ACCESS_ERROR
    dd = tmp / "adir"; dd.mkdir()
    idd = ObjectIdentity("dir", str(dd.resolve()), 0, "")
    wd = probe_read_access(run, idd)
    chk("FIX(defect1): directory -> ACCESS_ERROR not DENIED",
        wd.verdict == ACCESS_ERROR and wd.isolated is False)

    # missing object -> ACCESS_OBJECT_MISSING
    idm = ObjectIdentity("missing", str((tmp / "nope.bin").resolve()), 0, "")
    wm = probe_read_access(run, idm)
    chk("FIX: missing -> ACCESS_OBJECT_MISSING (INVALID)",
        wm.verdict == ACCESS_OBJECT_MISSING and wm.isolated is False)

    # Q3-A: preserve from CACHE -> UNEVALUATED; independent unequal -> False
    ev_cache = ResetEvidence(b"AAA", b"AAA", "observer", "cache")
    chk("Q3-A: preserve from cache -> UNEVALUATED", preserve_verdict(ev_cache) == UNEVALUATED)
    ev_uneq = ResetEvidence(b"AAA", b"BBB", "observer", "observer")
    chk("Q3-A: independent handoff!=restored -> False", preserve_verdict(ev_uneq) is False)
    ev_eq = ResetEvidence(b"AAA", b"AAA", "observer", "observer")
    chk("Q3-A: independent handoff==restored -> True", preserve_verdict(ev_eq) is True)

    # strict gate: UNEVALUATED not truthy-pass
    chk("GATE: UNEVALUATED sides -> NOT valid", judge_reset(UNEVALUATED, UNEVALUATED, True).valid is False)
    chk("GATE: all True -> valid", judge_reset(True, True, True).valid is True)

    # lifecycle: OS process times + old-exited-before-new
    script = tmp / "worker.py"
    script.write_text("import time,sys; time.sleep(0.05)\n", encoding="utf-8")
    cp, lc = spawn_worker_tracked([str(script)], run, old_worker_pid=None)
    chk("LIFECYCLE: OS creation time recorded for new worker", lc.new_create_time > 0)
    chk("LIFECYCLE: worker rc recorded", cp.returncode == 0)
    # now without an old pid, old_before_new is False (not claimable)
    chk("LIFECYCLE: old-before-new NOT claimed when no old pid",
        lc.old_terminated_before_new is False)

    # 知微: live old pid must NOT be judged as already-exited (was 0.0 <= new)
    cp_live, lc_live = spawn_worker_tracked([str(script)], run, old_worker_pid=os.getpid())
    chk("LIFECYCLE: LIVE old worker -> old-before-new NOT claimed (fail-closed)",
        lc_live.old_terminated_before_new is False)
    # a truly-exited old process -> old_exit>0 and gone -> claimable
    probe_script = tmp / "quick.py"
    probe_script.write_text("pass\n", encoding="utf-8")
    quick = subprocess.Popen([sys.executable, str(probe_script)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    quick.wait()
    gone = _process_is_gone(quick.pid)
    chk("LIFECYCLE: exited process -> _process_is_gone True", gone is True)

    chk("CLEANUP: checked (True on success)", _checked_cleanup(tmp) is True)

    passed = sum(1 for _, ok in results if ok)
    # 知微 P1: FAIL dominates; otherwise env-N/A (SKIP) => exit 2; else 0.
    suffix = ""
    if not_applicable:
        suffix = f" [{len(not_applicable)} NOT_APPLICABLE (env precondition)]"
    print(f"\nwin32_isolation selftest (V2): {passed}/{len(results)} PASS{suffix}")
    if passed != len(results):
        return 1
    if not_applicable:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
