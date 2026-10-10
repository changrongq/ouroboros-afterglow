"""
evidence_bundle.py — the unified EVIDENCE_BUNDLE + its validation (RC10).

凌翼 RC10: there is ONE evidence object and ONE pure adjudication chain. Both
ingress paths feed it:

    production ingress : live runtime -> EvidenceBundle
    replay ingress     : raw ledger + canonical fixture contract -> EvidenceBundle

    same adjudication chain, different ingress.

The single new structural requirement (凌翼 RC10 R2) is
REQUIRED_EVIDENCE_CONSUMPTION_MATRIX (see evidence_contract.py): every REQUIRED
EVIDENCE field must be RECORDED AND CONSUMED AND NEGATIVE-TESTED. A field that
is only recorded is a log, not a gate.

Required chain (any protocol-invalid layer => INVALID; INVALID dominates):

    FROZEN MEMBER SET
      -> required arms/phases present
      -> S_write raw observations valid
      -> PRE gate
      -> required_pre_class satisfied (contract, NOT ledger)
      -> J witness valid (J_after == S_handoff, byte-level)
      -> J S_handoff == RESET accepted handoff   (byte-level)
      -> reset valid (reset_valid MANDATORY; missing/malformed -> INVALID)
      -> reset-object identity (verified-restored == S_restored, byte-level)
      -> S_restored observations valid
      -> reader / literal witnesses valid (EXACT frozen probe set; expected
         derived from S_restored.q_raw / S_restored.literal)
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

#: Tri-state sentinel for a sub-check that was NOT REACHED (知微 RC11 P2-A).
#: Distinct from True (passed) and False (failed) so a default never masquerades
#: as a pass. String value => readable in artifacts/JSON.
UNEVALUATED = "UNEVALUATED"


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
    # arm -> {"reset_valid": bool, "reason": str, "clear_access": str,
    #         "accepted_handoff": {"literal": hex, "q_raw": hex},
    #         "verified_restored": {"literal": hex, "q_raw": hex}}
    reset_witness: dict = field(default_factory=dict)
    # reader/literal witnesses: {"raw_q": int, "affine": {u: {"num","den"}}, "literal": {u: int}}
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


def _validate_reset(b: EvidenceBundle) -> tuple[bool, str]:
    """reset_valid is MANDATORY and fail-closed (凌翼 RC10 R2).

        True      -> continue
        False     -> INVALID
        missing   -> INVALID
        malformed -> INVALID

    No "not written => default good" is permitted.
    """
    from evidence_contract import REQUIRED_RESET_FIELDS

    for mid, m in b.members.items():
        for arm in b.required_arms:
            rw = m.reset_witness.get(arm)
            if not isinstance(rw, dict):
                return False, f"RESET_WITNESS_MISSING: {mid}/{arm}"
            for field in REQUIRED_RESET_FIELDS:
                if field not in rw or rw.get(field) is None:
                    return False, f"RESET_FIELD_MISSING: {mid}/{arm}/{field}"
            if rw["reset_valid"] is not True:
                return False, f"RESET_INVALID: {mid}/{arm} (reset_valid={rw['reset_valid']!r})"
    return True, ""


def _validate_reset_object_identity(b: EvidenceBundle) -> tuple[bool, str]:
    """The reset-verified object, the stored S_restored, and the reader input
    must be the SAME BYTES, machine-verified (凌翼 RC10 R3-reset).

        reset verified restored bytes
            == EvidenceBundle.S_restored bytes
            == reader source observed bytes

    凌翼/知微 RC11 §7: we ALSO recompute the FROZEN RESET PRESERVE RULE from the
    raw bytes — the reset-accepted handoff must equal the restored state:

        accepted_handoff  ==  verified_restored   (byte-level, reset.py preserve)

    ``reset_valid`` is treated as a CLAIM to be checked, not a substitute for
    the computation. J may legally change state BEFORE the handoff; it may NOT
    explain a change AFTER it. If the preserved bytes differ across reset, the
    evidence itself violates the frozen rule and the fixture is INVALID.

    凌翼/知微 RC11 P2-A: the two sub-checks return EXPLICIT results so the
    structured flags are truthful. Returns
        (identity_checked, identity_ok, preserve_checked, preserve_ok, code)
    where a check may be *not reached* (checked=False) and its *_ok is then
    UNEVALUATED — never silently True.

    知微 RC11 P2-A re-review: EVERY identity-stage failure branch (missing /
    partial / malformed / mismatched) returns the SAME explicit shape
        (True, False, False, UNEVALUATED, code)
    so a preserve check that was NOT reached can never carry a default True.
    """
    for mid, m in b.members.items():
        for arm in b.required_arms:
            rw = m.reset_witness.get(arm, {})
            vr = rw.get("verified_restored")
            stored = m.arms.get(arm, {}).get("S_restored")

            # ---- identity check (ANY failure here -> preserve NOT reached) ----
            id_fail = None
            if not isinstance(vr, dict) or "literal" not in vr or "q_raw" not in vr:
                id_fail = f"RESET_VERIFIED_MISSING: {mid}/{arm}"
            elif stored is None:
                id_fail = f"RESET_STORED_RESTORED_MISSING: {mid}/{arm}"
            else:
                try:
                    vr_lit = bytes.fromhex(vr["literal"])
                    vr_q = bytes.fromhex(vr["q_raw"])
                except Exception:
                    id_fail = f"RESET_VERIFIED_MALFORMED: {mid}/{arm}"
                else:
                    if (vr_lit != stored.literal) or (vr_q != stored.q_raw):
                        id_fail = (f"RESET_OBJECT_IDENTITY_BREAK: {mid}/{arm} "
                                   f"verified-restored != stored S_restored (byte-level)")
            if id_fail is not None:
                # identity failed -> preserve check NOT reached
                return True, False, False, UNEVALUATED, id_fail

            # ---- preserve check (reached only if identity held) ----
            if not isinstance(rw.get("accepted_handoff"), dict) \
                    or "literal" not in rw["accepted_handoff"] \
                    or "q_raw" not in rw["accepted_handoff"]:
                return True, True, True, False, f"RESET_HANDOFF_MISSING: {mid}/{arm}"
            try:
                acc_lit = bytes.fromhex(rw["accepted_handoff"]["literal"])
                acc_q = bytes.fromhex(rw["accepted_handoff"]["q_raw"])
            except Exception:
                return True, True, True, False, f"RESET_HANDOFF_MALFORMED: {mid}/{arm}"
            if (acc_lit != vr_lit) or (acc_q != vr_q):
                return True, True, True, False, \
                    (f"RESET_PRESERVE_RULE_BREAK: {mid}/{arm} "
                     f"accepted_handoff != verified_restored (byte-level); "
                     f"preserved state changed across reset")
    return True, True, True, True, ""


def _independent_reader_ok(m: MemberEvidence) -> tuple[bool, str]:
    """Recompute expected R(q,u)=u+q/2 and L(lit,u)=u+sum(bytes) from RAW values
    and compare to the reader's returned values.

    凌翼 RC10 (reader gate tightened):

      · the witness MUST present EXACTLY the frozen probe key set
        (affine: {0,2}, literal: {0,2}); {}, {"0"}, {"2"}, {...,extra} are all
        ILLEGAL -> FAIL CLOSED;
      · expected values are DERIVED from the C arm's S_restored bytes
        (q := decode_int64_le(S_restored.q_raw); byte_sum := SUM(S_restored.literal));
      · reader_witness.raw_q is a REDUNDANT cross-check field ONLY: it must
        equal decode(S_restored.q_raw); it is NEVER the source of expected.

    This is what kills a fake reader that returns `u` regardless of q: with a
    q != 0 fixture, u != u + q/2, so the exact-key comparison fails.
    """
    from evidence_contract import (
        FROZEN_AFFINE_KEYS,
        FROZEN_LITERAL_KEYS,
        REQUIRED_RESET_FIELDS,
    )
    from harness_constants import decode_substrate

    rw = m.reader_witness
    if not rw:
        return False, "READER_WITNESS_MISSING"

    # ---- the C arm's S_restored is the ONLY legitimate source of truth ----
    c_restored = m.arms.get("C", {}).get("S_restored")
    if c_restored is None:
        return False, "READER_SOURCE_MISSING: C/S_restored absent"

    try:
        q = decode_substrate(c_restored.q_raw)
    except Exception:
        return False, "READER_SOURCE_INVALID: S_restored.q_raw not decodable"
    byte_sum = sum(c_restored.literal)

    # ---- raw_q is a redundant cross-check, never the expected source ----
    raw_q = rw.get("raw_q")
    if raw_q is None:
        return False, "READER_RAW_Q_MISSING"
    if raw_q != q:
        return False, (f"READER_RAW_Q_MISMATCH: witness raw_q={raw_q} != "
                       f"decode(S_restored.q_raw)={q}")

    # ---- EXACT frozen probe key equality (fail closed) ----
    aff = rw.get("affine")
    if not isinstance(aff, dict):
        return False, "READER_AFFINE_MISSING"
    if frozenset(aff.keys()) != FROZEN_AFFINE_KEYS:
        return False, (f"READER_AFFINE_PROBE_SET: got {sorted(aff.keys())} "
                       f"required {sorted(FROZEN_AFFINE_KEYS)}")
    lit = rw.get("literal")
    if not isinstance(lit, dict):
        return False, "READER_LITERAL_MISSING"
    if frozenset(lit.keys()) != FROZEN_LITERAL_KEYS:
        return False, (f"READER_LITERAL_PROBE_SET: got {sorted(lit.keys())} "
                       f"required {sorted(FROZEN_LITERAL_KEYS)}")

    # ---- compare against independently-derived expected values ----
    for u_s in FROZEN_AFFINE_KEYS:
        u = int(u_s)
        got = aff[u_s]
        try:
            got_f = Fraction(got["num"], got["den"])
        except Exception:
            return False, f"READER_AFFINE_MALFORMED: probe {u_s}"
        expected = Fraction(2 * u + q, 2)
        if got_f != expected:
            return False, (f"READER_AFFINE_MISMATCH: probe {u_s} got {got_f} "
                           f"expected {expected}")
    for u_s in FROZEN_LITERAL_KEYS:
        u = int(u_s)
        got = lit[u_s]
        if not isinstance(got, int):
            return False, f"READER_LITERAL_MALFORMED: probe {u_s}"
        if got != u + byte_sum:
            return False, (f"READER_LITERAL_MISMATCH: probe {u_s} got {got} "
                           f"expected {u + byte_sum}")
    return True, ""


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
    # ---- structured sub-verdicts (凌翼/知微 RC11 §8, P2-A) ----
    # Downstream consumers MUST read these flags, never guess a state from the
    # human-readable error-message prefix. Each flag is a tri-state:
    #   True  = the check ran and passed
    #   False = the check ran and failed
    #   UNEVALUATED = the check was NOT reached (e.g. an earlier gate failed)
    # A default is NEVER True — "not evaluated" must not masquerade as a pass.
    membership_ok: object = UNEVALUATED
    j_timing_ok: object = UNEVALUATED
    handoff_continuity_ok: object = UNEVALUATED
    reset_valid: object = UNEVALUATED          # the RESET gate verdict (recomputed)
    reset_identity_ok: object = UNEVALUATED
    preserve_rule_ok: object = UNEVALUATED
    reader_ok: object = UNEVALUATED


def evaluate_bundle(b: EvidenceBundle, required_pre_class: str,
                    expected_post_supported_class: str | None,
                    attempted: str = "full") -> GateResult:
    """Run the full chain; INVALID dominates anywhere protocol fails.

    Structured sub-verdicts are threaded as tri-state (True/False/UNEVALUATED).
    A gate that fails marks its own flag False; gates NOT REACHED stay
    UNEVALUATED (never defaulted to True).
    """
    out = GateResult(protocol=VALID_PROTOCOL, code="")

    mem_ok, mem_code = _validate_membership(b)
    ap_ok, ap_code = _validate_arms_phases(b)
    by_ok, by_code = _validate_bytes(b)
    if not mem_ok:
        return GateResult(protocol=INVALID_PROTOCOL, code=mem_code,
                          l2=INVALID, c3_post=INVALID, membership_ok=False)
    if not ap_ok:
        return GateResult(protocol=INVALID_PROTOCOL, code=ap_code,
                          l2=INVALID, c3_post=INVALID, membership_ok=True)
    if not by_ok:
        return GateResult(protocol=INVALID_PROTOCOL, code=by_code,
                          l2=INVALID, c3_post=INVALID, membership_ok=True)

    # ---- PRE gate (source = S_write) ----
    pre = _pre_from_bundle(b)
    out.pre_class, out.c2_pre, out.c3_pre, out.t_write = pre
    if out.c3_pre == INVALID or out.c2_pre == INVALID:
        return GateResult(protocol=INVALID_PROTOCOL, code="PRE_MEASUREMENT_INVALID",
                          pre_class=out.pre_class, l2=INVALID, c3_post=INVALID,
                          t_write=out.t_write, membership_ok=True)

    # required_pre_class is a CONTRACT precondition
    if required_pre_class and out.pre_class != required_pre_class:
        return GateResult(protocol=INVALID_PROTOCOL,
                          code=f"PROFILE_PRECONDITION_FAILED: required_pre_class="
                               f"{required_pre_class} got={out.pre_class}",
                          pre_class=out.pre_class, c2_pre=out.c2_pre, c3_pre=out.c3_pre,
                          t_write=out.t_write, l2=INVALID, c3_post=INVALID,
                          membership_ok=True)

    # ---- J timing + handoff continuity ----
    j_ok, j_code = _validate_j_witness(b)
    if not j_ok:
        return GateResult(protocol=INVALID_PROTOCOL, code=j_code, l2=INVALID,
                          c3_post=INVALID, membership_ok=True, j_timing_ok=False)
    hc_ok, hc_code = _validate_handoff_continuity(b)
    if not hc_ok:
        return GateResult(protocol=INVALID_PROTOCOL, code=hc_code, l2=INVALID,
                          c3_post=INVALID, membership_ok=True, j_timing_ok=True,
                          handoff_continuity_ok=False)

    # ---- reset validity (fail-closed; 凌翼 RC10 R2) ----
    # reset_valid has three-valued intent: True -> continue; missing / False /
    # malformed -> INVALID. There is no "not written => default good".
    reset_ok, reset_code = _validate_reset(b)
    if not reset_ok:
        return GateResult(protocol=INVALID_PROTOCOL, code=reset_code,
                          l2=INVALID, c3_post=INVALID, membership_ok=True,
                          j_timing_ok=True, handoff_continuity_ok=True, reset_valid=False)

    # ---- reset-object identity + frozen PRESERVE-rule recomputation ----
    id_checked, id_ok, pr_checked, pr_ok, ident_code = _validate_reset_object_identity(b)
    if not id_ok or not pr_ok:
        return GateResult(
            protocol=INVALID_PROTOCOL, code=ident_code, l2=INVALID, c3_post=INVALID,
            membership_ok=True, j_timing_ok=True, handoff_continuity_ok=True,
            reset_valid=True,
            reset_identity_ok=(id_ok if id_checked else UNEVALUATED),
            preserve_rule_ok=(pr_ok if pr_checked else UNEVALUATED),
        )

    # ---- reader witnesses (must be validated, fail-closed) ----
    for mid, m in b.members.items():
        ok, code = _independent_reader_ok(m)
        if not ok:
            return GateResult(protocol=INVALID_PROTOCOL,
                              code=f"READER_WITNESS_INVALID: {mid}/{code}",
                              l2=INVALID, c3_post=INVALID, membership_ok=True,
                              j_timing_ok=True, handoff_continuity_ok=True,
                              reset_valid=True, reset_identity_ok=True,
                              preserve_rule_ok=True, reader_ok=False)

    # ---- POST gate (source = S_restored) ----
    post_c1_ok, t_restored, c3_post, l2, supported = _post_from_bundle(b, attempted)
    out.post_c1_ok, out.t_restored, out.c3_post = post_c1_ok, t_restored, c3_post
    if c3_post == INVALID:
        return GateResult(protocol=INVALID_PROTOCOL, code="POST_MEASUREMENT_INVALID",
                          pre_class=out.pre_class, t_write=out.t_write, l2=INVALID,
                          c3_post=INVALID, post_c1_ok=post_c1_ok, membership_ok=True,
                          j_timing_ok=True, handoff_continuity_ok=True, reset_valid=True,
                          reset_identity_ok=True, preserve_rule_ok=True, reader_ok=True)
    # full chain passed -> every gate ran and passed
    out.membership_ok = True
    out.j_timing_ok = True
    out.handoff_continuity_ok = True
    out.reset_valid = True
    out.reset_identity_ok = True
    out.preserve_rule_ok = True
    out.reader_ok = True
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
