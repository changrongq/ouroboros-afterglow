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
artifacts/RC7/           # RC7 run artifacts (see WARNING below — RC7 FAILED qualification)
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

## ⚠️ RC7 STATUS — FAILED QUALIFICATION / RETAINED FOR AUDIT

```text
RC7 = NOT CLOSED
RC7 QUALIFICATION = FAIL / NON-QUALIFYING
REASON = ADVERSARIAL FALSE-PASS DEFECTS (independent review reproduced)
AUTHORITATIVE_FOR_SCIENTIFIC_EXECUTION = NO
```

RC7's own run reported 13/13, **but** an independent adversarial review (review_history)
reproduced false-PASS inputs. RC7 is retained unchanged as an audit record.

MANIFEST lineage: RC1 `b3802142…` → … → RC7 `45acd8b1…`→`c61d8aa7…`（FAILED）
→ **RC8 `61cbfd9f…`（current candidate）**。

---

## RC8 — closure round (凌翼 R1–R4 + 知微 §10)

```text
IMPLEMENTATION_BINDING_MANIFEST_HASH (RC8) = 61cbfd9f78e545ef5bc8f0bdd87fd10064721dea06d0de879537a2e6ca5a99ed
REFERENCE_HARNESS_SPEC_HASH                = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33
PARENT_PREREG_SHA256                       = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
```

RC8 repairs (all of 知微 §2–§9 + 凌翼's R1–R4):
- **Two public gates only**: `PRE_EVIDENCE_GATE` (source = **S_write**; L1→C1→C2→C3; **no failure-default C3**)
  and `POST_RESET_EVIDENCE_GATE` (source = **S_restored only**; **INVALID dominates**), plus `J_GATE`/`RESET_GATE`.
- **Single frozen oracle source** = `fixture_contracts.FROZEN_ORACLES` (fixtures take config only;
  runner takes oracle only; `evaluator` takes neither).
- **Ledger** = raw observations per **member × arm × phase**; independently recomputable
  (`recompute_from_ledger.py` re-derives via the same gates).
- **`manifest_bind.py` removed from the qualifying runtime**; `qualification_binding.py` (bound) verifies
  a non-empty, exact required-role set (empty set FAILS).
- **V4b** = `CombinedOnlyWriter` (no ON/OFF selector in the capability surface).
- **Reader witness** reads a **non-zero** C-arm q.
- **Adversarial regression** (all attacks rejected): bad J timing · storage no-op · constant extra ·
  invalid reset V5f · V4b separability · constant reader · empty component-set · empty C3 · INVALID L2.

---

## Status

```text
PHASE_A_HARNESS_QUALIFICATION = RC7 FAILED; RC8 = QUALIFYING RUN (awaiting independent review)
SCIENTIFIC_CLAIM_ELIGIBILITY  = NONE
SCIENTIFIC_EXECUTION          = MAY NOT START
```

---

## What this is NOT

- Not scientific evidence of memory / Afterglow mechanism (PHASE A is harness validation).
- Not authorized for scientific execution (OS-level isolation is not yet implemented;
  the reset layer is logic-level only — see the MANIFEST §十).
