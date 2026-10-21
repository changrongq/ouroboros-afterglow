# AFTERGLOW NARROW GUARANTEE CLAIM TRANSITION v0.2

**性质**：**合同变更提案（修订版）**。**不是已批准的合同变更。**
**上一版被审**：`76ac77d0938bf6f9aa3b36a7df2cd5b20bc643f7`（v0.1）
**三方意见**：睫 `CONDITIONAL`（BF-1/2/3）｜钳星「我这条线无叫停项」｜知微 `NOT_ACCEPTED_AS_WRITTEN`（P1-1/2/3/4）

```text
NEW_DOCUMENT               = AUTHORIZED
CODE_CHANGE                = NOT AUTHORIZED
FROZEN_CONTRACT_CHANGE     = NOT AUTHORIZED
NEW_LINEAGE_IMPLEMENTATION = NOT AUTHORIZED
SCIENTIFIC_EXECUTION       = MAY NOT START
PERSISTENT_WORKER_CLEAN_BLOCK = ACTIVE
G2_END_TO_END              = NOT ESTABLISHED
RE-3                       = NOT ESTABLISHED（不因本提案关闭）
DESIGN_ACCEPTANCE          = CONDITIONAL（不因本提案改变）
```

---

# 0 · 我先列自己在这一版要改正的错误

| # | 来源 | 我的错 | 严重性 |
|---|---|---|---|
| **E-1** | 知微 P1-2 | 断言"V1 恒 UNRESOLVED ⇒ 字段 6 必然不可达" | **推导错误**，已在 §4 更正 |
| **E-2** | 知微 P1-2 | 称字段 1–5 都"不依赖运行后枚举" | **事实错误**：字段 5 依赖枚举 |
| **E-3** | 知微 P1-3 | `t_obs` 写"尚未被授予执行许可"，暗示进程未执行 | **语义错误**：`--holding` 进程已在运行 |
| **E-4** | 知微文字项 | 称 `_target_identities` 在 `q3_handle_audit.py` | **符号归属错误**：在 V2 |
| **E-5** | 知微文字项 | 写"V1 恒 UNRESOLVED" | **过度概括**：V1 优先 FOUND_TARGET |
| **E-6** | 睫 BF-1 | 把六字段读成六条来路 | **未核独立性** |
| **E-7** | 睫 BF-3 | AC-2 未区分"仪器灵敏度"与"隔离证据" | **角色未写死** |

**下面逐条改正，不辩解。**

---

# 1 · 命题：二选一（知微 P1-3 要求）

知微：

> **二选一，在新文本中写清。**
> · 保留"创建未继承"：登记创建事件到观察事件之间的执行控制、可信主体及句柄变动约束…
> · 仅主张"指定观察时的有限集合缺席"：同步修改名称和用途，不从该状态倒推历史上从未继承。

## 1.1 我的选择

```text
CLAIM_FORM = B（仅主张指定观察时的有限集合缺席）
CLAIM_NAME = REGISTERED_FORBIDDEN_HANDLE_ABSENCE_AT_OBSERVATION
```

**为什么选 B**：

- 选 A（创建未继承）需要证明 `t_create → t_obs` 之间句柄未变，而 `--holding` 进程**已在执行**（知微 P1-3 已核实：`q3_business_worker_entry.py` L61-66 写 READY、轮询 mailbox）
- **我没有设计出**该区间的执行控制机制
- 选 B **不需要**那个区间证明——它只主张一个时刻的状态

**名称已改**：从 `NONINHERITANCE` 改为 `ABSENCE_AT_OBSERVATION`，因为新命题**不主张历史上的继承事实**。

**禁止词仍遵守**：`CLEAN` / `FULL_ISOLATION` / `END_TO_END_VALID` 未作 claim 名。

## 1.2 新命题的精确定义

```text
REGISTERED_FORBIDDEN_HANDLE_ABSENCE_AT_OBSERVATION

主体   ：worker W，由 CreateProcessWithLogonW 创建，以 afterglow_worker 运行
对象   ：受保护对象 P，由稳定 OS 身份（卷序列号 + 文件 ID）界定
集合 ℱ ：控制器在创建 W 之前已登记（见 §5.1）的句柄值集合
时刻   ：t_obs = CreateProcessWithLogonW 返回后的单次观测时刻
断言   ：在 t_obs 的成功查询中，ℱ 中任一值均未出现在 W 的句柄表中
```

**本命题不断言**：

- ❌ 这些句柄从未被继承
- ❌ worker 在 `t_obs` 之后不持有 P 的访问
- ❌ worker 的句柄集合为空

## 1.3 ℱ 的"可继承"限定已删除（睫 NB-2）

v0.1 的 ℱ 定义含"处于可继承状态"——睫指出：

> 而 `CreateProcessWithLogonW` 没有 `bInheritHandles` 参数，**不传递任何句柄**——无论那个句柄可继承与否。
> ⇒ 于是"可继承"这个限定，在该路径下不改变任何结论。

**v0.2 删除该限定**，ℱ 只登记**句柄值 + 对象身份 + 登记时刻**，不登记继承位（继承位在 B 形式下与结论无关）。

---

# 2 · 证据依赖图（知微 P1-2 要求重画）

## 2.1 我 v0.1 的错误（E-1）

我写：

> 而审计依赖 `audit_process_handles_for_target`（V1）——V1 在持久业务 worker 上恒 `UNRESOLVED`。因此字段 6 不可达。

**知微指出这推导不成立。我核了源码，他是对的：**

```python
# q3_reset_chain.py L970
worker_known_forbidden = (hstat == "HANDLE_AUDIT_FOUND_TARGET")   # ← 只判 FOUND_TARGET
```

**`UNRESOLVED` 会让此布尔为 `False`**，而字段 6 要求 `worker_known_forbidden_present is False` → **字段 6 可以通过**。

再加上 L949-958 的 **Profile B 豁免**：

```python
else:
    # Profile B: runtime audit is NOT the proof; it stays UNRESOLVED and is
    # recorded as-is.
    out.handle_audit_ok = True
    if hstat == "HANDLE_AUDIT_UNRESOLVED":
        out.reason = ... "PROFILE_B: runtime_handle_audit=UNRESOLVED (recorded, not CLEAN)"
    elif hstat in (None, "HANDLE_AUDIT_ERROR"):
        out.handle_audit_ok = False
```

**Profile B 只在 `None`/`ERROR` 时拒绝，`UNRESOLVED` 被接受并记录。**

## 2.2 重画的依赖图

| 层 | 文件 / 行 | 生产者 → 消费者 | 拒绝条件 | 可支持命题 |
|---|---|---|---|---|
| **L1 旧控制实验** | `win32_worker_process.py` L267-269 `leak_positive_control` | 正控制（`CreateProcessW` + inherit=TRUE）检出泄漏 ∧ 负控制（`CreateProcessWithLogonW`）未检出 → `leak_ok` | 无法 spawn ⇒ `NOT_APPLICABLE` | **仅**仪器灵敏度 |
| **L2 旧 Profile B** | `q3_reset_chain.py` L970/974-980 → `build_profile_b_proof` | `hstat==FOUND_TARGET` → 字段 6 输入；`leak_ok` → 字段 5 输入 | 字段全 True 才 `profile_b_ok` | **Profile B 自身的窄资格** |
| **L2b Profile B 运行时豁免** | `q3_reset_chain.py` L949-958 | `PROFILE_REQUIRES_CLEAN[Profile B] == False` ⇒ `UNRESOLVED` 被接受 | `None` / `ERROR` ⇒ 拒绝 | **不把 UNRESOLVED 当 CLEAN** |
| **L3 业务适配器** | `q3_reset_adapter.py` L129-141 `WorkerAccessWitness.proven` | `handle_audit_status == HANDLE_AUDIT_CLEAN` | **非 CLEAN 一律 False** | 业务持久 worker 的**原 CLEAN 主张** |
| **L4 新窄合同** | 本提案 | 靶向值缺席（若实现） | 见 §5 | **本提案主张的全新命题** |

## 2.3 由此得出的三条结论（v0.1 的断言撤销）

**结论 1 · 旧 Profile B 与业务适配器不是同一道门。**
L2 接受 `UNRESOLVED`；L3 要求 `CLEAN`。**"V1 恒 UNRESOLVED"只击穿 L3，不击穿 L2。**

**结论 2 · "只替换第六字段"不足以描述所需变更。**
L4 的判据与 L2/L3 都不同（见 §5），不是换个字段值的事。

**结论 3 · 旧字段单独为 True 也不能作为新 claim 的独立证据。**
（知微原话，照录）

## 2.4 字段 1–5 的分类更正（E-2）

v0.1 称"字段 1–5 都不依赖运行后枚举"。**错误**：

| 字段 | 是否依赖运行后枚举 |
|---|---|
| 1 `registered_creation_api_ok` | 否（读 attestation） |
| 2 `startupinfo_checked` | 否（读 STARTUPINFO facts） |
| 3 `inheritable_channels_checked` | 否（同上） |
| 4 `forbidden_handle_noninheritance_proven` | 否（**但见 §3：它是字段 1 的推论**） |
| **5 `leak_positive_control_detected`** | **是**——`leak_control_ok` 由正负两轮**调用审计器**得出 |

---

# 3 · 睫 BF-1：六字段 ≠ 六条来路

睫：

> 一旦字段 1 为真，字段 4 的两个条件在语义上必然为真。
> ⇒ 一条观测（API 名），被说了两遍——第二遍说的是第一遍的推论。
> ⇒ **独立性不由【字段数】决定，由来路决定。**

**我核实了字段 4 的构成**：

```python
"forbidden_handle_noninheritance_proven": bool(
    startupinfo_facts.get("api_has_no_inherit_param") is True
    and startupinfo_facts.get("fresh_logon_session") is True)
```

**这两个属性是 `CreateProcessWithLogonW` 的定义，不是观测。** 睫成立。

## 3.1 更正后的来路表

| 来路 | 覆盖字段 | 性质 |
|---|---|---|
| **A · API 名观测** | 1，且 4 为其推论 | 身份证据 |
| **B · STARTUPINFO 检查** | 2 | 身份证据 |
| **C · 无继承句柄列表** | 3 | 身份证据 |
| **D · 正负对照实验** | 5 | **仪器灵敏度**（非隔离证据） |
| **E · 运行期句柄观测** | 6 | 隔离观测 |

```text
六字段 = 五条来路 = 四条身份证据 + 一条仪器灵敏度 + 一条运行期观测
```

**"非继承"在本 claim 下的唯一支撑是 A（读到一个 API 名），而它的内容在 §1.3 之后已与结论无关。**

**这正是我选择 B 形式的另一个理由**：A 形式的"创建未继承"在 `CreateProcessWithLogonW` 之下，**等价于"该 API 不传递句柄"**——**一个 API 签名事实，不是一次隔离观测**。

---

# 4 · 睫 BF-2：真实持久 worker 上的隔离观测 = 零

睫：

> 字段 6 不可达 · 字段 5 取自 throwaway · 1/2/3/4 是身份证据非隔离证据

**但知微 P1-2 已证明字段 6 在 Profile B 下可达。**

## 4.1 两方就此的分歧，我如实并列

| 观点 | 依据 |
|---|---|
| **睫**：字段 6 在**持久业务 worker**（L3，要求 CLEAN）上不可达 | `q3_reset_adapter.py` L140 `!= HANDLE_AUDIT_CLEAN` |
| **知微**：字段 6 在 **Profile B**（L2，接受 UNRESOLVED）下可达 | `q3_reset_chain.py` L970 只判 FOUND_TARGET；L949-958 豁免 |

**两者不矛盾——他们说的是两个不同的层。**

**但我必须诚实说**：**本 claim 要作用于真实持久业务 worker，而该路径当前走的是 L3（要求 CLEAN）。**

⇒ 在 L3 下，`UNRESOLVED` 恒 False ⇒ **字段 6 确实不可达**（睫对）。
⇒ 在 L2 下可达（知微对）。
⇒ **本 claim 若要在持久 worker 上成立，需要一条不经过 L3 的新路径**，而那条路径**尚未设计**。

```text
PERSISTENT_WORKER_FIELD6_REACHABILITY = NOT ESTABLISHED（依赖未设计的新路径）
```

---

# 5 · 观测设计（知微 P1-4 要求）

## 5.1 ℱ 的创建前登记

```text
登记时机：CreateProcessWithLogonW 调用之前
登记内容：每个句柄的 (值, 对象 OS 身份, 属性)
绑定    ：(登记时刻, 该次创建的唯一标识)
防失配  ：登记与创建之间若句柄表发生变化 ⇒ 整次观测 INVALID
空集合  ：须单独标记 EMPTY_F_SOURCE，且空集合不能充当检出能力的正对照
```

**`EMPTY_F_SOURCE` 是知微明确要求的**：集合为空时不能算"证明能力"。

## 5.2 查询方法与其表示范围（知微点名的坑）

知微：

> V1 `_iter_handles` 使用 classic 表结构，PID 和句柄值字段均为 `c_ushort`…
> 若直接复用而不限制范围或验证表示能力，**字段宽度造成的漏选本身就可能被误写成"目标值不存在"**。

**这是源码可见的表示范围问题。** v0.2 必须处理：

| 问题 | 处理 |
|---|---|
| `UniqueProcessId` 为 `c_ushort` | 目标 PID 若 > 65535 ⇒ **观测 INVALID**（不得判缺席） |
| `HandleValue` 为 `c_ushort` | ℱ 中若有值 > 65535 ⇒ **观测 INVALID** |
| 枚举返回 `SIZE_MISMATCH` | 重试；仍失败 ⇒ **查询失败**（非缺席） |

**四态区分（知微要求）**：

```text
QUERY_FAILED        — 查询本身失败（权限/枚举/解码）
ABSENCE_CONFIRMED   — 有效查询中确认 ℱ 中所有值均未出现
VALUE_HIT           — 值命中（候选，**不等于**身份确认命中）
IDENTITY_CONFIRMED  — 命中且身份核验一致
```

**"值命中"不得被写成"检出受保护对象"或"证明真实继承"**（知微原话）。

## 5.3 稳定进程绑定

```text
禁止：只按裸 PID 查表
要求：绑定 (pid, create_time, image_path) 三元组（与 Option C 定义一一致）
失配 ⇒ 观测 INVALID
```

## 5.4 新审计器必须自带正负对照

知微：

> 新审计器的正负对照使用**同一新查询路径**…**旧 V1 控制成功不能自动给新仪器背书**。

**采纳。**

---

# 6 · 接受条件（重写）

## 6.1 AC 清单

```text
AC-1  创建 API == REGISTERED_CREATION_API
      且登记：登录 flags、创建 flags、STARTUPINFO/std-handle 设置、
              可执行文件与版本、实际进程身份与 token SID、OS/解释器环境
      （知微"创建 API 的前提需要进入新合同"）

AC-2  仪器灵敏度前提（**不是隔离证据**）：
      同一新查询路径的正负对照均成功
      ⇒ 正控制检出、负控制未检出
      ⇒ 否则 NOT_APPLICABLE（永不 PASS）

AC-3  ℱ 中每个值在有效查询中 ABSENCE_CONFIRMED
      ⇒ 仅此才满足负向条件

AC-4  身份与时间：对象身份由稳定 OS 身份界定；进程绑定为三元组；t_obs 与创建同一会话绑定

AC-5  失败收敛（**四原因分开，不得互相吸收**）：
      - 发现目标 / 值命中      ⇒ FOUND（不是缺席）
      - 测量无效（权限/枚举/解码/表示范围）⇒ INVALID
      - 未运行 / 环境不满足     ⇒ NOT_APPLICABLE
      - 已确认缺席              ⇒ ABSENCE_CONFIRMED
      **任一非 ABSENCE_CONFIRMED ⇒ 不输出保证通过**

AC-6  证据必须来自真实持久 worker，不得从 probe / throwaway 继承
```

## 6.2 AC-2 与 AC-5 的状态映射（知微要求，避免同一输入落入两个状态）

| 情形 | AC-2 | AC-5 | 整体 |
|---|---|---|---|
| 正控制成功 ∧ 负控制成功 | 满足 | — | 继续 AC-3 |
| 无法 spawn | **NOT_APPLICABLE** | — | **NOT_APPLICABLE**（非 INVALID） |
| 正控制未检出泄漏 | 不满足 | — | **INVALID**（仪器灵敏度不成立） |
| 查询权限失败 | — | INVALID | **INVALID** |
| ℱ 为空 | EMPTY_F_SOURCE | — | **NOT_APPLICABLE** |

**`NOT_APPLICABLE`（环境）与 `INVALID`（测量无效）不得混用**——这是知微点名的"同一个输入任意落入两个状态"。

## 6.3 "肯定缺席"的定义（知微 P1-1 要求）

```text
ABSENCE_CONFIRMED 成立，当且仅当：
  ① 查询成功（非 QUERY_FAILED）
  ② 查询范围覆盖 ℱ 全部值（非覆盖不足）
  ③ 进程身份三元组匹配（非失配）
  ④ ℱ 非空且已登记
  ⑤ 无任何值为 VALUE_HIT 或 IDENTITY_CONFIRMED
```

**`status != FOUND_TARGET` 不是合格判据**（知微原话）。

---

# 7 · 对照计划（知微要求：只写计划，不执行）

| # | 预期结果 | 触发条件 | 是否可作负向证据 |
|---|---|---|---|
| C-1 | `VALUE_HIT` | 值命中但身份未核 | **否** |
| C-2 | `IDENTITY_CONFIRMED` | 命中且身份一致 | **否**（这是"发现"） |
| C-3 | `ABSENCE_CONFIRMED` | 五条件全满足 | **是** |
| C-4 | `INVALID` — 权限失败 | 无凭据 / token 不足 | 否 |
| C-5 | `INVALID` — 枚举失败 | `SIZE_MISMATCH` 重试后仍失败 | 否 |
| C-6 | `INVALID` — 表示范围不支持 | PID 或句柄值 > 65535 | 否 |
| C-7 | `INVALID` — 身份失配 | 三元组不匹配 | 否 |
| C-8 | `NOT_APPLICABLE` — 未运行 | 无 worker | 否 |
| C-9 | `INVALID` — 登记至创建间 ℱ 变动 | 集合失配 | 否 |

**本轮不执行任何一项。**

---

# 8 · 科学影响分析（C1 / L1 待睫裁）

睫：

> 我没有读预注册里 C1 / L1 的混杂路径定义。那份文件 2458 行，我本轮没取。
> 而 209 句说：**给不出字节的，不进判定。**
> …请给我 C1 / L1 的混杂路径清单字节。

**这是 REQUIRED_EVIDENCE RE-C。我给出文件位置，但不代裁：**

```text
候选来源：prereg/ 目录下的 MVP 预注册文件
我的处理：不自行摘取（避免又一次"引用不在基线的内容"）
请睫取该文件 → 给出 C1/L1 混杂路径清单字节 → 由睫裁定
```

**在拿到该字节之前，C1 / L1 维持"需裁定"，不许被读成"能"。**

| Claim | 结论 |
|---|---|
| C1 | **需裁定**（待 RE-C） |
| C2 / C3 / L2 | **不能**（N-3/N-4/N-5/N-6 充分） |

---

# 9 · §3 七项的分类权（睫要求写死）

睫：

> **"本 claim 明示不覆盖" ≠ "非阻塞风险"**
> 一项不在本 claim 范围内 ⇒ 它与本 claim 无关
> 一项不在本 claim 范围内，但属于科学结论的混杂路径 ⇒ **它是缺口**

**v0.2 明确采纳，并加一列**：

| # | 不证明 | 与本 claim 的关系 | 与科学结论的关系 |
|---|---|---|---|
| N-1 | 运行中重新打开 | 范围外 | **缺口**（若 claim 依赖） |
| N-2 | `DuplicateHandle` | 范围外 | **缺口**（若依赖） |
| N-3 | 代理 / IPC | 范围外 | **缺口**（C2/C3 已判不能） |
| N-4 | 网络 | 范围外 | **缺口** |
| N-5 | 跨 episode 残留 | 范围外 | **缺口** |
| N-6 | Reset 后 CLEAN | 范围外 | **缺口** |
| N-7 | 端到端隔离 | 范围外 | **缺口** |

**七项全部为"缺口"，不是"已披露残余"。** 分类权在睫，我按她的判据列表。

---

# 10 · 删去"唯一真正的技术障碍"

知微：

> 建议删去"唯一真正的技术障碍"：本轮至少还需要明确事件语义、观测覆盖和实际依赖。
> 这些是**有限的设计问题**，不是判定项目做不成。

**采纳，删除该表述。** v0.1 那句话把多个问题压缩成一个，是过度概括。

---

# 11 · 文字校正（知微两项）

| 项 | v0.1 | v0.2 |
|---|---|---|
| 符号归属 | `_target_identities` 在 `q3_handle_audit.py` | **在 `q3_business_handle_audit_v2.py`（L491）**；V1 使用 `file_identity`（L132）/`handle_file_identity`（L161） |
| V1 返回值 | "恒 UNRESOLVED" | **"在已观察环境/版本/worker 类别下未取得 CLEAN"**；V1 L333-338 **优先返回 FOUND_TARGET** |

---

# 12 · 状态

```text
CLAIM_FORM                    = B（观察时点缺席）
CLAIM_NAME                    = REGISTERED_FORBIDDEN_HANDLE_ABSENCE_AT_OBSERVATION
PROPOSAL_IS_APPROVED          = NO

睫  BF-1 六字段≠六来路         = 已更正（§3）
睫  BF-2 隔离观测=零           = 分层澄清（§4），持久 worker 路径仍未建立
睫  BF-3 AC-2 角色             = 已写死（§6.1 AC-2 + §6.2）
知微 P1-1 肯定缺席判据         = 已定义（§6.3）
知微 P1-2 依赖图               = 已重画（§2.2），推导错误已撤销
知微 P1-3 命题二选一           = 已选 B（§1.1）
知微 P1-4 观测设计             = 已给（§5）

RE-A startupinfo_facts 生产点  = 见 §13（已补）
RE-B 靶向审计两前提            = 见 §13（已补来路）
RE-C C1/L1 混杂路径清单        = 待睫取字节

NEW_CODE / NEW_LINEAGE / FROZEN_CONTRACT_CHANGE = NOT AUTHORIZED
SCIENTIFIC_EXECUTION = MAY NOT START
```

---

# 13 · RE-A / RE-B 补充（本轮可给的字节）

## 13.1 RE-A · `startupinfo_facts` 的生产点

**位置**：`win32_worker_process.py`，`build_profile_b_proof` 的调用方传入。

**字段来源**：`startupinfo_facts` 的四个键（`cb_set` / `std_handles_null` / `reserved_zero` / `no_inheritable_handle_list` / `api_has_no_inherit_param` / `fresh_logon_session`）由创建路径的记录构造。

**我未取得其赋值点的完整字节**——`grep` 到 `startupinfo_facts=` 的传参，但**构造该 dict 的具体位置我需要下一轮确认**。

```text
RE-A_STATUS = PARTIAL（调用点已定位，构造点未确认）
```

## 13.2 RE-B · 靶向审计的两个前提

睫：

> 前提一 · 被继承的句柄，在子进程中【保持相同数值】——**这是官方保证还是观察所得？需要来路。**
> 前提二 · 同值 ⇒ 同对象

**知微给了前提一的官方出处**：

> Windows 文档说明**继承得到的句柄与父进程句柄具有相同值、权限并指向相同对象**。
> [Microsoft：Inheritance]

**我据此登记**：

```text
前提一（继承保值）  = TCB 假设，来路：Microsoft Learn "Inheritance"
                      状态：官方文档陈述，本项目未实测
前提二（同值 ⇒ 同对象） = **不成立为普遍命题**
                      知微：同一数字在另一进程中出现并不自动证明它就是那个对象
                      ⇒ 值命中只能作**否决**（fail-closed 方向安全）
                      ⇒ 不能作"已检出受保护对象"
```

**于是靶向审计的结论方向是不对称的**：

- 值命中 ⇒ 可疑 ⇒ **fail-closed**（安全方向）
- 值未命中 ⇒ 缺席（**依赖前提一在目标配置下成立**，而该项目未实测）

**这个不对称必须写进新合同**，不能只说"只比值不分类所以可用"。

---

# 14 · 结论

**v0.2 把命题从"创建未继承"改成"观察时点缺席"**，因为前者在 `CreateProcessWithLogonW` 下等价于 API 签名事实（§3.1），后者才是一个可以真正观测的断言。

**而我撤回了 v0.1 的一个核心推导**（字段 6 不可达），因为知微核出它在 Profile B 层不成立。

**新命题仍然不能在持久业务 worker 上成立**——因为那条路径走 L3（要求 CLEAN），而 L3 是另一道门。

**这三件事我没有解决，只标出**：RE-A 的构造点、前提一的实测、RE-C 的 C1/L1 字节。
