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
        "verified_handle_values": sorted(int(v) for v in ev.verified_handle_values),
        "all_verified_seen": bool(ev.all_verified_seen),
        "method": ev.method,
        "raw_ref": ev.raw_ref,
    }


def _evidence_seal(ev: "EnumeratorEvidence") -> str:
    msg = "|".join(f"{k}={_evidence_fields(ev)[k]}" for k in sorted(_evidence_fields(ev)))
    return hmac.new(_ENUM_SECRET, msg.encode("utf-8"), hashlib.sha256).hexdigest()


@dataclass
class EnumeratorEvidence:
    """Evidence, produced by the TRUSTED PRODUCER `build_enumerator_evidence(...)`,
    that specific handle values are OS-verified to refer to the target AND were seen by
    the enumerator this round (凌翼 TRUSTED_EVIDENCE_ORIGIN).

    IMPORTANT (凌翼): the HMAC `seal` is an INTEGRITY AID within the producer flow —
    it is NOT a cross-caller privilege boundary (the secret is a same-process module
    variable). The real guarantee is that the PRODUCER ITSELF performed the OS
    verification (DuplicateHandle + identity) and set `all_verified_seen` from its own
    enumeration; the AUDITOR then independently re-checks create_time + re-seen values.
    Do NOT rely on the seal as proof that the caller was trusted.
    """
    pid: int
    create_time: float
    verified_handle_values: list          # OS-verified (DuplicateHandle+identity) values
    all_verified_seen: bool               # producer observed the enumerator return ALL
    method: str = "q3_business_handle_audit_v2:trusted_producer"
    raw_ref: str = ""                     # path/ref to the raw observation
    seal: str | None = None               # set ONLY by build_enumerator_evidence

    @property
    def trusted(self) -> bool:
        # Integrity of the fields (seal) — an aid, NOT a trust boundary. The auditor
        # additionally re-checks create_time against the OS and re-seen handle values.
        if self.seal is None:
            return False
        try:
            if not hmac.compare_digest(self.seal, _evidence_seal(self)):
                return False
        except Exception:                                        # noqa: BLE001
            return False
        return (isinstance(self.pid, int) and self.pid > 0
                and self.create_time > 0.0
                and bool(self.verified_handle_values)
                and self.all_verified_seen is True)


def verify_held_handle(pid: int, handle_value: int,
                       target_identity) -> dict:
    """TRUSTED producer primitive: independently verify that `handle_value` in process
    `pid` refers to the target (by DuplicateHandle + OS identity). Returns a dict with
    what was ACTUALLY observed — never a caller assertion. 凌翼: the producer must
    PERFORM the OS verification, not accept it."""
    k = _k32()
    PROCESS_DUP_HANDLE = 0x0040
    DUPLICATE_SAME_ACCESS = 0x00000002
    me = k.GetCurrentProcess()
    out = {"handle_value": int(handle_value), "duplicated": False, "identity": None,
           "is_target": False, "last_error": None}
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
            out["identity"] = list(ident) if ident else None
            out["identity_api"] = api
            out["is_target"] = (ident is not None and ident == target_identity)
        finally:
            k.CloseHandle(dup)
    finally:
        k.CloseHandle(hproc)
    return out


def build_enumerator_evidence(*, pid: int, target_path: str,
                              worker_reported_handle_values, requester: str = "",
                              raw_ref: str = "") -> EnumeratorEvidence:
    """TRUSTED PRODUCER (凌翼: 'TRUSTED PRODUCER MUST PERFORM OS VERIFICATION; DO NOT
    ACCEPT CALLER-ASSERTED ALL_VERIFIED_SEEN').

    The producer itself, inside this call:
      1. reads the pid's OS create_time (GetProcessTimes);
      2. obtains the target's OS identity;
      3. for EACH worker-reported handle value: DuplicateHandle(pid, hv) + identity;
         a value counts as VERIFIED only if the OS identity == target identity;
      4. enumerates the pid itself and checks which verified values the enumerator
         returns;
      5. sets `all_verified_seen` from THAT observation (never from the caller).

    The caller supplies only the candidate (worker-reported) handle values and the
    target path; everything else is observed here. The seal is an integrity aid within
    this flow — 凌翼: it is NOT a cross-caller privilege boundary.
    """
    k = _k32()
    target_identity = HA.file_identity(str(target_path))
    os_ct = _process_create_time(pid)
    if target_identity is None or os_ct is None:
        # cannot observe -> return an UNSIGNED (untrusted) evidence rather than fake it
        return EnumeratorEvidence(pid=int(pid), create_time=float(os_ct or 0.0),
                                  verified_handle_values=[], all_verified_seen=False,
                                  method="q3_business_handle_audit_v2:build(failed)",
                                  raw_ref=raw_ref, seal=None)

    verified = []
    for hv in worker_reported_handle_values or []:
        v = verify_held_handle(pid, int(hv), target_identity)
        if v.get("duplicated") and v.get("is_target"):
            verified.append(int(hv))

    # enumerate the pid OURSELVES and see which verified values appear this run
    try:
        seen = {int(hv) for hv, _tp, _acc in HA._iter_handles(pid)}
    except Exception:                                            # noqa: BLE001
        seen = set()
    all_verified_seen = bool(verified) and all(v in seen for v in verified)

    ev = EnumeratorEvidence(pid=int(pid), create_time=float(os_ct),
                            verified_handle_values=sorted(set(verified)),
                            all_verified_seen=all_verified_seen,
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


def _target_identities(target_path: str) -> dict:
    """Compute the target's identity via BOTH APIs, so a remote handle's identity
    (obtained via whichever API works on it) can be compared LIKE-WITH-LIKE.
    Returns {api_name: identity_tuple} — only APIs that succeeded are present."""
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
        return out
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
    return out


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

    凌翼: `CALLER BOOLEAN IS NOT SUFFICIENT`. A CLEAN verdict requires
    `enumerator_evidence` — a TRUSTED, pid-bound EnumeratorEvidence produced by a
    trusted completeness check (q3_t0_enumerator_experiment), NOT a caller's own
    assertion. Without it, a would-be CLEAN is DOWNGRADED to UNRESOLVED
    (UNKNOWN_TO_CLEAN_DOWNGRADE = FORBIDDEN).

    Returns a V2AuditResult whose `status` is one of the four V2_* verdicts.
    """
    res = V2AuditResult(pid=pid, status=V2_ERROR, target_path=str(Path(target_path).resolve()))
    k = _k32()
    PROCESS_DUP_HANDLE = 0x0040
    DUPLICATE_SAME_ACCESS = 0x00000002
    me = k.GetCurrentProcess()

    try:
        target_ids = _target_identities(target_path)   # {api: identity}
        res.target_identity = next(iter(target_ids.values()), None)
        if not target_ids:
            res.status = V2_ERROR
            res.detail = "cannot read target file identity via any API"
            return res
        file_type = HA._file_type_index(target_path)
        res.file_type_index = file_type
        if file_type is None:
            res.status = V2_ERROR
            res.detail = "cannot determine File object-type index"
            return res

        counts = {"file_type_total": 0, "found_target": 0, "known_non_file": 0,
                  "non_target_proven": 0, "unresolved": 0, "openprocess_fail": 0,
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
                counts["openprocess_fail"] += 1
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
                    counts["duplicate_fail"] += 1
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
            res.detail = (f"{counts['unresolved']} relevant handle(s) could not be "
                          f"reliably classified (fail-closed)")
        else:
            # 凌翼 UNKNOWN_TO_CLEAN_DOWNGRADE = FORBIDDEN, and CLEAN_EVIDENCE_BINDING:
            # CLEAN requires (1) a SEALED, trusted EnumeratorEvidence; (2) its pid ==
            # this audit's pid; (3) its create_time == the OS-measured create_time of
            # THIS process (independent re-check); (4) its verified handle values were
            # ACTUALLY seen in THIS run's enumeration. A caller-built object fails (1).
            ev = enumerator_evidence
            ev_ok = False
            ev_detail = "no enumerator evidence"
            if ev is not None and getattr(ev, "trusted", False) and ev.pid == pid:
                os_ct = None
                try:
                    os_ct = _process_create_time(pid)
                except Exception:                                # noqa: BLE001
                    os_ct = None
                ct_match = (os_ct is not None
                            and abs(float(os_ct) - float(ev.create_time)) < 1e-3)
                seen_all = all(int(v) in seen_handles
                               for v in (ev.verified_handle_values or []))
                if ct_match and seen_all:
                    ev_ok = True
                    ev_detail = (f"sealed evidence from {ev.method}; create_time match; "
                                 f"verified handles re-seen in this run")
                else:
                    ev_detail = (f"evidence NOT confirmed: create_time_match={ct_match} "
                                 f"(os={os_ct} ev={ev.create_time}); "
                                 f"verified_handles_re_seen={seen_all}")
            elif ev is not None:
                ev_detail = "evidence present but not trusted (seal/fields) or pid mismatch"
            if not ev_ok:
                res.status = V2_UNRESOLVED
                res.detail = ("would be CLEAN on the handles seen, BUT " + ev_detail
                              + " => fail-closed (not CLEAN)")
            else:
                res.status = V2_CLEAN
                res.detail = (f"all {counts['file_type_total']} File-type handles positively "
                              f"classified non-target (proven_non_target="
                              f"{counts['non_target_proven']}); {ev_detail}")
        return res
    except Exception as e:                                        # noqa: BLE001
        res.status = V2_ERROR
        res.detail = f"{type(e).__name__}: {e}"
        return res
