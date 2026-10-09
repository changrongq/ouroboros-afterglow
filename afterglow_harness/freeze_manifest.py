"""
Freeze + detached-record generator for the Implementation Binding MANIFEST.

Produces `reports/MANIFEST_v0.1_HASH.txt` containing the MANIFEST's own hash,
computed over the exact file bytes. The hash is deliberately NOT written back
into the MANIFEST (avoids self-reference; SPEC §11).

Usage:
  python freeze_manifest.py            # compute + print + write detached record
  python freeze_manifest.py --check    # verify manifest file is unchanged
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from harness_constants import REFERENCE_HARNESS_SPEC_HASH, PARENT_PREREG_SHA256
from manifest_bind import compute_all, manifest_self_hash

REPORTS = Path(__file__).resolve().parent.parent / "reports"
MANIFEST_PATH = REPORTS / "AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md"
DETACHED_PATH = REPORTS / "MANIFEST_v0.1_HASH.txt"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not MANIFEST_PATH.exists():
        print(f"ERROR: manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        return 2

    self_h = manifest_self_hash(MANIFEST_PATH)
    derived = compute_all()

    # sanity: no *field* residue in the instantiated manifest. We look for an
    # assignment whose value is literally TO_IMPLEMENT (e.g. "= TO_IMPLEMENT"),
    # not prose that merely mentions the term.
    text = MANIFEST_PATH.read_text(encoding="utf-8")
    import re

    residual = len(re.findall(r"=\s*TO_IMPLEMENT\b", text))

    if args.check:
        if not DETACHED_PATH.exists():
            print("CHECK FAIL: no detached record")
            return 1
        rec = DETACHED_PATH.read_text(encoding="utf-8")
        ok = self_h["sha256"] in rec
        print(f"CHECK {'PASS' if ok else 'FAIL'}: {self_h['sha256']}")
        return 0 if ok else 1

    lines = []
    lines.append("# AFTERGLOW IMPLEMENTATION BINDING MANIFEST v0.1 — DETACHED HASH RECORD")
    lines.append("# (detached: NOT written into the MANIFEST, to avoid self-reference)")
    lines.append("")
    lines.append(f"MANIFEST_FILE              = {self_h['manifest_file']}")
    lines.append(f"MANIFEST_BYTES             = {self_h['bytes']}")
    lines.append(f"IMPLEMENTATION_BINDING_MANIFEST_HASH = {self_h['sha256']}")
    lines.append(f"HASH_ALGORITHM             = {self_h['algorithm']}")
    lines.append("")
    lines.append(f"REFERENCE_HARNESS_SPEC_HASH = {REFERENCE_HARNESS_SPEC_HASH}")
    lines.append(f"PARENT_PREREG_SHA256        = {PARENT_PREREG_SHA256}")
    lines.append("")
    lines.append("# Derived execution-critical hashes (from manifest_bind.compute_all):")
    lines.append(f"J_RULE_BUNDLE_HASH          = {derived['J_RULE_BUNDLE_HASH']}")
    lines.append(f"RESET_PROFILE_HASH          = {derived['RESET_PROFILE_HASH']}")
    lines.append(f"DISCRIMINATION_RULESET_HASH = {derived['DISCRIMINATION_RULESET_HASH']}")
    lines.append(f"CONTENT_CLASS_MANIFEST_HASH = {derived['CONTENT_CLASS_MANIFEST_HASH']}")
    lines.append("")
    lines.append("# Component source hashes:")
    for role, info in sorted(derived["components"].items()):
        lines.append(f"  {info['file']:<24} {info['sha256']}")
    lines.append("")
    lines.append("# Residual TO_IMPLEMENT in manifest (must be 0):")
    lines.append(f"TO_IMPLEMENT_RESIDUAL = {residual}")
    lines.append("")

    DETACHED_PATH.write_text("\n".join(lines), encoding="utf-8")

    print(f"MANIFEST bytes                      = {self_h['bytes']}")
    print(f"IMPLEMENTATION_BINDING_MANIFEST_HASH = {self_h['sha256']}")
    print(f"TO_IMPLEMENT residual               = {residual}")
    print(f"detached record written to          = {DETACHED_PATH}")
    return 0 if residual == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
