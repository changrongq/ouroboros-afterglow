"""
Qualifying known-answer suite driver (PHASE A — HARNESS_VALIDATION_EXECUTION).

Order fixed by SPEC §16.2.2:
  1. MANIFEST is already frozen; capture its frozen hash + the SPEC hash
     BEFORE the first fixture executes.
  2. Run all 13 fixtures on the same production evaluator/code path.
  3. Compare each result against its frozen unique oracle.

If the frozen MANIFEST hash cannot be captured (manifest missing / changed vs
the detached record), the run is NON-QUALIFYING and the driver refuses to stamp
QUALIFYING.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from fixtures import SCIENTIFIC_CLAIM_ELIGIBILITY, run_all
from harness_constants import REFERENCE_HARNESS_SPEC_HASH, PARENT_PREREG_SHA256
from manifest_bind import compute_all, manifest_self_hash

REPORTS = Path(__file__).resolve().parent.parent / "reports"
MANIFEST_PATH = REPORTS / "AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md"
DETACHED_PATH = REPORTS / "MANIFEST_v0.1_HASH.txt"
ARTIFACTS = Path(__file__).resolve().parent.parent / "afterglow_harness_artifacts"
RAW_PATH = ARTIFACTS / "RC6_qualifying_run_raw.json"
LEDGER_DIR = ARTIFACTS / "RC6_ledgers"


def capture_frozen_binding() -> tuple[dict, bool]:
    """Capture the already-frozen binding hashes BEFORE running fixtures.

    Checks TWO things, both required for a qualifying run:
      (a) the detached record matches the current MANIFEST bytes; and
      (b) EVERY current execution-critical component hash is present in the
          frozen MANIFEST (no component drift). (b) is essential: a run whose
          components moved on after freeze is binding-INVALID even if the
          MANIFEST file itself is unchanged.
    """
    if not MANIFEST_PATH.exists():
        return {"error": "manifest missing"}, False
    self_h = manifest_self_hash(MANIFEST_PATH)
    if not DETACHED_PATH.exists():
        return {"error": "detached record missing"}, False
    detached = DETACHED_PATH.read_text(encoding="utf-8")
    detached_match = self_h["sha256"] in detached

    man_text = MANIFEST_PATH.read_text(encoding="utf-8")
    derived = compute_all()
    drift = {
        info["file"]: (info["sha256"] in man_text)
        for info in derived["components"].values()
    }
    no_drift = all(drift.values())

    return {
        "SPEC_HASH": REFERENCE_HARNESS_SPEC_HASH,
        "MANIFEST_HASH": self_h["sha256"],
        "MANIFEST_BYTES": self_h["bytes"],
        "PREREG_SHA256": PARENT_PREREG_SHA256,
        "detached_match": detached_match,
        "component_binding_no_drift": no_drift,
        "component_drift": {k: v for k, v in drift.items() if not v},
    }, (detached_match and no_drift)


def main() -> int:
    print("=" * 72)
    print("PHASE A — known-answer suite")
    print(f"SCIENTIFIC_CLAIM_ELIGIBILITY = {SCIENTIFIC_CLAIM_ELIGIBILITY}")
    print("=" * 72)

    binding, frozen_ok = capture_frozen_binding()
    print("\n[captured BEFORE first fixture — SPEC §16.2.2]")
    for k, v in binding.items():
        print(f"    {k} = {v}")
    if not frozen_ok:
        print("\nBINDING NOT FROZEN / MISMATCH -> NON_QUALIFYING DEVELOPMENT VALIDATION")
        print("SCIENTIFIC_EXECUTION MAY NOT START")
    print()

    # ---- now run fixtures ----
    results = run_all()
    all_ok = True
    ledgers = []
    for r in results:
        ok = r.oracle_match
        all_ok &= ok
        print(f"[{ 'ORACLE MATCH' if ok else 'ORACLE MISMATCH' }] {r.fixture_id}")
        if not ok:
            print(f"    expected = {r.expected}")
            print(f"    actual   = {r.actual}")
        ledgers.append({
            "fixture_id": r.fixture_id,
            "expected": r.expected,
            "actual": r.actual,
            "oracle_match": ok,
            "ledger": dataclasses.asdict(r.ledger),
        })

    print("\n" + "=" * 72)
    print(f"fixtures: {sum(1 for r in results if r.oracle_match)}/{len(results)} oracle match")
    status = "PASS" if (all_ok and frozen_ok) else "FAIL"
    print(f"KNOWN_ANSWER_SUITE = {status}")
    if frozen_ok:
        print(f"  bound to SPEC_HASH     = {binding['SPEC_HASH']}")
        print(f"  bound to MANIFEST_HASH = {binding['MANIFEST_HASH']}")
        print("  => QUALIFYING RUN")
    else:
        print("  => NON_QUALIFYING DEVELOPMENT VALIDATION")

    # ---- emit machine-readable artifacts (for independent re-verification) ----
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    out = {
        "suite": "KNOWN_ANSWER_SUITE",
        "phase": "PHASE_A_HARNESS_VALIDATION_EXECUTION",
        "scientific_claim_eligibility": SCIENTIFIC_CLAIM_ELIGIBILITY,
        "binding_captured_before_first_fixture": binding,
        "frozen_ok": frozen_ok,
        "fixtures_total": len(results),
        "fixtures_oracle_match": sum(1 for r in results if r.oracle_match),
        "known_answer_suite": status,
        "per_fixture": ledgers,
    }
    RAW_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    # per-fixture ledger files
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    for item in ledgers:
        p = LEDGER_DIR / f"{item['fixture_id']}.json"
        p.write_text(json.dumps(item, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  raw result     -> {RAW_PATH}")
    print(f"  ledgers (13)   -> {LEDGER_DIR}")
    print("=" * 72)
    return 0 if (all_ok and frozen_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
