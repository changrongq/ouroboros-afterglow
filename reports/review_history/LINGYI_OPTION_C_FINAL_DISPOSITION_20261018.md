# OPTION C 正式归档 — 收口记录（2026-10-18）

**授权**：凌翼 `LINGYI — OPTION C FINAL DISPOSITION`（DATE = 2026-10-18）
**REVIEWED_IMPLEMENTATION**：`6511264`
**FOLLOWUP_INDEX**：`66a136a`
**本记录对应提交**：见文末

> 这是**收口裁决**，不是下一轮任务清单。本文件只记录归档事实与一处已补实的证据边界，**不启动任何新工作**。

---

## 0 · 收口结论（原样记录）

```text
OPTION_C_CURRENT_DESIGN        = CLOSED
C_FEASIBILITY                  = NOT ESTABLISHED
C_CURRENT_EXPLORATION          = STOPPED

NO FURTHER C WORK REQUIRED
NO NEW EXPERIMENT AUTHORIZED
NO GATE SELF-UNBLOCK

REOPEN ONLY UPON:
  NEW MATERIAL EVIDENCE
  OR SEPARATELY AUTHORIZED DESIGN
```

**凌翼的原话我记在这里，因为它定义了"收口"的含义**：

> 不是因为失败了，而是因为终于按照约定的方法，把一条不能成立的证明路线，清清楚楚地指出来了。

---

## 1 · 核验结论对照

| 上轮裁决事项 | 凌翼核验 | 我的记录 |
|---|---|---|
| `INCOMPARABLE` 退回诊断字段，保持四态合同 | 源码通过 | `V2_CONTRACT_STATUSES` 已存在并受断言保护 |
| 删除未经证明的 `CAUSE_IS_ONTOLOGICAL` 强结论 | 源码通过 | 已改为 `CAUSE_IS_IDENTITY_UNAVAILABLE`，三合取项保留 |
| 已知 protected 句柄身份不可读时拒绝 CLEAN | 受控负例报告通过，**证据范围有限** | 见第 2 节，局限已补实 |
| C 的三个定义与反例 | 草案合格，**不能支撑开闸** | 见第 3 节 |
| C 暂停、冻结 Q3、接线边界 | 本次提交未突破 | `FROZEN_Q3` / `RC11` / `V2_WIRING` 均未动 |

---

## 2 · 凌翼指出的证据局限，我已补实

### 他指出的问题（准确）

> 测试把所有相关句柄的身份读取都设为失败，并没有单独断言那枚已知目标句柄出现在审计记录中。因此，它支持整体 fail-closed 分支，却不能被描述成对目标句柄逐项审计轨迹的完整证明。

### 我核实的结果

**成立。** 我读了 `c_unreadable_target_control.py` 原版，它只断言了：

```python
(res.counts.get("non_target_proven") or 0) == 0
(res.counts.get("unresolved") or 0) > 0
```

**这两个都是聚合量，可以在"那枚句柄根本没被检查"的情况下依然成立。** 他的指摘准确。

### 已补的断言（`6511264` 之后）

新增四项，直接查 `res.records` 中的那一枚句柄：

```python
per_handle = [r for r in res.records if int(r.handle_value) == hv]
```

| 断言 | 结果 |
|---|---|
| known-target handle **APPEARS** in the per-handle records | PASS（`matches=1`, `handle=0x12c`） |
| that record is classified `unresolved`（not `non_target`） | PASS |
| that record did NOT become `non_target_proven` | PASS |
| that record carries an `unresolved_kind` | PASS（`no_identity`） |

### 重跑实测（保护句柄 300）

```text
per-handle record for the known target:
[{"handle_value": 300,
  "classification": "unresolved",
  "unresolved_kind": "no_identity",
  "name": "\\Device\\HarddiskVolume3\\...\\protected_01191676.bin"}]

PASS  known-target handle APPEARS in the per-handle records  [matches=1 handle=0x12c]
PASS  that record is classified unresolved (not non_target)
PASS  that record did NOT become proven non-target
PASS  that record carries an unresolved_kind  [no_identity]

DISTINCT_RESULTS: PASS
```

**意义**：那枚我们独立确认为目标的句柄，现在**在证据里有自己的一条记录**，而且是 `unresolved` + `no_identity`。凌翼写的"证据范围有限"从**文字描述**变成了**有数据支撑的边界**。

### 但这条限制**依然成立**，我明确保留

这项测试仍然**只是**：一个已知目标句柄在身份不可读时被拒于 CLEAN 之外。

它**仍然不是**：
- 句柄集合完整性的证明
- 关于枚举覆盖任意时刻的证明
- 重开 C 的理由

```text
UNREADABLE_TARGET_T1_CONTROL =
  SOURCE_REVIEWED
  REPORTED_TEST_PASS
  SCOPE_LIMITED
  NOT A COMPLETENESS PROOF
```

**我补实的是"轨迹可查"，不是"范围扩大"。** 两者的区别正是这份记录要守的线。

---

## 3 · 三份定义的最终判定（接受，不再推进）

| 定义 | 凌翼判定 | 我的草案主张 | 是否一致 |
|---|---|---|---|
| `OBSERVATION_BOUNDARY` | **PARTIAL** | 部分成立（反例 A：枚举非原子） | ✅ 一致 |
| `SNAPSHOT_COVERAGE_SEMANTICS` | **NOT ESTABLISHED** | 不能成立（反例 D/F） | ✅ 一致 |
| `TIME_SCOPE_OF_ASSURANCE` | **NOT ESTABLISHED** | 不能成立（反例 G/H） | ✅ 一致 |

### 凌翼替我的论证收紧的一处措辞，我接受

> A、D、G、H 是值得严肃对待的**未被排除的失败情景**，并非每一种都已通过实机实验复现。例如，在途 I/O 是否会以草案描述的具体顺序导致句柄产生，当前材料没有直接证明。

**这个纠正成立。** 我写的"反例"读起来像是已复现的观测，但实际是**逻辑上未排除的情形**——我并没有在实机上让在途 I/O 真的制造出一个句柄。

而且凌翼指出关闭 C **不需要**证明每种风险都实际发生：

> 只要方案要求的完整性保证无法建立，它就没有资格签出 CLEAN。这就够了。

**我接受这个更强的判据**，因为它不依赖任何一次实验的成败。

---

## 4 · 门禁常量：我一个未动

```text
C_OBSERVATION_BOUNDARY_DEFINED         = False
C_SNAPSHOT_COVERAGE_SEMANTICS_DEFINED  = False
C_TIME_SCOPE_OF_ASSURANCE_DEFINED      = False
```

凌翼明说"不必修改三个门禁常量"。**我也确实没改。**

理由不是怕麻烦：这三个常量是**闸的物理位置**。归档 C 是「这条路线不再推进」，不是「这条路线已经成立」。若把常量改成 `True`，闸就开了，而三份定义并没有一份能支撑它。

`C_CURRENT_ROUTE` 保持 `CLOSED_UNLESS_NEW_BOUNDARY_EVIDENCE`。

---

## 5 · 未来若要讨论窄保证

凌翼：

> 未来若要讨论较窄的"无 forbidden 句柄继承"保证，应当作为一个单独的合同问题提出，不能自动继承 CLEAN 的名称或效力。

**已记录。** 我**不会**主动启动，也不会把它说成 CLEAN 的弱化版。若将来提出，必须以**独立集成合同变更**的形式，重新走授权流程。

---

## 6 · 状态（收口后）

```text
OPTION_C_CURRENT_DESIGN        = CLOSED

PROBE_CLEAN_HISTORY            = VERIFIED   （frozen Q3 probe 路径）
PERSISTENT_BUSINESS_CLEAN      = NOT ESTABLISHED
CURRENT_BUSINESS_AUDIT         = UNRESOLVED
PERSISTENT_WORKER_CLEAN_BLOCK  = ACTIVE
PROBE_CLEAN_IS_NOT_BUSINESS_CLEAN = TRUE

OPTION_A                       = NOT AUTHORIZED
OPTION_B                       = ACTIVE
OPTION_C                       = CLOSED
C_FEASIBILITY                  = NOT ESTABLISHED
C_CURRENT_EXPLORATION          = STOPPED
C_CURRENT_ROUTE                = CLOSED_UNLESS_NEW_BOUNDARY_EVIDENCE

UNRESOLVED_OPERATIONAL / NO_IDENTITY / INCOMPARABLE = ACCEPTED
V2_FOUR_STATUS_CONTRACT        = RESTORED
ONTOLOGICAL_OVERCLAIM          = REMOVED

FROZEN_Q3                      = UNCHANGED   （digest 45034911…）
RC11                           = UNCHANGED   （78bdb90f…）
V2_WIRING                      = NOT AUTHORIZED
FULL_ADAPTER_ACCEPTANCE        = NOT ESTABLISHED
REAL_EXECUTION_WIRING          = NOT AUTHORIZED
SCIENTIFIC_EXECUTION           = MAY NOT START
```

---

## 7 · 归档清单

| 文件 | 角色 |
|---|---|
| `LINGYI_OPTION_C_FINAL_DISPOSITION_20261018`（本文件） | **收口裁决 + 归档记录** |
| `给凌翼_四项裁决落地_20261017.md` | 上轮裁决落地回报（`REVIEWED_IMPLEMENTATION`） |
| `给凌翼睫_C观测边界定义草案_20261017.md` | 三份定义草案与反例 |
| `20261017_OPTION_C_归档包_入口.md` | 单页导航 |
| `afterglow_harness/c_unreadable_target_control.py` | T1 负例驱动（含本次补实的逐句柄断言） |

**本记录之后，C 这条线不再产生新文件，除非出现 NEW MATERIAL EVIDENCE 或另行授权的设计。**
