"""Dump raw machine results for the two verification points 凌翼 requested.

  Point 1: post-V5e-fix MANIFEST lineage.
  Point 2: V4.1 actual scope/status semantics (raw, not the report table).

This script prints the *machine* result dicts, not a curated table.
"""
from __future__ import annotations

import json
from dataclasses import asdict

import fixtures


def main() -> None:
    print("=== V4.1 raw machine result ===")
    r = fixtures.fixture_V4_1()
    print("expected      :", json.dumps(r.expected, ensure_ascii=False))
    print("actual        :", json.dumps(r.actual, ensure_ascii=False))
    print("ledger.notes  :", json.dumps(r.ledger.notes, ensure_ascii=False))
    print("oracle_match  :", r.oracle_match)
    print()

    print("=== V5e raw machine result ===")
    r = fixtures.fixture_V5e()
    print("expected      :", json.dumps(r.expected, ensure_ascii=False))
    print("actual        :", json.dumps(r.actual, ensure_ascii=False))
    print("oracle_match  :", r.oracle_match)
    print()

    print("=== V4.1 ledger fixture_id / attempted scope fields present? ===")
    r = fixtures.fixture_V4_1()
    led_d = asdict(r.ledger)
    print("ledger keys   :", list(led_d.keys()))


if __name__ == "__main__":
    main()
