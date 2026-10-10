"""
replay_adapter.py (RC10) — the REPLAY INGRESS adapter.

凌翼 RC10 R3:

    same adjudication chain, different ingress.

    production ingress : live runtime -> EvidenceBundle
    replay ingress     : raw ledger + canonical fixture contract -> EvidenceBundle

Replay rebuilds an EvidenceBundle from:
  · the ledger's RAW OBSERVED BYTES (what was observed), and
  · the fixture_id -> canonical CONTRACT (evidence_contract.CONTRACT_BY_FIXTURE)
    — which decides members / arms / phases / required_pre_class / attempted /
      shape / expected result schema.

The ledger may answer "what did I observe". It may NOT answer "what was I
supposed to observe". Therefore this adapter IGNORES any ledger self-claim of
required_members / required_pre_class / attempted / shape, and takes all of
those from the frozen contract.

It then hands the rebuilt bundle to the SAME pure adjudicator
(evidence_bundle.evaluate_bundle) that production uses.
"""

from __future__ import annotations

from pathlib import Path

from evidence_contract import REQUIRED_FIXTURE_IDS, get_contract
from evidence_bundle import (
    ArmPhase,
    EvidenceBundle,
    MemberEvidence,
    evaluate_bundle,
)
from harness_constants import CONTENT_CLASS_OF, HarnessError


class ReplayContractError(HarnessError):
    """Any replay-time contract violation. FAIL CLOSED."""


def _rebuild_member(mid: str, m: dict) -> MemberEvidence:
    if not isinstance(m, dict):
        raise ReplayContractError(f"MEMBER_RECORD_MALFORMED: {mid}")
    payload = m.get("payload")
    if not isinstance(payload, str):
        raise ReplayContractError(f"MEMBER_PAYLOAD_MISSING: {mid}")
    me = MemberEvidence(member_id=mid,
                        content_class=CONTENT_CLASS_OF.get(mid, "?"),
                        payload=bytes.fromhex(payload))
    arms = m.get("arms")
    if not isinstance(arms, dict):
        raise ReplayContractError(f"MEMBER_ARMS_MISSING: {mid}")
    for arm, phases in arms.items():
        if not isinstance(phases, dict):
            raise ReplayContractError(f"MEMBER_ARM_MALFORMED: {mid}/{arm}")
        me.arms[arm] = {}
        for ph, ap in phases.items():
            if not isinstance(ap, dict) or "literal" not in ap or "q_raw" not in ap:
                raise ReplayContractError(f"PHASE_RECORD_MALFORMED: {mid}/{arm}/{ph}")
            me.arms[arm][ph] = ArmPhase(bytes.fromhex(ap["literal"]),
                                        bytes.fromhex(ap["q_raw"]))
    me.reset_witness = m.get("reset_witness", {})
    me.reader_witness = m.get("reader_witness", {})
    return me


def build_bundle_from_ledger(fixture_id: str, observations: dict) -> tuple[EvidenceBundle, dict]:
    """Build the EvidenceBundle for replay STRICTLY from the contract + raw
    observed bytes. Returns (bundle, contract).

    Raises ReplayContractError if the ledger does not even contain the frozen
    member set with well-formed raw bytes. It does NOT trust any ledger claim of
    required_members / required_pre_class / attempted / shape.
    """
    contract = get_contract(fixture_id)
    required_members = tuple(contract["required_members"])

    # STRUCTURAL: the ledger observations must contain EXACTLY the contract
    # member set. A missing member => INVALID (never a lower-tier PASS).
    got_members = set(observations.keys())
    if got_members != set(required_members):
        raise ReplayContractError(
            f"MEMBER_SET_MISMATCH: contract={sorted(required_members)} "
            f"ledger={sorted(got_members)}"
        )

    b = EvidenceBundle(
        fixture_id=fixture_id,
        required_members=required_members,
        required_arms=tuple(contract["required_arms"]),
        required_phases=tuple(contract["required_phases"]),
    )
    for mid in required_members:
        b.members[mid] = _rebuild_member(mid, observations[mid])
    return b, contract


def adjudicate_fixture_from_ledger(fixture_id: str, observations: dict) -> "GateResult":
    """Rebuild + adjudicate via the SAME pure chain production uses."""
    b, contract = build_bundle_from_ledger(fixture_id, observations)
    return evaluate_bundle(
        b,
        required_pre_class=contract["required_pre_class"],
        expected_post_supported_class=None,
        attempted=contract["attempted"],
    )


def observed_fixture_ids(ledger_dir: Path) -> set:
    return {p.stem for p in Path(ledger_dir).glob("*.json")}


def assert_exact_fixture_set(ledger_dir: Path) -> None:
    """Replay REQUIRES the exact frozen 13-fixture set: observed == required."""
    got = observed_fixture_ids(ledger_dir)
    if got != set(REQUIRED_FIXTURE_IDS):
        missing = sorted(set(REQUIRED_FIXTURE_IDS) - got)
        extra = sorted(got - set(REQUIRED_FIXTURE_IDS))
        raise ReplayContractError(
            f"FIXTURE_SET_MISMATCH: missing={missing} extra={extra}"
        )
