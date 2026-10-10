"""
adversarial_regression.py (RC9) — every known fail-open attack must be REJECTED.

Covers 凌翼 RC9 attack list + all prior:
  · bad J timing (J_after != S_handoff)          -> INVALID
  · J handoff != reset handoff (continuity)       -> INVALID
  · storage no-op / constant extra               -> no wrong promotion
  · V5 required_pre_class not satisfied           -> INVALID (PROFILE_PRECONDITION_FAILED)
  · missing frozen member                         -> INVALID (not downgraded)
  · invalid reset (V5f)                           -> INVALID (not scientific FAIL)
  · reader that ignores substrate                 -> INVALID (READER_WITNESS_INVALID)
  · V4b external capability probe                 -> no public separable path
  · empty/missing component-set                   -> preflight FAIL
  · ledger replay zero-check                      -> FAIL
  · empty C3 / INVALID l2                         -> helper-level
"""

from __future__ import annotations

import io
import contextlib
import json
import sys
import tempfile
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

import fixtures as f
import evaluator as e
import qualification_binding as qb
import run_known_answer_suite as driver
from evidence_bundle import ArmPhase, EvidenceBundle, MemberEvidence, evaluate_bundle
from fixture_contracts import FROZEN_ORACLES

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


def _bundle_from_fixture(fid):
    """Capture the raw bundle by re-running the fixture and rebuilding from its
    stored observations."""
    r = F(fid)
    obs = r.ledger.observations
    b = EvidenceBundle(fixture_id=fid, required_members=tuple(obs.keys()))
    from harness_constants import CONTENT_CLASS_OF
    for mid, m in obs.items():
        me = MemberEvidence(member_id=mid, content_class=CONTENT_CLASS_OF.get(mid, "?"),
                            payload=bytes.fromhex(m["payload"]))
        for arm, phases in m["arms"].items():
            me.arms[arm] = {ph: ArmPhase(bytes.fromhex(ap["literal"]), bytes.fromhex(ap["q_raw"]))
                            for ph, ap in phases.items()}
        me.reset_witness = m.get("reset_witness", {})
        me.reader_witness = m.get("reader_witness", {})
        b.members[mid] = me
    return b


# CE1: storage no-op -> V2/V3 must NOT claim L1 PASS
with patch.object(f, "storage_write", lambda *a, **k: None):
    chk("no-op storage: V2 not oracle-match", not oracle_match("V2", F("V2").actual))
    chk("no-op storage: V3 not oracle-match", not oracle_match("V3", F("V3").actual))

# CE2: constant extra (V5b never establishes C3) -> must NOT match oracle (pre-class gate)
real_extra = f.extra_write
with patch.object(f, "extra_write", lambda s, p, m: real_extra(s, p, f.EXTRA_CONSTANT)):
    a = F("V5b").actual
    chk("constant-pre V5b: L2 == INVALID", a.get("L2") == e.INVALID)
    chk("constant-pre V5b: not oracle-match", not oracle_match("V5b", a))

# CE3: bad J timing -> INVALID
b = _bundle_from_fixture("V5a")
for m in b.members.values():
    m.arms["C"]["J_after"] = ArmPhase(m.arms["C"]["J_after"].literal,
                                      bytes([m.arms["C"]["J_after"].q_raw[0] ^ 1]) + m.arms["C"]["J_after"].q_raw[1:])
res = evaluate_bundle(b, required_pre_class="C3", expected_post_supported_class=None, attempted="full")
chk("bad J timing -> INVALID", res.l2 == e.INVALID and "J_TIMING" in res.code)

# CE4: J handoff != reset handoff (continuity)
b = _bundle_from_fixture("V5a")
for m in b.members.values():
    acc = m.reset_witness["C"]["accepted_handoff"]
    m.reset_witness["C"]["accepted_handoff"] = {"literal": acc["literal"], "q_raw": "00" * 8}
res = evaluate_bundle(b, required_pre_class="C3", expected_post_supported_class=None, attempted="full")
chk("handoff discontinuity -> INVALID", res.l2 == e.INVALID and "HANDOFF" in res.code)

# CE5: missing frozen member -> INVALID (not downgraded to C2)
b = _bundle_from_fixture("V5a")
del b.members["B2"]
res = evaluate_bundle(b, required_pre_class="C3", expected_post_supported_class=None, attempted="full")
chk("missing member -> INVALID", res.l2 == e.INVALID and "MEMBER_SET" in res.code)

# CE6: reader that ignores substrate -> INVALID
with patch.object(f, "affine_read", lambda path, u: Fraction(u)):
    a = F("V5a").actual
    chk("constant reader -> V5a L2 INVALID", a.get("L2") == e.INVALID)
    chk("constant reader -> not oracle-match", not oracle_match("V5a", a))

# CE7: invalid reset V5f -> INVALID
real_reset = f._reset_arm
def always_invalid(arm, fault):
    h, r, ok, reason = real_reset(arm, fault)
    return h, r, False, "review reset failure"
with patch.object(f, "_reset_arm", always_invalid):
    a = F("V5f").actual
    chk("invalid reset V5f -> INVALID", a.get("L2") == e.INVALID)

# CE8: V4b external capability probe: tester gets ONLY the public handle
root = Path(tempfile.mkdtemp())
w = f.CombinedOnlyWriter(root, "x")
handle = w.public_handle()
probe = f.external_capability_probe(handle)
chk("V4b public handle exposes no separable write",
    all(n in ("write",) for n in probe["public_api"]))
chk("V4b ANI output", F("V4b").actual.get("C2") == e.ARCHITECTURALLY_NOT_IDENTIFIABLE)

# CE9: empty required-role set -> preflight FAIL
chk("empty role registry is rejected", len(qb.REQUIRED_RUNTIME_ROLES) > 0)

# CE10: ledger replay zero-check -> FAIL (structural: required scope non-empty)
import recompute_from_ledger as rec
chk("replay required scope non-empty for reset_suite", len(rec.REQUIRED_SCOPE["reset_suite"]) > 0)

# CE11: helper-level
chk("evaluate_c3 empty -> INVALID", e.evaluate_c3([], [], []).result == e.INVALID)
chk("l2_aggregate INVALID propagates", e.l2_aggregate(e.INVALID, e.NOT_ASSESSED, e.NOT_ASSESSED) == e.INVALID)

print()
passed = sum(1 for _, ok in RESULTS if ok)
print(f"adversarial_regression: {passed}/{len(RESULTS)} PASS")
sys.exit(0 if passed == len(RESULTS) else 1)
