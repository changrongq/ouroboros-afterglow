"""Verify the Zhiwei counterexamples are now REJECTED by the new fixtures."""
import sys
from unittest.mock import patch

sys.path.insert(0, r"d:\qcr\EntropyDrivenAI\selective_forgetting\afterglow_harness")
import fixtures as f

ok = True


def chk(name, cond):
    global ok
    ok = ok and cond
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")


# CE1: no-op storage_write => V2/V3 must NOT claim L1 PASS
with patch.object(f, "storage_write", lambda *a, **kw: None):
    v2 = f.fixture_V2()
    v3 = f.fixture_V3()
    print("  V2 actual:", v2.actual)
    print("  V3 actual:", v3.actual)
    chk("no-op storage => V2 L1 != PASS", v2.actual["L1"] != "PASS" or v2.actual["PRE_RESET_CHANGE_CLASS"] != "C2")
    chk("no-op storage => V3 L1 != PASS", v3.actual["L1"] != "PASS" or v3.actual["PRE_RESET_CHANGE_CLASS"] != "C3")

# CE2: wrong J => post class must not match the canned oracle
real_j = f.apply_j
for tag, fn, mode in [("V5b", f.fixture_V5b, "ERASE_EFFECT"),
                      ("V5d", f.fixture_V5d, "COLLAPSE_SIGN"),
                      ("V5e", f.fixture_V5e, "COLLAPSE_SIGN")]:
    with patch.object(f, "apply_j", lambda state, m, _m=mode: real_j(state, _m)):
        r = fn()
        print(f"  {tag} under wrong J: oracle_match={r.oracle_match} actual={r.actual}")
        chk(f"wrong-J {tag} => oracle mismatch", not r.oracle_match)

# CE6: empty C3 and INVALID L2
import evaluator as e
r = e.evaluate_c3([], [], [])
print("  evaluate_c3([],[],[]) ->", r.result)
chk("empty C3 => INVALID", r.result == "INVALID")
print("  l2_aggregate(INVALID,...) ->", e.l2_aggregate(e.INVALID, e.NOT_ASSESSED, e.NOT_ASSESSED))
chk("INVALID L2 propagates", e.l2_aggregate(e.INVALID, e.NOT_ASSESSED, e.NOT_ASSESSED) == "INVALID")

print()
print("COUNTEREXAMPLE REGRESSION =", "PASS" if ok else "FAIL")
sys.exit(0 if ok else 1)
