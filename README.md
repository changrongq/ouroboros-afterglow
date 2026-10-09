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
artifacts/RC7/           # RC7 qualifying run: raw machine-readable output + ledgers/
tests/                   # (reserved)
README.md / VERIFY.md / .gitattributes / .gitignore
```

> **Deviation from the intended tree (documented honestly):** the MANIFEST lives under
> `reports/`, not a separate `manifest/`. Reason: the frozen, hash-bound drivers
> (`run_known_answer_suite.py`, `verify_manifest_binding.py`) hard-code
> `../reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md`. Moving the MANIFEST would
> require editing those drivers → changing their bound hashes → invalidating RC6.
> All harness `.py` are kept in one flat directory for the same reason (they import each
> other by bare module name). Both are deliberate, to keep the frozen binding intact.


---

## Current frozen state (RC7)

```text
REFERENCE_HARNESS_SPEC_HASH          = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33
                                       （= spec/AFTERGLOW_IMPLEMENTATION_BINDING_v0.1.md, 36719 B, LF）
IMPLEMENTATION_BINDING_MANIFEST_HASH = 45acd8b1c38142f43e3102b79d8467a0312e114e6a4771ea56dcad6be18cba89
                                       （= reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md, 23700 B, LF）
PARENT_PREREG_SHA256                 = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
                                       （= prereg/AFTERGLOW_MVP_PREREGISTRATION_v0.1.md, 52129 B, LF）
```

MANIFEST lineage: RC1 `b3802142…` → RC2 `6cf3f7e3…` → RC3 `718d86fe…` → RC4 `d6a0f36d…`
→ RC5 `2b38e69f…` → RC6 `ba120276…` → **RC7 `45acd8b1…`（current）**。

**RC7 repairs (BD-57 + independent review):**
- all source `.py` converted to **LF** (eliminates the CRLF/LF binding drift);
- V2/V3 consume the **real** L1/C2/C3 (no discarded/hard-coded results);
- V5 rebuilds **post-reset** C1/C2/C3 from **post-reset** reads (reset all required arms);
- observer + both registered read paths are actually invoked;
- qualification preflight checks drivers + the ACTUAL SPEC/prereg files + the fixture set.

---

## Status

```text
PHASE_A_HARNESS_QUALIFICATION = PENDING（待凌翼 / 睫 独立核验签署）
SCIENTIFIC_CLAIM_ELIGIBILITY  = NONE
SCIENTIFIC_EXECUTION          = MAY NOT START（OS 级隔离尚未落地）
```

The qualifying run reported 13/13 oracle match, bound to the frozen SPEC + MANIFEST above.
Independent verification instructions are in `VERIFY.md`.

---

## What this is NOT

- Not scientific evidence of memory / Afterglow mechanism (PHASE A is harness validation).
- Not authorized for scientific execution (OS-level isolation is not yet implemented;
  the reset layer is logic-level only — see `reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md` §十).
