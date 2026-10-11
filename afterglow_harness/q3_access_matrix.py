"""
q3_access_matrix.py — Q3 EXECUTABLE ACCESS MATRIX (versioned data object).

凌翼 Q3 NEXT EXECUTION ORDER step 2:
    "Complete executable permission matrix"

Why this file exists
--------------------
Across Q3 rounds 4-8 the recurring disease was "recorded but not CONSUMED by the
gate": a claim lived in a docstring / report, but the adjudicator never read it,
so a wrong claim could still sail through to PASS.  The access matrix is the
explicit, machine-readable statement of *what access is expected, in which
phase, for which subject, on which object, for which operation* — together with
*which witness must prove it*.

This module is DATA + a pure validator only.  It performs no OS calls.  The
driver (q3_reset_chain via q3_qualify) MUST consume `validate_access_matrix()`
so the claim is actually enforced, not merely written down.

Row schema (each matrix row is a dict):
    id          : stable identifier, e.g. "W-READ-PROTECTED"
    subject     : "worker" | "observer"
    phase       : "pre_reset" | "post_reset"
    object      : "protected_substrate" | "code_dir" | "probe" | "clear_targets"
    operation   : "read" | "write" | "append" | "rename" | "delete"
    expected    : "DENIED" | "GRANTED"
    witness     : the evidence field that must prove the expectation, e.g.
                  "attestation.verdict_ok" | "attestation.identity_ok" |
                  "code_immutable_ok" | "preserve_ok" | "clear_ok"

Rules enforced by validation (fail-closed):
  1. Every row id is unique.
  2. `expected` is exactly "DENIED" or "GRANTED".
  3. Every row has a non-empty `witness` drawn from WITNESS_FIELDS.
  4. NO row may expect the worker to be GRANTED read/write/append/rename/delete
     on the protected substrate in the post_reset phase (that would be a
     blinding failure by construction).
  5. The observer must be GRANTED read on the protected substrate post_reset
     (otherwise "the observer's eyes stay open" is unproven).
  6. Under Profile B, the matrix MUST contain at least one row that requires the
     runtime handle audit to be recorded (never silently dropped).

Any violation => validate returns (False, [reasons]).
"""

from __future__ import annotations

MATRIX_VERSION = "q3_access_matrix/1.0"

# Witnesses are the concrete evidence fields the adjudicator already computes.
# A matrix row is only meaningful if its witness is one of these.
WITNESS_FIELDS = (
    "attestation.verdict_ok",       # strict-schema PROBE verdict (post-reset access)
    "attestation.identity_ok",      # SID/exit/create-time/hash identity gate
    "code_immutable_ok",            # code-dir effective-permission immutability
    "preserve_ok",                  # S_handoff == S_restored (observer reads)
    "clear_ok",                     # required clear categories actually gone
    "handle_audit_recorded",        # runtime handle audit status recorded verbatim
    "access_ok",                    # F4 strict verdict gate (alias of verdict_ok)
    "pre_reset_verdict_ok",         # 凌翼 STEP 2: a DISTINCT pre-reset access witness
)

# Expectations.
DENIED = "DENIED"
GRANTED = "GRANTED"

# The canonical, frozen matrix.  This is the executable statement of the Q3
# isolation claim: the worker is blind to the protected substrate in BOTH
# phases; the observer can still read it after the reset; the code dir is
# immutable to the worker.
#
# 凌翼 Q3 STEP 2 (P1·Blocking): the matrix must define the FROZEN REQUIRED row
# set, each row must bind its OWN (subject, phase, object, operation) witness,
# and a single post-reset probe MUST NOT be reused as the pre-reset witness.
ACCESS_MATRIX = (
    # --- worker is blinded to the protected substrate (both phases) ----------
    # 凌翼 STEP 2: pre-reset the worker CAN still read (the deny is what blinds
    # it); post-reset it MUST be denied. Two DISTINCT phase-bound witnesses.
    dict(id="W-READ-PROTECTED-PRE", subject="worker", phase="pre_reset",
         object="protected_substrate", operation="read",
         expected=GRANTED, witness="pre_reset_verdict_ok"),
    dict(id="W-READ-PROTECTED-POST", subject="worker", phase="post_reset",
         object="protected_substrate", operation="read",
         expected=DENIED, witness="attestation.verdict_ok"),
    # --- worker cannot tamper with the frozen probe / code dir ---------------
    dict(id="W-WRITE-PROBE", subject="worker", phase="post_reset",
         object="probe", operation="write",
         expected=DENIED, witness="code_immutable_ok"),
    dict(id="W-APPEND-PROBE", subject="worker", phase="post_reset",
         object="probe", operation="append",
         expected=DENIED, witness="code_immutable_ok"),
    dict(id="W-RENAME-CODDIR", subject="worker", phase="post_reset",
         object="code_dir", operation="rename",
         expected=DENIED, witness="code_immutable_ok"),
    dict(id="W-DELETE-PROBE", subject="worker", phase="post_reset",
         object="probe", operation="delete",
         expected=DENIED, witness="code_immutable_ok"),
    # --- observer's eyes stay open -------------------------------------------
    dict(id="O-READ-PROTECTED-POST", subject="observer", phase="post_reset",
         object="protected_substrate", operation="read",
         expected=GRANTED, witness="preserve_ok"),
    # --- clear contract is real ----------------------------------------------
    dict(id="CLEAR-REQUIRED", subject="observer", phase="post_reset",
         object="clear_targets", operation="delete",
         expected=GRANTED, witness="clear_ok"),
    # --- runtime handle audit is RECORDED (never silently dropped, any profile)
    dict(id="HANDLE-AUDIT-RECORDED", subject="worker", phase="post_reset",
         object="probe", operation="read",
         expected=DENIED, witness="handle_audit_recorded"),
)

#: 凌翼 Q3 STEP 2: the FROZEN set of rows that MUST be present. This is what
#: stops "九行不能只是当前恰好有九行" — removing a required row must FAIL.
REQUIRED_MATRIX_IDS = (
    "W-READ-PROTECTED-PRE",
    "W-READ-PROTECTED-POST",
    "W-WRITE-PROBE",
    "W-APPEND-PROBE",
    "W-RENAME-CODDIR",
    "W-DELETE-PROBE",
    "O-READ-PROTECTED-POST",
    "CLEAR-REQUIRED",
    "HANDLE-AUDIT-RECORDED",
)

#: 凌翼 Q3 STEP 2: which witnesses are PHASE-SPECIFIC. A row's witness must be
#: consistent with the row's phase — a post-reset probe witness may not serve a
#: pre-reset row (and vice versa).
PHASE_ALLOWED_WITNESSES = {
    "pre_reset": frozenset({"pre_reset_verdict_ok", "attestation.identity_ok"}),
    "post_reset": frozenset({"attestation.verdict_ok", "access_ok",
                             "code_immutable_ok", "preserve_ok", "clear_ok",
                             "handle_audit_recorded", "attestation.identity_ok"}),
}


def matrix_ids() -> tuple:
    return tuple(r["id"] for r in ACCESS_MATRIX)


def rows_for(subject: str, phase: str, obj: str, operation: str) -> tuple:
    return tuple(r for r in ACCESS_MATRIX
                 if r["subject"] == subject and r["phase"] == phase
                 and r["object"] == obj and r["operation"] == operation)


def validate_access_matrix() -> tuple:
    """Pure validator.  Returns (ok: bool, reasons: list[str]).

    Fail-closed: any structural or semantic defect yields ok=False.
    """
    reasons: list = []

    # 1. unique ids
    ids = [r.get("id") for r in ACCESS_MATRIX]
    if len(ids) != len(set(ids)):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        reasons.append(f"DUPLICATE_ROW_IDS: {dupes}")

    # 2. expectation + witness well-formedness
    for r in ACCESS_MATRIX:
        if r.get("expected") not in (DENIED, GRANTED):
            reasons.append(f"BAD_EXPECTED[{r.get('id')}]: {r.get('expected')!r}")
        if not r.get("witness"):
            reasons.append(f"MISSING_WITNESS[{r.get('id')}]")
        elif r["witness"] not in WITNESS_FIELDS:
            reasons.append(f"UNKNOWN_WITNESS[{r.get('id')}]: {r['witness']!r}")

    # 3. the worker must NEVER be granted write-ish access to the substrate/probe
    for r in ACCESS_MATRIX:
        if (r.get("subject") == "worker"
                and r.get("object") in ("protected_substrate", "probe", "code_dir")
                and r.get("operation") in ("read", "write", "append", "rename", "delete")
                and r.get("phase") == "post_reset"
                and r.get("expected") == GRANTED):
            reasons.append(f"WORKER_GRANTED_FORBIDDEN[{r.get('id')}]")

    # 4. observer must be GRANTED read on the protected substrate post_reset
    obs = rows_for("observer", "post_reset", "protected_substrate", "read")
    if not obs or all(r.get("expected") != GRANTED for r in obs):
        reasons.append("OBSERVER_NOT_GRANTED_READ_POST_RESET")

    # 5. the runtime handle audit must be required to be RECORDED
    if not any(r.get("witness") == "handle_audit_recorded" for r in ACCESS_MATRIX):
        reasons.append("HANDLE_AUDIT_NOT_REQUIRED_RECORDED")

    # 6. 凌翼 STEP 2: the FROZEN required row set MUST all be present.
    #    (Removing a required row — e.g. a worker DENY-read row — must FAIL.)
    present_ids = set(ids)
    missing_required = [i for i in REQUIRED_MATRIX_IDS if i not in present_ids]
    if missing_required:
        reasons.append(f"REQUIRED_MATRIX_ROWS_MISSING: {missing_required}")

    # 7. 凌翼 STEP 2: every row's witness must be consistent with the row's PHASE.
    #    A post-reset probe witness may NOT serve a pre-reset row (no reuse).
    for r in ACCESS_MATRIX:
        phase = r.get("phase")
        allowed = PHASE_ALLOWED_WITNESSES.get(phase)
        if allowed is None:
            reasons.append(f"UNKNOWN_PHASE[{r.get('id')}]: {phase!r}")
            continue
        if r.get("witness") not in allowed:
            reasons.append(
                f"WITNESS_PHASE_MISMATCH[{r.get('id')}]: witness {r.get('witness')!r} "
                f"not allowed for phase {phase!r}")

    return (len(reasons) == 0, reasons)


def required_matrix_ids() -> tuple:
    """The frozen required row set (凌翼 STEP 2)."""
    return REQUIRED_MATRIX_IDS


# ---------------------------------------------------------------------------
# Selftest — pure, no OS calls, safe on any platform.
# ---------------------------------------------------------------------------

def _selftest() -> int:
    global ACCESS_MATRIX
    results = []

    def chk(name, cond):
        results.append(bool(cond))
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    ok, reasons = validate_access_matrix()
    chk("canonical matrix validates", ok)
    if not ok:
        for r in reasons:
            print("   reason:", r)

    chk("matrix has >= 8 rows", len(ACCESS_MATRIX) >= 8)
    chk("ids unique", len(matrix_ids()) == len(set(matrix_ids())))
    chk("observer read post_reset present",
        len(rows_for("observer", "post_reset", "protected_substrate", "read")) >= 1)
    chk("worker read protected present (pre+post)",
        len(rows_for("worker", "pre_reset", "protected_substrate", "read")) >= 1
        and len(rows_for("worker", "post_reset", "protected_substrate", "read")) >= 1)

    # negative controls: the validator MUST reject the malformed
    _orig = ACCESS_MATRIX

    bad_dup = tuple(list(_orig) + [dict(_orig[0])])
    ACCESS_MATRIX = bad_dup
    ok_dup, why_dup = validate_access_matrix()
    chk("negative: duplicate id detected", ok_dup is False
        and any("DUPLICATE" in w for w in why_dup))

    bad_expected = tuple(list(_orig)[:-1] + [dict(_orig[-1], expected="MAYBE")])
    ACCESS_MATRIX = bad_expected
    ok_exp, why_exp = validate_access_matrix()
    chk("negative: bad expected detected", ok_exp is False
        and any("BAD_EXPECTED" in w for w in why_exp))

    bad_witness = tuple(list(_orig)[:-1] + [dict(_orig[-1], witness="vibes")])
    ACCESS_MATRIX = bad_witness
    ok_wit, why_wit = validate_access_matrix()
    chk("negative: unknown witness detected", ok_wit is False
        and any("UNKNOWN_WITNESS" in w for w in why_wit))

    no_obs = tuple(r for r in _orig if r.get("id") != "O-READ-PROTECTED-POST")
    ACCESS_MATRIX = no_obs
    ok_obs, why_obs = validate_access_matrix()
    chk("negative: missing observer grant detected", ok_obs is False
        and any("OBSERVER_NOT_GRANTED" in w for w in why_obs))

    no_audit = tuple(r for r in _orig if r.get("witness") != "handle_audit_recorded")
    ACCESS_MATRIX = no_audit
    ok_aud, why_aud = validate_access_matrix()
    chk("negative: missing handle-audit-recorded detected", ok_aud is False
        and any("HANDLE_AUDIT_NOT_REQUIRED" in w for w in why_aud))

    # worker granted substrate read in post_reset -> must be rejected
    granted = tuple(dict(r, expected=GRANTED) if r.get("id") == "W-READ-PROTECTED-POST"
                    else r for r in _orig)
    ACCESS_MATRIX = granted
    ok_gr, why_gr = validate_access_matrix()
    chk("negative: worker-granted substrate read detected", ok_gr is False
        and any("WORKER_GRANTED_FORBIDDEN" in w for w in why_gr))

    # 凌翼 STEP 2 negative: removing a REQUIRED worker DENY-read row must FAIL
    no_pre = tuple(r for r in _orig if r.get("id") != "W-READ-PROTECTED-PRE")
    ACCESS_MATRIX = no_pre
    ok_np, why_np = validate_access_matrix()
    chk("negative: missing required worker DENY-read (pre) row detected",
        ok_np is False and any("REQUIRED_MATRIX_ROWS_MISSING" in w for w in why_np))

    # 凌翼 STEP 2 negative: reusing a post-reset witness for a pre-reset row FAILS
    reuse = tuple(dict(r, witness="attestation.verdict_ok")
                  if r.get("id") == "W-READ-PROTECTED-PRE" else r for r in _orig)
    ACCESS_MATRIX = reuse
    ok_re, why_re = validate_access_matrix()
    chk("negative: post-reset witness reused for pre-reset row detected",
        ok_re is False and any("WITNESS_PHASE_MISMATCH" in w for w in why_re))

    ACCESS_MATRIX = _orig
    ok_restore, _ = validate_access_matrix()
    chk("restored matrix validates again", ok_restore is True)

    passed = sum(1 for r in results if r)
    print(f"\nq3_access_matrix selftest: {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
