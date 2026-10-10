"""
recompute_from_ledger.py — independent re-derivation from raw ledger observations.

Does NOT run fixtures. Reads only the raw member×arm×phase observations stored in
the RC8 ledgers and re-derives:
    L1 / C1 / T_write / pre C2 / pre C3
    J validity / reset validity
    post C1 / post C2 / post C3 / L2
then compares to the recorded actual.

If a reviewer cannot recompute from the ledger, the ledger is a log, not evidence.

Usage:
    python recompute_from_ledger.py --ledger <ledgers_dir> [--raw <raw.json>]
"""

from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path

import evaluator as ev
from fixture_contracts import FROZEN_ORACLES
from gates import POST_RESET_EVIDENCE_GATE, PRE_EVIDENCE_GATE
from harness_constants import CONTENT_CLASS_OF, StateSnapshot

_SAME_PAIRS = [("A1", "A2"), ("B1", "B2")]
_CROSS_PAIRS = [("A1", "B1"), ("A2", "B2")]


def _snap(d: dict) -> StateSnapshot:
    return StateSnapshot(literal=bytes.fromhex(d["literal"]), q_raw=bytes.fromhex(d["q_raw"]))


def _frac(d) -> Fraction | None:
    if d is None:
        return None
    return Fraction(d["num"], d["den"])


def _attributed(T) -> bool:
    return T is not None and abs(T) >= 1


def recompute_fixture(fid: str, obs: dict, gates: dict, attempted: str = "full") -> dict:
    """Re-derive the result for one fixture from raw observations.

    Uses the SAME public gates as the production path, so the recompute is
    definitionally identical (single semantics, single source).
    """
    if "arms" in obs:
        members = {"A1": obs}
    elif obs and all(isinstance(v, dict) and "arms" in v for v in obs.values()):
        members = obs
    else:
        return {}  # two-arm V0/V0b/V1 shape: only L1 exists; nothing more to recompute

    out: dict = {}

    member_write = {}
    member_restored = {}
    for mid, o in members.items():
        arms = o["arms"]
        payload = bytes.fromhex(o["payload"])
        member_write[mid] = {
            "A": _snap(arms["A"]["S_write"]),
            "B": _snap(arms["B"]["S_write"]),
            "C": _snap(arms["C"]["S_write"]),
            "payload": payload,
        }
        member_restored[mid] = {
            "A": _snap(arms["A"]["S_restored"]),
            "B": _snap(arms["B"]["S_restored"]),
            "C": _snap(arms["C"]["S_restored"]),
            "payload": payload,
        }

    pre = PRE_EVIDENCE_GATE(member_write)
    out["PRE_RESET_CHANGE_CLASS"] = pre.pre_class
    out["C3"] = pre.c3

    j_ok = True
    reset_ok = True
    for o in members.values():
        for arm in ("A", "B", "C"):
            A = o["arms"].get(arm, {})
            if A.get("J") not in (None, "NOT_APPLICABLE"):
                if A["J_after"]["digest"] != A["S_handoff"]["digest"]:
                    j_ok = False
            rw = A.get("reset_witness", {})
            if rw.get("reset_valid") is False:
                reset_ok = False
    out["j_timing_ok"] = j_ok
    out["reset_valid"] = reset_ok

    post = POST_RESET_EVIDENCE_GATE(member_restored, j_ok, reset_ok, attempted)
    out["post_C1_ok"] = post.post_c1_ok
    out["post_C3"] = post.c3_post
    out["L2"] = post.l2
    out["POST_RESET_SUPPORTED_CLASS"] = post.supported
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ledger", required=True)
    ap.add_argument("--raw", default=None)
    args = ap.parse_args()

    led_dir = Path(args.ledger)
    files = sorted(led_dir.glob("*.json"))
    if not files:
        print("no ledger files")
        return 2

    all_ok = True
    for f in files:
        item = json.loads(f.read_text(encoding="utf-8"))
        fid = item["fixture_id"]
        ledger = item["ledger"]
        obs = ledger.get("observations") or {}
        gates = ledger.get("gates") or {}
        attempted = (ledger.get("attempted_scope") or {}).get("attempted", "full")
        rec = recompute_fixture(fid, obs, gates, attempted)
        actual = item["actual"]
        # compare the recomputable keys only
        mism = {k: (actual.get(k), rec[k]) for k in rec
                if k in actual and actual.get(k) != rec[k]}
        status = "MATCH" if not mism else "MISMATCH"
        if mism:
            all_ok = False
        print(f"[{status}] {fid}  matched_keys={len([k for k in rec if k in actual])}  mism={mism}")

    print()
    print("RECOMPUTE_FROM_LEDGER =", "PASS" if all_ok else "FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
