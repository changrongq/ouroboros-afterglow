# C1 STRUCTURAL CLOSURE DESIGN v0.3 · 章节映射更正 + 必要条件 + 负向测试矩阵

**性质**：非冻结、文档级设计修订。不构成代码或科学执行授权。
**依据**：`凌翼裁定 · C1 Structural Closure v0.2`（2026-10-27）
**被审对象**：v0.2，`e3e285fc6dc8b03e68cae27631dd7f77aa4a4078`，SHA-256 `ed325ff90a827d8fd603e3ce1301bdbd414178d303dc26983353f2355d1c2961`
**日期**：2026-10-27

```text
BF8_STATUS                     = OPEN
BF8_AUTHORITY_BOUNDARY         = NOT ESTABLISHED
NB31_NON_NORMATIVE_ALIAS       = CONDITIONALLY ACCEPTED
NB31_PREREG_CHANGE             = NOT AUTHORIZED
Q1_FULL_EQUIVALENCE            = NOT ESTABLISHED
CODE_CHANGE                    = NOT AUTHORIZED
SCIENTIFIC_EXECUTION           = MAY NOT START
```

---

# 0 · 我这一轮的错：把 §28.1 当成了 C1 的成立规则

## 0.1 我的错

**v0.2 §9 写：**

```text
C1AuthorityGate = ESTABLISHED ⟺ prereg §28.1 C1 class rule 满足
（睫 Q-1 提出，我照录转呈）
```

**凌翼驳回，理由是规范引用不准确。我核了字节，全部成立：**

```text
prereg L629   "# 12. Positive Evidence Ladder"                      [读文件]
prereg L633   "## C1 — STORAGE_WRITE_ESTABLISHED"
prereg L635-637  "C1 表示：storage write 是目前最高被正向建立的 change class。"
prereg L643-646  "最强允许 claim：REGISTERED_STORAGE_WRITE_OBSERVED"
prereg L649   "因此 C1 是证据断言，不是世界断言。"

prereg L685   "# 13. L1 — Attributable Registered Change"           [读文件]
prereg L700-711  五项 Basic L1 gate
prereg L715-725  三项 class 选择规则（C3 → C2 → C1）
prereg L722-724  "else if an episode-specific registered storage write is established
                  in preregistered LITERAL_STORAGE_COMPONENTS under the Basic L1 /
                  §28.1 scope: PRE_RESET_CHANGE_CLASS = C1"

prereg L1698  "# 28. Class-Scoped Mandatory Failure Witness"        [读文件]
prereg L1711  "## 28.1 C1 / Basic L1 Witness"
prereg L1715-1719 "C1 的最小 mandatory failure path 是：
                   TARGET WRITE ARM vs NO-WRITE / MATCHED BASELINE CONTROL"
prereg L1721-1723 "它回答：attributable registered write/change 是否真的发生？"
prereg L1741  "仍可合法尝试并建立 C1。"
prereg L1743  "## 28.2 Attempted C2 Witness"  ← §28.1 止于此之前

prereg L1379  "# 24. POST_RESET_CLASS_RULE"                          [读文件]
```

**⇒ `§28.1` 规定的是 C1 的 **mandatory failure witness**（两臂对照），不是 C1 的成立规则。**
**⇒ C1 的成立规则在 `§13` L722-724。**
**⇒ C1 的科学含义与最强允许 claim 在 `§12` L633-649。**
**⇒ post-reset C1 在 `§24`，不得由 pre-reset 权威门覆盖。**

**⇒ 所以"§28.1 witness 满足 ⟺ 正式 C1 成立"是错的：§28.1 满足只是必要条件之一。**

## 0.2 这是我同一类错误的第五次

```text
E-3   N4/N5 编号错位                  ← 引用错
E-4   write_operator 在 §5（实为 §4）  ← 章节错
R-19  §7.2 禁"进 digest"读成"禁建关联"  ← 范围错
E-7   "存在返回 C1" 写成 "11 处全返回"   ← 量化错
E-9   §28.1 当成 C1 成立规则           ← 章节错（本次）
```

**⇒ 而 E-4 和 E-9 是同一类：我用"这一节提到了 C1"代替了"这一节定义了 C1"。**

**⇒ 因为 §28.1 标题里就有 "C1"，L723 也引用了 §28.1，所以它看起来像 C1 的定义处。**
**⇒ 而它只是被引用的**范围限定词**（"under the Basic L1 / §28.1 scope"）。**

---

# 1 · 表五 · 章节职责映射（凌翼 §2 要求）

| 章节 | 行 | 它定义什么 | 在 AuthorityGate 中的角色 |
|---|---|---|---|
| **§12** | L629-649 | C1 的**科学含义**与**最强允许 claim**（`REGISTERED_STORAGE_WRITE_OBSERVED`） | 决定"成立之后能说什么"，不是"是否成立" |
| **§13** 五项 gate | L700-711 | 正向 pre-reset class 的**共同入口** | **必要条件集合**（全部须满足） |
| **§13** class 选择 | L715-725 | C3 → C2 → C1 的**优先级** | **优先于** AuthorityGate 的 C1 结论 |
| **§28.1** | L1711-1741 | C1 的 **mandatory failure witness**（两臂对照） | 必要条件中的**一项** |
| **§24** | L1379-1559 | **post-reset** C1 | **超出 pre-reset AuthorityGate 范围** |
| **§37** | L2203-2262 | stop conditions | 任一命中 ⇒ 不建立 |

**⇒ 关键：`§28.1` 是 §13 class 选择里的一个**限定词**（L723 "under the Basic L1 / §28.1 scope"），不是独立成立条件。**

---

# 2 · 单向必要条件（凌翼已批准，我照录为设计约束）

**凌翼原文批准的形态：**

```text
C1AuthorityGate.PRE_RESET_C1 = ESTABLISHED
    ⇒
    all applicable frozen prereg requirements satisfied
    ∧ §13 Basic L1 gate valid
    ∧ §28.1 required witness valid
    ∧ episode-specific registered storage write established
    ∧ required independent observation and provenance valid
    ∧ no applicable invalidity / stop condition
```

**⇒ 我照录，并落为 AuthorityGate 的**内部结构**（不是输出声明）：**

```text
AuthorityResult.ESTABLISHED 只有在下列全部为真时才可产生：
  R-1  §13 L702  本次 execution 与 claim scope 所需 manifests / frozen rules 均有效
  R-2  §13 L703  §11 Independent State Observer 合法，完成 registered before/after observation
  R-3  §13 L704  §28.1 TARGET WRITE ARM vs NO-WRITE / MATCHED BASELINE CONTROL 已实际执行
  R-4  §13 L705-709  frozen D_ATTRIBUTION 在 canonical ΔS_identity_masked 上给出 ATTRIBUTED
  R-5  §13 L711  required provenance 完整，且无命中与本次 claim 相关的 §37 invalidity / stop condition
  R-6  §13 L722-724  episode-specific registered storage write 在 preregistered
                     LITERAL_STORAGE_COMPONENTS 上成立
  R-7  BF-8 的 writer—execution—observation 关联成立（本设计新增，非 prereg 原有）
  R-8  BF-9 的 execution 来源绑定成立（本设计新增）
  R-9  NB-29 通路登记成立（本设计新增）
```

**⇒ 而 `R-7 / R-8 / R-9` 我必须标明它们是**本设计新增**，不在冻结 prereg 里。**
**⇒ 这意味着 `AuthorityGate = ESTABLISHED` 比 prereg 的 C1 更严格，不是相等。**

## 2.1 反向蕴含不成立（凌翼裁 Q1_REVERSE_SUFFICIENCY = NOT ESTABLISHED）

```text
⇒ prereg §13 全部满足，不自动意味着 AuthorityGate 会输出 ESTABLISHED
   （因为 R-7/R-8/R-9 是新增的）
⇒ 也不意味着 AuthorityGate 不误判：
   漏判（该建立的没建立）、误判（不该建立的建立了）、
   越权签发、非法消费 —— 四条路径都未验证。
```

## 2.2 class 优先级必须保留（凌翼 Q1_CLASS_PRIORITY_PRESERVATION = REQUIRED）

**凌翼原文：**

> "注册存储写入这一证据要素成立" 与 "最终报告的最高 pre-reset change class 为 C1" 并非总是同一件事。若 C2 或 C3 独立成立，§13 的 class selection 会报告更高类别。不得让 AuthorityGate 覆盖这条优先级规则。

**⇒ 落为硬约束：**

```text
AuthorityResult 必须携带两个不同字段：
  · episode_specific_write_established  = BOOL（R-6 是否成立）
  · reported_pre_reset_change_class     = C1 / C2 / C3（按 §13 L715-725 优先级）

⇒ 禁止把前者当作后者。
⇒ 若 C2 或 C3 独立成立 ⇒ 后者必须是 C2/C3，即使 C1 要素成立。
⇒ 这一条我 v0.2 完全没写。
```

## 2.3 post-reset 排除（凌翼 Q1_POST_RESET_SCOPE = EXCLUDED）

```text
⇒ 本文的 AuthorityGate 只覆盖 pre-reset C1 claim。
⇒ post-reset C1 由 §24（L1379-1559）的规则决定，不得由本文的 AuthorityGate 自动覆盖。
⇒ 也不得扩展成 Memory Qualification。
```

---

# 3 · NB-31 · `L1_local` 的准确映射（凌翼 §1，条件接受）

**凌翼裁定：`CONDITIONALLY ACCEPTED — NON-NORMATIVE ALIAS ONLY`。三条约束我全部照录：**

```text
① 不得修改冻结产物的原始语义
   ⇒ evaluate_basic_l1 输出的 change_class=C1 按原始字节保留
   ⇒ L1_local 只是外部标签，不是对冻结字段的静默替换

② 不得通过改名修复旁路
   ⇒ 正式科学 C1 必须由经验证的权威消费边界签发
   ⇒ 任何调用者不能仅凭局部返回 C1、或自造 AuthorityResult 取得资格

③ 不得擅自修改 prereg
   ⇒ 非规范性别名无需改 prereg，因此不触及 D2
   ⇒ 但若新规则改变 C1 的定义域/建立条件/结果语义/执行权限 ⇒ 实质规范变更
```

## 3.1 我上一版的越界，撤回

**v0.2 §5 我写：**

> ⇒ 改名要动 prereg 里 C1 这个词的定义域 ⇒ 需 prereg 授权。这一格我不裁，请凌翼裁。

**凌翼裁：`NB31_PREREG_DEFINITION_CHANGE = NOT AUTHORIZED`，「我不批准 Coder 所说的'需要修改 prereg 中 C1 定义域'这一步」。**

**⇒ 撤回。正确做法是：**

```text
✗ 改冻结定义来适应新设计
✓ 设计一个【尊重冻结定义】的外部权威消费层
```

## 3.2 准确映射表

| 冻结侧（不可改） | 外部标签（非规范） | 关系 |
|---|---|---|
| `evaluate_basic_l1(...).change_class = C1` | `L1_local = C1` | **同一字节，不同语境名称** |
| `evaluate_basic_l1(...).result = FAIL` | `L1_local = FAIL` | 同上 |
| `evaluate_basic_l1(...).result = UNRESOLVED` | `L1_local = UNRESOLVED` | 同上 |
| `evaluate_basic_l1(...).result = INVALID` | `L1_local = INVALID` | 同上 |
| —— | `C1`（正式科学输出） | **只由 AuthorityGate 签发** |

**⇒ 三条禁止：**

```text
禁 1  L1_local == C1 不得被读成"正式 C1 已建立"
禁 2  不得把 change_class 字段值替换成 L1_local（那是静默替换冻结字段）
禁 3  不得声明 L1_local ⟺ 正式 C1（那是把别名升级成等价）
```

---

# 4 · 表一（第二轮）· 权限与可验证性（凌翼：方向接受，边界未闭合）

**凌翼原文：**

> "另设目录、账户、提交渠道"本身还不能证明防旁路。
> AuthorityGate 不能靠名字取得权威，权限必须能够被独立验证。
> 须明确权限根、实际签发主体、独立身份验证、正式消费者约束，以及伪造结果、重放记录、替换对象、绕过权威门的负向测试设计。

## 4.1 五个待明确项

| # | 项 | 内容 | 状态 |
|---|---|---|---|
| **P-1** | **权限根** | 正式结果区的 DACL 所有者是谁？谁能修改？父目录权限与文件权限须分别登记 | NOT ESTABLISHED |
| **P-2** | **实际签发主体** | 谁运行 AuthorityGate？其 token/SID、完整性级别、是否 elevated | NOT ESTABLISHED |
| **P-3** | **独立身份验证** | 签发主体的身份证据从哪采集？（不能由 AuthorityResult 自报） | NOT ESTABLISHED |
| **P-4** | **正式消费者约束** | 哪些进程可读正式结果区？读取本身是否留痕？ | NOT ESTABLISHED |
| **P-5** | **权限可独立验证** | 一个第三方如何在不信任 AuthorityGate 的前提下复核权限 | NOT ESTABLISHED |

**⇒ 落为新挂起项 T-16 AUTHORITY_PERMISSION_ROOT = NOT ESTABLISHED。**

## 4.1b 表一全文 · 五角色消费边界（承接 v0.2 §1.1，本版重排）

**⇒ 原因：v0.3 若只列五个待明确项而不重排角色表，单独看 v0.3 的人无法审“边界长什么样”。**

| 角色 | 产出 | 是否可形成正式 C1 | 边界依据 |
|---|---|---|---|
| **校准消费者**（`smoke_evaluator.py` / `recompute_from_ledger.py` / `fixtures.py` / `evidence_bundle.py` 现有路径） | 局部 `L1Result`（含 `change_class=C1`） | **否** | `PHASE_A` / `SCIENTIFIC_CLAIM_ELIGIBILITY = "NONE"`（fixtures.py L50-51；suite L159-160） |
| **证据采集者**（observer） | BEFORE/AFTER 原始字节 + digest + 采集阶段身份 | 否 | 只读；不参与判别 |
| **权威裁决者**（`C1AuthorityGate`，拟建） | `AuthorityResult` | **拟为唯一** | 须经注册与独立登记（T-16/T-17 未建立） |
| **正式结果存储** | 正式 C1 结论 | 否（存储不生产） | 只接受受信入口写入 |
| **任意其他调用者** | 局部 `L1Result` | **否（无资格）** | 见 N-18/N-19 |

**⇒ 两张必须分开的校验（知微 §2 第 4 条）：**

```text
(a) 字节完整性（hash）—— 只证明未被篡改
(b) 生产者身份      —— 证明是谁产出的
⇒ (a) 成立不蕴含 (b)。两者必须分别检查。
```

## 4.2 T-17 · 签发主体身份验证（本版新增项的定义）

**凌翼要求「独立身份验证」。而 P-3 只写了"从哪采集"，没写这一项叫什么、什么时候做。**

```text
T-17 AUTHORITY_ISSUER_IDENTITY = NOT ESTABLISHED

它要回答四件：【谁】签发、其【身份证据来自哪里】、【谁有权认为该证据有效】、
             以及【该证据在什么时点被固定】。

⇒ 而与 P-3 的区别：P-3 是「采集点」，T-17 是「整条身份链是否成立」。
⇒ 二者不能合并，因为采集到了不等于验证了。
⇒ 具体实现归知微（Windows 身份验证可行性）。
```

## 4.3 我这一版**不能**说表一已闭合

```text
⇒ 我 v0.2 说"表一 · 权威消费边界（已设计）"
⇒ 凌翼判：方向接受，边界未闭合
⇒ 所以本版改为：表一有结构，但五个待明确项全部 NOT ESTABLISHED
⇒ 且我不声称"另设目录+账户+渠道"能防旁路
```

---

# 5 · 表二（第二轮）· 采集主体仍需实证（凌翼：接受为设计基础）

**凌翼「尤其不能在 AFTER 尚未发生时预先宣称已计算最终内容摘要」—— 这是我 v0.2 已改的，接受。**

## 5.0 表二全文 · 三类证据对象（承接 v0.2 §2.1，本版重排以便独立审阅）

**⇒ 原因同表三：v0.3 若只引用不重排，单独看 v0.3 的人会找不到"三类对象"指什么。**

| 对象 | 何时固定 | 包含什么 | 谁能写 | 何时禁写 |
|---|---|---|---|---|
| **① 注册计划** `ExecutionPlan` | 相关干预及结果暴露**之前** | execution/episode/arm、候选与 writer 身份、payload 来源规则、目标对象与通路、观察及判定规则 | 受信登记者 | 计划确认后立即禁写 |
| **② 执行事件与观察证据** `ObservationEvent` | 对应阶段实际发生时（**只追加**） | 计划引用、受信采集来源、进程与对象绑定、各 arm 的 BEFORE/AFTER 原始数据与摘要、实际通路事件 | observer 独立采集路径 | **只追加，不可修改** |
| **③ 最终封存包** `SealedEvidence` | 所需证据收齐后、权威裁决前 | 对计划和事件集合的绑定、完整性状态、**最终包摘要** | 封存者 | 封存后不可改 |

**⇒ 命名更正（v0.2 已改，本版保留）：**

```text
record_identity  = 事前分配的随机/确定性标识（不是内容摘要）
package_digest   = 最终封存包的内容摘要（事后才可计算）
⇒ 二者不是同一个东西，不得混用。
```

**⇒ digest 输入域三件事分开：**

```text
① STATE digest 输入域不变：sha256(literal + q_raw)，24 字节            ← 冻结约束
② META 可以包含 STATE digest（§7.2 L347 digest output = META_FIELD）  ← 合规
③ package_digest 的 canonical 输入须【排除它自身】或放在包外           ← 防自引用
```

## 5.1 三项验证设计（不执行）

```text
V-1  先后顺序验证
     设计：先登记计划并取得确认 → 才放行干预 → 才有事件追加 → 才封存
     验证：一个"事件早于计划"的执行必须被拒绝
     状态：NOT EXECUTED

V-2  封存完整性验证
     设计：封存后任何追加/修改必须被发现
     验证：封存后修改一个字节 ⇒ 拒绝
     状态：NOT EXECUTED

V-3  采集主体验证
     设计：ObserverEvent 的提交主体须独立于 writer
     验证：writer 账户提交事件 ⇒ 拒绝
     状态：NOT EXECUTED
```

---

# 6 · 表三（第二轮）· 判定表全文 + `h>=2` 的适用范围

**⇒ 先重排表三全文（承接 v0.2 §3.2，本版保留并可独立审阅）。**
**⇒ 原因：v0.2 有这张表，v0.3 若只引用不重排，单独看 v0.3 的人会找不到“第 7 行 / 第 11 行”具体指什么。**

## 6.0 表三全文 · 三轴分离判定表

| # | 情形 | 执行/证据有效性 | 局部测量结果 | 正式 class | 输出 |
|---|---|---|---|---|---|
| 1 | 已确认实际发生、与 claim 相关的**违规回流** | INVALID | —（保留原始记录） | 不建立 | `INVALID`，reason=`UNREGISTERED_EPISODE_REINJECTION` |
| 2 | 本次执行**缺失必须具备的**来源/通路核验证据 | INVALID | 保留（若有） | 不建立 | `INVALID`，reason=具体缺项名（**不写成“已观测到回流”**） |
| 3 | 必需规则 / witness / provenance broken | INVALID | 保留（若有） | 不建立 | `INVALID`（§13 L741） |
| 4 | 实际 writer ≠ 注册主体 | INVALID | 保留 | 不建立 | `INVALID`，reason=`WRITER_MISMATCH` |
| 5 | 对象在 BEGIN/END 之间被替换 | INVALID | 保留 | 不建立 | `INVALID`，reason=`OBJECT_IDENTITY_CHANGED` |
| 6 | 仅**设计阶段存在未验证风险** | — | — | 不建立 | **不签发任何结论**；不得冒充实际违规，也不得冒充已执行的科学 FAIL |
| 7 | 边界外读取，经独立审查**确无相关因果路径** | 有效 | 正常 | 照常 | `NEUTRAL_REVIEWED`，保存排除依据（睫 NB-33 第五行） |
| 8 | 通路已登记 + 事件合规 + **有**因果路径 | 有效 | 正常 | 按规则 | 可纳入证据；**不等于** C1 已建立 |
| 9 | 全部 required structure 有效且已执行，测量为负 | 有效 | **FAIL** | 不建立 | `FAIL`（此时才允许） |
| 10 | 同上，落入不确定区 | 有效 | **UNRESOLVED** | 不建立 | `UNRESOLVED` |
| 11 | 同上，h≥2 且 payload 匹配，且 1-8 全过 | 有效 | **PASS** | **待定，须按 §13 L718-724 优先级** | 若 C3 独立成立 ⇒ `C3`；否则若 C2 ⇒ `C2`；否则 ⇒ `C1`（R-1..R-9 全过才可） |

**⇒ 第 11 行的 `h>=2` 适用范围，见 §6.1。**

## 6.1 `h>=2` 的适用范围（凌翼特别指出）

**凌翼原文：**

> 须进一步确保第 11 行的 `h≥2` 是冻结 reference 实现下的具体判别规则，不能未经候选适配证明就成为所有真实系统 C1 的通用规则。

**⇒ 核字节，确认凌翼指的正是这一处：**

```text
evaluator.py L210-212  _literal_byte_diff_count(a, b):
                       if len(a) != LITERAL_SIZE or len(b) != LITERAL_SIZE:
                           raise HarnessError("literal must be exactly 16 bytes in L1 diff")
                       ⇒ 16 字节约束在这里，不在 L237
evaluator.py L237   h = _literal_byte_diff_count(snap_A.literal, snap_B.literal)
evaluator.py L239   if h == 0: FAIL
evaluator.py L246   if h == 1: UNRESOLVED
evaluator.py L253   # h >= 2 -> positive attribution/change
⇒ 而 h>=2 阈值本身在 L240-267
⇒ 这是 reference 的 16 字节规格下的具体规则
```

**⇒ 表三第 11 行的 `h>=2` 必须标注（见 §6.0 表内第 11 行）：**

```text
① 只在【候选已注册的判别实现】schema 与 reference 一致时，才可引用 h>=2 这个阈值。
② 若 P-1 摘要变长（T-2 / Q-3）⇒ h 的定义与阈值须由候选独立注册。
③ 不得把 h>=2 写成"所有真实系统 C1 的通用规则"。
```

---

# 7 · 表四（第二轮）· 后续读取与 C1 最小条件的分离（凌翼 §3 表四裁定）

**凌翼原文：**

> 实际后续读取可以成为真实记忆用途的重要证据，不能在未获规范授权时被自动提升为所有 pre-reset C1 的通用定义条件。应区分"注册存储写入已被证明"和"该记忆后来确实参与业务计算"。

**⇒ 这是对睫 Q-2 裁定的一个**收窄**，我必须准确记录，因为它和睫的裁定有张力：**

```text
睫（2026-10-27）：Q-2 是 claim 的定义性前提，须在 outcome 前回答，
                 证明方式必须是一次观测。
凌翼（2026-10-27）：不得把"实际后续读取"自动提升为所有 pre-reset C1 的通用定义条件。

⇒ 二者其实不冲突，分界在【范围】：
   · 对 P-1 这一个具体候选来说，若无人读取则写入无业务后果
     ⇒ 该候选的 claim 无法成立（睫，针对候选）
   · 但"后续读取"不得成为一个【所有 pre-reset C1 的通用门槛】
     ⇒ 因为冻结 §13 的 C1 规则里没有这一条（凌翼，针对通用性）
```

**⇒ 落为两个分开的项：**

```text
T-15a  P-1 候选内的读取通路存在性   = NOT ESTABLISHED（睫：须观测证明）
T-15b  读取通路是否作为 pre-reset C1 的通用条件 = NOT ESTABLISHED（须规范授权，凌翼）
⇒ 两者不同：前者是候选设计，后者是规范变更。
⇒ 我 v0.2 把二者混在一处（§4.4 写"属于 claim 的定义性前提"，
   未限定"仅对该候选"）。
```

## 7.0 表四全文 · P-1 最小具体绑定（承接 v0.2 §4.3，本版重排）

| 项 | P-1 中的形态 | 状态 |
|---|---|---|
| **实际 writer 角色** | 待定：摘要生成器 / 编码器 / 持久写入者是否同一进程。**不能默认等同**（知微 §4.1） | NOT ESTABLISHED（铰 T-1 / T-4） |
| **业务 STATE schema** | 若摘要变长 ⇒ 非 16+8；须独立登记 `STATE_FIELDS` / `LITERAL_STORAGE_COMPONENTS` / `IDENTITY_ONLY_COMPONENTS` | NOT ESTABLISHED（T-2） |
| **payload 来源规则** | 三选一：(a) 交互原文 / (b) 事前固定摘要 / (c) 前瞻规则产生的编码记录。**禁止在看到写入结果后反向选 payload** | NOT ESTABLISHED（T-14） |
| **真实判别接口** | 经该候选注册的判别实现；不复用旧函数的阈值（见 §6.1） | NOT ESTABLISHED |
| **context 读取证据职责** | 须绑定受信采集来源；`path_id` 不能代替实际读取证据（知微 §6.2） | NOT ESTABLISHED（T-15a） |

**⇒ 权威门消费声明（知微 §6.1，我接受）：**

```text
✗ 旧：正式 C1 必须以 evaluate_basic_l1 返回 C1 为必要条件
✓ 新：权威门消费的是【经该候选注册的判别实现的结果】。
      只有在证明 schema 与语义适用时，才可具体复用旧函数。
      参考校准成功不提供真实摘要的测量资格。
```

## 7.1 T-13 · 「有无因果路径」的判定（承接 v0.2，本版补定义）

```text
T-13 CAUSAL_PATH_ADJUDICATION = NOT ESTABLISHED

它要回答【三项】，缺一不可：
  ① 谁作出「有无因果路径」的判定？
     ⇒ 不得自动判（无可计算判据）
     ⇒ 须由【独立审查者】作出
  ② 判定须引用什么证据？
     ⇒ 具体到：哪条通路、哪个阶段、读了什么、送给了哪一臂
  ③ 判定记录如何保管？
     ⇒ 须封存进表二的 ③ SealedEvidence
     ⇒ 判定时刻须早于正式结果签发

⇒ 若不钉死这三项，「有无因果路径」会变成一个事后可调的旋钮。
⇒ 而它直接决定表三第 7 行（NEUTRAL）与第 1/2 行（INVALID）的分界。
⇒ 具体科学边界请睫审，实现归知微。
```

---

# 8 · 负向测试矩阵（凌翼 §4 要求）

**凌翼要求：必要条件、充分条件、invalidity 和 class priority 的负向测试矩阵。**

## 8.1 必要条件（R-1..R-9）逐项缺失测试

| # | 移除哪一项 | 期望输出 | 理由 |
|---|---|---|---|
| N-01 | R-1 规则/hash 无效 | `INVALID` | §13 L702 + L741 |
| N-02 | R-2 observer 不合法 | `INVALID` | §13 L703；§37 `STATE_OBSERVER_NOT_INDEPENDENT` |
| N-03 | R-3 两臂未实际执行 | `INVALID` | §13 L704；witness 缺失 |
| N-04 | R-4 D_ATTRIBUTION 未 ATTRIBUTED | 不得 `ESTABLISHED` | §13 L705-709 |
| N-05 | R-5 provenance 不完整 | `INVALID` | §13 L711；`PROVENANCE_BREAK` |
| N-06 | R-6 episode-specific write 未成立 | 不得 `ESTABLISHED` | §13 L722-724 |
| N-07 | R-7 writer ≠ 注册主体 | `INVALID` | 本设计新增 |
| N-08 | R-8 旧快照冒充本轮 after | `INVALID` | 本设计新增 |
| N-09 | R-9 通路未登记且已发生 | `INVALID` | 凌翼 §4；§37 `UNREGISTERED_EPISODE_REINJECTION` |

## 8.2 充分性反向测试（凌翼 Q1_REVERSE_SUFFICIENCY = NOT ESTABLISHED）

| # | 情形 | 期望输出 |
|---|---|---|
| N-10 | R-1..R-6 全部满足，但 R-7 未验证 | `NOT_ESTABLISHED`（不得 `ESTABLISHED`） |
| N-11 | R-1..R-6 全部满足，R-7..R-9 全过 | `ESTABLISHED` |
| N-12 | 同 N-11，但 C2 独立成立 | `reported_pre_reset_change_class = C2`（**不是 C1**） |
| N-13 | 同 N-11，但 C3 独立成立 | `reported_pre_reset_change_class = C3`（**不是 C1**） |

## 8.3 invalidity 不得被局部结果掩盖（凌翼 §3 表三裁定）

| # | 情形 | 期望输出 |
|---|---|---|
| N-14 | 局部结果 FAIL，但同期存在适用非法再注入 | `INVALID`，**不是** `FAIL` |
| N-15 | 局部结果 UNRESOLVED，但 provenance broken | `INVALID`，**不是** `UNRESOLVED` |
| N-16 | 局部结果 PASS+NOT_ESTABLISHED，但 writer 不匹配 | `INVALID` |
| N-17 | 边界外读取，独立审查确无因果路径 | `NEUTRAL_REVIEWED`（不判 INVALID，也不判成立） |

## 8.4 旁路与伪造测试（凌翼 §3 表一裁定）

| # | 情形 | 期望 |
|---|---|---|
| N-18 | 直接调用 `evaluate_basic_l1`，读到 `change_class=C1`，提交为正式结论 | 拒绝（无权威签发） |
| N-19 | 自行构造 `AuthorityResult`，字段全对、自算 hash 也对 | 拒绝（生产者身份不可证） |
| N-20 | 重放上一 execution 的有效 `AuthorityResult` | 拒绝（execution_id 与本轮不符） |
| N-21 | 替换证据包后重新封存 | 拒绝（plan 引用不符） |
| N-22 | 用改名把 `L1_local` 声明为 `C1` | 拒绝（NB-31 禁 3） |

**⇒ 全部 22 条：只列设计，未执行。**

---

# 9 · 状态（照录凌翼 §5，并补本版新增项）

```text
BF8_STATUS                        = OPEN
BF8_AUTHORITY_BOUNDARY           = NOT ESTABLISHED
BF9_EPISODE_SOURCE_BINDING       = NOT ESTABLISHED
NB31_NON_NORMATIVE_ALIAS         = CONDITIONALLY ACCEPTED
NB31_PREREG_CHANGE               = NOT AUTHORIZED
Q1_FULL_EQUIVALENCE              = NOT ESTABLISHED
Q1_ONE_WAY_NECESSITY             = APPROVED_FOR_DESIGN
Q1_REVERSE_SUFFICIENCY           = NOT ESTABLISHED
Q1_POST_RESET_SCOPE              = EXCLUDED
Q1_CLASS_PRIORITY_PRESERVATION   = REQUIRED

COND_6_EPISODE_SPECIFIC_BINDING  = NOT ESTABLISHED
REGISTERED_PATH_AUTO_C1          = NO（凌翼 2026-10-26）
UNREGISTERED_READ_AUTO_STOP      = NO（凌翼 2026-10-26）

T_1_W_SHAPE                      = PENDING_QIANXING
T_2_SUBSTRATE_SCHEMA             = NOT ESTABLISHED
T_4_WRITER_SINGULARITY           = PENDING_QIANXING
T_13_CAUSAL_PATH_ADJUDICATION    = NOT ESTABLISHED
T_14_P1_PAYLOAD_IDENTITY         = NOT ESTABLISHED
T_15a_P1_READ_PATH_EXISTENCE     = NOT ESTABLISHED（候选内，须观测）
T_15b_READ_PATH_AS_GENERAL_GATE  = NOT ESTABLISHED（须规范授权）  [本版拆开]
T_16_AUTHORITY_PERMISSION_ROOT   = NOT ESTABLISHED  [本版新增]
T_17_AUTHORITY_ISSUER_IDENTITY   = NOT ESTABLISHED  [本版新增]

C1_MEASUREMENT_CHAIN_QUALIFIED   = NOT ESTABLISHED
C1_SCIENTIFIC_RESULT             = NOT ASSESSED
FROZEN_Q3_RC11                   = UNCHANGED
CODE_CHANGE                      = NOT AUTHORIZED
SCIENTIFIC_EXECUTION             = MAY NOT START
```

---

# 10 · 本轮未做

- 未写代码、未运行模块
- 未改 `evaluator.py` / `fixtures.py` / prereg / MANIFEST
  （`fa644a9b…` / `ad0855b0…` / `78bdb90f…` 均未变，见 §11）
- 未修改 prereg 中 C1 的定义域（凌翼明确不批准）
- 未把 `L1_local` 声明为等价于正式 C1
- 未宣称表一闭合
- 未把 h>=2 写成通用规则
- 未把 22 条负向测试说成已执行

---

# 11 · 冻结件核验（本版结束时现算）

```text
MANIFEST   78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059
prereg     ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
evaluator  fa644a9bcfd59ffbbb415f0f439599eb705333600e7f8f8f0b93997ce6a59b5a
⇒ 三者均与登记值一致
```

---

# 12 · 这一轮我该记住的

凌翼驳回我时用的理由是「规范引用不准确」。

**⇒ 而我引用 §28.1 时，我看到的是：**
- 标题里有 "C1"
- §13 L723 里也写了 "§28.1 scope"

**⇒ 于是我以为它定义了 C1。**

**⇒ 而它定义的是 C1 的"最小 mandatory failure path"——一个对照，不是一个成立规则。**

**⇒ 这是 E-4（§5 vs §4）的完全同形：**

```text
E-4  L169-171 有 write_operator ⇒ 我以为是 §5，实为 §4
E-9  §28.1 标题有 C1、被 §13 引用 ⇒ 我以为它定义 C1，实为 witness
```

**⇒ 两次，我都被"这一处提到了它"，骗成了"这一处定义了它"。**

**⇒ 所以我这一版加了表五（章节职责映射）。**
**⇒ 而它的用处不是我写给自己看的——是让下一个读我文件的人，**
**⇒ 能一眼看出我引的那一节，到底定义了什么。**

**⇒ 我不写"引用已全部核准"。**
**⇒ 我写：表五这张映射表，请你替我核**——**因为我自己已经被骗过两次。**
