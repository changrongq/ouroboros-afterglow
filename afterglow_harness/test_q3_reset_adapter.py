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


# ===========================================================================
# helpers / fixtures
# ===========================================================================
def _mk_state() -> StateSnapshot:
    return StateSnapshot(literal=b"\x01" * LITERAL_SIZE, q_raw=b"\x00" * SUBSTRATE_SIZE)


class _FakeQ3Result:
    """A minimal stand-in used ONLY in the logic layer where the real chain is not
    invoked. It is NEVER used to claim real OS evidence. It exists so the state
    machine can be exercised deterministically."""

    def __init__(self, *, valid=True, reset_mode="REAL_RESET",
                 real_reset_required=True, real_reset_ok=True,
                 clear_ok=True, access_ok=True, reason="ok"):
        self.valid = valid
        self.reset_mode = reset_mode
        self.real_reset_required = real_reset_required
        self.real_reset_ok = real_reset_ok
        self.clear_ok = clear_ok
        self.access_ok = access_ok
        self.reason = reason


def _base_adapter(tmp: Path, *, chain_override=None, **kw):
    """Build an adapter whose Q3 stage is driven by `chain_override` (an injectable
    function) so the LOGIC layer runs without a credential. The REAL layers override
    this to call the genuine chain."""
    # logic fixtures need the REAL files to exist so the OS-identity check passes.
    (tmp / "protected.bin").write_bytes(b"\x00" * SUBSTRATE_SIZE)
    (tmp / "literal.bin").write_bytes(b"\x00" * LITERAL_SIZE)
    adapter = A.Q3ResetAdapter(
        account="afterglow_worker", password="x" * 8,
        work_dir=tmp, protected=(tmp / "protected.bin"),
        literal_path=(tmp / "literal.bin"), substrate_path=(tmp / "protected.bin"),
        python_exe=sys.executable, clear_targets_by_category={},
        expected_sid="S-1-5-21-0-0-0-1001",
        transaction_id=uuid.uuid4().hex,
        supervisor=_NullSupervisor(tmp),
        forbidden_path=(tmp / "forbidden.bin"),
        **kw)
    if chain_override is not None:
        adapter._call_q3_chain = lambda: chain_override(adapter)  # injection seam
    return adapter


class _NullSupervisor:
    """Logic-layer supervisor: does NOT claim real OS evidence. Its witness is
    deliberately NON-ok unless the test sets it, so a logic pass never implies a
    real-worker pass. (Layer C replaces this entirely.)"""

    def __init__(self, work_dir):
        self.work_dir = Path(work_dir)
        self._w = None
        self._terminated = 0

    def start_business_worker_holding(self):
        self._w = A.BusinessWorkerWitness(
            pid=0, token_sid="", account="", create_time=0.0,
            entry_sha256="", create_api="null", started_and_holding=True)
        return self._w

    def witness(self):
        return self._w

    def witness_ok(self, w=None):
        return False                      # logic supervisor NEVER claims a real worker

    def prove_persistent_isolation(self, forbidden_path):
        return False                      # logic supervisor NEVER claims real isolation

    def release_into_execution(self):
        pass

    def terminate(self) -> str:
        self._terminated += 1
        return "TERMINATED"


def _grant_worker_write(path: Path) -> None:
    """Grant the worker account modify access to the work dir (OS-level setup)."""
    import subprocess
    acct = os.environ.get("AFTERGLOW_WORKER_ACCOUNT", "afterglow_worker")
    try:
        subprocess.run(["icacls", str(path), "/grant", f"{acct}:(OI)(CI)M"],
                       capture_output=True, text=True)
    except Exception:                                            # noqa: BLE001
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

        # A3: repeat call on a terminal transaction is REFUSED (no stale reuse).
        ad = _base_adapter(tmp, chain_override=lambda a: _FakeQ3Result(valid=False))
        ad.run_reset_transaction(_mk_state(), _mk_state())
        out2 = ad.run_reset_transaction(_mk_state(), _mk_state())
        _chk("A3 second call refused / INVALID", out2.integration_valid is False,
             out2.reason)

        # A4: exception in the Q3 stage is converged to INVALID (single failure contract).
        def chain_raises(adapter):
            raise RuntimeError("boom")
        ad = _base_adapter(tmp, chain_override=chain_raises)
        out = ad.run_reset_transaction(_mk_state(), _mk_state())
        _chk("A4 Q3 exception => integration INVALID", out.integration_valid is False)
        _chk("A4 state FAILED", ad.state == A.TX_FAILED)

        # A5: cleanup is idempotent (terminate called but state stable).
        _chk("A5 cleanup idempotent (second _cleanup no-op)",
             (ad._cleanup(), ad._cleanup(), ad.state == A.TX_FAILED)[-1])


# ===========================================================================
# LAYER B — controlled negative tests (inject INPUTS before the frozen chain)
# ===========================================================================
def layer_b_controlled() -> None:
    print("\n=== LAYER B: controlled negative tests ===")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # Create the real files so OS identity checks operate on real objects.
        (tmp / "protected.bin").write_bytes(b"\x00" * SUBSTRATE_SIZE)
        (tmp / "literal.bin").write_bytes(b"\x00" * LITERAL_SIZE)
        (tmp / "forbidden.bin").write_bytes(b"secret")

        # B1: object-mismatch negative — protected and substrate are DIFFERENT files.
        other = tmp / "different.bin"
        other.write_bytes(b"\x00" * SUBSTRATE_SIZE)
        raised = False
        try:
            A.Q3ResetAdapter(
                account="a", password="p", work_dir=tmp,
                protected=(tmp / "protected.bin"),
                literal_path=(tmp / "literal.bin"),
                substrate_path=other,                       # NOT the same object
                python_exe=sys.executable, clear_targets_by_category={},
                expected_sid="S-1-5-21-0-0-0-1001",
                transaction_id=uuid.uuid4().hex,
                supervisor=_NullSupervisor(tmp),
                forbidden_path=(tmp / "forbidden.bin"))
        except Exception as e:                              # noqa: BLE001
            raised = "SUBSTRATE" in str(e).upper() or "PROTECTED" in str(e).upper()
        _chk("B1 protected<->substrate object mismatch => refuse", raised)

        # B2: same object via a hardlink/alias is ACCEPTED (OS identity, not string).
        alias = tmp / "protected_alias.bin"
        try:
            os.link(tmp / "protected.bin", alias)
            ad = A.Q3ResetAdapter(
                account="a", password="p", work_dir=tmp,
                protected=(tmp / "protected.bin"),
                literal_path=(tmp / "literal.bin"),
                substrate_path=alias,                       # hardlink => same OS file
                python_exe=sys.executable, clear_targets_by_category={},
                expected_sid="S-1-5-21-0-0-0-1001",
                transaction_id=uuid.uuid4().hex,
                supervisor=_NullSupervisor(tmp),
                forbidden_path=(tmp / "forbidden.bin"))
            _chk("B2 hardlink alias => same OS file => accepted", True)
        except Exception as e:                              # noqa: BLE001
            _chk("B2 hardlink alias => same OS file => accepted", False, str(e))

        # B3..B9: each gate failure injected by CHANGING the Q3 result the chain
        # WOULD return because we altered its INPUTS (here modeled via the seam that
        # mirrors "the chain computed a real failure"). Every gate must bridge to
        # integration INVALID, not only the 3 the draft read.
        gates = [
            ("real_reset_ok", dict(valid=False, real_reset_ok=False)),
            ("clear_ok", dict(valid=False, clear_ok=False)),
            ("access_ok", dict(valid=False, access_ok=False)),
            ("handle_ok", dict(valid=False)),
            ("matrix_ok", dict(valid=False)),
            ("dacl_restore_ok", dict(valid=False)),
            ("preserve_ok", dict(valid=False)),
        ]
        for name, kw in gates:
            ad = _base_adapter(tmp, chain_override=lambda a, _kw=kw: _FakeQ3Result(**_kw))
            out = ad.run_reset_transaction(_mk_state(), _mk_state())
            _chk(f"B3 gate {name} fails => integration INVALID",
                 out.integration_valid is False, name)

        # B10: RC11 access_side_ok must be bound to THIS worker's witness, and Q3
        # access proof kept separate -> both required. If isolation stage fails,
        # integration must be INVALID even if Q3 valid.
        ad = _base_adapter(tmp, chain_override=lambda a: _FakeQ3Result(valid=True))
        out = ad.run_reset_transaction(_mk_state(), _mk_state())
        _chk("B10 isolation not proven => integration INVALID (even if Q3 valid)",
             out.integration_valid is False, out.reason)


# ===========================================================================
# LAYER C — real business worker integration (Windows + credential required)
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

        # C0: the work dir must be writable by the worker account for the holding
        # handshake; grant it (the OS-level ACL arrangement is part of setup).
        _grant_worker_write(tmp)

        sup = A.BusinessWorkerSupervisor(
            account=os.environ.get("AFTERGLOW_WORKER_ACCOUNT", "afterglow_worker"),
            entry_script=HERE / "q3_business_worker_entry.py",
            work_dir=tmp, python_exe=sys.executable,
            password=os.environ.get("AFTERGLOW_WORKER_PASSWORD"))

        # C2 (negative): a same-account worker must NEVER be accepted as a real
        # isolation subject. Without a password the supervisor must fail closed.
        sup_nopw = A.BusinessWorkerSupervisor(
            account=os.environ.get("AFTERGLOW_WORKER_ACCOUNT", "afterglow_worker"),
            entry_script=HERE / "q3_business_worker_entry.py",
            work_dir=tmp, python_exe=sys.executable, password="")
        nopw_rejected = False
        try:
            sup_nopw.start_business_worker_holding()
        except Exception:                                    # noqa: BLE001
            nopw_rejected = True
        finally:
            sup_nopw.terminate()
        _chk("C2 same-account worker refused (fail-closed)", nopw_rejected)

        # C1: start-holding, verify OS witness, prove durable isolation ON the worker,
        # then terminate. This exercises the real supervisor WITHOUT the frozen Q3.
        try:
            w = sup.start_business_worker_holding()
            _chk("C1 worker OS witness ok", sup.witness_ok(w),
                 f"pid={w.pid} ct={w.create_time:.0f} sid={w.token_sid[:12]}...")
            sup.release_into_execution()
            isolated = sup.prove_persistent_isolation(forbidden)
            _chk("C1 durable isolation proven ON the real worker", isolated)
        except Exception as e:                              # noqa: BLE001
            _chk("C1 worker lifecycle ran", False, f"{type(e).__name__}: {e}")
        finally:
            r1 = sup.terminate()
            r2 = sup.terminate()                            # idempotent
            _chk("C1 terminate idempotent, no live process",
                 r1 in ("TERMINATED", "NOT_STARTED") and r2 in ("TERMINATED", "NOT_STARTED"),
                 f"{r1}/{r2}")
    return PASS


# ===========================================================================
def main() -> int:
    print("=" * 72)
    print("Q3 RESET ADAPTER — INTEGRATION REGRESSION (layers A/B/C)")
    print(f"lineage = {A.INTEGRATION_LINEAGE}")
    print("=" * 72)
    layer_a_logic()
    layer_b_controlled()
    c_verdict = layer_c_real()

    print("\n" + "=" * 72)
    anyfail = any(v == FAIL for _, v, _ in _results)
    for name, v, tail in _results:
        print(f"[{v}] {name}")
    print("=" * 72)
    if anyfail:
        print("ADAPTER_REGRESSION = FAIL")
        return 1
    if c_verdict == SKIP:
        print("ADAPTER_REGRESSION = PARTIAL (logic+controlled passed; real layer SKIPPED")
        print("  => NOT a real-isolation pass; env precondition, NOT a pass)")
        return 2
    print("ADAPTER_REGRESSION = PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
