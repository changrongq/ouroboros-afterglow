# AFTERGLOW NARROW GUARANTEE CLAIM TRANSITION v0.4

**性质**：**合同变更提案（第三次修订）**。**不是已批准的合同变更。**
**上一版被审**：`d210038ac801a7548fcbaba72db6242c6a19a717`（v0.3）
**授权**：凌翼 `V04_DOC_ONLY_REVISION = AUTHORIZED`

```text
CLAIM_NAME = REGISTERED_HANDLE_VALUE_ABSENCE_AT_OBSERVATION   （凌翼裁定三，已采用）
CLAIM_FORM = B / ACCEPTED AS CANDIDATE

STATIC_TRUE_FIELDS        = STATIC PREMISES / NOT OBSERVATIONS
CREATION_API_PROVENANCE   = DECLARED CODE PATH
PROOF_SOURCE_INDEPENDENCE = NOT ESTABLISHED

C1_L1_SUPPORTED_BY_NEW_B    = NO
C2_C3_L2_SUPPORTED_BY_NEW_B = NO

NEW_B_EVIDENCE              = NOT ESTABLISHED
RE-3_RESET_OBSERVER_IDENTITY = NOT ESTABLISHED
DESIGN_ACCEPTANCE           = CONDITIONAL

CODE_CHANGE / CONTRACT_CHANGE / NEW_LINEAGE_IMPLEMENTATION = NOT AUTHORIZED
SCIENTIFIC_EXECUTION        = MAY NOT START
FROZEN_Q3_RC11              = UNCHANGED
```

**本轮仅设计文本修订 + 只读证据核对。**

---

# 交付项 1 · 证据来路分类与依赖关系修正

## 1.1 凌翼新指出的问题：字段 1 也不是观测

凌翼：

> `WorkerAttestation.creation_api` 的值是构造对象时**直接填写的字符串**：
> `creation_api="CreateProcessWithLogonW"`
> 实际 `_spawn()` 代码的确调用了这个 API，因此这个标签**有可核对的代码路径依据**。
> 但**标签本身不是操作系统独立返回的 API 调用观测**。
> v0.3 §2.3 把它直接归入"真观测"，**分类过强**。

**我核了字节，成立**（`q3_reset_chain.py` L437 与 L1829，两处均为字面量字符串）。

```text
CREATION_API_PROVENANCE = DECLARED_CODE_PATH / REQUIRES_CALLSITE_BINDING
```

## 1.2 六字段的完整来路分类（凌翼要求的五类区分）

凌翼要求区分：**实际读取的结构字段 / 代码路径声明 / 静态前提 / 测试结果 / 运行期审计结果**。

| 字段 | 内容 | 来路类别 | 独立性 |
|---|---|---|---|
| **1** `registered_creation_api_ok` | `attestation.creation_api == REGISTERED_CREATION_API` | **代码路径声明** | **不是 OS 观测**；可核对但需 call-site 绑定 |
| **2** `startupinfo_checked` | `cb_set` ∧ `std_handles_null` ∧ `reserved_zero` | **实际读取的结构字段** | **真观测**（读 `si` 结构） |
| **3** `inheritable_channels_checked` | `no_inheritable_handle_list` | **静态前提** | **常量 True，零信息** |
| **4** `forbidden_handle_noninheritance_proven` | `api_has_no_inherit_param` ∧ `fresh_logon_session` | **静态前提** | **两个常量，零信息** |
| **5** `leak_positive_control_detected` | `leak_control_ok` | **测试结果**（取自 throwaway/probe 类对象） | 仪器灵敏度，非隔离证据 |
| **6** `no_known_forbidden_handle_present` | `controller_opened_forbidden=leak_ok` ∧ `worker_known_forbidden_present` | **测试结果 ∧ 运行期审计结果** | 见 §1.4 |

## 1.3 凌翼对三个常量键的裁定（方案 b + c 并采）

| 键 | 正确定位（凌翼原文） |
|---|---|
| `no_inheritable_handle_list` | **API 接口及当前创建调用配置的静态约束** |
| `api_has_no_inherit_param` | **API 签名事实** |
| `fresh_logon_session` | **对选定 API、登录参数及操作系统行为的前提声明** |

```text
允许：登记为受审查的实现前提
不允许：计数为三项独立观测
不允许：由它们证明新 B 的数值缺席
```

## 1.4 依赖关系（凌翼要求：`leak_ok` 不得重复计独立性）

```text
字段 6 = 字段 5 ∧ (hstat ≠ FOUND_TARGET)
         ↑ 同一变量 leak_ok，不得算作两条来路
```

## 1.5 修正后的独立性结论

```text
PROOF_SOURCE_INDEPENDENCE = NOT ESTABLISHED
```

**理由**：

| 来路 | 计数 |
|---|---|
| 结构化观测（字段 2） | 1 |
| 代码路径声明（字段 1） | 非观测 |
| 静态前提（字段 3、4） | 0（零信息） |
| 测试结果（字段 5，throwaway 上式） | 1，且与字段 6 共享 |
| 运行期审计（字段 6 的 `hstat`） | 1 |

⇒ **真正的独立观测仅 2 条**（字段 2 的结构读取、字段 6 的 `hstat`），**且都不指向"数值缺席"**。

## 1.6 冻结口径（凌翼裁定后果）

```text
旧 Q3 冻结字节继续保留
其身份校验为 OK ≠ 上述证据强度问题已消失
⇒ 在审查报告中登记其证明限制
⇒ 不修改历史冻结文本
⇒ 不把该缺陷悄悄修正成 PASS
```

---

# 交付项 2 · 新名称与查询样本边界

## 2.1 名称（凌翼裁定三，已采用）

```text
采用：REGISTERED_HANDLE_VALUE_ABSENCE_AT_OBSERVATION
不再推荐：REGISTERED_FORBIDDEN_HANDLE_ABSENCE_AT_OBSERVATION
```

**凌翼给的理由照录**：

> 我们真正观察的，是登记集合 ℱ 中的**句柄数值**。
> 我们并**没有证明**，在查询样本里，不存在其他句柄数值指向受保护对象 P。
> 用 `FORBIDDEN_HANDLE_ABSENCE` 容易让下一个读者误以为受保护对象的**访问能力已经消失**。

## 2.2 规范公式（凌翼给定，逐字照录）

$$\mathcal{F} \cap H_{\text{sample}}(W) = \varnothing$$

其中 $H_{\text{sample}}(W)$ **仅代表一次已验证有效、覆盖充分的查询返回样本中属于目标 worker 的句柄数值集合**。

**该公式不蕴含**：

$$\text{WorkerCannotAccess}(P)$$

**也不蕴含**：这些句柄历史上从未被继承。

## 2.3 `AT_OBSERVATION` 的解释上限

```text
AT_OBSERVATION = 一次查询样本
≠ 已证明整个系统在同一原子时刻具有一致的全局快照
```

```text
T_OBS_SEMANTICS        = SINGLE_QUERY_SAMPLE
COVERAGE_JUSTIFICATION = NOT ESTABLISHED
NEW_B_EVIDENCE         = NOT ESTABLISHED
```

## 2.4 硬性失败条款（凌翼明确）

> 如果未来的审查发现**查询完整性、进程身份绑定或句柄值表示范围**无法被可信证明，该命题**不得输出 `ABSENCE_CONFIRMED`**。

```text
若 (查询完整性 ∨ 进程身份绑定 ∨ 句柄值表示范围) 不可信证明
  ⇒ 禁止输出 ABSENCE_CONFIRMED
```

---

# 交付项 3 · N-1..N-7 的 claim-scoped 覆盖矩阵

## 3.1 先区分三种状态（凌翼要求，不得混为一谈）

凌翼：

> 预注册 §37 列出了 `UNREGISTERED_EPISODE_REINJECTION` 等停机条件，**并不意味着这些违规事件已经发生**。

| 状态 | 含义 | 后果 |
|---|---|---|
| **S-1 尚未证明受控** | 科学验收证据不足 | **当前不能 PASS** |
| **S-2 已有有效证据表明发生** | 按适用 scope | **判 INVALID** |
| **S-3 前瞻分析证明不属因果依赖** | 可提排除理由 | **需独立审查** |

**三者不得混用。本矩阵全部落在 S-1。**

## 3.2 覆盖责任矩阵（凌翼裁定二，逐条照录）

| 缺口 | 首要证据责任 | 审查重点 |
|---|---|---|
| **N-1** 随后打开禁止对象 | Coder 提出 OS 访问边界及证据方案；知微核验 | 实际访问是否被控制 |
| **N-2** `DuplicateHandle` | Coder 提出能力约束；知微与钳星核验 | 复制、旧进程和新授权 |
| **N-3** 代理 / IPC | Coder 登记通信主体与通道；睫核对 | 禁止信息能否间接回流 |
| **N-4** 网络 | Coder 说明网络控制或具体 scope 排除依据；知微核验 | **不能用受限令牌代替网络隔离证据** |
| **N-5** 跨 episode 残留 | 钳星主审；Coder 提供生命周期设计 | 旧信息是否影响新 episode |
| **N-6** Reset 后证据 | 钳星与知微主审 | L2 所需 Reset 与重新建立证据 |
| **N-7** 端到端隔离 | 睫评估科学归因；凌翼最终裁定 | 综合性结论 |

**凌翼的限定，我照录**：

> 这是一份**设计责任分配**，不是声称上述成员已经接受任务，更不是任何一项缺口已经关闭。
> **N-7 不应被设计成一台新的"神奇测量仪"。端到端保证来自相关直接访问、间接通道、时间边界和失败收敛证据的合取。**

## 3.3 claim-scoped 应用表

| 科学层级 | N-1 | N-2 | N-3 | N-4 | N-5 | N-6 | N-7 | 新 B 能否单独支持 |
|---|---|---|---|---|---|---|---|---|
| **C1 / Basic L1** | **相关** | 相关 | **相关** | 相关 | 相关 | 不适用 | **相关** | **NO** |
| **C2 / C3** | 相关 | 相关 | **强相关** | **强相关** | **强相关** | 不适用 | 强相关 | **NO** |
| **L2** | 相关 | 相关 | 相关 | 相关 | **强相关** | **强相关** | 相关 | **NO** |

**"相关"的判定依据**：预注册 §37 的 stop conditions 中，`UNREGISTERED_EPISODE_REINJECTION`（L2253）与 `UNREGISTERED_RETRIEVAL_INDUCED_WRITE`（L2254）正是"信息回流"类混杂；`RESET_COMPATIBILITY_NOT_ESTABLISHED`（L2237）与 `STATE_OBSERVER_NOT_INDEPENDENT`（L2251）分别对应 N-6 与观察者独立性。

## 3.4 凌翼对 C1 的明确裁定

> 预注册 §28.1 特意允许**仅尝试 C1**，而不要求建立 C2/C3 的全部非存储对照。
> 因此，**不允许为了 C3 的高级保证，倒过来无限阻断所有 C1 设计**。
> 但 C1 仍必须满足自己的 Basic L1 gate：**独立状态观察、写入与不写入对照、冻结的归因规则、完整来源，以及没有与本次 claim 相关的有效停机事件**。

**据此**：

```text
C1 / Basic L1 = 新 B 单独不能支持；可独立评估是否有其他合格证据
C2 / C3       = 当前证据不足，不授权验收
L2            = 当前证据不足；必须另行建立 Reset 后证据
新 B 局部命题  = 仅是候选，尚无有效实际观测
```

---

# 交付项 4 · 新 B 的科学增量与停止条件（凌翼要求的核心分析）

凌翼：

> 当前还没有证明，投入工程实现这个极窄的数值命题，**能为 AfterGlow 的科学测量带来足够的增量价值**。

## 4.1 新 B 若获得有效测量，它增加了什么

| 项 | 新 B 提供的 | 是否科学增量 |
|---|---|---|
| 单次查询样本中 ℱ 数值缺席 | 一个**可失败的**观测结果 | **是**，但极小 |
| 创建路径的 API 标签 | 代码路径声明 | **否**（非观测，且已有） |
| 三个静态前提 | API 签名事实 | **否**（文档已知） |
| 仪器灵敏度（throwaway 上） | 检测器能看见 | **否**（已有） |

## 4.2 增量价值评估

**新 B 相对于"什么都没有"，增加了一条可失败观测。**

**新 B 相对于当下已有的东西**：

| 已有证据 | 内容 |
|---|---|
| Profile B 正负对照 | 已证明"注册路径在一个 throwaway 上不漏" |
| 三个静态前提 | API 签名已知 |
| 字段 2 的结构读取 | STARTUPINFO 已被读取检查 |

⇒ **新 B 的**唯一**新增是：把上述结论从 **throwaway 对象**移到**指定的真实 worker 对象**上，且**只针对 ℱ 中的几个数值**。

## 4.3 我的建议：**停止该 lineage 的实施计划**

```text
RECOMMENDATION = STOP_IMPLEMENTATION_OF_THIS_LINEAGE
```

**理由（逐条）**：

**一 · 它不能支持任何科学层级的验收。**
C1/L1/C2/C3/L2 全部 `NO`。它单独**不能**签发任何 claim。

**二 · 它的唯一增量受限于一个无法验证的前提。**
"查询完整性 / 覆盖充分性"目前 `NOT ESTABLISHED`（§2.3）。若该前提无法可信证明，**命题甚至不能输出 `ABSENCE_CONFIRMED`**（§2.4）——**那样它连那一点增量也给不出**。

**三 · 它的结论形状最容易被读强。**
`ℱ ∩ H_sample(W) = ∅` 与 `WorkerCannotAccess(P)` 在外观上极近，而凌翼裁定三改名，正是为了防这个。**一个必须靠改名来防误读的命题，其工程投入的性价比存疑。**

**四 · 真正决定科学可行性的不是它。**
N-1..N-7 中，**N-3（代理）与 N-5（跨 episode）** 是与信息回流 stop condition 直接相关的两项，而新 B 对它们**覆盖为零**。**把工程投在新 B 上，是在做最不关键的那一格。**

## 4.4 但我把决定权交回，并列出"若改变我建议"的条件

**若以下任一条成立，我的建议应被推翻**：

| # | 条件 | 谁能判定 |
|---|---|---|
| R-1 | 有科学 claim 的因果依赖**只**包含"创建时刻 ℱ 的数值缺席" | 睫 |
| R-2 | 查询完整性与覆盖可被可信证明（使 `ABSENCE_CONFIRMED` 可达） | 知微 |
| R-3 | 凌翼裁定：该局部命题是进入下一阶段的必要前置 | 凌翼 |

**我不自行决定终止。** 我提出建议，等三方与凌翼裁。

---

# 5 · 本轮我修正的自己错误

| # | 错误 | 来源 |
|---|---|---|
| 1 | 把字段 1（`creation_api` 字面量）归入"真观测" | 凌翼 |
| 2 | v0.3 称"四条真实来路"——实际只有**两条**是观测（字段 2、字段 6 的 `hstat`） | 凌翼+睫合并 |
| 3 | 名称仍用 `FORBIDDEN_HANDLE_ABSENCE`，易被读成"访问能力消失" | 凌翼裁定三 |
| 4 | 未区分"尚未证明受控 / 已发生 / 不属因果依赖"三态 | 凌翼裁定二 |

---

# 6 · 状态

```text
CLAIM_NAME                  = REGISTERED_HANDLE_VALUE_ABSENCE_AT_OBSERVATION
CLAIM_FORM                  = B / ACCEPTED AS CANDIDATE
PROOF_SOURCE_INDEPENDENCE   = NOT ESTABLISHED
STATIC_TRUE_FIELDS          = STATIC PREMISES / NOT OBSERVATIONS
CREATION_API_PROVENANCE     = DECLARED CODE PATH

T_OBS_SEMANTICS             = SINGLE_QUERY_SAMPLE
COVERAGE_JUSTIFICATION      = NOT ESTABLISHED
NEW_B_EVIDENCE              = NOT ESTABLISHED

C1_L1_SUPPORTED_BY_NEW_B    = NO
C2_C3_L2_SUPPORTED_BY_NEW_B = NO
N_COVERAGE_MATRIX           = ALL S-1（尚未证明受控）

RECOMMENDATION              = STOP_IMPLEMENTATION_OF_THIS_LINEAGE

RE-3 / DESIGN_ACCEPTANCE / PERSISTENT_WORKER_CLEAN_BLOCK / G2_END_TO_END = 未变
FROZEN_Q3_RC11              = UNCHANGED
CODE_CHANGE / CONTRACT_CHANGE / NEW_LINEAGE = NOT AUTHORIZED
SCIENTIFIC_EXECUTION        = MAY NOT START
```

---

# 7 · 本轮我没有做的事

- **未**写代码、**未**开发新审计器
- **未**修改冻结 Q3
- **未**接线
- **未**开展 Windows 实验
- **未**自行决定终止 lineage（只提建议）
- **未**代替睫/知微/钳星认领矩阵中的责任

**提交三方程复核后，回到船长与凌翼决定是否进入下一阶段。**
