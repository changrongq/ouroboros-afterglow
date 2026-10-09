# ouroboros-afterglow

AFTERGLOW Reference Harness — shared workspace for **凌翼 / 睫 / Coder / 船长**.

This repository is a **shared, read-oriented snapshot** of the Afterglow Reference Harness
and its implementation-binding freeze chain. It exists so 凌翼 and 睫 can independently
verify the artifacts without relying on a chat attachment.

---

## Layout

```
afterglow_harness/    # the Reference Harness source (the thing being verified)
artifacts/            # RC6 qualifying run: raw machine-readable output + 13 ledgers
reports/              # frozen SPEC, prereg, MANIFEST, freeze records, errata, reports
```

---

## Current frozen state (RC6)

```text
REFERENCE_HARNESS_SPEC_HASH          = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33
                                       （= reports/AFTERGLOW IMPLEMENTATION BINDING v0.1.md, 36719 B, LF）
IMPLEMENTATION_BINDING_MANIFEST_HASH = ba1202769ed5a8c7e58a3809967e2593ddb89fbfb85bde5d99616883c440af93
                                       （= reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md, 22904 B, LF）
PARENT_PREREG_SHA256                 = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
```

MANIFEST lineage: RC1 `b3802142…` → RC2 `6cf3f7e3…` → RC3 `718d86fe…` → RC4 `d6a0f36d…`
→ RC5 `2b38e69f…` → **RC6 `ba120276…`（current）**.

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
