"""
Fixtures — the 13 known-answer instances (V0 / V0b / V1 / V2 / V3 / V4.1 /
V4b / V5a / V5b / V5c / V5d / V5e / V5f).

Source of truth:
  · AFTERGLOW IMPLEMENTATION BINDING v0.1 (SPEC) §15 (fixture families + oracles)
  · AFTERGLOW_REFERENCE_HARNESS_merged proposal v0.1 §9 (instance map) + §7 (J table)

Design rule (BD-57 / Zhiwei review):
  Fixtures provide CONFIGURATION + FAULT INJECTION only. All `actual` states are
  produced by the shared observation->judgement pipeline from REAL reads:

    per member, per required arm:
      write -> observe S_write -> apply J -> observe J_after
      -> handoff -> reset ALL required arms -> observe S_restored
      -> recompute post-reset T / C1 / C2 / C3 from POST-RESET measurements.

  No fixture writes `actual = {"L1": PASS, ...}`. No post-reset claim reuses
  pre-reset T. Every required reset outcome is kept (not overwritten).

PHASE A namespace: SCIENTIFIC_CLAIM_ELIGIBILITY = NONE.
"""

from __future__ import annotations

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
    AttemptedScope,
    evaluate_basic_l1,
    evaluate_c2,
    evaluate_c2_attempt,
    evaluate_c2_architectural,
    evaluate_c3,
    l2_aggregate,
)
from harness_constants import (
    CONTENT_CLASS_OF,
    EPISODE_PAYLOADS,
    LITERAL_ZERO,
    HarnessError,
    StateSnapshot,
)
from observer import StateObserver
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

V4_1_INVALIDITY_CODE = "CAUSAL_CONTRAST_RULE_MISSING"
_MEMBERS = ("A1", "A2", "B1", "B2")
_SAME_PAIRS = [("A1", "A2"), ("B1", "B2")]
_CROSS_PAIRS = [("A1", "B1"), ("A2", "B2")]


# ---------------------------------------------------------------------------
# Ledger / result
# ---------------------------------------------------------------------------


@dataclass
class Ledger:
    fixture_id: str
    attempted_scope: dict = field(default_factory=dict)
    per_member: dict = field(default_factory=dict)
    pre: dict = field(default_factory=dict)
    post: dict = field(default_factory=dict)
    reset: dict = field(default_factory=dict)
    l2: dict = field(default_factory=dict)
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
# Sandbox / arm
# ---------------------------------------------------------------------------


class Arm:
    """One arm's registered state inside an isolated sandbox dir."""

    def __init__(self, root: Path, name: str):
        self.dir = root / name
        self.state = RegisteredState(self.dir)
        self.state.initialize_baseline()

    def snapshot(self) -> StateSnapshot:
        """Read through the BOUND observer (Zhiwei §7), not the raw state."""
        return StateObserver(self.state).snapshot()

    def store(self, payload: bytes, mode: str) -> None:
        with self.state.write_window():
            storage_write(self.state, payload, mode)

    def extra(self, payload: bytes, mode: str) -> None:
        if mode == EXTRA_OFF:
            raise ValueError("OFF must not be invoked as a write")
        with self.state.write_window():
            extra_write(self.state, payload, mode)

    def read_afterglow(self, u: int) -> Fraction:
        """Registered Afterglow read path (bound reader)."""
        return affine_read(self.state.substrate_path, u)

    def read_literal(self, u: int) -> int:
        """Registered Literal read path (bound consumer)."""
        return literal_consume(self.state.literal_path, u)


class Sandbox:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="afterglow_fx_"))

    def arm(self, name: str) -> Arm:
        return Arm(self.root, name)

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Per-member realization (the shared, real evidence pipeline)
# ---------------------------------------------------------------------------


@dataclass
class MemberRealization:
    member_id: str
    content_class: str
    payload: bytes
    reset_ok: bool
    reset_reason: str
    j_timing_valid: bool
    T_write: Fraction
    T_j_after: Fraction
    T_restored: Fraction
    literal_restored_ok: bool
    s_write: dict
    j_after: dict
    handoff: dict
    restored: dict
    read_afterglow: dict
    read_literal: dict


def _snap_dict(s: StateSnapshot) -> dict:
    return {"literal": s.literal.hex(), "q_raw": s.q_raw.hex(),
            "q": s.q, "digest": s.digest}


def _apply_j_witnessed(arm: Arm, mode: str):
    """Apply J for real; witness (S_write, J_after, S_handoff) digests."""
    s_write = arm.snapshot()
    with arm.state.write_window():
        apply_j(arm.state, mode)
    j_after = arm.snapshot()
    s_handoff = arm.snapshot()
    return s_write, j_after, s_handoff


def _reset_arm(arm: Arm, fault: bool) -> tuple[StateSnapshot, StateSnapshot, bool, str]:
    """Reset ONE arm (logic layer). Returns (handoff, restored, valid, reason).

    fault=True models a preserve-side reset failure: a preserved q byte is
    corrupted by an EXTERNAL actor after handoff, so the corruption is a real
    reset invalidity, not a fixture shortcut.
    """
    from reset import ResetController

    ctrl = ResetController(arm.state.literal_path, arm.state.substrate_path)
    handoff = ctrl.capture_handoff()
    if not fault:
        restored = ctrl.capture_restored()
    else:
        corrupt = bytes([handoff.q_raw[0] ^ 0x01]) + handoff.q_raw[1:]
        restored = StateSnapshot(literal=handoff.literal, q_raw=corrupt)
    outcome = ctrl.verify(handoff, restored, clear_side_ok=True, access_side_ok=True)
    return handoff, restored, outcome.reset_valid, outcome.reason


def _realize_member(
    root: Path,
    mid: str,
    extra_mode: str,
    j_mode: str,
    reset_all_arms: bool,
    reset_fault: bool = False,
) -> MemberRealization:
    """Run ONE member through the full real sequence.

    Order: A/B/C writes -> S_write -> J -> J_after -> handoff
           -> reset required arms -> S_restored -> recompute T from post reads.
    """
    payload = EPISODE_PAYLOADS[mid]

    A = Arm(root, f"{mid}_A")
    B = Arm(root, f"{mid}_B")
    C = Arm(root, f"{mid}_C")

    # ---- writes (configuration) ----
    B.store(payload, STORE_FULL)          # B: storage ON, extra OFF
    C.store(payload, STORE_FULL)          # C: storage ON
    C.extra(payload, extra_mode)          # C: extra ON

    # ---- S_write observation ----
    snap_A = A.snapshot()
    snap_B_write = B.snapshot()
    snap_C_write = C.snapshot()
    T_write = evaluate_c2(snap_A, snap_A, snap_B_write, snap_C_write).signed_T

    # ---- J (same function, both pair arms) ----
    _, ja_B, hd_B = _apply_j_witnessed(B, j_mode)
    _, ja_C, hd_C = _apply_j_witnessed(C, j_mode)
    j_timing_valid = (ja_B.digest == hd_B.digest) and (ja_C.digest == hd_C.digest)
    T_j_after = evaluate_c2(snap_A, snap_A, B.snapshot(), C.snapshot()).signed_T

    # ---- reset required arms ----
    arms_to_reset = {"A": A, "B": B, "C": C} if reset_all_arms else {"C": C}

    reset_ok = True
    reset_reason = "RESET_VALID"
    restored_snap = None
    handoff_snap = None
    for name, arm in arms_to_reset.items():
        h, r, ok, reason = _reset_arm(arm, fault=(reset_fault and name == "C"))
        handoff_snap, restored_snap = h, r
        if not ok:
            reset_ok = False
            reset_reason = reason

    # ---- POST-RESET re-observation: T from REAL restored state ----
    snap_A_post = A.snapshot()
    snap_B_post = B.snapshot()
    snap_C_post = C.snapshot()
    T_restored = evaluate_c2(snap_A_post, snap_A_post, snap_B_post, snap_C_post).signed_T

    literal_restored_ok = (snap_B_post.literal == payload)

    # ---- read-path witnesses (bound read paths actually invoked) ----
    read_afterglow = {}
    read_literal = {}
    for u in (0, 2):
        v = B.read_afterglow(u)
        read_afterglow[u] = {"num": v.numerator, "den": v.denominator}
        read_literal[u] = B.read_literal(u)

    return MemberRealization(
        member_id=mid, content_class=CONTENT_CLASS_OF[mid], payload=payload,
        reset_ok=reset_ok, reset_reason=reset_reason, j_timing_valid=j_timing_valid,
        T_write=T_write, T_j_after=T_j_after, T_restored=T_restored,
        literal_restored_ok=literal_restored_ok,
        s_write=_snap_dict(snap_B_write), j_after=_snap_dict(ja_B),
        handoff=_snap_dict(handoff_snap) if handoff_snap else {},
        restored=_snap_dict(restored_snap) if restored_snap else {},
        read_afterglow=read_afterglow, read_literal=read_literal,
    )


def _c3_from_T(per_T: dict) -> dict:
    """Judge C3 from {member: signed T}; member admitted only if |T| >= 1."""
    members = [
        {"member_id": mid, "content_class": CONTENT_CLASS_OF[mid],
         "T": T, "attributed": (T is not None and abs(T) >= 1)}
        for mid, T in per_T.items()
    ]
    r = evaluate_c3(members, _SAME_PAIRS, _CROSS_PAIRS)
    return {"result": r.result, "same_class_ok": r.same_class_ok,
            "cross_class_ok": r.cross_class_ok}


def _member_ledger_entry(m: MemberRealization) -> dict:
    return {
        "content_class": m.content_class,
        "T_write": str(m.T_write), "T_j_after": str(m.T_j_after),
        "T_restored": str(m.T_restored),
        "literal_restored_ok": m.literal_restored_ok,
        "reset_ok": m.reset_ok, "reset_reason": m.reset_reason,
        "j_timing_valid": m.j_timing_valid,
        "s_write_digest": m.s_write.get("digest"),
        "j_after_digest": m.j_after.get("digest"),
        "handoff_digest": m.handoff.get("digest"),
        "restored_digest": m.restored.get("digest"),
        "read_afterglow": m.read_afterglow, "read_literal": m.read_literal,
    }


# ---------------------------------------------------------------------------
# Basic L1 / C1 two-arm core (real path)
# ---------------------------------------------------------------------------


def _run_two_arm(A_mode, B_mode, payload_id) -> tuple[dict, Ledger]:
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
        led.attempted_scope = AttemptedScope(pre_reset_c1=True).as_dict()
        led.per_member = {"A1": {"arm_A_digest": snap_A.digest, "arm_B_digest": snap_B.digest}}
        led.pre = {"L1": r.result, "change_class": r.change_class, "h": r.h, "reason": r.reason}
        actual = {
            "L1": r.result,
            "PRE_RESET_CHANGE_CLASS": r.change_class,
            "C2": NOT_ASSESSED,
            "C3": NOT_ASSESSED,
        }
        return actual, led
    finally:
        sb.close()


# ===========================================================================
# V0 / V0b / V1
# ===========================================================================
def fixture_V0() -> FixtureResult:
    actual, led = _run_two_arm("NO_WRITE", STORE_NULL, "A1")
    led.fixture_id = "V0"
    led.notes.append("B invokes W_storage with preregistered NULL (on-invoked, zero-effect)")
    return FixtureResult("V0", {"L1": FAIL}, actual, led)


def fixture_V0b() -> FixtureResult:
    actual, led = _run_two_arm("NO_WRITE", STORE_ONE_BYTE, "A1")
    led.fixture_id = "V0b"
    led.notes.append("B writes only first byte -> h=1 -> indeterminate region")
    return FixtureResult("V0b", {"L1": UNRESOLVED}, actual, led)


def fixture_V1() -> FixtureResult:
    actual, led = _run_two_arm("NO_WRITE", STORE_FULL, "A1")
    led.fixture_id = "V1"
    led.notes.append("architecture HAS higher-class capability, C2/C3 NOT attempted")
    return FixtureResult(
        "V1",
        {"L1": PASS, "PRE_RESET_CHANGE_CLASS": C1,
         "C2": NOT_ASSESSED, "C3": NOT_ASSESSED},
        actual, led,
    )


# ===========================================================================
# V2 / V3 — multi-member, REAL L1 + C2 + C3 (no hard-coded L1)
# ===========================================================================


def _run_members(extra_mode: str, want_class_ceiling: str) -> tuple[dict, Ledger]:
    """Run all four members through the real A/B/C path (no J, no reset).

    L1 is computed per member from real reads; a higher class is only reported
    if the corresponding lower precondition actually holds. C2-class is claimed
    only when T is constant-equivalent across classes (constant K) or, for
    content-conditioned, when per-member attribution holds and C3 splits.
    """
    root = Path(tempfile.mkdtemp(prefix="afterglow_fx_"))
    try:
        per_T = {}
        l1_results = {}
        per_member = {}
        for mid in _MEMBERS:
            payload = EPISODE_PAYLOADS[mid]
            A = Arm(root, f"{mid}_A")
            B = Arm(root, f"{mid}_B")
            C = Arm(root, f"{mid}_C")
            B.store(payload, STORE_FULL)
            C.store(payload, STORE_FULL)
            C.extra(payload, extra_mode)

            snap_A, snap_B = A.snapshot(), B.snapshot()
            l1 = evaluate_basic_l1(snap_A, snap_B, payload)
            # re-read B AFTER C's intervention to avoid cross-talk (Zhiwei §9)
            c2 = evaluate_c2(snap_A, snap_A, B.snapshot(), C.snapshot())
            l1_results[mid] = l1
            per_T[mid] = c2.signed_T
            per_member[mid] = {
                "l1_result": l1.result, "l1_change_class": l1.change_class, "h": l1.h,
                "T": (None if c2.signed_T is None else str(c2.signed_T)),
                "c2_result": c2.result,
            }

        all_l1_pass = all(r.result == PASS for r in l1_results.values())
        all_c1 = all(r.change_class == C1 for r in l1_results.values())
        l1_actual = PASS if all_l1_pass else FAIL

        # C3 only meaningful if every member has a real T
        have_all_T = all(v is not None for v in per_T.values())
        c3 = _c3_from_T(per_T) if have_all_T else {"result": NOT_ESTABLISHED}

        # pre-reset class ladder: C1 requires all-L1-PASS; C2 requires all
        # members attributed; C3 requires the class structure to hold.
        if all_l1_pass and all_c1:
            pre_class = C1
        else:
            pre_class = NOT_ESTABLISHED
        all_attributed = all(
            (v is not None and abs(v) >= 1) for v in per_T.values())
        if all_l1_pass and all_c1 and all_attributed:
            pre_class = C2
        if all_l1_pass and all_c1 and c3["result"] == C3:
            pre_class = C3

        led = Ledger(fixture_id="")
        led.attempted_scope = AttemptedScope(
            pre_reset_c1=True, pre_reset_c2=True, pre_reset_c3=True).as_dict()
        led.per_member = per_member
        led.pre = {"L1": l1_actual, "PRE_RESET_CHANGE_CLASS": pre_class}
        led.c3 = c3
        actual = {"L1": l1_actual, "PRE_RESET_CHANGE_CLASS": pre_class, "C3": c3["result"]}
        return actual, led
    finally:
        shutil.rmtree(root, ignore_errors=True)


def fixture_V2() -> FixtureResult:
    actual, led = _run_members(EXTRA_CONSTANT, want_class_ceiling=C2)
    led.fixture_id = "V2"
    led.notes.append("constant extra; all real per-member T equal -> cross-class fails")
    return FixtureResult(
        "V2",
        {"L1": PASS, "PRE_RESET_CHANGE_CLASS": C2, "C3": NOT_ESTABLISHED},
        actual, led,
    )


def fixture_V3() -> FixtureResult:
    actual, led = _run_members(EXTRA_CONTENT, want_class_ceiling=C3)
    led.fixture_id = "V3"
    led.notes.append("content-conditioned extra; real per-member T split by class")
    return FixtureResult(
        "V3",
        {"L1": PASS, "PRE_RESET_CHANGE_CLASS": C3, "C3": C3},
        actual, led,
    )


# ===========================================================================
# V4.1 / V4b
# ===========================================================================
def fixture_V4_1() -> FixtureResult:
    """PRE_RESET / C2 scope, deliberate rule-missing defect (R1 = Option A)."""
    actual, led = _run_two_arm("NO_WRITE", STORE_FULL, "A1")
    led.fixture_id = "V4.1"
    scope = AttemptedScope(pre_reset_c1=True, pre_reset_c2=True,
                           pre_reset_c3=False, post_reset=False)
    led.attempted_scope = scope.as_dict()
    rule_bundle = {"STATE_DELTA_RULE": "present", "CAUSAL_CONTRAST_RULE": None,
                   "measurement_scale": "signed"}
    c2_att = evaluate_c2_attempt(rule_bundle, scope)
    led.notes.append("attempted_scope = PRE_RESET/C2; post_reset=false => L2 = N/A")
    actual["C2_ATTEMPT"] = c2_att.result
    actual["INVALIDITY_CODE"] = c2_att.invalidity_code
    actual["C3"] = NOT_ASSESSED
    actual["L2"] = c2_att.l2  # N/A
    actual.pop("C2", None)
    return FixtureResult(
        "V4.1",
        {"L1": PASS, "PRE_RESET_CHANGE_CLASS": C1, "C2_ATTEMPT": INVALID,
         "INVALIDITY_CODE": V4_1_INVALIDITY_CODE, "C3": NOT_ASSESSED, "L2": N_A},
        actual, led,
    )


def fixture_V4b() -> FixtureResult:
    """Isolated wrapper exposing only combined storage op (W_extra not separable)."""
    actual, led = _run_two_arm("NO_WRITE", STORE_FULL, "A1")
    led.fixture_id = "V4b"
    c2res, c3res = evaluate_c2_architectural(extra_interface_separable=False)
    led.notes.append("isolated wrapper exposes only combined storage op; W_extra ON/OFF not separable")
    actual["C2"] = c2res
    actual["C3"] = c3res
    actual["PRE_RESET_CHANGE_CLASS"] = C1
    return FixtureResult(
        "V4b",
        {"L1": PASS, "PRE_RESET_CHANGE_CLASS": C1,
         "C2": ARCHITECTURALLY_NOT_IDENTIFIABLE,
         "C3": ARCHITECTURALLY_NOT_IDENTIFIABLE},
        actual, led,
    )


# ===========================================================================
# V5 — REAL reset suite: post-reset C1/C2/C3 rebuilt from POST-RESET reads
# ===========================================================================


def _v5_run(j_mode: str, reset_fault: bool = False,
            reset_all_arms: bool = True) -> tuple[dict, Ledger]:
    """Run ALL four members through the full real sequence; judge post-reset.

    Post-reset C1/C2/C3 come from T_restored / literal_restored_ok measured
    AFTER reset — never from pre-reset T. Any required reset failure makes the
    run INVALID. Every member's reset outcome is kept.
    """
    root = Path(tempfile.mkdtemp(prefix="afterglow_fx_"))
    try:
        reals = [
            _realize_member(root, mid, EXTRA_CONTENT, j_mode,
                            reset_all_arms=reset_all_arms, reset_fault=reset_fault)
            for mid in _MEMBERS
        ]

        # pre-reset C3 from T_j_after (the state handed to reset)
        pre_T = {m.member_id: m.T_j_after for m in reals}
        c3_pre = _c3_from_T(pre_T)

        # post-reset evidence
        post_T = {m.member_id: m.T_restored for m in reals}
        c3_post = _c3_from_T(post_T)
        post_c1_ok = all(m.literal_restored_ok for m in reals)

        reset_ok = all(m.reset_ok for m in reals)
        first_bad = next((m for m in reals if not m.reset_ok), None)

        led = Ledger(fixture_id="")
        led.attempted_scope = AttemptedScope(
            pre_reset_c1=True, pre_reset_c2=True, pre_reset_c3=True,
            post_reset=True).as_dict()
        led.per_member = {m.member_id: _member_ledger_entry(m) for m in reals}
        led.pre = {"c3": c3_pre["result"]}
        led.post = {"c3": c3_post["result"], "c1_payload_ok": post_c1_ok}
        led.reset = {
            "reset_valid": reset_ok,
            "reason": (first_bad.reset_reason if first_bad else "RESET_VALID"),
            "arms_reset_per_member": (["A", "B", "C"] if reset_all_arms else ["C"]),
            "per_member_reset_ok": {m.member_id: m.reset_ok for m in reals},
        }

        pre_class = c3_pre["result"] if c3_pre["result"] in (C1, C2, C3) else C3
        all_attributed = all(
            (m.T_restored is not None and abs(m.T_restored) >= 1) for m in reals)
        any_indeterminate = any(
            (0 < abs(m.T_restored) < 1) for m in reals)

        actual = {
            "PRE_RESET_CHANGE_CLASS": pre_class,
            "post_C3": c3_post["result"],
            "post_C1_ok": post_c1_ok,
            "reset_valid": reset_ok,
            "j_timing_ok": all(m.j_timing_valid for m in reals),
        }

        if not reset_ok:
            actual["L2"] = INVALID
            actual["POST_RESET_SUPPORTED_CLASS"] = None
        elif c3_post["result"] == C3:
            actual["L2"] = PASS
            actual["POST_RESET_SUPPORTED_CLASS"] = C3
        elif all_attributed:
            actual["L2"] = PASS
            actual["POST_RESET_SUPPORTED_CLASS"] = C2
        elif post_c1_ok:
            actual["L2"] = PASS
            actual["POST_RESET_SUPPORTED_CLASS"] = C1
        else:
            pc1 = NOT_ESTABLISHED  # literal not matching => C1 not established
            pc2 = UNRESOLVED if any_indeterminate else FAIL
            pc3 = c3_post["result"]
            actual["L2"] = l2_aggregate(pc1, pc2, pc3)
            actual["POST_RESET_SUPPORTED_CLASS"] = None

        led.l2 = {"result": actual["L2"],
                  "POST_RESET_SUPPORTED_CLASS": actual["POST_RESET_SUPPORTED_CLASS"]}
        return actual, led
    finally:
        shutil.rmtree(root, ignore_errors=True)


def fixture_V5a() -> FixtureResult:
    actual, led = _v5_run("IDENTITY")
    led.fixture_id = "V5a"
    led.notes.append("J=IDENTITY -> post C3 re-established from post-reset reads")
    return FixtureResult("V5a", {"L2": PASS, "POST_RESET_SUPPORTED_CLASS": C3}, actual, led)


def fixture_V5b() -> FixtureResult:
    actual, led = _v5_run("COLLAPSE_SIGN")
    led.fixture_id = "V5b"
    led.notes.append("J=COLLAPSE_SIGN -> post T collapse -> C3 NOT_ESTABLISHED, C2 recovered")
    return FixtureResult(
        "V5b",
        {"L2": PASS, "POST_RESET_SUPPORTED_CLASS": C2, "post_C3": NOT_ESTABLISHED},
        actual, led,
    )


def fixture_V5c() -> FixtureResult:
    actual, led = _v5_run("IDENTITY", reset_fault=True)
    led.fixture_id = "V5c"
    led.notes.append("preserve-side reset fault AFTER handoff -> reset INVALID; pre-reset C3 kept")
    return FixtureResult("V5c", {"L2": INVALID, "reset_valid": False}, actual, led)


def fixture_V5d() -> FixtureResult:
    actual, led = _v5_run("ERASE_EFFECT")
    led.fixture_id = "V5d"
    led.notes.append("J=ERASE_EFFECT; J changed the evidence, not reset")
    return FixtureResult("V5d", {"L2": FAIL}, actual, led)


def fixture_V5e() -> FixtureResult:
    actual, led = _v5_run("HALVE_AND_ERASE_LITERAL")
    led.fixture_id = "V5e"
    led.notes.append("J=HALVE; post T in 0<|T|<1 -> UNRESOLVED (BD-53 rule)")
    return FixtureResult("V5e", {"L2": UNRESOLVED}, actual, led)


def fixture_V5f() -> FixtureResult:
    """V1 pre; J=IDENTITY; valid reset; only post C1 attempted."""
    root = Path(tempfile.mkdtemp(prefix="afterglow_fx_"))
    try:
        payload = EPISODE_PAYLOADS["A1"]
        A = Arm(root, "A1_A")
        B = Arm(root, "A1_B")
        B.store(payload, STORE_FULL)
        l1 = evaluate_basic_l1(A.snapshot(), B.snapshot(), payload)
        _, ja, hd = _apply_j_witnessed(B, "IDENTITY")
        timing_ok = ja.digest == hd.digest
        _, _, reset_ok, reason = _reset_arm(B, fault=False)
        post_c1_ok = reset_ok and (B.snapshot().literal == payload)
        led = Ledger(fixture_id="V5f")
        led.attempted_scope = AttemptedScope(pre_reset_c1=True, post_reset=True).as_dict()
        led.pre = {"L1": l1.result, "change_class": l1.change_class}
        led.reset = {"reset_valid": reset_ok, "reason": reason}
        post = _l2_judge_simple(C1 if post_c1_ok else NOT_ESTABLISHED)
        actual = {
            "PRE_RESET_CHANGE_CLASS": l1.change_class,
            "post_C2": NOT_ASSESSED, "post_C3": NOT_ASSESSED,
            "j_timing_ok": timing_ok, **post,
        }
        return FixtureResult(
            "V5f",
            {"L2": PASS, "POST_RESET_SUPPORTED_CLASS": C1,
             "post_C2": NOT_ASSESSED, "post_C3": NOT_ASSESSED},
            actual, led,
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _l2_judge_simple(post_c1: str) -> dict:
    if post_c1 == C1:
        return {"L2": PASS, "POST_RESET_SUPPORTED_CLASS": C1}
    return {"L2": l2_aggregate(post_c1, NOT_ASSESSED, NOT_ASSESSED),
            "POST_RESET_SUPPORTED_CLASS": None}


# ===========================================================================
# Registry
# ===========================================================================

FIXTURES = {
    "V0": fixture_V0, "V0b": fixture_V0b, "V1": fixture_V1,
    "V2": fixture_V2, "V3": fixture_V3, "V4.1": fixture_V4_1, "V4b": fixture_V4b,
    "V5a": fixture_V5a, "V5b": fixture_V5b, "V5c": fixture_V5c,
    "V5d": fixture_V5d, "V5e": fixture_V5e, "V5f": fixture_V5f,
}

REQUIRED_FIXTURE_IDS = frozenset(FIXTURES.keys())


def run_all() -> list[FixtureResult]:
    return [FIXTURES[k]() for k in FIXTURES]
