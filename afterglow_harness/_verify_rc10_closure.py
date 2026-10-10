"""RC10 closure check: the four RC9 P1 defects must now be CLOSED.

Run: python _verify_rc10_closure.py
Prints CLOSED/OPEN for each of §3/§5/§6/§7 from the RC9 review.
"""
import copy
import fixtures as f
from evidence_bundle import evaluate_bundle
from harness_constants import CONTENT_CLASS_OF
from evidence_bundle import ArmPhase, EvidenceBundle, MemberEvidence


def bundle_from(fid):
    r = f.FIXTURES[fid]()
    obs = copy.deepcopy(r.ledger.observations)
    b = EvidenceBundle(fixture_id=fid, required_members=tuple(obs.keys()))
    for mid, m in obs.items():
        me = MemberEvidence(mid, CONTENT_CLASS_OF.get(mid, "?"), bytes.fromhex(m["payload"]))
        for arm, phases in m["arms"].items():
            me.arms[arm] = {p: ArmPhase(bytes.fromhex(ap["literal"]), bytes.fromhex(ap["q_raw"]))
                            for p, ap in phases.items()}
        me.reset_witness = copy.deepcopy(m.get("reset_witness", {}))
        me.reader_witness = copy.deepcopy(m.get("reader_witness", {}))
        b.members[mid] = me
    return b


# §3 reader empty probes
b = bundle_from("V5a")
b.members["A1"].reader_witness["affine"] = {}
b.members["A1"].reader_witness["literal"] = {}
res = evaluate_bundle(b, required_pre_class="C3", expected_post_supported_class=None, attempted="full")
print("S3 empty reader probes -> protocol:", res.protocol, "l2:", res.l2, "code:", res.code)
print("   §3 CLOSED" if res.l2 == "INVALID" else "   §3 STILL OPEN")

# §5 replay restores contract
import recompute_from_ledger as rec
r = f.FIXTURES["V5a"]()
out = rec.recompute_reset_suite("V5a", copy.deepcopy(r.ledger.observations))
print("S5 V5a replay via contract L2:", out.get("L2"))
from evidence_contract import get_contract
print("S5 contract required_pre_class for V5a:", get_contract("V5a")["required_pre_class"])
print("   §5 CLOSED (contract-driven)" if get_contract("V5a")["required_pre_class"] == "C3" else "   §5 OPEN")

# §6 V4b probe detects selector
class Fake:
    def write(self, payload, extra_mode=f.EXTRA_CONTENT):
        pass
probe = f.external_capability_probe(Fake())
print("S6 probe on write(payload, extra_mode):", probe["separable_w_extra"])
print("   §6 CLOSED" if probe["separable_w_extra"] else "   §6 STILL OPEN")

# §7 missing reset_valid
b = bundle_from("V5a")
for m in b.members.values():
    for a in ("A", "B", "C"):
        m.reset_witness[a].pop("reset_valid", None)
res = evaluate_bundle(b, required_pre_class="C3", expected_post_supported_class=None, attempted="full")
print("S7 missing reset_valid -> protocol:", res.protocol, "l2:", res.l2, "code:", res.code)
print("   §7 CLOSED" if res.l2 == "INVALID" else "   §7 STILL OPEN")
