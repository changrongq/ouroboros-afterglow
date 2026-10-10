# Review & Adversarial History — INDEX

**有历史，有来路。** This is the chronological record of the adversarial review chain
that produced RC7 (failed) → RC8, plus the reproduction scripts.

> Authoritative current identity: see `../AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md`
> and `../MANIFEST_v0.1_HASH.txt`. This index is navigation only.

---

## The review chain (most recent last)

| # | Date | Who | Artifact | What it found / did |
|---|---|---|---|---|
| 1 | 2026-10-06 | 凌翼 / 知微 / 睫 | `AFTERGLOW_SYNTHETIC_HARNESS_PROPOSAL_ZHIWEI_v0.1.md`, `AFTERGLOW_REFERENCE_HARNESS_合并提案_v0.1.md` | initial harness design + merged proposal |
| 2 | 2026-10-08 | Coder | `给睫凌翼_FROZEN前hash核对_Coder_20261008.md` | pre-freeze hash reconciliation |
| 3 | 2026-10-09 | Coder | `给睫知微凌翼_SPEC_hash说明_Coder_20261009.md` | SPEC hash dispute (1386ba22 vs b7ec1dca) |
| 4 | 2026-10-09 | Coder | `AFTERGLOW_SPEC_RootAnchor_Decision_Coder_20261009.md` | root-anchor decision |
| 5 | 2026-10-09 | Coder | `给凌翼睫_SPEC锚点修正_RC4_说明_Coder_20261009.md` | RC4 root-anchor fix |
| 6 | 2026-10-09 | Coder | `AFTERGLOW_HARNESS_BD52_BD53_Impact_Assessment_Coder_20261009.md` | BD-52 / BD-53 assessment |
| 7 | 2026-10-09 | Coder | `给凌翼睫_BD55修复_RC5_独立核验 包_Coder_20261009.md` | BD-55 fix (RC5) |
| 8 | 2026-10-09 | Coder | `给凌翼睫_BD56修复_RC6_交付清单_Coder_20261009.md` | BD-56 fix (RC6) |
| 9 | 2026-10-10 | **知微** | `知微_仓库独立审阅_4b758b0.md` + `reproduce_review.py` | **independent review**: CRLF binding drift; V2/V3 discard L1; V5 uses pre-reset; ledger cross-arm; unbound helper |
| 10 | 2026-10-10 | Coder | `给凌翼知微_BD57_审阅答复_独立复核_Coder_20261010.md` | my independent reproduction of every item (all confirmed) |
| 11 | 2026-10-10 | Coder | `给凌翼_RC7未闭合简报_Coder_20261010.md` | RC7 declared NOT closed; escalation to 凌翼 |
| 12 | 2026-10-10 | 凌翼 | （裁定，见报告内引用） | R1–R4: one RC8 closure round; remove manifest_bind from runtime; V4b non-separable; retain RC7 |
| 13 | 2026-10-10 | **知微** | `知微_RC7闭合复核_63539ab.md` + `review_rc7.py` | **second review**: J-timing not gated; failure-default C3; ledger cross-arm; unbound runtime; V4b separable; reader q=0 |
| 14 | 2026-10-10 | Coder | `给凌翼睫知微_BD57_审阅P1_闭合报告_RC7_Coder_20261010.md` | RC7 per-item closure attempt |
| 15 | 2026-10-10 | Coder | `给凌翼睫知微_RC8交付报告_Coder_20261010.md` | **RC8 delivery**: two-gate architecture, single oracle, raw ledger, bound runtime, adversarial 15/15 |

---

## Reproduction scripts (independent, non-qualifying)

- `reproduce_review.py` — 知微's first-review reproduction (byte drift + V2/V3 + V5 attacks).
- `review_rc7.py` — 知微's RC7-closure reproduction.
- `../../afterglow_harness/adversarial_regression.py` — the RC8 regression (all attacks must be rejected).
- `../../afterglow_harness/recompute_from_ledger.py` — independent re-derivation from raw ledger.

---

## Status snapshot

```text
RC7 = FAILED QUALIFICATION / RETAINED FOR AUDIT  (this history is the evidence that the
      adversarial machinery actually caught real errors)
RC8 = current candidate  (see delivery report)
```
