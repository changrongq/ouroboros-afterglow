# RC11 DETACHED RECORD — EXTERNAL ERRATUM (OBS-1)

**Issued by**: Coder
**Date**: 2026-10-12
**Authority**: 凌翼 LINGYI REVIEW — Q3 / RC11 (2026-10-12), REVIEWED_HEAD = `68bc80f`
  > "OBS-1 = CONFIRMED. Record-table inconsistency. Preserve frozen bytes.
  >  Attach external erratum."
**Scope**: EXTERNAL record only. This file is **NOT** part of the frozen RC11 objects
and does **NOT** modify any RC11 byte.

---

## 1. The defect (睫 OBS-1, CONFIRMED)

`reports/MANIFEST_v0.1_HASH.txt` (the DETACHED hash record) contains a
"Component source hashes" table whose membership is **inconsistent** with the
RC11 execution-critical role registry (`qualification_role_registry.EXECUTION_CRITICAL_ROLES`):

- **Missing** (execution-critical, absent from the detached table):
  - `evidence_contract.py`
  - `replay_adapter.py`
- **Extra** (build provenance, present in the detached table):
  - `manifest_bind.py`
  - `freeze_manifest.py`

## 2. Why this did NOT make RC11 fail-open (凌翼 verified)

The runtime verifier `qualification_binding.verify()` does **NOT** consume the
detached file's component table as the authoritative role set. It uses:
1. the **frozen MANIFEST**'s EXECUTION_CRITICAL_ROLE_TABLE section,
2. the **registry** (`qualification_role_registry.EXECUTION_CRITICAL_ROLES`),
3. the **actual source files'** SHA-256.

The detached file is consumed only for the **manifest-hash** match
(`detached_match`), not for role-set membership. Therefore OBS-1 is a
**provenance-record inconsistency**, not an execution-time fail-open.

## 3. Frozen bytes (UNCHANGED — verified at erratum time)

| Object | bytes | sha256 |
|---|---|---|
| `AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md` | 28142 | `78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059` |
| `MANIFEST_v0.1_HASH.txt` (detached) | (unmodified) | (unmodified — see file) |

`verify_manifest_binding.py` at erratum time: **BINDING_INTEGRITY = PASS**.

## 4. Disposition

- **RC11 frozen bytes: DO NOT MODIFY** (凌翼). This erratum is external.
- **If RC12 is established**, generate a **consistent new detached record** as part
  of RC12 (its component table must match `EXECUTION_CRITICAL_ROLES` exactly:
  20 execution-critical roles; build-provenance listed separately).
- **Historical status unchanged**: `RC11_PHASE_A = CLOSED / HISTORICAL`.

## 5. Cross-reference

- 睫 OBS-1 / OBS-2: see `给凌翼睫知微_Q3RC11_对睫独立核验的回应_20261012.md`.
- 凌翼 ruling: `LINGYI REVIEW — Q3 / RC11` (REVIEWED_HEAD `68bc80f`).
