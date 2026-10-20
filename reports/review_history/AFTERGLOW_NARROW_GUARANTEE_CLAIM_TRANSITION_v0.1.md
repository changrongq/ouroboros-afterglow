# AFTERGLOW NARROW GUARANTEE CLAIM TRANSITION v0.1

**性质**：**合同变更提案**。**不是已批准的合同变更。**
**授权依据**：凌翼 `LINGYI — AFTERGLOW NEXT-STEP DIRECTION`（2026-10-21）
**基线提交**：`59cdaa59cef9cf9cd4b358ef10ee54a2af51217c`
**路由**：`NARROW_CLAIM_DESIGN_PATH = SELECTED`

```text
NEW_DOCUMENT                  = AUTHORIZED（本文件）
CODE_CHANGE                   = NOT AUTHORIZED
FROZEN_CONTRACT_CHANGE        = NOT AUTHORIZED
NEW_LINEAGE_IMPLEMENTATION    = NOT AUTHORIZED
SCIENTIFIC_EXECUTION          = MAY NOT START
PERSISTENT_WORKER_CLEAN_BLOCK = ACTIVE
G2_END_TO_END                 = NOT ESTABLISHED
RE-3_RESET_OBSERVER_IDENTITY  = NOT ESTABLISHED（不因本提案关闭）
DESIGN_ACCEPTANCE             = CONDITIONAL（不因本提案改变）
```

> 凌翼的最终原则，本文件通篇遵守：
> **更窄的可证明命题，可以成为新研究路线；不能被追认成旧命题已经通过。**

---

# 1 · 新 claim 的精确定义

## 1.1 候选名称

```text
REGISTERED_FORBIDDEN_HANDLE_NONINHERITANCE
```

**名称禁用词**（凌翼指定）：`CLEAN`、`FULL_ISOLATION`、`END_TO_END_VALID` —— **本文件全文未使用其作为 claim 名**。

## 1.2 六要素定义（凌翼要求逐项）

### ① 主体（Subject）

```text
被断言对象 = 一个业务 worker 进程 W
W 由控制器以 CreateProcessWithLogonW 创建
W 以 afterglow_worker 账户运行（新登录会话）
```

**不覆盖**：其他创建路径、其他账户、其他会话形态。

### ② 禁止句柄集合（Forbidden Handle Set）

```text
ℱ = { h | h 是控制器在创建 W 之前持有的、
          指向受保护对象 P 的、且在创建时刻处于"可继承"状态的有效句柄 }
```

**注意这个定义的三个限定**：

| 限定 | 含义 |
|---|---|
| "控制器在创建 W 之前持有的" | 只覆盖**继承**这一条路径，不覆盖 worker 自己后续打开 |
| "指向受保护对象 P 的" | 对象由**稳定 OS 身份**界定（卷序列号 + 文件 ID），不用路径 |
| "处于可继承状态" | 只对**可继承**句柄成立；不可继承句柄本就不会被继承 |

**`ℱ` 不是"worker 持有的全部句柄集合"。** 本 claim 不断言那个集合的任何性质。

### ③ 对象身份（Object Identity）

```text
P 的身份 = (VolumeSerialNumber, FileId)
由 GetFileInformationByHandle / GetFileInformationByHandleEx 读取
同 API 比对（不跨 API 混比）
```

**这与既有的 `q3_handle_audit._target_identities` 及 V2 的 `target_identity_reason` 语义一致。**

### ④ 创建 API（Creation API）

```text
REGISTERED_CREATION_API = "CreateProcessWithLogonW"
```

**证据依据（代码现行）**：

```python
# win32_worker_process.py L225
#: CreateProcessWithLogonW (and CreateProcess* with a NULL handle-inheritance
#: model) do NOT let the child inherit arbitrary controller handles: the API has
#: no bInheritHandles parameter and the child runs from a FRESH logon session.
REGISTERED_CREATION_API = "CreateProcessWithLogonW"
```

**本 claim 仅对这一个 API 成立。**

### ⑤ 观察时点（Observation Time Point）

```text
t_obs = 创建调用返回后、worker 尚未被授予任何执行许可之前的审计时刻
```

**这是一个时间点断言，不是一个区间断言。** 本 claim **不**覆盖 `t_obs` 之后。

### ⑥ 证据范围（Evidence Scope）

```text
范围 = 单次创建会话中的 ℱ 中每个句柄 h 在 t_obs 时刻不出现在 W 的句柄表中
不是 = W 的句柄表为空
不是 = W 永不获得 P 的访问
```

---

# 2 · 已有证据

凌翼要求：**不得跨对象或跨生命周期继承结论。**

## 2.1 来自冻结 Q3 Profile B 的证据

`q3_contract.PROFILE_B_PROOF_FIELDS` 六个字段（逐字照录）：

| # | 字段 | 代码语义（`build_profile_b_proof` 实际计算） |
|---|---|---|
| 1 | `registered_creation_api_ok` | 实际使用的 API == 注册值 |
| 2 | `startupinfo_checked` | STARTUPINFO 的 cb、标准句柄、保留字段被显式设置/检查 |
| 3 | `inheritable_channels_checked` | `startupinfo_facts["no_inheritable_handle_list"] is True` |
| 4 | `forbidden_handle_noninheritance_proven` | `api_has_no_inherit_param is True` **且** `fresh_logon_session is True` |
| 5 | `leak_positive_control_detected` | 故意泄漏控制被检测到 |
| 6 | `no_known_forbidden_handle_present` | 控制器**确实**打开过 forbidden，且 worker 中未发现 |

## 2.2 正负对照实验的实际内容（`leak_positive_control`）

**RUN-POSITIVE**（泄漏为真，**必须**被检出）：

```text
控制器以 INHERITABLE 打开 forbidden 并保持
spawn 子进程 WITH inheritance（CreateProcessW, bInheritHandles=TRUE）
子进程存活期间枚举其句柄表
EXPECTED: HANDLE_AUDIT_FOUND_TARGET
```

**RUN-NEGATIVE**（注册路径**不**泄漏）：

```text
控制器保持同一个 INHERITABLE 句柄打开
spawn 走 CreateProcessWithLogonW（无 handle list ⇒ 无继承）
审计子进程句柄表
EXPECTED: NOT FOUND_TARGET
```

**关键**：`ok = True` 仅当**正控制检出泄漏 且 负控制未检出**。环境不能 spawn 时返回 `(False, reason)` ⇒ **NOT_APPLICABLE，永不 PASS**。

**这正是本 claim 所依赖的证据形态**：一个**能失败**的对照实验，而不是"没看到泄漏"。

## 2.3 尚未在真实持久 worker 上建立的证据

| 项 | 状态 |
|---|---|
| Profile B 的正负对照是否在**真实持久业务 worker** 上跑过并记录 | **未建立** |
| `t_obs` 之后的任何时刻 | **未覆盖**（本 claim 不主张） |
| 持久 worker 上的 `no_known_forbidden_handle_present` | **依赖 V1 句柄审计**，而 V1 在持久 worker 上恒 `UNRESOLVED` ⇒ **该字段在持久 worker 上不可达** |

**第 3 行是致命的**：本 claim 的字段 6 需要一个**在持久 worker 上可判定的**审计，而现有 V1 做不到（见 §3）。

## 2.4 不得跨对象/跨生命周期继承的结论（凌翼要求）

```text
禁止的推广：
  ✗ 把 probe worker（短生命周期）的结论用于持久业务 worker
  ✗ 把一次创建的 ℱ 结论用于另一次创建
  ✗ 把 t_obs 时刻的结论用于 t_obs 之后
  ✗ 把 CreateProcessWithLogonW 的结论用于 CreateProcessAsUserW / CreateProcessW
```

---

# 3 · 明确不证明的内容（凌翼要求的七项）

| # | 不证明 | 说明 |
|---|---|---|
| **N-1** | 运行中重新打开句柄 | worker 在 `t_obs` 之后自行 `CreateFile(P)` —— 不在 ℱ 覆盖内 |
| **N-2** | `DuplicateHandle` | 复制路径不产生"继承"，本 claim 不涉及 |
| **N-3** | 代理 / IPC | worker 请求对端代读 —— 完全不在范围内 |
| **N-4** | 网络通路 | `NETWORK_PATH_CONTROL = NOT ESTABLISHED`（见 v6） |
| **N-5** | 跨 episode 残留 | 前一 episode 的信息影响后一 episode |
| **N-6** | Reset 后 CLEAN | `RE-3 = NOT ESTABLISHED`，本 claim 不涉 Reset |
| **N-7** | 端到端信息隔离 | `G2_END_TO_END = NOT ESTABLISHED` |

**这七项不是"已披露的残余风险"，是"本 claim 明示不覆盖"。** 分类权在睫。

---

# 4 · 旧合同依赖图

凌翼要求：**哪些要求 CLEAN、哪些可独立使用较窄证据、哪些因缺少原保证继续阻断。**

## 4.1 依赖 CLEAN 的（本 claim **不能**替代）

| 合同项 | 位置 | 为何必须 CLEAN |
|---|---|---|
| `audit_process_handles_for_target` 的 CLEAN 分支 | `q3_handle_audit.py` | 判据是"所有相关句柄均证非目标"，本 claim 不涉及 |
| V2 的 `V2_CLEAN` | `q3_business_handle_audit_v2.py` | 同上 |
| `PERSISTENT_WORKER_CLEAN_BLOCK` | 全局 | **本 claim 不解除** |
| `judge_reset` 的 `access_ok` | `win32_isolation.py` | 需独立观察者（`RE-3`） |

## 4.2 可独立使用较窄证据的

| 合同项 | 位置 | 为何可用更窄证据 |
|---|---|---|
| `PROFILE_B_PROOF_FIELDS` 第 1–5 项 | `q3_contract.py` | 都是"创建时刻的属性"，不依赖运行后枚举 |
| `REGISTERED_CREATION_API` 核对 | `win32_worker_process.py` | 只需读取实际 API 名 |
| Profile B 正负对照 | `leak_positive_control` | 是**可失败的实验**，不是枚举完备性 |

## 4.3 因缺少原保证而**继续阻断**

| 项 | 阻断理由 |
|---|---|
| `PROFILE_B_PROOF_FIELDS` 第 6 项（`no_known_forbidden_handle_present`） | 依赖 V1 审计；V1 在持久 worker 上恒 `UNRESOLVED` |
| 任何要求"worker 不持有 P 句柄"的断言 | 同上 |
| 任何要求"Reset 后仍被拒"的断言 | `RE-3` 未建立 |

## 4.4 一个必须点出的**冻结合同内部不一致**（不改，只报）

`q3_contract.py` L116 的注释写：

```python
# 4. the controller does NOT pass forbidden handles to the worker (bInheritHandles=FALSE)
"forbidden_handle_noninheritance_proven",
```

**但实际 API 是 `CreateProcessWithLogonW`，它没有 `bInheritHandles` 参数。**

`win32_worker_process.py` L258 的注释是正确的：

```python
# 4. non-inheritance: API has no bInheritHandles + fresh logon session
```

**这是冻结件内两处注释不一致。** 冻结不可改，**但新 claim 若沿用"`bInheritHandles=FALSE`"的表述，会继承这个错误**——所以我建议新合同文本以 `win32_worker_process.py` 的表述为准。

**这也是我自己在 v2 犯过的错**（把 `bInheritHandles=FALSE` 套到 `CreateProcessWithLogonW` 上），由凌翼 W-BD1 纠正。

---

# 5 · 科学影响分析

凌翼要求：**分别说明该有限保证能否支持 C1、C2、C3、L1、L2 的特定结论；不能以局部隔离证据代替科学因果归因。**

> **前置声明**：以下判断是**我的初步分析**，**证明语义的最终裁定权在睫**。我按"能/不能/需裁定"三档填写，不自裁"能"。

| Claim | 本有限保证能否支持 | 理由 |
|---|---|---|
| **C1**（已注册存储写入） | **需裁定** | C1 依赖"已注册存储"，本 claim 只保证**创建时刻**的继承隔离。若 C1 的混杂路径主要是继承，则可能够；若涉及运行后重新打开，则不够。**我不判，请睫裁。** |
| **C2**（ON/OFF 非存储对照） | **不能** | C2 需要控制"非存储对照"的信息通路，本 claim 明示不覆盖代理/IPC（N-3）。 |
| **C3**（内容条件差异） | **不能** | 同上，且需覆盖网络（N-4）与跨 episode（N-5）。 |
| **L1**（Basic） | **需裁定** | 取决于 L1 的 claim 是否只依赖创建时刻隔离。 |
| **L2**（post-reset） | **不能** | 本 claim 不涉 Reset（N-6），`RE-3` 未建立。 |

**关键约束（我照录凌翼原话）**：

> 不能以局部隔离证据代替科学因果归因。

**所以即使某一项"能"，也只说明该 claim 的**混杂路径之一**被阻断，**不说明科学结论成立**。**

---

# 6 · 变更方案（不执行）

凌翼要求：**指出需要新建或修订的具体合同及接受条件，提出独立 lineage、版本、哈希与失败收敛方式，但不执行变更。**

## 6.1 需要新建的

| 对象 | 内容 |
|---|---|
| **新合同文本** | `AFTERGLOW_NARROW_GUARANTEE_CONTRACT_v0.1.md`（定义 claim 六要素 + 接受条件） |
| **新 lineage** | 与冻结 Q3 **独立**，不得继承 Q3 的资格 PASS |
| **新验证器** | 针对本 claim 的独立验证入口（不复用 `verify_q3_freeze`） |

## 6.2 需要修订的

| 对象 | 修订点 | 风险 |
|---|---|---|
| `PROFILE_B_PROOF_FIELDS` 第 6 项 | 需替换为**在持久 worker 上可判定**的替代判据 | 该项依赖 V1，**目前无替代** |
| `q3_contract.py` L116 注释 | 与实现对齐（见 §4.4） | **冻结，需正式修订程序** |

## 6.3 接受条件（提案）

```text
AC-1  创建 API == REGISTERED_CREATION_API（读取实际值，非声明）
AC-2  正控制检出泄漏 ∧ 负控制未检出（两者缺一 ⇒ NOT_APPLICABLE，非 PASS）
AC-3  ℱ 中每个句柄 h 在 t_obs 的审计结果为 NOT FOUND
AC-4  对象身份由稳定 OS 身份界定，且同 API 比对
AC-5  任一条件不满足 ⇒ INVALID，永不回落到 PASS
AC-6  证据必须来自真实持久 worker，不得从 probe 继承
```

**AC-6 是当前最大的未满足项**——见 §2.3 第 3 行。

## 6.4 版本、哈希与失败收敛

```text
VERSIONING: 每次接受条件变更 ⇒ 新版本号 + 新哈希；
            不得就地修改已发布版本。
HASHING:    新 lineage 的固定清单与验证器各自有独立哈希；
            与 Q3 的 45034911… 无继承关系。
FAILURE:    任一 AC 不满足 ⇒ 输出 INVALID / NOT_APPLICABLE；
            绝不输出 PASS；与凌翼 B-4 一致。
```

## 6.5 本提案**不执行**的部分

- 不新建任何文件（除本提案）
- 不改冻结合同
- 不实现新 lineage
- 不改任何代码

---

# 7 · 我必须写清的一个诚实结论

**这个 claim 目前有一项接受条件（AC-6）在现有架构下无法满足。**

原因：AC-3 需要"`ℱ` 中每个句柄在 `t_obs` 的审计结果"，而审计依赖 `audit_process_handles_for_target`（V1）——**V1 在持久业务 worker 上恒 `UNRESOLVED`**（ConDrv / KsecDD / CNG）。

**因此**：

```text
若 AC-3 依赖 V1  ⇒ 本 claim 在持久 worker 上不可判
若 AC-3 换成"只审计 ℱ 中的特定句柄" ⇒ 需要新的靶向审计机制（未设计）
```

**这不是我在推诿，是这个 claim 目前唯一真正的技术障碍。**

**我建议的下一步（等授权）**：设计一个**靶向审计**——只检查"控制器在创建前持有且可继承的那些特定句柄值"是否出现在 worker 句柄表中，而**不是**枚举并分类 worker 的全部 File 句柄。

**这与 Option C 的区别**：Option C 要证明"所有句柄都不是目标"（需枚举完备性）；靶向审计只回答"这几个特定值是否出现"（**只需句柄值比对，不需身份分类**）。

**这是否可行，我没验证**——`_iter_handles` 返回句柄值，理论上可比对。**但我不声称它成立。**

---

# 8 · 状态

```text
NARROW_CLAIM_DESIGN_PATH      = SELECTED（凌翼）
NARROW_GUARANTEE_PROPOSAL     = DELIVERED（本文件）
PROPOSAL_IS_APPROVED          = NO（合同变更提案，非已批准变更）

RE-4                          = CLOSED
RE-3_RESET_OBSERVER_IDENTITY  = NOT ESTABLISHED（不因本提案关闭）
DESIGN_ACCEPTANCE             = CONDITIONAL（不因本提案改变）
G-1..G-9                      = OPEN

PERSISTENT_WORKER_CLEAN_BLOCK = ACTIVE
G2_END_TO_END                 = NOT ESTABLISHED
FROZEN_Q3 / RC11              = UNCHANGED
CODE_CHANGE                   = NOT AUTHORIZED
FROZEN_CONTRACT_CHANGE        = NOT AUTHORIZED
NEW_LINEAGE_IMPLEMENTATION    = NOT AUTHORIZED
SCIENTIFIC_EXECUTION          = MAY NOT START
```

---

# 9 · 我没有做的事

- **未**改任何代码
- **未**修改冻结合同
- **未**新建 lineage
- **未**声称本 claim 已成立
- **未**把 C1/C3/L1 判为"能"（交睫裁）
- **未**把 §7 的障碍说成"小问题"

---

# 10 · 提交三方独立审查

```text
REVIEWED_COMMIT = 以本文件所在提交的 git rev-parse HEAD 为准

PROPOSAL_ACCEPTANCE = （待睫 / 钳星 / 知微三方独立意见）
BLOCKING_FINDINGS   = （待三方）
OBJECTIONS          = （意见不一致时保留异议，不由 Coder 自行宣布 ACCEPT）

FROZEN_BOUNDARY = UNCHANGED
IMPLEMENTATION_AUTHORIZATION = NONE
SCIENTIFIC_EXECUTION = MAY NOT START
```

**审查分工（凌翼指定）**：
- **睫**：新旧 claim 是否存在语义偷换；局部证据能否支持对应科学结论
- **钳星**：worker 生命周期、跨 episode 旧能力复用、Reset 边界
- **知微**：创建 API、可复现正负对照、证据链、失败条件
