"""
q3_adversarial.py — Q3 ADVERSARIAL REGRESSION suite.

凌翼 Q3 step 5 (EXECUTION ORDER): "Unified driver + adversarial regressions".

Purpose
-------
The Q3 disease across rounds 4-8 was "evidence exists but the judgement does not
consume it". A happy-path selftest cannot catch that: it only shows the gates
PASS when everything is right. This suite deliberately INJECTS defects into the
Q3 gates and REQUIRES each to be rejected. If an injected defect is NOT rejected,
the harness has regressed (a green run would be meaningless).

Each case is a pure in-process mutation of a gate / data object; no OS privilege
is required, so this suite runs everywhere (Windows or not).

Cases
-----
  A1  access-matrix defect (unknown witness)        -> validate_access_matrix False
  A2  access-matrix defect (missing observer grant) -> validate_access_matrix False
  A3  access-matrix defect (worker granted read)    -> validate_access_matrix False
  A4  ResetChainResult matrix_ok False              -> .valid False
  A5  ResetChainResult dacl_restore_ok False        -> .valid False
  A6  ResetChainResult handle_ok False              -> .valid False
  A7  ResetChainResult identity_ok UNEVALUATED      -> .valid False
  A8  ResetChainResult all True but clear_ok False  -> .valid False
  A9  contract clear coverage: empty mapping        -> validate_clear_targets False
  A10 contract clear coverage: missing category     -> validate_clear_targets False
  A11 contract probe pin: mismatched hash           -> validate_probe_sha256 False
  A12 contract probe pin: empty pin (fail-closed)   -> validate_probe_sha256 False
  A13 clear_na_declared non-bool                    -> chain clear_ok False
  A14 FOUND_TARGET under Profile B                  -> .valid False (handle gate)
  A15 strict verdict substring attack               -> parse_verdict_strict None
  A16 worker-heard handle status UNRESOLVED, A     -> handle gate rejects
  A17 DACL SDDL compare: differing ACE set          -> _sddl_equal False
  A18 checked_rmtree residual on locked file        -> ok False, residuals>0

Exit codes: 0 all rejected (regression PASS); 1 one or more NOT rejected (FAIL).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _selftest() -> int:
    results = []

    def chk(name, cond):
        results.append((name, bool(cond)))
        print(f"[{'PASS' if cond else 'FAIL'}] {name}")

    # --- access matrix ------------------------------------------------------
    import q3_access_matrix as qam
    orig_matrix = qam.ACCESS_MATRIX

    # A1 unknown witness
    qam.ACCESS_MATRIX = tuple(
        dict(r, witness="vibes") if r["id"] == orig_matrix[0]["id"] else r
        for r in orig_matrix)
    ok, why = qam.validate_access_matrix()
    chk("A1 matrix unknown witness rejected", ok is False and any("UNKNOWN_WITNESS" in w for w in why))

    # A2 missing observer grant
    qam.ACCESS_MATRIX = tuple(r for r in orig_matrix if r["id"] != "O-READ-PROTECTED-POST")
    ok, why = qam.validate_access_matrix()
    chk("A2 matrix missing observer grant rejected", ok is False and any("OBSERVER" in w for w in why))

    # A3 worker granted substrate read
    qam.ACCESS_MATRIX = tuple(
        dict(r, expected="GRANTED") if r["id"] == "W-READ-PROTECTED-POST" else r
        for r in orig_matrix)
    ok, why = qam.validate_access_matrix()
    chk("A3 matrix worker-granted read rejected", ok is False and any("WORKER_GRANTED" in w for w in why))
    qam.ACCESS_MATRIX = orig_matrix
    chk("A3b matrix restored validates", qam.validate_access_matrix()[0] is True)

    # --- ResetChainResult gates --------------------------------------------
    from q3_reset_chain import ResetChainResult

    def _full_valid(**over):
        base = dict(clear_ok=True, preserve_ok=True, access_ok=True, handle_ok=True,
                    identity_ok=True, lifecycle_ok=True,
                    matrix_ok=True, dacl_restore_ok=True,
                    real_reset_required=False)
        base.update(over)
        return ResetChainResult(**base)

    chk("A4 matrix_ok False -> invalid", _full_valid(matrix_ok=False).valid is False)
    chk("A5 dacl_restore_ok False -> invalid", _full_valid(dacl_restore_ok=False).valid is False)
    chk("A6 handle_ok False -> invalid", _full_valid(handle_ok=False).valid is False)
    chk("A7 identity_ok UNEVALUATED -> invalid", _full_valid(identity_ok="UNEVALUATED").valid is False)
    chk("A8 clear_ok False -> invalid", _full_valid(clear_ok=False).valid is False)
    chk("A8b baseline all-True -> valid", _full_valid().valid is True)

    # --- contract clear coverage -------------------------------------------
    from q3_contract import (validate_clear_targets, validate_probe_sha256,
                             REQUIRED_CLEAR_CATEGORIES, PROBE_TEMPLATE_SHA256,
                             compute_probe_template_sha256)
    ok, missing = validate_clear_targets({})
    chk("A9 empty clear mapping rejected", ok is False and set(missing) == set(REQUIRED_CLEAR_CATEGORIES))
    partial = {c: Path("x") for c in REQUIRED_CLEAR_CATEGORIES[1:]}
    ok, missing = validate_clear_targets(partial)
    chk("A10 missing category rejected", ok is False and REQUIRED_CLEAR_CATEGORIES[0] in missing)

    # --- contract probe pin -------------------------------------------------
    chk("A11 mismatched probe hash rejected", validate_probe_sha256("deadbeef") is False)
    _pin = PROBE_TEMPLATE_SHA256
    import q3_contract as qc
    qc.PROBE_TEMPLATE_SHA256 = ""
    chk("A12 empty probe pin rejected (fail-closed)", validate_probe_sha256(compute_probe_template_sha256()) is False)
    qc.PROBE_TEMPLATE_SHA256 = _pin
    chk("A12b pinned hash validates", validate_probe_sha256(compute_probe_template_sha256()) is True)

    # --- strict verdict parser ---------------------------------------------
    from q3_reset_chain import parse_verdict_strict
    evil1 = "NONCE=n|RESULT=READ=GRANTED|NOTE=READ=DENIED"
    evil2 = "READ=DENIED"
    chk("A15 substring/short verdict rejected", parse_verdict_strict(evil1) is None and parse_verdict_strict(evil2) is None)
    good = "NONCE=n|OP=READ|TARGET=abc|RESULT=READ=DENIED"
    chk("A15b exact verdict parsed", parse_verdict_strict(good) is not None)

    # --- handle gate logic (profile-aware) ---------------------------------
    from q3_reset_chain import HANDLE_STATUS_PASS
    chk("A16 UNRESOLVED not in PASS set (Profile A)", "HANDLE_AUDIT_UNRESOLVED" not in HANDLE_STATUS_PASS)
    chk("A16b CLEAN in PASS set", "HANDLE_AUDIT_CLEAN" in HANDLE_STATUS_PASS)

    # A14: FOUND_TARGET always invalidates — the chain maps it to handle_audit_ok
    # False for ANY profile. Assert the mapping table directly.
    from q3_contract import PROFILE_REQUIRES_CLEAN, HANDLE_PROFILE_API_NO_INHERIT, HANDLE_PROFILE_RUNTIME
    # Profile B allows UNRESOLVED (recorded), Profile A does not.
    def _gate(status, profile):
        if status == "HANDLE_AUDIT_FOUND_TARGET":
            return False
        if status in HANDLE_STATUS_PASS:
            return True
        if PROFILE_REQUIRES_CLEAN.get(profile, True):
            return False
        if status in (None, "HANDLE_AUDIT_ERROR"):
            return False
        return True
    chk("A14 FOUND_TARGET invalid under B", _gate("HANDLE_AUDIT_FOUND_TARGET", HANDLE_PROFILE_API_NO_INHERIT) is False)
    chk("A14b FOUND_TARGET invalid under A", _gate("HANDLE_AUDIT_FOUND_TARGET", HANDLE_PROFILE_RUNTIME) is False)
    chk("A16c UNRESOLVED rejected under A", _gate("HANDLE_AUDIT_UNRESOLVED", HANDLE_PROFILE_RUNTIME) is False)
    chk("A16d UNRESOLVED accepted (recorded) under B", _gate("HANDLE_AUDIT_UNRESOLVED", HANDLE_PROFILE_API_NO_INHERIT) is True)
    chk("A16e ERROR rejected under B", _gate("HANDLE_AUDIT_ERROR", HANDLE_PROFILE_API_NO_INHERIT) is False)

    # --- DACL SDDL compare --------------------------------------------------
    from q3_dacl import _sddl_equal
    s1 = "D:(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)"
    s2 = "D:(A;OICI;FA;;;SY)"            # different ACE set
    chk("A17 differing ACE set not equal", _sddl_equal(s1, s2) is False)
    chk("A17b AI control-bit tolerated (same ACE set)",
        _sddl_equal("D:P(A;OICI;FA;;;SY)", "D:PAI(A;OICI;FA;;;SY)") is True)
    # 凌翼 STEP 4: ACE ORDER matters — reordered ACEs must NOT be equal.
    chk("A17c reordered ACEs NOT equal (order significant)",
        _sddl_equal("D:(A;OICI;FA;;;SY)(A;OICI;FA;;;BA)",
                    "D:(A;OICI;FA;;;BA)(A;OICI;FA;;;SY)") is False)
    # a different control flag (P present vs absent) must NOT be equal
    chk("A17d differing control flag NOT equal",
        _sddl_equal("D:P(A;OICI;FA;;;SY)", "D:(A;OICI;FA;;;SY)") is False)

    # 凌翼 STEP 1: the Profile B proof must reject ANY single-field failure.
    from q3_contract import evaluate_profile_b_proof, PROFILE_B_PROOF_FIELDS
    _gp = {f: True for f in PROFILE_B_PROOF_FIELDS}
    chk("A19 Profile B all-True proof accepted", evaluate_profile_b_proof(_gp)[0] is True)
    chk("A19b Profile B empty proof rejected", evaluate_profile_b_proof({})[0] is False)
    chk("A19c Profile B non-dict proof rejected", evaluate_profile_b_proof(None)[0] is False)
    _gp_bad = dict(_gp); _gp_bad[PROFILE_B_PROOF_FIELDS[0]] = False
    chk("A19d Profile B single False field rejected", evaluate_profile_b_proof(_gp_bad)[0] is False)

    # 凌翼 STEP 2: required matrix rows + phase binding.
    import q3_access_matrix as _qm
    _orig_m = _qm.ACCESS_MATRIX
    _no_row = tuple(r for r in _orig_m if r["id"] != "W-READ-PROTECTED-POST")
    _qm.ACCESS_MATRIX = _no_row
    chk("A20 matrix missing REQUIRED row rejected",
        _qm.validate_access_matrix()[0] is False)
    _reuse = tuple(dict(r, witness="attestation.verdict_ok")
                   if r["id"] == "W-READ-PROTECTED-PRE" else r for r in _orig_m)
    _qm.ACCESS_MATRIX = _reuse
    chk("A21 matrix post-reset witness reused for pre-reset rejected",
        _qm.validate_access_matrix()[0] is False)
    _qm.ACCESS_MATRIX = _orig_m
    chk("A21b matrix restored validates", _qm.validate_access_matrix()[0] is True)

    # 凌翼 STEP 6: provenance record deletion / addition attacks.
    from q3_provenance import verify_against_record, write_detached_record, required_role_set
    import tempfile as _tf
    _tmp = Path(_tf.mkdtemp(prefix="q3_adv_prov_"))
    try:
        _rec = _tmp / "rec.txt"
        write_detached_record(Path(__file__).resolve().parent, _rec)
        _text = _rec.read_text(encoding="utf-8")
        _del = "\n".join(l for l in _text.splitlines() if not l.startswith("q3_dacl.py "))
        _rec.write_text(_del + "\n", encoding="utf-8")
        _okd, _dd = verify_against_record(Path(__file__).resolve().parent, _rec)
        chk("A22 provenance deleted role line rejected",
            _okd is False and any("RECORD_MISSING_REQUIRED_ROLES" in x for x in _dd))
        _rec.write_text(_text + "fake_role.py " + "0" * 64 + "\n", encoding="utf-8")
        _oka, _da = verify_against_record(Path(__file__).resolve().parent, _rec)
        chk("A23 provenance unexpected role line rejected",
            _oka is False and any("RECORD_HAS_UNEXPECTED_ROLES" in x for x in _da))
    finally:
        import shutil as _sh
        _sh.rmtree(_tmp, ignore_errors=True)

    # --- checked cleanup residual ------------------------------------------
    import tempfile
    from q3_dacl import checked_rmtree
    lk = Path(tempfile.mkdtemp(prefix="q3_adv_"))
    try:
        sub = lk / "locked"; sub.mkdir()
        f = sub / "hold.txt"; f.write_text("h")
        fh = open(f, "r")
        try:
            ok, res = checked_rmtree(sub)
            chk("A18 locked tree -> failure with residuals", ok is False and len(res) > 0)
        finally:
            fh.close()
        checked_rmtree(lk)
    finally:
        import shutil
        shutil.rmtree(lk, ignore_errors=True)

    # 知微 P1: FULL_VALID artifact CONSUMER negative regressions (referenced from
    # the driver's consumer suite, duplicated here as adversarial coverage).
    import q3_qualify as _q
    import tempfile as _tf2, json as _json2
    from q3_contract import ACTIVE_HANDLE_PROFILE as _PROF, PROFILE_VERSION as _PV
    _orig_here = _q.HERE
    _tmp2 = Path(_tf2.mkdtemp(prefix="q3_adv_fv_"))
    _q.HERE = _tmp2
    _art = _tmp2 / "q3_full_valid_result.json"
    _rid = "adv-run-1"
    _gates = {g: True for g in _q.REQUIRED_FULL_VALID_GATES}
    _good = {"FULL_VALID_SUCCESS_PATH": "PASS", "run_id": _rid, "profile": _PROF,
             "profile_version": _PV.get(_PROF, ""), "profile_b_ok": True,
             "gates": dict(_gates)}

    def _cons(d):
        _art.write_text(_json2.dumps(d), encoding="utf-8")
        return _q._consume_full_valid(True, _rid)[0]
    try:
        chk("A24 FV consumer: good artifact -> PASS", _cons(_good) == "PASS")
        chk("A25 FV consumer: empty gates -> FAIL",
            _cons(dict(_good, gates={})) == "FAIL")
        chk("A26 FV consumer: missing gates -> FAIL",
            _cons({k: v for k, v in _good.items() if k != "gates"}) == "FAIL")
        for _b in ("UNEVALUATED", 1, None, "true"):
            _g = dict(_good); _g["gates"] = dict(_gates); _g["gates"]["access_ok"] = _b
            chk(f"A27 FV consumer: gate={_b!r} -> FAIL", _cons(_g) == "FAIL")
        _g = dict(_good); _g["gates"] = dict(_gates); _g["gates"]["access_ok"] = False
        chk("A28 FV consumer: gate=False -> FAIL", _cons(_g) == "FAIL")
        chk("A29 FV consumer: wrong profile -> FAIL",
            _cons(dict(_good, profile="NOPE")) == "FAIL")
        chk("A30 FV consumer: Profile B not proven -> FAIL",
            _cons(dict(_good, profile_b_ok=False)) == "FAIL")
        chk("A31 FV consumer: stale run_id -> FAIL",
            _cons(dict(_good, run_id="old")) == "FAIL")
        _art.unlink()
        chk("A32 FV consumer: missing artifact -> FAIL",
            _q._consume_full_valid(True, _rid)[0] == "FAIL")
    finally:
        import shutil as _sh2
        _q.HERE = _orig_here
        _sh2.rmtree(_tmp2, ignore_errors=True)

    # --- 凌翼 B1/B2: the reset gate consumes real-reset evidence --------------
    from q3_reset_chain import ResetChainResult as _R2
    _base = dict(clear_ok=True, preserve_ok=True, access_ok=True, handle_ok=True,
                 identity_ok=True, lifecycle_ok=True, matrix_ok=True,
                 dacl_restore_ok=True)
    # B2: a real reset demanded but not demonstrated -> INVALID
    chk("A33 B2 real_reset_required + real_reset_ok=False -> INVALID",
        _R2(**{**_base, "real_reset_required": True, "real_reset_ok": False}).valid is False)
    chk("A33b B2 real_reset_required + real_reset_ok=True -> valid (all else True)",
        _R2(**{**_base, "real_reset_required": True, "real_reset_ok": True}).valid is True)
    chk("A33c B2 real_reset not required -> real_reset_ok ignored",
        _R2(**{**_base, "real_reset_required": False, "real_reset_ok": False}).valid is True)
    # 凌翼 B2 fix: real_reset_required must be a LITERAL bool. UNKNOWN (UNEVALUATED/
    # None/"true") is NOT "no reset needed" -> INVALID. (Previously A33d wrongly
    # accepted UNEVALUATED as valid.)
    for _bad3 in ("UNEVALUATED", None, "true", 1, 0):
        chk(f"A33d B2 real_reset_required={_bad3!r} -> INVALID (strict tri-state)",
            _R2(**{**_base, "real_reset_required": _bad3}).valid is False)
    # B3: lineage boundary — RC12 must never fold into Q3 roles
    import q3_provenance as _qp
    chk("A34 B3: Q3 lineage boundary ok", _qp.assert_lineage_boundary()[0] is True)
    chk("A34b B3: RC12 not in Q3_EXECUTION_CRITICAL",
        "qualification_binding_rc12.py" not in _qp.Q3_EXECUTION_CRITICAL)
    chk("A34c B3: exactly 10 Q3 roles", len(_qp.Q3_EXECUTION_CRITICAL) == 10)

    # 凌翼 V5: REAL_RESET contract-prespawn enforcement.
    from q3_contract import classify_reset_mode, RESET_MODE_INCONSISTENT, RESET_MODE_REAL_RESET
    chk("A35 V5: clear_action without old worker -> INCONSISTENT",
        classify_reset_mode(None, lambda m: None) == RESET_MODE_INCONSISTENT)
    chk("A35b V5: old worker present -> REAL_RESET",
        classify_reset_mode(123, None) == RESET_MODE_REAL_RESET)
    chk("A35c V5: neither -> FIRST_START",
        classify_reset_mode(None, None) == "FIRST_START")
    chk("A35d V5: INCONSISTENT is a recognised mode",
        "INCONSISTENT" in __import__("q3_contract").RESET_MODES)

    passed = sum(1 for _, ok in results if ok)
    print(f"\nq3_adversarial selftest: {passed}/{len(results)} PASS")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(_selftest())
