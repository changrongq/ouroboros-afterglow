"""
Lineage evidence generator for 凌翼's two verification points.

Produces a reproducible artifact proving:
  (1) the frozen MANIFEST was rebuilt AFTER the V5e fix (so bound component
      hashes are the POST-fix hashes), and the detached record matches;
  (2) the exact scope/status semantics each fixture actually emits, so scope
      promotions (e.g. a pre-reset C2 defect labelled as L2 INVALID) are
      visible rather than hidden behind a curated table.

Not a qualification artifact. Evidence only.
"""

from __future__ import annotations

import json
from pathlib import Path

import fixtures
from harness_constants import REFERENCE_HARNESS_SPEC_HASH
from manifest_bind import compute_all, manifest_self_hash

REPORTS = Path(__file__).resolve().parent.parent / "reports"
MANIFEST_PATH = REPORTS / "AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md"
DETACHED_PATH = REPORTS / "MANIFEST_v0.1_HASH.txt"


def lineage() -> dict:
    d = compute_all()
    man_text = MANIFEST_PATH.read_text(encoding="utf-8")
    self_h = manifest_self_hash(MANIFEST_PATH)
    detached = DETACHED_PATH.read_text(encoding="utf-8")
    return {
        "SPEC_HASH": REFERENCE_HARNESS_SPEC_HASH,
        "FROZEN_MANIFEST_HASH": self_h["sha256"],
        "MANIFEST_BYTES": self_h["bytes"],
        "detached_record_match": self_h["sha256"] in detached,
        "bound_components_present_in_frozen_manifest": {
            info["file"]: (info["sha256"] in man_text)
            for info in d["components"].values()
        },
        "current_fixtures_py_hash": d["components"]["fixtures"]["sha256"],
        "current_evaluator_py_hash": d["components"]["evaluator"]["sha256"],
    }


def scope_audit() -> dict:
    out = {}
    for fid in ("V4.1", "V5e"):
        r = fixtures.FIXTURES[fid]()
        out[fid] = {
            "expected": r.expected,
            "actual": r.actual,
            "ledger_notes": r.ledger.notes,
            "ledger_fields": sorted(r.ledger.__dict__.keys()),
            "oracle_match": r.oracle_match,
        }
    return out


def main() -> int:
    print("=" * 72)
    print("LINEAGE EVIDENCE (verification point 1)")
    print("=" * 72)
    print(json.dumps(lineage(), indent=2, ensure_ascii=False))

    print()
    print("=" * 72)
    print("SCOPE / STATUS AUDIT (verification point 2)")
    print("=" * 72)
    print(json.dumps(scope_audit(), indent=2, ensure_ascii=False))

    # Explicit scope-promotion detector for V4.1
    v41 = fixtures.FIXTURES["V4.1"]()
    promoted = "L2" in v41.expected
    has_scope_field = any("scope" in k.lower() for k in v41.ledger.__dict__.keys())
    print()
    print("V4.1 SCOPE CHECK:")
    print(f"  oracle labels L2 (post-reset) : {promoted}")
    print(f"  ledger has attempted_scope    : {has_scope_field}")
    if promoted and not has_scope_field:
        print("  !! FINDING: pre-reset C2-scope defect labelled as L2 INVALID,")
        print("     and no attempted_scope recorded. SCOPE PROMOTION DEFECT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
