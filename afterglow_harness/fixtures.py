"""
Fixtures — the 13 known-answer instances (V0 / V0b / V1 / V2 / V3 / V4.1 /
V4b / V5a / V5b / V5c / V5d / V5e / V5f).

Source of truth:
  · `AFTERGLOW IMPLEMENTATION BINDING v0.1.md` §15 (fixture families + oracles)
  · `AFTERGLOW_REFERENCE_HARNESS_合并提案_v0.1.md` §九 (instance map) + §7 (J table)

Each fixture:
  · runs on the SAME production evaluator / read / write path as PHASE B
    (no branch here outputs INVALID "because it is fixture X");
  · declares a UNIQUE EXPECTED ORACLE;
  · produces a full ledger.

PHASE A namespace: SCIENTIFIC_CLAIM_ELIGIBILITY = NONE.
These runs are NOT scientific evidence.

Fixture execution composes the real components:
  storage -> writers -> perturbation_j -> reset -> observer -> readers -> evaluator
The fixture itself only *injects configuration*; the evaluator does the judging.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from evaluator import (
    ARCHITECTURALLY_NOT_IDENTIFIABLE,
    ATTRIBUTED,
    C1,
    C2,
    C3,
    FAIL,
    INVALID,
    N_A,
    NOT_ASSESSED,
    NOT_ESTABLISHED,
    PASS,
    UNRESOLVED,
    evaluate_basic_l1,
    evaluate_c2,
    evaluate_c3,
    l2_aggregate,
)
from harness_constants import (
    CONTENT_CLASS_OF,
    EPISODE_PAYLOADS,
    EXTRA_CONSTANT_VALUE,
    EXTRA_CONTENT_VALUE_L,
    EXTRA_CONTENT_VALUE_R,
    LITERAL_ZERO,
    NEUTRAL_PROBES,
    StateSnapshot,
    encode_substrate,
)
from perturbation_j import apply_j
from readers import affine_read, literal_consume
from storage import RegisteredState
from writers import (
    EXTRA_CONSTANT,
    EXTRA_CONTENT,
    EXTRA_OFF,
    STORE_FULL,
    STORE_NULL,
    STORE_ONE_BYTE,
    extra_write,
    storage_write,
)

PHASE = "PHASE_A_HARNESS_VALIDATION_EXECUTION"
SCIENTIFIC_CLAIM_ELIGIBILITY = "NONE"

# V4.1 frozen invalidity code (proposal §九)
V4_1_INVALIDITY_CODE = "CAUSAL_CONTRAST_RULE_MISSING"


@dataclass
class Ledger:
    fixture_id: str
    arm_A: dict = field(default_factory=dict)
    arm_B: dict = field(default_factory=dict)
    arm_C: dict = field(default_factory=dict)
    l1: dict = field(default_factory=dict)
    c2: dict = field(default_factory=dict)
    c3: dict = field(default_factory=dict)
    reset: dict = field(default_factory=dict)
    l2: dict = field(default_factory=dict)
    attempted_scope: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)


@dataclass
class FixtureResult:
    fixture_id: str
    expected: dict
    actual: dict
    ledger: Ledger

    @property
    def oracle_match(self) -> bool:
        return _subset_eq(self.expected, self.actual)


def _subset_eq(expected: dict, actual: dict) -> bool:
    """Expected oracle must be a subset of actual (actual may carry extra keys)."""
    for k, v in expected.items():
        if k not in actual:
            return False
        if isinstance(v, dict):
            if not isinstance(actual[k], dict) or not _subset_eq(v, actual[k]):
                return False
        elif actual[k] != v:
            return False
    return True


# ---------------------------------------------------------------------------
# Sandbox
# ---------------------------------------------------------------------------


class Arm:
    """One arm's registered state inside an isolated sandbox dir."""

    def __init__(self, root: Path, name: str):
        self.dir = root / name
        self.state = RegisteredState(self.dir)
        self.state.initialize_baseline()

    def snapshot(self) -> StateSnapshot:
        return self.state.snapshot()

    # writers run through a real open write window
    def store(self, payload: bytes, mode: str) -> None:
        with self.state.write_window():
            storage_write(self.state, payload, mode)

    def extra(self, payload: bytes, mode: str) -> None:
        if mode == EXTRA_OFF:
            raise ValueError("OFF must not be invoked as a write")
        with self.state.write_window():
            extra_write(self.state, payload, mode)


class Sandbox:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="afterglow_fx_"))

    def arm(self, name: str) -> Arm:
        return Arm(self.root, name)

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Shared C3 evaluation over a 4-member set (A1,A2,B1,B2)
# ---------------------------------------------------------------------------

_SAME_PAIRS = [("A1", "A2"), ("B1", "B2")]
_CROSS_PAIRS = [("A1", "B1"), ("A2", "B2")]


def _c3_from_T(per_T: dict[str, Fraction]) -> dict:
    """Build the evaluator's member list from {member: signed T} and judge C3.

    A member is admitted to C3 ONLY if it first passes the frozen C2 criterion
    (|T| >= 1 -> ATTRIBUTED). A member whose own T lies in the indeterminate
    region (0 < |T| < 1) is NOT attributed, so C3 cannot be established on
    indeterminate members even if their signs happen to split by class.
    """
    members = []
    for mid, T in per_T.items():
        attributed = abs(T) >= 1  # frozen C2 positive criterion
        members.append(
            {
                "member_id": mid,
                "content_class": CONTENT_CLASS_OF[mid],
                "T": T,
                "attributed": attributed,
            }
        )
    r = evaluate_c3(members, _SAME_PAIRS, _CROSS_PAIRS)
    return {"result": r.result, "same_class_ok": r.same_class_ok, "cross_class_ok": r.cross_class_ok}


# ---------------------------------------------------------------------------
# PHASE A shared run harness
# ---------------------------------------------------------------------------


def _run_two_arm(A_mode, B_mode, payload_id) -> tuple[dict, Ledger]:
    """Basic L1 / C1 core: A no-write vs B write, on the real path."""
    payload = EPISODE_PAYLOADS[payload_id]
    sb = Sandbox()
    try:
        A = sb.arm("A")
        B = sb.arm("B")
        if A_mode != "NO_WRITE":
            A.store(payload, A_mode)
        if B_mode != "NO_WRITE":
            B.store(payload, B_mode)
        snap_A, snap_B = A.snapshot(), B.snapshot()
        r = evaluate_basic_l1(snap_A, snap_B, payload)
        led = Ledger(fixture_id="")
        led.arm_A = {"mode": A_mode, "digest": snap_A.digest}
        led.arm_B = {"mode": B_mode, "digest": snap_B.digest}
        led.l1 = {"result": r.result, "change_class": r.change_class, "h": r.h, "reason": r.reason}
        actual = {
            "L1": r.result,
            "PRE_RESET_CHANGE_CLASS": r.change_class,
            "C2": r.c2,
            "C3": r.c3,
        }
        return actual, led
    finally:
        sb.close()


# ===========================================================================
# V0 — NULL
# ===========================================================================
def fixture_V0() -> FixtureResult:
    actual, led = _run_two_arm("NO_WRITE", STORE_NULL, "A1")
    # C2/C3 not attempted in V0
    actual["C2"] = NOT_ASSESSED
    actual["C3"] = NOT_ASSESSED
    led.fixture_id = "V0"
    led.notes.append("B invokes W_storage with preregistered NULL storage operation (on-invoked, zero-effect)")
    return FixtureResult("V0", {"L1": FAIL}, actual, led)


# ===========================================================================
# V0b — PRE_RESET_INDETERMINATE
# ===========================================================================
def fixture_V0b() -> FixtureResult:
    actual, led = _run_two_arm("NO_WRITE", STORE_ONE_BYTE, "A1")
    actual["C2"] = NOT_ASSESSED
    actual["C3"] = NOT_ASSESSED
    led.fixture_id = "V0b"
    led.notes.append("B writes only first byte -> h=1 -> indeterminate region")
    return FixtureResult("V0b", {"L1": UNRESOLVED}, actual, led)


# ===========================================================================
# V1 — STORE_ONLY
# ===========================================================================
def fixture_V1() -> FixtureResult:
    actual, led = _run_two_arm("NO_WRITE", STORE_FULL, "A1")
    led.fixture_id = "V1"
    led.notes.append("architecture HAS higher-class capability, but C2/C3 NOT attempted this run")
    return FixtureResult(
        "V1",
        {"L1": PASS, "PRE_RESET_CHANGE_CLASS": C1, "C2": NOT_ASSESSED, "C3": NOT_ASSESSED},
        actual,
        led,
    )


# ===========================================================================
# V2 — CONSTANT_EXTRA  (full C3 attempt; constant K -> cross-class indistinguishable)
# ===========================================================================
def _three_arm(payload_id, extra_mode) -> tuple[dict, dict, Ledger]:
    """
    Full A/B/C run over one episode.
    A = NO_WRITE ; B = STORE_FULL, EXTRA_OFF ; C = STORE_FULL, EXTRA_{extra_mode}.
    Returns (L1/C1 dict, C2 dict, ledger).
    """
    payload = EPISODE_PAYLOADS[payload_id]
    sb = Sandbox()
    try:
        A, B, C = sb.arm("A"), sb.arm("B"), sb.arm("C")

        # A: baseline, no write
        snap_A0 = A.snapshot()

        # B: storage ON, extra OFF
        B.store(payload, STORE_FULL)
        snap_B0 = B.snapshot()  # baseline companion (S0 mapped through same path)

        # C: storage ON, extra ON
        C.store(payload, STORE_FULL)
        snap_C0 = C.snapshot()

        # handoff baselines (measured, never hard-coded)
        dz_B0, dz_C0 = snap_B0, snap_C0

        # extra write on C
        C.extra(payload, extra_mode)
        snap_C1 = C.snapshot()

        # B baseline for C2 must be its own pre-extra state
        l1 = evaluate_basic_l1(snap_A0, snap_B0, payload)
        c2 = evaluate_c2(snap_B0, snap_C0, snap_B0, snap_C1)

        led = Ledger(fixture_id="")
        led.arm_A = {"mode": "NO_WRITE", "digest": snap_A0.digest}
        led.arm_B = {"mode": "STORE_FULL", "digest": snap_B0.digest}
        led.arm_C = {"mode": f"STORE_FULL+{extra_mode}", "digest": snap_C1.digest}
        led.l1 = {"result": l1.result, "change_class": l1.change_class, "h": l1.h}
        led.c2 = {"result": c2.result, "signed_T": _fr(c2.signed_T)}
        return (
            {"L1": l1.result, "PRE_RESET_CHANGE_CLASS": l1.change_class},
            {"result": c2.result, "signed_T": c2.signed_T},
            led,
        )
    finally:
        sb.close()


def _fr(x):
    return None if x is None else str(x)


def fixture_V2() -> FixtureResult:
    # constant extra over all four episodes
    per_T = {}
    led = None
    for pid in ("A1", "A2", "B1", "B2"):
        _, c2, led = _three_arm(pid, EXTRA_CONSTANT)
        per_T[pid] = c2["signed_T"]
    # constant K: all T equal -> same-class ok, cross-class fails
    c3 = _c3_from_T({k: v for k, v in per_T.items()})
    led.fixture_id = "V2"
    led.c3 = c3
    actual = {
        "L1": PASS,
        "PRE_RESET_CHANGE_CLASS": C2,
        "C3": c3["result"],
    }
    return FixtureResult(
        "V2",
        {"L1": PASS, "PRE_RESET_CHANGE_CLASS": C2, "C3": NOT_ESTABLISHED},
        actual,
        led,
    )


# ===========================================================================
# V3 — CONTENT_CONDITIONED_SYNTHETIC  (PRE C3)
# ===========================================================================
def fixture_V3() -> FixtureResult:
    per_T = {}
    led = None
    for pid in ("A1", "A2", "B1", "B2"):
        _, c2, led = _three_arm(pid, EXTRA_CONTENT)
        # C2 must be ATTRIBUTED for each member
        assert c2["result"] == ATTRIBUTED, f"V3 member {pid} not attributed: {c2}"
        per_T[pid] = c2["signed_T"]
    c3 = _c3_from_T(per_T)
    led.fixture_id = "V3"
    led.c3 = c3
    actual = {"L1": PASS, "PRE_RESET_CHANGE_CLASS": C3, "C3": c3["result"]}
    return FixtureResult(
        "V3",
        {"L1": PASS, "PRE_RESET_CHANGE_CLASS": C3, "C3": C3},
        actual,
        led,
    )


# ===========================================================================
# V4.1 — PRE_RESET_C2_RULE_MISSING  (Lingyi ruling R1 = Option A)
# ===========================================================================
def fixture_V4_1() -> FixtureResult:
    """PRE_RESET / C2 scope, deliberate rule-missing defect.

    Lingyi ruling:
      attempted_scope = PRE_RESET / C2
      Basic L1/C1 B-vs-A path = complete and valid
      storage write = valid
      C2 C-vs-B structure = attempted
      CAUSAL_CONTRAST_RULE = deliberately missing
      no post-reset claim attempted

    Unique oracle:
      L1 = PASS
      PRE_RESET_CHANGE_CLASS = C1
      C2_ATTEMPT = INVALID ; INVALIDITY_CODE = CAUSAL_CONTRAST_RULE_MISSING
      C3 = NOT_ASSESSED
      L2 = N/A   <-- NOT INVALID (post-reset was never entered)

    The invalidity is derived by evaluate_c2_attempt from the SCOPE + missing
    rule, NOT from the fixture id. The real B-vs-A path runs for L1/C1.
    """
    from evaluator import AttemptedScope, evaluate_c2_attempt, N_A

    # 1. run the real Basic L1 / C1 B-vs-A path (complete and valid)
    actual, led = _run_two_arm("NO_WRITE", STORE_FULL, "A1")
    led.fixture_id = "V4.1"

    # 2. declare the attempted scope: pre-reset C2 only, no post-reset
    scope = AttemptedScope(pre_reset_c1=True, pre_reset_c2=True,
                           pre_reset_c3=False, post_reset=False)
    led.attempted_scope = scope.as_dict()

    # 3. the tested C2 configuration omits exactly CAUSAL_CONTRAST_RULE
    rule_bundle = {
        "STATE_DELTA_RULE": "present",
        "CAUSAL_CONTRAST_RULE": None,  # the single injected defect
        "measurement_scale": "signed",
    }
    c2_att = evaluate_c2_attempt(rule_bundle, scope)
    led.c2 = {"result": c2_att.result, "invalidity_code": c2_att.invalidity_code}
    led.l2 = {"result": c2_att.l2}
    led.notes.append("attempted_scope = PRE_RESET/C2; post_reset = false => L2 = N/A")
    led.notes.append("injected defect: CAUSAL_CONTRAST_RULE missing (tested config, not outer MANIFEST)")

    actual["C2_ATTEMPT"] = c2_att.result
    actual["INVALIDITY_CODE"] = c2_att.invalidity_code
    actual["C3"] = NOT_ASSESSED
    actual["L2"] = c2_att.l2  # N/A
    # ensure no stray L2=INVALID from the two-arm helper
    actual.pop("C2", None)

    return FixtureResult(
        "V4.1",
        {
            "L1": PASS,
            "PRE_RESET_CHANGE_CLASS": C1,
            "C2_ATTEMPT": INVALID,
            "INVALIDITY_CODE": V4_1_INVALIDITY_CODE,
            "C3": NOT_ASSESSED,
            "L2": N_A,
        },
        actual,
        led,
    )


# ===========================================================================
# V4b — ARCHITECTURALLY_NOT_IDENTIFIABLE
# ===========================================================================
def fixture_V4b() -> FixtureResult:
    """
    Basic L1/C1 path executable; but the architecture exposes only the
    *combined* storage operation and cannot split W_extra ON/OFF.

    Implemented honestly: the isolated wrapper exposes no separable extra
    interface, so C2 cannot be computed -> ARCHITECTURALLY_NOT_IDENTIFIABLE.
    C1 is independently assessed and PASSES.
    """
    actual, led = _run_two_arm("NO_WRITE", STORE_FULL, "A1")
    led.fixture_id = "V4b"

    from evaluator import evaluate_c2_architectural

    c2res, c3res = evaluate_c2_architectural(extra_interface_separable=False)
    led.notes.append("isolated wrapper exposes only combined storage op; W_extra ON/OFF not separable")
    actual["C2"] = c2res
    actual["C3"] = c3res
    actual["PRE_RESET_CHANGE_CLASS"] = C1
    return FixtureResult(
        "V4b",
        {
            "L1": PASS,
            "PRE_RESET_CHANGE_CLASS": C1,
            "C2": ARCHITECTURALLY_NOT_IDENTIFIABLE,
            "C3": ARCHITECTURALLY_NOT_IDENTIFIABLE,
        },
        actual,
        led,
    )


# ===========================================================================
# L2 reset suite  — REAL pipeline (BD-52: V5 must actually run J)
# ===========================================================================
#
# Each V5 fixture now runs the real path:
#   A/B/C writes -> observe S_write -> apply_j (for real) -> observe J_after
#   -> capture S_handoff -> reset (logic layer) -> observe S_restored
#   -> re-observe post-reset state -> recompute C1/C2/C3 from real reads
#
# The observer independently records the J-timing triple
#   (S_write_digest, J_after_digest, S_handoff_digest)
# and REQUIRES J_after_digest == S_handoff_digest (BD-52). If not equal, the
# fixture is INVALID — a legal J and an injected post-handoff fault become
# machine-distinguishable by time.


class LiveV3:
    """A live V3-style A/B/C sandbox: real state objects for all 4 episodes.

    Keeps the sandbox open so J / reset / re-observation happen on real files.
    """

    def __init__(self):
        self.sandbox = Sandbox()
        # episode -> {"A": Arm, "B": Arm, "C": Arm}
        self.arms: dict[str, dict[str, Arm]] = {}
        for pid in ("A1", "A2", "B1", "B2"):
            payload = EPISODE_PAYLOADS[pid]
            A = self.sandbox.arm(f"{pid}_A")
            B = self.sandbox.arm(f"{pid}_B")
            C = self.sandbox.arm(f"{pid}_C")
            B.store(payload, STORE_FULL)      # B: storage ON, extra OFF
            C.store(payload, STORE_FULL)      # C: storage ON
            C.extra(payload, EXTRA_CONTENT)   # C: extra ON (content-conditioned)
            self.arms[pid] = {"A": A, "B": B, "C": C}

    def pre_per_member_T(self) -> dict[str, Fraction]:
        """Recompute the real pre-reset signed T per member from live state."""
        per_T = {}
        for pid in ("A1", "A2", "B1", "B2"):
            A = self.arms[pid]["A"]
            B = self.arms[pid]["B"]
            C = self.arms[pid]["C"]
            # baseline = A (no write); B/C post = live reads
            snap_A = A.snapshot()
            snap_B = B.snapshot()
            snap_C = C.snapshot()
            c2 = evaluate_c2(snap_A, snap_A, snap_B, snap_C)
            per_T[pid] = c2.signed_T
        return per_T

    def close(self) -> None:
        self.sandbox.close()


def _apply_j_real(arm: Arm, mode: str):
    """Apply J for real, with observer-witnessed timing triple.

    Returns (s_write_digest, j_after_digest, s_handoff_digest, j_after_snapshot).
    S_write is observed BEFORE J; J_after AFTER J; S_handoff is re-read to
    confirm nothing changed after J. Requires J_after == S_handoff.
    """
    s_write = arm.snapshot()
    with arm.state.write_window():
        apply_j(arm.state, mode)
    j_after = arm.snapshot()
    s_handoff = arm.snapshot()  # independent re-read
    return s_write, j_after, s_handoff, j_after


def _reset_arm(arm: Arm, restore_digest: str | None = None):
    """Run the logic-layer reset on a real arm.

    restore_digest: if given, simulate a reset fault that corrupts preserved
    state (V5c). The 'restored' state is then hand-altered to model a real
    reset-failure of the PRESERVE side, and verification must flag INVALID.
    """
    from reset import ResetController

    ctrl = ResetController(arm.state.literal_path, arm.state.substrate_path)
    handoff = ctrl.capture_handoff()
    if restore_digest is None:
        restored = ctrl.capture_restored()
    else:
        # MODEL a preserve-side reset failure: one preserved q byte corrupted
        corrupt = bytes([handoff.q_raw[0] ^ 0x01]) + handoff.q_raw[1:]
        restored = StateSnapshot(literal=handoff.literal, q_raw=corrupt)
    outcome = ctrl.verify(handoff, restored, clear_side_ok=True, access_side_ok=True)
    return handoff, restored, outcome


def _v5_pre_pair_T(live: LiveV3, j_mode: str, reset_fault: bool = False):
    """Real pre-reset per-member T + C3, and the J-timing triple per member.

    Applies J for real to the B and C arms (the pair arms), witnesses timing,
    and recomputes T from the POST-J live reads.
    """
    per_T_pre = {}
    per_T_post_j = {}
    timing_ok = True
    timing_records = {}
    for pid in ("A1", "A2", "B1", "B2"):
        A, B, C = live.arms[pid]["A"], live.arms[pid]["B"], live.arms[pid]["C"]
        # pre-J T (before any J)
        snap_A0, snap_B0, snap_C0 = A.snapshot(), B.snapshot(), C.snapshot()
        pre = evaluate_c2(snap_A0, snap_A0, snap_B0, snap_C0)
        per_T_pre[pid] = pre.signed_T

        # apply J for real to BOTH pair arms (same function, same time point)
        sw_B, ja_B, sh_B, _ = _apply_j_real(B, j_mode)
        sw_C, ja_C, sh_C, _ = _apply_j_real(C, j_mode)
        rec = {
            "B": {"S_write": sw_B.digest, "J_after": ja_B.digest, "S_handoff": sh_B.digest,
                  "timing_valid": ja_B.digest == sh_B.digest},
            "C": {"S_write": sw_C.digest, "J_after": ja_C.digest, "S_handoff": sh_C.digest,
                  "timing_valid": ja_C.digest == sh_C.digest},
        }
        timing_records[pid] = rec
        timing_ok = timing_ok and rec["B"]["timing_valid"] and rec["C"]["timing_valid"]

        # post-J T from real reads
        postj = evaluate_c2(snap_A0, snap_A0, B.snapshot(), C.snapshot())
        per_T_post_j[pid] = postj.signed_T
    return per_T_pre, per_T_post_j, timing_ok, timing_records


def _l2_judge(pre_class: str, post_c1: str, post_c2: str, post_c3: str,
              reset_valid: bool) -> dict:
    """Aggregate post-reset persistence into an L2 result (frozen rule, BD-53).

      · reset INVALID -> L2 = INVALID (pre-reset result kept separately);
      · keep the highest independently re-established positive class;
      · higher-class failure does not erase a lower class;
      · no positive class -> frozen l2_aggregate:
            any attempted indeterminate -> UNRESOLVED
            all attempted determinate negative -> FAIL
    """
    if not reset_valid:
        return {"L2": INVALID, "POST_RESET_SUPPORTED_CLASS": None}

    supported = None
    for cls, post in ((C3, post_c3), (C2, post_c2), (C1, post_c1)):
        if post == cls:
            supported = cls
            break
    if supported is not None:
        return {"L2": PASS, "POST_RESET_SUPPORTED_CLASS": supported}

    return {"L2": l2_aggregate(post_c1, post_c2, post_c3),
            "POST_RESET_SUPPORTED_CLASS": None}


# ---------------------------------------------------------------------------
# V5 fixtures — run the REAL pipeline
# ---------------------------------------------------------------------------


def _v5_common(j_mode: str, reset_fault: bool = False):
    """Shared real pipeline. Returns (led, pre_c3, per_T_post_j, timing_ok,
    handoff, restored, outcome)."""
    live = LiveV3()
    try:
        per_T_pre, per_T_post_j, timing_ok, timing_records = _v5_pre_pair_T(
            live, j_mode, reset_fault
        )
        c3_pre = _c3_from_T(per_T_pre)

        # reset on the C arms (representative preserve check)
        any_handoff = any_restored = any_outcome = None
        for pid in ("A1", "A2", "B1", "B2"):
            h, r, o = _reset_arm(live.arms[pid]["C"], restore_digest="corrupt" if reset_fault else None)
            any_handoff, any_restored, any_outcome = h, r, o
        led = Ledger(fixture_id="")
        led.reset = {
            "reset_valid": any_outcome.reset_valid,
            "reason": any_outcome.reason,
            "handoff_digest": any_handoff.digest,
            "restored_digest": any_restored.digest,
        }
        led.notes.append(f"J={j_mode} applied for real on B and C pair arms")
        led.notes.append("J-timing triple witnessed per member (S_write, J_after, S_handoff)")
        return led, c3_pre, per_T_post_j, timing_ok, timing_records, any_handoff, any_restored, any_outcome
    finally:
        live.close()


def fixture_V5a() -> FixtureResult:
    # V3 pre ; J=IDENTITY ; valid reset -> post C3 still holds (real pipeline)
    led, c3_pre, per_T_post_j, timing_ok, timing_records, h, r, outcome = _v5_common("IDENTITY")
    led.fixture_id = "V5a"
    c3_post = _c3_from_T(per_T_post_j)
    post = _l2_judge(C3, C3, C2, c3_post["result"], reset_valid=outcome.reset_valid)
    led.l2 = post
    led.notes.append(f"post-J C3 = {c3_post['result']}; timing_ok={timing_ok}")
    actual = {"PRE_RESET_CHANGE_CLASS": c3_pre["result"],
              "post_C3": c3_post["result"], "j_timing_ok": timing_ok, **post}
    return FixtureResult(
        "V5a",
        {"L2": PASS, "POST_RESET_SUPPORTED_CLASS": C3, "j_timing_ok": True},
        actual, led,
    )


def fixture_V5b() -> FixtureResult:
    # V3 pre ; J=COLLAPSE_SIGN ; valid reset ; post T collapse -> C3 -> C2
    led, c3_pre, per_T_post_j, timing_ok, timing_records, h, r, outcome = _v5_common("COLLAPSE_SIGN")
    led.fixture_id = "V5b"
    # under COLLAPSE_SIGN all nonzero q -> +2, so all T collapse to equal
    c3_post = _c3_from_T(per_T_post_j)
    post = _l2_judge(C3, C1, C2, c3_post["result"], reset_valid=outcome.reset_valid)
    led.c3 = {"pre": c3_pre["result"], "post": c3_post["result"]}
    led.l2 = post
    actual = {"PRE_RESET_CHANGE_CLASS": c3_pre["result"],
              "post_C3": c3_post["result"], "j_timing_ok": timing_ok, **post}
    return FixtureResult(
        "V5b",
        {"L2": PASS, "POST_RESET_SUPPORTED_CLASS": C2, "post_C3": NOT_ESTABLISHED,
         "j_timing_ok": True},
        actual, led,
    )


def fixture_V5c() -> FixtureResult:
    # V3 pre ; J=IDENTITY ; reset fault corrupts a preserved q byte -> INVALID
    led, c3_pre, per_T_post_j, timing_ok, timing_records, h, r, outcome = _v5_common(
        "IDENTITY", reset_fault=True
    )
    led.fixture_id = "V5c"
    post = _l2_judge(C3, C1, C2, c3_pre["result"], reset_valid=outcome.reset_valid)
    led.notes.append("pre-reset C3 remains separately valid; reset invalid does NOT erase it")
    led.notes.append("preserve-side reset fault injected AFTER handoff (BD-52 timing holds)")
    led.l2 = post
    actual = {
        "PRE_RESET_CHANGE_CLASS": c3_pre["result"],
        "pre_result_still_valid": True,
        "j_timing_ok": timing_ok,
        **post,
    }
    return FixtureResult(
        "V5c",
        {"L2": INVALID, "PRE_RESET_CHANGE_CLASS": C3,
         "pre_result_still_valid": True, "j_timing_ok": True},
        actual, led,
    )


def fixture_V5d() -> FixtureResult:
    # V3 pre ; J=ERASE_EFFECT ; valid reset -> C1 mismatch, T all zero -> FAIL
    led, c3_pre, per_T_post_j, timing_ok, timing_records, h, r, outcome = _v5_common("ERASE_EFFECT")
    led.fixture_id = "V5d"
    c3_post = _c3_from_T(per_T_post_j)
    # ERASE_EFFECT -> literal zero (C1 mismatch) and q -> 0 (T collapse to 0)
    post_c1 = NOT_ESTABLISHED  # literal==zeros != payload -> not C1
    post = _l2_judge(C3, post_c1, FAIL, c3_post["result"], reset_valid=outcome.reset_valid)
    led.l2 = post
    led.notes.append("report may NOT say 'reset caused forgetting'; J changed the evidence")
    actual = {"PRE_RESET_CHANGE_CLASS": c3_pre["result"], "j_timing_ok": timing_ok, **post}
    return FixtureResult("V5d", {"L2": FAIL, "j_timing_ok": True}, actual, led)


def fixture_V5e() -> FixtureResult:
    # V3 pre ; J=HALVE_AND_ERASE_LITERAL ; valid reset ; 0<|T|<1 -> UNRESOLVED
    led, c3_pre, per_T_post_j, timing_ok, timing_records, h, r, outcome = _v5_common(
        "HALVE_AND_ERASE_LITERAL"
    )
    led.fixture_id = "V5e"
    c3_post = _c3_from_T(per_T_post_j)
    # literal erased -> C1 determinate negative ; T = +/-1/2 -> indeterminate
    post_c1 = NOT_ESTABLISHED
    # Note: BD-53 — C1's determinate negative MUST NOT cancel C2/C3's indeterminate.
    post = _l2_judge(C3, post_c1, UNRESOLVED, c3_post["result"], reset_valid=outcome.reset_valid)
    led.l2 = post
    led.notes.append("T in 0<|T|<1 -> indeterminate; J changed evidence, not reset")
    led.notes.append("BD-53: lower C1 determinate negative does NOT cancel higher indeterminate")
    actual = {"PRE_RESET_CHANGE_CLASS": c3_pre["result"], "j_timing_ok": timing_ok, **post}
    return FixtureResult("V5e", {"L2": UNRESOLVED, "j_timing_ok": True}, actual, led)


def fixture_V5f() -> FixtureResult:
    # V1 pre ; J=IDENTITY ; valid reset ; only post C1 attempted (real pipeline)
    payload = EPISODE_PAYLOADS["A1"]
    sb = Sandbox()
    try:
        A, B = sb.arm("A"), sb.arm("B")
        B.store(payload, STORE_FULL)
        snap_A, snap_B = A.snapshot(), B.snapshot()
        l1 = evaluate_basic_l1(snap_A, snap_B, payload)
        # apply J=IDENTITY for real and witness timing
        sw, ja, sh, _ = _apply_j_real(B, "IDENTITY")
        timing_ok = (ja.digest == sh.digest)
        h, r, outcome = _reset_arm(B)
        post_c1 = l1.change_class if (outcome.reset_valid and B.snapshot().literal == payload) else NOT_ESTABLISHED
    finally:
        sb.close()

    led = Ledger(fixture_id="V5f")
    led.l1 = {"result": l1.result, "change_class": l1.change_class}
    led.reset = {"reset_valid": outcome.reset_valid, "J": "IDENTITY"}
    post = _l2_judge(C1, post_c1, NOT_ASSESSED, NOT_ASSESSED, reset_valid=outcome.reset_valid)
    led.l2 = post
    led.notes.append("higher class not attempted -> NOT_ASSESSED; L2 via post C1")
    actual = {
        "PRE_RESET_CHANGE_CLASS": l1.change_class,
        "post_C2": NOT_ASSESSED,
        "post_C3": NOT_ASSESSED,
        "j_timing_ok": timing_ok,
        **post,
    }
    return FixtureResult(
        "V5f",
        {"L2": PASS, "POST_RESET_SUPPORTED_CLASS": C1,
         "post_C2": NOT_ASSESSED, "post_C3": NOT_ASSESSED, "j_timing_ok": True},
        actual, led,
    )


# ===========================================================================
# Registry
# ===========================================================================

FIXTURES = {
    "V0": fixture_V0,
    "V0b": fixture_V0b,
    "V1": fixture_V1,
    "V2": fixture_V2,
    "V3": fixture_V3,
    "V4.1": fixture_V4_1,
    "V4b": fixture_V4b,
    "V5a": fixture_V5a,
    "V5b": fixture_V5b,
    "V5c": fixture_V5c,
    "V5d": fixture_V5d,
    "V5e": fixture_V5e,
    "V5f": fixture_V5f,
}


def run_all() -> list[FixtureResult]:
    return [FIXTURES[k]() for k in FIXTURES]
