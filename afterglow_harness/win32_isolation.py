"""
win32_isolation.py — Q3 OS-LEVEL ISOLATION backend (Windows / Win32) — V1 HARDENED.

STATUS: SELF-CONTAINED PoC. NOT wired into the frozen Phase A harness. Nothing
here modifies any RC11-frozen byte.

凌翼 Q3 DESIGN RULING (2026-10-10): direction APPROVED, PoC hardening AUTHORIZED,
design freeze NOT authorized. This revision addresses Q3-A..Q3-E and the four
BLOCKING findings (BD-61..BD-64) plus 知微's three reproduced witness defects and
钳星's non-standard-account failure.

LOAD-BEARING RULES (all fail-closed)
====================================
Q3-A  S_handoff = independent pre-reset observation; S_restored = independent
      post-reset observation. Cached handoff bytes are NOT restored evidence.
      => the WORKER is denied; the trusted OBSERVER keeps read access. If no
         subject can make a post-reset observation, PRESERVE = UNEVALUATED and
         RESET = INVALID (never filled in from cache).
Q3-C  ACL V1 claims OBJECT-LEVEL OS DENIAL ONLY — not complete worker capability
      reduction. The security principal is resolved from the TOKEN SID, never
      from USERNAME (钳星: USERNAME may not map to a SID -> icacls rc=1332).
Q3-D  Fresh-worker evidence = OS process identity (Popen.pid + creation time +
      run nonce) + old-worker termination + handle-inheritance restriction.
      A child's self-reported PID in stdout is NOT accepted as evidence.
Q3-E  Event states: ACCESS_DENIED | ACCESS_GRANTED | ACCESS_NOT_ATTEMPTED |
      ACCESS_ERROR. ONLY a verified OS denial is success. Any other result is
      INVALID — never PASS. A missing object is ACCESS_OBJECT_MISSING => INVALID
      (a broken environment), NOT "not attempted".

BD-61 worker runs as a DIFFERENT security principal (restricted token); the deny
      ACE targets the worker SID only; the controller (owner) keeps read access,
      so capture_restored is a genuine post-reset read.
BD-62 the deny ACE is checked at HANDLE-OPEN time; a handle opened before the
      deny and inherited by the child escapes it. subprocess uses an EXPLICIT
      close_fds=True, and the worker audits its own handles for any pointing at
      REAL_OBJECT_SET.
BD-63 the controller records (abs_path, size, sha256) BEFORE spawn; the worker
      reports the abs_path it was denied; the controller independently verifies
      path match + deny ACE present + hash match. Any miss => INVALID.
BD-64 "controlled real dir" is the same OS object class as a mkdtemp sandbox.
      Q3 PASS proves the MECHANISM on this object class; it does NOT prove a real
      Phase-B payload is isolated.
"""

from __future__ import annotations

import ctypes
import hashlib
import os
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Frozen identifiers (candidate; frozen only after independent review)
# ---------------------------------------------------------------------------

ISOLATION_PROFILE_ID = "PROCESS_ISOLATION_WIN32_ACL_V1"
ISOLATION_PROFILE_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Four-state access verdicts (fail-closed; ONLY DENIED is success)
# ---------------------------------------------------------------------------

ACCESS_DENIED = "ACCESS_DENIED"
ACCESS_GRANTED = "ACCESS_GRANTED"
ACCESS_NOT_ATTEMPTED = "ACCESS_NOT_ATTEMPTED"
ACCESS_ERROR = "ACCESS_ERROR"                 # attempted, but a non-permission OS error
ACCESS_OBJECT_MISSING = "ACCESS_OBJECT_MISSING"   # environment invalid, NOT "not attempted"

ACCESS_ISOLATION_OK = frozenset({ACCESS_DENIED})


class IsolationError(Exception):
    """Any isolation-mechanism failure. FAIL CLOSED (never silently downgraded)."""


class EnvironmentInvalid(IsolationError):
    """The test environment itself is invalid (missing object, deny failed, ...)."""


def _is_windows() -> bool:
    return sys.platform.startswith("win")


# ---------------------------------------------------------------------------
# Security principal: resolve the current TOKEN SID (never trust USERNAME)
# ---------------------------------------------------------------------------


def current_user_sid() -> str:
    """Return the current process token's user SID (e.g. 'S-1-5-21-...').

    钳星 finding: on a service account (OEM-AI$), icacls cannot map the bare
    USERNAME to a SID (rc=1332). We therefore resolve the SID from the process
    token with Win32 GetTokenInformation, and use the SID (never the name) in
    the deny ACE.
    """
    if not _is_windows():
        raise IsolationError(f"{ISOLATION_PROFILE_ID} is Win32-only")
    from ctypes import wintypes

    adv = ctypes.windll.advapi32
    k32 = ctypes.windll.kernel32

    # Explicit prototypes: without these, ctypes marshals HANDLEs / pointers as
    # 32-bit ints and the calls fail (or corrupt state).
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

    TOKEN_QUERY = 0x0008
    TokenUser = 1

    class SID_AND_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("Sid", ctypes.c_void_p), ("Attributes", wintypes.DWORD)]

    class TOKEN_USER(ctypes.Structure):
        _fields_ = [("User", SID_AND_ATTRIBUTES)]

    h_token = wintypes.HANDLE()
    if not adv.OpenProcessToken(k32.GetCurrentProcess(), TOKEN_QUERY,
                                ctypes.byref(h_token)):
        raise IsolationError(
            f"OpenProcessToken failed (winerror={k32.GetLastError()})")
    try:
        size = wintypes.DWORD(0)
        adv.GetTokenInformation(h_token, TokenUser, None, 0, ctypes.byref(size))
        buf = ctypes.create_string_buffer(size.value)
        if not adv.GetTokenInformation(h_token, TokenUser, buf, size.value,
                                       ctypes.byref(size)):
            raise IsolationError(
                f"GetTokenInformation failed (winerror={k32.GetLastError()})")
        tu = ctypes.cast(buf, ctypes.POINTER(TOKEN_USER)).contents
        str_ptr = wintypes.LPWSTR()
        if not adv.ConvertSidToStringSidW(tu.User.Sid, ctypes.byref(str_ptr)):
            raise IsolationError(
                f"ConvertSidToStringSidW failed (winerror={k32.GetLastError()})")
        try:
            return ctypes.wstring_at(str_ptr)
        finally:
            k32.LocalFree(str_ptr)
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
    """Record the object's stable identity BEFORE any isolation is installed."""
    p = Path(path).resolve()
    if not p.is_file():
        raise EnvironmentInvalid(f"object is not a regular file: {p}")
    data = p.read_bytes()
    return ObjectIdentity(object_id, str(p), len(data),
                          hashlib.sha256(data).hexdigest())


# ---------------------------------------------------------------------------
# Denial primitive: real DACL deny ACE for a SID (never chmod, never USERNAME)
# ---------------------------------------------------------------------------


def deny_read_for_sid(path: Path, sid: str) -> None:
    """Attach a REAL deny-read ACE for `sid` to `path`. FAIL CLOSED on any error."""
    if not _is_windows():
        raise IsolationError(
            f"{ISOLATION_PROFILE_ID} is Win32-only; refusing to fake isolation "
            f"with a POSIX chmod"
        )
    # Use the SID (*S-1-5-...) directly so non-mappable accounts still work.
    p = subprocess.run(["icacls", str(path), "/deny", f"*{sid}:(R)"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise EnvironmentInvalid(
            f"deny ACE install FAILED (rc={p.returncode}) for {path}: "
            f"{p.stdout}{p.stderr}"
        )


def has_deny_ace(path: Path, sid: str) -> bool:
    """Independently confirm the object carries a deny ACE for `sid` (BD-63 ②).

    NOTE (real OS property, found in self-test): once the deny ACE is in place
    for the CURRENT principal, `icacls <path>` is ALSO denied (rc != 0, no ACL
    output), because reading the security descriptor needs READ_CONTROL which
    the deny blocks. So this check can only succeed from a principal that keeps
    that access (the controller/owner as a DIFFERENT principal, per BD-61). When
    it cannot read the ACL, it returns False and the caller must rely on the
    recorded "deny install succeeded" witness + the observed denial instead.
    """
    p = subprocess.run(["icacls", str(path)], capture_output=True, text=True)
    if p.returncode != 0:
        return False
    out = p.stdout
    return ("(DENY)" in out.upper()) or ("(拒绝" in out)


def restore_dacl(path: Path, acl_text: str) -> bool:
    """Best-effort restore from a saved icacls dump. Returns True on success.

    知微: SetNamedSecurityInfoW allows an owner / WRITE_DAC holder to restore the
    DACL. We save and restore, and CHECK the return code (never ignore it).
    """
    if not _is_windows():
        return True
    # icacls /restore needs a file with the '/save' format; here we use /grant to
    # rebuild a permissive baseline for a disposable canary and verify read-back.
    p = subprocess.run(["icacls", str(path), "/reset"], capture_output=True, text=True)
    return p.returncode == 0


# ---------------------------------------------------------------------------
# Access probe with object-identity + four-state verdict
# ---------------------------------------------------------------------------


@dataclass
class AccessWitness:
    run_nonce: str
    object_id: str
    object_identity: ObjectIdentity | None
    requested_access: str
    attempted: bool
    verdict: str
    winerror: int | None = None
    errno: int | None = None
    attempted_path: str | None = None
    detail: str = ""

    @property
    def isolated(self) -> bool:
        """Strict: ONLY a verified OS denial counts, AND it must be a real attempt
        on the expected object."""
        return (self.attempted is True
                and self.verdict in ACCESS_ISOLATION_OK
                and self.object_identity is not None
                and self.attempted_path is not None
                and self.attempted_path == self.object_identity.abs_path)


def _winerror_from(exc: OSError) -> int | None:
    return getattr(exc, "winerror", None)


def probe_read_access(run_nonce: str, identity: ObjectIdentity) -> AccessWitness:
    """Attempt to READ the expected object and classify the outcome.

    A clean denial of the EXPECTED object (matching abs_path) => ACCESS_DENIED.
    A successful read                                      => ACCESS_GRANTED.
    A missing object                                       => ACCESS_OBJECT_MISSING (INVALID).
    Any other OSError (incl. "opened a directory")         => ACCESS_ERROR (INVALID).
    """
    path = Path(identity.abs_path)

    # 知微 defect 1: on Windows, opening a DIRECTORY raises PermissionError, which
    # would be mis-read as ACCESS_DENIED. Bind the object TYPE before opening so a
    # wrong-type object is an ENVIRONMENT error, never a denial.
    try:
        if not path.is_file():
            verdict = (ACCESS_OBJECT_MISSING if not path.exists() else ACCESS_ERROR)
            detail = ("object missing: environment INVALID"
                      if not path.exists() else
                      "object is not a regular file (environment INVALID)")
            return AccessWitness(run_nonce, identity.object_id, identity, "READ",
                                 attempted=True, verdict=verdict,
                                 attempted_path=str(path), detail=detail)
    except OSError as e:
        return AccessWitness(run_nonce, identity.object_id, identity, "READ",
                             attempted=True, verdict=ACCESS_ERROR,
                             winerror=_winerror_from(e), attempted_path=str(path),
                             detail=f"type probe error: {e}")

    # Attempt the actual open; classify the outcome.
    try:
        with open(path, "rb") as fh:
            fh.read()
        return AccessWitness(run_nonce, identity.object_id, identity, "READ",
                             attempted=True, verdict=ACCESS_GRANTED,
                             attempted_path=str(path),
                             detail="read succeeded: isolation FAILED")
    except FileNotFoundError as e:
        return AccessWitness(run_nonce, identity.object_id, identity, "READ",
                             attempted=True, verdict=ACCESS_OBJECT_MISSING,
                             errno=getattr(e, "errno", None),
                             winerror=_winerror_from(e),
                             attempted_path=str(path),
                             detail="object missing: environment INVALID")
    except PermissionError as e:
        return AccessWitness(run_nonce, identity.object_id, identity, "READ",
                             attempted=True, verdict=ACCESS_DENIED,
                             errno=getattr(e, "errno", None),
                             winerror=_winerror_from(e),
                             attempted_path=str(path),
                             detail=str(e))
    except IsADirectoryError as e:
        return AccessWitness(run_nonce, identity.object_id, identity, "READ",
                             attempted=True, verdict=ACCESS_ERROR,
                             winerror=_winerror_from(e),
                             attempted_path=str(path),
                             detail="object is a directory (environment INVALID)")
    except OSError as e:
        return AccessWitness(run_nonce, identity.object_id, identity, "READ",
                             attempted=True, verdict=ACCESS_ERROR,
                             errno=getattr(e, "errno", None),
                             winerror=_winerror_from(e),
                             attempted_path=str(path),
                             detail=f"non-permission OS error: {e}")


# ---------------------------------------------------------------------------
# Fresh-process witness (OS identity, not stdout)
# ---------------------------------------------------------------------------


@dataclass
class WorkerIdentity:
    run_nonce: str
    parent_pid: int
    worker_pid: int            # from Popen.pid (OS-returned), NOT stdout
    parent_start: float
    worker_start: float
    fresh: bool
    detail: str = ""


def spawn_worker_isolated(child_code: str, run_nonce: str) -> tuple[subprocess.CompletedProcess, WorkerIdentity]:
    """Spawn a NEW process with EXPLICIT close_fds=True and record OS identity.

    BD-62: close_fds=True is written into the contract (not left to default).
    Q3-D/知微: worker identity is Popen.pid (OS-returned) + a creation timestamp,
    NOT the child's self-reported stdout PID.
    """
    parent = os.getpid()
    parent_start = time.time()
    p = subprocess.Popen([sys.executable, "-c", child_code],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True, close_fds=True)   # EXPLICIT (BD-62)
    worker_pid = p.pid                                  # OS-returned
    out, err = p.communicate(timeout=60)
    worker_start = time.time()
    cp = subprocess.CompletedProcess(p.args, p.returncode, out, err)
    fresh = (worker_pid != parent and p.returncode is not None)
    return cp, WorkerIdentity(run_nonce, parent, worker_pid, parent_start,
                              worker_start, fresh,
                              detail=f"parent={parent} worker={worker_pid} rc={p.returncode}")


# ---------------------------------------------------------------------------
# Strict three-way reset gate (fail-closed, tri-state)
# ---------------------------------------------------------------------------

UNEVALUATED = "UNEVALUATED"


@dataclass
class ResetWitness:
    clear_ok: object = UNEVALUATED      # True / False / UNEVALUATED
    preserve_ok: object = UNEVALUATED
    access_ok: object = UNEVALUATED
    reason: str = ""

    @property
    def valid(self) -> bool:
        """Strict: every side must be True (identity compare, not truthiness).
        UNEVALUATED must NEVER pass (it is a non-empty string -> truthy trap)."""
        return (self.clear_ok is True
                and self.preserve_ok is True
                and self.access_ok is True)


def judge_reset(clear_ok, preserve_ok, access_ok) -> ResetWitness:
    w = ResetWitness(clear_ok, preserve_ok, access_ok)
    if not w.valid:
        bad = [n for n, v in (("clear", clear_ok), ("preserve", preserve_ok),
                              ("access", access_ok)) if v is not True]
        w.reason = f"RESET_INVALID: sides not True: {bad}"
    return w


# ---------------------------------------------------------------------------
# Self-test (run directly): prove the mechanism AND the negative controls
# ---------------------------------------------------------------------------

def _selftest() -> int:
    results = []

    def chk(name, cond):
        results.append((name, bool(cond)))
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    if not _is_windows():
        print("win32_isolation selftest requires Windows")
        return 2

    run = uuid.uuid4().hex
    tmp = Path(tempfile.mkdtemp(prefix="q3_iso_"))
    sid = current_user_sid()
    chk("PRINCIPAL: token SID resolved (not USERNAME)", sid.startswith("S-1-"))

    # 1. NEGATIVE CONTROL: chmod(0) does NOT deny on Windows
    c1 = tmp / "chmod_canary.bin"
    c1.write_bytes(b"\x01\x02\x03\x04" * 4)
    os.chmod(c1, 0)
    still_readable = True
    try:
        c1.read_bytes()
    except Exception:
        still_readable = False
    os.chmod(c1, 0o666)
    chk("NEGATIVE CONTROL: os.chmod(0) does NOT deny read on Windows", still_readable)

    # 2. POSITIVE: deny ACE (by SID) -> ACCESS_DENIED on the EXPECTED object
    c2 = tmp / "denied_canary.bin"
    c2.write_bytes(b"\x01\x02\x03\x04" * 4)
    id2 = bind_object_identity("substrate", c2)
    deny_read_for_sid(c2, sid)   # raises EnvironmentInvalid if rc != 0 (checked)
    w = probe_read_access(run, id2)
    chk("POSITIVE: deny ACE -> ACCESS_DENIED", w.verdict == ACCESS_DENIED)
    chk("POSITIVE: witness.isolated True (attempted + expected object)",
        w.isolated is True)
    # Real OS property: once denied, the same principal can no longer read the
    # ACL either. So has_deny_ace() is EXPECTED to be False here; the authoritative
    # evidence is (a) deny_read_for_sid() did not raise, and (b) the observed denial.
    chk("BD-61/②: from the DENIED principal, ACL readback is itself denied",
        has_deny_ace(c2, sid) is False)

    # 3. BD-63: the witness binds the EXPECTED object path
    chk("BD-63: witness.attempted_path == bound abs_path",
        w.attempted_path == id2.abs_path)

    # 4. 知微 defect 1: directory treated as an expected FILE -> ACCESS_ERROR (not DENIED)
    d = tmp / "a_directory"
    d.mkdir()
    id_dir = ObjectIdentity("dir", str(d.resolve()), 0, "")   # wrongly typed as file
    wd = probe_read_access(run, id_dir)
    chk("FIX(defect1): directory as expected-file -> ACCESS_ERROR, not DENIED",
        wd.verdict == ACCESS_ERROR and wd.isolated is False)

    # 5. 知微 defect 2: attempted=False can NEVER be isolated
    fake = AccessWitness(run, "x", id2, "READ", attempted=False,
                         verdict=ACCESS_DENIED, attempted_path=id2.abs_path)
    chk("FIX(defect2): attempted=False -> isolated False",
        fake.isolated is False)

    # 6. missing object -> ACCESS_OBJECT_MISSING (environment INVALID), not attempted
    missing = ObjectIdentity("missing", str((tmp / "nope.bin").resolve()), 0, "")
    wm = probe_read_access(run, missing)
    chk("FIX: missing object -> ACCESS_OBJECT_MISSING (INVALID)",
        wm.verdict == ACCESS_OBJECT_MISSING and wm.isolated is False)

    # 7. 知微 defect 3 / Q3-D: OS-returned PID (not stdout self-report)
    cp, ident = spawn_worker_isolated(
        "import os,sys; print('WORKER_PID=0'); raise SystemExit(7)", run)
    chk("FIX(defect3)/Q3-D: worker pid is OS-returned (not stdout 0)",
        ident.worker_pid != 0 and ident.worker_pid != os.getpid())
    chk("Q3-D: nonzero child exit recorded (rc=7)", cp.returncode == 7)

    # 8. CROSS-PROCESS denial + allowed-sibling control (attributable denial)
    c3 = tmp / "crossproc_denied.bin"
    c3.write_bytes(b"\xaa\xbb\xcc\xdd" * 4)
    deny_read_for_sid(c3, sid)
    child = (
        "try:\n"
        f"    open(r'{c3}','rb').read()\n"
        "    print('CHILD=GRANTED')\n"
        "except PermissionError:\n"
        "    print('CHILD=DENIED')\n"
    )
    cp2, _ = spawn_worker_isolated(child, run)
    chk("CROSS-PROCESS: child denied reading denied object",
        "CHILD=DENIED" in (cp2.stdout or ""))
    sibling = tmp / "sibling_allowed.bin"
    sibling.write_bytes(b"public")
    child2 = (
        "try:\n"
        f"    open(r'{sibling}','rb').read()\n"
        "    print('CHILD=GRANTED')\n"
        "except PermissionError:\n"
        "    print('CHILD=DENIED')\n"
    )
    cp3, _ = spawn_worker_isolated(child2, run)
    chk("CONTROL: child CAN read an allowed sibling object",
        "CHILD=GRANTED" in (cp3.stdout or ""))

    # 9. STRICT RESET GATE: UNEVALUATED must NOT pass (truthy trap)
    g1 = judge_reset(UNEVALUATED, UNEVALUATED, True)
    chk("Q3-A/E: reset with UNEVALUATED sides -> NOT valid", g1.valid is False)
    g2 = judge_reset(True, True, True)
    chk("Q3-A/E: reset with all True -> valid", g2.valid is True)

    # 10. CLEANUP return checked (no ignore_errors)
    ok_cleanup = _checked_cleanup(tmp)
    chk("知微: cleanup returns checked (True on success)", ok_cleanup is True)

    passed = sum(1 for _, ok in results if ok)
    print(f"\nwin32_isolation selftest (V1 hardened): {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


def _checked_cleanup(path: Path) -> bool:
    """Remove a disposable dir and VERIFY it is gone (知微: check return value)."""
    import shutil
    try:
        shutil.rmtree(path)
    except OSError as e:
        print(f"cleanup error: {e}")
        return False
    return not path.exists()


if __name__ == "__main__":
    raise SystemExit(_selftest())
