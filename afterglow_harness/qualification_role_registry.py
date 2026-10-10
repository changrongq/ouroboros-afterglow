"""
qualification_role_registry.py — the SINGLE bound canonical role registry (RC9).

凌翼 R2: split the role table into EXECUTION/QUALIFICATION-CRITICAL roles vs
BUILD_PROVENANCE, and make ONE data-only registry that BOTH the build side
(manifest_bind) and the runtime side (qualification_binding) read.

This file contains DATA ONLY — no judgement logic. It is itself an
EXECUTION_CRITICAL role and has its own hash.

Invariant the preflight must prove:
    registry.EXECUTION_CRITICAL_ROLES
        ==  MANIFEST parsed EXECUTION_CRITICAL_ROLES
        ==  actual required qualification files
    exact equality, non-empty.
"""

from __future__ import annotations

# Roles whose bytes can change a qualification decision => MUST be bound and
# verified. (Non-empty by construction; an empty set must FAIL.)
EXECUTION_CRITICAL_ROLES = (
    # core components
    "harness_constants.py",
    "storage.py",
    "writers.py",
    "readers.py",
    "observer.py",
    "perturbation_j.py",
    "reset.py",
    "evaluator.py",
    "fixtures.py",
    # qualification runtime
    "fixture_contracts.py",
    "evidence_contract.py",
    "evidence_bundle.py",
    "replay_adapter.py",
    "qualification_role_registry.py",
    "qualification_binding.py",
    "run_known_answer_suite.py",
    "qualify_phase_a.py",
    "verify_manifest_binding.py",
    # qualification-critical acceptance tools (凌翼: these are NOT provenance)
    "adversarial_regression.py",
    "recompute_from_ledger.py",
)

# Tools that produce/package the frozen artifact but do NOT decide qualification.
# Recorded for audit only; a change here does NOT invalidate a frozen MANIFEST.
BUILD_PROVENANCE = (
    "manifest_bind.py",
    "freeze_manifest.py",
)


def execution_critical_roles() -> frozenset:
    return frozenset(EXECUTION_CRITICAL_ROLES)


def build_provenance_roles() -> frozenset:
    return frozenset(BUILD_PROVENANCE)
