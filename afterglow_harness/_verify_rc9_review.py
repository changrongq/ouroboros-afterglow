import copy
import fixtures as f
import recompute_from_ledger as rec
from evidence_bundle import EvidenceBundle, MemberEvidence, ArmPhase, evaluate_bundle
from harness_constants import CONTENT_CLASS_OF

r = f.FIXTURES["V5a"]()
obs = copy.deepcopy(r.ledger.observations)

# §5: replay closes the required_pre_class gate (passes "")
out = rec.recompute_reset_suite(obs, "full")
print("S5 V5a replay L2:", out.get("L2"))
print("S5 REQUIRED_SCOPE reset_suite has required_pre_class?",
      "required_pre_class" in rec.REQUIRED_SCOPE["reset_suite"])

# §7: delete reset_valid from all reset_witness
b = EvidenceBundle("V5a", required_members=tuple(obs.keys()))
for mid, m in obs.items():
    me = MemberEvidence(mid, CONTENT_CLASS_OF.get(mid, "?"), bytes.fromhex(m["payload"]))
    for arm, phases in m["arms"].items():
        me.arms[arm] = {p: ArmPhase(bytes.fromhex(ap["literal"]), bytes.fromhex(ap["q_raw"]))
                        for p, ap in phases.items()}
    rw = copy.deepcopy(m.get("reset_witness", {}))
    for a in rw:
        rw[a].pop("reset_valid", None)
    me.reset_witness = rw
    me.reader_witness = m.get("reader_witness", {})
    b.members[mid] = me
res = evaluate_bundle(b, required_pre_class="C3", expected_post_supported_class=None, attempted="full")
print("S7 missing reset_valid -> protocol:", res.protocol, "L2:", res.l2, "code:", res.code)

# §6: V4b probe misses a selector in write signature
import fixtures as fx
class Fake:
    def __init__(self): self._arm = fx.Arm(__import__("pathlib").Path(__import__("tempfile").mkdtemp()), "f")
    def write(self, payload, extra_mode=fx.EXTRA_CONTENT): pass
probe = fx.external_capability_probe(Fake())
print("S6 probe on write(payload, extra_mode):", probe)
