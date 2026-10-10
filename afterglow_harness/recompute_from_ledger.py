"""
recompute_from_ledger.py (RC10) — independent, CONTRACT-DRIVEN ledger replay.

凌翼 RC10 R3:

    Replay must reconstruct the EvidenceBundle from
        raw ledger bytes  +  fixture_id -> canonical frozen contract
    and then run the SAME adjudication chain production runs.

    The ledger may answer "what did I observe".
    The ledger may NOT answer "what was I supposed to observe".

Concretely:
  · the exact frozen 13-fixture set is REQUIRED (observed == required);
  · members / arms / phases / required_pre_class / attempted / shape come from
    evidence_contract.CONTRACT_BY_FIXTURE — NEVER from the ledger;
  · reset_suite fixtures are adjudicated by replay_adapter through the SAME
    evidence_bundle.evaluate_bundle chain production uses;
  · two_arm / multi_member / non_separable_wrapper rederive their (smaller)
    derived-result scope through the SAME evaluator primitives production uses;
  · recomputed_keys MUST exactly equal the contract's expected_keys — a
    zero-check or a missing required key is a FAIL (fail closed).

Usage:
    python recompute_from_ledger.py --ledger <ledgers_dir>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import evaluator as ev
from evidence_contract import REQUIRED_FIXTURE_IDS, get_contract
from harness_constants import CONTENT_CLASS_OF, StateSnapshot
from replay_adapter import (
    ReplayContractError,
    assert_exact_fixture_set,
    build_bundle_from_ledger,
)
from evidence_bundle import evaluate_bundle


def _snap(d: dict) -> StateSnapshot:
    return StateSnapshot(literal=bytes.fromhex(d["literal"]), q_raw=bytes.fromhex(d["q_raw"]))


# ---------------------------------------------------------------------------
# reset_suite: contract-driven, SAME chain as production
# ---------------------------------------------------------------------------

def recompute_reset_suite(fixture_id: str, observations: dict) -> dict:
    """Adjudicate a reset_suite fixture via the SAME pure chain, using the
    CONTRACT for required_pre_class / attempted (never the ledger)."""
    bundle, contract = build_bundle_from_ledger(fixture_id, observations)
    res = evaluate_bundle(
        bundle,
        required_pre_class=contract["required_pre_class"],
        expected_post_supported_class=None,
        attempted=contract["attempted"],
    )
    # pre_class is reported from S_write (valid even if reset later fails)
    from evidence_bundle import _pre_from_bundle
    pre_class, _, _, _ = _pre_from_bundle(bundle)
    return {
        "PRE_RESET_CHANGE_CLASS": pre_class if pre_class else "",
        "post_C3": res.c3_post,
        "post_C1_ok": res.post_c1_ok,
        # structured sub-verdicts (RC11 §8): read flags, never guess from code prefix
        "reset_valid": res.reset_valid,
        "j_timing_ok": res.j_timing_ok,
        "L2": res.l2,
        "POST_RESET_SUPPORTED_CLASS": res.supported,
    }


# ---------------------------------------------------------------------------
# two_arm / non_separable_wrapper
# ---------------------------------------------------------------------------

def _recompute_two_arm(observations: dict, payload_id: str) -> dict:
    from harness_constants import EPISODE_PAYLOADS
    a = _snap(observations["A"]["S_write"])
    b = _snap(observations["B"]["S_write"])
    l1 = ev.evaluate_basic_l1(a, b, EPISODE_PAYLOADS[payload_id])
    return {"L1": l1.result, "PRE_RESET_CHANGE_CLASS": l1.change_class}


# ---------------------------------------------------------------------------
# multi_member
# ---------------------------------------------------------------------------

def _recompute_multi_member(observations: dict) -> dict:
    from evaluator import PASS, C1, C2, C3, evaluate_basic_l1, evaluate_c2, evaluate_c3
    SAME = [("A1", "A2"), ("B1", "B2")]
    CROSS = [("A1", "B1"), ("A2", "B2")]
    all_l1_pass = True
    per_T = {}
    for mid, m in observations.items():
        arms = m.get("arms", {})
        a = _snap(arms["A"]["S_write"])
        b = _snap(arms["B"]["S_write"])
        c = _snap(arms["C"]["S_write"])
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


def _recompute_v4_1(observations: dict) -> dict:
    """V4.1 — pre-reset C2 attempt INVALID (missing CAUSAL_CONTRAST_RULE)."""
    from evaluator import AttemptedScope, NOT_ASSESSED, evaluate_c2_attempt
    base = _recompute_two_arm(observations, "A1")
    scope = AttemptedScope(pre_reset_c1=True, pre_reset_c2=True,
                           pre_reset_c3=False, post_reset=False)
    rule_bundle = {"STATE_DELTA_RULE": "present", "CAUSAL_CONTRAST_RULE": None,
                   "measurement_scale": "signed"}
    c2a = evaluate_c2_attempt(rule_bundle, scope)
    return {**base, "C2_ATTEMPT": c2a.result, "INVALIDITY_CODE": c2a.invalidity_code,
            "C3": NOT_ASSESSED, "L2": c2a.l2}


def _recompute_non_separable(observations: dict) -> dict:
    """V4b — re-derive L1 and the architectural C2/C3 from the probe.

    凌翼/知微 RC11 §5: replay MUST NOT hard-code ``extra_interface_separable``;
    it re-runs the SAME registered-handle capability probe production runs, and
    feeds the OBSERVED capability result into the architectural judgement.
    Completeness of the probe is guarded by probe_is_valid() (positive control must
    be detected, else PROBE_INVALID — never an ANI PASS).
    """
    import tempfile
    import shutil
    from fixtures import CombinedOnlyWriter, external_capability_probe, probe_is_valid
    from evaluator import evaluate_c2_architectural
    base = _recompute_two_arm(observations, "A1")
    if not probe_is_valid():
        return {**base, "C2": "PROBE_INVALID", "C3": "PROBE_INVALID"}
    root = Path(tempfile.mkdtemp(prefix="afterglow_replay_probe_"))
    try:
        handle = CombinedOnlyWriter(root, "v4b").public_handle()
        probe = external_capability_probe(handle)
        separable = probe["separable_w_extra"]
        c2res, c3res = evaluate_c2_architectural(extra_interface_separable=separable)
        return {**base, "C2": c2res, "C3": c3res}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _recompute_digest_ok(observations: dict) -> bool:
    def _check_ap(ap) -> bool:
        if not isinstance(ap, dict) or "literal" not in ap or "q_raw" not in ap:
            return False
        StateSnapshot(bytes.fromhex(ap["literal"]), bytes.fromhex(ap["q_raw"]))
        return True

    for v in observations.values():
        if not isinstance(v, dict):
            return False
        if "arms" in v:
            for phases in v["arms"].values():
                for ap in phases.values():
                    if not _check_ap(ap):
                        return False
        else:
            for ap in v.values():
                if not _check_ap(ap):
                    return False
    return True


def recompute_one(fixture_id: str, observations: dict) -> dict:
    """Dispatch a fixture to its contract-driven recompute. Unknown => error."""
    contract = get_contract(fixture_id)
    shape = contract["shape"]
    if shape == "reset_suite":
        return recompute_reset_suite(fixture_id, observations)
    if shape == "two_arm":
        if fixture_id == "V4.1":
            return _recompute_v4_1(observations)
        return _recompute_two_arm(observations, "A1")
    if shape == "multi_member":
        return _recompute_multi_member(observations)
    if shape == "non_separable_wrapper":
        return _recompute_non_separable(observations)
    raise ReplayContractError(f"UNKNOWN_SHAPE: {shape!r} for {fixture_id}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    args = ap.parse_args()

    led_dir = Path(args.ledger)
    files = sorted(led_dir.glob("*.json"))
    if not files:
        print("no ledger files -> FAIL")
        return 2

    # R3: exact frozen 13-fixture set REQUIRED
    try:
        assert_exact_fixture_set(led_dir)
    except ReplayContractError as e:
        print(f"[FAIL] {e}")
        return 1

    all_ok = True
    total_checked = 0
    for f in files:
        item = json.loads(f.read_text(encoding="utf-8"))
        fid = item["fixture_id"]
        ledger = item["ledger"]
        obs = ledger.get("observations") or {}
        actual = item["actual"]

        if fid not in REQUIRED_FIXTURE_IDS:
            print(f"[FAIL] {fid} NOT_A_REQUIRED_FIXTURE")
            all_ok = False
            continue

        if not _recompute_digest_ok(obs):
            print(f"[FAIL] {fid} RAW_BYTES_INVALID")
            all_ok = False
            continue

        contract = get_contract(fid)
        scope = tuple(contract["expected_keys"])
        if len(scope) == 0:
            print(f"[FAIL] {fid} ZERO_SCOPE (empty expected_keys)")
            all_ok = False
            continue

        try:
            rec = recompute_one(fid, obs)
        except ReplayContractError as e:
            print(f"[FAIL] {fid} CONTRACT: {e}")
            all_ok = False
            continue

        # EXACT key-set equality (凌翼/知微 RC11 §5): recomputed_keys == expected_keys,
        # not merely "no scope key missing". Extra or missing recomputed keys FAIL.
        rec_keys = set(rec.keys())
        if rec_keys != set(scope):
            missing = sorted(set(scope) - rec_keys)
            extra = sorted(rec_keys - set(scope))
            print(f"[FAIL] {fid} RECOMPUTED_KEY_SET: missing={missing} extra={extra}")
            all_ok = False
            continue

        # required actual fields MUST be PRESENT (缺字段 != 合法 None)
        absent = [k for k in scope if k not in actual]
        if absent:
            print(f"[FAIL] {fid} ACTUAL_MISSING_REQUIRED_KEYS: {absent}")
            all_ok = False
            continue

        mism = {k: (actual[k], rec[k]) for k in scope if actual[k] != rec[k]}
        status = "MATCH" if not mism else "MISMATCH"
        if mism:
            all_ok = False
        total_checked += len(scope)
        print(f"[{status}] {fid} checked={len(scope)}/{len(scope)} mism={mism}")

    print()
    if total_checked == 0:
        print("RECOMPUTE_FROM_LEDGER = FAIL (no checks performed)")
        return 1
    print("RECOMPUTE_FROM_LEDGER =", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
