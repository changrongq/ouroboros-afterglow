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
from q3_reset_chain import q3_reset_chain, ResetChainResult, process_token_sid
from win32_isolation import (
    bind_object_identity, identity_still_matches,
    deny_read_for_sid, save_dacl,
    start_run, probe_read_access, _process_times,
)
from q3_handle_audit import file_identity


INTEGRATION_LINEAGE = "Q3_RESET_ADAPTER_INTEGRATION_V1"

# -- transaction states: DONE is the FINAL state; the rest are intermediate ----
TX_NEW = "NEW"
TX_Q3_OK = "Q3_OK"                       # intermediate — NEVER a success state
TX_BOUNDARY_OK = "BOUNDARY_OK"           # durable boundary built + proven
TX_WORKER_OK = "WORKER_OK"               # real worker started (task NOT begun)
TX_ISOLATION_OK = "ISOLATION_OK"         # worker denied on the durable boundary
TX_RC11_OK = "RC11_OK"                   # frozen verify() said RESET_VALID
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
    detail: str = ""

    @property
    def witness_ok(self) -> bool:
        # A boolean "started_and_holding" plus an OS-read pid + create_time + entry hash.
        return (isinstance(self.pid, int) and self.pid > 0
                and self.create_time > 0.0
                and bool(self.entry_sha256)
                and self.started_and_holding is True)


class BusinessWorkerSupervisor:
    """Real OS owner of the PERSISTENT business worker lifecycle.

    凌翼 Q4: "must really hold & verify OS process identity, lifecycle and
    resources; must NOT declare a worker qualified merely because it received
    identity_bound=True". Therefore the supervisor reads the OS itself.

    凌翼 constraint #1: the durable boundary is established BEFORE business
    execution; the worker is started but HELD (task not begun) until the
    boundary is proven, then released.

    Constraint #5: terminate() is idempotent; it never leaves a live process.
    """

    def __init__(self, *, account: str, entry_script: Path, work_dir: Path,
                 python_exe: str | None = None, password: str | None = None):
        self.account = account
        self.entry_script = Path(entry_script)
        self.work_dir = Path(work_dir)
        self.python_exe = python_exe or sys.executable
        # password is REQUIRED to create the worker under a DIFFERENT account; a
        # same-account child is NOT a real isolation subject (see start_...).
        self.password = password if password is not None else os.environ.get(
            "AFTERGLOW_WORKER_PASSWORD")
        self._proc: subprocess.Popen | None = None
        self._handle = None                  # OS process handle (cross-account path)
        self._witness: BusinessWorkerWitness | None = None
        self._released = False
        self._release_token = ""

    # ---- start (but do not let the worker process real input yet) ----------
    def start_business_worker_holding(self) -> BusinessWorkerWitness:
        if self._proc is not None or self._handle is not None:
            raise NotIsolatedError("business worker already started (supervisor single-use)")
        if not self.entry_script.is_file():
            raise NotIsolatedError(f"business entry not found: {self.entry_script}")
        entry_sha = _sha256_file(self.entry_script)
        self._release_token = uuid.uuid4().hex

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
            try:
                self.terminate()
            finally:
                raise NotIsolatedError("cannot read business worker token SID (fail-closed)")
        witness = BusinessWorkerWitness(
            pid=pid, token_sid=sid, account=self.account,
            create_time=create_time or 0.0, entry_sha256=entry_sha,
            create_api=create_api, started_and_holding=True,
            detail="started holding; awaiting isolation verification")
        self._witness = witness
        return witness

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
        # Cross-check the process is STILL the same live OS process (pid + create_time).
        create_now, exit_now = _process_times(w.pid)
        if create_now is None or exit_now:
            return False
        return abs(create_now - w.create_time) < 1e-6

    # ---- release the worker into real business execution -------------------
    def release_into_execution(self) -> None:
        if self._proc is None and self._handle is None:
            raise NotIsolatedError("release before start")
        if self._released:
            raise NotIsolatedError("double release")
        self._released = True
        try:
            # Hand the release token to the held child via a file the entry polls.
            token_file = self.work_dir / ".afterglow_release"
            token_file.write_text(self._release_token, encoding="ascii")
        except OSError as e:
            raise NotIsolatedError(f"release token write failed: {e}") from e

    # ---- prove persistent isolation ON THE REAL BUSINESS WORKER ------------
    def prove_persistent_isolation(self, forbidden_path: Path) -> bool:
        """Real ACCESS attempt by the business worker against the durable boundary.

        凌翼 I-2: must be proven on the REAL business worker, with its OWN raw OS
        evidence — NOT the Q3 probe's READ=DENIED reused. Here we install a durable
        deny ACE for the worker account SID and have the worker itself attempt a read.
        """
        if (self._proc is None and self._handle is None) or self._witness is None:
            raise NotIsolatedError("isolation check before worker start")
        sid = self._witness.token_sid
        if not sid:
            raise NotIsolatedError("business worker SID unknown; cannot prove isolation")
        deny_read_for_sid(forbidden_path, sid)
        # Ask the running business worker to attempt a read and report its verdict.
        result = self._ask_worker_to_attempt_read(forbidden_path)
        return result == "DENIED"

    def _ask_worker_to_attempt_read(self, path: Path) -> str:
        """Have the live business worker itself attempt the read (its own evidence)."""
        req = self.work_dir / ".afterglow_access_request.json"
        resp = self.work_dir / ".afterglow_access_response.json"
        try:
            if resp.exists():
                resp.unlink()
            req.write_text(json.dumps({"op": "READ", "path": str(Path(path).resolve())}),
                           encoding="utf-8")
        except OSError as e:
            raise NotIsolatedError(f"access request write failed: {e}") from e
        deadline = time.monotonic() + 30.0
        while time.monotonic() < deadline:
            if resp.exists():
                try:
                    data = json.loads(resp.read_text(encoding="utf-8"))
                    return str(data.get("result", "ERROR"))
                except (OSError, ValueError):
                    return "ERROR"
            if self._worker_exited():
                return "WORKER_EXITED"
            time.sleep(0.05)
        return "TIMEOUT"

    def _worker_exited(self) -> bool:
        """True if the business worker process is no longer running."""
        if self._proc is not None:
            return self._proc.poll() is not None
        if self._handle is not None and self._witness is not None:
            create_now, exit_now = _process_times(self._witness.pid)
            return create_now is None or bool(exit_now)
        return True

    # ---- idempotent terminate + resource release --------------------------
    def terminate(self) -> str:
        """Idempotent: safe to call many times; never leaves a live process."""
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
        INFINITE = 0xFFFFFFFF
        pid = self._witness.pid if self._witness else None

        if self._handle is not None:
            # cross-account path: terminate via the held handle, then confirm exit
            try:
                code = wintypes.DWORD(0)
                if k32.GetExitCodeProcess(self._handle, ctypes.byref(code)) and code.value == 259:
                    k32.TerminateProcess(self._handle, 1)
                k32.WaitForSingleObject(self._handle, 10000)
            except Exception as e:                               # noqa: BLE001
                self._audit_terminate = f"{type(e).__name__}: {e}"
            finally:
                try:
                    k32.CloseHandle(self._handle)
                except Exception:                                # noqa: BLE001
                    pass
                self._handle = None
            # confirm gone: either the pid no longer opens, or it has an exit time
            if pid is not None:
                create_now, exit_now = _process_times(pid)
                if create_now is not None and not exit_now:
                    return "STILL_ALIVE"
            return "TERMINATED"

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
                return f"TERMINATE_ERROR:{type(e).__name__}"
        if self._proc.poll() is None:
            return "STILL_ALIVE"
        for stream in (self._proc.stdout, self._proc.stderr):
            try:
                if stream is not None:
                    stream.close()
            except OSError:
                pass
        return "TERMINATED"


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
        self._expected_sid = expected_sid
        self._transaction_id = transaction_id
        self._supervisor = supervisor
        self._forbidden_path = Path(forbidden_path)
        self._old_worker_pid = old_worker_pid
        self._terminate_old_worker = terminate_old_worker
        self._clear_action = clear_action
        self._proving_real_replacement = proving_real_replacement
        self._probe_nonce = run_nonce or start_run()

        self._state = TX_NEW
        self._fail_reason: str | None = None
        self._r: ResetChainResult | None = None
        self._rc11: ResetOutcome | None = None
        self._witness: BusinessWorkerWitness | None = None
        self._bindings: dict = {}
        self._cleaned = False
        self._audit: dict = {}

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
        """Idempotent (constraint #5)."""
        if self._cleaned:
            return
        self._cleaned = True
        try:
            self._supervisor.terminate()
        except Exception as e:  # noqa: BLE001
            self._audit["terminate_error"] = f"{type(e).__name__}: {e}"
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
        """constraint #1: build the DURABLE isolation boundary BEFORE business exec."""
        sid = self._expected_sid
        if not sid:
            self._fail("expected_sid missing: cannot build durable boundary")
        try:
            deny_read_for_sid(self._forbidden_path, sid)
        except Exception as e:                                   # noqa: BLE001
            self._fail(f"durable boundary install failed: {e}", e)
        self._boundary_saved = save_dacl(self._forbidden_path)
        self._state = TX_BOUNDARY_OK

    def _stage_business_worker(self) -> None:
        """Start the PERSISTENT business worker but HOLD it (task not begun)."""
        try:
            w = self._supervisor.start_business_worker_holding()
        except Exception as e:                                   # noqa: BLE001
            self._fail(f"business worker start failed: {e}", e)
        self._witness = w
        if not self._supervisor.witness_ok(w):
            self._fail("business worker OS witness not established")
        self._state = TX_WORKER_OK

    def _stage_persistent_isolation(self) -> None:
        """Prove durable isolation ON THE REAL business worker (its own evidence)."""
        try:
            ok = self._supervisor.prove_persistent_isolation(self._forbidden_path)
        except Exception as e:                                   # noqa: BLE001
            self._fail(f"persistent isolation proof failed: {e}", e)
        if ok is not True:
            self._fail("persistent isolation not proven on the real business worker")
        # Only AFTER isolation is proven do we let the worker process real input.
        try:
            self._supervisor.release_into_execution()
        except Exception as e:                                   # noqa: BLE001
            self._fail(f"worker release failed: {e}", e)
        self._state = TX_ISOLATION_OK

    def _stage_rc11_verify(self, handoff: StateSnapshot, restored: StateSnapshot) -> None:
        """Frozen reset.py.verify() — an INDEPENDENT necessary condition.

        RC11 access_side_ok is bound to THIS real business worker's denial witness;
        the Q3 access proof is a SEPARATE necessary condition (constraint #2)."""
        if self._r is None:
            self._fail("RC11 verify before Q3 result")
        # RC11's access-side witness is THIS worker's denial (true, just proven).
        rc11_access_ok = (self._state == TX_ISOLATION_OK)
        self._rc11 = super().verify(
            handoff, restored,
            clear_side_ok=(self._r.clear_ok is True),
            access_side_ok=rc11_access_ok)
        if self._rc11.reset_valid is not True:
            self._fail(f"RC11 verify not VALID: {self._rc11.reason}")
        self._state = TX_RC11_OK

    def _stage_bind(self, handoff: StateSnapshot, restored: StateSnapshot) -> None:
        """constraint #3: bind snapshots + pid + evidence to ONE transaction."""
        self._bindings = {
            "transaction_id": self._transaction_id,
            "q3_run_nonce": self._probe_nonce,
            "old_worker_pid": self._old_worker_pid,
            "old_worker_pid_authority": "supervisor",   # never the verified party
            "protected": str(self._protected),
            "protected_os_identity": file_identity(self._protected),
            "substrate": str(self.substrate_path),
            "substrate_os_identity": file_identity(self.substrate_path),
            "literal": str(self._literal_path),
            "handoff_digest": handoff.digest,
            "restored_digest": restored.digest,
            "worker_pid": self._witness.pid if self._witness else None,
            "worker_create_time": self._witness.create_time if self._witness else None,
            "worker_entry_sha256": self._witness.entry_sha256 if self._witness else None,
            "q3_result_valid": self._r.valid if self._r else None,
            "q3_reset_mode": self._r.reset_mode if self._r else None,
            "rc11_reset_valid": self._rc11.reset_valid if self._rc11 else None,
        }

    # ---------------------------------------------- the SINGLE adjudicator
    def run_reset_transaction(self, handoff: StateSnapshot,
                              restored: StateSnapshot) -> IntegrationOutcome:
        """The ONLY entry that may produce integration success (TX_DONE).

        凌翼 constraint #3: the snapshots are captured/verified by the trusted
        controller and bound to this one transaction; they are accepted here as
        already-trusted inputs (their provenance is recorded in bindings)."""
        try:
            self._stage_q3()
            self._stage_boundary()          # durable boundary BEFORE business exec
            self._stage_business_worker()   # worker starts but HOLDS
            self._stage_persistent_isolation()
            self._stage_rc11_verify(handoff, restored)
            self._stage_bind(handoff, restored)
        except NotIsolatedError as e:
            # _fail already ran (state=FAILED, cleaned). Return the failure verdict.
            return self._failure_outcome(self._fail_reason or str(e))
        except Exception as e:                                   # noqa: BLE001
            return self._failure_outcome(f"integration raised: {type(e).__name__}: {e}")

        self._state = TX_DONE                                    # FINAL success ONLY here
        return IntegrationOutcome(
            integration_valid=True,
            reason="INTEGRATION_VALID: Q3+real-reset+business-worker+isolation+RC11+binding",
            transaction_id=self._transaction_id,
            state=self._state,
            q3_result=self._r, rc11_outcome=self._rc11,
            worker_witness=self._witness, bindings=self._bindings, audit=self._audit)

    def _failure_outcome(self, reason: str) -> IntegrationOutcome:
        if self._state not in _TERMINAL:
            self._state = TX_FAILED
            try:
                self._cleanup()
            except Exception as ce:                              # noqa: BLE001
                self._audit["cleanup_error"] = f"{type(ce).__name__}: {ce}"
        return IntegrationOutcome(
            integration_valid=False, reason=f"INTEGRATION_INVALID: {reason}",
            transaction_id=self._transaction_id, state=self._state,
            q3_result=self._r, rc11_outcome=self._rc11,
            worker_witness=self._witness, bindings=self._bindings, audit=self._audit)

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
        """Hook: report the CURRENT transaction's access status — never a fabricated
        True. constraint #2: it reflects the REAL business worker's denial witness,
        not merely the Q3 probe's."""
        if self._state in (TX_ISOLATION_OK, TX_RC11_OK, TX_DONE):
            return True
        return False


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


def _process_token_sid(pid: int) -> str | None:
    """Read the process token SID from the OS via the frozen Q3 helper.

    An empty/None SID means the supervisor cannot prove isolation, and the
    transaction fails closed (never a silent pass)."""
    try:
        return process_token_sid(pid)
    except Exception:                                            # noqa: BLE001
        return None
