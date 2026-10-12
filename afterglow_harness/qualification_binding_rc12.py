"""
qualification_binding_rc12.py — RC12 TARGETED HARDENING of the detached-record match.

Authority
---------
凌翼 LINGYI REVIEW — Q3 / RC11 (2026-10-12), REVIEWED_HEAD 68bc80f:
    OBS-2 = CONFIRMED
      Detached binding uses substring matching.
      Strict authoritative-field equality needed.
      RC12 targeted hardening AUTHORIZED.
    "旧 detached_match 不得被宣传为能够严格核验任意新 detached lineage；
     要获得修正后的绑定资格，必须建立新的 RC12 候选。"
    "RC12 的修法应该是严格解析唯一权威字段
     IMPLEMENTATION_BINDING_MANIFEST_HASH
     然后要求该字段值与实际 SHA-256 完全相等；重复字段、缺失字段、注释中的 hash、
     旧 hash 混入及错误字节数均不得取得匹配资格。"

What this fixes
---------------
RC11's `qualification_binding.verify()` used:
    detached_match = manifest_sha in detached_text
A substring test. Once the detached record carries a lineage (several historical
hashes), or the current hash appears in a comment, an OLD/other binding could
still "match". RC12 replaces this with a STRICT parse:

  1. find the UNIQUE authoritative line  `IMPLEMENTATION_BINDING_MANIFEST_HASH = <64hex>`
     (anchored, at line start);
  2. require EXACTLY ONE such line (duplicate => reject);
  3. require the field value to equal the actual SHA-256 **exactly**;
  4. require the recorded MANIFEST_BYTES to equal the actual byte count;
  5. reject any hash appearing only in comments / non-authoritative lines.

This module is the RC12 candidate. It is data + a pure function; it does NOT
modify any RC11 byte.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

RC12_ID = "RC12_DETACHED_BINDING_HARDENING_V1"
RC12_STATUS = "CANDIDATE (NOT yet qualified; RC11 remains the closed historical lineage)"

#: The single authoritative field name.
_AUTHORITATIVE_FIELD = "IMPLEMENTATION_BINDING_MANIFEST_HASH"
_BYTES_FIELD = "MANIFEST_BYTES"

#: Anchored: line begins (after optional spaces) with the field name, `=`, 64 hex.
_AUTH_RE = re.compile(
    r"^[ \t]*" + re.escape(_AUTHORITATIVE_FIELD) + r"[ \t]*=[ \t]*([0-9a-fA-F]{64})[ \t]*$",
    re.MULTILINE)
_BYTES_RE = re.compile(
    r"^[ \t]*" + re.escape(_BYTES_FIELD) + r"[ \t]*=[ \t]*(\d+)[ \t]*$",
    re.MULTILINE)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def strict_detached_match(manifest_path: Path, detached_path: Path) -> tuple[bool, dict]:
    """RC12 strict detached-record match. Returns (ok, evidence).

    Rejects (ok=False) on: missing detached file, missing/duplicate authoritative
    field, hash mismatch, byte-count mismatch. Only an EXACT, UNIQUE authoritative
    field equal to the actual manifest SHA-256 (and matching byte count) passes.
    """
    ev: dict = {"rc12_id": RC12_ID}
    if not manifest_path.exists():
        ev["error"] = "manifest missing"
        return False, ev
    actual_sha = sha256_file(manifest_path)
    actual_bytes = manifest_path.stat().st_size
    ev["actual_sha256"] = actual_sha
    ev["actual_bytes"] = actual_bytes

    if not detached_path.exists():
        ev["error"] = "detached missing"
        return False, ev
    text = detached_path.read_text(encoding="utf-8")

    # 1. exactly one authoritative field
    matches = _AUTH_RE.findall(text)
    ev["authoritative_field_count"] = len(matches)
    if len(matches) == 0:
        ev["reason"] = "AUTHORITATIVE_FIELD_MISSING"
        return False, ev
    if len(matches) > 1:
        ev["reason"] = "AUTHORITATIVE_FIELD_DUPLICATE"
        return False, ev
    recorded_sha = matches[0].lower()
    ev["recorded_sha256"] = recorded_sha

    # 2. exact hash equality
    if recorded_sha != actual_sha.lower():
        ev["reason"] = "HASH_MISMATCH"
        return False, ev

    # 3. byte-count equality (if the field is present)
    byte_matches = _BYTES_RE.findall(text)
    if byte_matches:
        if len(byte_matches) > 1:
            ev["reason"] = "BYTES_FIELD_DUPLICATE"
            return False, ev
        recorded_bytes = int(byte_matches[0])
        ev["recorded_bytes"] = recorded_bytes
        if recorded_bytes != actual_bytes:
            ev["reason"] = "BYTES_MISMATCH"
            return False, ev

    ev["reason"] = "EXACT_AUTHORITATIVE_MATCH"
    return True, ev


# ---------------------------------------------------------------------------
# Selftest — pure; demonstrates the RC11 substring hole is CLOSED under RC12.
# ---------------------------------------------------------------------------

def _selftest() -> int:
    import tempfile
    results = []

    def chk(name, cond):
        results.append(bool(cond))
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    tmp = Path(tempfile.mkdtemp(prefix="rc12_"))
    man = tmp / "MANIFEST.md"
    man.write_text("dummy manifest body\n", encoding="utf-8")
    real = sha256_file(man)
    real_bytes = man.stat().st_size

    def rec(text):
        d = tmp / "detached.txt"
        d.write_text(text, encoding="utf-8")
        return d

    good = f"MANIFEST_BYTES = {real_bytes}\nIMPLEMENTATION_BINDING_MANIFEST_HASH = {real}\n"
    ok, ev = strict_detached_match(man, rec(good))
    chk("RC12: exact authoritative match -> OK", ok is True)

    # RC11's substring hole: hash only in a COMMENT must NOT pass
    comment_only = f"# historical: {real}\nIMPLEMENTATION_BINDING_MANIFEST_HASH = {'0'*64}\n"
    ok, ev = strict_detached_match(man, rec(comment_only))
    chk("RC12: hash only in a comment -> REJECT (RC11 would pass)", ok is False)

    # duplicate authoritative field -> reject
    dup = good + f"IMPLEMENTATION_BINDING_MANIFEST_HASH = {real}\n"
    ok, ev = strict_detached_match(man, rec(dup))
    chk("RC12: duplicate authoritative field -> REJECT", ok is False)

    # missing field -> reject
    ok, ev = strict_detached_match(man, rec(f"MANIFEST_BYTES = {real_bytes}\n"))
    chk("RC12: missing authoritative field -> REJECT", ok is False)

    # wrong hash -> reject
    ok, ev = strict_detached_match(man, rec(good.replace(real, "a"*64)))
    chk("RC12: wrong hash -> REJECT", ok is False)

    # wrong byte count -> reject
    bad_bytes = f"MANIFEST_BYTES = {real_bytes + 1}\nIMPLEMENTATION_BINDING_MANIFEST_HASH = {real}\n"
    ok, ev = strict_detached_match(man, rec(bad_bytes))
    chk("RC12: wrong byte count -> REJECT", ok is False)

    # old/historical hash mixed in (lineage) -> reject (field must equal current)
    lineage = (f"# RC0 { '0'*64 }\nIMPLEMENTATION_BINDING_MANIFEST_HASH = {'1'*64}\n")
    ok, ev = strict_detached_match(man, rec(lineage))
    chk("RC12: historical-only hash (lineage) -> REJECT", ok is False)

    # missing detached -> reject
    ok, ev = strict_detached_match(man, tmp / "nope.txt")
    chk("RC12: missing detached file -> REJECT", ok is False)

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    passed = sum(1 for r in results if r)
    print(f"\nqualification_binding_rc12 selftest: {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
