"""
MANIFEST binding — deterministic computation of execution-critical hashes.

Purpose
-------
The MANIFEST must bind *actual, reproducible* hashes for:

  · each harness source file (component ID / version / hash);
  · the J rule bundle (all four modes together);
  · the reset profile;
  · the discriminator / rule bundles;
  · the fixture bundles (one per known-answer fixture).

This module computes those hashes from the CODE and the FROZEN rules, so the
MANIFEST is instantiated by *measurement*, not by hand-typing hex strings.

Determinism rules
-----------------
Every derived hash is SHA-256 over a canonical, order-stable byte encoding.
Lists are encoded in a fixed declared order; dictionaries are encoded with
sorted keys; integers are encoded as ASCII decimal; text is UTF-8.

NOTE: this module does NOT write hashes into the MANIFEST automatically, and
it does NOT self-hash the MANIFEST. Per SPEC §11, the MANIFEST hash lives in a
detached record to avoid self-reference.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Canonical encoding
# ---------------------------------------------------------------------------


def _canon(obj) -> bytes:
    """Deterministic byte encoding of a JSON-like structure."""
    if obj is None:
        return b"null"
    if isinstance(obj, bool):
        return b"true" if obj else b"false"
    if isinstance(obj, int):
        return b"int:" + str(obj).encode("ascii")
    if isinstance(obj, str):
        return b"str:" + obj.encode("utf-8")
    if isinstance(obj, (list, tuple)):
        parts = [b"list:["]
        for item in obj:
            parts.append(_canon(item))
            parts.append(b",")
        parts.append(b"]")
        return b"".join(parts)
    if isinstance(obj, dict):
        parts = [b"map:{"]
        for k in sorted(obj.keys()):
            parts.append(_canon(k))
            parts.append(b":")
            parts.append(_canon(obj[k]))
            parts.append(b",")
        parts.append(b"}")
        return b"".join(parts)
    raise TypeError(f"cannot canonicalize {type(obj)!r}")


def hash_obj(obj) -> str:
    return hashlib.sha256(_canon(obj)).hexdigest()


def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Component files (the code that implements each registered role)
# ---------------------------------------------------------------------------

COMPONENT_FILES = {
    "harness_constants": "harness_constants.py",
    "storage": "storage.py",
    "writers": "writers.py",
    "readers": "readers.py",
    "observer": "observer.py",
    "perturbation_j": "perturbation_j.py",
    "reset": "reset.py",
    "evaluator": "evaluator.py",
    "fixtures": "fixtures.py",
    # RC8: qualification-side runtime modules are now bound too.
    "fixture_contracts": "fixture_contracts.py",
    "gates": "gates.py",
    "qualification_binding": "qualification_binding.py",
    "run_known_answer_suite": "run_known_answer_suite.py",
    "verify_manifest_binding": "verify_manifest_binding.py",
    "adversarial_regression": "adversarial_regression.py",
    "recompute_from_ledger": "recompute_from_ledger.py",
}

#: Driven by harness_constants (single source of truth). Imported lazily to
#: avoid import cycles at module load.
def domain_partition() -> dict:
    from harness_constants import (
        IDENTITY_ONLY_COMPONENTS,
        LITERAL_STORAGE_COMPONENTS,
        NONSTORAGE_COMPONENT,
        NONSTATE_STORAGE_PIPELINE_NUISANCE_EXCLUSIONS,
        STATE_FIELD_LITERAL,
        STATE_FIELD_SUBSTRATE,
    )

    return {
        "STATE_FIELDS": sorted([STATE_FIELD_LITERAL, STATE_FIELD_SUBSTRATE]),
        "IDENTITY_ONLY_COMPONENTS": sorted(IDENTITY_ONLY_COMPONENTS),  # EMPTY
        "LITERAL_STORAGE_COMPONENTS": sorted(LITERAL_STORAGE_COMPONENTS),
        "NONSTORAGE_COMPONENT": sorted(NONSTORAGE_COMPONENT),
        "NONSTATE_STORAGE_PIPELINE_NUISANCE_EXCLUSIONS": sorted(
            NONSTATE_STORAGE_PIPELINE_NUISANCE_EXCLUSIONS
        ),
        "derived": {
            "ΔS_identity_masked": "ΔS_registered (identity mask empty)",
            "ΔS_nonstorage": "q change only (literal storage masked out)",
        },
    }



def component_hashes() -> dict:
    out = {}
    for role, fname in COMPONENT_FILES.items():
        p = HARNESS_DIR / fname
        out[role] = {
            "file": fname,
            "bytes": p.stat().st_size,
            "sha256": hash_file(p),
        }
    return out


# ---------------------------------------------------------------------------
# J rule bundle — all four modes frozen together
# ---------------------------------------------------------------------------

J_RULE_BUNDLE = {
    "J_NAME": "KNOWN_ANSWER_PRE_RESET_PERTURBATION",
    "J_SHORT": "J",
    "NAMESPACE": "HARNESS_VALIDATION_EXECUTION_ONLY",
    "SCIENTIFIC_CLAIM_ELIGIBILITY": "NONE",
    "modes": {
        "IDENTITY": {"literal": "unchanged", "q": "unchanged"},
        "COLLAPSE_SIGN": {"literal": "unchanged", "q": "nonzero->+2; zero->0"},
        "ERASE_EFFECT": {"literal": "16 zero bytes", "q": "0"},
        "HALVE_AND_ERASE_LITERAL": {
            "literal": "zeros",
            "q": "+2->+1; -2->-1; 0->0",
            "domain": "{0,+2,-2}",
        },
    },
    "ordering": ["IDENTITY", "COLLAPSE_SIGN", "ERASE_EFFECT", "HALVE_AND_ERASE_LITERAL"],
    # BD-52: observer MUST independently witness J's time point.
    "timing_witness": {
        "triple": ["S_write_digest", "J_after_digest", "S_handoff_digest"],
        "requirement": "J_after_digest == S_handoff_digest",
        "on_violation": "fixture = INVALID (J not proven to precede handoff)",
        "spec_ref": "SPEC §7.2 (merged from 15.3)",
    },
}


# ---------------------------------------------------------------------------
# Reset profile
# ---------------------------------------------------------------------------

RESET_PROFILE = {
    "RESET_PROFILE_ID": "PROCESS_REPLACE_PRESERVE_FILES_V1",
    "version": "1.0",
    "clear_preserve_table": [
        ["literal bytes", "PRESERVE"],
        ["substrate bytes", "PRESERVE"],
        ["model weight file", "PRESERVE_READ_ONLY"],
        ["old worker + memory", "CLEAR"],
        ["payload buffer / temp cache / counterfeit signal", "CLEAR"],
        ["old temp dir / input handles", "CLEAR"],
        ["reader / literal-consumer / schema / rules", "SAME_FROZEN_VERSION"],
        ["controller identity / ledger", "EXTERNAL_KEEP_NO_REINJECT"],
        ["original episode input / new write calls", "FORBIDDEN_REPLAY_AFTER_RESET"],
    ],
    "witnesses": ["clear-side", "preserve-side", "access-side"],
    "any_side_failure": "RESET_INVALID",
}


# ---------------------------------------------------------------------------
# Discriminator / rule bundles
# ---------------------------------------------------------------------------

RULE_BUNDLES = {
    "STATE_DELTA_RULE": {
        "id": "SYNTHETIC_STATE_DELTA_V1",
        "input_domain": "ΔS_identity_masked",
        "basic_l1": {"h=0": "negative", "h=1": "INDETERMINATE", "h>=2": "positive"},
    },
    "CAUSAL_CONTRAST_RULE": {
        "id": "SYNTHETIC_CAUSAL_CONTRAST_V1",
        "input_domain": "signed T over ΔS_nonstorage",
        "criterion": {"|T|>=1": "positive", "T=0": "negative", "0<|T|<1": "INDETERMINATE"},
        "signedness": "signed T stored in ledger",
    },
    "CONTENT_CONTRAST_RULE": {
        "id": "SYNTHETIC_CONTENT_CONTRAST_V1",
        "input_domain": "signed T over frozen class evidence set",
        "same_class": "exact equality",
        "cross_class": "exact inequality",
        "member_admission": "each member must first pass C2 (|T|>=1 -> attributed)",
        "abs_projection": "NOT in bundle (use => known-answer FAIL)",
    },
    "POST_RESET_CLASS_RULE": {
        "id": "SYNTHETIC_POST_RESET_CLASS_V1",
        "C1": "new observer reads 16-byte literal == registered payload exactly",
        "C2": "same logical pair C and B both reset; signed T passes same criterion",
        "C3": "full member set re-satisfies attribution + same/cross structure; no inherit",
        "lower_class": "independently re-established lower class kept even if higher fails",
        "not_attempted": "NOT_ASSESSED",
        # BD-53: FROZEN aggregation when no positive class is re-established.
        "L2_aggregation_rule_id": "SYNTHETIC_L2_AGGREGATION_V1",
        "L2_no_positive": {
            "any_attempted_indeterminate": "UNRESOLVED",
            "all_attempted_determinate_negative": "FAIL",
            "note": "lower-class determinate negative MUST NOT cancel higher-class indeterminate",
        },
    },
    "PERSISTENCE_MATCH_RULE": {
        "id": "SYNTHETIC_PERSISTENCE_MATCH_V1",
        "C1": "exact 16-byte payload match; file existence does NOT pass",
    },
}


# ---------------------------------------------------------------------------
# Content class manifest (the frozen class structure)
# ---------------------------------------------------------------------------

CONTENT_CLASS_MANIFEST = {
    "classes": {
        "L": {"episodes": ["A1", "A2"]},
        "R": {"episodes": ["B1", "B2"]},
    },
    "episode_payloads": {
        "A1": "cls=L;sample=01;",
        "A2": "cls=L;sample=02;",
        "B1": "cls=R;sample=01;",
        "B2": "cls=R;sample=02;",
    },
    "payload_length": 16,
    "same_class_pairs": [["A1", "A2"], ["B1", "B2"]],
    "cross_class_pairs": [["A1", "B1"], ["A2", "B2"]],
    "distinct_procedures": [
        "same-class: different episodes (A1 vs A2) -> class generalization",
        "replay: same episode -> repeatability control only (not class generalization)",
    ],
}


# ---------------------------------------------------------------------------
# Fixture bundles: each fixture freezes its rule bundle + unique oracle
# ---------------------------------------------------------------------------

FIXTURE_BUNDLES = {
    "V0": {
        "construction": "A NO_WRITE; B W_storage ON with STORE_NULL (on-invoked, zero-effect)",
        "oracle": {"L1": "FAIL"},
    },
    "V0b": {
        "construction": "A NO_WRITE; B STORE_ONE_BYTE (h=1)",
        "oracle": {"L1": "UNRESOLVED"},
    },
    "V1": {
        "construction": "A NO_WRITE; B STORE_FULL; only B/A attempted",
        "oracle": {"L1": "PASS", "PRE_RESET_CHANGE_CLASS": "C1",
                   "C2": "NOT_ASSESSED", "C3": "NOT_ASSESSED"},
    },
    "V2": {
        "construction": "A/B/C; STORE_FULL + EXTRA_CONSTANT; full C3 attempt",
        "oracle": {"L1": "PASS", "PRE_RESET_CHANGE_CLASS": "C2", "C3": "NOT_ESTABLISHED"},
    },
    "V3": {
        "construction": "A/B/C; STORE_FULL + EXTRA_CONTENT; full C3 attempt",
        "oracle": {"L1": "PASS", "PRE_RESET_CHANGE_CLASS": "C3", "C3": "C3"},
    },
    "V4.1": {
        "construction": "PRE_RESET/C2 attempt; CAUSAL_CONTRAST_RULE deliberately missing (tested config); no post-reset claim",
        "attempted_scope": {
            "pre_reset_C1": True,
            "pre_reset_C2": True,
            "pre_reset_C3": False,
            "post_reset": False,
        },
        "oracle": {
            "L1": "PASS",
            "PRE_RESET_CHANGE_CLASS": "C1",
            "C2_ATTEMPT": "INVALID",
            "INVALIDITY_CODE": "CAUSAL_CONTRAST_RULE_MISSING",
            "C3": "NOT_ASSESSED",
            "L2": "N/A",
        },
    },
    "V4b": {
        "construction": "isolated wrapper: W_extra ON/OFF not separable",
        "oracle": {"L1": "PASS", "PRE_RESET_CHANGE_CLASS": "C1",
                   "C2": "ARCHITECTURALLY_NOT_IDENTIFIABLE",
                   "C3": "ARCHITECTURALLY_NOT_IDENTIFIABLE"},
    },
    "V5a": {"construction": "REAL full pipeline; V3 pre; J=IDENTITY; reset ALL arms; post C1/C2/C3 rebuilt from POST-RESET reads",
            "j_timing_required": "J_after_digest == S_handoff_digest",
            "all_arms_reset": True,
            "post_from_post_reset_reads": True,
            "oracle": {"L2": "PASS", "POST_RESET_SUPPORTED_CLASS": "C3", "j_timing_ok": True}},
    "V5b": {"construction": "REAL full pipeline; V3 pre; J=COLLAPSE_SIGN; reset ALL arms; post T collapse",
            "j_timing_required": "J_after_digest == S_handoff_digest",
            "all_arms_reset": True,
            "post_from_post_reset_reads": True,
            "oracle": {"L2": "PASS", "POST_RESET_SUPPORTED_CLASS": "C2",
                       "post_C3": "NOT_ESTABLISHED", "j_timing_ok": True}},
    "V5c": {"construction": "REAL full pipeline; V3 pre; J=IDENTITY; preserve-side reset fault after handoff; reset INVALID",
            "j_timing_required": "J_after_digest == S_handoff_digest",
            "all_arms_reset": True,
            "post_from_post_reset_reads": True,
            "oracle": {"L2": "INVALID", "reset_valid": False}},
    "V5d": {"construction": "REAL full pipeline; V3 pre; J=ERASE_EFFECT; reset ALL arms",
            "j_timing_required": "J_after_digest == S_handoff_digest",
            "all_arms_reset": True,
            "post_from_post_reset_reads": True,
            "oracle": {"L2": "FAIL", "j_timing_ok": True}},
    "V5e": {"construction": "REAL full pipeline; V3 pre; J=HALVE_AND_ERASE_LITERAL; reset ALL arms",
            "j_timing_required": "J_after_digest == S_handoff_digest",
            "all_arms_reset": True,
            "post_from_post_reset_reads": True,
            "l2_rule": "SYNTHETIC_L2_AGGREGATION_V1 (C1 determinate neg does NOT cancel indeterminate)",
            "oracle": {"L2": "UNRESOLVED", "j_timing_ok": True}},
    "V5f": {"construction": "REAL pipeline; V1 pre; J=IDENTITY; valid reset; only post C1 attempted",
            "j_timing_required": "J_after_digest == S_handoff_digest",
            "post_from_post_reset_reads": True,
            "oracle": {"L2": "PASS", "POST_RESET_SUPPORTED_CLASS": "C1",
                       "post_C2": "NOT_ASSESSED", "post_C3": "NOT_ASSESSED", "j_timing_ok": True}},
}


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------


def compute_all() -> dict:
    return {
        "components": component_hashes(),
        "J_RULE_BUNDLE_HASH": hash_obj(J_RULE_BUNDLE),
        "RESET_PROFILE_HASH": hash_obj(RESET_PROFILE),
        "RULE_BUNDLE_HASHES": {k: hash_obj(v) for k, v in RULE_BUNDLES.items()},
        "DISCRIMINATION_RULESET_HASH": hash_obj(
            {
                "id": "SYNTHETIC_DISCRIMINATION_RULESET_V1",
                "members": RULE_BUNDLES,
                "order": list(RULE_BUNDLES.keys()),
            }
        ),
        "CONTENT_CLASS_MANIFEST_HASH": hash_obj(CONTENT_CLASS_MANIFEST),
        "CONTENT_CLASS_EVIDENCE_SET_HASH": hash_obj(CONTENT_CLASS_MANIFEST["episode_payloads"]),
        "DOMAIN_PARTITION_HASH": hash_obj(domain_partition()),
        "FIXTURE_RULE_BUNDLE_HASHES": {k: hash_obj(v) for k, v in FIXTURE_BUNDLES.items()},
    }


def manifest_self_hash(manifest_path: Path) -> dict:
    """Compute the MANIFEST's own hash for the DETACHED record.

    Never written back into the MANIFEST (avoids self-reference).
    """
    p = Path(manifest_path)
    return {
        "manifest_file": p.name,
        "bytes": p.stat().st_size,
        "sha256": hash_file(p),
        "algorithm": "SHA-256 over exact file bytes",
    }


def main() -> None:
    import json

    print(json.dumps(compute_all(), indent=2, ensure_ascii=False))


def dump_table() -> None:
    """Flat table of the values that must be pasted into the MANIFEST."""
    d = compute_all()
    for role in sorted(d["components"]):
        info = d["components"][role]
        print(f"{info['file']:<24} {info['bytes']:>6} {info['sha256']}")
    print()
    for k in ("J_RULE_BUNDLE_HASH", "RESET_PROFILE_HASH",
              "DISCRIMINATION_RULESET_HASH", "CONTENT_CLASS_MANIFEST_HASH",
              "CONTENT_CLASS_EVIDENCE_SET_HASH"):
        print(f"{k:<32} {d[k]}")
    print()
    for k in sorted(d["RULE_BUNDLE_HASHES"]):
        print(f"RULE {k:<34} {d['RULE_BUNDLE_HASHES'][k]}")
    print()
    for k, v in d["FIXTURE_RULE_BUNDLE_HASHES"].items():
        print(f"FIXTURE {k:<30} {v}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "table":
        dump_table()
    else:
        main()
