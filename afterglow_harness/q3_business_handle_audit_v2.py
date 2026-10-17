"""BUSINESS_WORKER_HANDLE_AUDIT_V2 — business-integration-layer handle audit.

Lineage: part of the Q3 reset adapter INTEGRATION layer (NOT the frozen Q3 roles).
Authority: 凌翼 `HANDLE AUDIT UNRESOLVED RULING` (2026-10-15):
  MODIFY_FROZEN_Q3_HANDLE_AUDIT = NO ; NEW_INTEGRATION_AUDIT_V2 = AUTHORIZED.
This does NOT replace the frozen q3_handle_audit.py; it serves the adapter only.

WHY: the frozen `audit_process_handles_for_target()` treats the BROAD Windows kernel
"File object type" as if every such handle can be read as an ordinary-file identity,
and silently degrades to UNRESOLVED on any it cannot. A real persistent business worker
holds console-device (`\\Device\\ConDrv`) and directory handles of that broad type, so
the frozen auditor returns UNRESOLVED forever (it never reaches CLEAN), even under an
admin token. This V2 classifies MORE CAREFULLY, without name-guessing.

CLASSIFICATION RULES (凌翼, binding):
  · a handle PROVEN (by reliable OS identity) to be the target file  => FOUND_TARGET
  · ALL relevant candidate handles PROVEN non-target                 => CLEAN
  · ANY relevant candidate handle NOT reliably classifiable          => UNRESOLVED
  · process enumeration / identity read / key API error              => ERROR

FORBIDDEN (凌翼):
  · NAME_ONLY_SKIP                    (skip a handle just because its name looks odd)
  · NAME_REOPEN_AS_HANDLE_IDENTITY    (treat a reopened-by-name handle as THE handle)
  · UNKNOWN_TO_CLEAN_DOWNGRADE        (call CLEAN when something is unknown)

Identity is obtained FROM THE DUPLICATED HANDLE where possible
(GetFileInformationByHandle, then GetFileInformationByHandleEx(FileIdInfo)). A name is
used only as a DIAGNOSTIC / cross-check, never as the physical identity.
"""

from __future__ import annotations

import ctypes
import hashlib
import hmac
import os
import secrets
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path

# frozen helpers we reuse READ-ONLY (enumeration + type index + identity of a path)
import q3_handle_audit as HA


V2_FOUND_TARGET = "FOUND_TARGET"
V2_CLEAN = "CLEAN"
V2_UNRESOLVED = "UNRESOLVED"
V2_ERROR = "ERROR"

# ---------------------------------------------------------------------------
# 凌翼 `LINGYI — JIE FOUR PROPOSALS RULING` (2026-10-17) — binding, machine-readable.
#
# Item 4 says the persistent blocker is "REQUIRED IN APPLICABLE REVIEWS AND WIRING
# DECISIONS". Written as a constant so it cannot be quietly dropped from a verdict:
# every applicable handoff/report must restate PERSISTENT_WORKER_CLEAN_BLOCK.
#
# Item 2 is the operative consequence for this module: a CLEAN verdict here is scoped
# to a single enumeration of a live process, so it is a POINT-IN-TIME observation, not
# a quiescence claim. Two equal snapshots do NOT prove quiescence; two unequal ones do
# NOT prove snapshot impossibility. Until an OBSERVATION BOUNDARY is defined (see
# C_OBSERVATION_BOUNDARY_* below), no CLEAN produced here may be promoted to
# BUSINESS_CLEAN.
#
# Item 1: PROBE_CLEAN != BUSINESS_CLEAN — a verdict must name its SUBJECT and SCOPE.
# ---------------------------------------------------------------------------
LINGYI_JIE_RULING_DATE = "2026-10-17"
PERSISTENT_WORKER_CLEAN_BLOCK = "ACTIVE"

VERDICT_SUBJECT_PROBE = "PROBE"            # short-lived attested probe worker
VERDICT_SUBJECT_BUSINESS = "BUSINESS"      # persistent business worker
PROBE_CLEAN_IS_NOT_BUSINESS_CLEAN = True
PERSISTENT_BUSINESS_CLEAN = "NOT ESTABLISHED"

# Item 2 STOP CONDITION: the three things that must be defined BEFORE any snapshot
# reasoning counts. None of them is currently defined, so the gate is CLOSED.
C_QUIESCENCE_PROOF_REQUIRED_DEFINITIONS = (
    "OBSERVATION_BOUNDARY",        # what is inside vs outside the observed set
    "SNAPSHOT_COVERAGE_SEMANTICS", # what a snapshot is taken to COVER
    "TIME_SCOPE_OF_ASSURANCE",     # how long a snapshot verdict is claimed to hold
)
C_OBSERVATION_BOUNDARY_DEFINED = False
C_SNAPSHOT_COVERAGE_SEMANTICS_DEFINED = False
C_TIME_SCOPE_OF_ASSURANCE_DEFINED = False
C_TWO_SNAPSHOT_EARLY_STOP = "DIAGNOSTIC ONLY"
C_FEASIBILITY = "NOT ESTABLISHED"          # 凌翼: if no credible boundary, record this
C_CURRENT_EXPLORATION = "STOPPED"          # 凌翼: ...and STOP CURRENT EXPLORATION

# Item 3: an independently-confirmed target plus a CONTROLLED identity failure is
# UNRESOLVED, never CLEAN. Simulation is not an OS-completeness proof.
UNREADABLE_TARGET_CONTROL_RESULT = "UNRESOLVED"
UNREADABLE_TARGET_CONTROL_MAY_BE_CLEAN = False
SIMULATION_IS_COMPLETENESS_PROOF = False

# Current route (凌翼, same ruling).
ROUTE_OPTION_A = "NOT AUTHORIZED"
ROUTE_OPTION_B = "ACTIVE"
ROUTE_OPTION_C = "LIMITED FEASIBILITY ONLY"

# 睫 (2026-10-17): the two unresolved causes are NOT interchangeable. Kept here so a
# future "we granted the privilege, why is it still not CLEAN" cannot aim at the wrong
# cause. OPERATIONAL_FAILURE != ONTOLOGICAL_NO_IDENTITY.
UNRESOLVED_KIND_OPERATIONAL = "operational"
UNRESOLVED_KIND_NO_IDENTITY = "no_identity"
# 睫 (2026-10-17, second pass): a THIRD bucket is required, not preferred. The case
# "handle identity was read, but there is no target identity from the SAME API to
# compare against" used to be filed as no_identity, on the stated reasoning that
# "granting privilege cannot remove it". That reasoning was an ASSERTION, not evidence:
# `_target_identities` returned a bare {} for two different situations --
#   (a) CreateFileW(target) itself failed            -> permissions/environment, FIXABLE
#   (b) it opened but neither API applies            -> ontological, NOT fixable
# and nothing in the returned value could separate them. Filing such a case under
# no_identity fed CAUSE_IS_ONTOLOGICAL ("operation succeeded on every relevant handle")
# a sentence that can be FALSE, and it did so in the one situation where the action it
# blocks ("grant privilege once more") is exactly the action still worth trying.
UNRESOLVED_KIND_INCOMPARABLE = "incomparable"

# The instrument did not obtain a baseline. This is ONE fact about the target side, not
# N facts about N handles: if the target has no comparable identity, every handle is
# incomparable for the SAME reason. Short-circuiting is therefore both more honest and
# more informative than reporting "12 handles each had a problem".
V2_INCOMPARABLE = "INCOMPARABLE"

# CAUSE_IS_ONTOLOGICAL may be printed ONLY under this conjunction. Dropping any single
# conjunct makes the sentence capable of lying.
CAUSE_IS_ONTOLOGICAL_REQUIRES = (
    "unresolved_operational == 0",
    "unresolved_no_identity > 0",
    "unresolved_incomparable == 0",
)

# 凌翼 CLEAN_EVIDENCE_BINDING (still open): the evidence must be PRODUCED by a trusted
# verification flow, not merely a constructible dataclass. We mirror the frozen
# AccessWitness pattern: a per-process secret seals the evidence, and only the trusted
# producer (see `build_enumerator_evidence` / q3_t0_enumerator_experiment) can compute
# 凌翼: the seal is an INTEGRITY AID within the trusted-producer flow, NOT a
# cross-caller privilege boundary (this secret is a same-process module variable).
# The real guarantee is that build_enumerator_evidence ITSELF performs the OS
# verification; the auditor independently re-checks. Do not claim the HMAC alone
# isolates callers.
_ENUM_SECRET: bytes = secrets.token_bytes(32)


def _evidence_fields(ev: "EnumeratorEvidence") -> dict:
    return {
        "pid": ev.pid,
        "create_time": round(float(ev.create_time), 6),
        "benign_control_values": sorted(int(v) for v in ev.benign_control_values),
        "all_benign_seen": bool(ev.all_benign_seen),
        "method": ev.method,
        "raw_ref": ev.raw_ref,
    }


def _evidence_seal(ev: "EnumeratorEvidence") -> str:
    f = _evidence_fields(ev)
    msg = "|".join(f"{k}={f[k]}" for k in sorted(f))
    return hmac.new(_ENUM_SECRET, msg.encode("utf-8"), hashlib.sha256).hexdigest()


@dataclass
class EnumeratorEvidence:
    """Evidence that the handle enumerator OBSERVED this worker's known handles
    (凌翼 T1 scope fix: 'TARGET-HANDLE POSITIVE EVIDENCE IS NOT A CLEAN-SIDE CONTROL').

    It proves the ENUMERATOR'S OBSERVATION CAPABILITY for this pid using a SEPARATE
    BENIGN control handle (a handle to a NON-protected object the worker genuinely
    holds) — NOT a handle to the protected target. In one stable state:
        positive target evidence  => ∃h Target(h)  => FOUND_TARGET
        CLEAN                     => ¬∃h Target(h)
    are mutually exclusive, so a target-handle positive CANNOT serve as a CLEAN-side
    control. Hence the benign control.

    BOUNDARY (凌翼, consistent with R1): the benign control ONLY proves the enumerator
    can observe this worker's handles. It does NOT prove protected-object isolation —
    the AUDITOR still independently checks the REAL protected object.

    The HMAC `seal` is an INTEGRITY AID within the producer flow, NOT a cross-caller
    privilege boundary (the secret is a same-process module variable).
    """
    pid: int
    create_time: float
    benign_control_values: list           # OS-verified BENIGN handles seen by the enum
    all_benign_seen: bool                 # enumerator returned ALL benign controls
    method: str = "q3_business_handle_audit_v2:trusted_producer"
    raw_ref: str = ""
    seal: str | None = None               # set ONLY by build_enumerator_evidence

    @property
    def observation_trusted(self) -> bool:
        if self.seal is None:
            return False
        try:
            if not hmac.compare_digest(self.seal, _evidence_seal(self)):
                return False
        except Exception:                                        # noqa: BLE001
            return False
        return (isinstance(self.pid, int) and self.pid > 0
                and self.create_time > 0.0
                and bool(self.benign_control_values)
                and self.all_benign_seen is True)


def quiescence_gate(observation_boundary_defined: bool = False,
                    snapshot_coverage_semantics_defined: bool = False,
                    time_scope_of_assurance_defined: bool = False) -> dict:
    """凌翼 `JIE FOUR PROPOSALS RULING` item 2 — the gate that must be OPENED first.

    This function exists so the STOP CONDITION is EXECUTABLE rather than a sentence in
    a report. It does not gather evidence and it does not decide anything about a real
    process; it only answers "are the three definitions in place?".

    凌翼's ruling, restated as logic:
        E(t1) == E(t2)  does NOT prove quiescence
        E(t1) != E(t2)  does NOT prove snapshot impossibility
    so neither outcome of the two-snapshot comparison may be used as a proof. The
    comparison stays DIAGNOSTIC ONLY regardless of its result.

    If all three definitions are absent/unestablished, this returns
    `exploration = STOPPED` and `c_feasibility = NOT ESTABLISHED`, which is exactly
    what must be recorded rather than continuing to explore.

    NOTE: passing True here is an ASSERTION by the caller that a definition exists. It
    is not proof that the definition is credible; a reviewer must accept it. Do not
    call this with True to unblock work — that would be self-authorization.
    """
    defined = {
        "OBSERVATION_BOUNDARY": bool(observation_boundary_defined),
        "SNAPSHOT_COVERAGE_SEMANTICS": bool(snapshot_coverage_semantics_defined),
        "TIME_SCOPE_OF_ASSURANCE": bool(time_scope_of_assurance_defined),
    }
    missing = [k for k, v in defined.items() if not v]
    gate_open = not missing
    return {
        "gate": "OBSERVATION_BOUNDARY_GATE",
        "required": list(C_QUIESCENCE_PROOF_REQUIRED_DEFINITIONS),
        "defined": defined,
        "missing": missing,
        "gate_open": gate_open,
        # 凌翼: E(t1)==E(t2) does not prove quiescence; E(t1)!=E(t2) does not prove
        # snapshot impossibility. Both outcomes remain non-proof => DIAGNOSTIC ONLY.
        "two_snapshot_early_stop": C_TWO_SNAPSHOT_EARLY_STOP,
        "quiescence_proven": False if not gate_open else None,
        "c_feasibility": C_FEASIBILITY if not gate_open else "REQUIRES_REVIEW",
        "exploration": C_CURRENT_EXPLORATION if not gate_open else "MAY_CONTINUE_UNDER_REVIEW",
        "persistent_worker_clean_block": PERSISTENT_WORKER_CLEAN_BLOCK,
    }


def verify_held_handle(pid: int, handle_value: int, target_identities: dict) -> dict:
    """TRUSTED producer primitive: independently verify `handle_value` in process `pid`
    by DuplicateHandle + OS identity, COMPARED LIKE-WITH-LIKE.

    `target_identities` is a per-API map {api_name: identity_tuple} (see
    `_target_identities`), because GetFileInformationByHandle (classic) and
    GetFileInformationByHandleEx(FileIdInfo) produce DIFFERENT tuple shapes and must
    not be compared directly.

    Returns what was ACTUALLY observed. 凌翼 (D2): `duplicated` does NOT imply a
    verified identity — an UNKNOWN identity is NOT evidence of non-target. So we expose
    an explicit `identity_known` flag and only set `is_non_target` when the candidate's
    identity was read AND a SAME-API target identity exists AND they DIFFER."""
    k = _k32()
    PROCESS_DUP_HANDLE = 0x0040
    DUPLICATE_SAME_ACCESS = 0x00000002
    me = k.GetCurrentProcess()
    out = {"handle_value": int(handle_value), "duplicated": False,
           "identity": None, "identity_api": "", "identity_known": False,
           "is_target": None,      # None = UNKNOWN (not False!)
           "is_non_target": False,  # True only if comparable identities DIFFER
           "last_error": None}
    hproc = k.OpenProcess(PROCESS_DUP_HANDLE, False, pid)
    if not hproc:
        out["last_error"] = ("OpenProcess", k.GetLastError())
        return out
    try:
        dup = ctypes.c_void_p()
        if not k.DuplicateHandle(hproc, ctypes.c_void_p(int(handle_value)), me,
                                 ctypes.byref(dup), 0, False, DUPLICATE_SAME_ACCESS):
            out["last_error"] = ("DuplicateHandle", k.GetLastError())
            return out
        out["duplicated"] = True
        try:
            ident, api, _le = _identity_from_handle(dup, k)
            if ident is not None:
                out["identity"] = list(ident)
                out["identity_api"] = api
                out["identity_known"] = True
                # 凌翼 D2: compare SAME-API identities only.
                target_same_api = (target_identities or {}).get(api)
                if target_same_api is not None:
                    if tuple(ident) == tuple(target_same_api):
                        out["is_target"] = True
                        out["is_non_target"] = False
                    else:
                        out["is_target"] = False
                        out["is_non_target"] = True
                else:
                    # no same-API target identity to compare -> identity known but NOT
                    # comparable => target-ness UNKNOWN (neither target nor benign)
                    out["is_target"] = None
                    out["is_non_target"] = False
            # identity unknown stays identity_known=False, is_target=None, is_non_target=False
        finally:
            k.CloseHandle(dup)
    finally:
        k.CloseHandle(hproc)
    return out


def build_enumerator_evidence(*, pid: int, benign_handle_values, protected_path: str,
                              requester: str = "", raw_ref: str = "") -> EnumeratorEvidence:
    """TRUSTED PRODUCER for a CLEAN-SIDE BENIGN CONTROL (凌翼 T1 scope fix).

    It proves the enumerator OBSERVES this worker's handles, using SEPARATE BENIGN
    handles (handles to objects that are NOT the protected target). The producer itself:
      1. reads the pid's OS create_time (GetProcessTimes);
      2. obtains the PROTECTED object's OS identity VIA BOTH APIS (same-API compare);
      3. for EACH candidate benign handle value: DuplicateHandle(pid, hv) + identity;
         a value counts as BENIGN only if its identity was actually READ (identity_known)
         AND a SAME-API target identity exists AND they DIFFER (is_non_target). An
         UNKNOWN identity, or an identity with no comparable target, is NOT benign;
      4. enumerates the pid itself and checks which benign values the enumerator returns;
      5. sets `all_benign_seen` from THAT observation (never from the caller).

    The caller may only propose candidate benign handle values; the producer decides.
    A caller cannot assert `all_benign_seen`. (The HMAC seal is an integrity aid, not a
    cross-caller boundary.)
    """
    target_identities, _target_reason = _target_identities(str(protected_path))
    os_ct = _process_create_time(pid)
    if not target_identities or os_ct is None:
        return EnumeratorEvidence(pid=int(pid), create_time=float(os_ct or 0.0),
                                  benign_control_values=[], all_benign_seen=False,
                                  method="q3_business_handle_audit_v2:build(failed)",
                                  raw_ref=raw_ref, seal=None)

    benign = []
    for hv in benign_handle_values or []:
        v = verify_held_handle(pid, int(hv), target_identities)
        # 凌翼 D2: duplicated != verified benign; require identity_known AND a SAME-API
        # target identity that DIFFERS (is_non_target). UNKNOWN identity is NOT benign.
        if v.get("duplicated") and v.get("identity_known") and v.get("is_non_target"):
            benign.append(int(hv))

    try:
        seen = {int(hv) for hv, _tp, _acc in HA._iter_handles(pid)}
    except Exception:                                            # noqa: BLE001
        seen = set()
    all_benign_seen = bool(benign) and all(v in seen for v in benign)

    ev = EnumeratorEvidence(pid=int(pid), create_time=float(os_ct),
                            benign_control_values=sorted(set(benign)),
                            all_benign_seen=all_benign_seen,
                            method="q3_business_handle_audit_v2:trusted_producer",
                            raw_ref=raw_ref, seal=None)
    ev.seal = _evidence_seal(ev)
    return ev


# device name prefixes: 凌翼 says these names are DIAGNOSTIC ONLY and NOT sufficient
# for CLEAN without a reliable OS device-property corroboration. We keep the prefixes
# ONLY for the diagnostic record; they no longer downgrade a handle to 'positively
# non-file' for the CLEAN verdict.
_KNOWN_NON_FILE_DEVICE_PREFIXES = (
    "\\Device\\ConDrv",      # console driver
    "\\Device\\NamedPipe\\",
    "\\Device\\Nsi",
    "\\Device\\Afd",
    "\\Device\\KsecDD",
)


@dataclass
class V2HandleRecord:
    handle_value: int
    granted_access: int
    type_index: int
    openprocess_ok: bool = False
    duplicate_ok: bool = False
    identity_api: str = ""                 # which API produced the identity (if any)
    file_identity: tuple | None = None
    name: str | None = None                # diagnostic only
    classification: str = ""               # target | non_target_known_device | ...
    unresolved_reason: str = ""
    # 睫 (2026-10-17): which of the two disjoint causes produced the unresolved.
    #   "operational" = we failed to operate (permissions / duplicate / enumeration)
    #   "no_identity" = we operated but the object carries no readable file identity
    #   ""            = not classified as unresolved
    unresolved_kind: str = ""
    getlasterror: dict = field(default_factory=dict)


@dataclass
class V2AuditResult:
    pid: int
    status: str
    target_path: str
    target_identity: tuple | None = None
    file_type_index: int | None = None
    records: list = field(default_factory=list)
    matched: list = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    detail: str = ""
    # 凌翼 `JIE FOUR PROPOSALS RULING` item 1: BIND SUBJECT + SCOPE TO VERDICT.
    # A verdict that does not say WHO it is about and WHAT it covers is not conclusive.
    #   subject = PROBE  (short-lived attested probe worker) or BUSINESS (persistent)
    #   scope   = POINT_IN_TIME_SINGLE_ENUMERATION  (this module never claims more)
    subject: str = VERDICT_SUBJECT_BUSINESS
    scope: str = "POINT_IN_TIME_SINGLE_ENUMERATION"
    # Item 1: PROBE_CLEAN != BUSINESS_CLEAN. A PROBE-subject CLEAN must never be
    # aggregated into a business-isolation claim.
    promotable_to_business_clean: bool = False
    # Item 4: required in every applicable verdict, so it cannot be dropped.
    persistent_worker_clean_block: str = PERSISTENT_WORKER_CLEAN_BLOCK
    # 睫 (2026-10-17): WHY the target baseline has (or lacks) identities. Without this
    # the caller cannot distinguish a fixable permission failure from an ontological
    # "no API applies" case -- the two used to collapse into a bare {}.
    target_identity_reason: str = ""


def _process_create_time(pid: int) -> float | None:
    """OS-measured process creation time (for independent create_time re-check)."""
    try:
        from win32_isolation import _process_times
        ct, _ = _process_times(pid)
        return ct
    except Exception:                                            # noqa: BLE001
        return None


def _k32():
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.DuplicateHandle.restype = wintypes.BOOL
    k.DuplicateHandle.argtypes = [
        wintypes.HANDLE, ctypes.c_void_p, wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p),
        wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.GetFileInformationByHandle.restype = wintypes.BOOL
    k.GetFileInformationByHandle.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(HA.BY_HANDLE_FILE_INFORMATION)]
    k.GetFileInformationByHandleEx.restype = wintypes.BOOL
    k.GetFileInformationByHandleEx.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                               ctypes.c_void_p, wintypes.DWORD]
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    k.GetCurrentProcess.restype = wintypes.HANDLE
    k.GetCurrentProcess.argtypes = []
    k.GetLastError.restype = wintypes.DWORD
    return k


class _FILE_ID_INFO(ctypes.Structure):
    _fields_ = [("VolumeSerialNumber", ctypes.c_ulonglong),
                ("FileId", ctypes.c_ubyte * 16)]


FileIdInfo = 18  # FILE_INFO_BY_HANDLE_CLASS


TARGET_IDENTITIES_OK = "OK"
TARGET_IDENTITIES_CREATEFILE_FAILED = "CREATEFILE_FAILED"
TARGET_IDENTITIES_OPENED_NO_API = "OPENED_NO_API"


def _target_identities(target_path: str) -> tuple:
    """Compute the target's identity via BOTH APIs, so a remote handle's identity
    (obtained via whichever API works on it) can be compared LIKE-WITH-LIKE.

    Returns ``(identities, reason)`` where ``identities`` is ``{api_name: identity}``
    and ``reason`` is one of:

        "OK"                        -- at least one API produced an identity
        "CREATEFILE_FAILED:<err>"   -- we could not OPEN the target at all (permissions
                                       / environment). FIXABLE: granting privilege may
                                       make this go away.
        "OPENED_NO_API"             -- we opened the target but NEITHER API yielded an
                                       identity. ONTOLOGICAL: more privilege cannot help.

    睫 (2026-10-17): before this change the function returned a bare ``{}`` for BOTH
    cases, so the caller could not tell "we never got a baseline because we lack
    permission" from "the APIs do not apply to this object". That conflation is exactly
    the T1 contract violation `UNKNOWN != NON_TARGET`, applied to the TARGET side.

    The reason string is the whole point: an empty dict carries no field saying WHY it
    is empty, so any downstream sentence that asserts a cause is asserting something
    the code never observed.
    """
    k = _k32()
    GENERIC_READ = 0x80000000
    FILE_SHARE_ALL = 0x7
    OPEN_EXISTING = 3
    FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    k.CreateFileW.restype = ctypes.c_void_p
    k.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_ulong, ctypes.c_ulong,
                              ctypes.c_void_p, ctypes.c_ulong, ctypes.c_ulong,
                              ctypes.c_void_p]
    out = {}
    h = k.CreateFileW(str(target_path), GENERIC_READ, FILE_SHARE_ALL, None,
                      OPEN_EXISTING, FILE_FLAG_BACKUP_SEMANTICS, None)
    if not h or h == -1:
        return out, f"{TARGET_IDENTITIES_CREATEFILE_FAILED}:{k.GetLastError()}"
    try:
        # GetFileInformationByHandle (classic)
        info = HA.BY_HANDLE_FILE_INFORMATION()
        if k.GetFileInformationByHandle(ctypes.c_void_p(h), ctypes.byref(info)):
            out["GetFileInformationByHandle"] = (
                info.dwVolumeSerialNumber, info.nFileIndexHigh, info.nFileIndexLow)
        # GetFileInformationByHandleEx(FileIdInfo)
        fid = _FILE_ID_INFO()
        if k.GetFileInformationByHandleEx(ctypes.c_void_p(h), FileIdInfo,
                                          ctypes.byref(fid), ctypes.sizeof(fid)):
            out["GetFileInformationByHandleEx:FileIdInfo"] = _fmt_file_id(fid)
    finally:
        k.CloseHandle(ctypes.c_void_p(h))
    return (out, TARGET_IDENTITIES_OK) if out else (out, TARGET_IDENTITIES_OPENED_NO_API)


def _fmt_file_id(fid: "_FILE_ID_INFO") -> tuple:
    """Normalise FILE_ID_INFO to (VolumeSerialNumber, FileId128-as-int)."""
    fo = bytes(fid.FileId)
    return (fid.VolumeSerialNumber, int.from_bytes(fo[:8], "little")
            | (int.from_bytes(fo[8:], "little") << 64))


def _identity_from_handle(dup, k) -> tuple:
    """Return (identity_tuple|None, api_used, getlasterror_dict). Identity from the
    DUPLICATED handle (never from a reopened-by-name handle). Tries, in order:
       1. GetFileInformationByHandle            (classic: vol + file index)
       2. GetFileInformationByHandleEx(FileIdInfo)  (works with fewer rights / dirs)
    """
    lasterr = {}
    info = HA.BY_HANDLE_FILE_INFORMATION()
    if k.GetFileInformationByHandle(dup, ctypes.byref(info)):
        return ((info.dwVolumeSerialNumber, info.nFileIndexHigh, info.nFileIndexLow),
                "GetFileInformationByHandle", lasterr)
    lasterr["GetFileInformationByHandle"] = k.GetLastError()

    fid = _FILE_ID_INFO()
    if k.GetFileInformationByHandleEx(dup, FileIdInfo, ctypes.byref(fid),
                                      ctypes.sizeof(fid)):
        return (_fmt_file_id(fid), "GetFileInformationByHandleEx:FileIdInfo", lasterr)
    lasterr["GetFileInformationByHandleEx"] = k.GetLastError()
    return (None, "", lasterr)


def audit_business_worker_handles(pid: int, target_path: str,
                                  enumerator_evidence: "EnumeratorEvidence | None" = None
                                  ) -> V2AuditResult:
    """V2 audit: classify each File-type handle of `pid` against the target file.

    凌翼 T1 scope: a CLEAN verdict requires `enumerator_evidence` — a BENIGN
    enumerator-observation control produced by the trusted producer
    (`build_enumerator_evidence`), proving the enumerator observes this worker's own
    handles. It is NOT a target-handle positive (that would be FOUND_TARGET). Without
    trusted observation evidence, a would-be CLEAN is DOWNGRADED to UNRESOLVED
    (UNKNOWN_TO_CLEAN_DOWNGRADE = FORBIDDEN). The benign control does NOT prove
    protected-object isolation; the auditor independently checks the real object.

    Returns a V2AuditResult whose `status` is one of the four V2_* verdicts.
    """
    res = V2AuditResult(pid=pid, status=V2_ERROR, target_path=str(Path(target_path).resolve()))
    k = _k32()
    PROCESS_DUP_HANDLE = 0x0040
    DUPLICATE_SAME_ACCESS = 0x00000002
    me = k.GetCurrentProcess()

    try:
        target_ids, target_reason = _target_identities(target_path)
        res.target_identity = next(iter(target_ids.values()), None)
        res.target_identity_reason = target_reason
        if not target_ids:
            # 睫 (2026-10-17): SHORT-CIRCUIT. The instrument never obtained a baseline.
            # Reporting N per-handle verdicts here would dress up ONE failure as N
            # failures, and would attribute to the handles a defect that lives entirely
            # on the target side. INCOMPARABLE is the honest verdict: "I did not
            # obtain a baseline", not "each handle had a problem".
            res.status = V2_INCOMPARABLE
            res.scope = "NO_BASELINE_OBTAINED"
            if target_reason.startswith(TARGET_IDENTITIES_CREATEFILE_FAILED):
                why = ("CREATEFILE_FAILED is an OPERATIONAL failure: more privilege "
                       "may fix it (FIXABLE).")
            else:
                why = ("OPENED_NO_API means neither identity API applies to this "
                       "object even though it opened (ONTOLOGICAL: privilege cannot "
                       "help).")
            res.detail = (
                f"target baseline NOT obtained (reason={target_reason}); audit "
                f"short-circuited to INCOMPARABLE -- no per-handle classification was "
                f"performed, and the handle count is deliberately NOT reported as N "
                f"separate errors. " + why)
            res.counts = {"file_type_total": 0, "found_target": 0, "known_non_file": 0,
                          "non_target_proven": 0, "unresolved": 0,
                          "unresolved_operational": 0, "unresolved_no_identity": 0,
                          "unresolved_incomparable": 0, "openprocess_fail": 0,
                          "duplicate_fail": 0, "enum_error": 0,
                          "short_circuited": True, "target_identity_reason": target_reason}
            return res
        file_type = HA._file_type_index(target_path)
        res.file_type_index = file_type
        if file_type is None:
            res.status = V2_ERROR
            res.detail = "cannot determine File object-type index"
            return res

        # 睫 (2026-10-17) asked for the two unresolved causes to be counted
        # SEPARATELY, because they mean different things:
        #   unresolved_operational  = we FAILED TO OPERATE (OpenProcess denied by
        #                             ordinary permissions, DuplicateHandle failed,
        #                             enumeration error). Environmental; may be
        #                             fixable by granting privilege.
        #   unresolved_no_identity  = we OPERATED but the object has NO FILE
        #                             IDENTITY to read (device objects such as
        #                             \Device\ConDrv / KsecDD / CNG). Ontological;
        #                             no amount of privilege makes it readable.
        # Consequence 睫 named: if unresolved_operational == 0 while
        # unresolved_no_identity > 0, the conclusion does NOT hold on this object
        # and "just fix the permissions" is the WRONG direction. Collapsing the two
        # into one number invites exactly that misreading once privileges are given
        # and the number still refuses to reach 0.
        #
        # `unresolved` is retained as the SUM so existing readers keep the same
        # total; the CLEAN branch is sensitive ONLY to the two split counters.
        counts = {"file_type_total": 0, "found_target": 0, "known_non_file": 0,
                  "non_target_proven": 0, "unresolved": 0,
                  "unresolved_operational": 0, "unresolved_no_identity": 0,
                  "unresolved_incomparable": 0,
                  "openprocess_fail": 0,
                  "duplicate_fail": 0, "enum_error": 0}
        try:
            handles = list(HA._iter_handles(pid))
        except Exception as e:                                    # noqa: BLE001
            res.status = V2_ERROR
            res.detail = f"handle enumeration error: {type(e).__name__}: {e}"
            res.counts = counts
            return res
        # every handle value the enumerator returned THIS run (for evidence re-check)
        seen_handles = {int(hv) for hv, _tp, _acc in handles}

        for hv, tp, acc in handles:
            if tp != file_type:
                continue
            counts["file_type_total"] += 1
            rec = V2HandleRecord(handle_value=hv, granted_access=acc, type_index=tp)
            hproc = k.OpenProcess(PROCESS_DUP_HANDLE, False, pid)
            if not hproc:
                rec.getlasterror["OpenProcess"] = k.GetLastError()
                rec.classification = "unresolved"
                rec.unresolved_reason = "OpenProcess(PROCESS_DUP_HANDLE) failed"
                rec.unresolved_kind = "operational"
                counts["openprocess_fail"] += 1
                counts["unresolved_operational"] += 1
                counts["unresolved"] += 1
                res.records.append(rec)
                continue
            rec.openprocess_ok = True
            try:
                dup = ctypes.c_void_p()
                if not k.DuplicateHandle(hproc, ctypes.c_void_p(hv), me,
                                         ctypes.byref(dup), 0, False, DUPLICATE_SAME_ACCESS):
                    rec.getlasterror["DuplicateHandle"] = k.GetLastError()
                    rec.classification = "unresolved"
                    rec.unresolved_reason = "DuplicateHandle failed"
                    rec.unresolved_kind = "operational"
                    counts["duplicate_fail"] += 1
                    counts["unresolved_operational"] += 1
                    counts["unresolved"] += 1
                    res.records.append(rec)
                    continue
                rec.duplicate_ok = True
                try:
                    ident, api, lasterr = _identity_from_handle(dup, k)
                    rec.getlasterror.update(lasterr)
                    rec.identity_api = api
                    rec.file_identity = ident
                    if ident is not None:
                        # a REAL identity obtained. Compare LIKE-WITH-LIKE: the target
                        # identity must come from the SAME API (凌翼: don't mix APIs).
                        target_same_api = target_ids.get(api)
                        if target_same_api is None:
                            # this API never produced a target identity => cannot decide
                            rec.classification = "unresolved"
                            rec.unresolved_reason = (f"handle identity via {api} but target "
                                                     f"has no {api} identity to compare")
                            rec.unresolved_kind = "incomparable"
                            counts["unresolved_incomparable"] += 1
                            counts["unresolved"] += 1
                            res.records.append(rec)
                            continue
                        if ident == target_same_api:
                            rec.classification = "target"
                            counts["found_target"] += 1
                            res.matched.append(f"{hv:#x}:{api}:{ident}")
                        else:
                            rec.classification = "non_target_proven"
                            counts["non_target_proven"] += 1
                        res.records.append(rec)
                        continue
                    # identity NOT obtainable from the handle -> get a name for DIAGNOSIS
                    try:
                        rec.name = HA._name_of_remote_handle(pid, hv)
                    except Exception:                             # noqa: BLE001
                        rec.name = None
                    # 凌翼: NAME-ONLY DEVICE CLASSIFICATION IS NOT SUFFICIENT FOR CLEAN.
                    # A console-device / pipe / dir NAME is DIAGNOSTIC ONLY and cannot,
                    # by itself, prove the handle is non-target. Such a handle without a
                    # reliable OS identity is therefore UNRESOLVED (fail-closed), NOT a
                    # 'positively non-file' skip.
                    if rec.name:
                        rec.classification = "unresolved"
                        rec.unresolved_reason = (
                            f"no identity from handle (both APIs failed); name={rec.name!r} "
                            f"is diagnostic only and cannot alone prove non-target")
                    else:
                        rec.classification = "unresolved"
                        rec.unresolved_reason = "no identity from handle and no name"
                    # both APIs operated successfully but the object yields no file
                    # identity => ONTOLOGICAL, not an operation failure.
                    rec.unresolved_kind = "no_identity"
                    counts["unresolved_no_identity"] += 1
                    counts["unresolved"] += 1
                    res.records.append(rec)
                finally:
                    k.CloseHandle(dup)
            finally:
                k.CloseHandle(hproc)
        res.counts = counts

        if res.matched:
            res.status = V2_FOUND_TARGET
            res.detail = f"worker holds handle(s) to target: {res.matched}"
        elif counts["unresolved"] > 0:
            res.status = V2_UNRESOLVED
            # 睫: state the two causes SEPARATELY so a future "we granted the
            # privilege, why is it still not CLEAN" question cannot be pointed at the
            # wrong cause.
            res.detail = (f"{counts['unresolved']} relevant handle(s) could not be "
                          f"reliably classified (fail-closed): "
                          f"unresolved_operational={counts['unresolved_operational']} "
                          f"(operation refused/by permissions), "
                          f"unresolved_no_identity={counts['unresolved_no_identity']} "
                          f"(object carries no readable file identity), "
                          f"unresolved_incomparable={counts['unresolved_incomparable']} "
                          f"(handle identity read, but no like-API target baseline)")
            # 睫 (2026-10-17): ALL THREE conjuncts are required. With only the first
            # two, an incomparable case would print "operation succeeded on every
            # relevant handle", which is FALSE -- the failure is on the TARGET side
            # and may well be a permission problem that more privilege would fix.
            if (counts["unresolved_operational"] == 0
                    and counts["unresolved_no_identity"] > 0
                    and counts["unresolved_incomparable"] == 0):
                res.detail += (
                    "; CAUSE_IS_ONTOLOGICAL: operation succeeded on every relevant handle, "
                    "so granting further privilege cannot move this to CLEAN — the "
                    "conclusion does not hold on this object")
            elif counts["unresolved_incomparable"] > 0:
                res.detail += (
                    "; CAUSE_IS_INCOMPARABLE: the target baseline is missing for at least "
                    "one API -- this is ONE fact about the instrument, not N independent "
                    "handle defects; do not read it as evidence about the target's "
                    "isolation")
        else:
            # 凌翼 T1 scope: CLEAN needs a BENIGN enumerator-observation control (NOT a
            # target-handle positive, which would itself be FOUND_TARGET). The auditor
            # independently re-checks: (1) observation evidence is sealed/trusted;
            # (2) pid matches; (3) its create_time == the OS-measured create_time of THIS
            # process; (4) its BENIGN control handle values were actually seen this run.
            # The benign control proves ONLY that the enumerator observes this worker's
            # handles — it does NOT prove protected-object isolation.
            ev = enumerator_evidence
            ev_ok = False
            ev_detail = "no enumerator observation evidence"
            if ev is not None and getattr(ev, "observation_trusted", False) and ev.pid == pid:
                os_ct = _process_create_time(pid)
                ct_match = (os_ct is not None
                            and abs(float(os_ct) - float(ev.create_time)) < 1e-3)
                benign_seen = all(int(v) in seen_handles
                                  for v in (ev.benign_control_values or []))
                if ct_match and benign_seen:
                    ev_ok = True
                    ev_detail = (f"benign enumerator control verified via {ev.method}; "
                                 f"create_time match; benign controls re-seen")
                else:
                    ev_detail = (f"observation evidence NOT confirmed: create_time_match="
                                 f"{ct_match} (os={os_ct} ev={ev.create_time}); "
                                 f"benign_controls_re_seen={benign_seen}")
            elif ev is not None:
                ev_detail = ("observation evidence present but not trusted (seal/fields) "
                             "or pid mismatch")
            if not ev_ok:
                res.status = V2_UNRESOLVED
                res.detail = ("would be CLEAN on the handles seen, BUT " + ev_detail
                              + " => fail-closed (not CLEAN). NOTE: a benign control "
                              "proves observation capability only, NOT isolation.")
            else:
                res.status = V2_CLEAN
                res.detail = (f"all {counts['file_type_total']} File-type handles positively "
                              f"classified non-target (proven_non_target="
                              f"{counts['non_target_proven']}); {ev_detail} (benign "
                              f"control does NOT itself prove isolation); "
                              f"SCOPE={res.scope} subject={res.subject} "
                              f"-- this is NOT a quiescence claim: handles opened after "
                              f"this enumeration are outside it; "
                              f"PERSISTENT_WORKER_CLEAN_BLOCK={PERSISTENT_WORKER_CLEAN_BLOCK!r}")
                # 凌翼 item 1: a BUSINESS-subject CLEAN is still scoped to this single
                # enumeration and is NOT promoted to PERSISTENT_BUSINESS_CLEAN (which
                # remains NOT ESTABLISHED). Never True.
                res.promotable_to_business_clean = False
        return res
    except Exception as e:                                        # noqa: BLE001
        res.status = V2_ERROR
        res.detail = f"{type(e).__name__}: {e}"
        return res
