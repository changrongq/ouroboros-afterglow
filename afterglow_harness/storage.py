"""
Registered state storage — file-backed literal store + substrate register.

Physical layout (frozen):
  literal.bin    : exactly 16 bytes
  substrate.bin  : exactly 8 bytes, signed int64 little-endian

Access discipline:
  · Writers hold a writable handle ONLY during a write window; the write
    window is closed (handle closed, perms dropped) before any observation.
  · The observer reads via a separate read-only path (see observer.py).
  · Readers (affine / literal-consumer) get a read-only handle and may never
    write registered state.

All width and format violations raise HarnessError (strict; no repair).
"""

from __future__ import annotations

import os
from pathlib import Path

from harness_constants import (
    HarnessError,
    LITERAL_SIZE,
    LITERAL_ZERO,
    SUBSTRATE_SIZE,
    SUBSTRATE_ZERO,
    StateSnapshot,
    encode_substrate,
)

LITERAL_FILENAME = "literal.bin"
SUBSTRATE_FILENAME = "substrate.bin"


class RegisteredState:
    """A single arm's registered state, backed by two files in a sandbox dir.

    One arm per process. A/B/C for a given episode each live in their own
    RegisteredState (their own directory) — they are never co-resident in one
    writable mapping.
    """

    def __init__(self, sandbox_dir: str | os.PathLike):
        self.dir = Path(sandbox_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.literal_path = self.dir / LITERAL_FILENAME
        self.substrate_path = self.dir / SUBSTRATE_FILENAME
        self._write_open = False

    # -- lifecycle ---------------------------------------------------------

    def initialize_baseline(self) -> None:
        """Create both files at the canonical zero baseline."""
        self._write_bytes(self.literal_path, LITERAL_ZERO)
        self._write_bytes(self.substrate_path, SUBSTRATE_ZERO)

    def _write_bytes(self, path: Path, data: bytes) -> None:
        with open(path, "wb") as f:
            f.write(data)

    # -- raw read (observer / read-only consumers) -------------------------

    def read_literal_bytes(self) -> bytes:
        return self.literal_path.read_bytes()

    def read_substrate_bytes(self) -> bytes:
        return self.substrate_path.read_bytes()

    def snapshot(self) -> StateSnapshot:
        """Read-only snapshot for the observer. Enforces exact widths."""
        lit = self.read_literal_bytes()
        sub = self.read_substrate_bytes()
        if len(lit) != LITERAL_SIZE:
            raise HarnessError(
                f"literal.bin must be exactly {LITERAL_SIZE} bytes, got {len(lit)}"
            )
        if len(sub) != SUBSTRATE_SIZE:
            raise HarnessError(
                f"substrate.bin must be exactly {SUBSTRATE_SIZE} bytes, got {len(sub)}"
            )
        return StateSnapshot(literal=lit, q_raw=sub)

    # -- write primitives (only used inside a write window) ----------------

    def _open_write_window(self) -> None:
        if self._write_open:
            raise HarnessError("write window already open")
        self._write_open = True

    def _close_write_window(self) -> None:
        self._write_open = False

    def _assert_write_open(self) -> None:
        if not self._write_open:
            raise HarnessError("attempted write outside an open write window")

    def write_literal(self, data: bytes) -> None:
        self._assert_write_open()
        if len(data) != LITERAL_SIZE:
            raise HarnessError(
                f"literal write must be exactly {LITERAL_SIZE} bytes, got {len(data)}"
            )
        self._write_bytes(self.literal_path, data)

    def write_substrate(self, q: int) -> None:
        self._assert_write_open()
        self._write_bytes(self.substrate_path, encode_substrate(q))

    # context manager so write windows are always closed
    def write_window(self):
        state = self

        class _Win:
            def __enter__(self_inner):
                state._open_write_window()
                return state

            def __exit__(self_inner, *exc):
                state._close_write_window()
                return False

        return _Win()
