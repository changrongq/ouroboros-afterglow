"""Reproduce 知微's key RC7-review counterexamples in-process (no subprocesses)."""
import sys, dataclasses, json
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, r"d:\qcr\ouroboros-afterglow\afterglow_harness")
import fixtures as f
import manifest_bind as mb
from harness_constants import StateSnapshot, encode_substrate


def show(name, r):
    print(f"\n[{name}] oracle_match={r.oracle_match}")
    print("  actual  :", json.dumps(r.actual, ensure_ascii=False, default=str))
    print("  expected:", json.dumps(r.expected, ensure_ascii=False, default=str))


print("=" * 70)
print("§2  J-timing invalid must be rejected, but is it?")
real_wit = f._apply_j_witnessed
def bad_timing(arm, mode):
    sw, ja, hd = real_wit(arm, mode)
    return sw, ja, StateSnapshot(hd.literal, encode_substrate(hd.q + 7))
with patch.object(f, "_apply_j_witnessed", bad_timing):
    rs = f.run_all()
print("  invalid J timing => matches:", sum(r.oracle_match for r in rs), "/", len(rs))
v5a = next(r for r in rs if r.fixture_id == "V5a")
print("  V5a actual.j_timing_ok =", v5a.actual.get("j_timing_ok"), " L2 =", v5a.actual.get("L2"))

print("\n" + "=" * 70)
print("§2b executed oracle vs frozen oracle")
for r in f.run_all():
    miss = mb.FIXTURE_BUNDLES.get(r.fixture_id, {}).get("oracle")
    if miss != r.expected:
        print(f"  {r.fixture_id}: frozen={miss} executed={r.expected}")

print("\n" + "=" * 70)
print("§3a V5a under no-op storage")
with patch.object(f, "storage_write", lambda *a, **k: None):
    show("V5a noop-storage", f.fixture_V5a())

print("\n" + "=" * 70)
print("§3b V5b under constant extra")
real_extra = f.extra_write
with patch.object(f, "extra_write", lambda s, p, m: real_extra(s, p, f.EXTRA_CONSTANT)):
    show("V5b constant-pre", f.fixture_V5b())

print("\n" + "=" * 70)
print("§4 normal V5a ledger cross-arm check")
n = f.fixture_V5a()
for mid, x in n.ledger.per_member.items():
    print(f"  {mid}: j_after==handoff? {x['j_after_digest']==x['handoff_digest']}  reported j_timing_valid={x['j_timing_valid']}")

print("\n" + "=" * 70)
print("§6 V5f reset-invalid => L2?")
calls = []
def always_invalid(arm, fault):
    h, r, ok, reason = f._reset_arm  # placeholder
real_reset = f._reset_arm
def ai(arm, fault):
    h, r, ok, reason = real_reset(arm, fault)
    return h, r, False, "review reset failure"
with patch.object(f, "_reset_arm", ai):
    show("V5f reset-invalid", f.fixture_V5f())

print("\n" + "=" * 70)
print("§6b V4b wrapper separable via param?")
import tempfile
root = Path(tempfile.mkdtemp())
w_off = f.CombinedStorageWrapper(root, "off")
w_on = f.CombinedStorageWrapper(root, "on")
w_off.combined_write(f.EPISODE_PAYLOADS["A1"], f.STORE_FULL, f.EXTRA_OFF)
w_on.combined_write(f.EPISODE_PAYLOADS["A1"], f.STORE_FULL, f.EXTRA_CONTENT)
print("  off q =", w_off.arm.snapshot().q, " on q =", w_on.arm.snapshot().q,
      " same literal =", w_off.arm.snapshot().literal == w_on.arm.snapshot().literal)
print("  => ON/OFF IS selectable via the single public entry's extra_mode param")

print("\n" + "=" * 70)
print("§7 constant reader undetected?")
from fractions import Fraction
with patch.object(f, "affine_read", lambda path, u: Fraction(u)):
    rs = f.run_all()
print("  constant reader => matches:", sum(r.oracle_match for r in rs), "/", len(rs))
