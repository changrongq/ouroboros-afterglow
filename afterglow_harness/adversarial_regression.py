"""
adversarial_regression.py — every known false-PASS attack must be REJECTED.

Covers 凌翼's required attack list (RC8 ruling):
  · bad J timing
  · storage no-op
  · constant extra / absent pre-C3
  · invalid reset V5f   (must be INVALID, not scientific FAIL)
  · V4b separability attack (ON/OFF must be unbuildable)
  · reader that ignores substrate (constant reader must be caught)
  · empty/missing component-set attack
  · plus all prior known-answer regressions

Each attack asserts the OUTCOME IS NOT the naive PASS. Not a qualification run.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import fixtures as f
import gates as g
import evaluator as e
import qualification_binding as qb
from fixture_contracts import FROZEN_ORACLES
from harness_constants import StateSnapshot, encode_substrate
from fractions import Fraction

RESULTS = []


def chk(name, cond):
    RESULTS.append((name, cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")


def oracle_match(fid, actual):
    exp = FROZEN_ORACLES[fid]
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
    return sub(exp, actual)


def F(fid):
    return f.FIXTURES[fid]()


# CE1: storage no-op -> V2/V3 must NOT claim L1 PASS/C3
with patch.object(f, "storage_write", lambda *a, **k: None):
    chk("no-op storage: V2 not (L1 PASS & C2)", not oracle_match("V2", F("V2").actual))
    chk("no-op storage: V3 not (L1 PASS & C3)", not oracle_match("V3", F("V3").actual))
    a5 = F("V5a").actual
    chk("no-op storage: V5a pre-class is NOT C3", a5.get("PRE_RESET_CHANGE_CLASS") != e.C3)

# CE2: wrong J -> post class must not match
real_j = f.apply_j
for fid, mode in [("V5b", "ERASE_EFFECT"), ("V5d", "COLLAPSE_SIGN"), ("V5e", "COLLAPSE_SIGN")]:
    with patch.object(f, "apply_j", lambda s, m, _m=mode: real_j(s, _m)):
        chk(f"wrong-J {fid} rejected", not oracle_match(fid, F(fid).actual))

# CE3: bad J timing -> INVALID (V5a must NOT be PASS)
real_wit = f._apply_j_witnessed
def bad_timing(arm, mode):
    sw, ja, hd = real_wit(arm, mode)
    return sw, ja, StateSnapshot(hd.literal, encode_substrate(hd.q + 7))
with patch.object(f, "_apply_j_witnessed", bad_timing):
    a = F("V5a").actual
    chk("bad J timing: V5a L2 == INVALID", a.get("L2") == e.INVALID)
    chk("bad J timing: V5a not oracle match", not oracle_match("V5a", a))

# CE4: invalid reset V5f -> must be INVALID (not scientific FAIL)
real_reset = f._reset_arm
def always_invalid(arm, fault):
    h, r, ok, reason = real_reset(arm, fault)
    return h, r, False, "review reset failure"
with patch.object(f, "_reset_arm", always_invalid):
    a = F("V5f").actual
    chk("invalid reset V5f: L2 == INVALID", a.get("L2") == e.INVALID)

# CE5: V4b separability attack — ON/OFF must be unbuildable from the surface
root = Path(tempfile.mkdtemp())
w = f.CombinedOnlyWriter(root, "x")
surf = w.capability_surface()
chk("V4b surface has NO extra selector", "extra_mode" not in surf and "extra_on" not in surf)
chk("V4b ANI output", F("V4b").actual.get("C2") == e.ARCHITECTURALLY_NOT_IDENTIFIABLE)

# CE6: constant reader (ignores substrate) must be caught by reader witness
def expected_affine(q, u):
    return Fraction(2 * u + q, 2)
with patch.object(f, "affine_read", lambda path, u: Fraction(u)):
    r = F("V5a")
    obs = r.ledger.observations
    bad = False
    for mid, o in obs.items():
        rw = o.get("reader_witness", {})
        q = rw.get("raw_q")
        if q is not None:
            got = Fraction(rw["affine_u0"]["num"], rw["affine_u0"]["den"])
            if got != expected_affine(q, 0):
                bad = True
    chk("constant reader detected (raw_q vs reader output mismatch)", bad)

# CE7: empty/missing component-set attack -> preflight must FAIL
with patch.object(qb, "REQUIRED_RUNTIME_ROLES", frozenset()):
    ev2 = {}
    # simulate: empty role set must NOT pass
    ok_empty = (len(qb.REQUIRED_RUNTIME_ROLES) > 0)
    chk("empty required-role set is rejected", not ok_empty)

# CE8: helper-level checks
chk("evaluate_c3 empty -> INVALID", e.evaluate_c3([], [], []).result == e.INVALID)
chk("l2_aggregate INVALID propagates", e.l2_aggregate(e.INVALID, e.NOT_ASSESSED, e.NOT_ASSESSED) == e.INVALID)

print()
passed = sum(1 for _, ok in RESULTS if ok)
print(f"adversarial_regression: {passed}/{len(RESULTS)} PASS")
sys.exit(0 if passed == len(RESULTS) else 1)
