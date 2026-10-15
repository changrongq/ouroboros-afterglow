"""Q3 reset adapter — integration regression tests (isolated prototype).

Lineage: Q3_RESET_ADAPTER_INTEGRATION_V1  (test file; not a frozen role).

THREE TEST LAYERS (凌翼 V3 REVIEW §三):
  A. LOGIC unit tests       — transaction state machine, return-value consumption,
                              exception handling, repeat-call / stale-PASS refusal.
                              (proves: logic;        cannot replace: real isolation)
  B. CONTROLLED Windows     — inject a REAL Q3 failure by changing INPUTS *before*
     negative tests           the frozen chain computes; assert the INTEGRATION
                              adjudicator does not output VALID.
                              (proves: failure propagation; cannot replace: full lifecycle)
  C. REAL business worker   — real replace + SID + entry identity + durable isolation
     integration tests        + failure reclamation.
                              (proves: real isolation; cannot replace: final science auth)

FORBIDDEN (凌翼): using a mock that makes the supervisor return True to declare the
real worker identity/isolation "verified". Layer C does NOT use such a mock.

Run:  python test_q3_reset_adapter.py
Exit: 0 = all layers that could run passed; 2 = some layer SKIPPED (env precondition,
      NOT a pass); 1 = FAIL.
"""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import q3_reset_adapter as A
from harness_constants import StateSnapshot, LITERAL_SIZE, SUBSTRATE_SIZE

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
_results: list[tuple[str, str, str]] = []


def _chk(name: str, cond: bool, detail: str = "") -> bool:
    _results.append((name, PASS if cond else FAIL, detail))
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}  {detail}")
    return cond


def _skip(name: str, detail: str = "") -> None:
    """Record a SKIP into the SAME structured result set so the summary cannot drop it
    (知微 ZW-R2-05: a printed SKIP that never entered _results was silently uncounted)."""
    _results.append((name, SKIP, detail))
    print(f"  [SKIP] {name}  {detail}")


# ===========================================================================
# helpers / fixtures
# ===========================================================================
def _mk_state() -> StateSnapshot:
    return StateSnapshot(literal=b"\x01" * LITERAL_SIZE, q_raw=b"\x00" * SUBSTRATE_SIZE)


class _FakeQ3Result:
    """A minimal stand-in used ONLY in the logic layer where the real chain is not
    invoked. It is NEVER used to claim real OS evidence. It carries EVERY gate field
    so a negative case can break the conjunction at a SPECIFIC gate (睫: 7 names, 1
    case before)."""

    def __init__(self, *, valid=True, reset_mode="REAL_RESET",
                 real_reset_required=True, real_reset_ok=True,
                 clear_ok=True, access_ok=True, reason="ok",
                 handle_ok=True, identity_ok=True, lifecycle_ok=True,
                 matrix_ok=True, dacl_restore_ok=True, preserve_ok=True):
        self.valid = valid
        self.reset_mode = reset_mode
        self.real_reset_required = real_reset_required
        self.real_reset_ok = real_reset_ok
        self.clear_ok = clear_ok
        self.access_ok = access_ok
        self.reason = reason
        self.handle_ok = handle_ok
        self.identity_ok = identity_ok
        self.lifecycle_ok = lifecycle_ok
        self.matrix_ok = matrix_ok
        self.dacl_restore_ok = dacl_restore_ok
        self.preserve_ok = preserve_ok


def _base_adapter(tmp: Path, *, chain_override=None, supervisor=None, **kw):
    """Build an adapter whose Q3 stage is driven by `chain_override` (an injectable
    function) so the LOGIC layer runs without a credential. The REAL layers override
    this to call the genuine chain.

    NOTE (知微 ZW-R2-04): this helper must NOT overwrite files a caller already placed
    (Layer D's pristine fixture). We only CREATE a file if it does not already exist."""
    # logic fixtures need the REAL files to exist so the OS-identity check passes;
    # create them ONLY if absent (never clobber a caller-provided fixture).
    if not (tmp / "protected.bin").exists():
        (tmp / "protected.bin").write_bytes(b"\x00" * SUBSTRATE_SIZE)
    if not (tmp / "literal.bin").exists():
        (tmp / "literal.bin").write_bytes(b"\x00" * LITERAL_SIZE)
    # account SID resolution needs a resolvable account; use the CURRENT user so the
    # logic layer can construct (the isolation claim is the supervisor's, not this).
    import getpass
    acct = os.environ.get("AFTERGLOW_WORKER_ACCOUNT") or getpass.getuser()
    if supervisor is None:
        supervisor = _SwitchSupervisor(tmp, ok=False)   # logic default: NOT ok
    adapter = A.Q3ResetAdapter(
        account=acct, password="x" * 8,
        work_dir=tmp, protected=(tmp / "protected.bin"),
        literal_path=(tmp / "literal.bin"), substrate_path=(tmp / "protected.bin"),
        python_exe=sys.executable, clear_targets_by_category={},
        expected_sid=None,                        # resolved from the account (R3)
        transaction_id=uuid.uuid4().hex,
        supervisor=supervisor,
        forbidden_path=(tmp / "forbidden.bin"),
        **kw)
    if chain_override is not None:
        adapter._call_q3_chain = lambda: chain_override(adapter)  # injection seam
    # logic layer: override the boundary ACL seams so no real ACL privilege is needed;
    # the isolation proof is stubbed via the _SwitchSupervisor (Layer C/D use the real
    # boundary primitives). This keeps the state-machine tests runnable unprivileged.
    if isinstance(supervisor, _SwitchSupervisor):
        adapter._save_boundary_dacl = lambda: "STUBBED-DACL"
        adapter._install_boundary = lambda sid: None
        def _stub_rollback():
            # honors supervisor.fail_restore so D2-01 (restore-pending retry) is testable
            if getattr(supervisor, "fail_restore", False):
                adapter._audit["boundary_restored"] = False
            else:
                adapter._audit["boundary_restored"] = True
        adapter._rollback_boundary = _stub_rollback
        # the switch supervisor's SID must equal the PRESPAWN resolved account SID so
        # the R3 equality gate is satisfied on the success path (unless a test sets a
        # deliberately-different SID, e.g. B4).
        if not supervisor.sid_pinned:
            supervisor.sid = adapter._resolved_account_sid
    return adapter


class _SwitchSupervisor:
    """Logic-layer supervisor with an EXPLICIT ok switch (睫第198句 fix: a恒-False
    supervisor made every downstream gate unreachable). When ok=False it never claims
    real isolation; when ok=True it produces a structurally-valid witness so the
    SUCCESS path can be exercised. This is still a LOGIC double — it is used ONLY in
    Layers A/B, never to claim real OS evidence (Layer D uses the real supervisor)."""

    def __init__(self, work_dir, *, ok: bool, sid: str = "S-1-5-21-0-0-0-2002",
                 entry_sha: str = "deadbeef", sid_pinned: bool = False):
        self.work_dir = Path(work_dir)
        self.ok = ok
        self.sid = sid
        self.sid_pinned = sid_pinned      # True => do NOT auto-align to resolved SID
        self.entry_sha = entry_sha
        self._w = None
        self._terminated = 0
        self._release_acked = False
        self.last_handle_status = A.HANDLE_AUDIT_CLEAN if ok else A.HANDLE_AUDIT_UNRESOLVED
        self.fail_terminate = False       # set by a test to simulate STILL_ALIVE
        self.force_worker_report = None   # set by a test to force the access verdict

    def start_business_worker_holding(self):
        self._w = A.BusinessWorkerWitness(
            pid=4242, token_sid=self.sid, account="w", create_time=123.0,
            entry_sha256=self.entry_sha, create_api="switch",
            started_and_holding=True, ready_seen=True, ready_pid=4242)
        return self._w

    def witness(self):
        return self._w

    def witness_ok(self, w=None):
        return bool(self.ok and self._w is not None and self._w.witness_ok)

    def prove_persistent_isolation(self, target_path):
        target_id = A.file_identity(Path(target_path))
        report = self.force_worker_report or ("DENIED" if self.ok else "GRANTED")
        return A.WorkerAccessWitness(
            request_nonce="n", op="READ", target_path=str(Path(target_path)),
            target_os_identity=target_id, worker_pid=4242, worker_sid=self.sid,
            worker_create_time=123.0,
            worker_reported=report,
            controller_seal_ok=False,
            controller_verdict="HANDLE_AUDIT",
            handle_audit_status=self.last_handle_status)

    def release_into_execution(self):
        self._release_acked = True

    def terminate(self) -> str:
        self._terminated += 1
        if self.fail_terminate:
            return "STILL_ALIVE"          # cleanup NOT confirmed
        return "EXIT_CONFIRMED"


def _grant_worker_write(path: Path) -> None:
    """Grant the worker account modify access to the work dir (OS-level setup).

    The worker must be able to CREATE files here (READY/ACK/response), and the
    controller (us) must keep full control — so we grant both explicitly rather than
    relying on inherited ACEs from an Administrators-owned temp dir."""
    import subprocess, getpass
    acct = os.environ.get("AFTERGLOW_WORKER_ACCOUNT", "afterglow_worker")
    me = os.environ.get("USERNAME") or getpass.getuser()
    for who in (acct, me):
        try:
            subprocess.run(["icacls", str(path), "/grant", f"{who}:(OI)(CI)M"],
                           capture_output=True, text=True)
        except Exception:                                        # noqa: BLE001
            pass


# ===========================================================================
# LAYER A — logic unit tests
# ===========================================================================
def layer_a_logic() -> None:
    print("\n=== LAYER A: logic unit tests ===")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # A0: state names — DONE is terminal; Q3_OK is not a success state.
        _chk("A0 DONE is terminal", "DONE" in A._TERMINAL)
        _chk("A0 Q3_OK is NOT terminal/success",
             A.TX_Q3_OK not in A._TERMINAL and A.TX_Q3_OK != A.TX_DONE)

        # A1: a Q3 result that is not `valid is True` must fail, even if the
        # individual fields look fine -> asserts the CONJUNCTION is consumed.
        def chain_invalid(adapter):
            return _FakeQ3Result(valid=False, reason="forged")
        ad = _base_adapter(tmp, chain_override=chain_invalid)
        out = ad.run_reset_transaction(_mk_state(), _mk_state())
        _chk("A1 invalid Q3 => integration INVALID", out.integration_valid is False,
             out.reason)
        _chk("A1 state is FAILED", ad.state == A.TX_FAILED)

        # A2: valid Q3 but reset_mode != REAL_RESET => must fail (FIRST_START masquerade).
        def chain_first_start(adapter):
            return _FakeQ3Result(valid=True, reset_mode="FIRST_START",
                                 real_reset_required=False, real_reset_ok="UNEVALUATED")
        ad = _base_adapter(tmp, chain_override=chain_first_start)
        out = ad.run_reset_transaction(_mk_state(), _mk_state())
        _chk("A2 FIRST_START while proving real replacement => INVALID",
             out.integration_valid is False, out.reason)
        _chk("A2 failed at the REAL_RESET gate (not earlier)",
             "REAL_RESET" in (out.reason or ""), out.reason)

        # A3: repeat call on a terminal transaction is REFUSED (no stale reuse).
        #      distinguish failure-then-repeat AND success-then-repeat.
        ad = _base_adapter(tmp, chain_override=lambda a: _FakeQ3Result(valid=False))
        ad.run_reset_transaction(_mk_state(), _mk_state())
        out2 = ad.run_reset_transaction(_mk_state(), _mk_state())
        _chk("A3a second call after failure refused / INVALID",
             out2.integration_valid is False, out2.reason)
        sup_ok = _SwitchSupervisor(tmp, ok=True)
        ad = _base_adapter(tmp, chain_override=lambda a: _FakeQ3Result(valid=True),
                           supervisor=sup_ok)
        first = ad.run_reset_transaction(_mk_state(), _mk_state())
        second = ad.run_reset_transaction(_mk_state(), _mk_state())
        _chk("A3b success path reached (assert integration_valid is True)", first.integration_valid is True, first.reason)
        # 睫点1 / 知微 D2-05: "didn't fail" != "was called". Assert EACH stage emitted
        # its OWN ordered event, so silently skipping a stage (e.g. no-op boundary)
        # turns A3b RED.
        _chk("A3b state == TX_DONE", first.state == A.TX_DONE)
        ev = first.stage_events or []
        def _ran(stage, what=None):
            return any(s == stage and (what is None or w == what) for s, w in ev)
        six = (_ran("q3", "begin") and _ran("boundary", "installed")
               and _ran("worker", "begin") and _ran("isolation", "begin")
               and _ran("rc11", "verified") and _ran("bind", "begin")
               and _ran("release", "acked"))
        _chk("A3b six stages each emitted their OWN event (skip a stage => RED)",
             bool(six), f"events={ev}")
        _chk("A3c second call after SUCCESS refused / INVALID",
             second.integration_valid is False, second.reason)

        # A3b-neg (知微 D2-05): if _stage_boundary is a no-op (never emits its event),
        # the success path must NOT still pass. Replace boundary with a no-op that
        # emits nothing, and require integration_valid is False OR the six-stage
        # assertion to fail — i.e. the boundary trace must not be back-filled.
        sup2 = _SwitchSupervisor(tmp, ok=True)
        ad2 = _base_adapter(tmp, supervisor=sup2, chain_override=lambda a: _FakeQ3Result(valid=True))
        ad2._stage_boundary = lambda: None          # no-op boundary (emits no event)
        out2 = ad2.run_reset_transaction(_mk_state(), _mk_state())
        ev2 = out2.stage_events or []
        has_boundary_ev = any(s == "boundary" for s, _ in ev2)
        _chk("A3b-neg no-op boundary => boundary event absent (trace not back-filled)",
             has_boundary_ev is False, f"events={ev2}")

        # A4: exception in the Q3 stage is converged to INVALID (single failure contract).
        def chain_raises(adapter):
            raise RuntimeError("boom")
        ad = _base_adapter(tmp, chain_override=chain_raises)
        out = ad.run_reset_transaction(_mk_state(), _mk_state())
        _chk("A4 Q3 exception => integration INVALID", out.integration_valid is False)
        _chk("A4 state FAILED", ad.state == A.TX_FAILED)

        # A5: cleanup idempotent — assert BOTH the return values AND state (睫: A5 was
        #     name-mismatched before; it only checked tuple[-1]).
        sup = _SwitchSupervisor(tmp, ok=True)
        ad = _base_adapter(tmp, chain_override=lambda a: _FakeQ3Result(valid=False),
                           supervisor=sup)
        ad.run_reset_transaction(_mk_state(), _mk_state())
        n1 = sup._terminated
        ad._cleanup(); ad._cleanup()
        _chk("A5 cleanup idempotent (terminate called once; state stable)",
             sup._terminated == n1 and ad.state == A.TX_FAILED,
             f"terminated={sup._terminated} state={ad.state}")

        # A6: P1-D — cleanup honours the terminate result: a STILL_ALIVE terminate must
        #     NOT be recorded as cleaned, and must be retryable.
        sup = _SwitchSupervisor(tmp, ok=True)
        sup.fail_terminate = True
        ad = _base_adapter(tmp, chain_override=lambda a: _FakeQ3Result(valid=False),
                           supervisor=sup)
        ad.run_reset_transaction(_mk_state(), _mk_state())
        _chk("A6 STILL_ALIVE => cleanup NOT confirmed", ad._audit.get("cleanup_confirmed") is False)
        _chk("A6 not marked cleaned (retryable)", ad._cleaned is False)
        sup.fail_terminate = False
        ad._cleanup()                                   # retry now succeeds
        _chk("A6 retry cleanup confirms exit", ad._cleaned is True)

        # A7 (知微 D2-01): after an EXIT_CONFIRMED, a FAILED ACL restore must remain
        #     RETRYABLE (restore-only) — not locked by _cleaned=True.
        sup = _SwitchSupervisor(tmp, ok=True)
        sup.fail_restore = True
        ad = _base_adapter(tmp, chain_override=lambda a: _FakeQ3Result(valid=False),
                           supervisor=sup)
        ad.run_reset_transaction(_mk_state(), _mk_state())
        _chk("A7 exit confirmed but restore FAILED => cleanup NOT complete",
             ad._audit.get("cleanup_complete") is not True
             and ad._audit.get("boundary_restore_pending") is True, str(ad._audit))
        _chk("A7 still retryable (_cleaned False)", ad._cleaned is False)
        sup.fail_restore = False
        ad._cleanup()                                   # restore-only retry
        _chk("A7 retry restores => cleanup complete",
             ad._audit.get("cleanup_complete") is True
             and ad._audit.get("boundary_restore_confirmed") is True, str(ad._audit))


# ===========================================================================
# LAYER B — controlled negative tests (inject INPUTS before the frozen chain)
# ===========================================================================
def layer_b_controlled() -> None:
    print("\n=== LAYER B: controlled negative tests ===")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "protected.bin").write_bytes(b"\x00" * SUBSTRATE_SIZE)
        (tmp / "literal.bin").write_bytes(b"\x00" * LITERAL_SIZE)
        (tmp / "forbidden.bin").write_bytes(b"secret")
        import getpass
        acct = os.environ.get("AFTERGLOW_WORKER_ACCOUNT") or getpass.getuser()

        # B1: object-mismatch negative — assert the EXCEPTION TYPE is NotIsolatedError
        #     (睫: the old substring assertion accepted any unrelated error) and the
        #     message names the mismatch.
        other = tmp / "different.bin"
        other.write_bytes(b"\x00" * SUBSTRATE_SIZE)
        from reset import NotIsolatedError
        b1_ok = False
        try:
            A.Q3ResetAdapter(
                account=acct, password="p", work_dir=tmp,
                protected=(tmp / "protected.bin"),
                literal_path=(tmp / "literal.bin"),
                substrate_path=other,                       # NOT the same object
                python_exe=sys.executable, clear_targets_by_category={},
                expected_sid=None,
                transaction_id=uuid.uuid4().hex,
                supervisor=_SwitchSupervisor(tmp, ok=True),
                forbidden_path=(tmp / "forbidden.bin"))
        except NotIsolatedError as e:
            b1_ok = "PROTECTED" in str(e).upper() and "SUBSTRATE" in str(e).upper()
        except Exception as e:                              # noqa: BLE001
            b1_ok = False
        _chk("B1 protected<->substrate mismatch => NotIsolatedError", b1_ok)

        # B2: same object via a hardlink alias is ACCEPTED (OS identity, not string).
        #     If os.link is unavailable (Windows privilege), SKIP — do NOT fake.
        alias = tmp / "protected_alias.bin"
        try:
            os.link(tmp / "protected.bin", alias)
            have_link = True
        except OSError:
            have_link = False
        if have_link:
            try:
                A.Q3ResetAdapter(
                    account=acct, password="p", work_dir=tmp,
                    protected=(tmp / "protected.bin"),
                    literal_path=(tmp / "literal.bin"),
                    substrate_path=alias,                   # hardlink => same OS file
                    python_exe=sys.executable, clear_targets_by_category={},
                    expected_sid=None,
                    transaction_id=uuid.uuid4().hex,
                    supervisor=_SwitchSupervisor(tmp, ok=True),
                    forbidden_path=(tmp / "forbidden.bin"))
                _chk("B2 hardlink alias => same OS file => accepted", True)
            except Exception as e:                          # noqa: BLE001
                _chk("B2 hardlink alias => same OS file => accepted", False, str(e))
        else:
            _skip("B2 hardlink alias => same OS file => accepted",
                  "os.link unavailable (privilege) — NOT a pass")

        # B3 (知微 D2-05): the adapter consumes the FROZEN r.valid CONJUNCTION, not the
        # individual gate fields. So this is honestly a COMPARATOR test: for EACH gate
        # broken ALONE, `valid` (the conjunction) is False => the adapter must reject.
        # It is NOT seven independent real-gate traces. Compute `valid` the same way
        # the frozen ResetChainResult.valid does, so the case genuinely varies the gate.
        def _frozen_valid(**fields):
            # mirrors q3_reset_chain.ResetChainResult.valid
            if fields.get("real_reset_required") not in (True, False):
                return False
            gates = [fields.get(k) for k in ("clear_ok", "preserve_ok", "access_ok",
                     "handle_ok", "identity_ok", "lifecycle_ok", "matrix_ok",
                     "dacl_restore_ok")]
            if fields.get("real_reset_required") is True:
                gates.append(fields.get("real_reset_ok"))
            return all(x is True for x in gates)

        base = dict(real_reset_required=True, real_reset_ok=True, clear_ok=True,
                    preserve_ok=True, access_ok=True, handle_ok=True, identity_ok=True,
                    lifecycle_ok=True, matrix_ok=True, dacl_restore_ok=True)
        gates = ["clear_ok", "preserve_ok", "access_ok", "handle_ok", "identity_ok",
                 "lifecycle_ok", "matrix_ok", "dacl_restore_ok", "real_reset_ok"]
        for g in gates:
            fields = dict(base); fields[g] = False
            valid = _frozen_valid(**fields)
            sup = _SwitchSupervisor(tmp, ok=True)
            ad = _base_adapter(tmp, supervisor=sup,
                               chain_override=lambda a, _v=valid: _FakeQ3Result(valid=_v))
            out = ad.run_reset_transaction(_mk_state(), _mk_state())
            _chk(f"B3 gate {g} false => conjunction invalid => integration INVALID",
                 valid is False and out.integration_valid is False, out.reason)

        # B4: a same-account/same-SID worker must be REJECTED (R3 SID equality):
        #     supervisor returns a SID != the prespawn resolved account SID.
        sup = _SwitchSupervisor(tmp, ok=True, sid="S-1-5-21-0-0-0-9999", sid_pinned=True)
        ad = _base_adapter(tmp, supervisor=sup, chain_override=lambda a: _FakeQ3Result(valid=True))
        out = ad.run_reset_transaction(_mk_state(), _mk_state())
        _chk("B4 worker SID != prespawn resolved SID => INVALID",
             out.integration_valid is False and "SID" in (out.reason or "").upper(),
             out.reason)

        # B5: handle audit NOT CLEAN (UNRESOLVED) must NOT pass (凌翼 R2).
        sup = _SwitchSupervisor(tmp, ok=True)
        sup.last_handle_status = A.HANDLE_AUDIT_UNRESOLVED
        ad = _base_adapter(tmp, supervisor=sup, chain_override=lambda a: _FakeQ3Result(valid=True))
        out = ad.run_reset_transaction(_mk_state(), _mk_state())
        _chk("B5 handle audit UNRESOLVED => INVALID (UNRESOLVED != CLEAN)",
             out.integration_valid is False, out.reason)

        # B6: isolation not proven because the worker reported NOT-DENIED (supervisor
        #     ok=True so identity/witness pass, but the access verdict is GRANTED) =>
        #     must fail AT the isolation gate, not earlier.
        sup = _SwitchSupervisor(tmp, ok=True)
        sup.force_worker_report = "GRANTED"       # witness identity OK; access NOT denied
        ad = _base_adapter(tmp, supervisor=sup, chain_override=lambda a: _FakeQ3Result(valid=True))
        out = ad.run_reset_transaction(_mk_state(), _mk_state())
        _chk("B6 worker access NOT denied => INVALID at isolation gate",
             out.integration_valid is False
             and "persistent isolation not proven" in (out.reason or "").lower(),
             out.reason)

        # B7: real-object binding gate — isolation proven on a DIFFERENT OS object than
        #     the protected one => must fail AT _stage_bind (凌翼 R1: canary != protected).
        sup = _SwitchSupervisor(tmp, ok=True)
        ad = _base_adapter(tmp, supervisor=sup, chain_override=lambda a: _FakeQ3Result(valid=True))
        def wrong_target_prove(path):
            (tmp / "elsewhere.bin").write_bytes(b"\x00" * SUBSTRATE_SIZE)
            return A.WorkerAccessWitness(
                request_nonce="n", op="READ", target_path=str(tmp / "elsewhere.bin"),
                target_os_identity=A.file_identity(tmp / "elsewhere.bin"),
                worker_pid=4242, worker_sid=sup.sid, worker_create_time=123.0,
                worker_reported="DENIED", controller_seal_ok=False,
                controller_verdict="HANDLE_AUDIT", handle_audit_status=A.HANDLE_AUDIT_CLEAN)
        sup.prove_persistent_isolation = wrong_target_prove
        out = ad.run_reset_transaction(_mk_state(), _mk_state())
        _chk("B7 isolation on WRONG object (canary!=protected) => INVALID at bind gate",
             out.integration_valid is False
             and "binding recheck" in (out.reason or "").lower(), out.reason)


# ===========================================================================
# LAYER C — real business worker lifecycle (Windows + credential required)
# ===========================================================================
def layer_c_real() -> str:
    print("\n=== LAYER C: real business worker integration ===")
    if not sys.platform.startswith("win"):
        print("  SKIP: not Windows")
        return SKIP
    if not os.environ.get("AFTERGLOW_WORKER_PASSWORD"):
        print("  SKIP: AFTERGLOW_WORKER_PASSWORD not set (env precondition, NOT a pass)")
        return SKIP

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        (tmp / "protected.bin").write_bytes(b"\x00" * SUBSTRATE_SIZE)
        (tmp / "literal.bin").write_bytes(b"\x00" * LITERAL_SIZE)
        forbidden = tmp / "forbidden.bin"
        forbidden.write_bytes(b"secret")

        # C0: the mailbox dir must be writable by the worker account for the holding
        # handshake; grant it (the OS-level ACL arrangement is part of setup).
        mailbox = tmp.parent / (tmp.name + "_mailbox")
        mailbox.mkdir(parents=True, exist_ok=True)
        _grant_worker_write(mailbox)

        sup = A.BusinessWorkerSupervisor(
            account=os.environ.get("AFTERGLOW_WORKER_ACCOUNT", "afterglow_worker"),
            entry_script=HERE / "q3_business_worker_entry.py",
            work_dir=tmp, mailbox_dir=mailbox, python_exe=A._direct_interpreter(),
            password=os.environ.get("AFTERGLOW_WORKER_PASSWORD"))

        # C2 (negative): a same-account worker must NEVER be accepted as a real
        # isolation subject. Without a password the supervisor must fail closed.
        sup_nopw = A.BusinessWorkerSupervisor(
            account=os.environ.get("AFTERGLOW_WORKER_ACCOUNT", "afterglow_worker"),
            entry_script=HERE / "q3_business_worker_entry.py",
            work_dir=tmp, python_exe=A._direct_interpreter(), password="")
        nopw_rejected = False
        try:
            sup_nopw.start_business_worker_holding()
        except Exception:                                    # noqa: BLE001
            nopw_rejected = True
        finally:
            sup_nopw.terminate()
        _chk("C2 same-account worker refused (fail-closed)", nopw_rejected)

        # C3 (negative): a wrong ENTRY identity must be refused (R3 entry binding).
        sup_badentry = A.BusinessWorkerSupervisor(
            account=os.environ.get("AFTERGLOW_WORKER_ACCOUNT", "afterglow_worker"),
            entry_script=HERE / "q3_business_worker_entry.py",
            work_dir=tmp, python_exe=A._direct_interpreter(),
            password=os.environ.get("AFTERGLOW_WORKER_PASSWORD"),
            expected_entry_sha256="0" * 64)
        badentry_rejected = False
        try:
            sup_badentry.start_business_worker_holding()
        except Exception:                                    # noqa: BLE001
            badentry_rejected = True
        finally:
            sup_badentry.terminate()
        _chk("C3 wrong entry identity refused (fail-closed)", badentry_rejected)

        # C1: start-holding (consume READY), verify OS witness, prove durable
        # isolation ON the worker with a CONTROLLER-corroborated witness, release
        # with ACK, then terminate. Real supervisor; no frozen Q3 here.
        try:
            w = sup.start_business_worker_holding()
            _chk("C1 worker OS witness ok (READY consumed)", sup.witness_ok(w),
                 f"pid={w.pid} ct={w.create_time:.0f} sid={w.token_sid[:12]}...")
            # durable boundary FIRST (R1: prove on the REAL object)
            A.deny_read_for_sid(forbidden, w.token_sid)
            wit = sup.prove_persistent_isolation(forbidden)
            _chk("C1 worker bound access attempt reported DENIED",
                 wit.worker_reported == "DENIED", f"worker={wit.worker_reported}")
            if wit.handle_audit_status == A.HANDLE_AUDIT_CLEAN:
                _chk("C1 controller handle audit CLEAN => isolation proven", wit.proven,
                     f"handles={wit.handle_audit_status}")
            else:
                # 凌翼 R2: if the environment cannot complete the handle audit, this is
                # NOT_EVALUATED (a narrower proven conclusion), NOT a pass and NOT a
                # quiet failure — the witness correctly refuses to claim `proven`.
                print(f"  [SKIP] C1 handle audit = {wit.handle_audit_status} "
                      f"(env cannot fully audit) => NOT_EVALUATED, not a pass")
                _skip("C1 controller handle audit CLEAN => isolation proven",
                      f"env UNEVALUATED: {wit.handle_audit_status}")
                _chk("C1 witness refuses to claim proven without CLEAN audit",
                     wit.proven is False, wit.handle_audit_status)
            sup.release_into_execution()
            _chk("C1 release ACKed", getattr(sup, "_release_acked", False))
        except Exception as e:                              # noqa: BLE001
            _chk("C1 worker lifecycle ran", False, f"{type(e).__name__}: {e}")
        finally:
            r1 = sup.terminate()
            r2 = sup.terminate()                            # idempotent
            _chk("C1 terminate idempotent, EXIT_CONFIRMED",
                 r1 == "EXIT_CONFIRMED" and r2 in ("EXIT_CONFIRMED", "NOT_STARTED"),
                 f"{r1}/{r2}")
    return PASS


# ===========================================================================
# LAYER D — REAL success path through run_reset_transaction()
# ===========================================================================
def layer_d_real_success() -> str:
    """凌翼: at least ONE real, complete success path through run_reset_transaction()
    asserting integration_valid is True, with a REAL adapter and the REAL replacement
    contract (真实旧 worker + 非空 clear categories/action), controller-captured
    snapshots with CORRECT timing (restored AFTER reset). 知微 D2-02/D2-03.

    Required environment (all three, else SKIP — NOT a pass):
      AFTERGLOW_Q3_FULL_FIXTURE   = a directory containing:
          protected.bin (SUBSTRATE_SIZE), literal.bin (LITERAL_SIZE),
          and `fixture.json` (an EXECUTABLE descriptor) with keys:
            old_worker_pid       : int (a REAL live old worker to terminate), or null
            clear_targets_by_category : {category: [paths]} (NON-EMPTY)
            (the controller wires terminate_old_worker/clear_action from this)
      AFTERGLOW_WORKER_PASSWORD   = the worker credential.
    """
    print("\n=== LAYER D: real success path (run_reset_transaction) ===")
    fp = os.environ.get("AFTERGLOW_Q3_FULL_FIXTURE")
    if not fp:
        print("  SKIP: AFTERGLOW_Q3_FULL_FIXTURE not set (needs a real Q3-passable")
        print("        fixture + executable descriptor). NOT a pass.")
        _skip("D1 real success path", "AFTERGLOW_Q3_FULL_FIXTURE not set")
        return SKIP
    from pathlib import Path as _P
    import json as _json
    fx = _P(fp)
    files = {p.name: p for p in fx.iterdir()}
    if not {"protected.bin", "literal.bin", "fixture.json"}.issubset(files):
        print(f"  SKIP: fixture missing protected.bin/literal.bin/fixture.json "
              f"(has {sorted(files)})")
        _skip("D1 real success path", "fixture incomplete")
        return SKIP

    # 知微 D2-02: read the EXECUTABLE descriptor — do NOT hardcode an empty clear map.
    desc = _json.loads(files["fixture.json"].read_text(encoding="utf-8"))
    clear_targets = desc.get("clear_targets_by_category") or {}
    old_worker_pid = desc.get("old_worker_pid")
    if not clear_targets:
        print("  SKIP: descriptor clear_targets_by_category is EMPTY => cannot prove a "
              "REAL reset (would be FIRST_START). NOT a pass.")
        _skip("D1 real success path", "clear_targets_by_category empty => not a real reset")
        return SKIP
    if old_worker_pid is None:
        print("  SKIP: descriptor has no old_worker_pid => cannot prove REAL_RESET. NOT a pass.")
        _skip("D1 real success path", "no old_worker_pid => not a real replacement")
        return SKIP

    _grant_worker_write(fx)
    acct = os.environ.get("AFTERGLOW_WORKER_ACCOUNT", "afterglow_worker")

    # 知微 D3-02: the frozen chain contract is `category -> path STRING`
    # (q3_reset_chain.py: `_map = dict(...); Path(str(t)).exists()` for each value).
    # Normalize the descriptor to that shape: if a value is a list, require it to have
    # exactly ONE entry and collapse to the string; reject/whitelist extra shapes.
    def _norm_map(m):
        out = {}
        for cat, val in (m or {}).items():
            if isinstance(val, (list, tuple)):
                if len(val) != 1:
                    raise ValueError(
                        f"clear category {cat!r} has {len(val)} paths; the frozen "
                        f"contract takes ONE path per category (D3-02)")
                out[cat] = str(val[0])
            else:
                out[cat] = str(val)
        return out

    clear_targets = _norm_map(clear_targets)

    # 知微 D3-01: the frozen chain calls `terminator(old_pid)` — the callback MUST
    # accept the pid. It performs identity/terminate; the frozen chain waits+confirms
    # exit on ITS OWN handle, so we must not claim success from an unchecked wait.
    def _terminate_old(old_pid):
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.windll.kernel32
        PROCESS_TERMINATE = 0x0001
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.TerminateProcess.restype = wintypes.BOOL
        k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        h = k32.OpenProcess(PROCESS_TERMINATE, False, int(old_pid))
        if not h:
            return False                       # no handle => cannot terminate => False
        try:
            ok = k32.TerminateProcess(h, 1)    # the frozen chain confirms exit itself
            return bool(ok)
        finally:
            k32.CloseHandle(h)

    # 知微 D3-01/D3-02: the frozen chain calls `clear_action(clear_targets_by_category)`
    # — accept the mapping and remove every declared target path.
    def _clear_action(mapping):
        import os as _os
        for cat, path in (mapping or {}).items():
            try:
                _os.remove(str(path))
            except FileNotFoundError:
                pass
        return True

    # 知微 D3-01: assert BOTH callbacks can bind the EXACT arity the frozen chain uses
    # (`terminator(old_pid)` and `clear_action(mapping)`), so a signature mismatch is
    # caught here rather than as a TypeError deep inside the frozen chain.
    import inspect
    try:
        inspect.signature(_terminate_old).bind(0)                 # terminator(old_pid)
        inspect.signature(_clear_action).bind({})                 # clear_action(mapping)
        _chk("D1 callbacks bind the frozen arity (terminate(old_pid), clear_action(map))",
             True)
    except TypeError as e:
        _chk("D1 callbacks bind the frozen arity", False, str(e))
        return FAIL

    # 知微 D4-01: the frozen Q3 chain LOCKS DOWN `fx` (denies the worker write on
    # code_dir.parent). The business mailbox must be a SEPARATE writable dir.
    mailbox = fx.parent / (fx.name + "_mailbox")
    mailbox.mkdir(parents=True, exist_ok=True)
    _grant_worker_write(mailbox)

    sup = A.BusinessWorkerSupervisor(
        account=acct, entry_script=HERE / "q3_business_worker_entry.py",
        work_dir=fx, mailbox_dir=mailbox, python_exe=A._direct_interpreter(),
        password=os.environ.get("AFTERGLOW_WORKER_PASSWORD"),
        expected_entry_sha256=A._sha256_file(HERE / "q3_business_worker_entry.py"))
    ad = A.Q3ResetAdapter(
        account=acct, password=os.environ.get("AFTERGLOW_WORKER_PASSWORD", ""),
        work_dir=fx, protected=files["protected.bin"],
        literal_path=files["literal.bin"], substrate_path=files["protected.bin"],
        python_exe=A._direct_interpreter(),
        clear_targets_by_category=clear_targets,          # from the descriptor (non-empty)
        expected_sid=None, transaction_id=uuid.uuid4().hex, supervisor=sup,
        forbidden_path=files.get("forbidden.bin", files["protected.bin"]),
        old_worker_pid=old_worker_pid, terminate_old_worker=_terminate_old,
        clear_action=_clear_action, proving_real_replacement=True)
    handoff = ad.capture_handoff()
    # 知微 D2-03: pass a PROVIDER so restored is captured AFTER reset, before RC11.
    try:
        out = ad.run_reset_transaction(handoff, restored_provider=ad.capture_restored)
    finally:
        ad._cleanup()
    _chk("D1 real success path integration_valid is True",
         out.integration_valid is True, out.reason)
    _chk("D1 restored captured AFTER reset (provider)",
         (out.bindings or {}).get("restored_capture_timing") == "provider_after_reset",
         str((out.bindings or {}).get("restored_capture_timing")))
    return PASS


# ===========================================================================
def main() -> int:
    print("=" * 72)
    print("Q3 RESET ADAPTER — INTEGRATION REGRESSION (layers A/B/C/D)")
    print(f"lineage = {A.INTEGRATION_LINEAGE}")
    print("=" * 72)
    layer_a_logic()
    layer_b_controlled()
    c_verdict = layer_c_real()
    d_verdict = layer_d_real_success()

    print("\n" + "=" * 72)
    # structured, de-duplicated counts (知微: 35 distinct PASS entries — do NOT count
    # the summary re-print as 70; and SKIPs must be visible, not dropped)
    n_pass = sum(1 for _, v, _ in _results if v == PASS)
    n_fail = sum(1 for _, v, _ in _results if v == FAIL)
    n_skip = sum(1 for _, v, _ in _results if v == SKIP)
    seen = set()
    for name, v, tail in _results:
        if (name, v) in seen:
            continue
        seen.add((name, v))
        print(f"[{v}] {name}")
    print("=" * 72)
    print(f"DISTINCT_RESULTS: PASS={n_pass} FAIL={n_fail} SKIP={n_skip}")
    if n_fail:
        print("ADAPTER_REGRESSION = FAIL")
        return 1
    # any SKIP in a REQUIRED item => PARTIAL (not a pass)
    if n_skip or c_verdict == SKIP or d_verdict == SKIP:
        print("ADAPTER_REGRESSION = PARTIAL (real-scope items UNEVALUATED/SKIPPED")
        print("  => NOT a real-isolation/full-success pass; env precondition, NOT a pass)")
        return 2
    print("ADAPTER_REGRESSION = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
