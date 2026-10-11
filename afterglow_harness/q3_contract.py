"""
q3_contract.py — Q3 FROZEN CONTRACT for required evidence (Windows / Win32).

STATUS: SELF-CONTAINED PoC contract. NOT wired into the frozen Phase A harness.

凌翼 R3 / 睫 BD-68: "冻结可执行合同。权限矩阵、必需 clear targets、N/A 资格、worker
身份、可信 probe hash，全部由独立合同决定，不能由调用方临时改写。"
知微: "required_clear_targets 与 clear_na_declared 目前仍由调用者作为普通参数提供，
并非由已冻结的 Q3 合同强制决定。"

This module is DATA-ONLY: it is the single frozen source of what a Q3 reset run
MUST clear, which handle-isolation proof profile applies, and the trusted-probe
identity. The driver takes these from HERE, not from ad-hoc caller arguments.

Rule (凌翼/睫): an EMPTY required clear set does NOT pass, unless the contract
explicitly declares NOT_APPLICABLE. "Unlisted target = NOT AUDITED", never
"cleared".
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Frozen profile identity
# ---------------------------------------------------------------------------

Q3_PROFILE_ID = "Q3_RESET_PROFILE_WIN32_ACL_V1"
Q3_PROFILE_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Handle-isolation proof profiles (凌翼 R2: preregistered; no post-hoc N/A)
# ---------------------------------------------------------------------------
#
# RUNTIME_HANDLE_AUDIT   : requires a full runtime handle enumeration == CLEAN.
# API_NO_INHERIT_PROFILE : evidence = create-API no-inherit + STARTUPINFO +
#                          inheritable-channel checks + a leak positive control.
#                          UNRESOLVED stays UNRESOLVED (never rewritten to CLEAN).
#
# 凌翼 R2 explicitly FORBIDS: converting observed UNRESOLVED to CLEAN, or
# assigning N/A after seeing the result.

HANDLE_PROFILE_RUNTIME = "RUNTIME_HANDLE_AUDIT"
HANDLE_PROFILE_API_NO_INHERIT = "API_NO_INHERIT_PROFILE"

#: Profile versions (preregistered; a run records the version used).
PROFILE_VERSION = {
    HANDLE_PROFILE_RUNTIME: "1.0",
    HANDLE_PROFILE_API_NO_INHERIT: "1.0",
}

#: The ACTIVE profile for this contract. Chosen BEFORE execution; a run MUST NOT
#: switch profiles after seeing a result (凌翼 Q3).
#:
#: 凌翼 Q3: Profile A (RUNTIME_HANDLE_AUDIT) needs a full runtime enumeration to
#: return CLEAN; Profile B (API_NO_INHERIT_PROFILE) proves a NARROWER claim —
#: "the new worker did not INHERIT a forbidden handle from the controller". B does
#: NOT prove "the worker holds no target handle by any other means". While an
#: environment cannot reach A's CLEAN, B is the reachable path; we therefore set
#: the ACTIVE profile to B, with its narrower scope stated explicitly.
ACTIVE_HANDLE_PROFILE = HANDLE_PROFILE_API_NO_INHERIT

#: Per-profile CLAIM (the exact proposition proven) — must be echoed verbatim.
PROFILE_CLAIM = {
    HANDLE_PROFILE_RUNTIME:
        "At the audit time point, the worker holds NO handle to the protected "
        "object (full runtime enumeration status == CLEAN).",
    HANDLE_PROFILE_API_NO_INHERIT:
        "The NEW worker did NOT INHERIT a forbidden-juxtaposed handle from the "
        "controller (create-API + STARTUPINFO/inheritable-channel checks + leak "
        "positive control). It does NOT assert that the worker can never obtain "
        "the handle by other means (opened before deny, explicit DuplicateHandle).",
}

#: Scope text (must be echoed in any result claiming validity).
PROFILE_SCOPE = {
    HANDLE_PROFILE_RUNTIME:
        "runtime handle audit CLEAN; UNRESOLVED/ERROR => INVALID.",
    HANDLE_PROFILE_API_NO_INHERIT:
        "inherited-handle isolation only; runtime_handle_audit stays UNRESOLVED "
        "and is recorded as-is (never rewritten to CLEAN); FOUND_TARGET always INVALID.",
}

#: The ONLY runtime-audit statuses a profile may use as PASS (凌翼 Q3/BD-65).
PROFILE_REQUIRES_CLEAN = {
    HANDLE_PROFILE_RUNTIME: True,       # A: needs runtime CLEAN
    HANDLE_PROFILE_API_NO_INHERIT: False,   # B: does NOT claim runtime CLEAN
}

#: Preregistered acceptance conditions for Profile B (must ALL hold).
PROFILE_B_ACCEPTANCE = (
    "registered actual process-creation API is checked",
    "STARTUPINFO + std handles + reserved fields + inheritable channels checked",
    "controller open handles to forbidden objects are NOT passed to the worker",
    "a deliberate handle-leak POSITIVE CONTROL is detected by the probe",
    "worker token SID / old-worker termination / new process creation verified",
    "real access denial verified (bound probe, strict schema)",
    "observer independent reads of S_handoff/S_restored + clear/preserve verified",
    "profile_selection happens BEFORE worker spawn (no post-hoc switch)",
    "if runtime audit returns FOUND_TARGET -> INVALID even under B",
)

#: Finite trust boundary (凌翼 Q10) — echoed in any frozen scope statement.
TRUST_ROOT = (
    "preregistered contract + hash",
    "trusted controller / observer",
    "OS process identity + access control",
    "bound executable code",
    "independently observed raw events",
)
TRUST_VALIDATION = (
    "byte/hash consistency",
    "required witness consumption",
    "positive and negative controls",
    "no unresolved mandatory evidence",
    "no authority self-certification",
)
TRUSTED_COMPUTING_BASE = (
    "the running Windows OS, the trusted controller, and the authorized execution "
    "environment are the declared trusted computing base. We do NOT prove the "
    "Windows kernel itself is flawless (out of Q3's engineering threat model)."
)

# ---------------------------------------------------------------------------
# REQUIRED CLEAR TARGETS (frozen; caller may only SHRINK, never define)
# ---------------------------------------------------------------------------
#
# A Q3 reset run MUST declare what it clears. The contract names the REQUIRED
# categories. Concrete paths are supplied per-run but MUST cover the required
# categories; a run that supplies an empty set (and does not declare NOT_APPLICABLE
# in the contract) is INVALID (BD-66/BD-68).

REQUIRED_CLEAR_CATEGORIES = (
    "counterfeit_signal",       # the declared-cleared input-side signal
    "episode_input_path",       # episode reinjection path
    "temporary_buffers",        # temp runtime buffers
)

#: Per-run NOT_APPLICABLE declaration must be an explicit bool tied to a category
#: the contract permits as N/A. Empty by default: every category is REQUIRED.
CONTRACT_NOT_APPLICABLE_ALLOWED = frozenset()

# ---------------------------------------------------------------------------
# Trusted probe identity (frozen; the worker must not be able to substitute it)
# ---------------------------------------------------------------------------

#: The trusted probe TEMPLATE is frozen here (identity = its bytes' SHA-256).
#: The driver renders parameters into THIS template; it does not accept an
#: arbitrary probe file. (凌翼 P1-3 / 睫 BD-73: the contract must CONTAIN the
#: pinned hash, not just a name.)
PROBE_TEMPLATE_ID = "Q3_BOUND_FORBIDDEN_ACCESS_PROBE_V1"

#: Pinned SHA-256 of the trusted probe TEMPLATE SOURCE (the PROBE_TEMPLATE string
#: in q3_reset_chain). 睫 BD-73: this value lives HERE; the driver reads it and
#: does NOT accept probe_sha_expected as a caller parameter. While it is empty the
#: run MUST be treated as NOT_EVALUATED (never PASS) — fail-closed.
PROBE_TEMPLATE_SHA256 = "1750b843722366aaf7f95150fd4da32fdfd465fbb3cd9eda94f38e7f142e10f4"

#: Source of the trusted probe template (single frozen module: this is data).
PROBE_TEMPLATE_SOURCE = "q3_reset_chain.PROBE_TEMPLATE"


def compute_probe_template_sha256() -> str:
    """SHA-256 of the canonical probe template SOURCE text (the code the worker
    must execute). Computed the same way at freeze time and at run time."""
    import hashlib
    from q3_reset_chain import PROBE_TEMPLATE
    return hashlib.sha256(PROBE_TEMPLATE.encode("utf-8")).hexdigest()


def required_clear_categories() -> tuple:
    return REQUIRED_CLEAR_CATEGORIES


def active_handle_profile() -> str:
    return ACTIVE_HANDLE_PROFILE


def profile_scope_text(profile: str | None = None) -> str:
    return PROFILE_SCOPE.get(profile or ACTIVE_HANDLE_PROFILE, "<unknown profile>")


def validate_clear_targets(provided: dict) -> tuple[bool, list]:
    """BD-72: the contract itself validates the caller's coverage.

    Returns (ok, missing). `provided` maps category -> path. A category is
    covered iff present AND mapped to a non-empty path. The driver MUST call
    this; not calling it (or ignoring `ok`) => INVALID.
    """
    if not isinstance(provided, dict):
        return False, list(REQUIRED_CLEAR_CATEGORIES)
    missing = []
    for cat in REQUIRED_CLEAR_CATEGORIES:
        if cat not in provided or not provided[cat]:
            missing.append(cat)
    return (len(missing) == 0), missing


def validate_probe_sha256(actual: str) -> bool:
    """BD-73: the executed probe's template-source hash must equal the pinned
    hash. False while PROBE_TEMPLATE_SHA256 is unset (fail-closed)."""
    if not PROBE_TEMPLATE_SHA256:
        return False
    return actual == PROBE_TEMPLATE_SHA256
