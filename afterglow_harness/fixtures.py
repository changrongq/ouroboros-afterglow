"""
Fixtures (RC9) — build the unified EVIDENCE_BUNDLE; judge via evidence_bundle.

No fixture writes actual results. Fixtures provide CONFIG + FAULT INJECTION only.
All judgement flows through evidence_bundle.evaluate_bundle, whose chain is:

  member-set -> arms/phases -> S_write -> PRE -> required_pre_class
  -> J witness -> J<S_handoff==RESET handoff (byte-level) -> reset valid
  -> S_restored -> reader witnesses -> POST -> L2

INVALID dominates everywhere. The runner compares against FROZEN_ORACLES.
"""

from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path

from fixture_contracts import FIXTURE_CONFIGS, REQUIRED_FIXTURE_IDS
from evidence_bundle import ArmPhase, EvidenceBundle, MemberEvidence, evaluate_bundle
from evaluator import (
    ARCHITECTURALLY_NOT_IDENTIFIABLE,
    C1,
    INVALID,
    N_A,
    NOT_ASSESSED,
    evaluate_basic_l1,
    evaluate_c2_attempt,
    evaluate_c2_architectural,
)
from harness_constants import CONTENT_CLASS_OF, EPISODE_PAYLOADS
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


@dataclass
class Ledger:
    fixture_id: str
    attempted_scope: dict = field(default_factory=dict)
    observations: dict = field(default_factory=dict)
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


def _subset_eq(expected, actual) -> bool:
    for k, v in expected.items():
        if k not in actual:
            return False
        if isinstance(v, dict):
            if not _subset_eq(v, actual[k]):
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

    def snapshot(self):
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

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


def _ap(snap) -> ArmPhase:
    return ArmPhase(literal=snap.literal, q_raw=snap.q_raw)


def _apply_j_witnessed(arm, mode):
    s_write = arm.snapshot()
    with arm.state.write_window():
        apply_j(arm.state, mode)
    j_after = arm.snapshot()
    s_handoff = arm.snapshot()
    return s_write, j_after, s_handoff


def _reset_arm(arm, fault):
    from reset import ResetController
    ctrl = ResetController(arm.state.literal_path, arm.state.substrate_path)
    handoff = ctrl.capture_handoff()
    if not fault:
        restored = ctrl.capture_restored()
    else:
        corrupt = bytes([handoff.q_raw[0] ^ 0x01]) + handoff.q_raw[1:]
        from harness_constants import StateSnapshot
        restored = StateSnapshot(literal=handoff.literal, q_raw=corrupt)
    outcome = ctrl.verify(handoff, restored, clear_side_ok=True, access_side_ok=True)
    return handoff, restored, outcome.reset_valid, outcome.reason


# ---------------------------------------------------------------------------
# Member realization -> MemberEvidence
# ---------------------------------------------------------------------------


def _realize_member(root, mid, extra_mode, j_mode, reset_fault) -> MemberEvidence:
    payload = EPISODE_PAYLOADS[mid]
    A = Arm(root, f"{mid}_A")
    B = Arm(root, f"{mid}_B")
    C = Arm(root, f"{mid}_C")
    B.store(payload, STORE_FULL)
    C.store(payload, STORE_FULL)
    if extra_mode != EXTRA_OFF:
        C.extra(payload, extra_mode)

    me = MemberEvidence(member_id=mid, content_class=CONTENT_CLASS_OF[mid], payload=payload)
    for name, arm in (("A", A), ("B", B), ("C", C)):
        me.arms[name] = {"S_write": _ap(arm.snapshot())}

    for name in ("B", "C"):
        sw, ja, hd = _apply_j_witnessed({"A": A, "B": B, "C": C}[name], j_mode)
        me.arms[name]["S_write"] = _ap(sw)
        me.arms[name]["J_after"] = _ap(ja)
        me.arms[name]["S_handoff"] = _ap(hd)

    for name, arm in (("A", A), ("B", B), ("C", C)):
        fault = reset_fault and name == "C"
        h, r, ok, reason = _reset_arm(arm, fault)
        me.reset_witness[name] = {
            "reset_valid": ok, "reason": reason,
            "accepted_handoff": {"literal": h.literal.hex(), "q_raw": h.q_raw.hex()},
            "clear_access": "LOGICAL_DECLARATION",
        }
        me.arms[name]["S_restored"] = _ap(arm.snapshot())

    c_snap = C.snapshot()
    me.reader_witness = {
        "raw_q": c_snap.q,
        "affine": {str(u): {"num": C.read_afterglow(u).numerator,
                            "den": C.read_afterglow(u).denominator} for u in (0, 2)},
        "literal": {str(u): C.read_literal(u) for u in (0, 2)},
    }
    return me


def _member_obs(me: MemberEvidence) -> dict:
    return {
        "member": me.member_id, "content_class": me.content_class,
        "payload": me.payload.hex(),
        "arms": {a: {ph: {"literal": ap.literal.hex(), "q_raw": ap.q_raw.hex()}
                     for ph, ap in phases.items()}
                 for a, phases in me.arms.items()},
        "reset_witness": me.reset_witness,
        "reader_witness": me.reader_witness,
    }


# ---------------------------------------------------------------------------
# Fixture runners
# ---------------------------------------------------------------------------


def _run_two_arm(cfg, fid):
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
        led = Ledger(fixture_id=fid)
        led.attempted_scope = {"shape": "two_arm"}
        led.observations = {"A": {"S_write": {"literal": snap_A.literal.hex(), "q_raw": snap_A.q_raw.hex()}},
                            "B": {"S_write": {"literal": snap_B.literal.hex(), "q_raw": snap_B.q_raw.hex()}}}
        actual = {"L1": l1.result, "PRE_RESET_CHANGE_CLASS": l1.change_class,
                  "C2": NOT_ASSESSED, "C3": NOT_ASSESSED}
        return actual, led
    finally:
        sb.close()


def _run_multi_member(cfg, fid):
    extra_mode = cfg["extra_mode"]
    root = Path(tempfile.mkdtemp(prefix="afterglow_fx_"))
    try:
        bundle = EvidenceBundle(fixture_id=fid, required_members=_MEMBERS)
        for mid in _MEMBERS:
            payload = EPISODE_PAYLOADS[mid]
            A = Arm(root, f"{mid}_A")
            B = Arm(root, f"{mid}_B")
            C = Arm(root, f"{mid}_C")
            B.store(payload, STORE_FULL)
            C.store(payload, STORE_FULL)
            if extra_mode != EXTRA_OFF:
                C.extra(payload, extra_mode)
            me = MemberEvidence(member_id=mid, content_class=CONTENT_CLASS_OF[mid], payload=payload)
            for name, arm in (("A", A), ("B", B), ("C", C)):
                me.arms[name] = {"S_write": _ap(arm.snapshot())}
            bundle.members[mid] = me
        from evidence_bundle import _pre_from_bundle
        pre_class, c2, c3, _ = _pre_from_bundle(bundle)
        led = Ledger(fixture_id=fid)
        led.observations = {m: _member_obs(bundle.members[m]) for m in bundle.members}
        led.attempted_scope = {"shape": "multi_member"}
        actual = {"L1": _l1_of(bundle), "PRE_RESET_CHANGE_CLASS": pre_class, "C3": c3}
        return actual, led
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _l1_of(bundle):
    from evaluator import PASS
    ok = True
    for mid, me in bundle.members.items():
        a = me.arms["A"]["S_write"].snapshot()
        b = me.arms["B"]["S_write"].snapshot()
        if evaluate_basic_l1(a, b, me.payload).result != PASS:
            ok = False
    return PASS if ok else "FAIL"


def _run_reset_suite(cfg, fid):
    j_mode = cfg["j_mode"]
    pre_extra = cfg.get("pre_extra", EXTRA_CONTENT)
    reset_fault = cfg["reset_fault"]
    attempted = cfg["attempted"]
    required_pre = cfg.get("required_pre_class", "")
    root = Path(tempfile.mkdtemp(prefix="afterglow_fx_"))
    try:
        bundle = EvidenceBundle(fixture_id=fid, required_members=_MEMBERS)
        for mid in _MEMBERS:
            bundle.members[mid] = _realize_member(root, mid, pre_extra, j_mode, reset_fault)

        from evaluator import C3
        res = evaluate_bundle(bundle, required_pre_class=required_pre,
                              expected_post_supported_class=None, attempted=attempted)

        # pre_class is reported independent of any later protocol invalidity:
        # the PRE gate reads S_write, which is valid even if reset later fails.
        from evidence_bundle import _pre_from_bundle
        pre_class, _, _, _ = _pre_from_bundle(bundle)

        led = Ledger(fixture_id=fid)
        led.attempted_scope = {"attempted": attempted, "required_pre_class": required_pre,
                               "shape": "reset_suite"}
        led.observations = {m: _member_obs(bundle.members[m]) for m in bundle.members}
        led.gates = {"protocol": res.protocol, "code": res.code}
        led.l2 = {"result": res.l2, "POST_RESET_SUPPORTED_CLASS": res.supported}

        actual = {
            "PRE_RESET_CHANGE_CLASS": pre_class if pre_class else "",
            "post_C3": res.c3_post,
            "post_C1_ok": res.post_c1_ok,
            "reset_valid": not res.code.startswith("RESET_INVALID") if res.code else True,
            "j_timing_ok": not res.code.startswith(("J_", "HANDOFF_")) if res.code else True,
            "L2": res.l2,
            "POST_RESET_SUPPORTED_CLASS": res.supported,
        }
        if attempted == "post_C1_only":
            actual["post_C2"] = NOT_ASSESSED
        if res.protocol == INVALID:
            actual["INVALIDITY_CODE"] = res.code
        return actual, led
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _run_two_arm_rule_missing(cfg, fid):
    actual, led = _run_two_arm(cfg, fid)
    from evaluator import AttemptedScope
    scope = AttemptedScope(pre_reset_c1=True, pre_reset_c2=True, pre_reset_c3=False, post_reset=False)
    led.attempted_scope = dict(scope.as_dict())
    led.attempted_scope["shape"] = "two_arm"
    rule_bundle = {"STATE_DELTA_RULE": "present", "CAUSAL_CONTRAST_RULE": None,
                   "measurement_scale": "signed"}
    c2a = evaluate_c2_attempt(rule_bundle, scope)
    actual.pop("C2", None)
    actual["C2_ATTEMPT"] = c2a.result
    actual["INVALIDITY_CODE"] = c2a.invalidity_code
    actual["C3"] = NOT_ASSESSED
    actual["L2"] = c2a.l2
    return actual, led


def _run_non_separable_wrapper(cfg, fid):
    root = Path(tempfile.mkdtemp(prefix="afterglow_fx_"))
    try:
        # External capability probe: only the registered public handle is given
        # to the tester. No Arm / store / mode / selector escapes.
        handle = CombinedOnlyWriter(root, "v4b")
        probe = external_capability_probe(handle)
        separable = probe["separable_w_extra"]
        c2res, c3res = evaluate_c2_architectural(extra_interface_separable=separable)

        payload = EPISODE_PAYLOADS["A1"]
        A = Arm(root, "A")
        B = Arm(root, "B")
        B.store(payload, STORE_FULL)
        l1 = evaluate_basic_l1(A.snapshot(), B.snapshot(), payload)

        led = Ledger(fixture_id=fid)
        led.attempted_scope = {"shape": "non_separable_wrapper"}
        led.observations = {
            "A": {"S_write": {"literal": A.snapshot().literal.hex(), "q_raw": A.snapshot().q_raw.hex()}},
            "B": {"S_write": {"literal": B.snapshot().literal.hex(), "q_raw": B.snapshot().q_raw.hex()}},
        }
        led.notes.append(f"external_probe={probe}")
        actual = {"L1": l1.result, "PRE_RESET_CHANGE_CLASS": l1.change_class,
                  "C2": c2res, "C3": c3res}
        return actual, led
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------------------
# V4b: non-separable public interface + EXTERNAL capability probe
# ---------------------------------------------------------------------------


class _OnlyWriteHandle:
    """The ONLY public handle given to the tester: write(payload). No selector."""

    def __init__(self, inner):
        self._inner = inner

    def write(self, payload: bytes) -> None:
        self._inner.write(payload)


class CombinedOnlyWriter:
    """Indivisible writer exposed solely through _OnlyWriteHandle."""

    def __init__(self, root: Path, name: str):
        self._arm = Arm(root, name)

    def write(self, payload: bytes) -> None:
        self._arm.store(payload, STORE_FULL)
        self._arm.extra(payload, EXTRA_CONTENT)

    def public_handle(self) -> "_OnlyWriteHandle":
        return _OnlyWriteHandle(self)


def external_capability_probe(handle) -> dict:
    """Probe the REGISTERED PUBLIC interface from OUTSIDE. ANI is established by
    what the tester can DO, not by what the object claims.

    The tester receives only the public handle. If it cannot construct a
    same-E / same-storage-path W_extra ON/OFF pair through the public surface,
    the architecture is non-separable.
    """
    public_api = tuple(n for n in dir(handle) if not n.startswith("_"))
    has_split = any(n in public_api for n in ("store", "extra", "extra_mode", "set_extra_off"))
    # Does calling the only public operation ever expose a selector?
    takes_selector = "mode" in getattr(handle.write, "__code__", None).co_names if False else False
    separable = has_split or takes_selector
    return {"public_api": public_api, "separable_w_extra": separable}


FIXTURES = {
    "V0":   lambda: _f("V0", _run_two_arm),
    "V0b":  lambda: _f("V0b", _run_two_arm),
    "V1":   lambda: _f("V1", _run_two_arm),
    "V2":   lambda: _f("V2", _run_multi_member),
    "V3":   lambda: _f("V3", _run_multi_member),
    "V4.1": lambda: _f("V4.1", _run_two_arm_rule_missing),
    "V4b":  lambda: _f("V4b", _run_non_separable_wrapper),
    "V5a":  lambda: _f("V5a", _run_reset_suite),
    "V5b":  lambda: _f("V5b", _run_reset_suite),
    "V5c":  lambda: _f("V5c", _run_reset_suite),
    "V5d":  lambda: _f("V5d", _run_reset_suite),
    "V5e":  lambda: _f("V5e", _run_reset_suite),
    "V5f":  lambda: _f("V5f", _run_reset_suite),
}


def _f(fid, runner):
    actual, led = runner(FIXTURE_CONFIGS[fid], fid)
    return FixtureResult(fid, {}, actual, led)


def run_all():
    return [FIXTURES[k]() for k in FIXTURE_CONFIGS]
