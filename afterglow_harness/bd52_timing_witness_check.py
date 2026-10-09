"""BD-52 negative witness: prove the J-timing guard actually REJECTS a violation.

This is NOT a fixture. It demonstrates that if J's post-digest does not equal
the handoff digest (i.e. J did not complete before handoff), the guard raises
and the affected check is INVALID — i.e. a legal J and an injected post-handoff
fault are machine-distinguishable.
"""
from __future__ import annotations

from evaluator import JTimingWitness, assert_j_timing
from harness_constants import HarnessError


def main() -> int:
    ok = True

    # (1) legal: J_after == S_handoff
    good = JTimingWitness("sw", "ja", "ja")
    try:
        assert_j_timing(good)
        print("[PASS] legal J (J_after == S_handoff) accepted")
    except HarnessError:
        print("[FAIL] legal J wrongly rejected")
        ok = False

    # (2) violation: J applied AFTER handoff -> J_after != S_handoff
    bad = JTimingWitness("sw", "ja2", "ja1")
    try:
        assert_j_timing(bad)
        print("[FAIL] timing violation NOT rejected (BD-52 hole!)")
        ok = False
    except HarnessError as e:
        print(f"[PASS] timing violation rejected: {e}")

    # (3) a post-handoff injected fault has J_after != handoff too -> INVALID
    injected = JTimingWitness("sw", "pre_handoff", "handoff")
    try:
        assert_j_timing(injected)
        print("[FAIL] injected post-handoff fault NOT rejected")
        ok = False
    except HarnessError:
        print("[PASS] injected post-handoff fault rejected (same path as illegal J)")

    print()
    print("BD-52 NEGATIVE WITNESS =", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
