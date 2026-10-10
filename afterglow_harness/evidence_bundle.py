"""
evidence_bundle.py — the unified EVIDENCE_BUNDLE + its validation (RC9).

凌翼 RC9: there is ONE evidence object that both production qualification and
ledger replay must use; nothing may bypass it.

    EVIDENCE_BUNDLE = member × arm × phase × raw observation × protocol witness

Required chain (any protocol-invalid layer => INVALID; INVALID dominates):

    FROZEN MEMBER SET
      -> required arms present
      -> S_write raw observations valid
      -> PRE gate
      -> required_pre_class satisfied
      -> J witness valid
      -> J S_handoff == RESET accepted handoff   (byte-level)
      -> reset valid
      -> S_restored observations valid
      -> reader / literal-consumer witnesses valid
      -> POST gate
      -> L2

INVALID is NOT "highest tier not established, try next". Only a *legitimate*
NOT_ESTABLISHED permits lower-class fallback. INVALID and NOT_ESTABLISHED are
kept strictly distinct here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from evaluator import (
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
)
from harness_constants import CONTENT_CLASS_OF, StateSnapshot, canonical_state_digest

_SAME_PAIRS = [("A1", "A2"), ("B1", "B2")]
_CROSS_PAIRS = [("A1", "B1"), ("A2", "B2")]

VALID_PROTOCOL = PASS
INVALID_PROTOCOL = INVALID


# ---------------------------------------------------------------------------
# Raw observation object
# ---------------------------------------------------------------------------


@dataclass
class ArmPhase:
    """Raw bytes for one arm at one phase. Digest is DERIVED, never trusted."""
    literal: bytes
    q_raw: bytes

    def snapshot(self) -> StateSnapshot:
        return StateSnapshot(literal=self.literal, q_raw=self.q_raw)

    @property
    def digest(self) -> str:
        return canonical_state_digest(self.literal, self.q_raw)


@dataclass
class MemberEvidence:
    member_id: str
    content_class: str
    payload: bytes
    # arm -> phase -> ArmPhase
    arms: dict = field(default_factory=dict)
    # arm -> {"reset_valid": bool, "reason": str, "clear_access": str}
    reset_witness: dict = field(default_factory=dict)
    # reader/literal witnesses: {"raw_q": int, "affine": {u: Fraction-or-str}, "literal": {u: int}}
    reader_witness: dict = field(default_factory=dict)


@dataclass
class EvidenceBundle:
    fixture_id: str
    members: dict = field(default_factory=dict)  # member_id -> MemberEvidence
    required_members: tuple = ()
    required_arms: tuple = ("A", "B", "C")
    required_phases: tuple = ("S_write", "S_handoff", "S_restored")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_membership(b: EvidenceBundle) -> tuple[bool, str]:
    frozen = set(b.required_members)
    got = set(b.members.keys())
    if frozen != got:
        return False, f"MEMBER_SET_MISMATCH: frozen={sorted(frozen)} got={sorted(got)}"
    return True, ""


def _validate_arms_phases(b: EvidenceBundle) -> tuple[bool, str]:
    for mid, m in b.members.items():
        for arm in b.required_arms:
            if arm not in m.arms:
                return False, f"REQUIRED_ARM_MISSING: {mid}/{arm}"
            for ph in ("S_write", "S_restored"):
                if ph not in m.arms[arm]:
                    return False, f"REQUIRED_PHASE_MISSING: {mid}/{arm}/{ph}"
    return True, ""


def _validate_bytes(b: EvidenceBundle) -> tuple[bool, str]:
    """Raw-byte/digest consistency: re-derive digest from raw bytes."""
    from harness_constants import LITERAL_SIZE, SUBSTRATE_SIZE

    for mid, m in b.members.items():
        for arm, phases in m.arms.items():
            for ph, ap in phases.items():
                if len(ap.literal) != LITERAL_SIZE or len(ap.q_raw) != SUBSTRATE_SIZE:
                    return False, f"RAW_WIDTH: {mid}/{arm}/{ph}"
    return True, ""


def _validate_j_witness(b: EvidenceBundle) -> tuple[bool, str]:
    """Per pair arm (B/C): J_after must EQUAL J's S_handoff (byte-level), i.e. no
    state change happened between the J-applied observation and the handoff."""
    for mid, m in b.members.items():
        for arm in ("B", "C"):
            phases = m.arms.get(arm, {})
            ja = phases.get("J_after")
            sh = phases.get("S_handoff")
            if ja is None or sh is None:
                return False, f"J_WITNESS_MISSING: {mid}/{arm}"
            if ja.literal != sh.literal or ja.q_raw != sh.q_raw:
                return False, f"J_TIMING_INVALID: {mid}/{arm} J_after != S_handoff (byte-level)"
    return True, ""


def _validate_handoff_continuity(b: EvidenceBundle) -> tuple[bool, str]:
    """J S_handoff must EQUAL the reset-accepted handoff, per arm (byte-level).

    For B/C pair arms: reset input must equal J's S_handoff.
    For A (no J): reset input must equal A's S_write.
    """
    for mid, m in b.members.items():
        for arm in b.required_arms:
            phases = m.arms.get(arm, {})
            j_sh = phases.get("S_handoff")
            sw = phases.get("S_write")
            accepted = m.reset_witness.get(arm, {}).get("accepted_handoff")
            if accepted is None:
                return False, f"RESET_HANDOFF_MISSING: {mid}/{arm}"
            acc = ArmPhase(bytes.fromhex(accepted["literal"]), bytes.fromhex(accepted["q_raw"]))
            expected = j_sh if j_sh is not None else sw
            if expected is None:
                return False, f"HANDOFF_INPUT_MISSING: {mid}/{arm}"
            if (acc.literal != expected.literal) or (acc.q_raw != expected.q_raw):
                return False, (f"HANDOFF_CONTINUITY_BREAK: {mid}/{arm} "
                               f"expected==accepted failed (byte-level)")
    return True, ""


def _independent_reader_ok(m: MemberEvidence) -> bool:
    """Recompute expected R(q,u)=u+q/2 and L(lit,u)=u+sum(bytes) from RAW values
    and compare to the reader's returned values.

    The reader is invoked AFTER reset, so it reads the C arm's S_restored state.
    """
    rw = m.reader_witness
    if not rw:
        return False
    q = rw.get("raw_q")
    if q is None:
        return False
    aff = rw.get("affine", {})
    for u_s, got in aff.items():
        u = int(u_s)
        expected = Fraction(2 * u + q, 2)
        if Fraction(got["num"], got["den"]) != expected:
            return False
    lit = rw.get("literal", {})
    c_restored = m.arms.get("C", {}).get("S_restored")
    if c_restored is None:
        return False
    byte_sum = sum(c_restored.literal)
    for u_s, got in lit.items():
        u = int(u_s)
        if got != u + byte_sum:
            return False
    return True


# ---------------------------------------------------------------------------
# PRE / POST from a bundle (with INVALID dominance)
# ---------------------------------------------------------------------------


@dataclass
class GateResult:
    protocol: str          # PASS | INVALID
    code: str
    pre_class: str = ""
    c2_pre: str = NOT_ASSESSED
    c3_pre: str = NOT_ASSESSED
    t_write: dict = field(default_factory=dict)
    c3_post: str = NOT_ASSESSED
    post_c1_ok: bool = False
    t_restored: dict = field(default_factory=dict)
    l2: str = ""
    supported: str | None = None


def evaluate_bundle(b: EvidenceBundle, required_pre_class: str,
                    expected_post_supported_class: str | None,
                    attempted: str = "full") -> GateResult:
    """Run the full chain; INVALID dominates anywhere protocol fails."""
    out = GateResult(protocol=VALID_PROTOCOL, code="")

    for ok, code in (_validate_membership(b), _validate_arms_phases(b),
                     _validate_bytes(b)):
        if not ok:
            return GateResult(protocol=INVALID_PROTOCOL, code=code,
                              l2=INVALID, c3_post=INVALID)

    # ---- PRE gate (source = S_write) ----
    pre = _pre_from_bundle(b)
    out.pre_class, out.c2_pre, out.c3_pre, out.t_write = pre
    if out.c3_pre == INVALID or out.c2_pre == INVALID:
        return GateResult(protocol=INVALID_PROTOCOL, code="PRE_MEASUREMENT_INVALID",
                          pre_class=out.pre_class, l2=INVALID, c3_post=INVALID,
                          t_write=out.t_write)

    # required_pre_class is a CONTRACT precondition
    if required_pre_class and out.pre_class != required_pre_class:
        return GateResult(protocol=INVALID_PROTOCOL,
                          code=f"PROFILE_PRECONDITION_FAILED: required_pre_class="
                               f"{required_pre_class} got={out.pre_class}",
                          pre_class=out.pre_class, c2_pre=out.c2_pre, c3_pre=out.c3_pre,
                          t_write=out.t_write, l2=INVALID, c3_post=INVALID)

    # ---- J timing + handoff continuity ----
    j_ok, j_code = _validate_j_witness(b)
    if not j_ok:
        return GateResult(protocol=INVALID_PROTOCOL, code=j_code, l2=INVALID, c3_post=INVALID)
    hc_ok, hc_code = _validate_handoff_continuity(b)
    if not hc_ok:
        return GateResult(protocol=INVALID_PROTOCOL, code=hc_code, l2=INVALID, c3_post=INVALID)

    # ---- reset validity ----
    for mid, m in b.members.items():
        for arm in b.required_arms:
            rw = m.reset_witness.get(arm, {})
            if rw.get("reset_valid") is False:
                return GateResult(protocol=INVALID_PROTOCOL,
                                  code=f"RESET_INVALID: {mid}/{arm}", l2=INVALID, c3_post=INVALID)

    # ---- reader witnesses (must be validated) ----
    for mid, m in b.members.items():
        if not _independent_reader_ok(m):
            return GateResult(protocol=INVALID_PROTOCOL,
                              code=f"READER_WITNESS_INVALID: {mid}", l2=INVALID, c3_post=INVALID)

    # ---- POST gate (source = S_restored) ----
    post_c1_ok, t_restored, c3_post, l2, supported = _post_from_bundle(b, attempted)
    out.post_c1_ok, out.t_restored, out.c3_post = post_c1_ok, t_restored, c3_post
    if c3_post == INVALID:
        return GateResult(protocol=INVALID_PROTOCOL, code="POST_MEASUREMENT_INVALID",
                          pre_class=out.pre_class, t_write=out.t_write, l2=INVALID,
                          c3_post=INVALID, post_c1_ok=post_c1_ok)
    out.l2, out.supported = l2, supported
    return out


def _pre_from_bundle(b: EvidenceBundle):
    per_T = {}
    l1_reason = ""
    for mid, m in b.members.items():
        a = m.arms["A"]["S_write"].snapshot()
        bb = m.arms["B"]["S_write"].snapshot()
        c = m.arms["C"]["S_write"].snapshot()
        l1 = evaluate_basic_l1(a, bb, m.payload)
        if l1.result == INVALID:
            return "", INVALID, INVALID, {}
        if l1.result != PASS:
            return NOT_ESTABLISHED, NOT_ASSESSED, NOT_ASSESSED, {}
        c2 = evaluate_c2(a, a, bb, c)
        per_T[mid] = c2.signed_T
    all_attr = all(t is not None and abs(t) >= 1 for t in per_T.values())
    members = [{"member_id": mid, "content_class": CONTENT_CLASS_OF[mid], "T": t,
                "attributed": (t is not None and abs(t) >= 1)} for mid, t in per_T.items()]
    r3 = evaluate_c3(members, _SAME_PAIRS, _CROSS_PAIRS)
    if r3.result == INVALID:
        return C1, ATTRIBUTED if all_attr else NOT_ESTABLISHED, INVALID, per_T
    pre_class = C3 if r3.result == C3 else (C2 if all_attr else C1)
    return pre_class, (ATTRIBUTED if all_attr else NOT_ESTABLISHED), r3.result, per_T


def _post_from_bundle(b: EvidenceBundle, attempted: str):
    per_T = {}
    post_c1 = True
    for mid, m in b.members.items():
        a = m.arms["A"]["S_restored"].snapshot()
        bb = m.arms["B"]["S_restored"].snapshot()
        c = m.arms["C"]["S_restored"].snapshot()
        if bb.literal != m.payload:
            post_c1 = False
        per_T[mid] = evaluate_c2(a, a, bb, c).signed_T
    members = [{"member_id": mid, "content_class": CONTENT_CLASS_OF[mid], "T": t,
                "attributed": (t is not None and abs(t) >= 1)} for mid, t in per_T.items()]
    r3 = evaluate_c3(members, _SAME_PAIRS, _CROSS_PAIRS)
    if r3.result == INVALID:
        return post_c1, per_T, INVALID, INVALID, None

    if attempted == "post_C1_only":
        return post_c1, per_T, NOT_ASSESSED, (PASS if post_c1 else FAIL), (C1 if post_c1 else None)

    all_attr = all(t is not None and abs(t) >= 1 for t in per_T.values())
    if r3.result == C3:
        return post_c1, per_T, C3, PASS, C3
    if all_attr:
        return post_c1, per_T, r3.result, PASS, C2
    if post_c1:
        return post_c1, per_T, r3.result, PASS, C1
    any_indet = any(t is not None and 0 < abs(t) < 1 for t in per_T.values())
    return post_c1, per_T, r3.result, (UNRESOLVED if any_indet else FAIL), None
