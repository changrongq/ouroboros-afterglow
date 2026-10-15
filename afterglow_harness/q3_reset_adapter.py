"""Q3 reset adapter — INTEGRATION layer (isolated prototype; NOT wired to scientific entry).

Lineage: Q3_RESET_ADAPTER_INTEGRATION_V1  (SEPARATE from RC11 and the frozen Q3 roles).

What this module IS:
  · the single authoritative *integration* adjudicator `run_reset_transaction()`
    that produces the ONLY integration-success result, combining:
        V_Q3 ∧ V_real-reset ∧ V_business-worker ∧ V_persistent-isolation ∧ V_RC11 ∧ V_binding
  · a `BusinessWorkerSupervisor` that really starts / holds / OS-verifies / terminates
    a PERSISTENT business worker (never the short-lived Q3 probe).

What this module is NOT:
  · it does NOT modify `reset.py` (RC11, FROZEN) or the 10 frozen Q3 roles;
  · it is NOT wired to any scientific execution entry (REAL_EXECUTION_WIRING = NOT AUTHORIZED);
  · it does NOT let a mock return True stand in for real OS evidence.

Design authority: 凌翼 LINGYI Q3 RESET ADAPTER V3 REVIEW (2026-10-13):
  DESIGN_V3 = ACCEPTED AS PROTOTYPE BASELINE;
  5 implementation constraints: durable-boundary-before-business-execution,
  hook-results-actually-consumed, trusted-snapshot-and-pid-binding,
  single-failure-contract, idempotent-cleanup.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from reset import ResetController, NotIsolatedError, ResetOutcome
from harness_constants import HarnessError, StateSnapshot, LITERAL_SIZE, SUBSTRATE_SIZE
from q3_contract import RESET_MODE_REAL_RESET

# Frozen Q3 chain + the OS-level primitives we build on (read-only use).
from q3_reset_chain import (
    q3_reset_chain, ResetChainResult, process_token_sid, _sid_for_account,
)
from win32_isolation import (
    bind_object_identity, identity_still_matches,
    deny_read_for_sid, save_dacl, restore_dacl,
    start_run, probe_read_access, _process_times,
)
from q3_handle_audit import (
    file_identity, audit_process_handles_for_target,
    HANDLE_AUDIT_CLEAN, HANDLE_AUDIT_FOUND_TARGET, HANDLE_AUDIT_UNRESOLVED,
    HANDLE_AUDIT_ERROR,
)


INTEGRATION_LINEAGE = "Q3_RESET_ADAPTER_INTEGRATION_V1"

# -- transaction states: DONE is the FINAL state; the rest are intermediate ----
TX_NEW = "NEW"
TX_Q3_OK = "Q3_OK"                       # intermediate — NEVER a success state
TX_BOUNDARY_OK = "BOUNDARY_OK"           # durable boundary built + proven
TX_WORKER_OK = "WORKER_OK"               # real worker started (task NOT begun)
TX_ISOLATION_OK = "ISOLATION_OK"         # worker denied on the durable boundary
TX_RC11_OK = "RC11_OK"                   # frozen verify() said RESET_VALID
TX_RELEASED = "RELEASED"                 # business release ACKed (ALL gates passed)
TX_DONE = "DONE"                         # FINAL success — set ONLY in run_reset_transaction
TX_FAILED = "FAILED"                     # terminal failure
TX_CLOSED = "CLOSED"                     # cleaned up (idempotent)

_TERMINAL = frozenset({TX_DONE, TX_FAILED, TX_CLOSED})
# The ONLY states from which a fresh transaction may begin (single-use).
_STARTABLE = frozenset({TX_NEW})


# ===========================================================================
#  Business worker supervisor  (凌翼 I-1 / Q4)
# ===========================================================================
@dataclass
class BusinessWorkerWitness:
    """OS-read evidence that a PERSISTENT business worker exists and is bound.

    Every field is read from the OS / real process — NOT copied from a caller's
    boolean. `witness_ok` is the strict conjunction the adjudicator consumes.
    """
    pid: int
    token_sid: str
    account: str
    create_time: float
    entry_sha256: str                 # hash of the business entry actually running
    create_api: str
    started_and_holding: bool         # true: process is alive but has NOT begun real work
    ready_seen: bool = False          # READY_HOLDING handshake observed for THIS pid
    ready_pid: int | None = None      # pid the READY file reported
    detail: str = ""

    @property
    def witness_ok(self) -> bool:
        # A boolean "started_and_holding" plus an OS-read pid + create_time + entry hash
        # AND a consumed READY handshake bound to THIS pid (凌翼 R3 / 知微 ZW-02).
        return (isinstance(self.pid, int) and self.pid > 0
                and self.create_time > 0.0
                and bool(self.entry_sha256)
                and self.started_and_holding is True
                and self.ready_seen is True
                and self.ready_pid == self.pid)


@dataclass
class WorkerAccessWitness:
    """A trusted, controller-corroborated access witness for the REAL business worker.

    凌翼 R2: a worker self-report is NOT sufficient. This binds: the request nonce,
    the target object (path + OS identity), the worker pid/sid/create_time, the raw
    worker verdict, AND the controller's independent corroboration
    (probe_read_access seal from the CONTROLLER's own read + handle audit status).
    """
    request_nonce: str
    op: str
    target_path: str
    target_os_identity: tuple | None
    worker_pid: int
    worker_sid: str
    worker_create_time: float
    worker_reported: str              # raw string the worker wrote
    controller_seal_ok: bool          # controller-side probe_read_access produced a sealed denial
    controller_verdict: str           # controller-side observed verdict on the SAME object
    handle_audit_status: str          # HANDLE_AUDIT_* for THIS worker + target
    detail: str = ""

    @property
    def proven(self) -> bool:
        """Strict (凌翼 R2): the CONTROLLER's independent handle audit for THIS worker
        + the REAL target is exactly CLEAN. That is the necessary, non-substitutable
        condition (凌翼: WORKER_SELF_REPORT IS NOT INDEPENDENT OS EVIDENCE).

        The worker's self-reported attempt is kept ONLY as a CONSISTENCY CROSS-CHECK:
        a non-DENIED self-report can VETO (fail-closed), but a DENIED self-report can
        NOT establish the proof on its own. `controller_seal_ok` is NOT part of the
        success predicate (it is not a real independent seal — 睫第202句)."""
        # necessary: controller-side handle audit CLEAN (UNRESOLVED/ERROR/FOUND != CLEAN)
        if self.handle_audit_status != HANDLE_AUDIT_CLEAN:
            return False
        # necessary: the observed target identity is bound
        if self.target_os_identity is None:
            return False
        # consistency cross-check (veto only): a non-DENIED self-report fails closed,
        # but a DENIED self-report does not by itself satisfy the proof.
        if self.worker_reported != "DENIED":
            return False
        return True


class BusinessWorkerSupervisor:
    """Real OS owner of the PERSISTENT business worker lifecycle.

    凌翼 Q4: "must really hold & verify OS process identity, lifecycle and
    resources; must NOT declare a worker qualified merely because it received
    identity_bound=True". Therefore the supervisor reads the OS itself.

    凌翼 constraint #1: the durable boundary is established BEFORE business
    execution; the worker is started but HELD (task not begun) until the
    boundary is proven, then released.

    Constraint #5 / 凌翼 R-CLEANUP: terminate() separates TERMINATION_REQUESTED
    from EXIT_CONFIRMED; it never drops the only process handle while the process
    may still be alive, and never claims cleanup done without confirming exit.
    """

    def __init__(self, *, account: str, entry_script: Path, work_dir: Path,
                 python_exe: str | None = None, password: str | None = None,
                 expected_entry_sha256: str | None = None):
        self.account = account
        self.entry_script = Path(entry_script)
        self.work_dir = Path(work_dir)
        self.python_exe = python_exe or _direct_interpreter()
        # password is REQUIRED to create the worker under a DIFFERENT account; a
        # same-account child is NOT a real isolation subject (see start_...).
        self.password = password if password is not None else os.environ.get(
            "AFTERGLOW_WORKER_PASSWORD")
        # 凌翼 R3: the prespawn, TRUSTED entry identity (bytes) the worker must run.
        self.expected_entry_sha256 = expected_entry_sha256
        self._proc: subprocess.Popen | None = None
        self._handle = None                  # OS process handle (cross-account path)
        self._witness: BusinessWorkerWitness | None = None
        self._released = False
        self._release_token = ""
        self._ready_file = self.work_dir / ".afterglow_worker_ready"
        # 知微 D2-04: the supervisor owns its OWN audit dict (it is a different class
        # from Q3ResetAdapter, which has its own `_audit`). Failure exits must not
        # reference an attribute that does not exist here.
        self.audit: dict = {}

    # ---- start (but do not let the worker process real input yet) ----------
    def start_business_worker_holding(self) -> BusinessWorkerWitness:
        if self._proc is not None or self._handle is not None:
            raise NotIsolatedError("business worker already started (supervisor single-use)")
        if not self.entry_script.is_file():
            raise NotIsolatedError(f"business entry not found: {self.entry_script}")
        entry_sha = _sha256_file(self.entry_script)
        # 凌翼 R3: refuse if the entry bytes do not match the prespawn trusted identity.
        if self.expected_entry_sha256 is not None and entry_sha != self.expected_entry_sha256:
            raise NotIsolatedError(
                f"business entry identity mismatch: {entry_sha} != "
                f"{self.expected_entry_sha256} (prespawn trusted identity)")
        self._release_token = uuid.uuid4().hex
        # clear any stale READY file so we only accept THIS run's handshake
        try:
            if self._ready_file.exists():
                self._ready_file.unlink()
        except OSError as e:
            raise NotIsolatedError(f"cannot clear stale READY file: {e}") from e

        if self.password:
            pid, handle, create_time = self._start_cross_account_holding(entry_sha)
            create_api = "CreateProcessWithLogonW"
        else:
            raise NotIsolatedError(
                "no worker password: a same-account child is NOT a real isolation "
                "subject. Set AFTERGLOW_WORKER_PASSWORD (env) — refusing to fake "
                "cross-account isolation (凌翼 I-2).")

        sid = _process_token_sid(pid)
        if not sid:
            # fail closed: without the worker's real token SID we cannot prove isolation
            self._confirmed_exit_or_raise("cannot read business worker token SID")
        # 凌翼 R3: consume the READY handshake bound to THIS pid BEFORE anything else.
        ready_pid = self._await_ready(pid)
        witness = BusinessWorkerWitness(
            pid=pid, token_sid=sid, account=self.account,
            create_time=create_time or 0.0, entry_sha256=entry_sha,
            create_api=create_api, started_and_holding=True,
            ready_seen=True, ready_pid=ready_pid,
            detail="started holding; READY consumed; awaiting isolation verification")
        self._witness = witness
        return witness

    def _await_ready(self, pid: int, timeout: float = 30.0) -> int:
        """Wait for the worker's READY_HOLDING handshake; return the pid it reported.
        Fail-closed on timeout or on a READY whose pid is not THIS process."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._ready_file.exists():
                try:
                    reported = int(self._ready_file.read_text(encoding="ascii").strip())
                except (OSError, ValueError):
                    reported = -1
                if reported != pid:
                    self._confirmed_exit_or_raise(
                        f"READY reported pid {reported} != worker pid {pid}")
                return reported
            if self._process_gone(pid):
                raise NotIsolatedError("worker exited before signalling READY (fail-closed)")
            time.sleep(0.03)
        self._confirmed_exit_or_raise("worker READY handshake timed out")

    def _start_cross_account_holding(self, entry_sha: str) -> tuple[int, object, float | None]:
        """Create the worker under a DIFFERENT account via CreateProcessWithLogonW,
        with a private logon session (LOGON_WITH_PROFILE), no inherited handles.

        The worker is started with --holding so it signals READY and WAITS for the
        release token before touching real input (凌翼 constraint #1)."""
        import ctypes
        from ctypes import wintypes
        adv = ctypes.windll.advapi32
        k32 = ctypes.windll.kernel32
        adv.CreateProcessWithLogonW.restype = wintypes.BOOL
        adv.CreateProcessWithLogonW.argtypes = [
            wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD, ctypes.c_void_p,
            wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p]

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
        pi = PROCESS_INFORMATION()
        LOGON_WITH_PROFILE = 0x00000001
        CREATE_NO_WINDOW = 0x08000000
        cmd = ctypes.create_unicode_buffer(
            f'"{self.python_exe}" "{self.entry_script}" --work-dir "{self.work_dir}" '
            f'--holding --release-token {self._release_token}')
        ok = adv.CreateProcessWithLogonW(self.account, ".", self.password or "",
                                         LOGON_WITH_PROFILE, None, cmd,
                                         CREATE_NO_WINDOW, None, str(self.work_dir),
                                         ctypes.byref(si), ctypes.byref(pi))
        if not ok:
            raise NotIsolatedError(
                f"CreateProcessWithLogonW failed: err={k32.GetLastError()}")
        self._handle = pi.hProcess
        # keep the thread handle closed; keep the process handle for lifecycle
        try:
            k32.CloseHandle(pi.hThread)
        except Exception:                                        # noqa: BLE001
            pass
        create_time, _ = _process_times(pi.dwProcessId)
        return pi.dwProcessId, pi.hProcess, create_time

    def _process_gone(self, pid: int) -> bool:
        """Liveness via the OWNED handle first (cross-account OpenProcess by pid can
        fail with access-denied, which must NOT be read as 'exited')."""
        if self._handle is not None:
            import ctypes
            from ctypes import wintypes
            k32 = ctypes.windll.kernel32
            k32.WaitForSingleObject.restype = wintypes.DWORD
            k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            WAIT_OBJECT_0 = 0x00000000
            WAIT_TIMEOUT = 0x00000102
            rc = k32.WaitForSingleObject(self._handle, 0)
            # signaled (WAIT_OBJECT_0) => exited; still alive => not gone
            if rc == WAIT_OBJECT_0:
                return True
            if rc == WAIT_TIMEOUT:
                return False
        create_now, exit_now = _process_times(pid)
        # only claim gone when we positively observe an exit time; an unreadable
        # (access-denied) process is NOT treated as gone.
        if create_now is None:
            return False
        return bool(exit_now)

    def witness(self) -> BusinessWorkerWitness | None:
        return self._witness

    def witness_ok(self, w: BusinessWorkerWitness | None = None) -> bool:
        w = w if w is not None else self._witness
        if w is None or not w.witness_ok:
            return False
        # Reject a same-account worker: identity must DIFFER from the controller
        # (otherwise it is not a real isolation subject — 凌翼 I-2).
        try:
            from q3_reset_chain import current_process_sid
            if w.token_sid == current_process_sid():
                return False
        except Exception:                                        # noqa: BLE001
            return False
        # Cross-check the process is STILL the same live OS process. Use the OWNED
        # handle when we have one (cross-account OpenProcess-by-pid can be denied,
        # which must not be read as 'dead'). Fall back to create_time match.
        if self._handle is not None:
            return not self._process_gone(w.pid)
        try:
            create_now, exit_now = _process_times(w.pid)
        except Exception:                                        # noqa: BLE001
            return False
        if create_now is None or exit_now:
            return False
        return abs(create_now - w.create_time) < 1e-6

    # ---- release the worker into real business execution -------------------
    def release_into_execution(self) -> None:
        """Hand the release token AND require an explicit business ACK (凌翼:
        VERIFY_RELEASE_ACK). A missing/foreign ACK is a failure, not a success."""
        if self._proc is None and self._handle is None:
            raise NotIsolatedError("release before start")
        if self._released:
            raise NotIsolatedError("double release")
        self._released = True
        ack_file = self.work_dir / ".afterglow_release_ack"
        try:
            if ack_file.exists():
                ack_file.unlink()
            token_file = self.work_dir / ".afterglow_release"
            token_file.write_text(self._release_token, encoding="ascii")
        except OSError as e:
            raise NotIsolatedError(f"release token write failed: {e}") from e
        # await ACK bound to THIS pid + THIS token
        deadline = time.monotonic() + 30.0
        pid = self._witness.pid if self._witness else -1
        while time.monotonic() < deadline:
            if ack_file.exists():
                try:
                    body = json.loads(ack_file.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    raise NotIsolatedError("release ACK unreadable/corrupt")
                if body.get("pid") == pid and body.get("token") == self._release_token:
                    self._release_acked = True
                    return
                raise NotIsolatedError(
                    f"release ACK mismatch: pid={body.get('pid')} token={body.get('token')!r}")
            if self._worker_exited():
                raise NotIsolatedError("worker exited before ACKing release")
            time.sleep(0.03)
        raise NotIsolatedError("release ACK timed out (fail-closed)")

    # ---- trusted access witness ON THE REAL BUSINESS WORKER (凌翼 R2) --------
    def prove_persistent_isolation(self, target_path: Path) -> WorkerAccessWitness:
        """Prove the REAL business worker is denied reading `target_path`, with a
        CONTROLLER-corroborated witness (凌翼 R2).

        Requires ALL of:
          1. a bound real access attempt BY the worker (nonce + pid + target),
          2. the CONTROLLER's own independent sealed denial on the SAME object
             (probe_read_access) — the controller corroborates, it does not replace,
          3. a handle audit for THIS worker + target that is exactly HANDLE_AUDIT_CLEAN.
        The worker self-report alone is NOT sufficient (self-report is a consistency
        cross-check only).

        NOTE: this function does NOT install the boundary. Installing the boundary and
        observing it are SEPARATE stages (凌翼: 安装边界与观察边界要分开) — the boundary
        must already be in place from _stage_boundary before this runs.
        """
        if (self._proc is None and self._handle is None) or self._witness is None:
            raise NotIsolatedError("isolation check before worker start")
        w = self._witness
        if not w.token_sid:
            raise NotIsolatedError("business worker SID unknown; cannot prove isolation")

        target = Path(target_path)
        target_id = file_identity(target)          # OS identity of the observed target
        if target_id is None:
            raise NotIsolatedError(f"target OS identity unreadable: {target}")
        nonce = uuid.uuid4().hex

        # (1) bound access attempt BY the worker (its own raw evidence)
        worker_reported = self._ask_worker_to_attempt_read(target, nonce, w)

        # (2) CONTROLLER-side corroboration = a handle audit for THIS worker + the REAL
        #     target (凌翼 R2: the controller's independent contribution is the handle
        #     audit + identity binding — NOT its own read, which a privileged
        #     controller would always 'succeed').
        try:
            hres = audit_process_handles_for_target(w.pid, str(target.resolve()))
            handle_status = getattr(hres, "status", HANDLE_AUDIT_ERROR)
        except Exception:                                        # noqa: BLE001
            handle_status = HANDLE_AUDIT_ERROR

        return WorkerAccessWitness(
            request_nonce=nonce, op="READ", target_path=str(target.resolve()),
            target_os_identity=target_id, worker_pid=w.pid, worker_sid=w.token_sid,
            worker_create_time=w.create_time, worker_reported=worker_reported,
            # 凌翼 R2 / 睫第202句: we did NOT run any controller-side read (a privileged
            # controller's read would be a cannot-fail check => wall-door). The
            # controller's REAL independent contribution is the handle audit below.
            controller_seal_ok=False,                    # not a real independent seal
            controller_verdict="HANDLE_AUDIT",           # controller's actual contribution
            handle_audit_status=handle_status,
            detail=f"worker_self_report={worker_reported} (consistency only) "
                   f"handle_audit={handle_status} target={target_id}")

    def _ask_worker_to_attempt_read(self, path: Path, nonce: str,
                                    w: BusinessWorkerWitness) -> str:
        """Have the live worker attempt the read; accept its response ONLY if it is
        bound to THIS nonce + THIS worker pid (凌翼 R2 / 知微 ZW-01)."""
        req = self.work_dir / ".afterglow_access_request.json"
        resp = self.work_dir / ".afterglow_access_response.json"
        try:
            if resp.exists():
                resp.unlink()
            req.write_text(json.dumps({
                "op": "READ", "path": str(Path(path).resolve()), "nonce": nonce}),
                encoding="utf-8")
        except OSError as e:
            raise NotIsolatedError(f"access request write failed: {e}") from e
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            if resp.exists():
                try:
                    data = json.loads(resp.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    return "ERROR:CORRUPT"
                # binding checks: the response must echo THIS nonce and THIS pid
                if data.get("nonce") != nonce:
                    return "ERROR:NONCE_MISMATCH"
                if data.get("pid") != w.pid:
                    return "ERROR:PID_MISMATCH"
                return str(data.get("result", "ERROR"))
            if self._worker_exited():
                return "WORKER_EXITED"
            time.sleep(0.05)
        return "TIMEOUT"

    def _worker_exited(self) -> bool:
        """True if the business worker process is no longer running."""
        if self._proc is not None:
            return self._proc.poll() is not None
        if self._witness is not None:
            return self._process_gone(self._witness.pid)
        return True

    def _confirmed_exit_or_raise(self, msg: str) -> "NoReturn":  # noqa: F821
        """Terminate + confirm exit, THEN RAISE the original failure, preserving the
        original reason (知微 ZW-R2-06 / D2-04). This is a failure exit: it ALWAYS
        raises after cleanup. The cleanup status is recorded on the SUPERVISOR's own
        audit (this class has no `_audit` of the adapter — D2-04)."""
        try:
            status = self.terminate()
        except Exception as e:                                   # noqa: BLE001
            self.audit["terminate_error"] = f"{type(e).__name__}: {e}"
            status = "ERROR"
        self.audit["terminate_status"] = status
        raise NotIsolatedError(f"{msg} (cleanup status={status})")

    # ---- idempotent terminate: REQUESTED vs EXIT_CONFIRMED (凌翼 R-CLEANUP) --
    def terminate(self) -> str:
        """Returns 'EXIT_CONFIRMED' | 'NOT_STARTED' | 'STILL_ALIVE' | 'ERROR:...'.

        Idempotent. NEVER drops the only process handle while the process may be
        alive: the handle is closed only after exit is confirmed (or re-opened by
        pid for a liveness re-check when we no longer hold a handle)."""
        if self._proc is None and self._handle is None:
            return "NOT_STARTED"
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        k32.TerminateProcess.restype = wintypes.BOOL
        k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        k32.WaitForSingleObject.restype = wintypes.DWORD
        k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        k32.GetExitCodeProcess.restype = wintypes.BOOL
        k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        k32.CloseHandle.restype = wintypes.BOOL
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        WAIT_OBJECT_0 = 0x00000000
        WAIT_TIMEOUT = 0x00000102
        STILL_ACTIVE = 259
        pid = self._witness.pid if self._witness else None

        if self._handle is not None:
            # cross-account path: terminate via the held handle, then CONFIRM exit.
            # 凌翼 TERMINATE_WIN32_RESULTS: a FAILED OS call is NOT exit evidence.
            try:
                code = wintypes.DWORD(0)
                got1 = k32.GetExitCodeProcess(self._handle, ctypes.byref(code))
                if not got1:
                    # cannot even query: keep the handle, report honest failure
                    return f"ERROR:GetExitCodeProcess1:{k32.GetLastError()}"
                if code.value == STILL_ACTIVE:
                    k32.TerminateProcess(self._handle, 1)      # TERMINATION_REQUESTED
                wait_rc = k32.WaitForSingleObject(self._handle, 10000)
                # EXIT_CONFIRMED requires WAIT_OBJECT_0 (signaled) AND a readable
                # exit code that is NOT STILL_ACTIVE. Anything else => not confirmed.
                if wait_rc == WAIT_TIMEOUT:
                    return "STILL_ALIVE"                        # keep handle
                if wait_rc != WAIT_OBJECT_0:
                    return f"ERROR:WaitForSingleObject:{wait_rc}"   # WAIT_FAILED etc.
                code2 = wintypes.DWORD(0)
                if not k32.GetExitCodeProcess(self._handle, ctypes.byref(code2)):
                    return f"ERROR:GetExitCodeProcess2:{k32.GetLastError()}"
                if code2.value == STILL_ACTIVE:
                    return "STILL_ALIVE"                        # keep handle for retry
                if not k32.CloseHandle(self._handle):
                    # exit confirmed but handle close failed: report but do not claim
                    # the handle is gone.
                    return f"ERROR:CloseHandle:{k32.GetLastError()}"
                self._handle = None
            except Exception as e:                               # noqa: BLE001
                return f"ERROR:{type(e).__name__}:{e}"
            return "EXIT_CONFIRMED"

        # same-account (subprocess.Popen) path — used only where cross-account is N/A
        if self._proc.poll() is None:
            try:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
                    self._proc.wait(timeout=10)
            except OSError as e:
                return f"ERROR:{type(e).__name__}"
        if self._proc.poll() is None:
            return "STILL_ALIVE"
        for stream in (self._proc.stdout, self._proc.stderr):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass
        return "EXIT_CONFIRMED"


# ===========================================================================
#  Integration outcome  (the ONLY success verdict of the integration layer)
# ===========================================================================
@dataclass
class IntegrationOutcome:
    integration_valid: bool
    reason: str
    transaction_id: str
    state: str
    q3_result: ResetChainResult | None = None
    rc11_outcome: ResetOutcome | None = None
    worker_witness: BusinessWorkerWitness | None = None
    bindings: dict = field(default_factory=dict)
    audit: dict = field(default_factory=dict)
    stage_events: list = field(default_factory=list)   # ordered [(stage, what), ...]


# ===========================================================================
#  The adapter + the single authoritative adjudicator
# ===========================================================================
class Q3ResetAdapter(ResetController):
    """ResetController whose hooks are backed by ONE frozen-Q3 transaction.

    `run_reset_transaction()` is the ONLY place allowed to set TX_DONE (= integration
    success). reset.py is FROZEN and untouched; this subclass supplies the hooks a
    real deployment must override.
    """

    def __init__(self, *, account: str, password: str, work_dir: Path,
                 protected: Path, literal_path: Path, substrate_path: Path,
                 python_exe: str, clear_targets_by_category: dict,
                 expected_sid: str, transaction_id: str,
                 supervisor: BusinessWorkerSupervisor,
                 forbidden_path: Path,
                 old_worker_pid: int | None = None,
                 terminate_old_worker=None, clear_action=None,
                 proving_real_replacement: bool = True,
                 run_nonce: str | None = None):
        super().__init__(literal_path, substrate_path)

        # --- constraint #3: bind protected <-> substrate as the SAME real object ---
        self._assert_protected_is_substrate(protected, substrate_path)
        self._protected = Path(protected)
        # literal_path is preserved SEPARATELY (its own object) — kept on the base.
        self._literal_path = Path(literal_path)

        self._account = account
        self._password = password
        self._work_dir = Path(work_dir)
        self._python_exe = python_exe
        self._clear = clear_targets_by_category
        self._transaction_id = transaction_id
        self._supervisor = supervisor
        self._forbidden_path = Path(forbidden_path)
        self._old_worker_pid = old_worker_pid
        self._terminate_old_worker = terminate_old_worker
        self._clear_action = clear_action
        self._proving_real_replacement = proving_real_replacement
        self._probe_nonce = run_nonce or start_run()

        # 凌翼 R3 (PRESPAWN_ACCOUNT_SID_RESOLUTION): the isolation boundary SID is
        # NOT taken from the caller's `expected_sid` string. It is resolved by the
        # TRUSTED controller from the ACCOUNT via the OS (LookupAccountNameW), once,
        # BEFORE any boundary is installed. `expected_sid` (if given) is only a hint
        # that must MATCH the OS resolution.
        try:
            self._resolved_account_sid = _sid_for_account(account)
        except Exception as e:                                   # noqa: BLE001
            raise NotIsolatedError(
                f"cannot resolve account {account!r} to a SID (fail-closed): {e}") from e
        if expected_sid is not None and expected_sid != self._resolved_account_sid:
            raise NotIsolatedError(
                f"expected_sid {expected_sid!r} != OS-resolved account SID "
                f"{self._resolved_account_sid!r} (prespawn account SID resolution)")
        # Backwards-compatible attribute name used by callers/tests.
        self._expected_sid = self._resolved_account_sid

        self._state = TX_NEW
        self._fail_reason: str | None = None
        self._r: ResetChainResult | None = None
        self._rc11: ResetOutcome | None = None
        self._witness: BusinessWorkerWitness | None = None
        self._access_witness: WorkerAccessWitness | None = None
        self._boundary_saved: str | None = None
        self._bindings: dict = {}
        self._cleaned = False
        self._audit: dict = {}
        # 知微 D2-05: an ordered log of stage events, so a test can prove each stage
        # ACTUALLY RAN (not back-filled by a later stage). e.g. a no-op boundary would
        # leave no "boundary:installed" event => detectable.
        self._stage_events: list[tuple[str, str]] = []

    def _event(self, stage: str, what: str) -> None:
        self._stage_events.append((stage, what))

    # -- constraint #3: OS file identity (not merely normalized string) ------
    @staticmethod
    def _assert_protected_is_substrate(protected: Path, substrate_path: Path) -> None:
        """The Q3 `protected` object MUST be the SAME OS file as RC11 `substrate_path`.

        The authority is the OS physical file identity (volume serial + file index,
        which matches across hardlinks / path aliases / case). A string-normalization
        match is NOT proof (two different aliases may or may not be the same file),
        and a string MISMATCH is NOT proof of difference (a hardlink has a different
        path but the same file). Therefore: reject when the OS identities are present
        and differ; if identity cannot be read, fail closed."""
        pp, sp = Path(protected), Path(substrate_path)
        id_p, id_s = file_identity(pp), file_identity(sp)
        if id_p is None or id_s is None:
            # cannot establish OS identity => fail closed (never assume "same").
            raise NotIsolatedError(
                f"PROTECTED<->SUBSTRATE identity unreadable (fail-closed): "
                f"protected={pp} id={id_p} substrate={sp} id={id_s}")
        if id_p != id_s:
            raise NotIsolatedError(
                f"PROTECTED<->SUBSTRATE not the same OS file object: "
                f"protected={pp} id={id_p} substrate={sp} id={id_s}")

    # ------------------------------------------------------------------ state
    @property
    def state(self) -> str:
        return self._state

    def _fail(self, msg: str, exc: BaseException | None = None) -> "NoReturn":  # noqa: F821
        """Single failure contract (constraint #4): set FAILED, cleanup (idempotent),
        then raise the one external error type. Never leaves a live process."""
        self._state = TX_FAILED
        self._fail_reason = msg
        try:
            self._cleanup()
        except Exception as ce:  # cleanup must never mask the failure
            self._audit["cleanup_error"] = f"{type(ce).__name__}: {ce}"
        raise NotIsolatedError(msg) from exc

    def _cleanup(self) -> None:
        """Idempotent (constraint #5) + 凌翼 FAILURE_CLEANUP_ORDER (BLOCKING).

        知微 D2-01: `_cleaned` must NOT conflate two independent facts. Track them
        separately:
          · worker_exit_confirmed  — the business worker is CONFIRMED gone.
          · boundary_restore_confirmed — the original ACL is CONFIRMED restored.
        Cleanup is COMPLETE only when BOTH hold. A failed restore after a confirmed
        exit REMAINS RETRYABLE (restore-only), even though the worker is gone. A
        boundary that was installed but never had a worker may also be rolled back.

        Order: stop the worker + confirm exit FIRST; only THEN restore the ACL.
        """
        # Already fully complete => nothing to do.
        if self._audit.get("cleanup_complete") is True:
            return

        # (0) If we never started a worker, "worker exited" is trivially true.
        worker_started = (self._witness is not None)
        # (1) Worker exit: only re-run if not already confirmed.
        if self._audit.get("worker_exit_confirmed") is not True:
            try:
                status = self._supervisor.terminate()
            except Exception as e:  # noqa: BLE001
                self._audit["terminate_error"] = f"{type(e).__name__}: {e}"
                status = "ERROR"
            self._audit["terminate_status"] = status
            if status == "EXIT_CONFIRMED":
                self._audit["worker_exit_confirmed"] = True
            elif status == "NOT_STARTED":
                # 知微: NOT_STARTED is NOT an exit proof for something that started.
                # If a worker was never started, it is trivially "exited"; else unknown.
                if not worker_started:
                    self._audit["worker_exit_confirmed"] = True
                else:
                    self._audit["worker_exit_confirmed"] = False
            else:
                # STILL_ALIVE / ERROR: keep the boundary; retain control; retryable.
                self._audit["worker_exit_confirmed"] = False

        if self._audit.get("worker_exit_confirmed") is not True:
            # Protect the (possibly) still-live worker: DO NOT restore the boundary.
            self._audit["cleanup_confirmed"] = False
            self._audit["boundary_retained"] = True
            self._cleaned = False                 # retain control; retryable
            if (self._audit.get("terminate_status") == "NOT_STARTED"
                    and self._state == TX_NEW):
                self._state = TX_CLOSED
            else:
                self._state = TX_FAILED
            return

        # (2) Worker exit CONFIRMED -> it is now safe to restore the original ACL.
        if self._audit.get("boundary_restore_confirmed") is not True:
            self._rollback_boundary()
            restored = self._audit.get("boundary_restored")
            if restored is False:
                # exit confirmed but ACL restore NOT confirmed: retry restore-only,
                # DO NOT mark cleanup complete (知微 D2-01: keep it retryable).
                self._audit["cleanup_confirmed"] = False
                self._audit["boundary_restore_pending"] = True
                self._cleaned = False             # still retryable (restore-only)
                if self._state not in (TX_DONE,):
                    self._state = TX_FAILED if self._state != TX_NEW else TX_CLOSED
                return
            self._audit["boundary_restore_confirmed"] = True
            self._audit["boundary_restore_pending"] = False

        # (3) BOTH confirmed => cleanup complete.
        self._audit["cleanup_complete"] = True
        self._audit["cleanup_confirmed"] = True
        self._cleaned = True
        if self._state not in (TX_DONE,):
            self._state = TX_FAILED if self._state != TX_NEW else TX_CLOSED

    # ------------------------------------------------------------------ stages
    def _call_q3_chain(self) -> ResetChainResult:
        """The REAL frozen chain invocation. This is the single seam a test may
        replace to inject a genuine Q3 failure by CHANGING THE INPUTS the chain
        computes from (never by fabricating a passing/failing result object)."""
        return q3_reset_chain(
            account=self._account, password=self._password,
            work_dir=self._work_dir, python_exe=self._python_exe,
            protected=self._protected, run_nonce=self._probe_nonce,
            clear_targets_by_category=self._clear,
            expected_sid=self._expected_sid,
            old_worker_pid=self._old_worker_pid,
            terminate_old_worker=self._terminate_old_worker,
            clear_action=self._clear_action)

    def _stage_q3(self) -> None:
        self._event("q3", "begin")
        if self._state != TX_NEW:
            raise NotIsolatedError(f"transaction not reusable (state={self._state})")
        try:
            r = self._call_q3_chain()
        except Exception as e:                                   # noqa: BLE001
            self._fail(f"Q3 chain raised: {type(e).__name__}: {e}", e)
        self._r = r
        if r.valid is not True:                                  # 睫 191: THE conjunction
            self._fail(f"Q3 not valid: {r.reason}")
        if self._proving_real_replacement:
            if r.reset_mode != RESET_MODE_REAL_RESET:
                self._fail(f"reset_mode={r.reset_mode!r} != REAL_RESET")
            if r.real_reset_required is not True:
                self._fail("real_reset_required is not True")
            if r.real_reset_ok is not True:
                self._fail("real_reset_ok is not True")
        self._state = TX_Q3_OK

    def _stage_boundary(self) -> None:
        """constraint #1 + 凌翼 DACL timing: build the DURABLE isolation boundary
        BEFORE business exec, and SAVE the original DACL BEFORE modifying it.

        The boundary SID is the PRESPAWN OS-resolved account SID (not a caller string).
        The actual ACL primitives go through _save_boundary_dacl / _install_boundary,
        which the logic-layer tests may override (the real layers use the OS)."""
        self._event("boundary", "begin")
        sid = self._resolved_account_sid
        if not sid:
            self._fail("resolved account SID missing: cannot build durable boundary")
        # 凌翼 DACL timing: save the ORIGINAL DACL BEFORE installing the deny ACE.
        self._boundary_saved = self._save_boundary_dacl()
        if not self._boundary_saved:
            self._fail("original DACL save returned empty (fail-closed)")
        try:
            self._install_boundary(sid)
        except Exception as e:                                   # noqa: BLE001
            self._rollback_boundary()
            self._fail(f"durable boundary install failed: {e}", e)
        self._event("boundary", "installed")
        self._state = TX_BOUNDARY_OK

    # -- boundary primitive seams (overridable in the logic layer) -----------
    # 凌翼 R1: the ACL deny, the isolation observation, and the restore MUST all
    # operate on the SAME real protected object. `_boundary_target()` and
    # `_protected_target()` are therefore the same object by construction.
    def _boundary_target(self) -> Path:
        return self._protected_target()

    def _save_boundary_dacl(self) -> str | None:
        return save_dacl(self._boundary_target())

    def _install_boundary(self, sid: str) -> None:
        deny_read_for_sid(self._boundary_target(), sid)

    def _rollback_boundary(self) -> None:
        """Restore the original DACL. CONSUMES the restore result (知微 ZW-R2-02):
        a False / NOT_APPLICABLE / error is recorded, never silently treated as done."""
        if not self._boundary_saved:
            return
        try:
            ok = restore_dacl(self._boundary_target(), self._boundary_saved)
        except Exception as e:                                   # noqa: BLE001
            self._audit["dacl_rollback_error"] = f"{type(e).__name__}: {e}"
            self._audit["boundary_restored"] = False
            return
        self._audit["boundary_restored"] = bool(ok)
        if not ok:
            self._audit["dacl_rollback_error"] = "restore_dacl returned False"

    def _stage_business_worker(self) -> None:
        """Start the PERSISTENT business worker but HOLD it (task not begun).

        凌翼 R3: BEFORE any access/release, verify the worker's REAL token SID equals
        the PRESPAWN OS-resolved account SID. A mismatch fails immediately and closes
        the configuration-vs-observation window (睫第201句)."""
        self._event("worker", "begin")
        try:
            w = self._supervisor.start_business_worker_holding()
        except Exception as e:                                   # noqa: BLE001
            self._fail(f"business worker start failed: {e}", e)
        self._witness = w
        # 睫第201句 / 凌翼 R3: the REAL token SID must equal the prespawn resolved SID.
        if w is None or w.token_sid != self._resolved_account_sid:
            self._fail(f"worker SID {getattr(w, 'token_sid', None)} != "
                       f"prespawn account SID {self._resolved_account_sid}")
        if not self._supervisor.witness_ok(w):
            self._fail("business worker OS witness not established (READY/identity)")
        self._state = TX_WORKER_OK

    def _stage_persistent_isolation(self) -> None:
        """Prove durable isolation ON THE REAL business worker via a CONTROLLER-
        corroborated witness (凌翼 R2). Does NOT install the boundary (that already
        happened in _stage_boundary) and does NOT release the worker (which now
        happens only after ALL gates — see _stage_release)."""
        self._event("isolation", "begin")
        try:
            witness = self._supervisor.prove_persistent_isolation(self._protected_target())
        except Exception as e:                                   # noqa: BLE001
            self._fail(f"persistent isolation proof failed: {e}", e)
        self._access_witness = witness
        if not witness.proven:
            # UNRESOLVED/ERROR handle audit must NOT pass (凌翼 R2: UNRESOLVED != CLEAN)
            self._fail(f"persistent isolation not proven (worker={witness.worker_reported} "
                       f"controller={witness.controller_verdict} "
                       f"handles={witness.handle_audit_status})")
        self._state = TX_ISOLATION_OK

    def _protected_target(self) -> Path:
        """The REAL protected object the isolation proof MUST target (凌翼 R1:
        canary evidence cannot substitute; the first real integration proves the
        protected object itself)."""
        return self._protected

    def _capture_restored_now(self, fallback: StateSnapshot | None) -> StateSnapshot:
        """Capture the restored snapshot at the correct point (after reset, before
        RC11/release). 知微 D2-03. Prefer the controller-supplied provider; a direct
        `restored` arg is used only as a flagged fallback."""
        prov = getattr(self, "_restored_provider", None)
        if prov is not None:
            snap = prov()
            self._audit["restored_capture_timing"] = "provider_after_reset"
        elif fallback is not None:
            snap = fallback
            self._audit["restored_capture_timing"] = "caller_precomputed"
        else:
            self._fail("no restored snapshot: neither provider nor precomputed arg given")
        if not isinstance(snap, StateSnapshot):
            self._fail(f"restored provider returned non-StateSnapshot: {type(snap).__name__}")
        return snap

    def _stage_rc11_verify(self, handoff: StateSnapshot, restored: StateSnapshot) -> None:
        """Frozen reset.py.verify() — an INDEPENDENT necessary condition.

        RC11 access_side_ok is derived from THIS transaction's REAL access witness
        object (凌翼 m1: not a constant bleached through a state check)."""
        self._event("rc11", "begin")
        if self._r is None:
            self._fail("RC11 verify before Q3 result")
        aw = self._access_witness
        rc11_access_ok = bool(aw is not None and aw.proven is True)
        self._rc11 = super().verify(
            handoff, restored,
            clear_side_ok=(self._r.clear_ok is True),
            access_side_ok=rc11_access_ok)
        if self._rc11.reset_valid is not True:
            self._fail(f"RC11 verify not VALID: {self._rc11.reason}")
        self._event("rc11", "verified")
        self._state = TX_RC11_OK

    def _stage_release(self) -> None:
        """凌翼: RELEASE_AFTER_ALL_PREREQUISITE_GATES + VERIFY_RELEASE_ACK. Only after
        Q3, boundary, worker, isolation, RC11 and binding all passed do we let the
        business worker process real input — AND we verify the ACK."""
        self._event("release", "begin")
        try:
            self._supervisor.release_into_execution()
        except Exception as e:                                   # noqa: BLE001
            self._fail(f"worker release failed: {e}", e)
        if not getattr(self._supervisor, "_release_acked", False):
            self._fail("release ACK not confirmed (fail-closed)")
        self._event("release", "acked")
        self._state = TX_RELEASED

    def _stage_bind(self, handoff: StateSnapshot, restored: StateSnapshot) -> None:
        """constraint #3 → 凌翼 R1: bind AND VERIFY (rejecting gate, not just a record).
        Re-reads the OS identity + content binding of the protected/substrate/literal
        objects, and the access target, and FAILS CLOSED on any drift / unreadable /
        substitution. (凌翼: _stage_bind must be a rejecting gate; canary != protected.)"""
        self._event("bind", "begin")
        # -- protected must still be the SAME OS file as substrate (re-check) --
        id_p = file_identity(self._protected)
        id_s = file_identity(self.substrate_path)
        if id_p is None or id_s is None or id_p != id_s:
            self._fail(f"binding recheck: protected/substrate OS identity drifted or "
                       f"unreadable: protected={id_p} substrate={id_s}")
        # -- the access target MUST be the real protected object (凌翼 R1) --
        aw = self._access_witness
        if aw is None or aw.target_os_identity != id_p:
            self._fail(f"binding recheck: isolation was NOT proven on the protected "
                       f"object (target={getattr(aw, 'target_os_identity', None)} != "
                       f"protected={id_p}) — canary evidence cannot substitute")
        # -- literal must still be readable/bound (its own object) --
        id_l = file_identity(self._literal_path)
        if id_l is None:
            self._fail("binding recheck: literal object OS identity unreadable")

        self._bindings = {
            "transaction_id": self._transaction_id,
            "q3_run_nonce": self._probe_nonce,
            "old_worker_pid": self._old_worker_pid,
            "old_worker_pid_authority": "supervisor",   # never the verified party
            "resolved_account_sid": self._resolved_account_sid,
            "protected": str(self._protected),
            "protected_os_identity": id_p,
            "substrate": str(self.substrate_path),
            "substrate_os_identity": id_s,
            "literal": str(self._literal_path),
            "literal_os_identity": id_l,
            "forbidden_canary": str(self._forbidden_path),
            "forbidden_canary_os_identity": file_identity(self._forbidden_path),
            "access_witness_target": aw.target_path,
            "access_witness_nonce": aw.request_nonce,
            "access_witness_handle_status": aw.handle_audit_status,
            "handoff_digest": handoff.digest,
            "restored_digest": restored.digest,
            "restored_capture_timing": self._audit.get("restored_capture_timing"),
            "worker_pid": self._witness.pid if self._witness else None,
            "worker_sid": self._witness.token_sid if self._witness else None,
            "worker_create_time": self._witness.create_time if self._witness else None,
            "worker_entry_sha256": self._witness.entry_sha256 if self._witness else None,
            "q3_result_valid": self._r.valid if self._r else None,
            "q3_reset_mode": self._r.reset_mode if self._r else None,
            "rc11_reset_valid": self._rc11.reset_valid if self._rc11 else None,
        }

    # ---------------------------------------------- the SINGLE adjudicator
    def run_reset_transaction(self, handoff: StateSnapshot,
                              restored: StateSnapshot | None = None,
                              restored_provider=None) -> IntegrationOutcome:
        """The ONLY entry that may produce integration success (TX_DONE).

        Order (凌翼): Q3 → boundary → worker → isolation → [capture restored] → RC11 →
        binding → RELEASE → DONE.

        知微 D2-03: `restored` MUST be captured AFTER the real reset and BEFORE RC11 /
        release. To guarantee ordering, prefer `restored_provider` (a callable the
        controller uses to capture restored from the bound objects at the correct
        moment). Passing `restored` directly is kept for back-compat but is flagged in
        the audit as `restored_capture_timing="caller_precomputed"` (the caller may
        have evaluated it before the reset — D2-03); the fixture entry must use the
        provider form.

        凌翼 constraint #3: the snapshots are captured/verified by the trusted
        controller and bound to this one transaction (provenance recorded in bindings)."""
        self._restored_provider = restored_provider
        self._restored_precomputed = restored is not None
        try:
            self._stage_q3()
            self._stage_boundary()          # durable boundary BEFORE business exec
            self._stage_business_worker()   # worker starts but HOLDS
            self._stage_persistent_isolation()
            # 知微 D2-03: capture restored HERE (after reset/Q3, before RC11/release).
            restored = self._capture_restored_now(restored)
            self._stage_rc11_verify(handoff, restored)
            self._stage_bind(handoff, restored)
            self._stage_release()           # ONLY after ALL prerequisite gates + ACK
        except NotIsolatedError as e:
            # _fail already ran (state=FAILED, cleaned). Return the failure verdict.
            return self._failure_outcome(self._fail_reason or str(e))
        except Exception as e:                                   # noqa: BLE001
            return self._failure_outcome(f"integration raised: {type(e).__name__}: {e}")

        self._state = TX_DONE                                    # FINAL success ONLY here
        return IntegrationOutcome(
            integration_valid=True,
            reason="INTEGRATION_VALID: Q3+real-reset+business-worker+isolation+RC11+binding+release-ack",
            transaction_id=self._transaction_id,
            state=self._state,
            q3_result=self._r, rc11_outcome=self._rc11,
            worker_witness=self._witness, bindings=self._bindings, audit=self._audit,
            stage_events=list(self._stage_events))

    def _failure_outcome(self, reason: str) -> IntegrationOutcome:
        if self._state not in _TERMINAL:
            self._state = TX_FAILED
            try:
                self._cleanup()
            except Exception as ce:                              # noqa: BLE001
                self._audit["cleanup_error"] = f"{type(ce).__name__}: {ce}"
        # 睫: do NOT let a sub-conclusion (RC11 said VALID) sit inside a False verdict
        # as if adopted. If the failure happened after RC11 ran, mark it UNADOPTED
        # explicitly so no downstream reader can mistake the part for the whole.
        unadopted = None
        if self._rc11 is not None and self._rc11.reset_valid is True:
            unadopted = {
                "rc11_outcome_UNADOPTED": True,
                "note": "RC11 verify ran and returned VALID, but the WHOLE integration "
                        "verdict is INVALID (a later gate failed); do NOT consume "
                        "rc11_outcome.reset_valid as a stand-alone pass",
            }
            self._audit.update(unadopted)
        return IntegrationOutcome(
            integration_valid=False, reason=f"INTEGRATION_INVALID: {reason}",
            transaction_id=self._transaction_id, state=self._state,
            q3_result=self._r,
            rc11_outcome=(None if unadopted else self._rc11),   # don't present a
            #   stand-alone VALID rc11 inside a False verdict (睫: unadopted子结论)
            worker_witness=self._witness, bindings=self._bindings, audit=self._audit,
            stage_events=list(self._stage_events))

    # ---------------------------------------------- ResetController hooks
    def restart_worker(self) -> None:
        """Hook: drive the business-worker stage INSIDE the one transaction.

        constraint #2: this hook is NOT bypassed — it advances the SAME transaction
        (shared with run_reset_transaction via the single-use state machine). Calling
        it when the transaction already ran or failed is refused (no stale reuse)."""
        if self._state == TX_NEW:
            # A caller invoking the hook directly gets the full staged flow for the
            # worker portion; the authoritative success gate remains run_reset_transaction.
            raise NotIsolatedError(
                "restart_worker hook must be driven by run_reset_transaction(); "
                "the integration success verdict is produced ONLY there")
        if self._state in _TERMINAL:
            raise NotIsolatedError(f"transaction not reusable (state={self._state})")
        # If we are mid-transaction (invoked by the adjudicator flow), no-op.
        return None

    def access_probe(self) -> bool:
        """Hook: report the CURRENT transaction's access isolation from the REAL
        access witness object — never a fabricated True, never a state constant
        (凌翼 m1). constraint #2: it reflects THIS business worker's denial witness,
        not merely the Q3 probe's."""
        aw = self._access_witness
        return bool(aw is not None and aw.proven is True)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _direct_interpreter() -> str:
    """Resolve a DIRECT Python interpreter for the cross-account worker.

    A uv-created venv's `Scripts\\python.exe` is a 262144-byte REDIRECTOR: it spawns
    the base interpreter as a CHILD and exits, so the pid CreateProcessWithLogonW
    returns is NOT the process that runs the script. That breaks pid/handle binding.
    We therefore launch a real (non-stub) interpreter: AFTERGLOW_PUBLIC_PYTHON if set,
    else the venv's base `home` python from pyvenv.cfg, else sys.executable."""
    env = os.environ.get("AFTERGLOW_PUBLIC_PYTHON")
    if env and Path(env).is_file():
        return env
    try:
        import sys as _sys
        cfg = Path(_sys.executable).resolve().parent.parent / "pyvenv.cfg"
        if cfg.is_file():
            for line in cfg.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip().startswith("home"):
                    home = line.split("=", 1)[1].strip()
                    cand = Path(home) / "python.exe"
                    if cand.is_file():
                        return str(cand)
    except Exception:                                            # noqa: BLE001
        pass
    return sys.executable


def _process_token_sid(pid: int) -> str | None:
    """Read the process token SID from the OS via the frozen Q3 helper.

    An empty/None SID means the supervisor cannot prove isolation, and the
    transaction fails closed (never a silent pass)."""
    try:
        return process_token_sid(pid)
    except Exception:                                            # noqa: BLE001
        return None
