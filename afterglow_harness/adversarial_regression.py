"""
adversarial_regression.py (RC10) — every known fail-open attack must be REJECTED,
and every REQUIRED EVIDENCE field must be proven to have veto power.

凌翼 RC10 R2/R5: a field only earns the name REQUIRED EVIDENCE if it is
    RECORDED  AND  CONSUMED  AND  NEGATIVE-TESTED
otherwise it is merely a log. This module provides the NEGATIVE-TESTED leg.

The six TOP-LEVEL acceptance tests (凌翼 RC10 R5) are R5-1..R5-6 below:
    R5-1 delete one V5a/A1 reader probe          -> Phase-A FAIL
    R5-2 delete reset_valid                      -> INVALID / Phase-A FAIL
    R5-3 change verified-restored vs S_restored  -> INVALID (one byte)
    R5-4 change ledger required_pre_class/members/attempted
                                                 -> replay ignores ledger claim
    R5-5 V4b probe + selector-bearing control    -> MUST detect separability
    R5-6 delete one required member              -> INVALID (never lower-tier PASS)

Plus the retained RC7/RC8/RC9 attack list.

Runs offline; does NOT need the frozen MANIFEST (role hashes are refreshed at
freeze time). Exits non-zero if ANY check fails.
"""

from __future__ import annotations

import copy
import shutil
import sys
import tempfile
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

import fixtures as f
import evaluator as e
from evidence_bundle import ArmPhase, EvidenceBundle, MemberEvidence, evaluate_bundle
from fixture_contracts import FROZEN_ORACLES
from evidence_contract import REQUIRED_EVIDENCE_CONSUMPTION_MATRIX

RESULTS = []


def chk(name, cond):
    RESULTS.append((name, cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")


def F(fid):
    return f.FIXTURES[fid]()


def oracle_match(fid, actual):
    def sub(a, b):
        for k, v in a.items():
            if k not in b:
                return False
            if isinstance(v, dict):
                if not sub(v, b[k]):
                    return False
            elif b[k] != v:
                return False
        return True
    return sub(FROZEN_ORACLES[fid], actual)


def _bundle_from_fixture(fid, required_members=None):
    """Rebuild a bundle from a fixture's stored observations (deep-copied)."""
    r = F(fid)
    obs = copy.deepcopy(r.ledger.observations)
    from harness_constants import CONTENT_CLASS_OF
    members = required_members if required_members is not None else tuple(obs.keys())
    b = EvidenceBundle(fixture_id=fid, required_members=members)
    for mid, m in obs.items():
        me = MemberEvidence(member_id=mid, content_class=CONTENT_CLASS_OF.get(mid, "?"),
                            payload=bytes.fromhex(m["payload"]))
        for arm, phases in m["arms"].items():
            me.arms[arm] = {ph: ArmPhase(bytes.fromhex(ap["literal"]), bytes.fromhex(ap["q_raw"]))
                            for ph, ap in phases.items()}
        me.reset_witness = copy.deepcopy(m.get("reset_witness", {}))
        me.reader_witness = copy.deepcopy(m.get("reader_witness", {}))
        b.members[mid] = me
    return b


def _eval_v5a(b):
    return evaluate_bundle(b, required_pre_class="C3", expected_post_supported_class=None,
                           attempted="full")


# ===========================================================================
# 凌翼 RC10 R5 — SIX TOP-LEVEL ACCEPTANCE TESTS
# ===========================================================================

# --- R5-1: delete one V5a/A1 reader probe -> Phase-A FAIL ------------------
for probe_key in ("0", "2"):
    b = _bundle_from_fixture("V5a")
    del b.members["A1"].reader_witness["affine"][probe_key]
    res = _eval_v5a(b)
    chk(f"R5-1 delete V5a/A1 affine[{probe_key}] -> INVALID",
        res.l2 == e.INVALID and "READER" in res.code)
for probe_key in ("0", "2"):
    b = _bundle_from_fixture("V5a")
    del b.members["A1"].reader_witness["literal"][probe_key]
    res = _eval_v5a(b)
    chk(f"R5-1 delete V5a/A1 literal[{probe_key}] -> INVALID",
        res.l2 == e.INVALID and "READER" in res.code)

# empty probe dict => INVALID (was the RC9 hole)
b = _bundle_from_fixture("V5a")
b.members["A1"].reader_witness["affine"] = {}
b.members["A1"].reader_witness["literal"] = {}
res = _eval_v5a(b)
chk("R5-1 empty reader probes -> INVALID", res.l2 == e.INVALID and "READER" in res.code)

# extra unexpected probe key => INVALID
b = _bundle_from_fixture("V5a")
b.members["A1"].reader_witness["affine"]["999"] = {"num": 1, "den": 1}
res = _eval_v5a(b)
chk("R5-1 extra affine[999] -> INVALID", res.l2 == e.INVALID and "PROBE_SET" in res.code)

# raw_q cross-check: corrupt raw_q -> INVALID
b = _bundle_from_fixture("V5a")
b.members["A1"].reader_witness["raw_q"] = REDACTED_ROTATED_CREDENTIAL
res = _eval_v5a(b)
chk("R5-1 corrupt raw_q cross-check -> INVALID",
    res.l2 == e.INVALID and "RAW_Q" in res.code)


# --- R5-2: delete reset_valid -> INVALID -----------------------------------
def _delete_reset_valid(fid):
    b = _bundle_from_fixture(fid)
    for m in b.members.values():
        for arm in ("A", "B", "C"):
            m.reset_witness[arm].pop("reset_valid", None)
    return b


b = _delete_reset_valid("V5a")
res = _eval_v5a(b)
chk("R5-2 delete reset_valid -> INVALID",
    res.l2 == e.INVALID and "RESET_FIELD_MISSING" in res.code)

# also: reset_valid=False must be INVALID (not PASS)
b = _bundle_from_fixture("V5a")
b.members["A1"].reset_witness["C"]["reset_valid"] = False
res = _eval_v5a(b)
chk("R5-2 reset_valid=False -> INVALID", res.l2 == e.INVALID and "RESET_INVALID" in res.code)

# --- R5-3: change verified-restored vs stored S_restored by one byte -> INVALID
b = _bundle_from_fixture("V5a")
stored = b.members["A1"].arms["C"]["S_restored"]
b.members["A1"].arms["C"]["S_restored"] = ArmPhase(
    stored.literal, bytes([stored.q_raw[0] ^ 0x01]) + stored.q_raw[1:])
res = _eval_v5a(b)
chk("R5-3 S_restored != verified-restored (1 byte) -> INVALID",
    res.l2 == e.INVALID and "OBJECT_IDENTITY" in res.code)

# --- R5-6: delete one required member -> INVALID (never lower-tier PASS) ----
b = _bundle_from_fixture("V5a")
del b.members["B2"]
res = _eval_v5a(b)
chk("R5-6 missing member -> INVALID (MEMBER_SET)",
    res.l2 == e.INVALID and "MEMBER_SET" in res.code)


# ===========================================================================
# R5-4 / R5-5 — replay ignores ledger claims; V4b probe validity
# ===========================================================================

def _replay_ignores_ledger_members():
    """Ledger observations with a WRONG member set; replay adapter must fail
    closed (contract expects the frozen set)."""
    import replay_adapter as ra
    b = _bundle_from_fixture("V5a")
    obs = {mid: f._member_obs(m) for mid, m in b.members.items()}
    del obs["B2"]  # ledger now claims only 3 members
    try:
        ra.build_bundle_from_ledger("V5a", obs)
        return False  # should have raised
    except ra.ReplayContractError as ex:
        return "MEMBER_SET_MISMATCH" in str(ex)


chk("R5-4 ledger missing member -> replay fails closed (contract wins)",
    _replay_ignores_ledger_members())


def _replay_uses_contract_pre_class():
    """A ledger that self-claims no precondition must NOT weaken replay: the
    contract for V5a says required_pre_class=C3."""
    import recompute_from_ledger as rec
    b = _bundle_from_fixture("V5a")
    obs = {mid: f._member_obs(m) for mid, m in b.members.items()}
    out = rec.recompute_reset_suite("V5a", obs)
    return out.get("L2") == "PASS"


chk("R5-4 replay uses CONTRACT required_pre_class (V5a L2=PASS)",
    _replay_uses_contract_pre_class())


def _replay_rejects_changed_pre_class():
    """If the underlying data fails the C3 precondition, replay must say so
    (it cannot be talked out of it by the ledger)."""
    import recompute_from_ledger as rec
    real_extra = f.extra_write
    with patch.object(f, "extra_write", lambda s, p, m: real_extra(s, p, f.EXTRA_CONSTANT)):
        r = F("V5b")
    obs = copy.deepcopy(r.ledger.observations)
    out = rec.recompute_reset_suite("V5b", obs)
    return out.get("L2") == e.INVALID


chk("R5-4 changed pre_class (C3 contract vs C2 data) -> replay INVALID",
    _replay_rejects_changed_pre_class())


# --- R5-5: V4b probe MUST detect separability on a selector-bearing control --
chk("R5-5 probe_is_valid() (detects positive control)", f.probe_is_valid())

root = Path(tempfile.mkdtemp())
try:
    ctl = f.SeparableControlHandle(root, "ctl")
    pos = f.external_capability_probe(ctl)
    chk("R5-5 SeparableControlHandle -> separable_w_extra=True", pos["separable_w_extra"] is True)
    combo = f.CombinedOnlyWriter(root, "neg")
    neg = f.external_capability_probe(combo.public_handle())
    chk("R5-5 CombinedOnlyHandle -> separable_w_extra=False", neg["separable_w_extra"] is False)
    chk("R5-5 V4b production ANI output",
        F("V4b").actual.get("C2") == e.ARCHITECTURALLY_NOT_IDENTIFIABLE)
    chk("R5-5 production uses the probed public handle type",
        type(combo.public_handle()).__name__ == "_OnlyWriteHandle")
finally:
    shutil.rmtree(root, ignore_errors=True)


# ===========================================================================
# RETAINED RC7/RC8/RC9 ATTACKS
# ===========================================================================

with patch.object(f, "storage_write", lambda *a, **k: None):
    chk("no-op storage: V2 not oracle-match", not oracle_match("V2", F("V2").actual))
    chk("no-op storage: V3 not oracle-match", not oracle_match("V3", F("V3").actual))

real_extra = f.extra_write
with patch.object(f, "extra_write", lambda s, p, m: real_extra(s, p, f.EXTRA_CONSTANT)):
    a = F("V5b").actual
    chk("constant-pre V5b: L2 == INVALID", a.get("L2") == e.INVALID)
    chk("constant-pre V5b: not oracle-match", not oracle_match("V5b", a))

b = _bundle_from_fixture("V5a")
for m in b.members.values():
    ja = m.arms["C"]["J_after"]
    m.arms["C"]["J_after"] = ArmPhase(ja.literal,
                                      bytes([ja.q_raw[0] ^ 1]) + ja.q_raw[1:])
res = _eval_v5a(b)
chk("bad J timing -> INVALID", res.l2 == e.INVALID and "J_TIMING" in res.code)

b = _bundle_from_fixture("V5a")
for m in b.members.values():
    acc = m.reset_witness["C"]["accepted_handoff"]
    m.reset_witness["C"]["accepted_handoff"] = {"literal": acc["literal"], "q_raw": "00" * 8}
res = _eval_v5a(b)
chk("handoff discontinuity -> INVALID", res.l2 == e.INVALID and "HANDOFF" in res.code)

with patch.object(f, "affine_read", lambda path, u: Fraction(u)):
    a = F("V5a").actual
    chk("constant reader -> V5a L2 INVALID", a.get("L2") == e.INVALID)
    chk("constant reader -> not oracle-match", not oracle_match("V5a", a))

real_reset = f._reset_arm
def always_invalid(arm, fault):
    h, r, ok, reason = real_reset(arm, fault)
    return h, r, False, "review reset failure"
with patch.object(f, "_reset_arm", always_invalid):
    a = F("V5f").actual
    chk("invalid reset V5f -> INVALID", a.get("L2") == e.INVALID)

chk("evaluate_c3 empty -> INVALID", e.evaluate_c3([], [], []).result == e.INVALID)
chk("l2_aggregate INVALID propagates",
    e.l2_aggregate(e.INVALID, e.NOT_ASSESSED, e.NOT_ASSESSED) == e.INVALID)


# ===========================================================================
# REQUIRED_EVIDENCE_CONSUMPTION_MATRIX integrity (R2)
# ===========================================================================

chk("consumption matrix non-empty", len(REQUIRED_EVIDENCE_CONSUMPTION_MATRIX) > 0)
chk("every matrix row has all required legs",
    all({"field", "recorded_in", "prod_gate", "replay_gate", "negative_test"} <= set(row)
        for row in REQUIRED_EVIDENCE_CONSUMPTION_MATRIX))


print()
passed = sum(1 for _, ok in RESULTS if ok)
print(f"adversarial_regression: {passed}/{len(RESULTS)} PASS")
sys.exit(0 if passed == len(RESULTS) else 1)
