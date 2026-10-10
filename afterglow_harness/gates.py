"""
gates.py — the TWO public evidence gates (凌翼 RC8 ruling).

There are exactly two public entry points for judgement:

    PRE_EVIDENCE_GATE   (evidence source = S_write)
    POST_RESET_EVIDENCE_GATE (evidence source = S_restored ONLY)

Plus two protocol gates that run BEFORE any post claim:

    J_GATE     (any required J-timing failure -> INVALID)
    RESET_GATE (any required reset failure   -> INVALID)

Hard rules (frozen):
  · PRE consumes S_write; NO fixture hand-writes L1/C2/C3.
  · Basic L1/C1 must pass before C2; C2 attribution before C3.
  · NO FAILURE DEFAULT: NOT_ESTABLISHED is NOT C3.
  · J/reset invalidity => INVALID, and INVALID dominates any scientific result.
  · POST consumes S_restored ONLY; never inherits a pre label.
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
from harness_constants import CONTENT_CLASS_OF, StateSnapshot

_SAME_PAIRS = [("A1", "A2"), ("B1", "B2")]
_CROSS_PAIRS = [("A1", "B1"), ("A2", "B2")]


# ---------------------------------------------------------------------------
# PRE_EVIDENCE_GATE  (evidence source = S_write)
# ---------------------------------------------------------------------------


@dataclass
class PreEvidence:
    l1: str = ""
    l1_change_class: str = ""
    t_write: dict = field(default_factory=dict)   # member -> Fraction (S_write)
    c2: str = NOT_ASSESSED
    c3: str = NOT_ASSESSED
    pre_class: str = NOT_ESTABLISHED
    reason: str = ""


def _attributed(T: Fraction | None) -> bool:
    return T is not None and abs(T) >= 1


def PRE_EVIDENCE_GATE(
    member_write: dict,
) -> PreEvidence:
    """Judge pre-reset evidence from S_write observations ONLY.

    member_write: {member_id: {"A": StateSnapshot, "B": StateSnapshot, "C": StateSnapshot, "payload": bytes}}

    Order (mandatory, non-promoting):
      1. Basic L1 per member from S_write A vs B; C1 requires payload match.
      2. If ANY member L1 != PASS  -> pre_class = NOT_ESTABLISHED (NEVER C3).
      3. C2 = per-member T_write = dz_C - dz_B; requires all members attributed.
      4. C3 = frozen member set of T_write (same-class eq, cross-class neq).
    """
    out = PreEvidence()
    if not member_write:
        out.reason = "no members"
        return out

    l1_results = {}
    per_T = {}
    for mid, obs in member_write.items():
        l1 = evaluate_basic_l1(obs["A"], obs["B"], obs["payload"])
        c2 = evaluate_c2(obs["A"], obs["A"], obs["B"], obs["C"])
        l1_results[mid] = l1
        per_T[mid] = c2.signed_T

    all_l1_pass = all(r.result == PASS for r in l1_results.values())
    all_c1 = all(r.change_class == C1 for r in l1_results.values())
    any_invalid = any(r.result == INVALID for r in l1_results.values())

    out.t_write = per_T
    out.l1 = PASS if all_l1_pass else (INVALID if any_invalid else FAIL)
    out.l1_change_class = C1 if (all_l1_pass and all_c1) else NOT_ESTABLISHED

    # NO FAILURE DEFAULT: if L1 not fully PASS, nothing promotes.
    if not all_l1_pass:
        out.c2 = NOT_ASSESSED
        out.c3 = NOT_ASSESSED
        out.pre_class = NOT_ESTABLISHED
        out.reason = "Basic L1 not fully PASS -> C2/C3 MUST NOT promote"
        return out

    # C2 requires every member attributed
    all_attributed = all(_attributed(v) for v in per_T.values())
    if not all_attributed:
        out.c2 = NOT_ESTABLISHED
        out.c3 = NOT_ASSESSED
        out.pre_class = C1  # C1 may stand; C2/C3 do not promote
        out.reason = "not all members attributed -> C3 MUST NOT promote"
        return out

    out.c2 = ATTRIBUTED
    members = [
        {"member_id": mid, "content_class": CONTENT_CLASS_OF[mid], "T": T,
         "attributed": _attributed(T)}
        for mid, T in per_T.items()
    ]
    r3 = evaluate_c3(members, _SAME_PAIRS, _CROSS_PAIRS)
    out.c3 = r3.result
    out.pre_class = C3 if r3.result == C3 else C2
    out.reason = "C2 attributed; pre class set by C3 structure"
    return out


# ---------------------------------------------------------------------------
# Protocol gates
# ---------------------------------------------------------------------------


def J_GATE(j_timing_valid: bool) -> str:
    """Return INVALID if J timing is not valid; else PASS."""
    return PASS if j_timing_valid else INVALID


def RESET_GATE(reset_ok: bool) -> str:
    """Return INVALID if reset is not valid; else PASS."""
    return PASS if reset_ok else INVALID


# ---------------------------------------------------------------------------
# POST_RESET_EVIDENCE_GATE  (evidence source = S_restored ONLY)
# ---------------------------------------------------------------------------


@dataclass
class PostEvidence:
    reset_valid: bool
    j_timing_ok: bool
    post_c1_ok: bool
    t_restored: dict = field(default_factory=dict)
    c3_post: str = NOT_ASSESSED
    l2: str = ""
    supported: str | None = None
    reason: str = ""


def POST_RESET_EVIDENCE_GATE(
    member_restored: dict,
    j_timing_ok: bool,
    reset_valid: bool,
    attempted: str = "full",
) -> PostEvidence:
    """Judge post-reset evidence from S_restored ONLY.

    INVALID dominates: any J/reset/measurement invalidity -> L2 = INVALID, and we
    do NOT then ask "but does post C3 look right?".
    """
    out = PostEvidence(reset_valid=reset_valid, j_timing_ok=j_timing_ok, post_c1_ok=False)

    # 1. protocol invalidity dominates
    if J_GATE(j_timing_ok) == INVALID:
        out.l2 = INVALID
        out.reason = "J_TIMING_INVALID -> INVALID (dominates any scientific result)"
        return out
    if RESET_GATE(reset_valid) == INVALID:
        out.l2 = INVALID
        out.reason = "RESET_INVALID -> INVALID (dominates any scientific result)"
        return out

    # 2. measurement presence
    if not member_restored:
        out.l2 = INVALID
        out.reason = "MEASUREMENT_MISSING: no restored members"
        return out

    # 3. rebuild post C1/C2/C3 from S_restored
    per_T = {}
    post_c1_ok = True
    for mid, obs in member_restored.items():
        c2 = evaluate_c2(obs["A"], obs["A"], obs["B"], obs["C"])
        per_T[mid] = c2.signed_T
        if obs["B"].literal != obs["payload"]:
            post_c1_ok = False
    out.t_restored = per_T
    out.post_c1_ok = post_c1_ok

    members = [
        {"member_id": mid, "content_class": CONTENT_CLASS_OF[mid], "T": T,
         "attributed": _attributed(T)}
        for mid, T in per_T.items()
    ]
    r3 = evaluate_c3(members, _SAME_PAIRS, _CROSS_PAIRS)
    out.c3_post = r3.result

    if attempted == "post_C1_only":
        out.c3_post = NOT_ASSESSED  # C3 not attempted in this fixture
        out.l2 = PASS if post_c1_ok else FAIL
        out.supported = C1 if post_c1_ok else None
        out.reason = "only post C1 attempted"
        return out

    # full persistence ladder
    if r3.result == C3:
        out.l2, out.supported = PASS, C3
    elif all(_attributed(v) for v in per_T.values()):
        out.l2, out.supported = PASS, C2
    elif post_c1_ok:
        out.l2, out.supported = PASS, C1
    else:
        # no positive class: frozen aggregation (INVALID already handled)
        any_indet = any(v is not None and 0 < abs(v) < 1 for v in per_T.values())
        if any_indet:
            out.l2 = UNRESOLVED
        else:
            out.l2 = FAIL
        out.supported = None
    out.reason = "post-reset ladder rebuilt from S_restored"
    return out
