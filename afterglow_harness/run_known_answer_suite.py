"""
Qualifying known-answer suite driver (PHASE A — HARNESS_VALIDATION_EXECUTION).

Order fixed by SPEC §16.2.2:
  1. Full qualification PREFLIGHT: capture the frozen MANIFEST hash AND check
     every bound object (9 components + 2 drivers + the ACTUAL SPEC & prereg
     files + the required fixture-id set) BEFORE the first fixture runs.
  2. Run all 13 fixtures on the same production evaluator/code path.
  3. Compare each result against its frozen unique oracle.

If ANY preflight item fails, the run is NON-QUALIFYING and this driver refuses
to stamp QUALIFYING. The completeness gate lives HERE (not in an optional
separate command), per the Zhiwei §6 requirement.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path

from fixtures import REQUIRED_FIXTURE_IDS, SCIENTIFIC_CLAIM_ELIGIBILITY, run_all
from manifest_bind import compute_all, hash_file, manifest_self_hash

ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = ROOT / "reports" / "AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md"
DETACHED_PATH = ROOT / "reports" / "MANIFEST_v0.1_HASH.txt"


def _find(*candidates: Path) -> Path | None:
    for c in candidates:
        if c.exists():
            return c
    return None


# SPEC/prereg may live in the repo layout (spec/, prereg/) or the working
# layout (reports/). Resolve against the first that exists.
SPEC_PATH = _find(
    ROOT / "spec" / "AFTERGLOW_IMPLEMENTATION_BINDING_v0.1.md",
    ROOT / "reports" / "AFTERGLOW IMPLEMENTATION BINDING v0.1.md",
)
PREREG_PATH = _find(
    ROOT / "prereg" / "AFTERGLOW_MVP_PREREGISTRATION_v0.1.md",
    ROOT / "prereg" / "AFTERGLOW_MVP_PREREGISTRATION_v0.1_FREEZE_CANDIDATE.md",
    ROOT / "reports" / "AFTERGLOW_MVP_PREREGISTRATION_v0.1_FREEZE_CANDIDATE.md",
    ROOT / "reports" / "AFTERGLOW MVP PREREGISTRATION v0.1.md",
)
HARNESS_DIR = Path(__file__).resolve().parent

ARTIFACTS = ROOT / "afterglow_harness_artifacts"
RAW_PATH = ARTIFACTS / "RC7_qualifying_run_raw.json"
LEDGER_DIR = ARTIFACTS / "RC7_ledgers"

# Execution-critical, hash-bound drivers (must be present in the MANIFEST).
BOUND_DRIVERS = ("run_known_answer_suite.py", "verify_manifest_binding.py")


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def capture_frozen_binding() -> tuple[dict, bool]:
    """Full qualification preflight. Returns (evidence, ok).

    ok is True ONLY if ALL of:
      (a) detached record matches the current MANIFEST bytes;
      (b) every bound component hash is present in the MANIFEST;
      (c) every bound DRIVER hash is present in the MANIFEST;
      (d) the ACTUAL SPEC file hash matches the frozen SPEC constant;
      (e) the ACTUAL prereg file hash matches the frozen prereg constant;
      (f) the required fixture-id set is exactly what the suite will run.
    """
    ev: dict = {}
    if not MANIFEST_PATH.exists():
        return {"error": "manifest missing"}, False
    self_h = manifest_self_hash(MANIFEST_PATH)
    ev["MANIFEST_HASH"] = self_h["sha256"]
    ev["MANIFEST_BYTES"] = self_h["bytes"]

    detached_match = False
    if DETACHED_PATH.exists():
        detached = DETACHED_PATH.read_text(encoding="utf-8")
        detached_match = self_h["sha256"] in detached
    ev["detached_match"] = detached_match

    man_text = MANIFEST_PATH.read_text(encoding="utf-8")
    derived = compute_all()

    comp = {i["file"]: (i["sha256"] in man_text) for i in derived["components"].values()}
    ev["component_binding_no_drift"] = all(comp.values())
    ev["component_drift"] = {k: v for k, v in comp.items() if not v}

    drivers = {name: (hash_file(HARNESS_DIR / name) in man_text) for name in BOUND_DRIVERS}
    ev["driver_binding_no_drift"] = all(drivers.values())
    ev["driver_drift"] = {k: v for k, v in drivers.items() if not v}

    # (d)(e) actual file hashes vs the frozen constants in the MANIFEST text
    spec_actual = _sha256_file(SPEC_PATH) if (SPEC_PATH and SPEC_PATH.exists()) else None
    prereg_actual = _sha256_file(PREREG_PATH) if (PREREG_PATH and PREREG_PATH.exists()) else None
    ev["SPEC_FILE_HASH"] = spec_actual
    ev["PREREG_FILE_HASH"] = prereg_actual
    ev["spec_file_matches_frozen"] = bool(spec_actual and spec_actual in man_text)
    ev["prereg_file_matches_frozen"] = bool(prereg_actual and prereg_actual in man_text)

    # (f) fixture-id set
    from fixtures import FIXTURES

    run_ids = set(FIXTURES.keys())
    ev["fixture_set_ok"] = run_ids == set(REQUIRED_FIXTURE_IDS)
    ev["fixture_set"] = sorted(run_ids)

    ok = all([
        detached_match,
        ev["component_binding_no_drift"],
        ev["driver_binding_no_drift"],
        ev["spec_file_matches_frozen"],
        ev["prereg_file_matches_frozen"],
        ev["fixture_set_ok"],
    ])
    return ev, ok


def main() -> int:
    print("=" * 72)
    print("PHASE A — known-answer suite")
    print(f"SCIENTIFIC_CLAIM_ELIGIBILITY = {SCIENTIFIC_CLAIM_ELIGIBILITY}")
    print("=" * 72)

    binding, frozen_ok = capture_frozen_binding()
    print("\n[qualification preflight — captured BEFORE first fixture, SPEC §16.2.2]")
    for k, v in binding.items():
        print(f"    {k} = {v}")
    if not frozen_ok:
        print("\nPREFLIGHT FAILED -> NON_QUALIFYING DEVELOPMENT VALIDATION")
        print("SCIENTIFIC_EXECUTION MAY NOT START")
    print()

    # ---- run fixtures ----
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

    # completeness: every required id ran exactly once
    ran_ids = [x["fixture_id"] for x in ledgers]
    completeness_ok = (len(ran_ids) == len(set(ran_ids)) == len(REQUIRED_FIXTURE_IDS)
                       and set(ran_ids) == set(REQUIRED_FIXTURE_IDS))

    print("\n" + "=" * 72)
    print(f"fixtures: {sum(1 for r in results if r.oracle_match)}/{len(results)} oracle match")
    status = "PASS" if (all_ok and frozen_ok and completeness_ok) else "FAIL"
    print(f"KNOWN_ANSWER_SUITE = {status}")
    if frozen_ok and completeness_ok:
        print(f"  bound to SPEC_HASH     = {binding['SPEC_FILE_HASH']}")
        print(f"  bound to MANIFEST_HASH = {binding['MANIFEST_HASH']}")
        print("  => QUALIFYING RUN")
    else:
        print("  => NON_QUALIFYING DEVELOPMENT VALIDATION")

    # ---- emit machine-readable artifacts ----
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    out = {
        "suite": "KNOWN_ANSWER_SUITE",
        "phase": "PHASE_A_HARNESS_VALIDATION_EXECUTION",
        "scientific_claim_eligibility": SCIENTIFIC_CLAIM_ELIGIBILITY,
        "preflight_captured_before_first_fixture": binding,
        "preflight_ok": frozen_ok,
        "fixture_completeness_ok": completeness_ok,
        "fixtures_total": len(results),
        "fixtures_oracle_match": sum(1 for r in results if r.oracle_match),
        "known_answer_suite": status,
        "per_fixture": ledgers,
    }
    RAW_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    for item in ledgers:
        (LEDGER_DIR / f"{item['fixture_id']}.json").write_text(
            json.dumps(item, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  raw result     -> {RAW_PATH}")
    print(f"  ledgers (13)   -> {LEDGER_DIR}")
    print("=" * 72)
    return 0 if (all_ok and frozen_ok and completeness_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
