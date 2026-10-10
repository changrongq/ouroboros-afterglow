"""
fixture_contracts.py — the SINGLE bound canonical source for fixture configs and
frozen oracles (凌翼 RC8 ruling: ORACLE one bound canonical source).

Consumers:
  · fixtures.py            -> FIXTURE_CONFIGS only (never the oracle)
  · the runner comparator  -> FROZEN_ORACLES only
  · evaluator.py           -> NEITHER (this module must never be imported there)

This module intentionally contains NO executable logic beyond data, so that its
hash is the contract identity.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Fixture CONFIGS — construction parameters only (no expected answers)
# ---------------------------------------------------------------------------

FIXTURE_CONFIGS = {
    "V0":   {"kind": "two_arm", "A_mode": "NO_WRITE", "B_mode": "STORE_NULL", "payload": "A1"},
    "V0b":  {"kind": "two_arm", "A_mode": "NO_WRITE", "B_mode": "STORE_ONE_BYTE", "payload": "A1"},
    "V1":   {"kind": "two_arm", "A_mode": "NO_WRITE", "B_mode": "STORE_FULL", "payload": "A1"},
    "V2":   {"kind": "multi_member", "extra_mode": "EXTRA_CONSTANT", "ceiling": "C2"},
    "V3":   {"kind": "multi_member", "extra_mode": "EXTRA_CONTENT", "ceiling": "C3"},
    "V4.1": {"kind": "two_arm_rule_missing", "A_mode": "NO_WRITE", "B_mode": "STORE_FULL",
             "payload": "A1", "missing_rule": "CAUSAL_CONTRAST_RULE"},
    "V4b":  {"kind": "non_separable_wrapper"},
    "V5a":  {"kind": "reset_suite", "j_mode": "IDENTITY", "reset_fault": False, "attempted": "full"},
    "V5b":  {"kind": "reset_suite", "j_mode": "COLLAPSE_SIGN", "reset_fault": False, "attempted": "full"},
    "V5c":  {"kind": "reset_suite", "j_mode": "IDENTITY", "reset_fault": True, "attempted": "full"},
    "V5d":  {"kind": "reset_suite", "j_mode": "ERASE_EFFECT", "reset_fault": False, "attempted": "full"},
    "V5e":  {"kind": "reset_suite", "j_mode": "HALVE_AND_ERASE_LITERAL", "reset_fault": False, "attempted": "full"},
    "V5f":  {"kind": "reset_suite", "j_mode": "IDENTITY", "reset_fault": False, "attempted": "post_C1_only",
             "pre_extra": "OFF"},
}

REQUIRED_FIXTURE_IDS = frozenset(FIXTURE_CONFIGS.keys())

# ---------------------------------------------------------------------------
# FROZEN ORACLES — the unique expected result per fixture.
# The runner comparator consumes THIS ONLY. fixtures.py must not read it.
# ---------------------------------------------------------------------------

FROZEN_ORACLES = {
    "V0":   {"L1": "FAIL"},
    "V0b":  {"L1": "UNRESOLVED"},
    "V1":   {"L1": "PASS", "PRE_RESET_CHANGE_CLASS": "C1",
             "C2": "NOT_ASSESSED", "C3": "NOT_ASSESSED"},
    "V2":   {"L1": "PASS", "PRE_RESET_CHANGE_CLASS": "C2", "C3": "NOT_ESTABLISHED"},
    "V3":   {"L1": "PASS", "PRE_RESET_CHANGE_CLASS": "C3", "C3": "C3"},
    "V4.1": {"L1": "PASS", "PRE_RESET_CHANGE_CLASS": "C1", "C2_ATTEMPT": "INVALID",
             "INVALIDITY_CODE": "CAUSAL_CONTRAST_RULE_MISSING",
             "C3": "NOT_ASSESSED", "L2": "N/A"},
    "V4b":  {"L1": "PASS", "PRE_RESET_CHANGE_CLASS": "C1",
             "C2": "ARCHITECTURALLY_NOT_IDENTIFIABLE",
             "C3": "ARCHITECTURALLY_NOT_IDENTIFIABLE"},
    "V5a":  {"L2": "PASS", "POST_RESET_SUPPORTED_CLASS": "C3", "j_timing_ok": True, "reset_valid": True},
    "V5b":  {"L2": "PASS", "POST_RESET_SUPPORTED_CLASS": "C2", "post_C3": "NOT_ESTABLISHED",
             "j_timing_ok": True, "reset_valid": True},
    "V5c":  {"L2": "INVALID", "reset_valid": False},
    "V5d":  {"L2": "FAIL", "j_timing_ok": True, "reset_valid": True},
    "V5e":  {"L2": "UNRESOLVED", "j_timing_ok": True, "reset_valid": True},
    "V5f":  {"L2": "PASS", "POST_RESET_SUPPORTED_CLASS": "C1",
             "post_C2": "NOT_ASSESSED", "post_C3": "NOT_ASSESSED", "j_timing_ok": True, "reset_valid": True},
}

assert set(FROZEN_ORACLES.keys()) == set(REQUIRED_FIXTURE_IDS), "contract id mismatch"
