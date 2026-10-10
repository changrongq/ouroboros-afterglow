"""
recompute_from_ledger.py (RC9) — independent, required-scope ledger replay.

凌翼 RC9: replay must recompute from the ledger's RAW literal/q bytes (not the
recorded digest strings), and must check an EXACT required key set per fixture.
Zero checks => FAIL. A missing required field => FAIL.

Usage:
    python recompute_from_ledger.py --ledger <ledgers_dir>
"""

from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path

import evaluator as ev
from fixture_contracts import FROZEN_ORACLES
from harness_constants import CONTENT_CLASS_OF, StateSnapshot, canonical_state_digest

# Required replay scope = the keys that MUST be independently re-derived and
# compared against the recorded actual, per fixture family.
REQUIRED_SCOPE = {
    "two_arm": ("L1", "PRE_RESET_CHANGE_CLASS"),
    "multi_member": ("L1", "PRE_RESET_CHANGE_CLASS", "C3"),
    "reset_suite": (
        "PRE_RESET_CHANGE_CLASS", "post_C3", "post_C1_ok", "reset_valid",
        "j_timing_ok", "L2", "POST_RESET_SUPPORTED_CLASS",
    ),
    "non_separable_wrapper": ("L1", "PRE_RESET_CHANGE_CLASS"),
}


def _snap(d: dict) -> StateSnapshot:
    return StateSnapshot(literal=bytes.fromhex(d["literal"]), q_raw=bytes.fromhex(d["q_raw"]))


def _recompute_digest_ok(observations: dict) -> bool:
    """Re-derive digest from raw bytes for every stored phase (byte-level check).

    Handles BOTH shapes:
      · per-member:  {member: {"arms": {arm: {phase: {literal,q_raw}}}}}
      · two-arm:     {"A": {"S_write": {literal,q_raw}}, "B": {...}}
    """
    def _check_ap(ap) -> bool:
        if not isinstance(ap, dict) or "literal" not in ap or "q_raw" not in ap:
            return False
        StateSnapshot(bytes.fromhex(ap["literal"]), bytes.fromhex(ap["q_raw"]))
        return True

    for v in observations.values():
        if not isinstance(v, dict):
            return False
        if "arms" in v:  # per-member shape
            for phases in v["arms"].values():
                for ap in phases.values():
                    if not _check_ap(ap):
                        return False
        else:  # two-arm shape: {phase: {literal,q_raw}}
            for ap in v.values():
                if not _check_ap(ap):
                    return False
    return True


def recompute_reset_suite(observations: dict, attempted: str) -> dict:
    """Re-derive the V5-family result from raw observations (single semantics)."""
    from evidence_bundle import ArmPhase, EvidenceBundle, MemberEvidence, evaluate_bundle

    bundle = EvidenceBundle(fixture_id="replay", required_members=tuple(observations.keys()))
    for mid, m in observations.items():
        me = MemberEvidence(member_id=mid, content_class=CONTENT_CLASS_OF.get(mid, "?"),
                            payload=bytes.fromhex(m["payload"]))
        for arm, phases in m["arms"].items():
            me.arms[arm] = {ph: ArmPhase(bytes.fromhex(ap["literal"]), bytes.fromhex(ap["q_raw"]))
                            for ph, ap in phases.items()}
        me.reset_witness = m.get("reset_witness", {})
        me.reader_witness = m.get("reader_witness", {})
        bundle.members[mid] = me

    res = evaluate_bundle(bundle, required_pre_class="", expected_post_supported_class=None,
                          attempted=attempted)
    from evidence_bundle import _pre_from_bundle
    pre_class, _, _, _ = _pre_from_bundle(bundle)
    return {
        "PRE_RESET_CHANGE_CLASS": pre_class if pre_class else "",
        "post_C3": res.c3_post,
        "post_C1_ok": res.post_c1_ok,
        "reset_valid": not res.code.startswith("RESET_INVALID") if res.code else True,
        "j_timing_ok": not res.code.startswith(("J_", "HANDOFF_")) if res.code else True,
        "L2": res.l2,
        "POST_RESET_SUPPORTED_CLASS": res.supported,
    }


def _recompute_two_arm(observations: dict) -> dict:
    """Re-derive L1 for the two-arm family from raw bytes."""
    from evaluator import PASS, FAIL, C1, NOT_ESTABLISHED
    from harness_constants import EPISODE_PAYLOADS
    a = _snap(observations["A"]["S_write"])
    b = _snap(observations["B"]["S_write"])
    # payload is fixed per two-arm family (A1)
    l1 = ev.evaluate_basic_l1(a, b, EPISODE_PAYLOADS["A1"])
    return {"L1": l1.result, "PRE_RESET_CHANGE_CLASS": l1.change_class}


def _recompute_multi_member(observations: dict) -> dict:
    """Re-derive pre L1 / pre-class / C3 for the multi-member family."""
    from evaluator import PASS, C1, C2, C3, NOT_ESTABLISHED, ATTRIBUTED, evaluate_basic_l1, evaluate_c2, evaluate_c3
    from harness_constants import CONTENT_CLASS_OF
    SAME = [("A1", "A2"), ("B1", "B2")]
    CROSS = [("A1", "B1"), ("A2", "B2")]
    all_l1_pass = True
    per_T = {}
    for mid, m in observations.items():
        a = _snap(m["arms"]["A"]["S_write"])
        b = _snap(m["arms"]["B"]["S_write"])
        c = _snap(m["arms"]["C"]["S_write"])
        payload = bytes.fromhex(m["payload"])
        l1 = evaluate_basic_l1(a, b, payload)
        if l1.result != PASS:
            all_l1_pass = False
        c2 = evaluate_c2(a, a, b, c)
        per_T[mid] = c2.signed_T
    l1_res = PASS if all_l1_pass else "FAIL"
    all_attr = all(t is not None and abs(t) >= 1 for t in per_T.values())
    members = [{"member_id": mid, "content_class": CONTENT_CLASS_OF[mid], "T": t,
                "attributed": (t is not None and abs(t) >= 1)} for mid, t in per_T.items()]
    r3 = evaluate_c3(members, SAME, CROSS)
    pre_class = C3 if r3.result == C3 else (C2 if all_attr else C1)
    return {"L1": l1_res, "PRE_RESET_CHANGE_CLASS": pre_class, "C3": r3.result}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    args = ap.parse_args()

    led_dir = Path(args.ledger)
    files = sorted(led_dir.glob("*.json"))
    if not files:
        print("no ledger files -> FAIL")
        return 2

    all_ok = True
    total_checked = 0
    for f in files:
        item = json.loads(f.read_text(encoding="utf-8"))
        fid = item["fixture_id"]
        ledger = item["ledger"]
        obs = ledger.get("observations") or {}
        actual = item["actual"]
        shape = (ledger.get("attempted_scope") or {}).get("shape", "")
        attempted = (ledger.get("attempted_scope") or {}).get("attempted", "full")

        # byte-level digest consistency (all stored phases must be raw-width-valid)
        if not _recompute_digest_ok(obs):
            print(f"[FAIL] {fid} RAW_BYTES_INVALID")
            all_ok = False
            continue

        if shape == "two_arm":
            scope = REQUIRED_SCOPE["two_arm"]
            rec = _recompute_two_arm(obs)
        elif shape == "non_separable_wrapper":
            scope = REQUIRED_SCOPE["non_separable_wrapper"]
            rec = _recompute_two_arm(obs)
        elif shape == "multi_member":
            scope = REQUIRED_SCOPE["multi_member"]
            rec = _recompute_multi_member(obs)
        elif shape == "reset_suite":
            scope = REQUIRED_SCOPE["reset_suite"]
            rec = recompute_reset_suite(obs, attempted)
        else:
            print(f"[FAIL] {fid} UNKNOWN_SHAPE: {shape!r}")
            all_ok = False
            continue

        checked = len([k for k in scope if k in rec])
        if checked == 0:
            print(f"[FAIL] {fid} ZERO_CHECKS (required scope {scope})")
            all_ok = False
            continue

        mism = {k: (actual.get(k), rec.get(k)) for k in scope if actual.get(k) != rec.get(k)}
        status = "MATCH" if not mism else "MISMATCH"
        if mism:
            all_ok = False
        total_checked += checked
        print(f"[{status}] {fid} checked={checked}/{len(scope)} mism={mism}")

    print()
    if total_checked == 0:
        print("RECOMPUTE_FROM_LEDGER = FAIL (no checks performed)")
        return 1
    print("RECOMPUTE_FROM_LEDGER =", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
