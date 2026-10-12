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
| 30 | 2026-10-10 | **知微** | `知微_RC11_P2A闭合复核_5e17fe8.md` | **eighth review / closure (written report)**: P2-A CLOSED (84/84 full-chain identity error cases across 4 member × 3 arm + 12 helper S_restored-missing cases); clean entry PASS; adversarial 54/54; P2-B call + wording CLOSED |

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

### RC11 — 睫独立核验 OBS 裁决（凌翼 2026-10-12，REVIEWED_HEAD `68bc80f`）

```text
OBS-1 = CONFIRMED  (detached 组件名单错位; RC11 冻结字节不动; 附外部勘误)
OBS-2 = CONFIRMED  (detached_match 子串匹配; 批准 RC12 定向加固)
OBS-3 = CLOSED     (INDEX.md = 10621 B / CR=0 / LF=121)
OBS-4 = CURRENTLY NOT REPRODUCED  (仓库 About 已不再显示旧 RC7)
RC11_PHASE_A = CLOSED / HISTORICAL
RC11_FROZEN_BYTES = DO NOT MODIFY
```

- OBS-1 勘误：`../RC11_DETACHED_RECORD_ERRATUM_OBS1_20261012.md`（外部记录，不动冻结字节）。
- OBS-2 加固：`../RC12_README.md` + `afterglow_harness/qualification_binding_rc12.py`（RC12 候选）。
- 睫原始签署原件：`睫_独立核验签署_20261012.md`（REQ-1，已收）。
- **RC 编号勘误（衔环发现 → 凌翼处置 B）**：`../RC11_MANIFEST_RC_NUMBER_ERRATUM_20261012.md`
  （头 RC11 / 底 RC9 / changelog 缺 RC10·RC11；**不动冻结字节**；依据
  `RC11_MANIFEST_头尾RC编号核对_20261012.md`）。

---

## Q3 — OS-level isolation (下一层；NOT frozen)

凌翼裁定：`Q3_DIRECTION = APPROVED`，`Q3_DESIGN_FREEZE = NOT AUTHORIZED`。
RC11 Phase A 保持冻结，**未动一字节**。Q3 为独立 lineage。

按顺序阅读：

| # | 文件 | 内容 |
|---|---|---|
| Q3-1 | `给凌翼睫知微_Q3_OS隔离层设计提案_Coder_20261010.md` | 设计提案：三向 witness、三态 access、真实 vs 沙箱 |
| Q3-2 | `给凌翼知微睫钳星_Q3契约修订_V1硬化PoC_Coder_20261011.md` | 契约修订 Q3-A..E + V1 硬化 PoC |
| Q3-3 | `给凌翼知微睫钳星_Q3_V2硬化_20261011.md` | V2：HMAC 封条认证 witness；chmod 负对照 |
| Q3-4 | `给凌翼知微睫钳星_Q3_V3跨进程实证_Coder_20261011.md` | V3：跨账户 worker 被拒 + observer 可读（同类对象） |
| Q3-5 | `给凌翼知微睫钳星_Q3安全处理_F2F3F4_端到端链_20261011.md` | 安全（凭据轮换+历史清除）+ Q3-F2/F3/F4 + 端到端链 |
| Q3-6 | `给凌翼知微睫钳星_Q3句柄审计_clear_端到端_20261011.md` | BD-62 句柄继承审计 + clear-side + 链整合 |
| Q3-7 | `给凌翼知微_Q3_BD65_BD66_F2F3F4门禁_20261011.md` | BD-65/BD-66 封堵 + F2/F3/F4 纳入唯一门禁 |
| Q3-8 | `给凌翼知微_Q3_四缺口修复_P1时序_P1生命周期_P1probe_P2_20261011.md` | P1-1 时序 / P1-2 生命周期 / P1-3 probe 身份 / P2 布尔 |
| Q3-9 | `给凌翼知微_Q3_probe权限锁补强_旧入口NameError修复_20261011.md` | probe 有效权限锁 + 旧入口 NameError |
| Q3-10 | `给凌翼睫_Q3_十步执行令进展_第1-6步完成_20261011.md` | 凌翼 10 步执行令 第 1–6 步 |
| Q3-11 | `给凌翼睫知微_Q3_第二轮四项P1复现与修复_20261011.md` | 凌翼二轮源码复查 4 项 P1 复现与修复（Profile B 证据链 / 矩阵 / FULL_VALID / DACL+provenance） |
| Q3-12 | `Q3_INDEPENDENT_REVIEW_RECORD_荣弦_20261011.md` | **独立窗口复核记录**（荣弦，独立主机，Python `D:\Python`）：8 组件全 PASS + FULL_VALID PASS |
| Q3-13 | `给凌翼睫知微_Q3_知微P1FULL_VALID消费门禁复现修复_20261012.md` | 知微 P1：FULL_VALID 消费门禁严格化（schema/布尔/profile/run-id）+ DACL 权限前提诊断 |
| Q3-14 | `给凌翼睫知微_Q3RC11_对睫独立核验的回应_20261012.md` | 对睫独立核验签署（RC11 字节+执行）的回应 + 4 条 OBS 处置 |
| Q3-15 | `睫_独立核验签署_20261012.md` | **睫独立核验签署原件**（RC11 字节+执行；OBS-1～4；自我更正 BD-67） |
| Q3-16 | `荣弦复跑原始记录_1db6286_20261012.txt` | **荣弦复跑原始记录**（`1db6286`；有密码 FAIL→改路径 PASS→无密码 NOT_EVALUATED） |
| Q3-17 | `知微_Windows实机复跑_20261012.md` + `给Coder_知微_Q3实机复跑与权限差异澄清_20261012.md` | **知微实机复跑原件**（`1db6286`；DACL 权限前提澄清 + FULL_VALID 消费 P1） |

**Q3 评审请求（凌翼 2026-10-12，REVIEWED_HEAD `68bc80f` 所需原始材料）**：

| 槽位 | 内容 | 状态 |
|---|---|---|
| REQ-1 | **睫 2026-10-12 独立核验签署完整原文**（含 OBS-1～4 风险评级、RC11 字节核验命令与执行结果） | ✅ **RECEIVED**（`睫_独立核验签署_20261012.md`，原件落位） |
| REQ-2 | **最新固定 commit 的独立 Windows 复跑原始日志**（`q3_qualify` 输出、run-id、FULL_VALID 产物、Profile B 六字段、真实 FAIL/SKIP） | ✅ **RECEIVED**（多轮）— `5fda429`：管理员 `REQ2_当前提交复跑_船长管理员_5fda429_20261012.md`（PASS，run_id `f1e7d604…`）+ 知微 `知微_REQ2当前提交复跑_5fda429_20261012.md`（NOT_EVALUATED）。**`6afe56a`（v5）**：船长 `evidence/REQ2_captain_admin_6afe56a_20261012/`（**PASS**，run_id `7fb2b985…`）+ 知微 `evidence/REQ2_zhiwei_6afe56a_20261012/`（**NOT_EVALUATED**；`independent_role_hashes` 十角色 **10/10 匹配**，digest `10c4548e…`）。两轮均**未改源码字节**（仅 `AFTERGLOW_PUBLIC_PYTHON`）。 |

> REQ-1 / REQ-2 均已满足（含 v5 `6afe56a` 独立复跑）。
> 复跑无需改源码：设 `AFTERGLOW_PUBLIC_PYTHON=<本机公共解释器>` 即可。两种权限上下文（管理员 PASS / 未提升 NOT_EVALUATED）**分别如实记录，互不替代**。

**RC12（OBS-2 定向加固候选）**：见 `../RC12_README.md` 与
`afterglow_harness/qualification_binding_rc12.py`（`strict_detached_match`，selftest 8/8）。
**RC11 冻结字节不动**（OBS-1 勘误见 `../RC11_DETACHED_RECORD_ERRATUM_OBS1_20261012.md`）。

Q3 代码（`afterglow_harness/`）：`win32_isolation.py`、`win32_worker_process.py`、
`q3_handle_audit.py`、`q3_reset_chain.py`、`q3_contract.py`、`q3_access_matrix.py`、
`q3_dacl.py`、`q3_qualify.py`、`q3_adversarial.py`、`q3_provenance.py`（均自测 PASS，未接入 frozen Phase A）。

Q3 状态：

```text
Q3 = IN PROGRESS  (PoC continuation AUTHORIZED; design freeze NOT AUTHORIZED)
  q3_access_matrix      14/14 PASS
  q3_dacl               14/14 PASS
  q3_adversarial        50/50 PASS   (含知微 P1 FULL_VALID 消费门禁负向回归)
  q3_provenance         10/10 PASS
  win32_isolation       21/21 PASS   (未提升令牌主机 -> DACL 项 NOT_APPLICABLE)
  win32_worker_process   4/4  PASS
  q3_handle_audit        5/5  PASS
  q3_reset_chain        85/85 PASS
  q3_qualify --selftest 17/17 PASS   (FULL_VALID 消费门禁: schema/布尔/profile/run-id)
  FULL_VALID_SUCCESS_PATH = PASS (profile=API_NO_INHERIT_PROFILE v=1.0; run_id 绑定)
  Q3_QUALIFICATION = PASS (exit 0)
  HANDLE-ISOLATION PROFILES: A RUNTIME_HANDLE_AUDIT / B API_NO_INHERIT (ACTIVE=B)
  INDEPENDENT WINDOWS RUN = PERFORMED (荣弦 1db6286; 知微 1db6286)
  LATEST-COMMIT EXACT REPLAY (5fda429) = RECEIVED
    管理员(船长)  Q3_QUALIFICATION = PASS         (run_id f1e7d604…)
    未提升(知微)  Q3_QUALIFICATION = NOT_EVALUATED (仅旧 DACL 恢复权限前提 N/A)
  V5 EXACT REPLAY (6afe56a) = RECEIVED
    管理员(船长)  Q3_QUALIFICATION = PASS         (run_id 7fb2b985…; reset_chain 113/113)
    未提升(知微)  Q3_QUALIFICATION = NOT_EVALUATED (十角色 10/10 + digest 10c4548e… MATCH)
  NATIVE EVIDENCE BUNDLE = ARCHIVED (evidence/ ; 见 evidence/INDEX.md)
```

> 安全：worker 凭据**不得入库**（运行时 env 注入 `AFTERGLOW_WORKER_PASSWORD`）。
> 曾误将口令写入代码/报告——已轮换并经 `filter-repo` 清除历史（详见 Q3-5）。

---

## Q3 DESIGN FREEZE — REGISTERED（2026-10-12）

凌翼 `Q3_DESIGN_FREEZE = AUTHORIZED`（REVIEWED_HEAD `8d09e62`）。

- **登记**: `../frozen/Q3_DESIGN_FREEZE_REGISTRATION_20261012.md`
- **冻结引用（detached，不可随意移动）**: `../frozen/Q3_FROZEN_REFERENCE_2c92074.txt`
- **机器可读角色表**: `../frozen/Q3_FROZEN_ROLES_2c92074.json`
- **验证器**: `../../afterglow_harness/verify_q3_freeze.py`（`Q3_FROZEN_IDENTITY = OK`）
- **FROZEN_CODE_COMMIT** = `2c92074a9808b1c9acd5ad5a36cba7a34e472892`；**10 角色**；**DIGEST** = `450349115b71bc9013c7a79f91d9bdf5f1728f2cbae65b025eb35a66af56da36`
- 自此刻起 **10 个 Q3 冻结源码不得修改**；`SCIENTIFIC_EXECUTION = MAY NOT START`。
