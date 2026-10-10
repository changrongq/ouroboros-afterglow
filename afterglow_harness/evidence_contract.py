"""
evidence_contract.py (RC11) — the SINGLE frozen source of REQUIRED EVIDENCE and
its required CONSUMPTION (凌翼 RC10 ruling R2; 知微 RC10 review → RC11 fixes).

凌翼 RC10, R2:

    REQUIRED_EVIDENCE_CONSUMPTION_MATRIX

    Every required field must be:
      recorded
      consumed by production judgement
      consumed by replay judgement
      covered by deletion/corruption adversarial test

    Missing / empty / malformed required evidence MUST FAIL CLOSED.

    A field only earns the name REQUIRED EVIDENCE if it is
        RECORDED  AND  CONSUMED  AND  NEGATIVE-TESTED
    otherwise it is merely a log.

This module is DATA ONLY. It is the canonical contract that BOTH ingress
adapters read:

    · production ingress (fixtures.py)     -> live runtime -> EvidenceBundle
    · replay ingress     (replay_adapter)  -> raw ledger + THIS contract -> EvidenceBundle

The ledger may answer "what did I observe". It may NOT answer "what was I
supposed to observe". That second question is answered HERE, and only here.

Consumers:
  · evidence_bundle.py    -> PROBE_SETS, REQUIRED_RESET_FIELDS
  · fixtures.py           -> CONTRACT_BY_FIXTURE (production ingress)
  · replay_adapter.py     -> CONTRACT_BY_FIXTURE (replay ingress)
  · adversarial_regression.py -> REQUIRED_EVIDENCE_MATRIX (negative tests)
  · run_known_answer_suite.py -> REQUIRED_FIXTURE_IDS, oracle key schema
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Frozen neutral reader probe sets (凌翼 RC10: AFFINE_PROBES = LITERAL_PROBES = {0, 2})
# ---------------------------------------------------------------------------

AFFINE_PROBES = (0, 2)
LITERAL_PROBES = (0, 2)

#: The frozen key set that a reader witness MUST present. Exact equality is
#: required: {}, {"0"}, {"2"}, {"0","2","999"} are all ILLEGAL.
FROZEN_AFFINE_KEYS = frozenset(str(u) for u in AFFINE_PROBES)
FROZEN_LITERAL_KEYS = frozenset(str(u) for u in LITERAL_PROBES)

# ---------------------------------------------------------------------------
# Required reset-witness fields (凌翼 RC10: reset_valid is MANDATORY)
# ---------------------------------------------------------------------------

#: Every reset witness must carry ALL of these. A missing key => INVALID.
#: reset_valid has three-valued intent: True -> continue; anything else ->
#: INVALID (missing / False / malformed all fail closed).
REQUIRED_RESET_FIELDS = ("reset_valid", "accepted_handoff")

# ---------------------------------------------------------------------------
# Required phases per arm, and the frozen member/arm sets
# ---------------------------------------------------------------------------

REQUIRED_ARMS = ("A", "B", "C")
REQUIRED_PHASES = ("S_write", "S_handoff", "S_restored")
#: J-bearing arms additionally require the J_after witness phase.
J_ARMS = ("B", "C")
J_PHASE = "J_after"

MULTI_MEMBER_SET = ("A1", "A2", "B1", "B2")

# ---------------------------------------------------------------------------
# Per-fixture canonical CONTRACT (production AND replay derive from THIS)
# ---------------------------------------------------------------------------
#
# Fields:
#   shape                 : family tag (also the replay REQUIRED_SCOPE key)
#   required_members      : the frozen member set for this fixture
#   required_arms         : arms that must be present
#   required_phases       : phases that must be present per arm
#   required_pre_class    : the CONTRACT precondition on the pre-reset class
#                           ("" => no explicit precondition)
#   attempted             : the attempted-scope tag handed to the adjudicator
#   expected_keys         : the canonical derived-result keys replay must
#                           recompute AND compare (exact required scope)

_TWO_ARM = {
    "shape": "two_arm",
    "required_members": ("A1",),  # two-arm family is single-member (A1 payload)
    "required_arms": ("A", "B"),
    "required_phases": ("S_write",),
    "required_pre_class": "",
    "attempted": "full",
    "expected_keys": ("L1", "PRE_RESET_CHANGE_CLASS"),
}

# V4.1 has its OWN complete decision schema (凌翼/知微 RC11 §5): its special
# pre-reset C2-attempt INVALIDITY decision MUST be compared, not merely computed.
_V4_1 = {
    "shape": "two_arm",
    "required_members": ("A1",),
    "required_arms": ("A", "B"),
    "required_phases": ("S_write",),
    "required_pre_class": "",
    "attempted": "pre_reset_C2_only",
    "expected_keys": ("L1", "PRE_RESET_CHANGE_CLASS", "C2_ATTEMPT",
                      "INVALIDITY_CODE", "C3", "L2"),
}

# V4b has its OWN complete decision schema: the architectural non-separability
# decision (C2/C3) MUST be compared.
_V4_B = {
    "shape": "non_separable_wrapper",
    "required_members": ("A1",),
    "required_arms": ("A", "B"),
    "required_phases": ("S_write",),
    "required_pre_class": "",
    "attempted": "full",
    "expected_keys": ("L1", "PRE_RESET_CHANGE_CLASS", "C2", "C3"),
}

_MULTI_MEMBER = {
    "shape": "multi_member",
    "required_members": MULTI_MEMBER_SET,
    "required_arms": ("A", "B", "C"),
    "required_phases": ("S_write",),
    "required_pre_class": "",
    "attempted": "full",
    "expected_keys": ("L1", "PRE_RESET_CHANGE_CLASS", "C3"),
}

_NON_SEPARABLE = _V4_B  # retained name for clarity; V4b's canonical contract


def _reset_suite(j_mode: str, reset_fault: bool, attempted: str, required_pre_class: str) -> dict:
    return {
        "shape": "reset_suite",
        "required_members": MULTI_MEMBER_SET,
        "required_arms": REQUIRED_ARMS,
        "required_phases": REQUIRED_PHASES,
        "required_pre_class": required_pre_class,
        "attempted": attempted,
        "j_mode": j_mode,
        "reset_fault": reset_fault,
        "expected_keys": (
            "PRE_RESET_CHANGE_CLASS", "post_C3", "post_C1_ok", "reset_valid",
            "j_timing_ok", "L2", "POST_RESET_SUPPORTED_CLASS",
        ),
    }


CONTRACT_BY_FIXTURE = {
    "V0": dict(_TWO_ARM),
    "V0b": dict(_TWO_ARM),
    "V1": dict(_TWO_ARM),
    "V2": dict(_MULTI_MEMBER),
    "V3": dict(_MULTI_MEMBER),
    "V4.1": dict(_V4_1),
    "V4b": dict(_V4_B),
    "V5a": _reset_suite("IDENTITY", False, "full", "C3"),
    "V5b": _reset_suite("COLLAPSE_SIGN", False, "full", "C3"),
    "V5c": _reset_suite("IDENTITY", True, "full", "C3"),
    "V5d": _reset_suite("ERASE_EFFECT", False, "full", "C3"),
    "V5e": _reset_suite("HALVE_AND_ERASE_LITERAL", False, "full", "C3"),
    "V5f": _reset_suite("IDENTITY", False, "post_C1_only", "C1"),
}

#: The exact frozen fixture-id set. Replay REQUIRES observed == this set.
REQUIRED_FIXTURE_IDS = frozenset(CONTRACT_BY_FIXTURE.keys())

assert len(REQUIRED_FIXTURE_IDS) == 13, "exactly 13 fixtures are frozen"


# ---------------------------------------------------------------------------
# REQUIRED_EVIDENCE_CONSUMPTION_MATRIX  (凌翼 RC10 R2, the sole new structural requirement)
# ---------------------------------------------------------------------------
#
# Each entry binds ONE required evidence field to:
#   recorded_in    : where the field is captured
#   prod_gate      : the production adjudicator check that consumes it
#   replay_gate    : the replay-side check that consumes it (same chain)
#   negative_test  : the deletion/corruption test that proves it is mandatory
#
# A field with an empty/deleted/malformed value MUST fail closed in BOTH gates.

REQUIRED_EVIDENCE_CONSUMPTION_MATRIX = (
    {
        "field": 'reader_witness.affine["0"]',
        "recorded_in": "fixtures._realize_member -> MemberEvidence.reader_witness",
        "prod_gate": "evidence_bundle._independent_reader_ok (affine probe key == frozen set)",
        "replay_gate": "replay_adapter -> same evidence_bundle._independent_reader_ok",
        "negative_test": "CE-R1 delete affine['0'] -> Phase-A FAIL",
    },
    {
        "field": 'reader_witness.affine["2"]',
        "recorded_in": "fixtures._realize_member",
        "prod_gate": "evidence_bundle._independent_reader_ok (affine probe key == frozen set)",
        "replay_gate": "replay_adapter -> same gate",
        "negative_test": "CE-R2 delete affine['2'] -> Phase-A FAIL",
    },
    {
        "field": 'reader_witness.literal["0"]',
        "recorded_in": "fixtures._realize_member",
        "prod_gate": "evidence_bundle._independent_reader_ok (literal probe key == frozen set)",
        "replay_gate": "replay_adapter -> same gate",
        "negative_test": "CE-R3 delete literal['0'] -> Phase-A FAIL",
    },
    {
        "field": 'reader_witness.literal["2"]',
        "recorded_in": "fixtures._realize_member",
        "prod_gate": "evidence_bundle._independent_reader_ok (literal probe key == frozen set)",
        "replay_gate": "replay_adapter -> same gate",
        "negative_test": "CE-R4 delete literal['2'] -> Phase-A FAIL",
    },
    {
        "field": "reader_witness.raw_q  (redundant cross-check only)",
        "recorded_in": "fixtures._realize_member",
        "prod_gate": "evidence_bundle._independent_reader_ok (raw_q MUST == decode(S_restored.q_raw))",
        "replay_gate": "replay_adapter -> same gate",
        "negative_test": "CE-R5 corrupt raw_q -> Phase-A FAIL (cross-check)",
    },
    {
        "field": "reset_witness[arm].reset_valid",
        "recorded_in": "fixtures._reset_arm",
        "prod_gate": "evidence_bundle reset gate (missing/False -> INVALID)",
        "replay_gate": "replay_adapter -> same reset gate",
        "negative_test": "CE-R6 delete reset_valid -> INVALID / Phase-A FAIL",
    },
    {
        "field": "reset_witness[arm].accepted_handoff",
        "recorded_in": "fixtures._reset_arm",
        "prod_gate": "evidence_bundle._validate_handoff_continuity (byte-level)",
        "replay_gate": "replay_adapter -> same continuity gate",
        "negative_test": "CE-R7 alter accepted_handoff byte -> INVALID",
    },
    {
        "field": "arms[arm].S_handoff / arms[arm].J_after",
        "recorded_in": "fixtures._apply_j_witnessed",
        "prod_gate": "evidence_bundle._validate_j_witness (J_after == S_handoff byte-level)",
        "replay_gate": "replay_adapter -> same J gate",
        "negative_test": "CE-R8 change J_after byte -> INVALID",
    },
    {
        "field": "S_restored (verified-restored object identity)",
        "recorded_in": "fixtures._reset_arm -> arms[arm].S_restored",
        "prod_gate": "evidence_bundle reset-object identity (reset-verified == S_restored == reader input)",
        "replay_gate": "replay_adapter rebuilds S_restored from raw ledger; identity re-checked",
        "negative_test": "CE-R9 change S_restored vs verified-reset byte -> INVALID",
    },
    {
        "field": "fixture_id -> required_members",
        "recorded_in": "evidence_contract.CONTRACT_BY_FIXTURE (NOT the ledger)",
        "prod_gate": "evidence_bundle._validate_membership (frozen set equality)",
        "replay_gate": "replay_adapter takes members from CONTRACT, ignores ledger claim",
        "negative_test": "CE-R10 delete required member -> INVALID; CE-R11 ledger claims wrong member set -> replay uses contract",
    },
    {
        "field": "fixture_id -> required_pre_class",
        "recorded_in": "evidence_contract.CONTRACT_BY_FIXTURE (NOT the ledger)",
        "prod_gate": "evidence_bundle required_pre_class precondition",
        "replay_gate": "replay_adapter takes required_pre_class from CONTRACT, ignores ledger claim",
        "negative_test": "CE-R12 change C3->C2 -> FAIL; CE-R13 ledger claims no precondition -> replay still enforces contract",
    },
    {
        "field": "fixture_id -> attempted / shape",
        "recorded_in": "evidence_contract.CONTRACT_BY_FIXTURE (NOT the ledger)",
        "prod_gate": "evidence_bundle.evaluate_bundle(attempted=...)",
        "replay_gate": "replay_adapter takes attempted/shape from CONTRACT, ignores ledger claim",
        "negative_test": "CE-R14 ledger claims attempted=post_C1_only for V5a -> replay ignores, uses full",
    },
    {
        "field": "observed_fixture_ids (exact frozen 13-set)",
        "recorded_in": "replay_adapter (from ledger dir filenames)",
        "prod_gate": "run_known_answer_suite completeness check",
        "replay_gate": "replay_adapter exact set equality vs REQUIRED_FIXTURE_IDS",
        "negative_test": "CE-R15 drop one fixture ledger -> FAIL",
    },
    {
        "field": "fixture_id identity (filename == outer == ledger.fixture_id)",
        "recorded_in": "run_known_answer_suite (writes <id>.json with matching ids)",
        "prod_gate": "run_known_answer_suite completeness (ran ids unique == required)",
        "replay_gate": "replay_adapter.assert_exact_fixture_set (three-way identity + uniqueness)",
        "negative_test": "RC11 §6: 13 correct names w/ duplicate internal V1 -> FAIL; name/content mismatch -> FAIL",
    },
    {
        "field": "V4.1 / V4b special decision schema (C2_ATTEMPT/INVALIDITY_CODE/L2; C2/C3)",
        "recorded_in": "evidence_contract.CONTRACT_BY_FIXTURE expected_keys",
        "prod_gate": "fixtures runner emits the keys; run_known_answer_suite compares vs oracle",
        "replay_gate": "recompute_from_ledger exact key-set + value comparison",
        "negative_test": "RC11 §5: corrupt V4.1/V4b special fields -> replay FAIL",
    },
    {
        "field": "reset preserve rule (accepted_handoff == verified_restored, raw bytes)",
        "recorded_in": "fixtures._reset_arm reset_witness",
        "prod_gate": "evidence_bundle._validate_reset_object_identity (recomputed)",
        "replay_gate": "replay_adapter -> same preserve recomputation",
        "negative_test": "RC11 §7: handoff q != restored q w/ reset_valid=True -> INVALID (RESET_PRESERVE_RULE_BREAK)",
    },
    {
        "field": "same-run link (run manifest ledger_dir)",
        "recorded_in": "run_known_answer_suite writes RC11_run_manifest.json",
        "prod_gate": "qualify_phase_a reads the manifest to pick the replay dir",
        "replay_gate": "recompute_from_ledger --ledger <that dir>",
        "negative_test": "RC11 §4: clean snapshot PASS; aggregator has no hard-coded version dir",
    },
    {
        "field": "V4b separable positive control (probe validity)",
        "recorded_in": "fixtures.external_capability_probe(SeparableControlHandle)",
        "prod_gate": "fixtures.external_capability_probe -> evaluate_c2_architectural",
        "replay_gate": "recompute_from_ledger re-runs the probe (observed, not hardcoded)",
        "negative_test": "CE-R16 probe must return separable_w_extra=True on a selector-bearing control; else PROBE_INVALID",
    },
)


def get_contract(fixture_id: str) -> dict:
    """Return the canonical contract for a fixture id, FAIL CLOSED if unknown."""
    if fixture_id not in CONTRACT_BY_FIXTURE:
        raise KeyError(f"UNKNOWN_FIXTURE_ID: {fixture_id!r} not in frozen contract")
    return CONTRACT_BY_FIXTURE[fixture_id]
