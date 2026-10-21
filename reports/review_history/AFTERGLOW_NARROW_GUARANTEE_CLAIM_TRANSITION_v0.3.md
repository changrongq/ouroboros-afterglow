# AFTERGLOW NARROW GUARANTEE CLAIM TRANSITION v0.3

**性质**：**合同变更提案（第二次修订）**。**不是已批准的合同变更。**
**上一版被审**：`5fc802f6a0ef78875515a654c99837a74d26c9da`（v0.2）

```text
CLAIM_FORM_B_SELECTION = ACCEPTED（知微）
PROPOSAL_ACCEPTANCE    = CONDITIONAL / NOT_YET（睫不升不降；知微 NOT_YET）

本轮处理：知微 R1 / R2 / R3 + RE-A 补齐 + 观测机制待办
          睫 BF-4 / BF-5 / BF-1升级 / BF-2撤回 / NB-5 / NB-6 / NB-7 + RE-C 裁定

CODE_CHANGE / FROZEN_CONTRACT_CHANGE / NEW_LINEAGE_IMPLEMENTATION = NOT AUTHORIZED
SCIENTIFIC_EXECUTION = MAY NOT START
PERSISTENT_WORKER_CLEAN_BLOCK = ACTIVE ； G2_END_TO_END = NOT ESTABLISHED
```

---

# 0 · 本轮我要改的六处

| # | 来源 | 内容 |
|---|---|---|
| **F-1** | 睫 BF-4（最重） | 字段 3 / 字段 4 是**字面量 True**，不是观测 |
| **F-2** | 睫 BF-5 | 字段 5 与字段 6 **共享 `leak_ok`**，不是两条来路 |
| **F-3** | 睫 NB-5 | `leak_ok` 的负向控制要求 **throwaway 取得 CLEAN**（probe 类对象） |
| **F-4** | 睫 BF-1 升级 | 字段 4 **不是字段 1 的推论，是常量** |
| **F-5** | 知微 R3 | 选了 B 之后，**不再以"继承保值"作为前提**；补"同一时刻不同数值仍可指向 P" |
| **F-6** | 知微 R1/R2 | "需要不经过 L3 的新路径"表述改为无歧义；§2.1 限定为豁免分支 |

---

# F-1 · 字段 3 / 字段 4 是常量（睫 BF-4，我核实成立）

## 1.1 字节

`q3_reset_chain.py` L331-355：

```python
def startupinfo_facts(si) -> dict:
    """凌翼 Q3 STEP 1: record what the STARTUPINFO actually established.

    We do NOT assert a fixed True; we READ the real struct we are about to pass:
    ...
    """
    return {
        "cb_set": (getattr(si, "cb", 0) == ctypes.sizeof(si)),          # 真读
        "std_handles_null": (... hStdInput/Output/Error ...),          # 真读
        "reserved_zero": (getattr(si, "cbReserved2", 0) == 0 ...),     # 真读
        # CreateProcessWithLogonW takes NO handle list / bInheritHandles parameter
        "no_inheritable_handle_list": True,      # ← 字面量
        "api_has_no_inherit_param": True,        # ← 字面量
        # LOGON_WITH_PROFILE creates a fresh logon session for the worker
        "fresh_logon_session": True,             # ← 字面量
    }
```

## 1.2 而 L961-963 的注释写的是

```python
# 6b. 凌翼 Q3 STEP 1 (P1·Blocking): the inherited-handle-isolation gate MUST be
#     computed from REAL evidence, not hard-coded True.
```

**凌翼要求"不得硬编码 True"；满足它的这个函数，六个键里三个是硬编码 True，而它的 docstring 写着 "We do NOT assert a fixed True"。**

## 1.3 后果

```text
字段 3 = inheritable_channels_checked          ← 常量 True
字段 4 = forbidden_handle_noninheritrance_proven ← 两个合取项都是常量 True
```

**一个字面量恒为 True 的字段，在任何情况下不会为 False。**

⇒ **它不携带信息。**（睫第 202 句：一个不可能失败的动作，不是验证）

## 1.4 因此撤回 v0.2 §3.1

v0.2 说"非继承的唯一支撑是 A（**读到**一个 API 名）"。

**字节说：那不是"读到"，那是"写死"。**

---

# F-2 / F-3 / F-4 · 来路表重写（按睫给的修正）

## 2.1 字节依据

```python
# q3_reset_chain.py L974-980
build_profile_b_proof(
    att,
    startupinfo_facts=...,
    leak_control_ok=leak_ok,               # ← 字段 5
    controller_opened_forbidden=leak_ok,   # ← 字段 6 的第一个合取项
    worker_known_forbidden_present=worker_known_forbidden,
)

# win32_worker_process.py L267-269
"no_known_forbidden_handle_present": bool(
    controller_opened_forbidden is True
    and worker_known_forbidden_present is False)
```

⇒ **字段 6 = 字段 5 ∧ (hstat ≠ FOUND_TARGET)**

## 2.2 `leak_ok` 取自 probe 类对象（睫 NB-5）

```python
# win32_worker_process.py L423-424
neg_clean = (neg_status == HANDLE_AUDIT_CLEAN) and h2_opened
ok = bool(detected and neg_clean)
```

**负向控制要求一个 `time.sleep(3)` 的 throwaway 子进程取得 `CLEAN`。**
**短命、简单、能拿到 CLEAN ⇒ 正是 probe 类对象的定义。**

⇒ **`PROBE_CLEAN != BUSINESS_CLEAN` 在此第二次适用。**

## 2.3 重写后的来路表（照睫给的格式）

| 类 | 来路 | 对应字段 | 性质 |
|---|---|---|---|
| **真观测** | ① `attestation.creation_api` | 字段 1 | API 名观测 |
| **真观测** | ② `si` 的 `cb` / std handles / reserved（三个键真读） | 字段 2 | 结构观测 |
| **真观测** | ③ `leak_ok`（取自 **throwaway/probe 类**对象） | 字段 5，且字段 6 的一半 | 仪器灵敏度 |
| **真观测** | ④ `hstat`（`!= FOUND_TARGET`） | 字段 6 的另一半 | 运行期状态 |
| **常量** | ⑤ `no_inheritable_handle_list = True` | 字段 3 | **零信息** |
| **常量** | ⑥ `api_has_no_inherit_param = True`、`fresh_logon_session = True` | 字段 4 | **零信息** |

```text
六字段 = 四条真实来路 + 两个常量
且 字段 5 与 字段 6 共享其中一条（leak_ok）
```

**v0.2 的"六字段 = 五条来路"作废。**

## 2.4 一个正反守则（睫 NB-5 要求写进文本）

```text
leak_ok 的负向控制取自 throwaway（probe 类）对象。
不得读作业务 worker 上的隔离证据。
```

---

# F-5 · 知微 R3：B 形式不再需要"继承保值"作为前提

## 3.1 知微的论证（我接受）

> 这个纯数值命题不需要先证明这些值如何可能进入 W。无论 Windows 是否保留继承值，只要观测有效、覆盖成立，就能讨论这些特定值当时出现或未出现。
> ⇒ §13.2 的"值未命中 ⇒ 缺席，依赖继承保值且未实测"与 B 形式不一致。

**采纳。删除该依赖。**

## 3.2 继承保值的重新登记

```text
前提一（继承保值）= 历史命题背景，来源 Microsoft Learn "Inheritance"
                    ≠ B 形式的阻塞验收项
                    不为其开设实验
```

## 3.3 但 B 必须补一个新边界（知微要求）

> **ℱ 的数值缺席，不能证明 W 在同一 t_obs 没有通过其他句柄值访问 P。**
> 例：ℱ = {0x100}，W 的 0x100 不存在，但 0x200 可以指向 P；则数值缺席命题为真，"W 不持有 P 的句柄"为假。

**v0.2 §1.2 只排除了 `t_obs` 之后的访问，漏了同一时刻的其他值。补上：**

```text
本命题不断言：
  ❌ 这些句柄从未被继承
  ❌ worker 在 t_obs 之后不持有 P 的访问
  ❌ worker 的句柄集合为空
  ❌ 【新增】worker 在 t_obs 时刻未通过**其他句柄值**持有对 P 的访问
```

## 3.4 名称的固定说明（知微建议，不另起表决）

```text
当前名称：REGISTERED_FORBIDDEN_HANDLE_ABSENCE_AT_OBSERVATION
固定说明：缺席的是【登记数值】，不是受保护对象的全部访问能力。
```

**并接受知微建议的备选**：`REGISTERED_HANDLE_VALUE_ABSENCE_AT_OBSERVATION`（若凌翼认为更清晰）。

## 3.5 删除 v0.2 §3.1 / §14 中"创建未继承 = API 签名事实"的论断

知微：

> 本轮无需裁决已放弃的 A 命题。

**采纳。A 命题的论证从本文档移除，不再作为 B 的支撑。**

---

# F-6 · 知微 R1 / R2：L3 表述改正

## 4.1 R1 · "需要不经过 L3 的新路径"改为无歧义

知微：

> 旧 L3 阻断的是**现有适配器验收**；它不构成"同一个 worker 上无法独立观察数值缺席"的**逻辑证明**。
> 可以设计独立观测入口，同时让旧 L3 完整保留。
> 这不是允许业务绕过 L3，不是允许接线，也不是批准新实现；只是在合同图上分开"局部命题验证"与"旧业务验收"。

**改正为**：

```text
L3 的 CLEAN 要求 = 现有业务适配器验收的门槛
                 ≠ 同一 worker 上无法独立观察数值缺席的逻辑证明

本 claim 的验证 = 独立的局部命题验证入口
旧 L3        = 完整保留，不因此放宽
业务绕过 L3  = 不允许
接线         = 未授权
```

**并删除"字段六不可达"这个命名**（知微收口条件）。

## 4.2 R2 · §2.1 的豁免描述需限定

知微：

> 同文件第 939–942 行仍首先拒绝 `FOUND_TARGET`，其他资格条件也仍存在。
> 可写"对无已确认目标的审计状态，允许正式 `UNRESOLVED`；错误/缺失仍拒绝"，不要写为整个 Profile B 仅有两种拒绝原因。

**v0.2 已改为**：

```text
Profile B 的豁免分支：
  对【无已确认目标】的审计状态，允许正式 UNRESOLVED 并记录；
  错误/缺失（None / ERROR）仍拒绝。
  —— 这不表示 Profile B 整体只有两种拒绝原因：
      L939-942 仍首先拒绝 FOUND_TARGET，其他资格条件亦仍存在。
```

## 4.3 四件事分开记录（知微收口条件）

**不强行认定两方在讨论同一个字段。**

| # | 事实 | 层 |
|---|---|---|
| 1 | Profile B 接受 `UNRESOLVED`（豁免分支）、拒绝 `FOUND_TARGET`/`None`/`ERROR` | L2 |
| 2 | 业务适配器要求恰好 `CLEAN` | L3 |
| 3 | 新 B 的观测器 **尚未建立**（`NOT ESTABLISHED`） | L4 |
| 4 | 新 B 即使建立，**不能替代**旧业务 CLEAN 要求 | L4 → L3 |

**`NEW_B_EVIDENCE = NOT ESTABLISHED`** —— 知微原话，照录。

---

# 5 · RE-A 补齐（睫已定位，我核了字节）

## 5.1 生产点

**位置**：`q3_reset_chain.py` L331 `def startupinfo_facts(si)`，**不是** `win32_worker_process.py`。（v0.2 说错了）

**调用链**（睫给，我核了 L974-979 与本文件一致）：

```text
L381-383   si_used = si_pi[0] ; _spawn(si_pi, ...)
L429-438   WorkerAttestation(..., creation_api="CreateProcessWithLogonW",
                             startupinfo_facts=startupinfo_facts(si_used))
L974-979   build_profile_b_proof(..., startupinfo_facts=getattr(att,...))
```

## 5.2 六个键的生产方式（睫核，我复核）

| 键 | 实际来源 | 性质 |
|---|---|---|
| `cb_set` | 比较传入结构 cb 与 sizeof | **真读** |
| `std_handles_null` | 读取三个标准句柄是否为零/None | **真读** |
| `reserved_zero` | 读取两个保留字段是否为零/None | **真读** |
| `no_inheritable_handle_list` | **函数内字面值 True** | **常量** |
| `api_has_no_inherit_param` | **函数内字面值 True** | **常量** |
| `fresh_logon_session` | **函数内字面值 True** | **常量** |

## 5.3 第二构造点（睫 NB-7）

`q3_reset_chain.py` L1830-1832：自测路径**手写全 True dict**。

⇒ **`startupinfo_facts` 是调用方传入的参数，值源完全由调用方决定。**

```text
RE-A_PRODUCER_LOCATION = VERIFIED（chain.py L331 / L438 / L1830）
RE-A_OPEN_ITEM = 三个常量键是否改为从实际调用参数读取，或登记为 TCB 假设
                 —— 需凌翼裁，本轮不改代码
```

---

# 6 · 观测机制的未决项（知微要求如实保留）

## 6.1 `t_obs` 是哪个证据事件

知微：

> 一次查询有开始和结束时刻；如果要声称一个共同瞬时状态，需说明快照或等效一致性的依据。
> 若仅保证一个返回样本中未见这些值，就把结论绑定到该样本，不自动推广成整个查询区间或某个未证实的原子时点。

**本版诚实结论**：

```text
T_OBS_SEMANTICS = SINGLE_QUERY_SAMPLE（拟）
  即：结论绑定【一次查询返回的样本】，
      不推广为"整个查询区间无变化"，也不声称"原子时点"。
  若将来要主张更强语义，需另行给出快照一致性的依据。
```

## 6.2 "覆盖 ℱ"如何由证据成立

知微：

> PID/句柄范围检查是必要改进，不是自动证明覆盖。
> 要定义解析有效、身份连续绑定、查询完整/失败的判据。
> 可以把要求限定到目标进程与 ℱ，不必分类全部无关对象。

**保留为待办，本版只写要求不写实现**：

```text
COVERAGE_JUSTIFICATION = NOT ESTABLISHED
  需要：解析有效判据 / 身份连续绑定判据 / 查询完整或失败的判据
  限定：只需覆盖目标进程与 ℱ，不需分类无关对象
```

## 6.3 §5.1 的"整次 INVALID"须收窄（知微要求）

知微：

> 若选择纯数值 B，不应无说明地要求整个控制器句柄表不变；
> 请限定保护的登记关联或固定集合，明确哪些变化真正影响所声明命题。

**改正**：

```text
原（过宽）：登记与创建之间若【句柄表】发生变化 ⇒ 整次 INVALID
改为：登记与创建之间，若【ℱ 中登记的句柄值/对象身份】发生变化 ⇒ 整次 INVALID
      控制器句柄表的其他变化不影响本命题。
```

§7 C-9 同步改为"ℱ 变动"。

---

# 7 · 睫 RE-C 裁定，我照录

睫取到预注册字节后裁定：

> **C1 = 不能由本窄保证单独支持**（不给 CONDITIONAL 缓冲）
> **L1（C1 scope）= 同上**
> 但这**不是**说 C1 永远不能——它需要 N-1..N-7 中相关项由**其他已建立证据**覆盖，或该 claim scope 不依赖它们，**而这要凌翼裁**。

**依据（睫给）**：预注册 **没有"混杂路径清单"** 这种形式，它用的是 gate + scope + §37 Master Stop Conditions。Basic L1 gate 条件 5 要求"无命中 §37 的 stop condition"，而 §37 含：

```
UNREGISTERED_EPISODE_REINJECTION
UNREGISTERED_RETRIEVAL_INDUCED_WRITE
STATE_OBSERVER_NOT_INDEPENDENT
RESET_COMPATIBILITY_NOT_ESTABLISHED
```

**前两条正是"信息回流"类混杂，而窄保证只阻断"创建时刻继承"一条。**

## 7.1 我据此更新 §8

| Claim | 结论 | 依据 |
|---|---|---|
| **C1** | **不能**（睫裁） | §37 前两条 stop condition 命中 |
| **L1（C1 scope）** | **不能**（睫裁） | Basic L1 gate 条件 5 无法单独满足 |
| C2 / C3 / L2 | 不能 | N-3/N-4/N-5/N-6 |

**并保留睫的限定**：这不是"C1 永远不能"，是"需其他已建立证据覆盖相关项，由凌翼裁"。

---

# 8 · NB-6 · 两个"独立观察者"同名不同义（睫要求劈开）

睫：

> 预注册 §11 Independent State Observer：observer != write operator；不能写注册 substrate；独立读/算状态身份 ⇒ **有冻结 identity/version/hash ⇒ 可满足**
> RE-3 RESET_OBSERVER_IDENTITY：边界生效期内、以非特权身份、对真实持久 worker 发起越界尝试 ⇒ **不可得**
> ⇒ **同名，不同义**
> 将来一定有人说"预注册 §11 已有 Independent State Observer，所以 RE-3 有解了"——而那是 193 句最纯的形状。

**本文档明写**：

```text
预注册 §11 的 Independent State Observer
   ≠ RE-3 的 RESET_OBSERVER_IDENTITY
前者可满足；前者不解决后者。
RE-3 维持 NOT ESTABLISHED。
```

---

# 9 · 睫 §一 的自认，我照录并采纳其方法

睫：

> 我把【我核到的那一层】，写成了【那一格的全体】。而我没有写层。
> 我的错不是停在了我这里——它被 Coder 当成已核对的引用，写进了 v0.1，然后才在下一环被知微接住。
> **我写的字，在下游会自动升级成"已核对"。**
> 所以从今天起，我给别人审查意见时，凡是引用代码处，我写明【我核到的是哪一层】。

**我把这条方法用到本文档**：§2 / §5 的每处引用都标了层（L1/L2/L3/L4）。

---

# 10 · 状态

```text
CLAIM_FORM                    = B（观察时点数值缺席）
CLAIM_NAME                    = REGISTERED_FORBIDDEN_HANDLE_ABSENCE_AT_OBSERVATION
                                （固定说明：缺席的是登记数值，非全部访问能力）
PROPOSAL_ACCEPTANCE           = CONDITIONAL / NOT_YET

睫 BF-4 字段3/4 是常量          = 已确认并采信（§F-1）
睫 BF-5 字段5/6 共享 leak_ok    = 已确认并采信（§F-2）
睫 BF-1 升级 字段4 是常量       = 已接受
睫 BF-2 撤回（分层）            = 已按知微分层次表述
睫 NB-5 throwaway 上的 CLEAN    = 已写进文本（§2.4）
睫 NB-6 同名不同义              = 已劈开（§8）
睫 NB-7 第二构造点              = 已记录（§5.3）
知微 R1 L3 表述                 = 已改（§4.1）
知微 R2 豁免限定                = 已改（§4.2）
知微 R3 不再以继承保值为前提     = 已改（§F-5），并补新边界

RE-A 生产点                     = VERIFIED（L331/L438/L1830）
RE-A 待决                       = 三个常量键如何处理（需凌翼裁）
RE-B 继承保值                   = 降为背景，不再是 B 的阻塞项
RE-C C1/L1                      = 睫已裁"不能"，剩余待凌翼

T_OBS_SEMANTICS                 = SINGLE_QUERY_SAMPLE（拟）
COVERAGE_JUSTIFICATION          = NOT ESTABLISHED
NEW_B_EVIDENCE                  = NOT ESTABLISHED（观测器未建立）

IMPLEMENTATION_AUTHORIZATION    = NONE
SCIENTIFIC_EXECUTION            = MAY NOT START
```

---

# 11 · 需要凌翼裁的三件事

**一 · 字段 3 / 字段 4 的三个常量键怎么办？**

- (a) 改为从实际调用参数读取（需代码授权）
- (b) 在合同中登记为 **TCB 假设**（"我们相信 `CreateProcessWithLogonW` 无继承参数、`LOGON_WITH_PROFILE` 产生新会话"）
- (c) 保留现状但**在文档中标注为零信息字段**（本版已做）

**我倾向 (b)**：这不是可以"读取"的东西——它是 API 文档事实。**但把它写成"读到的"就是错。**

**二 · N-1..N-7 由谁覆盖？**（睫明确此项不由她裁）

**三 · 名称是否采用 `REGISTERED_HANDLE_VALUE_ABSENCE_AT_OBSERVATION`？**（知微建议，非必须）

---

# 12 · 本轮我没有做的事

- **未**写代码（三个常量键未改）
- **未**修改冻结合同
- **未**建 lineage
- **未**替凌翼裁 N-1..N-7 的覆盖归属
- **未**声称新 B 观测器已建立
- **未**把 C1/L1 改回"需裁定"（睫已裁"不能"）
