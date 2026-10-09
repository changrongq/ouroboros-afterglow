"""
KNOWN_ANSWER_PRE_RESET_PERTURBATION  (short name: J)

J is a pre-registered, per-fixture, ONE-SHOT synthetic state perturbation that
executes:
  · only in PHASE A / HARNESS VALIDATION,
  · only AFTER the S_write observation,
  · only BEFORE the S_handoff snapshot,
  · is independently observed before/after,
  · is NEVER called by RESET,
  · NEVER executes in SCIENTIFIC_EXECUTION.

J is a synthetic fault injector used to test whether the evaluator correctly
handles "the evidence later weakens / disappears". J is NOT a forgetting
mechanism. This distinction is load-bearing:

  J is  : "an artificial fault injector"
  J is not : "how our Afterglow would forget"

J modes (all four must be frozen by fixture bundle hash before the first
qualifying fixture runs; no picking a mode after seeing a result):
  IDENTITY                : literal unchanged ; q unchanged
  COLLAPSE_SIGN           : literal unchanged ; q nonzero -> +2 ; 0 -> 0
  ERASE_EFFECT            : literal -> 16 zero bytes ; q -> 0
  HALVE_AND_ERASE_LITERAL : literal -> zeros ; q in {+2->+1, -2->-1, 0->0}
"""

from __future__ import annotations

from harness_constants import (
    EXTRA_CONSTANT_VALUE,
    LITERAL_SIZE,
    LITERAL_ZERO,
    HarnessError,
    encode_substrate,
)
from storage import RegisteredState

J_NAME = "KNOWN_ANSWER_PRE_RESET_PERTURBATION"
J_SHORT = "J"
J_NAMESPACE = "HARNESS_VALIDATION_EXECUTION_ONLY"
J_SCIENTIFIC_CLAIM_ELIGIBILITY = "NONE"

IDENTITY = "IDENTITY"
COLLAPSE_SIGN = "COLLAPSE_SIGN"
ERASE_EFFECT = "ERASE_EFFECT"
HALVE_AND_ERASE_LITERAL = "HALVE_AND_ERASE_LITERAL"

J_MODES = (IDENTITY, COLLAPSE_SIGN, ERASE_EFFECT, HALVE_AND_ERASE_LITERAL)


def apply_j(state: RegisteredState, mode: str) -> None:
    """Apply J once, inside an open write window.

    Guards:
      · mode must be one of the frozen four;
      · HALVE_AND_ERASE_LITERAL is only defined on the frozen input domain
        {0, +2, -2}; any other q is a fixture execution error, not a rule
        extension.
    """
    if mode not in J_MODES:
        raise HarnessError(f"unknown J mode: {mode!r}")

    snap = state.snapshot()
    q = snap.q
    lit = snap.literal

    if mode == IDENTITY:
        return

    if mode == COLLAPSE_SIGN:
        # literal unchanged; q nonzero -> +2 ; zero -> 0
        new_q = EXTRA_CONSTANT_VALUE if q != 0 else 0
        state.write_substrate(new_q)
        return

    if mode == ERASE_EFFECT:
        state.write_literal(LITERAL_ZERO)
        state.write_substrate(0)
        return

    if mode == HALVE_AND_ERASE_LITERAL:
        if q not in (0, 2, -2):
            raise HarnessError(
                f"HALVE_AND_ERASE_LITERAL undefined off frozen domain "
                f"{{0,+2,-2}}; got q={q}"
            )
        new_q = {0: 0, 2: 1, -2: -1}[q]
        state.write_literal(LITERAL_ZERO)
        state.write_substrate(new_q)
        return

    raise HarnessError(f"unreachable J mode: {mode!r}")  # pragma: no cover
