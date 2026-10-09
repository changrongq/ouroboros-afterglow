"""Verify that every currently-computed hash still appears in the frozen MANIFEST.

Run after ANY code change to detect binding drift before relying on a PASS.
"""
from __future__ import annotations

from pathlib import Path

from manifest_bind import compute_all, hash_file

MANIFEST = Path(__file__).resolve().parent.parent / "reports" / "AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md"

# Execution-critical drivers (凌翼 boundary: can change qualification decision
# => MUST BE BOUND). Build tooling is provenance-only and checked separately.
BOUND_DRIVERS = ("run_known_answer_suite.py", "verify_manifest_binding.py")
PROVENANCE_TOOLS = ("manifest_bind.py", "freeze_manifest.py")


def main() -> int:
    man = MANIFEST.read_text(encoding="utf-8")
    d = compute_all()
    bad = 0

    print("components:")
    for role, info in sorted(d["components"].items()):
        ok = info["sha256"] in man
        bad += 0 if ok else 1
        print(f"  {info['file']:<24} {'OK ' if ok else 'DRIFT'}  {info['sha256'][:16]}...")

    print("derived:")
    for key in ("J_RULE_BUNDLE_HASH", "RESET_PROFILE_HASH", "DISCRIMINATION_RULESET_HASH",
                "CONTENT_CLASS_MANIFEST_HASH", "CONTENT_CLASS_EVIDENCE_SET_HASH"):
        ok = d[key] in man
        bad += 0 if ok else 1
        print(f"  {key:<28} {'OK ' if ok else 'DRIFT'}  {d[key][:16]}...")

    print("fixtures:")
    for k, h in d["FIXTURE_RULE_BUNDLE_HASHES"].items():
        ok = h in man
        bad += 0 if ok else 1
        print(f"  {k:<28} {'OK ' if ok else 'DRIFT'}  {h[:16]}...")

    here = Path(__file__).resolve().parent
    print("bound drivers:")
    for name in BOUND_DRIVERS:
        h = hash_file(here / name)
        ok = h in man
        bad += 0 if ok else 1
        print(f"  {name:<28} {'OK ' if ok else 'DRIFT'}  {h[:16]}...")

    print("provenance tools (advisory, not binding):")
    for name in PROVENANCE_TOOLS:
        h = hash_file(here / name)
        print(f"  {name:<28} {'rec ' if h in man else 'warn'}  {h[:16]}...")

    print()
    print(f"BINDING_INTEGRITY = {'PASS' if bad == 0 else f'FAIL ({bad} drift)'}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
