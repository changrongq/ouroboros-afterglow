"""
verify_q3_freeze.py — verify the Q3 frozen source against the DETACHED freeze reference.

凌翼 Q3 DESIGN FREEZE (2026-10-12): freeze the 10 Q3 execution roles at
FROZEN_CODE_COMMIT 2c92074 with lineage digest 45034911... This script checks the
CURRENT working tree against the detached reference `reports/frozen/
Q3_FROZEN_REFERENCE_2c92074.txt`:

  · every frozen role exists;
  · its byte count and SHA-256 match the reference exactly;
  · the recomputed lineage digest equals the reference digest.

Exit codes: 0 = FROZEN_IDENTITY_OK, 1 = DRIFT (mismatch), 2 = reference missing.

IMPORTANT (凌翼): the reference is the EXTERNAL authority. This verifier does NOT
trust q3_provenance's own output as authorization — it reads the frozen reference
and re-hashes the actual bytes independently.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parent / "reports" / "frozen" / "Q3_FROZEN_REFERENCE_2c92074.txt"

_REF_RE = re.compile(r"^([A-Za-z0-9_]+\.py)\s+(\d+)\s+([0-9a-f]{64})\s*$")
_DIGEST_RE = re.compile(r"^Q3_LINEAGE_DIGEST\s*=\s*([0-9a-f]{64})\s*$", re.MULTILINE)


def _load_reference() -> tuple[dict, str]:
    """Parse ONLY the frozen Q3 role block (between 'Frozen Q3 roles' and the next
    '# ' section marker), so RC12 / RC11 lines are NOT counted as Q3 roles."""
    roles: dict = {}
    digest = ""
    in_q3_block = False
    for line in REFERENCE.read_text(encoding="utf-8").splitlines():
        if line.startswith("# Frozen Q3 roles"):
            in_q3_block = True
            continue
        if in_q3_block and line.startswith("# "):
            in_q3_block = False      # end of Q3 block (next section comment)
        d = _DIGEST_RE.match(line)
        if d:
            digest = d.group(1)
            continue
        if in_q3_block:
            m = _REF_RE.match(line)
            if m:
                roles[m.group(1)] = (int(m.group(2)), m.group(3))
    return roles, digest


def _recompute_digest(hashes: dict) -> str:
    payload = "".join(f"{r} {hashes[r]}\n" for r in sorted(hashes))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main() -> int:
    if not REFERENCE.exists():
        print(f"REFERENCE_MISSING: {REFERENCE}")
        return 2
    roles, ref_digest = _load_reference()
    if len(roles) != 10:
        print(f"REFERENCE_MALFORMED: expected 10 roles, parsed {len(roles)}")
        return 2

    problems = []
    hashes = {}
    for role, (ref_bytes, ref_sha) in sorted(roles.items()):
        p = HERE / role
        if not p.exists():
            problems.append(f"MISSING {role}")
            continue
        raw = p.read_bytes()
        actual_sha = hashlib.sha256(raw).hexdigest()
        hashes[role] = actual_sha
        if len(raw) != ref_bytes:
            problems.append(f"BYTES {role}: ref={ref_bytes} actual={len(raw)}")
        if actual_sha != ref_sha:
            problems.append(f"SHA256 {role}: ref={ref_sha} actual={actual_sha}")

    if len(hashes) == 10:
        recomputed = _recompute_digest(hashes)
        if recomputed != ref_digest:
            problems.append(f"DIGEST: ref={ref_digest} actual={recomputed}")

    if problems:
        print("Q3_FROZEN_IDENTITY = DRIFT")
        for p in problems:
            print("  -", p)
        return 1
    print("Q3_FROZEN_IDENTITY = OK")
    print(f"  roles=10 digest={ref_digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
