# RC12 — Detached-Binding Hardening (CANDIDATE)

**Authority**: 凌翼 LINGYI REVIEW — Q3 / RC11 (2026-10-12), REVIEWED_HEAD `68bc80f`
**Status**: `RC12_STATUS = CANDIDATE (NOT yet qualified)`
**Relation to RC11**: parallel candidate. **RC11 remains the CLOSED historical lineage;
its frozen bytes are NOT modified.**

---

## What RC12 is (and is not)

- **IS**: a **targeted** hardening of ONE thing — the detached-record match
  (`OBS-2`). RC12 is a new, separate lineage that must earn its own qualification.
- **IS NOT**: a rewrite of Q3, a rollback of RC11's Phase A, or a license to edit
  frozen RC11 bytes. 凌翼: "不能把 RC11 的历史冻结文件偷偷修掉，也不必因为 OBS-2
  而重做 Q3 全部工程。"

## The defect it fixes (OBS-2, CONFIRMED)

RC11 `qualification_binding.verify()`:
```python
ev["detached_match"] = bool(
    detached_path.exists() and manifest_sha in detached_path.read_text(encoding="utf-8"))
```
`manifest_sha in text` is a **substring** test. Consequences:
- a hash appearing only in a **comment** would match;
- once the detached file records a **lineage** (several historical hashes), an
  **old** hash could still match its own line — but more importantly, the check
  cannot distinguish "bound to THIS object" from "appears somewhere".

## The RC12 fix

`afterglow_harness/qualification_binding_rc12.py` — `strict_detached_match()`:
1. parse the **unique** authoritative line
   `IMPLEMENTATION_BINDING_MANIFEST_HASH = <64hex>` (anchored);
2. **exactly one** such line (duplicate ⇒ reject);
3. field value **exactly equals** the actual manifest SHA-256;
4. `MANIFEST_BYTES` (if present) exactly equals the actual byte count;
5. a hash present **only** in a comment / non-authoritative line ⇒ reject.

Selftest: **8/8** (incl. the comment-only hole that RC11 would have passed).

## RC12 acceptance checklist (before RC12 can be declared QUALIFIED)

- [ ] E-1 RC12 role registry (includes `qualification_binding_rc12.py`; RC11 roles kept intact).
- [ ] E-2 New consistent detached record (component table == `EXECUTION_CRITICAL_ROLES`,
      20 roles; build-provenance listed separately) — resolves OBS-1.
- [ ] E-3 New RC12 MANIFEST + detached HASH record (LF), self-reference forbidden.
- [ ] E-4 `qualification_binding_rc12.strict_detached_match` wired as the runtime match.
- [ ] E-5 Adversarial regressions (comment-only, duplicate field, lineage, wrong bytes).
- [ ] E-6 Independent reviewer replay + 凌翼 adjudication.
- [ ] E-7 RC11 historical status preserved (`RC11_PHASE_A = CLOSED / HISTORICAL`).

## Provenance

- RC12 source file: `afterglow_harness/qualification_binding_rc12.py`
  (hash recorded when the RC12 candidate is frozen — NOT in this README).
