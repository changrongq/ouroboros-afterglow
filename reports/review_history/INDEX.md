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
| 15 | 2026-10-10 | Coder | `给凌翼睫知微_RC8交付报告_Coder_20261010.md` | **RC8 delivery**: two-gate architecture, single oracle, raw ledger, bound runtime |
| 16 | 2026-10-10 | **知微** | `知微_RC8独立复核_e099ddf.md` + `review_rc8.py` / `review_rc8_followup.py` | **third review**: 7 P1 seams (reader not gated, pre-class not enforced, ledger zero-check, J↔reset unlinked, missing-member downgrade, role-set mismatch, V4b public arm) |
| 17 | 2026-10-10 | Coder | `给凌翼_RC8未闭合简报_Coder_20261010.md` | RC8 declared NOT closed; escalation to 凌翼 |
| 18 | 2026-10-10 | 凌翼 | （R1–R4 裁定） | one RC9 closure round; single role registry; V4b external probe; retain RC8 |
| 19 | 2026-10-10 | Coder | `给凌翼睫知微_RC9交付报告_Coder_20261010.md` | **RC9 delivery**: EVIDENCE_BUNDLE; single public chain; single role registry; qualify_phase_a single entry; adversarial 16/16 |
| 20 | 2026-10-10 | **知微** | `知微_RC9独立复核_2a0737b.md` | **fourth review**: 4 P1 (reader empty-probe hole; replay does not restore contract; V4b probe misses selector; reset_valid missing + restored unlinked) |
| 21 | 2026-10-10 | Coder | `给凌翼_RC9复核裁决请求_Coder_20261010.md` | RC9 per-item reproduction (all four confirmed); request ruling |
| 22 | 2026-10-10 | 凌翼 | （R1–R5 裁定） | RC9 = NOT CLOSED; RC10 AUTHORIZED; +REQUIRED_EVIDENCE_CONSUMPTION_MATRIX; one chain two ingress; preserve RC9 |
| 23 | 2026-10-10 | Coder | `给凌翼睫知微_RC10交付报告_Coder_20261010.md` | **RC10 delivery**: single adjudication chain + dual ingress; reader/reset/replay/V4b fail-closed; 6 top acceptance tests + 4 P1 all PASS |
| 24 | 2026-10-10 | **知微** | `知微_RC10独立复核_ca4c510.md` | **fifth review**: 4 P1 bug (single-entry reads stale RC9_ledgers; V4 special results unchecked; 13-set checks filenames only; reset preserve not recomputed) + §8 wording/impl |
| 25 | 2026-10-10 | Coder | `给知微凌翼睫_RC11交付报告_Coder_20261010.md` | **RC11 delivery** (Bug fix, no ruling needed): same-run manifest link; V4 full schema compared; 3-way fixture identity; preserve rule recomputed; structured sub-verdicts; adversarial 43/43 |
| 26 | 2026-10-10 | **知微** | `知微_RC11独立复核_525f81f.md` | **sixth review**: 4 P1 CLOSED confirmed; 2 P2 kept (P2-A reset_identity_ok truthfulness; P2-B behavioral_split from signature not real call) |
| 27 | 2026-10-10 | Coder | `给知微凌翼睫_RC11_P2闭合报告_Coder_20261010.md` | **RC11 P2 closure**: tri-state sub-verdicts (UNEVALUATED); real ON/OFF behavioral calls; adversarial 51/51 |
| 28 | 2026-10-10 | **知微** | `知微_RC11_P2复核_c11063c.md` | **seventh review**: P2-B real-call CLOSED; P2-A PARTIAL (3 adjacent identity-failure branches still default True) + P2-B docstring overclaim |
| 29 | 2026-10-10 | Coder | `给知微凌翼睫_RC11_P2A补全报告_Coder_20261010.md` | **RC11 P2-A complete**: all identity-stage failures return (True,False,False,UNEVALUATED); docstring narrowed; adversarial 54/54 |
| 30 | 2026-10-10 | **知微** | `知微_RC11_P2A闭合确认_5e17fe8.md` | **eighth review / closure**: P2-A CLOSED (84/84 error cases across member×arm); clean entry PASS; adversarial 54/54; both P2 now closed |

---

## Reproduction scripts (independent, non-qualifying)

- `reproduce_review.py` — 知微's first-review reproduction (byte drift + V2/V3 + V5 attacks).
- `review_rc7.py` — 知微's RC7-closure reproduction.
- `review_rc8.py` / `review_rc8_followup.py` — 知微's RC8-closure reproduction (7 P1 seams).
- `../../afterglow_harness/_verify_rc10_closure.py` — RC10 closure reproduction (§3/§5/§6/§7).
- `../../afterglow_harness/_verify_rc11_closure.py` — RC11 closure reproduction (§4 same-run link + stale-dir).
- `../../afterglow_harness/adversarial_regression.py` — the RC11 regression (54/54; R5-1..R5-6 + RC11 minimal acceptance + P2-A/P2-B + retained attacks).
- `../../afterglow_harness/recompute_from_ledger.py` — independent, CONTRACT-DRIVEN re-derivation from raw ledger.
- `../../afterglow_harness/qualify_phase_a.py` — the single Phase-A PASS entry point (consumes the run manifest).

---

## Status snapshot

```text
RC7  = FAILED QUALIFICATION / RETAINED FOR AUDIT
RC8  = FAILED QUALIFICATION / RETAINED FOR AUDIT
RC9  = NOT CLOSED (FAILED QUALIFICATION) / RETAINED FOR AUDIT / AUTHORITATIVE_FOR_SCIENTIFIC_EXECUTION = NO
RC10 = NOT CLOSED (知微 RC10 review: 4 P1) / RETAINED FOR AUDIT / AUTHORITATIVE_FOR_SCIENTIFIC_EXECUTION = NO
RC11 = CLOSED  (PHASE_A_QUALIFICATION = PASS via qualify_phase_a.py; clean-snapshot;
                4 P1 + P2-A + P2-B all closed; 知微 closure review on 5e17fe8)
```

RC7, RC8, RC9, RC10 are retained as the evidence that the adversarial machinery actually caught
real errors (each round's findings were confirmed by Coder's own reproduction before repair).
RC11 is the CURRENT CLOSED CANDIDATE; 知微 confirmed closure of all 4 P1 + 2 P2 on commit
`5e17fe8` (P2-A verified across 84 member×arm error cases). RC9/RC10 remain
`AUTHORITATIVE_FOR_SCIENTIFIC_EXECUTION = NO`.

> 注：RC11 的资格范围仍限于 reference harness 的逻辑层（HARNESS_VALIDATION）；
> OS 级隔离、真实模型、科学候选仍按既有交付报告声明的后续范围，未在本轮开启。
