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

from fixture_contracts import FROZEN_ORACLES, REQUIRED_FIXTURE_IDS
from fixtures import SCIENTIFIC_CLAIM_ELIGIBILITY, run_all
import qualification_binding as qb

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
RAW_PATH = ARTIFACTS / "RC8_qualifying_run_raw.json"
LEDGER_DIR = ARTIFACTS / "RC8_ledgers"


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _subset_eq(expected: dict, actual: dict) -> bool:
    """Expected (frozen oracle) must be a subset of actual."""
    for k, v in expected.items():
        if k not in actual:
            return False
        if isinstance(v, dict):
            if not isinstance(actual[k], dict) or not _subset_eq(v, actual[k]):
                return False
        elif actual[k] != v:
            return False
    return True


def capture_frozen_binding() -> tuple[dict, bool]:
    """Full qualification preflight via the bound qualification_binding verifier.

    (凌翼 RC8 R2: manifest_bind.py is FORBIDDEN in the qualifying runtime; this
    path uses qualification_binding only.)
    """
    contract_hash = qb.sha256_file(HARNESS_DIR / "fixture_contracts.py")
    ev, ok = qb.verify(
        harness_dir=HARNESS_DIR,
        manifest_path=MANIFEST_PATH,
        detached_path=DETACHED_PATH,
        spec_path=SPEC_PATH,
        prereg_path=PREREG_PATH,
        fixture_contract_hash=contract_hash,
    )
    # fixture-id set (completeness) still checked here
    ev["fixture_set_ok"] = (set(FROZEN_ORACLES.keys()) == set(REQUIRED_FIXTURE_IDS))
    ok = ok and ev["fixture_set_ok"]
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

    # ---- run fixtures; compare against the SINGLE frozen oracle source ----
    results = run_all()
    all_ok = True
    ledgers = []
    for r in results:
        oracle = FROZEN_ORACLES[r.fixture_id]
        ok = _subset_eq(oracle, r.actual)
        all_ok &= ok
        print(f"[{ 'ORACLE MATCH' if ok else 'ORACLE MISMATCH' }] {r.fixture_id}")
        if not ok:
            print(f"    frozen oracle = {oracle}")
            print(f"    actual        = {r.actual}")
        ledgers.append({
            "fixture_id": r.fixture_id,
            "frozen_oracle": oracle,
            "actual": r.actual,
            "oracle_match": ok,
            "ledger": dataclasses.asdict(r.ledger),
        })

    # completeness: every required id ran exactly once
    ran_ids = [x["fixture_id"] for x in ledgers]
    completeness_ok = (len(ran_ids) == len(set(ran_ids)) == len(REQUIRED_FIXTURE_IDS)
                       and set(ran_ids) == set(REQUIRED_FIXTURE_IDS))

    print("\n" + "=" * 72)
    print(f"fixtures: {sum(1 for x in ledgers if x['oracle_match'])}/{len(results)} oracle match")
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
        "fixtures_oracle_match": sum(1 for x in ledgers if x["oracle_match"]),
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
