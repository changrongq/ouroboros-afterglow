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

## Qualification lineage

```text
RC7 = FAILED QUALIFICATION / RETAINED FOR AUDIT (adversarial false-PASS defects)
RC8 = FAILED QUALIFICATION / RETAINED FOR AUDIT (seams: reader/pre-class/handoff/member/binding)
RC9 = CURRENT CANDIDATE  (all fail-open -> fail-closed)
```

MANIFEST lineage: RC1 `b3802142…` → … → RC7 `c61d8aa7…`(FAILED) → RC8 `61cbfd9f…`(FAILED)
→ **RC9 `67dfb538…`（current candidate）**。

---

## RC9 — closure round (凌翼 R1–R4 + 知微 RC8 review §11)

```text
IMPLEMENTATION_BINDING_MANIFEST_HASH (RC9) = 67dfb5380e8c3a0f6adaaa37372f339cf373202339324062b0aeefd16c7ec7aa
REFERENCE_HARNESS_SPEC_HASH                = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33
PARENT_PREREG_SHA256                       = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
```

RC9 repairs (all fail-open -> fail-closed):
- **ONE evidence object**: `evidence_bundle.EVIDENCE_BUNDLE` = member × arm × phase × raw × witness;
  both production and replay must use it.
- **ONE public chain**: member-set → arms/phases → S_write → PRE → **required_pre_class** →
  J witness → **J.S_handoff == RESET accepted handoff (byte-level)** → reset → S_restored →
  **reader/literal witnesses** → POST → L2. **INVALID dominates everywhere.**
- **ONE role registry**: `qualification_role_registry.py` (data only); MANIFEST §十三 uses
  `EXECUTION_CRITICAL_ROLE_TABLE_BEGIN/END`; **three-way exact equality** (registry == MANIFEST == files).
- **`manifest_bind.py` is BUILD_PROVENANCE only** (removed from runtime).
- **`qualify_phase_a.py`** = the SINGLE PASS entry (suite AND adversarial AND ledger replay).
- **`recompute_from_ledger.py`**: REQUIRED_SCOPE per fixture; zero-check ⇒ FAIL; digest recomputed from raw bytes.
- **V4b** = `CombinedOnlyWriter` + `external_capability_probe` (no public Arm/store/mode/selector).
- **Adversarial regression** (16/16): bad J timing · handoff discontinuity · missing member ·
  constant reader · constant-pre V5b · invalid reset V5f · V4b probe · empty roles · empty C3 · INVALID L2.

---

## Status

```text
PHASE_A_QUALIFICATION = PASS (RC9)   [by qualify_phase_a.py: suite + adversarial + replay]
SCIENTIFIC_CLAIM_ELIGIBILITY  = NONE
SCIENTIFIC_EXECUTION          = MAY NOT START
```

---

## What this is NOT

- Not scientific evidence of memory / Afterglow mechanism (PHASE A is harness validation).
- Not authorized for scientific execution (OS-level isolation is not yet implemented;
  the reset layer is logic-level only — see the MANIFEST §十).
