"""
Read paths (readers / consumers).

Two registered read paths, kept separate and never merged:

  REGISTERED_AFTERGLOW_READ_PATH
      substrate.bin -> SYNTHETIC_AFFINE_READER_V1 -> neutral future computation
      R(q, u) = u + q/2

  REGISTERED_LITERAL_READ_PATH
      literal.bin   -> LITERAL_CONSUMER_V1 -> neutral future computation
      L(literal, u) = u + SUM(unsigned_byte_i, i = 0..15)

Shared rules for BOTH paths:
  · read-only: never write registered state;
  · the operand file must be EXACTLY its fixed width (whole-file length check,
    not merely "read N bytes"); a 9-byte substrate file is an error;
  · no access to the other operand (q-reader cannot read literal; literal
    consumer cannot read q), no access to class label / ledger / oracle /
    phase;
  · NO fallback / repair / clamp / normalization / missing-file => 0;
  · exact integer/ rational output; never take float formatting as evidence;
  · output is NOT a C1/C2/C3 outcome, NOT an attribution result, NOT a
    persistence criterion — it only witnesses a live registered read path.
"""

from __future__ import annotations

from fractions import Fraction
from pathlib import Path

from harness_constants import (
    HarnessError,
    LITERAL_SIZE,
    SUBSTRATE_SIZE,
    decode_substrate,
)

# ---------------------------------------------------------------------------
# Read operator identities (versions/hashes filled after implementation)
# ---------------------------------------------------------------------------

READ_OPERATOR_ID = "SYNTHETIC_AFFINE_READER_V1"
READ_OPERATOR_VERSION = "1.0"

LITERAL_CONSUMER_ID = "LITERAL_CONSUMER_V1"
LITERAL_CONSUMER_VERSION = "1.0"


def _read_exact_whole_file(path: Path, expected: int, what: str) -> bytes:
    """Read a file enforcing whole-file exact length (no truncation, no tail)."""
    raw = path.read_bytes()
    if len(raw) != expected:
        raise HarnessError(
            f"{what} file must be exactly {expected} bytes, got {len(raw)}"
        )
    return raw


# ---------------------------------------------------------------------------
# REGISTERED_AFTERGLOW_READ_PATH
# ---------------------------------------------------------------------------


def affine_read(substrate_path: str | Path, u: int) -> Fraction:
    """R(q, u) = u + q/2, returned as an exact Fraction.

    The reader reads exactly 8 bytes little-endian signed int64.
    """
    raw = _read_exact_whole_file(Path(substrate_path), SUBSTRATE_SIZE, "substrate")
    q = decode_substrate(raw)
    # exact rational: (2u + q) / 2
    return Fraction(2 * u + q, 2)


# ---------------------------------------------------------------------------
# REGISTERED_LITERAL_READ_PATH
# ---------------------------------------------------------------------------


def literal_consume(literal_path: str | Path, u: int) -> int:
    """L(literal, u) = u + SUM(unsigned_byte_i, i = 0..15), exact integer.

    The consumer reads exactly 16 bytes. It does not read q, class, ledger,
    oracle or phase, and never writes state.
    """
    raw = _read_exact_whole_file(Path(literal_path), LITERAL_SIZE, "literal")
    return u + sum(raw)  # sum over unsigned byte values


# ---------------------------------------------------------------------------
# Neutral future computation (witness only)
# ---------------------------------------------------------------------------


def neutral_future_computation_afterglow(substrate_path: str | Path) -> dict:
    """Run the neutral probe set over the Afterglow read path.

    Returns exact values (as strings/numerators) for each neutral probe.
    This witnesses that substrate.bin participates in a future computation.
    """
    out = {}
    for u in (0, 2):
        val = affine_read(substrate_path, u)
        out[u] = {"numerator": val.numerator, "denominator": val.denominator}
    return out


def neutral_future_computation_literal(literal_path: str | Path) -> dict:
    """Run the neutral probe set over the Literal read path."""
    out = {}
    for u in (0, 2):
        out[u] = literal_consume(literal_path, u)
    return out
