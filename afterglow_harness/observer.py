"""
Independent state observer.

The observer is a read-only component that is NOT the write operator. It
collects registered state by reading STATE_FIELDS from the files directly and
computing state identities independently. Writer-reported digests are never
treated as evidence.

Requirements (SPEC §11 / proposal §四):
  observer != write operator
  observer cannot write registered substrate
  observer reads canonical STATE_FIELDS independently
  observer computes state identities independently
"""

from __future__ import annotations

from pathlib import Path

from harness_constants import StateSnapshot
from storage import RegisteredState

STATE_OBSERVER_ID = "SYNTHETIC_OBSERVER_V1"
STATE_OBSERVER_VERSION = "1.0"


class StateObserver:
    """Read-only observer over a RegisteredState sandbox."""

    def __init__(self, state: RegisteredState):
        self._state = state

    def snapshot(self) -> StateSnapshot:
        """Collect a read-only snapshot and its canonical digest."""
        return self._state.snapshot()

    def digest(self) -> str:
        return self.snapshot().digest

    # The observer has no method that writes registered state.
    # (No write handles are held here.)


def snapshot_paths(literal_path: str | Path, substrate_path: str | Path) -> StateSnapshot:
    """Observer helper: snapshot directly from file paths.

    Useful when the observer runs in a separate process than the writer.
    """
    lit = Path(literal_path).read_bytes()
    sub = Path(substrate_path).read_bytes()
    from harness_constants import HarnessError, LITERAL_SIZE, SUBSTRATE_SIZE

    if len(lit) != LITERAL_SIZE:
        raise HarnessError(f"literal.bin must be exactly {LITERAL_SIZE} bytes")
    if len(sub) != SUBSTRATE_SIZE:
        raise HarnessError(f"substrate.bin must be exactly {SUBSTRATE_SIZE} bytes")
    return StateSnapshot(literal=lit, q_raw=sub)
