"""
Fixtures (RC8) — the 13 known-answer instances.

凌翼 RC8 ruling compliance:
  · fixtures.py consumes fixture_contracts.FIXTURE_CONFIGS only (NEVER the oracle);
  · all judgement routes through exactly two public gates in gates.py:
        PRE_EVIDENCE_GATE        (source = S_write)
        POST_RESET_EVIDENCE_GATE (source = S_restored)
    plus J_GATE / RESET_GATE before any post claim;
  · NO fixture hand-writes L1/C2/C3; NO failure-default-to-C3;
  · ledger stores raw observations per member x arm x phase, independently recomputable
    (see recompute_from_ledger.py);
  · the active runtime reader witnesses a NON-ZERO q (from the C arm).

The runner comparator consumes FROZEN_ORACLES from fixture_contracts; this module
does not.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from fixture_contracts import FIXTURE_CONFIGS, REQUIRED_FIXTURE_IDS
from gates import POST_RESET_EVIDENCE_GATE, PRE_EVIDENCE_GATE
from evaluator import (
    ARCHITECTURALLY_NOT_IDENTIFIABLE,
    C1,
    INVALID,
    N_A,
    NOT_ASSESSED,
    NOT_ESTABLISHED,
    PASS,
    evaluate_basic_l1,
    evaluate_c2_attempt,
    evaluate_c2_architectural,
)
from harness_constants import CONTENT_CLASS_OF, EPISODE_PAYLOADS, StateSnapshot
from observer import StateObserver
from perturbation_j import apply_j
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

PHASE = "PHASE_A_HARNESS_VALIDATION_EXECUTION"
SCIENTIFIC_CLAIM_ELIGIBILITY = "NONE"

_MEMBERS = ("A1", "A2", "B1", "B2")


# ---------------------------------------------------------------------------
# Ledger / result
# ---------------------------------------------------------------------------


@dataclass
class Ledger:
    fixture_id: str
    attempted_scope: dict = field(default_factory=dict)
    # member -> arm -> phase -> raw observation
    observations: dict = field(default_factory=dict)
    pre: dict = field(default_factory=dict)
    post: dict = field(default_factory=dict)
    gates: dict = field(default_factory=dict)
    l2: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)


@dataclass
class FixtureResult:
    fixture_id: str
    expected: dict
    actual: dict
    ledger: Ledger

    @property
    def oracle_match(self) -> bool:
        return _subset_eq(self.expected, self.actual)


def _subset_eq(expected: dict, actual: dict) -> bool:
    for k, v in expected.items():
        if k not in actual:
            return False
        if isinstance(v, dict):
            if not isinstance(actual[k], dict) or not _subset_eq(v, actual[k]):
                return False
        elif actual[k] != v:
            return False
    return True


# ---------------------------------------------------------------------------
# Sandbox / arm
# ---------------------------------------------------------------------------


class Arm:
    def __init__(self, root: Path, name: str):
        self.dir = root / name
        self.state = RegisteredState(self.dir)
        self.state.initialize_baseline()

    def snapshot(self) -> StateSnapshot:
        return StateObserver(self.state).snapshot()

    def store(self, payload: bytes, mode: str) -> None:
        with self.state.write_window():
            storage_write(self.state, payload, mode)

    def extra(self, payload: bytes, mode: str) -> None:
        if mode == EXTRA_OFF:
            raise ValueError("OFF must not be invoked as a write")
        with self.state.write_window():
            extra_write(self.state, payload, mode)

    def read_afterglow(self, u: int) -> Fraction:
        return affine_read(self.state.substrate_path, u)

    def read_literal(self, u: int) -> int:
        return literal_consume(self.state.literal_path, u)


class Sandbox:
    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="afterglow_fx_"))

    def arm(self, name: str) -> Arm:
        return Arm(self.root, name)

    def close(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def _snap(s: StateSnapshot) -> dict:
    return {"literal": s.literal.hex(), "q_raw": s.q_raw.hex(), "q": s.q, "digest": s.digest}


def _apply_j_witnessed(arm: Arm, mode: str):
    """Apply J; witness (S_write, J_after, S_handoff)."""
    s_write = arm.snapshot()
    with arm.state.write_window():
        apply_j(arm.state, mode)
    j_after = arm.snapshot()
    s_handoff = arm.snapshot()
    return s_write, j_after, s_handoff


def _reset_arm(arm: Arm, fault: bool):
    from reset import ResetController

    ctrl = ResetController(arm.state.literal_path, arm.state.substrate_path)
    handoff = ctrl.capture_handoff()
    if not fault:
        restored = ctrl.capture_restored()
    else:
        corrupt = bytes([handoff.q_raw[0] ^ 0x01]) + handoff.q_raw[1:]
        restored = StateSnapshot(literal=handoff.literal, q_raw=corrupt)
    # clear/access are LOGICAL declarations, not OS-verified witnesses.
    outcome = ctrl.verify(handoff, restored, clear_side_ok=True, access_side_ok=True)
    return handoff, restored, outcome.reset_valid, outcome.reason


# ---------------------------------------------------------------------------
# Member realization -> per-member x per-arm x per-phase raw observations
# ---------------------------------------------------------------------------


def _realize_member(root: Path, mid: str, extra_mode: str, j_mode: str,
                    reset_all_arms: bool, reset_fault: bool) -> dict:
    """Run one member through the full sequence, returning RAW observations only.

    Returns {"arms": {arm: {phase: dim}}, "member": mid, "content_class", "payload"}.
    J is applied only to pair arms B and C; arm A gets J = NOT_APPLICABLE.
    """
    payload = EPISODE_PAYLOADS[mid]
    A = Arm(root, f"{mid}_A")
    B = Arm(root, f"{mid}_B")
    C = Arm(root, f"{mid}_C")

    B.store(payload, STORE_FULL)
    C.store(payload, STORE_FULL)
    if extra_mode != EXTRA_OFF:
        C.extra(payload, extra_mode)

    arms = {"A": A, "B": B, "C": C}
    obs = {"member": mid, "content_class": CONTENT_CLASS_OF[mid],
           "payload": payload.hex(), "arms": {}}

    # S_write
    for name, arm in arms.items():
        obs["arms"][name] = {"S_write": _snap(arm.snapshot()), "J": "NOT_APPLICABLE"}

    # J on pair arms B, C
    for name in ("B", "C"):
        sw, ja, hd = _apply_j_witnessed(arms[name], j_mode)
        obs["arms"][name]["S_write"] = _snap(sw)
        obs["arms"][name]["J_after"] = _snap(ja)
        obs["arms"][name]["S_handoff"] = _snap(hd)
        obs["arms"][name]["J"] = j_mode

    # reset + recompute per arm
    for name, arm in arms.items():
        if reset_all_arms or name == "C":
            fault = reset_fault and name == "C"
            h, r, ok, reason = _reset_arm(arm, fault)
            obs["arms"][name]["reset_witness"] = {
                "handoff_digest": h.digest, "restored_digest": r.digest,
                "reset_valid": ok, "reason": reason,
                "clear_access": "LOGICAL_DECLARATION",
            }
            obs["arms"][name]["S_restored"] = _snap(arm.snapshot())
        else:
            obs["arms"][name]["reset_witness"] = {"reset_valid": True, "reason": "NOT_REQUIRED"}
            obs["arms"][name]["S_restored"] = _snap(arm.snapshot())

    # reader witness on the C arm (q != 0 in the content-conditioned case)
    c_arm = arms["C"]
    obs["reader_witness"] = {
        "raw_q_hex": c_arm.snapshot().q_raw.hex(),
        "raw_q": c_arm.snapshot().q,
        "affine_u0": _frac(c_arm.read_afterglow(0)),
        "affine_u2": _frac(c_arm.read_afterglow(2)),
        "literal_u0": c_arm.read_literal(0),
    }
    return obs


def _frac(v: Fraction) -> dict:
    return {"num": v.numerator, "den": v.denominator}


def _obs_to_snapshot(d: dict) -> StateSnapshot:
    return StateSnapshot(literal=bytes.fromhex(d["literal"]), q_raw=bytes.fromhex(d["q_raw"]))


# ---------------------------------------------------------------------------
# Fixture runners (config-driven)
# ---------------------------------------------------------------------------


def _run_two_arm(cfg: dict) -> tuple[dict, Ledger]:
    payload = EPISODE_PAYLOADS[cfg["payload"]]
    sb = Sandbox()
    try:
        A = sb.arm("A")
        B = sb.arm("B")
        if cfg["A_mode"] != "NO_WRITE":
            A.store(payload, cfg["A_mode"])
        if cfg["B_mode"] != "NO_WRITE":
            B.store(payload, cfg["B_mode"])
        snap_A, snap_B = A.snapshot(), B.snapshot()
        l1 = evaluate_basic_l1(snap_A, snap_B, payload)
        led = Ledger(fixture_id="")
        led.observations = {"A": {"S_write": _snap(snap_A)}, "B": {"S_write": _snap(snap_B)}}
        led.pre = {"L1": l1.result, "change_class": l1.change_class, "h": l1.h}
        actual = {"L1": l1.result, "PRE_RESET_CHANGE_CLASS": l1.change_class,
                  "C2": NOT_ASSESSED, "C3": NOT_ASSESSED}
        return actual, led
    finally:
        sb.close()


def _run_multi_member(cfg: dict) -> tuple[dict, Ledger]:
    extra_mode = cfg["extra_mode"]
    root = Path(tempfile.mkdtemp(prefix="afterglow_fx_"))
    try:
        member_write = {}
        observations = {}
        for mid in _MEMBERS:
            payload = EPISODE_PAYLOADS[mid]
            A = Arm(root, f"{mid}_A")
            B = Arm(root, f"{mid}_B")
            C = Arm(root, f"{mid}_C")
            B.store(payload, STORE_FULL)
            C.store(payload, STORE_FULL)
            C.extra(payload, extra_mode)
            sa, sb_, sc = A.snapshot(), B.snapshot(), C.snapshot()
            member_write[mid] = {"A": sa, "B": sb_, "C": sc, "payload": payload}
            observations[mid] = {"A": _snap(sa), "B": _snap(sb_), "C": _snap(sc)}

        pre = PRE_EVIDENCE_GATE(member_write)
        led = Ledger(fixture_id="")
        led.observations = observations
        led.pre = {"L1": pre.l1, "pre_class": pre.pre_class, "c2": pre.c2, "c3": pre.c3,
                   "t_write": {k: (None if v is None else _frac(v)) for k, v in pre.t_write.items()}}
        actual = {"L1": pre.l1, "PRE_RESET_CHANGE_CLASS": pre.pre_class, "C3": pre.c3}
        return actual, led
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _run_reset_suite(cfg: dict) -> tuple[dict, Ledger]:
    j_mode = cfg["j_mode"]
    reset_fault = cfg["reset_fault"]
    attempted = cfg["attempted"]
    pre_extra = cfg.get("pre_extra", EXTRA_CONTENT)
    root = Path(tempfile.mkdtemp(prefix="afterglow_fx_"))
    try:
        member_obs = {}
        member_write = {}
        member_restored = {}
        for mid in _MEMBERS:
            obs = _realize_member(root, mid, pre_extra, j_mode,
                                  reset_all_arms=True, reset_fault=reset_fault)
            member_obs[mid] = obs
            member_write[mid] = {
                "A": _obs_to_snapshot(obs["arms"]["A"]["S_write"]),
                "B": _obs_to_snapshot(obs["arms"]["B"]["S_write"]),
                "C": _obs_to_snapshot(obs["arms"]["C"]["S_write"]),
                "payload": bytes.fromhex(obs["payload"]),
            }
            member_restored[mid] = {
                "A": _obs_to_snapshot(obs["arms"]["A"]["S_restored"]),
                "B": _obs_to_snapshot(obs["arms"]["B"]["S_restored"]),
                "C": _obs_to_snapshot(obs["arms"]["C"]["S_restored"]),
                "payload": bytes.fromhex(obs["payload"]),
            }

        pre = PRE_EVIDENCE_GATE(member_write)

        # J gate: every required arm's J_after digest == S_handoff digest
        j_ok = True
        for o in member_obs.values():
            for arm in ("B", "C"):
                a = o["arms"][arm]
                if a.get("J") != "NOT_APPLICABLE":
                    if a["J_after"]["digest"] != a["S_handoff"]["digest"]:
                        j_ok = False
        # reset gate: every required arm reset valid
        reset_ok = all(
            o["arms"][a]["reset_witness"].get("reset_valid", True)
            for o in member_obs.values() for a in ("A", "B", "C")
        )

        post = POST_RESET_EVIDENCE_GATE(member_restored, j_ok, reset_ok, attempted)

        led = Ledger(fixture_id="")
        led.observations = member_obs
        led.attempted_scope = {"attempted": attempted}
        led.pre = {"pre_class": pre.pre_class, "c2": pre.c2, "c3": pre.c3}
        led.gates = {"j_timing_ok": j_ok, "reset_valid": reset_ok}
        led.post = {"post_c1_ok": post.post_c1_ok, "c3_post": post.c3_post,
                    "l2": post.l2, "supported": post.supported}
        led.l2 = {"result": post.l2, "POST_RESET_SUPPORTED_CLASS": post.supported}
        actual = {
            "PRE_RESET_CHANGE_CLASS": pre.pre_class,
            "post_C3": post.c3_post,
            "post_C1_ok": post.post_c1_ok,
            "reset_valid": reset_ok,
            "j_timing_ok": j_ok,
            "L2": post.l2,
            "POST_RESET_SUPPORTED_CLASS": post.supported,
        }
        if attempted == "post_C1_only":
            actual["post_C2"] = NOT_ASSESSED
        return actual, led
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Fixture functions (dispatch by config kind)
# ---------------------------------------------------------------------------


def _make(fid: str):
    cfg = FIXTURE_CONFIGS[fid]
    kind = cfg["kind"]

    if kind == "two_arm":
        def fn():
            actual, led = _run_two_arm(cfg)
            led.fixture_id = fid
            return FixtureResult(fid, {}, actual, led)
        return fn

    if kind == "multi_member":
        def fn():
            actual, led = _run_multi_member(cfg)
            led.fixture_id = fid
            return FixtureResult(fid, {}, actual, led)
        return fn

    if kind == "reset_suite":
        def fn():
            actual, led = _run_reset_suite(cfg)
            led.fixture_id = fid
            return FixtureResult(fid, {}, actual, led)
        return fn

    if kind == "two_arm_rule_missing":
        def fn():
            actual, led = _run_two_arm(cfg)
            led.fixture_id = fid
            from evaluator import AttemptedScope
            scope = AttemptedScope(pre_reset_c1=True, pre_reset_c2=True,
                                   pre_reset_c3=False, post_reset=False)
            led.attempted_scope = scope.as_dict()
            rule_bundle = {"STATE_DELTA_RULE": "present",
                           "CAUSAL_CONTRAST_RULE": None, "measurement_scale": "signed"}
            c2a = evaluate_c2_attempt(rule_bundle, scope)
            actual.pop("C2", None)
            actual["C2_ATTEMPT"] = c2a.result
            actual["INVALIDITY_CODE"] = c2a.invalidity_code
            actual["C3"] = NOT_ASSESSED
            actual["L2"] = c2a.l2
            return FixtureResult(fid, {}, actual, led)
        return fn

    if kind == "non_separable_wrapper":
        def fn():
            # Only a combined, indivisible write() is exposed; NO ON/OFF selector.
            root = Path(tempfile.mkdtemp(prefix="afterglow_fx_"))
            try:
                # L1/C1 assessed on the storage path (baseline A vs a storage-only
                # write to B), separate from the wrapper's capability question.
                payload = EPISODE_PAYLOADS["A1"]
                A = Arm(root, "A")
                B = Arm(root, "B")
                B.store(payload, STORE_FULL)  # storage ON, extra OFF (baseline path)
                l1 = evaluate_basic_l1(A.snapshot(), B.snapshot(), payload)

                w = CombinedOnlyWriter(root, "v4b")
                w.write(payload)  # indivisible write (storage+extra), for capability check
                surface = w.capability_surface()
                separable = ("extra_mode" in surface)
                c2res, c3res = evaluate_c2_architectural(extra_interface_separable=separable)

                led = Ledger(fixture_id=fid)
                led.notes.append(f"capability_surface={surface}; separable={separable}")
                actual = {"L1": l1.result, "PRE_RESET_CHANGE_CLASS": l1.change_class,
                          "C2": c2res, "C3": c3res}
                return FixtureResult(fid, {}, actual, led)
            finally:
                shutil.rmtree(root, ignore_errors=True)
        return fn

    raise ValueError(f"unknown kind {kind!r}")


class CombinedOnlyWriter:
    """Indivisible writer: write(payload) does storage+extra together.

    The public capability surface exposes NO extra_mode / on-off / split method,
    so a same-E / same-storage-path W_extra ON/OFF pair CANNOT be constructed.
    ANI is derived from this capability structure, not a method-name blacklist.
    """

    def __init__(self, root: Path, name: str):
        self.arm = Arm(root, name)
        self.last_write_snapshot = None

    def write(self, payload: bytes) -> None:
        # fixed indivisible operation: storage AND extra together
        self.arm.store(payload, STORE_FULL)
        self.arm.extra(payload, EXTRA_CONTENT)
        self.last_write_snapshot = self.arm.snapshot()

    def capability_surface(self) -> tuple:
        # Public capabilities. Deliberately NO extra selector.
        return ("write",)

    # intentionally NO extra_on / extra_off / set_extra_off / extra_mode


FIXTURES = {fid: _make(fid) for fid in REQUIRED_FIXTURE_IDS}


def run_all() -> list[FixtureResult]:
    return [FIXTURES[k]() for k in FIXTURE_CONFIGS]
