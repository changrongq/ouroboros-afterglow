"""
Write operators.

Arm model (frozen):
  Arm A: storage NOT called ; extra NOT called
  Arm B: storage called     ; extra NOT called
  Arm C: storage called     ; extra called

Storage modes:
  STORE_FULL     : write the full 16-byte episode payload
  STORE_NULL     : called but makes no state change (V0)
  STORE_ONE_BYTE : write only the first payload byte; rest stays baseline (V0b)

Extra modes (SET semantics — NOT accumulation):
  EXTRA_CONSTANT : q := 2             (independent of content class)
  EXTRA_CONTENT  : cls=L -> q := 2
                   cls=R -> q := -2
  OFF            : NOT INVOKED (the component is not called at all)

Content for EXTRA_CONTENT is derived from the ACTUAL episode payload, not
supplied by the controller as the expected +/-2. The controller passes only
the raw episode bytes; the writer computes the class from them.

Guards:
  · before an ON extra write, q must be 0 (baseline);
  · the ON extra write is invoked exactly once per execution;
  · OFF means not invoked — no counters / placeholders / ack fields are
    created in registered state; call tracking lives in META (external).
"""

from __future__ import annotations

from harness_constants import (
    EPISODE_PAYLOADS,
    EXTRA_CONSTANT_VALUE,
    EXTRA_CONTENT_VALUE_L,
    EXTRA_CONTENT_VALUE_R,
    LITERAL_SIZE,
    HarnessError,
    WRITE_PRECONDITION_Q,
)
from storage import RegisteredState

# -- storage modes ----------------------------------------------------------

STORE_FULL = "STORE_FULL"
STORE_NULL = "STORE_NULL"
STORE_ONE_BYTE = "STORE_ONE_BYTE"

# -- extra modes ------------------------------------------------------------

EXTRA_CONSTANT = "EXTRA_CONSTANT"
EXTRA_CONTENT = "EXTRA_CONTENT"
EXTRA_OFF = "OFF"


def _content_class_from_payload(payload: bytes) -> str:
    """Derive content class from the actual episode bytes.

    Payload form: b"cls=<X>;sample=<NN>;". We parse the class from the bytes
    themselves so the harness genuinely reads content rather than trusting a
    controller-supplied label.
    """
    try:
        text = payload.decode("ascii")
    except UnicodeDecodeError as e:
        raise HarnessError(f"episode payload must be ASCII: {e}")
    if not text.startswith("cls=") or ";" not in text:
        raise HarnessError(f"malformed episode payload: {text!r}")
    cls = text[len("cls=") : text.index(";")]
    if cls not in ("L", "R"):
        raise HarnessError(f"unknown content class in payload: {cls!r}")
    return cls


def storage_write(state: RegisteredState, payload: bytes, mode: str) -> None:
    """Storage writer. If mode is STORE_NULL it is called but changes nothing."""
    if len(payload) != LITERAL_SIZE:
        raise HarnessError(
            f"episode payload must be exactly {LITERAL_SIZE} bytes, got {len(payload)}"
        )
    if mode == STORE_NULL:
        # called, but zero-effect: registered state is untouched.
        return
    if mode == STORE_FULL:
        state.write_literal(payload)
        return
    if mode == STORE_ONE_BYTE:
        # partial write: first byte only; the rest stays at baseline (zeros).
        from harness_constants import LITERAL_ZERO

        partial = payload[:1] + LITERAL_ZERO[1:]
        state.write_literal(partial)
        return
    raise HarnessError(f"unknown storage mode: {mode!r}")


def extra_write(state: RegisteredState, payload: bytes, mode: str) -> None:
    """Extra (W_extra) writer with SET semantics.

    OFF means NOT INVOKED: this function must not be called at all for OFF
    arms. If it is called with EXTRA_OFF we treat that as a protocol error,
    so OFF-invocation bugs are loud rather than silent.
    """
    if mode == EXTRA_OFF:
        raise HarnessError(
            "extra_write must not be called for OFF arms (OFF = NOT INVOKED)"
        )

    # SET semantics precondition: q must be at the frozen precondition value.
    snap = state.snapshot()
    if snap.q != WRITE_PRECONDITION_Q:
        raise HarnessError(
            f"extra write requires q == {WRITE_PRECONDITION_Q}, got {snap.q}"
        )

    if mode == EXTRA_CONSTANT:
        state.write_substrate(EXTRA_CONSTANT_VALUE)
        return
    if mode == EXTRA_CONTENT:
        cls = _content_class_from_payload(payload)
        if cls == "L":
            state.write_substrate(EXTRA_CONTENT_VALUE_L)
        else:  # cls == "R"
            state.write_substrate(EXTRA_CONTENT_VALUE_R)
        return
    raise HarnessError(f"unknown extra mode: {mode!r}")
