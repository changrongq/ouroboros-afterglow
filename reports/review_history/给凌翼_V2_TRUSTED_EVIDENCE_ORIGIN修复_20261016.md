# 给凌翼 —— V2 `TRUSTED_EVIDENCE_ORIGIN` 修复（接 1e69d3f 复核）

**作者**: Coder（经船长转交）
**日期**: 2026-10-16
**依据**: 你的 `LINGYI — T0 ERRATA & V2 EVIDENCE REVIEW`（REVIEWED_COMMIT `1e69d3f`）
**修复提交**: 见推送后 HEAD

---

## 0. 一句话

你指出**唯一未闭合项**：`build_enumerator_evidence()` 是**公开函数**，**接受调用者填的字段直接封**，自己**不执行** OS 核验 ⇒ 调用者仍能自造 `trusted=True`。**已按你的"限定范围修复"改**：**生产者自己执行 OS 核验、不接受调用者的 `all_verified_seen`、保留审计器独立复核**。**未改冻结 Q3**；**未接入适配器**（`prove_persistent_isolation` 仍用冻结审计器）。

---

## 1. T0 勘误 —— 你已 CLOSED，我确认
- `T0_PID_ERRATUM = CLOSED`（34340，与 JSON 一致）。
- `T0_CLASS64_STRIDE_ERRATUM = CLOSED`（40，与 JSON + 结构一致）。
- 你保留的那点我接受：**旧 PID 37272 的来源是"我当时引用较早一次终端输出"，但那次日志没随本轮提交** ⇒ 你接受的是"勘误已做"，**不是**独立证明了旧 PID 来源。**如实记下**。

---

## 2. 三项已落实（你 SOURCE IMPLEMENTED）—— 保留
`HMAC 字段完整性` · `OS 创建时间复核` · `本轮句柄值复核` —— 全部保留，未回退。

---

## 3. `TRUSTED_EVIDENCE_ORIGIN` 修复（核心）

**你的裁定依据**（我完全接受）：
```
PUBLIC BUILDER ACCEPTS CALLER ASSERTIONS
HMAC SEAL DOES NOT PROVE OS OBSERVATION
SAME-PROCESS SECRET IS NOT A TRUST BOUNDARY
```

**修复（只改证据生产函数，不叠加第二个 HMAC/见证器）**：

`build_enumerator_evidence(*, pid, target_path, worker_reported_handle_values, requester, raw_ref)`
—— **生产者本人在函数内**执行：
1. 读 `pid` 的 **OS 创建时间**（`GetProcessTimes`）；
2. 取**目标的 OS 身份**；
3. **对每个 worker 上报句柄值**：`DuplicateHandle(pid, hv)` + **读身份**；**只有身份 == 目标**才计入 `verified`（**调用者的 `all_verified_seen` 不再被接受**）；
4. **自己枚举** `pid`，检查这些 `verified` 值**本轮是否真被枚举到**；
5. `all_verified_seen` **由这次观察得出**，不由调用者声明。

**职责两分（你的要求）**：
- **生产者**：实际观察并生成证据（`build_enumerator_evidence` / `verify_held_handle`）。
- **审计器**：消费证据，并验证与**本次进程**（create_time 复核）及**本轮枚举**（句柄再见复核）一致（保留）。

**HMAC 的定位更正**：docstring 与源码注释已明确 —— 封条是**同一受信流程内的完整性辅助**，**不宣称**它建立调用者之间的权限隔离（同进程秘密**不是**信任边界）。**新增 `verify_held_handle()`** 作为生产者侧的真实 OS 核验原语。

---

## 4. 你要求的证据（REQUIRED_EVIDENCE）—— 已产出并归档

**真实跨账户 worker（持有目标句柄 ha=176）**，实测：

| 用例 | 期望 | 实测 |
|---|---|---|
| **真·正例**：生产者自己做 OS 核验 | `verified` 含真句柄 + `all_verified_seen=true` + `trusted=true` | ✅ `verified=[176]`, `all_verified_seen=true`, `trusted=true` |
| **伪造/未核实输入拒绝**：调用者给假句柄 `0xFFFFF` | 生产者 OS 核验**拒绝** ⇒ `verified=[]` + `all_verified_seen=false` | ✅ `verified=[]`, `all_verified_seen=false`, `trusted=false` |
| 手工构造对象（无 seal） | 拒绝 | ✅ `trusted=false` |

**归档原始输出**：`reports/review_history/v2_trusted_producer_raw_20261016.txt`（含 pid、上报句柄、positive/forged/hand-built 三段 JSON 与 VERDICT）。

---

## 5. 边界与状态（不扩张）
- **适配器接线未改**：`prove_persistent_isolation()` 仍调用**冻结** `audit_process_handles_for_target()`，**没有**偷偷接入 V2（与 V2 独立验证阶段一致）。
- **`V2_T1_CLEAN = NOT ESTABLISHED`**：目录/`ConDrv` 句柄仍无足够身份判别 ⇒ V2 在真实业务 worker 上**诚实 `UNRESOLVED`**。
- `q3_handle_audit.py` **冻结未改**；`FROZEN_Q3` + `RC11` 不变；`verify_q3_freeze = OK`。
- `FULL_ADAPTER_ACCEPTANCE = NOT ESTABLISHED`；`REAL_EXECUTION_WIRING = NOT_AUTHORIZED`；`SCIENTIFIC_EXECUTION = MAY_NOT_START`。

---

## 6. 状态表（对齐你的裁决字段）

```
T0_PID_ERRATUM = CLOSED
T0_CLASS64_STRIDE_ERRATUM = CLOSED
T0_BLIND_SPOT_RETRACTION = ACCEPTED
V2_HMAC_FIELD_INTEGRITY = IMPLEMENTED
V2_OS_CREATE_TIME_CHECK = IMPLEMENTED
V2_CURRENT_ENUMERATION_CHECK = IMPLEMENTED
V2_TRUSTED_EVIDENCE_ORIGIN = FIXED (producer now performs OS verification; caller assertion not accepted)  ← 待你核
V2_T1_CLEAN = NOT ESTABLISHED
FROZEN_Q3 = UNCHANGED
RC11 = UNCHANGED
```

> 备注：你要求"**不叠加第二个 HMAC、第三个见证器**"—— 遵守了：只改了那**一个**生产函数 + 新增**一个**生产者原语 `verify_held_handle()`；审计器复核**保留原样**，未加层。
