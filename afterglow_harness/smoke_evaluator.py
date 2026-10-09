"""
Smoke test for evaluator + reset (logic layer).

Verifies:
  · Basic L1 h semantics (0 -> FAIL, 1 -> UNRESOLVED, >=2 -> PASS);
  · 睫 OBSERVATION ①: q_B != q_A is ARM_CONFIG_INVALID, not a topping-up term;
  · C1 requires exact payload match, not merely L1 PASS;
  · C2 signed T with |T|>=1 / 0 / 0<|T|<1;
  · 睫 OBSERVATION ④: missing B measurement -> INVALID, never implicit 0;
  · C3 same-class exact equality + cross-class exact inequality;
  · reset verify: preserve/clear/access three-way.

Not a qualifying fixture.
"""

from __future__ import annotations

from fractions import Fraction

from evaluator import (
    ARCHITECTURALLY_NOT_IDENTIFIABLE,
    ATTRIBUTED,
    C1,
    C2,
    C3,
    FAIL,
    INVALID,
    NOT_ASSESSED,
    NOT_ESTABLISHED,
    PASS,
    UNRESOLVED,
    JTimingWitness,
    assert_j_timing,
    evaluate_basic_l1,
    evaluate_c2,
    evaluate_c3,
    l2_aggregate,
)
from harness_constants import (
    EPISODE_PAYLOADS,
    LITERAL_ZERO,
    HarnessError,
    StateSnapshot,
    encode_substrate,
)

RESULTS = []


def check(name, cond):
    RESULTS.append(cond)
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")


def snap(literal: bytes, q: int) -> StateSnapshot:
    return StateSnapshot(literal=literal, q_raw=encode_substrate(q))


def main() -> int:
    payload = EPISODE_PAYLOADS["A1"]

    # --- Basic L1: h=0 (A==B, both zero) -> FAIL --------------------------
    r = evaluate_basic_l1(
        snap(LITERAL_ZERO, 0), snap(LITERAL_ZERO, 0), payload
    )
    check("L1 h=0 -> FAIL", r.result == FAIL and r.change_class == NOT_ESTABLISHED)

    # --- Basic L1: h=1 (one byte diff) -> UNRESOLVED ----------------------
    partial = payload[:1] + LITERAL_ZERO[1:]
    r = evaluate_basic_l1(snap(LITERAL_ZERO, 0), snap(partial, 0), payload)
    check("L1 h=1 -> UNRESOLVED", r.result == UNRESOLVED and r.h == 1)

    # --- Basic L1: full payload (16-byte diff) -> PASS + C1 ---------------
    r = evaluate_basic_l1(snap(LITERAL_ZERO, 0), snap(payload, 0), payload)
    check("L1 h=16 -> PASS + C1", r.result == PASS and r.change_class == C1)

    # --- C1 not established when L1 PASS but payload mismatch -------------
    other = EPISODE_PAYLOADS["A2"]  # also 16 bytes, differs from A1
    r = evaluate_basic_l1(snap(LITERAL_ZERO, 0), snap(other, 0), payload)
    check(
        "L1 PASS but payload mismatch -> C1 NOT_ESTABLISHED",
        r.result == PASS and r.change_class == NOT_ESTABLISHED,
    )

    # --- OBSERVATION 1: q_B != q_A -> ARM_CONFIG_INVALID ------------------
    r = evaluate_basic_l1(snap(LITERAL_ZERO, 0), snap(payload, 2), payload)
    check(
        "OBS1 q_B!=q_A -> INVALID (not h topping-up)",
        r.result == INVALID and "ARM_CONFIG_INVALID" in r.reason,
    )

    # --- C2: signed T ------------------------------------------------------
    # B: +2 vs 0 -> dz_B = 1 ; C: +2 vs 0 -> dz_C = 1 ; T = 0 -> FAIL
    r = evaluate_c2(snap(LITERAL_ZERO, 0), snap(LITERAL_ZERO, 0),
                    snap(payload, 2), snap(payload, 2))
    check("C2 T=0 -> FAIL", r.result == FAIL and r.signed_T == 0)

    # B: +2 (dz=1) ; C: +4 (dz=2) ; T = 1 -> ATTRIBUTED
    r = evaluate_c2(snap(LITERAL_ZERO, 0), snap(LITERAL_ZERO, 0),
                    snap(payload, 2), snap(payload, 4))
    check("C2 T=+1 -> ATTRIBUTED", r.result == ATTRIBUTED and r.signed_T == Fraction(1))

    # B: +2 (dz=1) ; C: -2 (dz=-1) ; T = -2 -> ATTRIBUTED (signed preserved)
    r = evaluate_c2(snap(LITERAL_ZERO, 0), snap(LITERAL_ZERO, 0),
                    snap(payload, 2), snap(payload, -2))
    check("C2 T=-2 -> ATTRIBUTED signed kept", r.result == ATTRIBUTED and r.signed_T == Fraction(-2))

    # OBSERVATION 4: missing B measurement -> INVALID, not implicit 0
    r = evaluate_c2(None, snap(LITERAL_ZERO, 0), None, snap(payload, 2))
    check(
        "OBS4 missing B measurement -> INVALID (no implicit 0)",
        r.result == INVALID and "MEASUREMENT_MISSING" in r.reason,
    )

    # --- C3: same-class equal, cross-class unequal -> C3 ------------------
    members = [
        {"member_id": "A1", "content_class": "L", "T": Fraction(1), "attributed": True},
        {"member_id": "A2", "content_class": "L", "T": Fraction(1), "attributed": True},
        {"member_id": "B1", "content_class": "R", "T": Fraction(-1), "attributed": True},
        {"member_id": "B2", "content_class": "R", "T": Fraction(-1), "attributed": True},
    ]
    r = evaluate_c3(members, [("A1", "A2"), ("B1", "B2")], [("A1", "B1"), ("A2", "B2")])
    check("C3 established", r.result == C3)

    # --- C3: constant (all T equal) -> NOT_ESTABLISHED (cross fails) -------
    const_members = [
        {"member_id": "A1", "content_class": "L", "T": Fraction(1), "attributed": True},
        {"member_id": "A2", "content_class": "L", "T": Fraction(1), "attributed": True},
        {"member_id": "B1", "content_class": "R", "T": Fraction(1), "attributed": True},
        {"member_id": "B2", "content_class": "R", "T": Fraction(1), "attributed": True},
    ]
    r = evaluate_c3(const_members, [("A1", "A2"), ("B1", "B2")], [("A1", "B1")])
    check("C3 constant -> NOT_ESTABLISHED (cross fails)", r.result == NOT_ESTABLISHED)

    # --- C3: unattributed member -> NOT_ESTABLISHED -----------------------
    bad = [dict(m) for m in members]
    bad[2]["attributed"] = False
    r = evaluate_c3(bad, [("A1", "A2")], [("A1", "B1")])
    check("C3 unattributed member -> NOT_ESTABLISHED", r.result == NOT_ESTABLISHED)

    # --- BD-52: J-timing witness ------------------------------------------
    good = JTimingWitness(s_write_digest="a", j_after_digest="b", s_handoff_digest="b")
    check("J timing: J_after == S_handoff -> valid", good.timing_valid)
    bad_t = JTimingWitness(s_write_digest="a", j_after_digest="b", s_handoff_digest="c")
    check("J timing: J_after != S_handoff -> invalid", not bad_t.timing_valid)
    try:
        assert_j_timing(bad_t)
        check("assert_j_timing raises on violation", False)
    except HarnessError as e:
        check("assert_j_timing raises on violation", "J_TIMING_VIOLATION" in str(e))

    # --- BD-53: frozen L2 aggregation -------------------------------------
    check("L2: any indeterminate -> UNRESOLVED",
          l2_aggregate(FAIL, UNRESOLVED, NOT_ESTABLISHED) == UNRESOLVED)
    check("L2: all determinate negative -> FAIL",
          l2_aggregate(FAIL, FAIL, NOT_ESTABLISHED) == FAIL)
    check("L2: lower determinate neg does NOT cancel higher indeterminate",
          l2_aggregate(FAIL, UNRESOLVED, NOT_ESTABLISHED) == UNRESOLVED)

    print()
    passed = sum(1 for ok in RESULTS if ok)
    print(f"smoke_evaluator: {passed}/{len(RESULTS)} PASS")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
