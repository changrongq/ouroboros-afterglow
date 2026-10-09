"""
Evaluator — the judgement core (Basic L1 / C1 / C2 / C3).

The evaluator receives observations and frozen rules; it does NOT receive the
expected oracle, nor any fixture ID usable for table lookup. It returns a
result + ledger.

Frozen semantics implemented here (with provenance to SPEC / proposal):

  Basic L1 / C1  (only B vs A)
      h = (#literal byte positions differing between B and A)
          + (1 if q_B != q_A else 0)
      h = 0   -> determinate negative
      h = 1   -> INDETERMINATE
      h >= 2  -> positive attribution / change
      THEN, to establish C1, B's 16 bytes must independently match the
      registered episode payload exactly. L1 PASS alone is NOT C1.

      ★ OBSERVATION ① (睫): the q term must NOT be a positive topping-up term
        for h. If q_B != q_A, that is an arm-configuration violation for a
        Basic-L1 (B vs A) judgement, because B's extra writer is OFF by
        definition. So q_B != q_A -> ARM_CONFIG_INVALID, not h += 1.

  C2  (only C vs B)
      Δz_X = z_X - z_baseline(X)   with z = q/2
      T(E) = Δz_C(E) - Δz_B(E)     (signed)
      |T| >= 1        -> positive / ATTRIBUTED
      T == 0          -> determinate negative
      0 < |T| < 1     -> INDETERMINATE
      ledger stores signed T; C3 always compares signed T.

      ★ OBSERVATION ④ (睫): Δz_B MUST be actually measured and recorded — the
        evaluator must NOT hard-code it to 0. If the B measurement is missing,
        that is a measurement error (INVALID scope), not an implicit 0.

  C3  (on the full frozen member set)
      same-class  : exact equality of signed T
      cross-class : exact inequality of signed T
      Every member must first pass nonstorage attribution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction

from harness_constants import (
    LITERAL_SIZE,
    HarnessError,
    StateSnapshot,
    decode_substrate,
)

# ---------------------------------------------------------------------------
# Result vocabulary
# ---------------------------------------------------------------------------

PASS = "PASS"
FAIL = "FAIL"
UNRESOLVED = "UNRESOLVED"
INVALID = "INVALID"

#: Frozen vocabulary distinction (prereg §H / BD16): 
#:   NOT_ASSESSED = 没有测 (attempted-but-not-run is NOT this)
#:   N/A          = 不适用 (the ladder level was never entered at all)
N_A = "N/A"

C1 = "C1"
C2 = "C2"
C3 = "C3"

NOT_ASSESSED = "NOT_ASSESSED"
NOT_ESTABLISHED = "NOT_ESTABLISHED"
ARCHITECTURALLY_NOT_IDENTIFIABLE = "ARCHITECTURALLY_NOT_IDENTIFIABLE"

ATTRIBUTED = "ATTRIBUTED"
DETECTED_UNATTRIBUTED = "DETECTED_UNATTRIBUTED"


@dataclass
class AttemptedScope:
    """Mechanically-encodable record of WHAT was attempted.

    The evaluator derives invalidity from (scope + missing rules), NEVER from a
    fixture id. A fixture that never enters the post-reset ladder records
    ``post_reset = False`` and the L2 field becomes ``N/A`` (not applicable),
    because "did not enter L2" is NOT a kind of L2 failure.
    """

    pre_reset_c1: bool = False
    pre_reset_c2: bool = False
    pre_reset_c3: bool = False
    post_reset: bool = False

    def as_dict(self) -> dict:
        return {
            "pre_reset_C1": self.pre_reset_c1,
            "pre_reset_C2": self.pre_reset_c2,
            "pre_reset_C3": self.pre_reset_c3,
            "post_reset": self.post_reset,
        }


# ---------------------------------------------------------------------------
# J-timing witness  (BD-52: observer MUST independently witness J's time point)
# ---------------------------------------------------------------------------
#
# SPEC §7.2 (post-BD-52): the observer independently records the triple
#     ( S_write_digest , J_after_digest , S_handoff_digest )
# and REQUIRES  J_after_digest == S_handoff_digest.
# If they are not equal, J did not finish before the handoff snapshot, and the
# fixture is INVALID (not PASS). This makes "a legal J" and "an injected
# post-handoff fault" machine-distinguishable by TIME, not by wording.


@dataclass
class JTimingWitness:
    s_write_digest: str
    j_after_digest: str
    s_handoff_digest: str

    @property
    def timing_valid(self) -> bool:
        return self.j_after_digest == self.s_handoff_digest

    def as_dict(self) -> dict:
        return {
            "S_write_digest": self.s_write_digest,
            "J_after_digest": self.j_after_digest,
            "S_handoff_digest": self.s_handoff_digest,
            "timing_valid": self.timing_valid,
        }


def assert_j_timing(handoff: JTimingWitness) -> None:
    """Raise (fixture INVALID scope) if J was not proven to precede handoff."""
    if not handoff.timing_valid:
        raise HarnessError(
            "J_TIMING_VIOLATION: J_after_digest != S_handoff_digest; "
            "J did not complete before the handoff snapshot -> fixture INVALID"
        )


# ---------------------------------------------------------------------------
# Frozen L2 aggregation rule (BD-53)
# ---------------------------------------------------------------------------
#
# When NO positive class is re-established post-reset, the L2 outcome is:
#     · any attempted class in the frozen indeterminate region -> UNRESOLVED
#     · only when ALL attempted classes are determinate negative -> FAIL
# i.e. a lower-class determinate negative MUST NOT cancel a higher-class
# indeterminate. This rule is FROZEN (was previously an implicit choice).

L2_RULE_ID = "SYNTHETIC_L2_AGGREGATION_V1"


def l2_aggregate(post_c1: str, post_c2: str, post_c3: str) -> str:
    """Frozen L2 aggregation when no positive class was re-established."""
    attempted = [p for p in (post_c1, post_c2, post_c3) if p != NOT_ASSESSED]
    if not attempted:
        return NOT_ASSESSED
    if any(p == UNRESOLVED for p in attempted):
        return UNRESOLVED
    if all(p in (FAIL, NOT_ESTABLISHED) for p in attempted):
        return FAIL
    return UNRESOLVED




@dataclass
class L1Result:
    result: str = ""
    change_class: str = ""  # C1 / NOT_ESTABLISHED / NOT_ASSESSED
    h: int = 0
    reason: str = ""
    c2: str = NOT_ASSESSED
    c3: str = NOT_ASSESSED
    measurement_error: bool = False


@dataclass
class C2Result:
    result: str = ""
    signed_T: Fraction | None = None
    reason: str = ""


@dataclass
class C3Result:
    result: str = ""
    per_member_T: dict = field(default_factory=dict)
    same_class_ok: bool = False
    cross_class_ok: bool = False
    reason: str = ""


# ---------------------------------------------------------------------------
# Basic L1 / C1   (B vs A only)
# ---------------------------------------------------------------------------


def _literal_byte_diff_count(a: bytes, b: bytes) -> int:
    if len(a) != LITERAL_SIZE or len(b) != LITERAL_SIZE:
        raise HarnessError("literal must be exactly 16 bytes in L1 diff")
    return sum(1 for x, y in zip(a, b) if x != y)


def evaluate_basic_l1(
    snap_A: StateSnapshot,
    snap_B: StateSnapshot,
    registered_payload: bytes,
) -> L1Result:
    """Basic L1 / C1: only B vs A. Uses identity-masked state distance h.

    Implements 睫 OBSERVATION ①: q_B != q_A is an ARM_CONFIG_INVALID,
    NOT a positive topping-up term.
    """
    q_A = snap_A.q
    q_B = snap_B.q

    # ① q difference is not a topping-up term.
    if q_B != q_A:
        return L1Result(
            result=INVALID,
            reason="ARM_CONFIG_INVALID: q_B != q_A in a Basic-L1 (B vs A) judgement; "
            "B's extra writer is OFF; q difference must not top up h",
        )

    h = _literal_byte_diff_count(snap_A.literal, snap_B.literal)

    if h == 0:
        return L1Result(
            result=FAIL,
            change_class=NOT_ESTABLISHED,
            h=h,
            reason="h=0: determinate negative (no registered change)",
        )
    if h == 1:
        return L1Result(
            result=UNRESOLVED,
            change_class=NOT_ESTABLISHED,
            h=h,
            reason="h=1: falls inside the frozen indeterminate region",
        )
    # h >= 2 -> positive attribution/change
    if snap_B.literal != registered_payload:
        # L1 PASS, but C1 requires exact payload match in B.
        return L1Result(
            result=PASS,
            change_class=NOT_ESTABLISHED,
            h=h,
            reason="L1 PASS (h>=2) but B literal != registered payload; C1 NOT established",
        )
    return L1Result(
        result=PASS,
        change_class=C1,
        h=h,
        reason="L1 PASS (h>=2) and B literal matches registered payload -> C1 established",
    )


# ---------------------------------------------------------------------------
# C2   (C vs B)
# ---------------------------------------------------------------------------


def _z(q: int) -> Fraction:
    return Fraction(q, 2)


def evaluate_c2(
    snap_B_baseline: StateSnapshot | None,
    snap_C_baseline: StateSnapshot | None,
    snap_B: StateSnapshot | None,
    snap_C: StateSnapshot | None,
) -> C2Result:
    """C2: signed treatment contrast T = Δz_C - Δz_B.

    Requires actual measurements of BOTH arms' baselines and post states.
    ★ OBSERVATION ④: Δz_B is measured, never hard-coded to 0.
    """
    if None in (snap_B_baseline, snap_C_baseline, snap_B, snap_C):
        return C2Result(
            result=INVALID,
            reason="MEASUREMENT_MISSING: C2 requires measured baselines and post states "
            "for both B and C; Δz_B must not be hard-coded to 0",
        )

    dz_B = _z(snap_B.q) - _z(snap_B_baseline.q)
    dz_C = _z(snap_C.q) - _z(snap_C_baseline.q)
    T = dz_C - dz_B

    if abs(T) >= 1:
        return C2Result(result=ATTRIBUTED, signed_T=T, reason="|T|>=1 positive")
    if T == 0:
        return C2Result(result=FAIL, signed_T=T, reason="T=0 determinate negative")
    return C2Result(
        result=UNRESOLVED, signed_T=T, reason="0<|T|<1 falls in indeterminate region"
    )


# ---------------------------------------------------------------------------
# C3   (full frozen member set, signed T)
# ---------------------------------------------------------------------------


def evaluate_c3(
    members: list[dict],
    same_class_pairs: list[tuple[str, str]],
    cross_class_pairs: list[tuple[str, str]],
) -> C3Result:
    """C3: compare signed T over the full frozen member set.

    members: list of dicts {member_id, content_class, T (Fraction|None),
                            attributed (bool)}.
    same_class_pairs / cross_class_pairs: member_id pairs to test.

    Rules:
      · every member must first pass nonstorage attribution;
      · same-class  -> exact equality of signed T;
      · cross-class -> exact inequality of signed T;
      · replay is not a substitute for different episodes (enforced upstream
        by the fixture, not here).
    """
    per = {m["member_id"]: m for m in members}

    # all members must be attributed
    unattributed = [m["member_id"] for m in members if not m.get("attributed", False)]
    if unattributed:
        return C3Result(
            result=NOT_ESTABLISHED,
            per_member_T={k: v.get("T") for k, v in per.items()},
            reason=f"C3 NOT_ESTABLISHED: unattributed members {unattributed}",
        )

    for m in members:
        if m.get("T") is None:
            return C3Result(
                result=INVALID,
                reason=f"MEASUREMENT_MISSING: member {m['member_id']} has no signed T",
            )

    same_ok = all(per[a]["T"] == per[b]["T"] for a, b in same_class_pairs)
    cross_ok = all(per[a]["T"] != per[b]["T"] for a, b in cross_class_pairs)

    reason = f"same_class_ok={same_ok} cross_class_ok={cross_ok}"
    if same_ok and cross_ok:
        return C3Result(
            result=C3,
            per_member_T={k: v["T"] for k, v in per.items()},
            same_class_ok=True,
            cross_class_ok=True,
            reason="C3 established: " + reason,
        )
    return C3Result(
        result=NOT_ESTABLISHED,
        per_member_T={k: v["T"] for k, v in per.items()},
        same_class_ok=same_ok,
        cross_class_ok=cross_ok,
        reason="C3 NOT_ESTABLISHED: " + reason,
    )


# ---------------------------------------------------------------------------
# Rule-bundle guarded C2  (scope-driven; NOT fixture-id special-cased)
# ---------------------------------------------------------------------------

REQUIRED_C2_RULES = ("STATE_DELTA_RULE", "CAUSAL_CONTRAST_RULE", "measurement_scale")


@dataclass
class C2AttemptResult:
    """Result of a pre-reset C2 attempt, judged from its OWN scope."""

    result: str  # INVALID | PASS/... (only INVALID path used by V4.1)
    invalidity_code: str | None
    attempted_scope: AttemptedScope
    l2: str  # N/A when post-reset was never entered


def evaluate_c2_attempt(
    rule_bundle: dict,
    scope: AttemptedScope,
) -> C2AttemptResult:
    """Judge a pre-reset C2 attempt from scope + rule completeness.

    Derivation rule (frozen, scope-driven):

      · if the C2 scope was NOT attempted -> the C2 attempt is N/A-scope;
      · if attempted and any required C2 rule is missing ->
            result = INVALID on the *C2 attempt scope*
            invalidity_code = "<RULE>_MISSING"
      · post-reset is derived from scope.post_reset:
            if post_reset is False -> l2 = N/A  (ladder level NEVER ENTERED)

    The invalidity is derived from the SCOPE and the MISSING RULE, never from a
    fixture identity. Any C2 attempt with this shape follows the same path.
    """
    if not scope.pre_reset_c2:
        # C2 not attempted: nothing to invalidate here.
        return C2AttemptResult(
            result=NOT_ASSESSED,
            invalidity_code=None,
            attempted_scope=scope,
            l2=N_A if not scope.post_reset else UNRESOLVED,
        )

    for rule_name in REQUIRED_C2_RULES:
        if rule_bundle.get(rule_name) is None:
            return C2AttemptResult(
                result=INVALID,
                invalidity_code=f"{rule_name.upper()}_MISSING",
                attempted_scope=scope,
                # post-reset never entered -> L2 is N/A, NOT INVALID.
                l2=N_A if not scope.post_reset else INVALID,
            )

    # complete bundle: the attempt proceeds (normal path; not exercised by V4.1)
    return C2AttemptResult(
        result=PASS,
        invalidity_code=None,
        attempted_scope=scope,
        l2=N_A if not scope.post_reset else UNRESOLVED,
    )



# ---------------------------------------------------------------------------
# Architectural non-identifiability  (V4b)
# ---------------------------------------------------------------------------


def evaluate_c2_architectural(extra_interface_separable: bool) -> tuple[str, str]:
    """Return (C2_result, C3_result) given whether the architecture exposes a
    separable W_extra ON/OFF interface.

    If the counterfactual (same-E, same-storage-path, W_extra ON vs OFF) is
    architecturally impossible, C2/C3 are ARCHITECTURALLY_NOT_IDENTIFIABLE —
    NOT FAIL and NOT INVALID. C1 remains independently assessable elsewhere.
    """
    if extra_interface_separable:
        # separable -> normal assessment path (not exercised by V4b)
        return (NOT_ASSESSED, NOT_ASSESSED)
    return (ARCHITECTURALLY_NOT_IDENTIFIABLE, ARCHITECTURALLY_NOT_IDENTIFIABLE)
