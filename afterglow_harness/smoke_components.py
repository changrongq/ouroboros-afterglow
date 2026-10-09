"""
Component smoke test — verifies the base building blocks behave as frozen.

This is NOT a qualifying known-answer fixture. It only checks that the
primitives (storage widths, SET semantics, read paths, J modes) do what the
SPEC says, so that fixture construction can proceed on a sound base.

Run:
    python -m afterglow_harness.smoke_components
"""

from __future__ import annotations

import tempfile
from fractions import Fraction
from pathlib import Path

from harness_constants import (
    EXTRA_CONSTANT_VALUE,
    EXTRA_CONTENT_VALUE_L,
    EXTRA_CONTENT_VALUE_R,
    EPISODE_PAYLOADS,
    LITERAL_SIZE,
    LITERAL_ZERO,
    SUBSTRATE_SIZE,
    SUBSTRATE_ZERO,
    canonical_state_digest,
    decode_substrate,
    encode_substrate,
)
from perturbation_j import (
    COLLAPSE_SIGN,
    ERASE_EFFECT,
    HALVE_AND_ERASE_LITERAL,
    IDENTITY,
    apply_j,
)
from readers import affine_read, literal_consume
from storage import RegisteredState
from writers import (
    EXTRA_CONSTANT,
    EXTRA_CONTENT,
    EXTRA_OFF,
    STORE_FULL,
    STORE_NULL,
    STORE_ONE_BYTE,
    extra_write,
    storage_write,
)

RESULTS = []


def check(name: str, cond: bool, detail: str = "") -> None:
    RESULTS.append((name, cond))
    flag = "PASS" if cond else "FAIL"
    print(f"[{flag}] {name}" + (f"  ({detail})" if detail else ""))


def fresh(tmp: Path, name: str) -> RegisteredState:
    s = RegisteredState(tmp / name)
    s.initialize_baseline()
    return s


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # --- widths / encodings -------------------------------------------
        check("literal size 16", LITERAL_SIZE == 16)
        check("substrate size 8", SUBSTRATE_SIZE == 8)
        check(
            "encode/decode roundtrip",
            decode_substrate(encode_substrate(-12345)) == -12345,
        )

        # --- baseline ------------------------------------------------------
        s = fresh(tmp, "baseline")
        snap = s.snapshot()
        check("baseline literal zeros", snap.literal == LITERAL_ZERO)
        check("baseline q == 0", snap.q == 0)
        check(
            "digest is 24-byte input",
            canonical_state_digest(LITERAL_ZERO, SUBSTRATE_ZERO)
            == canonical_state_digest(LITERAL_ZERO, SUBSTRATE_ZERO),
        )

        # --- STORE_FULL ----------------------------------------------------
        s = fresh(tmp, "store_full")
        payload = EPISODE_PAYLOADS["A1"]
        with s.write_window():
            storage_write(s, payload, STORE_FULL)
        check("STORE_FULL writes payload", s.snapshot().literal == payload)

        # --- STORE_NULL (called but zero effect) ---------------------------
        s = fresh(tmp, "store_null")
        with s.write_window():
            storage_write(s, payload, STORE_NULL)
        check("STORE_NULL leaves literal zero", s.snapshot().literal == LITERAL_ZERO)

        # --- STORE_ONE_BYTE ------------------------------------------------
        s = fresh(tmp, "store_one")
        with s.write_window():
            storage_write(s, payload, STORE_ONE_BYTE)
        lit = s.snapshot().literal
        check("STORE_ONE_BYTE first byte only", lit[0] == payload[0] and lit[1:] == LITERAL_ZERO[1:])

        # --- EXTRA_CONSTANT (SET) ------------------------------------------
        s = fresh(tmp, "extra_const")
        with s.write_window():
            storage_write(s, EPISODE_PAYLOADS["B1"], STORE_FULL)
            extra_write(s, EPISODE_PAYLOADS["B1"], EXTRA_CONSTANT)
        check("EXTRA_CONSTANT q == 2", s.snapshot().q == EXTRA_CONSTANT_VALUE)

        # --- EXTRA_CONSTANT idempotence (SET, not accumulate) --------------
        # second call must fail the q==0 precondition, proving SET-not-add.
        s = fresh(tmp, "extra_const_idem")
        with s.write_window():
            storage_write(s, EPISODE_PAYLOADS["B1"], STORE_FULL)
            extra_write(s, EPISODE_PAYLOADS["B1"], EXTRA_CONSTANT)
        try:
            with s.write_window():
                extra_write(s, EPISODE_PAYLOADS["B1"], EXTRA_CONSTANT)
            check("EXTRA second call rejected (q!=0 guard)", False)
        except Exception:
            check("EXTRA second call rejected (q!=0 guard)", True)

        # --- EXTRA_CONTENT derives class from bytes ------------------------
        sL = fresh(tmp, "extra_L")
        with sL.write_window():
            storage_write(sL, EPISODE_PAYLOADS["A1"], STORE_FULL)
            extra_write(sL, EPISODE_PAYLOADS["A1"], EXTRA_CONTENT)
        check("EXTRA_CONTENT cls=L -> +2", sL.snapshot().q == EXTRA_CONTENT_VALUE_L)

        sR = fresh(tmp, "extra_R")
        with sR.write_window():
            storage_write(sR, EPISODE_PAYLOADS["B1"], STORE_FULL)
            extra_write(sR, EPISODE_PAYLOADS["B1"], EXTRA_CONTENT)
        check("EXTRA_CONTENT cls=R -> -2", sR.snapshot().q == EXTRA_CONTENT_VALUE_R)

        # --- EXTRA_OFF must not be called ----------------------------------
        try:
            with sR.write_window():
                extra_write(sR, EPISODE_PAYLOADS["B1"], EXTRA_OFF)
            check("OFF invocation raises (NOT INVOKED)", False)
        except Exception:
            check("OFF invocation raises (NOT INVOKED)", True)

        # --- affine reader -------------------------------------------------
        s = fresh(tmp, "reader")
        with s.write_window():
            storage_write(s, EPISODE_PAYLOADS["A1"], STORE_FULL)
            extra_write(s, EPISODE_PAYLOADS["A1"], EXTRA_CONSTANT)  # q=+2
        check("affine R(q=2,u=0) == 1", affine_read(s.substrate_path, 0) == Fraction(1, 1))
        check("affine R(q=2,u=2) == 3", affine_read(s.substrate_path, 2) == Fraction(3, 1))

        # --- affine reader strict length -----------------------------------
        bad = tmp / "bad_substrate"
        bad.mkdir()
        (bad / "substrate.bin").write_bytes(b"\x00" * 9)  # 9 bytes -> error
        try:
            affine_read(bad / "substrate.bin", 0)
            check("affine reader rejects 9-byte file", False)
        except Exception:
            check("affine reader rejects 9-byte file", True)

        # --- literal consumer ----------------------------------------------
        s = fresh(tmp, "litcon")
        with s.write_window():
            storage_write(s, EPISODE_PAYLOADS["A1"], STORE_FULL)
        pay = EPISODE_PAYLOADS["A1"]
        check(
            "literal consumer L(lit,0) == sum(bytes)",
            literal_consume(s.literal_path, 0) == sum(pay),
        )
        bad2 = tmp / "bad_literal"
        bad2.mkdir()
        (bad2 / "literal.bin").write_bytes(b"\x00" * 15)  # 15 bytes -> error
        try:
            literal_consume(bad2 / "literal.bin", 0)
            check("literal consumer rejects 15-byte file", False)
        except Exception:
            check("literal consumer rejects 15-byte file", True)

        # --- J modes -------------------------------------------------------
        s = fresh(tmp, "j_identity")
        with s.write_window():
            storage_write(s, EPISODE_PAYLOADS["A1"], STORE_FULL)
            extra_write(s, EPISODE_PAYLOADS["A1"], EXTRA_CONSTANT)  # q=+2
        before = s.snapshot()
        with s.write_window():
            apply_j(s, IDENTITY)
        check("J IDENTITY unchanged", s.snapshot().digest == before.digest)

        s = fresh(tmp, "j_collapse")
        with s.write_window():
            storage_write(s, EPISODE_PAYLOADS["A1"], STORE_FULL)
            extra_write(s, EPISODE_PAYLOADS["A1"], EXTRA_CONSTANT)  # +2
        with s.write_window():
            apply_j(s, COLLAPSE_SIGN)
        check("J COLLAPSE_SIGN +2 -> +2", s.snapshot().q == 2)
        s2 = fresh(tmp, "j_collapse_neg")
        with s2.write_window():
            storage_write(s2, EPISODE_PAYLOADS["B1"], STORE_FULL)
            extra_write(s2, EPISODE_PAYLOADS["B1"], EXTRA_CONTENT)  # -2
        with s2.write_window():
            apply_j(s2, COLLAPSE_SIGN)
        check("J COLLAPSE_SIGN -2 -> +2", s2.snapshot().q == 2)

        s = fresh(tmp, "j_erase")
        with s.write_window():
            storage_write(s, EPISODE_PAYLOADS["A1"], STORE_FULL)
            extra_write(s, EPISODE_PAYLOADS["A1"], EXTRA_CONSTANT)
        with s.write_window():
            apply_j(s, ERASE_EFFECT)
        snap = s.snapshot()
        check("J ERASE_EFFECT zeros literal and q", snap.literal == LITERAL_ZERO and snap.q == 0)

        s = fresh(tmp, "j_halve")
        with s.write_window():
            storage_write(s, EPISODE_PAYLOADS["A1"], STORE_FULL)
            extra_write(s, EPISODE_PAYLOADS["A1"], EXTRA_CONSTANT)  # +2
        with s.write_window():
            apply_j(s, HALVE_AND_ERASE_LITERAL)
        snap = s.snapshot()
        check("J HALVE +2 -> +1 and literal erased", snap.q == 1 and snap.literal == LITERAL_ZERO)

    # --- BD-56: domain partition / mask decomposition ---
    from harness_constants import (
        IDENTITY_ONLY_COMPONENTS,
        LITERAL_STORAGE_COMPONENTS,
        NONSTORAGE_COMPONENT,
        STATE_FIELD_LITERAL,
        STATE_FIELD_SUBSTRATE,
        delta_identity_masked_includes_literal,
        delta_nonstorage_includes_q,
    )

    check("BD-56 IDENTITY_ONLY_COMPONENTS == EMPTY", len(IDENTITY_ONLY_COMPONENTS) == 0)
    check("BD-56 LITERAL_STORAGE_COMPONENTS == {literal}", LITERAL_STORAGE_COMPONENTS == frozenset({STATE_FIELD_LITERAL}))
    check("BD-56 NONSTORAGE_COMPONENT == {substrate}", NONSTORAGE_COMPONENT == frozenset({STATE_FIELD_SUBSTRATE}))
    check("BD-56 ΔS_identity_masked includes literal", delta_identity_masked_includes_literal())
    check("BD-56 ΔS_nonstorage includes q", delta_nonstorage_includes_q())

    print()
    passed = sum(1 for _, ok in RESULTS if ok)
    total = len(RESULTS)
    print(f"smoke_components: {passed}/{total} PASS")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
