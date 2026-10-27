# C1 STRUCTURAL CLOSURE DESIGN v0.3 · 章节映射更正 + 必要条件 + 负向测试矩阵

**性质**：非冻结、文档级设计修订。不构成代码或科学执行授权。
**依据**：`凌翼裁定 · C1 Structural Closure v0.2`（2026-10-27）
**被审对象**：v0.2，`e3e285fc6dc8b03e68cae27631dd7f77aa4a4078`，SHA-256 `ed325ff90a827d8fd603e3ce1301bdbd414178d303dc26983353f2355d1c2961`
**日期**：2026-10-27

## 标题页 · 本文覆盖凌翼 §4 批准的五项交付

**凌翼 v0.2 裁定 §4 批准的改进项，逐项对应如下：**

| # | 凌翼要求的交付 | 本文对应节 | 状态 |
|---|---|---|---|
| 1 | `L1_local` 与原始字段、正式科学输出的准确映射 | **§3** | 已给映射表 + 三条禁令 |
| 2 | 表一权限与权威消费边界的**可验证性** | **§4**（含 §4.1b 五角色表、P-1..P-5 五项待明确） | **只到"待明确"，未验证** |
| 3 | AuthorityGate 与冻结 prereg §12、§13、§28.1 及适用条款的**完整规则映射** | **§1**（章节级 + 规则级 G-1..G-21 + X-1..X-4）、**§2**（三层必要条件） | 已给；**"完整"待睫核** |
| 4 | 必要条件、充分条件、invalidity 和 class priority 的**负向测试矩阵** | **§8**（23 条，按三层重排） | 已给设计；**未执行** |
| 5 | P-1 后续读取证据与 C1 最小科学条件的**明确分离** | **§7.1** | 已给七行对照表 |

**⇒ 标题页列这段的原因：**
```text
原标题只写了"章节映射更正 + 必要条件 + 负向测试矩阵"三项
⇒ 漏了第 2 项（权限边界）和第 5 项（P-1 分离）
⇒ 读者会以为本文只覆盖三项
⇒ 而漏的那两项恰恰是凌翼判定"边界未闭合"的地方
```

**⇒ 第 2 项我必须标清：本文只做到"列出五项待明确"，没有做到"可验证"。**
**⇒ 这正是凌翼原文「表一：方向接受，边界未闭合」的意思，我不把它写成"已完成"。**

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

# 1 · 表五 · 章节职责映射（凌翼 §2 要求）

| 章节 | 行 | 它定义什么 | 在 AuthorityGate 中的角色 |
|---|---|---|---|
| **§12** | L629-649 | C1 的**科学含义**与**最强允许 claim**（`REGISTERED_STORAGE_WRITE_OBSERVED`） | 决定"成立之后能说什么"，不是"是否成立" |
| **§13** 五项 gate | L700-711 | 正向 pre-reset class 的**共同入口** | **必要条件集合**（全部须满足） |
| **§13** class 选择 | L715-725 | C3 → C2 → C1 的**优先级** | **优先于** AuthorityGate 的 C1 结论 |
| **§28.1** | L1711-1741 | C1 的 **mandatory failure witness**（两臂对照） | 必要条件中的**一项** |
| **§24** | L1379-1556 | **post-reset** class 规则（含 24.3 Post-reset C1，L1528-1536） | **超出 pre-reset AuthorityGate 范围**（不是"无 post-reset C1"，是"由 §24 独立定义"） |
| **§37** | L2203-2261 | stop conditions（L2207 为代码块起始围栏，L2208-2261 为 39 条条款行） | 任一命中 ⇒ 不建立 |

**⇒ 关键：`§28.1` 是 §13 class 选择里的一个**限定词**（L723 "under the Basic L1 / §28.1 scope"），不是独立成立条件。**

## 1.1 表五之二 · 规则级映射（凌翼 §4 要求）

**上面那张表是【章节级】，回答"每一章讲什么"。**
**而凌翼 §4 要求的是"AuthorityGate 与冻结 prereg §12、§13、§28.1 及适用条款之间的完整规则映射"——那是【规则级】。**

**⇒ 本章补上。规则级 = AuthorityGate 的每一个判定点，对应到哪一条款、哪一句、什么判定。**
**⇒ 而章节级那不张表不删，因为两者回答不同的问题。**

| # | AuthorityGate 判定点 | 冻结条款（精确） | 条款原文（节录） | 判定性质 |
|---|---|---|---|---|
| **G-1** | 规则/hash 有效性 | §13 L702 | "本次 execution 与该 claim scope 所需 manifests / frozen rules 均有效" | 必要条件 |
| **G-2** | observer 合法性 + before/after 已完成 | §13 L703 → §11 L604-625 | L703："§11 Independent State Observer 合法，并完成 registered before / after observation"；§11 L606："before / after state 必须由独立于 W 的 observer 采集"；L619-625 四条 + "W 不能认证自己已经改变 state" | 必要条件 |
| **G-3** | 两臂已实际执行 | §13 L704 | "§28.1 preregistered TARGET WRITE ARM vs NO-WRITE / MATCHED BASELINE CONTROL 已实际执行" | 必要条件 |
| **G-4** | D_ATTRIBUTION 给出 ATTRIBUTED | §13 L705 + L708 | L705："frozen D_ATTRIBUTION 在该 §28.1 scope 的 canonical ΔS_identity_masked 上给出 Basic-L1/C1-scope"；L708（代码块内）："attribution_result = ATTRIBUTED"（L707/L709 为围栏） | 必要条件 |
| **G-5** | provenance 完整 + 无命中 stop condition | §13 L711 | "required provenance 完整，且没有命中与该 attempted claim 相关的 §37 invalidity / stop condition" | 必要条件 |
| **G-6** | episode-specific write 成立 | §13 L722-724 | "else if an episode-specific registered storage write is established in preregistered LITERAL_STORAGE_COMPONENTS under the Basic L1 / §28.1 scope: PRE_RESET_CHANGE_CLASS = C1" | 必要条件 |
| **G-7** | 两臂 witness 形态合格 | §28.1 L1716-1718 | 代码块内三行（L1715/L1719 为围栏）："TARGET WRITE ARM" / "vs" / "NO-WRITE / MATCHED BASELINE CONTROL" | G-3 的具体形态约束 |
| **G-8** | witness 回答的问题 | §28.1 L1721-1723 | "attributable registered write/change 是否真的发生？" | G-3/G-6 的语义锚点 |
| **G-9** | C1 不要求 C2/C3 结构 | §28.1 L1727-1731 + L1741 | L1727："它不要求："；L1730-1731：same-E ON/OFF nonstorage counterfactual / content-class contrast；L1741："仍可合法尝试并建立 C1" | 排除性规定 |
| **G-10** | class 优先级（**非 AuthorityGate 判定，是 AuthorityGate 必须让位的机制**） | §13 L718-724（L717/L725 为围栏） | 代码块内 else-if 链：L718-719 C3；L720-721 C2；L722-724 C1 | **让位类**：AuthorityGate 不执行此链，只输出 C1 要素 |
| **G-11** | gate PASS ≠ class 成立 | §13 L727 | "因此 Basic L1 PASS 本身不得被引用为 C1/C2/C3；PRE_RESET_CHANGE_CLASS 必须来自对应 class rule" | **禁止性规定** |
| **G-12** | invalidity 不得写成 FAIL | §13 L741 | "不得把 protocol/execution invalidity 写成 L1 = FAIL" | **禁止性规定** |
| **G-13** | C1 的科学含义 | §12 L633-637 | "C1 表示：storage write 是目前最高被正向建立的 change class" | 语义定义 |
| **G-14** | 最强允许 claim | §12 L643-646 | "REGISTERED_STORAGE_WRITE_OBSERVED" | 输出上限 |
| **G-15** | C1 是证据断言 | §12 L649 | "因此 C1 是证据断言，不是世界断言" | 语义边界 |
| **G-16** | META 不进 STATE digest | §7.2 L326 + L346-347 + L350 | L326："不得进入 substrate state digest"；L346-347（代码块内，L345/L348 为围栏）："digest input = STATE_FIELDS only" / "digest output = META_FIELD"；L350："digest 输出不得回灌进自己的输入" | **硬约束** |
| **G-17** | post-reset C1 的独立定义（pre-reset 权威门不得代替它） | §24 L1379-1556，其中 post-reset C1 在 L1528-1536（**24.3 Post-reset C1**，L1533 `POST_RESET_SUPPORTED_CLASS = C1`） | §24 定义的是 **post-reset** 的 class 规则本身（含 L1415-1417 "C1 persistence scope"、L1528-1536 "Post-reset C1"）；**不是"不涉及 C1"** | **范围隔离**：本文 AuthorityGate 只覆盖 pre-reset，不得代替 §24 的 post-reset 判定 |
| **G-18** | stop condition 清单 | §37 L2208-2261 | 39 条（逐行计数，无空行） | 触发即 INVALID |

**⇒ 而 AuthorityGate 还有三项【本设计新增、无冻结条款对应】的判定点：**

| # | 判定点 | 对应条款 | 性质 |
|---|---|---|---|
| **G-19** | writer—execution—observation 关联（R-7） | **部分对应 §4 L169-171**（不是"无"） | §4 已冻结 writer 三字段；缺的是"实际执行主体核对机制"（§31 无 write_operator）。**这才是 BF-8 的真身** |
| **G-20** | execution 来源绑定（R-8） | **§31 L1948-1949**（不是"无"） | execution_id / execution_hash 属 provenance 必备 ⇒ 归入 gate 5 具体化 |
| **G-21** | 通路登记（R-9） | 部分对应 §37 L2253-2254 | 部分新增 |

**⇒ 而 G-10（class 优先级）实际依赖的 C2/C3 独立性判据：**

> ⚠️ **以下四项【不是 AuthorityGate 的判定点】。**
> AuthorityGate 只判 C1 要素是否成立（见 §2 开头的三层划分）。C2/C3 是否独立成立，由 §16 / §19-20 各自的规则判定，**不归 AuthorityGate**。
> 保留这张表，是因为它说明"最终 class 可能不是 C1"，而 AuthorityGate 的消费者必须知道这一点。

| # | class selection 机制的输入条件（**非 AuthorityGate 判定点**） | 冻结条款（精确） | 条款原文（节录） | 对 AuthorityGate 的意义 |
|---|---|---|---|---|
| **X-1** | C2 是否「独立成立」 | §16 L944-960 | L948-956："只有当 C2 所要求的 paired evidence 已实际执行，并且对应 ledger entries 满足：registered ON/OFF treatment contrast established AND D_NONSTORAGE_BASELINE_ROLE_HASH = <the frozen registered role hash> AND attribution_result = ATTRIBUTED"；L960："才可建立 C2" | AuthorityGate **不判**；但须声明"我未判定 C2" |
| **X-2** | C2 的 ATTRIBUTED 不得借用 C1 的 | §16 L958 | "Basic L1 / C1 scope 的 D_ATTRIBUTION result 不得满足这一 conjunct" | **硬约束**：AuthorityGate 输出的 ATTRIBUTED 不得被用于满足 C2 |
| **X-3** | C3 是否「独立成立」 | §19 L1081-1090 | L1081："Every C3 Member Must Be Individually Attributed"；L1086："FOR EVERY e IN CONTENT_CLASS_EVIDENCE_SET" | AuthorityGate **不判** |
| **X-4** | C3 的比较对象 | §20 L1136-1142 | L1138："C3 的 canonical comparison object 是"；L1141："T_CONTRAST_RESULT(E)" | AuthorityGate **不判** |

**⇒ 为什么仍需保留这四项：**

```text
⇒ §13 L718-724 的 class selection 说"若 C3 独立成立则报 C3，否则若 C2 则报 C2，否则 C1"
⇒ 但"独立成立"不是自明的 —— 它由 §16 / §19-20 各自的规则定义
⇒ 若不映射 §16 / §19-20，"class 优先级"这句话就是空的
⇒ 而 X-2 尤其关键：C1 的 ATTRIBUTED 不得借用去满足 C2
   ⇒ 这正是"gate PASS ≠ class 成立"（G-11）在 C2 侧的具体形态
⇒ 而 AuthorityGate 的正确姿态是：
   · 只输出 C1 要素是否成立
   · 明确声明"未判定 C2/C3"
   · 不得输出最终 PRE_RESET_CHANGE_CLASS
```

**⇒ 这三项是"AuthorityGate ≠ prereg C1"的具体所在。**
**⇒ 其中只有 G-19（writer 核对机制）与 G-21（通路登记机制）真正超出 prereg；G-20 在 prereg §31 L1948-1949 已有要求。**
**⇒ 因此 `ESTABLISHED` 蕴含 prereg C1，但 prereg C1 不蕴含 `ESTABLISHED`（见 §2.1）。**
**⇒ 本章仍是【设计】，未执行、未验证。规则映射的准确性请睫核。**

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
  R-4  §13 L705 + L708  frozen D_ATTRIBUTION 在 canonical ΔS_identity_masked
                       上给出 ATTRIBUTED（L707/L709 为围栏）
  R-5  §13 L711  required provenance 完整，且无命中与本次 claim 相关的 §37 invalidity / stop condition
  R-6  §13 L722-724  episode-specific registered storage write 在 preregistered
                     LITERAL_STORAGE_COMPONENTS 上成立（L717/L725 为围栏）
  R-7  BF-8 的 writer—execution—observation 关联成立
       ⇒ 【部分新增】：§4 L169-171 已冻结 writer 三字段，但无核对机制（§31 无 write_operator）
  R-8  BF-9 的 execution 来源绑定成立
       ⇒ 【不是新增】：§31 L1948-1949 已要求 execution_id/execution_hash 为 provenance 必备
          ⇒ 属 gate 5（R-5）的具体化
  R-9  NB-29 通路登记成立
       ⇒ 【部分新增】：§37 L2253-2254 已禁"未登记"，但登记机制未定义
  R-10 C1 的 ATTRIBUTED 未被借用去满足 C2 conjunct（§16 L958 明文禁止）
```

## 2.1 反向蕴含不成立（凌翼裁 Q1_REVERSE_SUFFICIENCY = NOT ESTABLISHED）

```text
⇒ prereg §13 全部满足，不自动意味着 AuthorityGate 会输出 ESTABLISHED
   ⇒ 真正超出 prereg 的只有：R-7 的【核对机制】与 R-9 的【登记机制定义】
   ⇒ R-8 不超出（属 gate 5 具体化）
   ⇒ 而 prereg 满足仍不意味着 AuthorityGate 会输出 ESTABLISHED，
     因为 R-7 / R-9 的机制尚未存在
⇒ 也不意味着 AuthorityGate 不误判：
   漏判（该建立的没建立）、误判（不该建立的建立了）、
   越权签发、非法消费 —— 四条路径都未验证。
```

## 2.2 class 优先级必须保留（凌翼 Q1_CLASS_PRIORITY_PRESERVATION = REQUIRED）

**凌翼原文：**

> "注册存储写入这一证据要素成立" 与 "最终报告的最高 pre-reset change class 为 C1" 并非总是同一件事。若 C2 或 C3 独立成立，§13 的 class selection 会报告更高类别。不得让 AuthorityGate 覆盖这条优先级规则。

**⇒ 落为硬约束：**

> ⚠️ **【本代码块已作废：它把 class selection 塞进了 AuthorityResult】
> 下方 `reported_pre_reset_change_class` 字段的设计是错的——它把 §13 的 class 选择职责塞给了 AuthorityGate。
> **当前有效版本见 §2.2c。**

```text
（作废）AuthorityResult 必须携带两个不同字段：
  · episode_specific_write_established  = BOOL（R-6 是否成立）
  · reported_pre_reset_change_class     = C1 / C2 / C3（按 §13 L715-725 优先级）

⇒ 禁止把前者当作后者。
⇒ 若 C2 或 C3 独立成立 ⇒ 后者必须是 C2/C3，即使 C1 要素成立。
⇒ 这一条我 v0.2 完全没写。
```

## 2.2c AuthorityResult 的完整取值集合

**⇒ 全文只定义了 `ESTABLISHED`，此前从未说"不成立"时返回什么。**
**⇒ 而 `INVALID` 在文中出现 30 次，没有任何一处说明它属于 `AuthorityResult`。**
**⇒ 这是一处真实的定义缺口，不是措辞问题。**

**⇒ 补全为四值（对齐 §13 L729-741 的三种否定形态 + 证据缺失）：**

| 值 | 含义 | 何时产生 | 权威条款 |
|---|---|---|---|
| `ESTABLISHED` | C1 要素成立 | R-1..R-10 全过 | §13 L722-724 |
| `NOT_ESTABLISHED` | C1 要素未成立（结构有效、无违规） | R-6 不成立；或其他 gate 通过但 C1 专属判据不满足 | §13 L722-724 |
| `INVALID` | 本次执行/证据无效（**不是科学负结果**） | R-1/R-2/R-3/R-5/R-7/R-8/R-9 任一失败；或命中 §37 | §13 L741 |
| `FAIL` / `UNRESOLVED` | **科学** 确定负结果 / 不确定区 | 仅当 required structure 有效且已执行时 | §13 L729-732 / L735-738 |

**⇒ 而这四个值必须与表三的十一行一一对齐：**

```text
表三第 1-5 行  → AuthorityResult = INVALID
表三第 6 行    → 不签发（无 AuthorityResult）
表三第 7 行    → NEUTRAL_REVIEWED（不是 AuthorityResult 的四个值之一，是独立标记）
表三第 8 行    → 不产生 ESTABLISHED（只是"可纳入证据"）
表三第 9 行    → AuthorityResult = FAIL
表三第 10 行   → AuthorityResult = UNRESOLVED
表三第 11 行   → AuthorityResult = ESTABLISHED（若 R-1..R-10 全过）
```

**⇒ 两处仍不一致，我必须指出而不假装解决：**

```text
① 表三第 7 行 NEUTRAL_REVIEWED 不在四值里
   ⇒ 我倾向它不属于 AuthorityResult，而是独立的审查记录标记
   ⇒ 但这一点须睫确认
② 表三第 8 行"可纳入证据"到底对应哪个值？
   ⇒ 它可能不对应任何 AuthorityResult 值，只是"这一个证据项被接受"
   ⇒ 也可能是 NOT_ESTABLISHED（因为 C1 未建立）
   ⇒ 须睫确认
⇒ 落为 T-19 AUTHORITY_RESULT_ENUM_COMPLETENESS = NOT ESTABLISHED
```

**⇒ 一条附注：**

> **我定义了"成功"的形态，却从没定义"失败"的形态。**
> **而一个只有成功分支的接口，无法被实现。**

**⇒ 于是 G-10a..G-10d 的定位也要改：**

```text
✗ 它们不是 AuthorityGate 的判定点
✓ 它们是【class selection 机制】的输入条件，AuthorityGate 需要知道它们存在、且不由自己判定

⇒ 保留它们的映射价值（说明 C1 不是最终 class 的唯一可能）
⇒ 但不再写成 AuthorityGate 的 G-10x 判定点
```

## 2.3 post-reset 排除（凌翼 Q1_POST_RESET_SCOPE = EXCLUDED）

```text
⇒ 本文的 AuthorityGate 只覆盖 pre-reset C1 claim。
⇒ post-reset C1 由 §24（L1379-1556）的规则决定，不得由本文的 AuthorityGate 自动覆盖。
⇒ 也不得扩展成 Memory Qualification。
```

## 2.4 BF-8 的旁路结论为什么是"结构性不可能"（睫 NB-30）

**v0.3 上一稿把这一段弄丢了，只在状态表留了一行孤立的子项。补回。**

```text
evaluate_basic_l1 是【可 import 的公开函数】。

调用点 = 11 处（可枚举）：
  evidence_bundle.py        L519
  fixtures.py               L252 / L299 / L399
  recompute_from_ledger.py  L86 / L106
  smoke_evaluator.py        L63 / L70 / L74 / L79 / L86

import 行 = 4 处（这才是关键）：
  evidence_bundle.py        L56
  fixtures.py               L30
  recompute_from_ledger.py  L95
  smoke_evaluator.py        L34

⇒ 11 个调用点可枚举，而"将来谁再 import 一次"不可枚举。
⇒ 所以在【不动 evaluator.py】的前提下，函数层旁路封闭是【结构性不可能】，
  不是"我暂时还没证明"。

⇒ 两条结论必须分开（凌翼 v0.2 裁定 §2）：
   函数层旁路（谁能调用 evaluate_basic_l1）
     = 不动 evaluator.py 则结构性不可封闭
   正式 C1 旁路（谁能签发正式 C1）
     = 可以封闭，封点在【正式消费边界 + 合同层命名】（见 §4.1b / §3）
```

## 2.4a 术语对照表（正式 C1 / C1 要素 / 最终 class）

**⇒ 全文曾出现三个近义词：正式 C1 / C1 要素 / 最终 class，然从未给出对照。**
**⇒ 三者不是同一个东西，但我从未给出对照。读者会误以为它们同义。**

| 本文用词 | 精确定义 | 由谁产生 | 与 §13 的关系 |
|---|---|---|---|
| **`L1_local`** | `evaluate_basic_l1` 返回的局部计算结果（含 `change_class=C1`） | reference 函数 | 非规范别名（凌翼 NB-31） |
| **C1 要素成立** | `episode-specific registered storage write` 这一条独立判据成立 | AuthorityGate | §13 L722-724 的 C1 分支 |
| **「正式 C1」** | 承凌翼/知微措辞：经权威消费边界签发、可作为科学输出的 C1 判定结果 | AuthorityGate（唯一） | = C1 要素成立 + R-1..R-10 全过 |
| **`PRE_RESET_CHANGE_CLASS = C1`** | §13 的 **class selection 结果** | §13 L715-725 机制 | **不是 AuthorityGate 输出** |

**⇒ 关键区分（必须记住）：**

```text
「正式 C1」       = C1 要素成立（AuthorityGate 的输出）
「最终 class = C1」= §13 机制赋值的结果
⇒ 二者在【C2/C3 都不成立】时才重合
⇒ 若 C2/C3 独立成立，则「正式 C1」可能仍为真，而「最终 class」是 C2/C3
```

**⇒ 所以本文用「正式 C1」时，指的都是** AuthorityGate 的输出 **，不是最终报告类别。**
**⇒ 若发现任何一处用法与之不符，那一处是错的。**

## 2.4b `__all__` 存在，但管不到顶层绝对导入路径

**⇒ 须说明 `afterglow_harness/__init__.py` 里的 `__all__` 是否削弱上面的论证。**

```text
afterglow_harness/__init__.py（209 字节）：
  __all__ = [
      "harness_constants", "storage", "readers",
      "writers", "observer", "perturbation_j",
  ]
  ⇒ 六项，【不含 evaluator】
```

**⇒ 这说明两件事，方向相反：**

```text
① 包层确实做了导出白名单 —— 说明作者有意识地限制对外暴露
② 但 evaluator 不在白名单里，而四个调用方用的是【绝对导入】：
   from evaluator import (...)        （evidence_bundle / fixtures / smoke_evaluator）
   import evaluator as ev             （recompute_from_ledger）
   ⇒ 都是 import 顶层模块名，不是 from afterglow_harness import evaluator
   ⇒ 所以 __all__ 对这条路径【完全无效】
```

**⇒ 结论不变，但理由必须写准：**

```text
✗ 不完全的说法：evaluator 是公开函数，谁都能 import
✓ 准确的说法：
   · 包层有 __all__ 白名单（说明作者想过这件事）
   · 但白名单不包含 evaluator
   · 且实际调用方走的是顶层绝对导入，绕过了白名单
   · ⇒ 在【不改任何现有文件】的前提下，新增调用者只需写一行
        from evaluator import evaluate_basic_l1
     即可，无任何机制阻止
   ⇒ 这是"不可枚举"的具体机制，而不仅仅是一个断言
```

**⇒ 并且这把 §4.1b 的消费边界要求变得更具体：**

```text
⇒ 若将来要把 evaluator 纳入白名单管理，须改 __init__.py
   ⇒ 而 __init__.py 是否在执行关键角色表里？须核（本轮未核，列为待查）
⇒ T-18 MODULE_EXPORT_CONTROL = NOT ESTABLISHED
```

### 2.4c `__init__.py` 不在冻结角色表内

**⇒ 核验结果：**

```text
MANIFEST         grep "__init__"          → 零命中                    [终端核验]
role_registry    grep "__init__"          → 零命中                    [终端核验]
manifest_bind    COMPONENT_FILES（L85-107）→ 22 项，无 __init__.py     [读文件]
                  其中含：harness_constants / storage / writers / readers /
                  observer / perturbation_j / reset / evaluator / fixtures /
                  fixture_contracts / evidence_bundle / qualification_role_registry /
                  qualification_binding / run_known_answer_suite / qualify_phase_a /
                  verify_manifest_binding / adversarial_regression /
                  recompute_from_ledger ＋ BUILD_PROVENANCE 两项
```

**⇒ 结论：**

```text
① __init__.py 存在，且有 __all__ 白名单（六项）
② 但 __init__.py 本身【不在冻结角色表】，也不在 COMPONENT_FILES
③ ⇒ 它不在任何冻结 hash 底下 ⇒ 可以改它，而不改变任何已登记 hash
④ ⇒ 也就是说：包层的"导出控制"是一个可以被静默修改的表面
```

**⇒ 这独立于 BF-8 的一格：**

```text
T-18 MODULE_EXPORT_CONTROL = NOT ESTABLISHED
  ├ __all__ 存在                  = YES
  ├ __all__ 含 evaluator          = NO
  ├ __init__.py 是否冻结          = NO（不在 role_registry / COMPONENT_FILES / MANIFEST）
  ├ 实际调用方是否走白名单         = NO（走顶层绝对导入）
  └ 结论：导出控制层既不被使用，也不被冻结。
          它看起来像一道门，但不锁，也不记账。
```

**⇒ 我不判定这是不是缺陷。** 它可能是有意的（`__init__.py` 只是包标记）。
**⇒ 但它必须被记录**，因为将来若有人用"我们有 `__all__` 控制导出"来论证旁路已封闭，这句话是不成立的。
**⇒ 请知微核："`__init__.py` 不在冻结表内"是有意设计还是遗漏。**

## 2.5 post-reset 扩展到 Memory Qualification 的排除

```text
⇒ AuthorityGate 的 ESTABLISHED 不构成 Memory Qualification。
⇒ 也不构成 post-reset C1（§24 独立规则）。
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

# 4 · 表一 · 权限与可验证性（凌翼：方向接受，边界未闭合）

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
| **正式结果存储** | AuthorityGate 的 C1 要素判定结果（**不是最终 `PRE_RESET_CHANGE_CLASS`**；后者由 §13 L715-725 机制写入） | 否（存储不生产） | 只接受受信入口写入 |
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

# 5 · 表二 · 采集主体仍需实证（凌翼：接受为设计基础）

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

# 6 · 表三 · 判定表全文 + `h>=2` 的适用范围

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
| 11 | 同上，h≥2 且 payload 匹配，且 1-8 全过 | 有效 | **PASS** | **C1 要素成立（不等于最终 class = C1）** | AuthorityGate 输出 `ESTABLISHED` = C1 要素成立；**最终 `PRE_RESET_CHANGE_CLASS` 由 §13 L715-725 机制另行赋值**（可能因 C2/C3 独立成立而取更高类别） |

**⇒ 第 11 行的 `h>=2` 适用范围，见 §6.1。**
**⇒ 第 11 行「正式 class」列：** AuthorityGate 只判 C1 要素，不判最终 class（见 §2 开头的三层划分）。

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

# 7 · 表四 · 后续读取与 C1 最小条件的分离（凌翼 §3 表四裁定）

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

## 7.0 表四全文 · P-1 最小具体绑定（本版重排）

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

## 7.1 P-1 后续读取证据 vs C1 最小科学条件的明确分离（凌翼 §4 要求）

**⇒ 凌翼 §4 要求「P-1 后续读取证据与 C1 最小科学条件的明确分离」，而本文此前只有零散的 T-15a/T-15b，没有一张明确的分离表。**

| 项 | "注册存储写入已被证明"（C1 最小条件） | "该记忆后来确实参与业务计算"（后续读取证据） |
|---|---|---|
| **证据内容** | 本次 episode 的 registered write 确实发生且可归属 | 后续某个 episode 实际读取了该记录 |
| **归属条款** | prereg §13 L700-724（五项 gate + class rule） | **无冻结条款**（§13 C1 规则里没有这一条） |
| **是否 C1 成立的必要条件** | **是** | **否**（凌翼 2026-10-27 明文：不得自动提升为所有 pre-reset C1 的通用定义条件） |
| **是否 P-1 候选的 claim 必要前提** | 是 | **是**（睫 2026-10-27：属 claim 定义性前提，须在 outcome 前回答） |
| **证明方式** | 按 gate + class rule 判定 | **须一次真实观测**，不是设计论证（睫） |
| **未满足时的后果** | C1 不建立 | P-1 的 claim 不成立；**但不得据此把通用 C1 判为不成立** |
| **本书编号** | R-1..R-6（C1 自身）+ R-10（不得借用给 C2） | T-15a（存在性）/ T-15b（是否通用门槛） |

**⇒ 这一格最容易被两个方向的误用：**

```text
误用 A  把"后续读取"当成 C1 的通用必要条件
        ⇒ 凌翼已禁（会扩大 prereg §13 的规则）
误用 B  因为"后续读取"不是 C1 通用条件，就在 P-1 里也不要求它
        ⇒ 睫已禁（那样 P-1 的写入即使成立，也不证明记忆被用上）
```

**⇒ 正确关系：**

```text
C1（通用）     ─ 不需要后续读取
P-1 的 claim   ─ 需要后续读取（但这是【候选语义】，不是【C1 规则】）
```

## 7.2 T-13 · 「有无因果路径」的判定（承接 v0.2，本版补定义）

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

## 8.1 必要条件逐项缺失测试

**⇒ 本表把 R-1..R-10 按三层分开，以区分"gate 失败"与"C1 不成立"。**
**⇒ 现按 §2 开头的三层分开，并明确各自的期望输出。**

### 8.1a 第一层 · Basic L1 gate（共享，C1/C2/C3 都要过）

| # | 移除哪一项 | 期望输出 | 理由 | 关键区别 |
|---|---|---|---|---|
| N-01 | R-1 规则/hash 无效 | `INVALID` | §13 L702 + L741 | **不是** C1 不成立，是**执行无效** |
| N-02 | R-2 observer 不合法 | `INVALID` | §13 L703；§37 `STATE_OBSERVER_NOT_INDEPENDENT` | 同上 |
| N-03 | R-3 两臂未实际执行 | `INVALID` | §13 L704；witness 缺失 | 同上 |
| N-04 | R-4 D_ATTRIBUTION 未 ATTRIBUTED | **分两种，不能统一**：<br>① 结构有效且已执行，attribution 给出**确定负结果** ⇒ `L1 = FAIL`（L729-732）<br>② 结果落入 indeterminate region ⇒ `L1 = UNRESOLVED`（L735-738）<br>③ rule 缺失 / outcome 后改变 ⇒ **INVALID**（L741） | §13 L705 + L708 + L729-741 | 三种情况不可混为一谈 |
| N-05 | R-5 provenance 不完整 | `INVALID` | §13 L711；`PROVENANCE_BREAK` | 同上 |

### 8.1b 第二层 · C1 class rule（C1 专属）

| # | 移除哪一项 | 期望输出 | 理由 | 关键区别 |
|---|---|---|---|---|
| N-06 | R-6 episode-specific write 未成立 | 不得 `ESTABLISHED`（AuthorityGate 不签发 C1 要素） | §13 L722-724（L717/L725 为围栏） | **gate 可能全过，只是 C1 的专属判据没成立** ⇒ 此时可能 C2/C3 成立 |

### 8.1c 第三层 · 本设计新增（比 prereg 更严格）

| # | 移除哪一项 | 期望输出 | 理由 |
|---|---|---|---|
| N-07 | R-7 writer ≠ 注册主体 | `INVALID` | 本设计新增 |
| N-08 | R-8 旧快照冒充本轮 after | `INVALID` | 本设计新增 |
| N-09 | R-9 通路未登记且已发生 | `INVALID` | 凌翼 §4；§37 `UNREGISTERED_EPISODE_REINJECTION` |

### 8.1d 约束项 · 不得借用（跨层）

| # | 情形 | 期望输出 | 理由 |
|---|---|---|---|
| N-09a | R-10 C1 的 ATTRIBUTED 被借用去满足 C2 conjunct | C2 **不得**因此建立 | §16 L958："Basic L1 / C1 scope 的 D_ATTRIBUTION result 不得满足这一 conjunct" |

**⇒ 三层分开之后，有一条以前看不出来的区别现在显出来了：**

```text
第一层失败（N-01..N-05）⇒ INVALID ⇒ 整次执行无效，连 class 都到不了
第二层失败（N-06）      ⇒ 只是 C1 要素未建立 ⇒ 若 C2/C3 独立成立，报告 C2/C3
第三层失败（N-07..N-09）⇒ 按本设计判 INVALID ⇒ 但注意：prereg 本身不管这三条
```

## 8.2 充分性反向测试（凌翼 Q1_REVERSE_SUFFICIENCY = NOT ESTABLISHED）

| # | 情形 | 期望输出 |
|---|---|---|
| N-10 | R-1..R-6 全部满足，但 R-7 未验证 | `NOT_ESTABLISHED`（不得 `ESTABLISHED`） |
| N-11 | R-1..R-6 全部满足，R-7..R-10 全过 | `ESTABLISHED`（= C1 要素成立；**不**等于最终 class = C1） |
| N-12 | 同 N-11，但 C2 独立成立 | AuthorityGate 仍只报 C1 要素成立；**最终 class 由 §13 机制赋为 C2**（不是 AuthorityGate 输出 C2） |
| N-13 | 同 N-11，但 C3 独立成立 | 同上；最终 class 赋为 C3（不是 AuthorityGate 输出 C3） |

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

**⇒ 全部 23 条（N-01..N-09a / N-10..N-13 / N-14..N-17 / N-18..N-22）：只列设计，未执行。**

---

# 9 · 状态（照录凌翼 §5，并补本版新增项）

```text
BF8_STATUS                        = OPEN
  ├ BF8_PATH_B_BYPASS_FREE        = NOT PROVEN（v0.2 原键，本版保留）
  ├ BF8_PATH_B_CLOSURE_WITHOUT_TOUCHING_EVALUATOR = STRUCTURALLY_IMPOSSIBLE（睫 NB-30，§2.4）
  ├ 函数层封闭（不动 evaluator.py） = STRUCTURALLY_IMPOSSIBLE（§2.4）
  ├ 正式 C1 消费边界               = NOT ESTABLISHED（本版 §4.1b 给出表一，凌翼判"边界未闭合"）
  └ BF8_CODE_IMPLEMENTATION        = NOT AUTHORIZED

BF9_SOURCE_BINDING_GAP           = ACCEPTED（v0.2 原键，本版保留）
BF9_SECTION_7_2_CONFLICT         = REJECTED（凌翼；我原判断错）
BF9_EPISODE_SOURCE_BINDING       = NOT ESTABLISHED
  └ 准确表述：尚未建立真实候选所需的独立 episode/execution 来源绑定链
    （META 载体在 reference 中存在：Ledger / suite manifest）
STATE_DIGEST_DOMAIN              = UNCHANGED

NB31_NON_NORMATIVE_ALIAS         = CONDITIONALLY ACCEPTED
NB31_PREREG_CHANGE               = NOT AUTHORIZED
NB_31_L1_LOCAL_NAMING            = 呈请凌翼裁 → 已裁：CONDITIONALLY ACCEPTED（见 §3）
Q1_FULL_EQUIVALENCE              = NOT ESTABLISHED
Q1_ONE_WAY_NECESSITY             = APPROVED_FOR_DESIGN
Q1_REVERSE_SUFFICIENCY           = NOT ESTABLISHED
Q1_POST_RESET_SCOPE              = EXCLUDED
Q1_CLASS_PRIORITY_PRESERVATION   = REQUIRED

COND_6_EPISODE_SPECIFIC_BINDING  = NOT ESTABLISHED
FOLLOWUP_READ_REGISTRATION       = TWO_LEVEL_BINDING_REQUIRED
REGISTERED_PATH_AUTO_C1          = NO（凌翼 2026-10-26）
UNREGISTERED_READ_AUTO_STOP      = NO（凌翼 2026-10-26）

T_1_W_SHAPE                      = PENDING_QIANXING
T_2_SUBSTRATE_SCHEMA             = NOT ESTABLISHED
T_4_WRITER_SINGULARITY           = PENDING_QIANXING
T_5_META_RECORD_STORE            = NOT ESTABLISHED（承接 v0.2，本版未丢）
T_9_NEGATIVE_CASE_DETECTION      = NOT ESTABLISHED（承接 v0.2，本版未丢）
T_10_STATISTICAL_UNIT_RULE       = PREREGISTRATION_REQUIRED（承接 v0.2，本版未丢）
T_12_AUTHORITY_CONSUMER_PERMISSION = NOT ESTABLISHED（承接 v0.2，本版未丢）
T_13_CAUSAL_PATH_ADJUDICATION    = NOT ESTABLISHED（§7.2 有定义）
T_14_P1_PAYLOAD_IDENTITY         = NOT ESTABLISHED（§7.0 有定义）
T_15a_P1_READ_PATH_EXISTENCE     = NOT ESTABLISHED（候选内，须观测）
T_15b_READ_PATH_AS_GENERAL_GATE  = NOT ESTABLISHED（须规范授权）  [T-15 在此拆开]
T_16_AUTHORITY_PERMISSION_ROOT   = NOT ESTABLISHED（§4.1 有定义）
T_17_AUTHORITY_ISSUER_IDENTITY   = NOT ESTABLISHED（§4.2 有定义）
T_18_MODULE_EXPORT_CONTROL       = NOT ESTABLISHED（§2.4c 有定义）
T_19_AUTHORITY_RESULT_ENUM       = PARTIALLY_DEFINED（§2.2c 给四值；两处不对齐待睫确认）

C1_MEASUREMENT_CHAIN_QUALIFIED   = NOT ESTABLISHED
C1_SCIENTIFIC_RESULT             = NOT ASSESSED
C1_END_TO_END_FEASIBILITY        = PENDING_DESIGN_VALIDATION

D1_EXTERNAL_EXPLANATORY_RECORD   = ALLOWED_NON_NORMATIVE（本文即此类）
D1_FROZEN_MANIFEST_EDITS         = FORBIDDEN（本文未改任何冻结件）
D2_LEGACY_HASH_PROVENANCE        = NOT ESTABLISHED
D2_RENAME_AS_REPAIR              = REJECTED

NEW_B_LINEAGE                    = DESIGN_PARKED
RE-3_RESET_OBSERVER_IDENTITY     = NOT ESTABLISHED
G2_END_TO_END                    = NOT ESTABLISHED
PERSISTENT_WORKER_CLEAN_BLOCK    = ACTIVE

FROZEN_Q3_RC11                   = UNCHANGED
CODE_CHANGE                      = NOT AUTHORIZED
IMPLEMENTATION_AUTHORIZATION     = NONE
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
- 未把 23 条负向测试说成已执行

---

# 11 · 冻结件核验（本版结束时现算）

```text
MANIFEST   78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059
prereg     ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
evaluator  fa644a9bcfd59ffbbb415f0f439599eb705333600e7f8f8f0b93997ce6a59b5a
⇒ 三者均与登记值一致
```

---


## 交付说明

**本文是设计正文。** 八轮自检中的勘误、撤回与自省，已归入：
[C1_STRUCTURAL_CLOSURE_DESIGN_勘误与自省记录_20261027.md](C1_STRUCTURAL_CLOSURE_DESIGN_勘误与自省记录_20261027.md)

**本文不构成：**

```text
代码实施授权  IMPLEMENTATION_AUTHORIZATION = NONE
代码变更      CODE_CHANGE = NOT AUTHORIZED
科学执行      SCIENTIFIC_EXECUTION = MAY NOT START
结构闭合      NOT DECLARED
```

**请睫、知微、钳星复核的落点见 §8 与各节末尾。**

