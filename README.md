# ouroboros-afterglow

AFTERGLOW Reference Harness — shared workspace for **凌翼 / 睫 / Coder / 船长**.

This repository is a **shared, read-oriented snapshot** of the Afterglow Reference Harness
and its implementation-binding freeze chain. It exists so 凌翼 and 睫 can independently
verify the artifacts without relying on a chat attachment.

---

## Layout

```
prereg/                  # frozen preregistration (FREEZE_CANDIDATE = frozen ad0855b0…)
spec/                    # frozen SPEC object + freeze record
reports/                 # implementation-binding MANIFEST + detached hash record + errata
reports/review_history/  # correspondence + review reports
afterglow_harness/       # the Reference Harness source (flat module layout, all .py)
artifacts/RC7/ RC8/ RC9/ RC10/ RC11/   # frozen run artifacts, one dir per candidate
tests/                   # (reserved)
README.md / VERIFY.md / .gitattributes / .gitignore
```

> **Deviation from the intended tree (documented honestly):** the MANIFEST lives under
> `reports/`, not a separate `manifest/`. Reason: the frozen, hash-bound drivers
> (`run_known_answer_suite.py`, `verify_manifest_binding.py`) hard-code
> `../reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md`. Moving the MANIFEST
> without editing those drivers would invalidate their bound hashes. All harness `.py`
> are kept in one flat directory (they import each other by bare module name). RC8 will
> introduce a bound qualification-binding module and may revisit this layout.

---

## Qualification lineage

```text
RC7  = FAILED QUALIFICATION / RETAINED FOR AUDIT (adversarial false-PASS defects)
RC8  = FAILED QUALIFICATION / RETAINED FOR AUDIT (seams: reader/pre-class/handoff/member/binding)
RC9  = NOT CLOSED / RETAINED FOR AUDIT (知微 4 P1)
RC10 = NOT CLOSED / RETAINED FOR AUDIT (知微 4 P1)
RC11 = CLOSED  (PHASE_A_QUALIFICATION = PASS; 凌翼 FINAL ADJUDICATION)
```

MANIFEST lineage: RC1 `b3802142…` → … → RC7 `c61d8aa7…`(FAILED) → RC8 `61cbfd9f…`(FAILED)
→ RC9 `67dfb538…`(NOT CLOSED) → RC10 `dd30e3ad…`(NOT CLOSED)
→ **RC11 `78bdb90f…`（CLOSED）**。

---

## RC11 — closure round (凌翼 R1–R5 + 知微 RC9/RC10/RC11 reviews)

```text
IMPLEMENTATION_BINDING_MANIFEST_HASH (RC11) = 78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059
REFERENCE_HARNESS_SPEC_HASH                 = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33
PARENT_PREREG_SHA256                        = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
```

RC11 repairs (all fail-open -> fail-closed):
- **ONE adjudication chain, TWO ingress**: `evidence_bundle.evaluate_bundle` is the sole judge;
  production (`fixtures.py`) builds the bundle from live runtime, replay (`replay_adapter.py`)
  builds it from raw ledger + the canonical contract (`evidence_contract.CONTRACT_BY_FIXTURE`).
  The ledger answers "what did I observe", never "what was required".
- **REQUIRED_EVIDENCE_CONSUMPTION_MATRIX**: every required field must be RECORDED ∧ CONSUMED
  (production) ∧ CONSUMED (replay) ∧ NEGATIVE-TESTED; missing/empty/malformed ⇒ FAIL CLOSED.
- **Same-run link**: `run_known_answer_suite.py` writes `RC11_run_manifest.json`; the single
  entry point replays THAT ledger dir — no hard-coded version path.
- **reader gate**: EXACT frozen probe set {0,2}; expected derived from `S_restored`; `raw_q` is a
  redundant cross-check only.
- **reset gate**: `reset_valid` mandatory (missing/malformed ⇒ INVALID); reset-preserve rule
  recomputed from raw bytes (`accepted_handoff == verified_restored`).
- **fixture identity**: filename stem == outer id == inner ledger id; unique; exact frozen 13-set.
- **V4.1/V4b**: full decision schema compared; V4b probe does STRUCTURAL + BEHAVIORAL (real ON/OFF
  calls) with a separable positive control.
- **Structured sub-verdicts** are tri-state (True/False/UNEVALUATED); a default is never True.
- **Adversarial regression** (54/54): all of the above, plus all prior RC7/RC8/RC9 false-PASS attacks.

---

## Status

```text
PHASE_A_QUALIFICATION = PASS (RC11)  [by qualify_phase_a.py: suite + adversarial + replay]
RC11 = CLOSED                        [凌翼 FINAL ADJUDICATION on commit 5e17fe8]
SCIENTIFIC_CLAIM_ELIGIBILITY  = NONE
OS_LEVEL_ISOLATION            = NOT ESTABLISHED
SCIENTIFIC_EXECUTION          = MAY NOT START
```

---

## What this is NOT

- Not scientific evidence of memory / Afterglow mechanism (PHASE A is harness validation).
- Not authorized for scientific execution (OS-level isolation is not yet implemented;
  the reset layer is logic-level only — see the MANIFEST §十).
