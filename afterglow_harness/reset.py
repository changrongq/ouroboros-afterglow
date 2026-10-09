"""
Reset — PROCESS_REPLACE_PRESERVE_FILES_V1  (logic layer).

What this module does:
  · orchestrates the reset *protocol* at the Python/logic level:
      capture S_handoff (read-only) -> verify preserved bytes survive ->
      capture S_restored -> run the three-way witnesses;
  · computes the clear/preserve verification for the registered state.

What this module does NOT do (and must not pretend to do):
  · OS-level process replacement and permission isolation.
    SPEC §六 / proposal §六 require that the *actual* isolation be enforced
    by separate processes with different access rights — "仅在 Python 中约定
    不调用写函数不算隔离完成". This module therefore exposes a hook
    (external_worker_restart / access_isolation_probe) that a real deployment
    must supply; the default implementation raises NotIsolatedError.

Reset validity is a *protocol* judgement (INVALID vs valid), separate from the
scientific L2 result.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness_constants import HarnessError, StateSnapshot

RESET_PROFILE_ID = "PROCESS_REPLACE_PRESERVE_FILES_V1"
RESET_PROFILE_VERSION = "1.0"


class NotIsolatedError(HarnessError):
    """Raised when reset would proceed without real OS-level isolation."""


@dataclass
class ResetOutcome:
    reset_valid: bool
    reason: str
    handoff: StateSnapshot | None = None
    restored: StateSnapshot | None = None
    clear_side_ok: bool = False
    preserve_side_ok: bool = False
    access_side_ok: bool = False


class ResetController:
    """Logic-level reset controller.

    A real deployment must subclass / supply:
      · restart_worker()      : actually terminate + start a fresh worker with
                                reduced capabilities (no access to old temp dir,
                                no episode input, no ledger, no oracle);
      · access_probe()        : actually attempt a forbidden access and confirm
                                it is *denied* (not merely "code didn't try").
    """

    def __init__(self, literal_path: Path, substrate_path: Path):
        self.literal_path = Path(literal_path)
        self.substrate_path = Path(substrate_path)

    # -- hooks a real deployment must override ------------------------------

    def restart_worker(self) -> None:
        raise NotIsolatedError(
            "restart_worker not implemented: PROCESS_REPLACE_PRESERVE_FILES_V1 "
            "requires real OS-level process replacement, not a Python-level flag"
        )

    def access_probe(self) -> bool:
        """Return True iff a genuinely forbidden access was genuinely denied."""
        raise NotIsolatedError(
            "access_probe not implemented: access-side witness requires real "
            "permission isolation (a denied access), not a code convention"
        )

    # -- logic-level procedure ---------------------------------------------

    def capture_handoff(self) -> StateSnapshot:
        lit = self.literal_path.read_bytes()
        sub = self.substrate_path.read_bytes()
        from harness_constants import LITERAL_SIZE, SUBSTRATE_SIZE

        if len(lit) != LITERAL_SIZE or len(sub) != SUBSTRATE_SIZE:
            raise HarnessError("handoff snapshot: width violation")
        return StateSnapshot(literal=lit, q_raw=sub)

    def capture_restored(self) -> StateSnapshot:
        return self.capture_handoff()

    def verify(
        self,
        handoff: StateSnapshot,
        restored: StateSnapshot,
        clear_side_ok: bool,
        access_side_ok: bool,
    ) -> ResetOutcome:
        """Decide reset validity from the three-way witnesses."""
        preserve_ok = (
            handoff.literal == restored.literal and handoff.q_raw == restored.q_raw
        )
        if not preserve_ok:
            return ResetOutcome(
                reset_valid=False,
                reason="RESET_INVALID: preserved registered state changed across reset",
                handoff=handoff,
                restored=restored,
                clear_side_ok=clear_side_ok,
                preserve_side_ok=False,
                access_side_ok=access_side_ok,
            )
        if not clear_side_ok:
            return ResetOutcome(
                reset_valid=False,
                reason="RESET_INVALID: clear-side counterfeit signal not removed",
                handoff=handoff,
                restored=restored,
                clear_side_ok=False,
                preserve_side_ok=True,
                access_side_ok=access_side_ok,
            )
        if not access_side_ok:
            return ResetOutcome(
                reset_valid=False,
                reason="RESET_INVALID: access-side isolation not proven",
                handoff=handoff,
                restored=restored,
                clear_side_ok=clear_side_ok,
                preserve_side_ok=True,
                access_side_ok=False,
            )
        return ResetOutcome(
            reset_valid=True,
            reason="RESET_VALID: clear+preserve+access all verified",
            handoff=handoff,
            restored=restored,
            clear_side_ok=True,
            preserve_side_ok=True,
            access_side_ok=True,
        )
