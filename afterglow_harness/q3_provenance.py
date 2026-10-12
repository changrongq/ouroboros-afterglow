"""
q3_provenance.py — Q3 new-lineage provenance + INDEPENDENT recompute of the RC11
20 execution-critical role hashes (凌翼 Q7 / EXECUTION ORDER step 6).

Why a SEPARATE module
---------------------
凌翼 Q7: "new-lineage provenance + independent recompute of RC11's 20
execution-critical source hashes." The RC11 hashes are anchored inside the FROZEN
RC11 MANIFEST (78bdb90f...), which MUST NOT be touched. Q3 is a NEW lineage, so it
carries its OWN provenance:

  · Q3_EXECUTION_CRITICAL  — the Q3 modules whose bytes can change a Q3 decision
                             (contract, matrix, dacl, handle audit, reset chain,
                             worker/isolation, driver, adversarial).
  · RC11_ROLE_RECOMPUTE    — an INDEPENDENT re-hash of the 20 RC11 roles, so we can
                             prove the frozen bytes still match their RC11 digests
                             without trusting the MANIFEST (defence against a
                             changed-on-disk-but-manifest-not-updated drift).

This module performs no OS calls beyond reading bytes; it is safe everywhere.

Canonical hashing
-----------------
Role bytes are hashed AS-ON-DISK after LF-normalisation is NOT applied here (the
frozen objects are hashed by raw bytes). We report the RAW SHA-256 (exactly what
qualification_binding.sha256_file computes) so the recompute is comparable.

A Q3 lineup is frozen by writing a DETACHED record (q3_provenance_detached.txt)
that lists every role + raw sha256; a later run recomputes and compares.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

Q3_LINEAGE_ID = "Q3_OS_ISOLATION_LINEAGE_V1"

# Q3 modules whose bytes can change a Q3 qualification decision.
# 凌翼 B3 (Q3 FREEZE ADJUDICATION 2026-10-12): the Q3 freeze list keeps its OWN
# 10 execution roles. RC12's binding module is a SEPARATE lineage and MUST NOT be
# folded in here (folding it in would silently change the Q3 lineage digest).
Q3_EXECUTION_CRITICAL = (
    "q3_contract.py",
    "q3_access_matrix.py",
    "q3_dacl.py",
    "q3_handle_audit.py",
    "q3_reset_chain.py",
    "win32_isolation.py",
    "win32_worker_process.py",
    "q3_qualify.py",
    "q3_adversarial.py",
    "q3_provenance.py",
)

#: 凌翼 B3: module names that belong to a DIFFERENT lineage and must NEVER appear
#: in Q3_EXECUTION_CRITICAL (guards against accidental folding).
FOREIGN_LINEAGE_MODULES = (
    "qualification_binding_rc12.py",
)


def assert_lineage_boundary() -> tuple[bool, list]:
    """凌翼 B3: Q3 and RC12 are SEPARATE lineages. Returns (ok, violations).

    ok iff Q3_EXECUTION_CRITICAL contains exactly 10 roles AND none of the
    FOREIGN_LINEAGE_MODULES appear in it.
    """
    violations = []
    q3 = list(Q3_EXECUTION_CRITICAL)
    if len(q3) != 10:
        violations.append(f"Q3_ROLE_COUNT={len(q3)} (expected 10)")
    if len(set(q3)) != len(q3):
        violations.append("Q3_ROLE_DUPLICATE")
    for m in FOREIGN_LINEAGE_MODULES:
        if m in q3:
            violations.append(f"FOREIGN_MODULE_IN_Q3: {m}")
    return (len(violations) == 0), violations


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def role_hashes(harness_dir: Path, roles) -> tuple[dict, list]:
    """Hash each role in `roles` under `harness_dir`.

    Returns (hashes, missing). A missing role is NOT silently skipped; it is
    reported so a caller can fail closed.
    """
    hashes = {}
    missing = []
    for r in roles:
        p = Path(harness_dir) / r
        if p.exists():
            hashes[r] = sha256_file(p)
        else:
            missing.append(r)
    return hashes, missing


def recompute_rc11_roles(harness_dir: Path) -> tuple[dict, list]:
    """Independently re-hash the RC11 20 execution-critical roles.

    We import the frozen RC11 registry to know WHICH roles; but the HASHES come
    from our own byte read, independent of the MANIFEST.
    """
    from qualification_role_registry import EXECUTION_CRITICAL_ROLES
    return role_hashes(harness_dir, EXECUTION_CRITICAL_ROLES)


def recompute_q3_roles(harness_dir: Path) -> tuple[dict, list]:
    return role_hashes(harness_dir, Q3_EXECUTION_CRITICAL)


def q3_lineage_digest(harness_dir: Path) -> tuple[str, list]:
    """A single canonical digest over ALL Q3 execution-critical role hashes.

    BD-76 (睫): the lineage-boundary guard MUST run at the GENERATION entry point,
    not only in the tests that merely prove it exists. If the Q3 role SET has been
    altered (wrong count / RC12 folded in), we FAIL here — raising — instead of
    silently emitting a new digest for a mutated set. This is the door the change
    actually walks through.

    Deterministic: roles sorted, joined as '<role> <sha256>\\n', then SHA-256.
    Returns (digest, missing).
    """
    ok, violations = assert_lineage_boundary()
    if not ok:
        raise ValueError(f"LINEAGE_BOUNDARY_VIOLATION (digest not generated): {violations}")
    hashes, missing = recompute_q3_roles(harness_dir)
    if missing:
        return "", missing
    payload = "".join(f"{r} {hashes[r]}\n" for r in sorted(hashes))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest(), []


def write_detached_record(harness_dir: Path, out_path: Path) -> str:
    """Write a DETACHED provenance record (roles + raw hashes + lineage digest).

    BD-76 (睫): guard at THIS entry point too — a mutated Q3 role set must not
    produce a record. Fails closed (raises) before writing anything.

    Returns the lineage digest. The record is OUTSIDE the frozen objects (it is
    metadata), so it can be regenerated; it never edits any role file.
    """
    _ok, _violations = assert_lineage_boundary()
    if not _ok:
        raise ValueError(f"LINEAGE_BOUNDARY_VIOLATION (record not written): {_violations}")
    q3_hashes, q3_missing = recompute_q3_roles(harness_dir)
    rc11_hashes, rc11_missing = recompute_rc11_roles(harness_dir)
    digest, _ = q3_lineage_digest(harness_dir)
    lines = [f"Q3_LINEAGE_ID {Q3_LINEAGE_ID}"]
    lines.append(f"Q3_LINEAGE_DIGEST {digest}")
    lines.append("# Q3 execution-critical roles (raw sha256)")
    for r in sorted(q3_hashes):
        lines.append(f"{r} {q3_hashes[r]}")
    lines.append("# RC11 recompute (independent re-hash of the 20 roles)")
    for r in sorted(rc11_hashes):
        lines.append(f"{r} {rc11_hashes[r]}")
    if q3_missing:
        lines.append("# MISSING_Q3_ROLES " + " ".join(sorted(q3_missing)))
    if rc11_missing:
        lines.append("# MISSING_RC11_ROLES " + " ".join(sorted(rc11_missing)))
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return digest


def required_role_set() -> frozenset:
    """凌翼 Q3 STEP 6: the FROZEN union of roles a valid record MUST contain —
    all Q3 execution-critical roles AND all RC11 execution-critical roles."""
    from qualification_role_registry import EXECUTION_CRITICAL_ROLES
    return frozenset(set(Q3_EXECUTION_CRITICAL) | set(EXECUTION_CRITICAL_ROLES))


def verify_against_record(harness_dir: Path, record_path: Path) -> tuple[bool, list]:
    """Recompute and compare against a detached record. Returns (ok, diffs).

    凌翼 Q3 STEP 6 (P1): a record that OMITS a required role must FAIL — comparing
    only the entries that happen to be present lets a deletion attack pass. We
    therefore require EXACT role-set equality against the frozen required set,
    THEN compare each hash.
    """
    if not Path(record_path).exists():
        return False, ["record missing"]
    rec = {}
    for line in Path(record_path).read_text(encoding="utf-8").splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        if len(parts) == 2 and parts[0].endswith(".py"):
            rec[parts[0]] = parts[1]
    current, _ = recompute_q3_roles(harness_dir)
    current.update(recompute_rc11_roles(harness_dir)[0])
    diffs = []
    # 1. EXACT role-set equality (deletion / addition attack).
    required = required_role_set()
    recorded = set(rec.keys())
    missing_roles = sorted(required - recorded)
    extra_roles = sorted(recorded - required)
    if missing_roles:
        diffs.append(f"RECORD_MISSING_REQUIRED_ROLES: {missing_roles}")
    if extra_roles:
        diffs.append(f"RECORD_HAS_UNEXPECTED_ROLES: {extra_roles}")
    # 2. per-role hash comparison (for roles present on both sides).
    for r in sorted(required & recorded):
        if r not in current:
            diffs.append(f"MISSING_FILE {r}")
        elif current[r] != rec[r]:
            diffs.append(f"CHANGED {r}: {rec[r]} -> {current[r]}")
    return (len(diffs) == 0), diffs


# ---------------------------------------------------------------------------
# Selftest
# ---------------------------------------------------------------------------

def _selftest() -> int:
    global Q3_EXECUTION_CRITICAL
    import tempfile
    results = []

    def chk(name, cond):
        results.append(bool(cond))
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    harness = Path(__file__).resolve().parent

    q3, q3_missing = recompute_q3_roles(harness)
    chk("Q3 roles all present", q3_missing == [])
    chk("Q3 roles non-empty", len(q3) == len(Q3_EXECUTION_CRITICAL))
    # 凌翼 B3: exactly 10 Q3 roles; RC12 module must NOT be in the Q3 lineage.
    _lb_ok, _lb_v = assert_lineage_boundary()
    chk("B3: Q3 lineage boundary (exactly 10 roles, no RC12)", _lb_ok is True)
    if not _lb_ok:
        print("   violations:", _lb_v)
    chk("B3: RC12 module is NOT in Q3_EXECUTION_CRITICAL",
        "qualification_binding_rc12.py" not in Q3_EXECUTION_CRITICAL)
    chk("B3: RC12 module IS in FOREIGN_LINEAGE_MODULES",
        "qualification_binding_rc12.py" in FOREIGN_LINEAGE_MODULES)

    # BD-76 (睫): the guard must FIRE at the GENERATION entries, not only exist in
    # the tests. Mutate the Q3 role set and prove digest/record generation FAILS.
    _orig_roles = Q3_EXECUTION_CRITICAL
    try:
        # (a) fold RC12 into the Q3 set -> digest generation must RAISE
        Q3_EXECUTION_CRITICAL = tuple(_orig_roles) + ("qualification_binding_rc12.py",)
        _raised = False
        try:
            q3_lineage_digest(harness)
        except ValueError:
            _raised = True
        chk("BD-76: mutated set (RC12 folded) -> q3_lineage_digest RAISES", _raised is True)
        # (b) record write must also RAISE and write NOTHING
        import tempfile as _tf
        _rp = Path(_tf.mkdtemp(prefix="bd76_")) / "rec.txt"
        _raised2 = False
        try:
            write_detached_record(harness, _rp)
        except ValueError:
            _raised2 = True
        chk("BD-76: mutated set -> write_detached_record RAISES", _raised2 is True)
        chk("BD-76: record NOT written on violation", not _rp.exists())
        # (c) 11-role count alone (drop a real role) also RAISES
        Q3_EXECUTION_CRITICAL = tuple(_orig_roles)[:-1]
        _raised3 = False
        try:
            q3_lineage_digest(harness)
        except ValueError:
            _raised3 = True
        chk("BD-76: 9-role set -> q3_lineage_digest RAISES", _raised3 is True)
    finally:
        Q3_EXECUTION_CRITICAL = _orig_roles
    chk("BD-76: original set restores and generates",
        q3_lineage_digest(harness)[0] == q3_lineage_digest(harness)[0]
        and len(q3_lineage_digest(harness)[0]) == 64)

    rc11, rc11_missing = recompute_rc11_roles(harness)
    chk("RC11 roles all present (no drift)", rc11_missing == [])
    chk("RC11 recompute covers 20 roles", len(rc11) == 20)

    d1, m1 = q3_lineage_digest(harness)
    d2, m2 = q3_lineage_digest(harness)
    chk("lineage digest deterministic", d1 == d2 and len(d1) == 64 and m1 == [])

    # detached record round-trip
    tmp = Path(tempfile.mkdtemp(prefix="q3_prov_"))
    try:
        rec = tmp / "q3_provenance_detached.txt"
        dig = write_detached_record(harness, rec)
        chk("record written + digest matches", rec.exists() and dig == d1)
        ok, diffs = verify_against_record(harness, rec)
        chk("verify against fresh record -> ok", ok is True and diffs == [])

        # mutate the record to simulate drift -> must be detected
        text = rec.read_text(encoding="utf-8")
        rec.write_text(text.replace("q3_contract.py ", "q3_contract.py 0", 1), encoding="utf-8")
        ok2, diffs2 = verify_against_record(harness, rec)
        chk("tampered record detected as CHANGED", ok2 is False and any("CHANGED" in x for x in diffs2))

        # 凌翼 STEP 6: DELETING a role line from the record must FAIL (exact set)
        rec.write_text(text, encoding="utf-8")
        lines = [l for l in text.splitlines() if not l.startswith("q3_dacl.py ")]
        rec.write_text("\n".join(lines) + "\n", encoding="utf-8")
        ok_del, diffs_del = verify_against_record(harness, rec)
        chk("record with a DELETED role line detected (missing required)",
            ok_del is False and any("RECORD_MISSING_REQUIRED_ROLES" in x for x in diffs_del))

        # adding an unexpected role line must also FAIL
        rec.write_text(text + "totally_fake_role.py " + "0" * 64 + "\n", encoding="utf-8")
        ok_add, diffs_add = verify_against_record(harness, rec)
        chk("record with an UNEXPECTED role detected",
            ok_add is False and any("RECORD_HAS_UNEXPECTED_ROLES" in x for x in diffs_add))
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for r in results if r)
    print(f"\nq3_provenance selftest: {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
