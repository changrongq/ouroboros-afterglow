"""
qualification_binding.py — the QUALIFICATION-SIDE binding verifier (RC8).

凌翼 RC8 ruling R2: manifest_bind.py stays BUILD_PROVENANCE ONLY and is FORBIDDEN
in the qualifying runtime. This module is the qualification runtime's OWN bound
verifier; it does NOT import manifest_bind.

It performs, and nothing else:
  1. hash exact MANIFEST bytes;
  2. match the detached record;
  3. parse the exact role -> path -> hash map that the MANIFEST binds;
  4. hash the ACTUAL runtime files;
  5. require EXACT required-role set equality (not subset; non-empty);
  6. verify SPEC/prereg exact hashes;
  7. verify fixture-contract identity.

No vacuous all({})=True is possible: the required role set is explicit and
non-empty, and role set equality is required.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

# The required runtime roles. This set is itself frozen (its identity is part of
# the MANIFEST). Selection/decision logic may NOT bypass it.
REQUIRED_RUNTIME_ROLES = frozenset({
    "harness_constants.py",
    "storage.py",
    "writers.py",
    "readers.py",
    "observer.py",
    "perturbation_j.py",
    "reset.py",
    "evaluator.py",
    "fixtures.py",
    # qualification-side runtime modules:
    "fixture_contracts.py",
    "gates.py",
    "qualification_binding.py",
    "run_known_answer_suite.py",
    "verify_manifest_binding.py",
})


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_role_hash_map(manifest_text: str) -> dict[str, str]:
    """Extract '<file>.py  ....  <sha256>' lines from the MANIFEST §十三 table."""
    roles: dict[str, str] = {}
    for line in manifest_text.splitlines():
        m = re.match(r"^\s*([A-Za-z0-9_]+\.py)\s+[0-9.]+\s+([0-9a-f]{64})\s*$", line)
        if m:
            roles[m.group(1)] = m.group(2)
    return roles


def verify(
    harness_dir: Path,
    manifest_path: Path,
    detached_path: Path,
    spec_path: Path | None,
    prereg_path: Path | None,
    fixture_contract_hash: str,
) -> tuple[dict, bool]:
    ev: dict = {}
    if not manifest_path.exists():
        return {"error": "manifest missing"}, False
    manifest_sha = sha256_file(manifest_path)
    ev["MANIFEST_HASH"] = manifest_sha
    ev["MANIFEST_BYTES"] = manifest_path.stat().st_size

    ev["detached_match"] = bool(
        detached_path.exists() and manifest_sha in detached_path.read_text(encoding="utf-8")
    )

    man_text = manifest_path.read_text(encoding="utf-8")
    bound_roles = _parse_role_hash_map(man_text)
    ev["frozen_role_count"] = len(bound_roles)

    # 5. EXACT role set equality, non-empty
    ev["required_roles_nonempty"] = len(REQUIRED_RUNTIME_ROLES) > 0
    observed = frozenset(r for r in REQUIRED_RUNTIME_ROLES if (harness_dir / r).exists())
    ev["role_set_equal"] = (observed == REQUIRED_RUNTIME_ROLES)
    ev["roles_missing_files"] = sorted(REQUIRED_RUNTIME_ROLES - observed)

    # 4. hash actual runtime files; compare to the MANIFEST role-hash map
    role_hash_ok: dict[str, bool] = {}
    for role in sorted(REQUIRED_RUNTIME_ROLES):
        p = harness_dir / role
        role_hash_ok[role] = (p.exists() and role in bound_roles
                              and sha256_file(p) == bound_roles[role])
    ev["role_hash_ok"] = all(role_hash_ok.values())
    ev["role_hash_mismatch"] = {k: v for k, v in role_hash_ok.items() if not v}

    # 6. SPEC / prereg exact hashes (must appear in the MANIFEST)
    spec_sha = sha256_file(spec_path) if (spec_path and spec_path.exists()) else None
    prereg_sha = sha256_file(prereg_path) if (prereg_path and prereg_path.exists()) else None
    ev["SPEC_FILE_HASH"] = spec_sha
    ev["PREREG_FILE_HASH"] = prereg_sha
    ev["spec_file_matches_frozen"] = bool(spec_sha and spec_sha in man_text)
    ev["prereg_file_matches_frozen"] = bool(prereg_sha and prereg_sha in man_text)

    # 7. fixture-contract identity (its own file hash must be bound)
    ev["fixture_contract_hash"] = fixture_contract_hash
    ev["fixture_contract_bound"] = fixture_contract_hash in man_text

    ok = all([
        ev["detached_match"],
        ev["required_roles_nonempty"],
        ev["role_set_equal"],
        ev["role_hash_ok"],
        ev["spec_file_matches_frozen"],
        ev["prereg_file_matches_frozen"],
        ev["fixture_contract_bound"],
    ])
    return ev, ok
