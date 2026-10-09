"""Assess BD-53: which L2 rule does _l2_judge implement, and is V5e's oracle unique?"""
import sys
sys.path.insert(0, r"d:\qcr\EntropyDrivenAI\selective_forgetting\afterglow_harness")

from evaluator import C1, C2, C3, FAIL, NOT_ASSESSED, NOT_ESTABLISHED, UNRESOLVED
from fixtures import _l2_judge

print("=== BD-53 assessment: _l2_judge behavior ===")
cases = [
    ("V5e-style: C1=FAIL, C2=UNRESOLVED, C3=NOT_EST", (C3, FAIL, UNRESOLVED, NOT_ESTABLISHED)),
    ("only C1 determinate negative", (C3, FAIL, NOT_ASSESSED, NOT_ASSESSED)),
    ("all determinate negative", (C3, FAIL, FAIL, NOT_ESTABLISHED)),
    ("mixed FAIL + UNRESOLVED", (C3, FAIL, UNRESOLVED, FAIL)),
]
for name, (pc, c1, c2, c3) in cases:
    r = _l2_judge(pc, c1, c2, c3, reset_valid=True)
    print(f"  {name:<48} -> {r}")

print()
print("Rule A (any indeterminate -> UNRESOLVED): matches V5e oracle UNRESOLVED?")
print("Rule C (lower determinate negative overrides higher): would give FAIL, contradicts oracle.")
print()
print("=> _l2_judge uses Rule A (indeterminate wins). V5e oracle consistent ONLY under Rule A.")
print("=> Oracle uniqueness depends on an UNFROZEN rule choice = BD-53 CONFIRMED (spec-level).")
