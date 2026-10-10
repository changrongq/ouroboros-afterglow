"""
verify_manifest_binding.py (RC9) — thin wrapper over qualification_binding.

RC8's version kept a hard-coded role list (and treated manifest_bind.py as a
bound driver). RC9's single authority is qualification_binding + the role
registry. This wrapper just calls it, so the two can never disagree.
"""
from __future__ import annotations

from pathlib import Path

import qualification_binding as qb

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MANIFEST_PATH = ROOT / "reports" / "AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md"
DETACHED_PATH = ROOT / "reports" / "MANIFEST_v0.1_HASH.txt"
SPEC_PATH = ROOT / "spec" / "AFTERGLOW_IMPLEMENTATION_BINDING_v0.1.md"
PREREG_PATH = ROOT / "prereg" / "AFTERGLOW_MVP_PREREGISTRATION_v0.1.md"

if not SPEC_PATH.exists():
    SPEC_PATH = ROOT / "reports" / "AFTERGLOW IMPLEMENTATION BINDING v0.1.md"
if not PREREG_PATH.exists():
    for cand in ("AFTERGLOW_MVP_PREREGISTRATION_v0.1_FREEZE_CANDIDATE.md",
                 "AFTERGLOW MVP PREREGISTRATION v0.1.md"):
        p = ROOT / "reports" / cand
        if p.exists():
            PREREG_PATH = p
            break


def main() -> int:
    contract_hash = qb.sha256_file(HERE / "fixture_contracts.py")
    ev, ok = qb.verify(HERE, MANIFEST_PATH, DETACHED_PATH, SPEC_PATH, PREREG_PATH, contract_hash)
    for k in ("MANIFEST_HASH", "detached_match", "registry_vs_manifest_equal",
              "role_set_equal", "role_hash_ok", "provenance_not_in_critical",
              "spec_file_matches_frozen", "prereg_file_matches_frozen",
              "fixture_contract_bound"):
        print(f"    {k} = {ev.get(k)}")
    print()
    print("BINDING_INTEGRITY =", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
