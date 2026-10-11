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

#: The ACTIVE profile for this frozen contract. Chosen BEFORE execution.
ACTIVE_HANDLE_PROFILE = HANDLE_PROFILE_RUNTIME

#: Public scope text (must be echoed in any result claiming validity).
PROFILE_SCOPE = {
    HANDLE_PROFILE_RUNTIME:
        "worker holds NO handle to the protected object, verified by full "
        "runtime enumeration (status CLEAN).",
    HANDLE_PROFILE_API_NO_INHERIT:
        "the CREATE API used does not inherit handles; OS inheritable-channel "
        "checks pass; a leak positive control is detected. This does NOT prove "
        "the worker holds no handle by other means (e.g. opened before deny, "
        "explicit DuplicateHandle injection); scope is limited accordingly.",
}

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
