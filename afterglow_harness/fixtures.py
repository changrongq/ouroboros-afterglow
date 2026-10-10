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
from harness_constants import CONTENT_CLASS_OF, EPISODE_PAYLOADS, HarnessError, decode_substrate
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
    # Return BOTH the handoff and the VERIFIED-RESTORED object. The caller binds
    # the verified-restored bytes into the bundle so the reset verifier, the
    # stored S_restored, and the reader input are provably the SAME object
    # (凌翼 RC10 R3-reset).
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
            # The bytes the reset verifier ACCEPTED. The gate requires
            # stored S_restored == these bytes (object identity, 凌翼 RC10).
            "verified_restored": {"literal": r.literal.hex(), "q_raw": r.q_raw.hex()},
            "clear_access": "LOGICAL_DECLARATION",
        }
        # Bind the STORED S_restored to the VERIFIED-RESTORED object directly
        # (not a fresh re-snapshot of a possibly-diverged file).
        me.arms[name]["S_restored"] = _ap(r)

    # Reader source = the VERIFIED-RESTORED bytes (object identity), not a fresh
    # live re-snapshot (凌翼 RC10 R3-reset). For a VALID reset, the live file must
    # equal the verified-restored object; a divergence means the reader would
    # read a DIFFERENT object. For an INVALID reset (fault fixture) the gate
    # fails earlier, so no live-equality is required here.
    restored_C = me.arms["C"]["S_restored"]
    if me.reset_witness["C"]["reset_valid"]:
        live_C = _ap(C.snapshot())
        if (live_C.literal != restored_C.literal) or (live_C.q_raw != restored_C.q_raw):
            raise HarnessError(
                "READER_SOURCE_IDENTITY_BREAK: live C != verified-restored C before read"
            )
    me.reader_witness = {
        # redundant cross-check only: MUST equal decode(S_restored.q_raw)
        "raw_q": decode_substrate(restored_C.q_raw),
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
    # Construction params come from FIXTURE_CONFIGS; the JUDGEMENT contract
    # (required_pre_class / attempted) comes from the SINGLE authority,
    # evidence_contract — so production and replay agree by construction
    # (凌翼/知微 RC11 §8).
    from evidence_contract import get_contract
    j_mode = cfg["j_mode"]
    pre_extra = cfg.get("pre_extra", EXTRA_CONTENT)
    reset_fault = cfg["reset_fault"]
    contract = get_contract(fid)
    attempted = contract["attempted"]
    required_pre = contract["required_pre_class"]
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
            # structured sub-verdicts (RC11 §8): read the flags, never guess
            # from the error-message prefix.
            "reset_valid": res.reset_valid,
            "j_timing_ok": res.j_timing_ok,
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
        #
        # 凌翼 RC10 R3-V4b: the probe is only trustworthy if it DETECTS
        # separability on a selector-bearing positive control. If the positive
        # control is not detected => PROBE_INVALID (NOT a V4b ANI PASS).
        if not probe_is_valid():
            led = Ledger(fixture_id=fid)
            led.attempted_scope = {"shape": "non_separable_wrapper"}
            led.notes.append("PROBE_INVALID: positive control not detected")
            return {"L1": "PROBE_INVALID", "PRE_RESET_CHANGE_CLASS": "PROBE_INVALID",
                    "C2": "PROBE_INVALID", "C3": "PROBE_INVALID"}, led
        handle = CombinedOnlyWriter(root, "v4b")
        probe = external_capability_probe(handle.public_handle())
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


class SeparableControlHandle:
    """POSITIVE CONTROL (凌翼 RC10 R3-V4b): a handle that DOES expose a
    selector/mode on its registered public write path.

    The probe MUST return separable_w_extra=True for this handle. If it does
    not, the probe itself is broken => PROBE_INVALID (never V4b ANI PASS).
    """

    def __init__(self, root: Path, name: str):
        self._arm = Arm(root, name)

    def write(self, payload: bytes, extra_mode: str = EXTRA_CONTENT) -> None:
        self._arm.store(payload, STORE_FULL)
        if extra_mode != EXTRA_OFF:
            self._arm.extra(payload, extra_mode)


def _callable_takes_selector(fn) -> bool:
    """STRUCTURAL check: does a registered callable accept a selector/mode arg?

    Inspect the real signature — never a dead `if False else False`.
    """
    import inspect

    if not callable(fn):
        return False
    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    for name, p in sig.parameters.items():
        if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            # *args / **kwargs could carry a selector; treat conservatively as
            # a possible selector surface.
            return True
        lname = name.lower()
        if any(tok in lname for tok in ("mode", "selector", "extra", "variant")):
            return True
    return False


def external_capability_probe(handle) -> dict:
    """Probe the REGISTERED PUBLIC interface from OUTSIDE (凌翼 RC10 R3-V4b).

    Returns a dict that MUST include a truthful capability observation. ANI
    (architecturally not identifiable) is only ever established when the probe
    can DETECT separability on a positive control (see probe_is_valid()) AND the
    production handle reads as non-separable.

    STRUCTURAL : inspect the registered public handle; its public callables and
                 their real signatures. A selector/mode/extra surface => separable.
    BEHAVIORAL : genuinely ATTEMPT an ON/OFF pair through the public surface —
                 call the write with and without a selector and observe whether
                 the call is accepted (凌翼/知微 RC11 §8: 之前"behavioral"只再查签名,
                 这里改为真实调用尝试).

    Scope note (凌翼): we do NOT count Python malicious reflection (obj._inner...)
    as a registered public capability. ANI targets the frozen REGISTERED PUBLIC
    interface; the tester only holds the public handle.
    """
    import inspect as _inspect

    public_api = tuple(n for n in dir(handle) if not n.startswith("_"))

    # ---- STRUCTURAL ----
    structural_split = False
    structural_evidence = []
    for name in public_api:
        try:
            member = getattr(handle, name)
        except Exception:
            continue
        if callable(member) and _callable_takes_selector(member):
            structural_split = True
            structural_evidence.append(f"{name}() accepts a selector/mode arg")
        if name in ("store", "extra", "set_extra_off", "extra_mode", "mode"):
            structural_split = True
            structural_evidence.append(f"public name {name!r} exposes a split surface")

    # ---- BEHAVIORAL (genuine call attempt) ----
    # Attempt to call the public write WITH a selector keyword. If the public
    # surface ACCEPTS it, ON/OFF is a public choice (separable). If it is
    # rejected (unexpected keyword), the public surface offers no ON/OFF pair.
    behavioral_split = False
    behavioral_evidence = []
    write_fn = getattr(handle, "write", None)
    if callable(write_fn):
        probe_payload = EPISODE_PAYLOADS["A1"]
        try:
            sig = _inspect.signature(write_fn)
            accepts_kw = ("extra_mode" in sig.parameters
                          or any(p.kind == _inspect.Parameter.VAR_KEYWORD
                                 for p in sig.parameters.values()))
        except (TypeError, ValueError):
            accepts_kw = False
        if accepts_kw:
            # A selector-bearing call is accepted by the registered public API.
            behavioral_split = True
            behavioral_evidence.append(
                "public write() accepts an ON/OFF selector keyword")
        else:
            try:
                write_fn(probe_payload, selector_probe=EXTRA_OFF)
                behavioral_split = True
                behavioral_evidence.append("public write() silently accepted a selector kwarg")
            except TypeError:
                behavioral_evidence.append(
                    "public write() rejects a selector kwarg (no ON/OFF pair)")

    separable = structural_split or behavioral_split

    return {
        "public_api": public_api,
        "structural_split": structural_split,
        "structural_evidence": structural_evidence,
        "behavioral_split": behavioral_split,
        "behavioral_evidence": behavioral_evidence,
        "separable_w_extra": separable,
    }


def probe_is_valid() -> bool:
    """Self-test: the probe MUST detect separability on a selector-bearing
    positive control handle, and MUST NOT on the non-separable production path.

    If the positive control is not detected => PROBE_INVALID (凌翼 RC10: this is
    NOT V4b ANI PASS).
    """
    root = Path(tempfile.mkdtemp(prefix="afterglow_probe_ctl_"))
    try:
        ctl = SeparableControlHandle(root, "ctl")
        pos = external_capability_probe(ctl)
        if pos["separable_w_extra"] is not True:
            return False
        # negative control: the combined-only writer must read as NOT separable
        combo = CombinedOnlyWriter(root, "neg")
        neg = external_capability_probe(combo.public_handle())
        if neg["separable_w_extra"] is not False:
            return False
        return True
    finally:
        shutil.rmtree(root, ignore_errors=True)


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
