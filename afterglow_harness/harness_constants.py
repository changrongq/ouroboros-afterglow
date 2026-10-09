"""
AFTERGLOW REFERENCE HARNESS — shared constants and canonical rules.

This module defines the FROZEN constants and canonical encoding rules used by
every other harness component. Nothing here may vary between fixtures.

Bound by:
  REFERENCE_HARNESS_SPEC_HASH = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33
  PARENT_PREREG_SHA256        = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4

Design rules honored here:
  · state digest input is literal[16] || q_le_i64[8]  (24 bytes); the digest
    itself is NOT written back into those 24 bytes (no self-reference);
  · exactly-fixed widths: literal = 16 bytes, substrate = 8 bytes;
  · strict errors only — never fallback / repair / clamp / normalize.
"""

from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Frozen widths and encodings
# ---------------------------------------------------------------------------

LITERAL_SIZE = 16  # bytes, exact
SUBSTRATE_SIZE = 8  # bytes, exact (signed int64 little-endian)

LITERAL_ZERO = b"\x00" * LITERAL_SIZE
SUBSTRATE_ZERO = struct.pack("<q", 0)

#: canonical state digest input = literal[16] || q_le_i64[8]
STATE_DIGEST_INPUT_SIZE = LITERAL_SIZE + SUBSTRATE_SIZE  # 24


class HarnessError(Exception):
    """Any execution / schema / protocol error.

    Raising this means the run is *invalid or errored* — it must NEVER be
    silently converted into a scientific FAIL.
    """


def encode_substrate(q: int) -> bytes:
    """Encode a signed int64 scalar to exactly 8 little-endian bytes."""
    if not isinstance(q, int):
        raise HarnessError(f"substrate value must be int, got {type(q)!r}")
    if not (-(2**63) <= q < 2**63):
        raise HarnessError(f"substrate value out of int64 range: {q}")
    return struct.pack("<q", q)


def decode_substrate(raw: bytes) -> int:
    """Decode exactly 8 little-endian bytes to a signed int64 scalar.

    Strict: the caller must pass exactly SUBSTRATE_SIZE bytes. Length checking
    on the *file* is the caller's duty (see readers.py), which enforces the
    whole-file-exactly-8 rule.
    """
    if len(raw) != SUBSTRATE_SIZE:
        raise HarnessError(
            f"substrate must be exactly {SUBSTRATE_SIZE} bytes, got {len(raw)}"
        )
    return struct.unpack("<q", raw)[0]


def canonical_state_bytes(literal: bytes, q_raw: bytes) -> bytes:
    """Return the 24-byte canonical state digest input.

    literal must be exactly 16 bytes; q_raw must be exactly 8 bytes.
    """
    if len(literal) != LITERAL_SIZE:
        raise HarnessError(
            f"literal must be exactly {LITERAL_SIZE} bytes, got {len(literal)}"
        )
    if len(q_raw) != SUBSTRATE_SIZE:
        raise HarnessError(
            f"substrate raw must be exactly {SUBSTRATE_SIZE} bytes, got {len(q_raw)}"
        )
    return literal + q_raw


def canonical_state_digest(literal: bytes, q_raw: bytes) -> str:
    """SHA-256 over the 24-byte canonical state digest input.

    Note: the digest is derived FROM the 24 bytes; it is never written back
    into them (avoids self-reference).
    """
    payload = canonical_state_bytes(literal, q_raw)
    return hashlib.sha256(payload).hexdigest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file_hex(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Frozen parent identities (must match the SPEC / prereg / model)
# ---------------------------------------------------------------------------

REFERENCE_HARNESS_SPEC_HASH = (
    "b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33"
)
PARENT_PREREG_SHA256 = (
    "ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4"
)

# ---------------------------------------------------------------------------
# Synthetic write-model constants (SET semantics, not accumulation)
# ---------------------------------------------------------------------------

#: EXTRA_CONSTANT sets q := 2 regardless of episode content class.
EXTRA_CONSTANT_VALUE = 2

#: EXTRA_CONTENT sets q := +2 for class L, q := -2 for class R.
EXTRA_CONTENT_VALUE_L = 2
EXTRA_CONTENT_VALUE_R = -2

#: freeze guard: the write path asserts q == 0 before an ON write.
WRITE_PRECONDITION_Q = 0

# ---------------------------------------------------------------------------
# Domain partition / mask decomposition  (BD-56)
# ---------------------------------------------------------------------------
#
# The frozen decomposition, made EXPLICIT here so that executed semantics and
# frozen binding semantics are the same object (凌翼 BD-56). Only STATE_FIELDS
# take part in a state delta; META/VOLATILE never do.
#
#   STATE_FIELDS = { literal.bin[16], substrate.bin[8] }
#
#   IDENTITY_ONLY_COMPONENTS = EMPTY_SET
#       (this harness writes NO identity-only content into STATE; episode
#        identity lives in META. So the identity mask subtracts nothing.)
#
#   LITERAL_STORAGE_COMPONENTS = { literal.bin[0:16] }
#
#   NONSTORAGE_COMPONENT      = { substrate q }
#       (do NOT put q into any mask set)
#
# Derived (canonical):
#   ΔS_registered       = literal change + q change
#   ΔS_identity_masked  = ΔS_registered            (identity mask is empty)
#   ΔS_nonstorage       = q change only            (literal storage masked out)

STATE_FIELD_LITERAL = "literal.bin[0:16]"
STATE_FIELD_SUBSTRATE = "substrate.bin[8]"

IDENTITY_ONLY_COMPONENTS: frozenset = frozenset()  # EMPTY_SET (BD-56)
LITERAL_STORAGE_COMPONENTS = frozenset({STATE_FIELD_LITERAL})
NONSTORAGE_COMPONENT = frozenset({STATE_FIELD_SUBSTRATE})  # = q

#: Components registered as nuisance but NOT part of STATE_FIELDS; they are
#: never a state-delta operand and therefore are never "re-masked" out of STATE.
NONSTATE_STORAGE_PIPELINE_NUISANCE_EXCLUSIONS = frozenset(
    {"filename", "path", "length", "mtime", "allocation_metadata", "logs", "container_hash"}
)


def delta_identity_masked_includes_literal() -> bool:
    """ΔS_identity_masked = ΔS_registered - IDENTITY_ONLY. With an empty
    identity set, literal change IS visible in ΔS_identity_masked."""
    return STATE_FIELD_LITERAL not in IDENTITY_ONLY_COMPONENTS


def delta_nonstorage_includes_q() -> bool:
    """ΔS_nonstorage = ΔS_registered - (IDENTITY_ONLY + LITERAL_STORAGE +
    NUISANCE). literal is masked out, so only the substrate q remains."""
    masked = IDENTITY_ONLY_COMPONENTS | LITERAL_STORAGE_COMPONENTS
    return STATE_FIELD_SUBSTRATE in NONSTORAGE_COMPONENT and STATE_FIELD_LITERAL in masked

# ---------------------------------------------------------------------------
# Read-path probe values (neutral; carry no episode/class/phase/oracle)
# ---------------------------------------------------------------------------

NEUTRAL_PROBES = (0, 2)

# ---------------------------------------------------------------------------
# Episode payload templates (four, equal-length, 16-byte ASCII)
# ---------------------------------------------------------------------------

EPISODE_PAYLOADS = {
    "A1": b"cls=L;sample=01;",
    "A2": b"cls=L;sample=02;",
    "B1": b"cls=R;sample=01;",
    "B2": b"cls=R;sample=02;",
}

CONTENT_CLASS_OF = {"A1": "L", "A2": "L", "B1": "R", "B2": "R"}


@dataclass(frozen=True)
class StateSnapshot:
    """An observer-collected snapshot of registered state (read-only)."""

    literal: bytes
    q_raw: bytes

    @property
    def q(self) -> int:
        return decode_substrate(self.q_raw)

    @property
    def digest(self) -> str:
        return canonical_state_digest(self.literal, self.q_raw)
