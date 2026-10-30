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
| 4 | 必要条件、充分条件、invalidity 和 class priority 的**负向测试矩阵** | **§8**（24 条，按三层重排） | 已给设计；**未执行** |
| 5 | P-1 后续读取证据与 C1 最小科学条件的**明确分离** | **§7.1** | 已给七行对照表 |

**⇒ 第 2 项须标清：本文只做到"列出五项待明确"，尚未做到"可验证"。**
**⇒ 这与凌翼原文「表一：方向接受，边界未闭合」一致，不写作"已完成"。**


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

**⇒ 而 AuthorityGate 还有三项超出 prereg 既有要求的判定点（各自与冻结条款的关系不同）：**

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
**⇒ 因此 `C1_STORAGE_ELEMENT_ESTABLISHED` 蕴含 prereg 中注册存储写入证据要素及适用 gate 成立，但它不指最终 `PRE_RESET_CHANGE_CLASS=C1`；且 prereg C1 不蕴含前者（见 §2.1）。**
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
> **当前有效版本见 §2.2b。**

```text
（作废）AuthorityResult 必须携带两个不同字段：
  · episode_specific_write_established  = BOOL（R-6 是否成立）
  · reported_pre_reset_change_class     = C1 / C2 / C3（按 §13 L715-725 优先级）

⇒ 禁止把前者当作后者。
⇒ 若 C2 或 C3 独立成立 ⇒ 后者必须是 C2/C3，即使 C1 要素成立。
⇒ 这一条我 v0.2 完全没写。
```

## 2.2b 结果的三根轴（不是单一枚举）

**⇒ 全文只定义了 `ESTABLISHED`，此前从未说"不成立"时返回什么。**
**⇒ 而 `INVALID` 在文中出现 30 次，没有任何一处说明它属于 `AuthorityResult`。**
**⇒ 这是一处真实的定义缺口，不是措辞问题。**

**⇒ 已更正：此前称"四值"是错的。实际不是四个值，而是【三根轴】。**

**⇒ 凌翼指出：`NOT_ESTABLISHED` 属于证据类别的建立状态，`FAIL`/`UNRESOLVED` 属于测量结果，`INVALID` 属于执行/证据有效性。三件事不在同一根轴上。**

**⇒ 核 `evaluator.py` 实际输出：**

```text
result 有四个值：INVALID（L232） / FAIL（L241） / UNRESOLVED（L248） / PASS（L257, L263）
change_class 有两个值：NOT_ESTABLISHED（L242, L249, L258） / C1（L264）
```

**⇒ 所以正确写法是分轴，不是单一枚举：**

| 轴 | 取值 | 含义 | 权威条款 |
|---|---|---|---|
| **轴 A · 执行/证据有效性** | `VALID` / `INVALID` | 本次执行与证据是否成立。`INVALID` **不是**科学负结果 | §13 L741 |
| **轴 B · 测量结果** | `FAIL` / `UNRESOLVED` / `PASS` | 仅当轴 A = `VALID` 时才有意义。轴 A = `INVALID` 时轴 B 为 `NOT_INSTANTIATED`（**接口状态，不是第四种科学测量结果**） | §13 L729-738 |
| **轴 C · C1 要素建立** | 轴 A = `VALID` 时（规范值）：`C1_STORAGE_ELEMENT_ESTABLISHED` / `NOT_ESTABLISHED`<br>轴 A = `INVALID` 时：`NOT_INSTANTIATED`（接口占位）<br>**非规范派生**：轴 B = `UNRESOLVED` 时另设 `derived.c1_element_establishment = UNDETERMINED`（凌翼 2026-10-28：仅作注释，**不是**轴 C 的规范值） | 轴 A = `VALID` 时才有科学含义；`INVALID` 时为接口占位 | §13 L722-724 |

**⇒ 三轴的依赖规则（已按睫 T-19 裁定与知微 §3.1 收紧）：**

**⇒ 术语声明（凌翼 2026-10-28 要求）：**

```text
本文所说的「轴 C 规范值」是本设计的【映射用语】，
不是冻结 prereg 新增的结果字段。
⇒ 冻结 prereg / evaluator 中只有 result 与 change_class，没有"轴"这一层。
⇒ 三个轴是本设计为了区分三类语义而建立的【外部映射层】。
⇒ 因此不得据「轴 C 规范值」宣称冻结件新增了任何结果字段。
```

```text
轴 A = INVALID
    ⇒ 轴 B、轴 C 均为 NOT_INSTANTIATED（不实例化）
      注：这是【接口状态】，不是第四种科学测量结果
      但【保留】原始局部结果供审查，不得删除历史证据

轴 A = VALID, 轴 B = PASS
    ⇒ 轴 C ∈ { C1_STORAGE_ELEMENT_ESTABLISHED, NOT_ESTABLISHED }

轴 A = VALID, 轴 B = FAIL
    ⇒ 轴 C = NOT_ESTABLISHED（确定地没有建立正向要素）

轴 A = VALID, 轴 B = UNRESOLVED
    ⇒ 轴 C 的【规范值】仍为 NOT_ESTABLISHED（冻结 change_class 原样保留）
    ⇒ 另设【非规范派生注释】derived.c1_element_establishment = UNDETERMINED
    ⇒ 二者并存，UNDETERMINED 不得替换或改写 change_class（凌翼 BF-11）
⇒ 关键区别（三条，不得互相替代）：
   · FAIL        = 有效执行中的【确定负结果】（§13 L729-732）
   · UNRESOLVED  = 有效执行中的【不确定结果】（§13 L735-738），不得据此作否定结论
   · NOT_ESTABLISHED 是"C1 类别未建立"；它不等于"已证明不存在"（凌翼）
   · UNDETERMINED 是派生注释，不是轴 C 的规范值，也不改判据

⇒ 为什么 UNRESOLVED 需要单独注释（睫，经凌翼裁定后修正表述）：
   冻结 change_class 对 FAIL 与 UNRESOLVED 都给 NOT_ESTABLISHED，这是【正确且不改】的。
   但 NOT_ESTABLISHED 读起来像一个结论；在 UNRESOLVED 底下，它其实是一个没结论。
   ⇒ 因此需要的不是改冻结值，而是加一个派生注释，让"不确定"不被读成"确定没有"。

```

**⇒ BF-11：`UNDETERMINED` 与冻结代码的关系（睫提出，凌翼 2026-10-28 已裁）**

```text
冻结 evaluator.py L246-249（字节）：
   if h == 1:
       return L1Result(
           result=UNRESOLVED,
           change_class=NOT_ESTABLISHED,      ← 冻结字段
           ...

⇒ 也就是说：【冻结代码已规定 UNRESOLVED 时 change_class = NOT_ESTABLISHED】

⇒ 而本文让轴 C 输出 UNDETERMINED
   ⇒ 若被理解为【改写 change_class 的值】
     ⇒ 那就是实质规范变更
     ⇒ 而 NB31_PREREG_CHANGE = NOT AUTHORIZED

⇒ 因此必须明确：UNDETERMINED 是【外部接口派生字段】，不是 change_class 的替代
   · change_class 的原始字节值【原样保留】= NOT_ESTABLISHED
   · 而 AuthorityGate 另设一个派生字段表达"不确定"
   · 二者并存，不得静默替换

   具体做法（本文拟议 → 凌翼已于 2026-10-28 裁定：ALLOWED AS NON-NORMATIVE DERIVED ANNOTATION ONLY）：
     冻结字段   change_class            = NOT_ESTABLISHED（不改，原样保留）
     派生字段   derived.c1_element_establishment = UNDETERMINED（本设计新增，非规范派生注释）
   ⇒ 消费者若只读 change_class，看到的是 NOT_ESTABLISHED（冻结语义不变）
   ⇒ 消费者若读派生字段，才知道"这是不确定，不是确定没有"
   ⇒ 但【不得】声明派生字段替换或改写了 change_class

⇒ 裁定结果：BF11_SEMANTIC_DECISION = RESOLVED / FROZEN_FIELD_REWRITE = PROHIBITED / NORMATIVE_EXTENSION = NOT AUTHORIZED
```


## 2.2b-1 派生的六项条件与四种情况（凌翼 2026-10-28 裁定原文）

**⇒ 凌翼裁定的六项必须同时满足的条件，逐条落点：**

```text
① 原始 result / change_class / 相关证据保持不变
   ⇒ 本文：change_class 原样保留 = NOT_ESTABLISHED

② UNDETERMINED 须明确标记为非规范派生字段
   ⇒ 本文：已标"派生字段"（本节 + 表三第 10 行）

③ 派生过程须记录【来源字段 / 适用规则 / 版本】，且可独立复算
   ⇒ 此前缺失，现补：派生记录至少须含
      · source_result        = raw_l1.result        （= UNRESOLVED）
      · source_change_class  = raw_l1.change_class  （= NOT_ESTABLISHED）
      · derivation_rule_id   = 本文 §2.2b 轴映射规则标识
      · derivation_rule_version
      · 独立复算条件：同一 (source_result, source_change_class,
        derivation_rule_version) 必得同一派生值
   ⇒ 缺任一项，派生值不得被引用

④ 只允许在执行/证据有效性已确认、且测量确为 UNRESOLVED 时派生
   不得仅凭未经验证的局部结果签发科学结论
   ⇒ 本文：轴 A = VALID 前提；不得绕过 AuthorityGate

⑤ 派生字段不得单独充当正式 C1 判定或最终 PRE_RESET_CHANGE_CLASS
   ⇒ 本文：已写明（表三第 11 行、§2.2d）

⑥ 不得用该字段改变冻结的 FAIL / UNRESOLVED / INVALID 判据
   ⇒ 本文：已写明"不得改写 change_class"
```

**⇒ 四种情况的区分（凌翼 §3，本文照录为唯一权威）：**

```text
A = VALID, B = FAIL       → 正向 C1 不建立 → 可记录 NOT_ESTABLISHED
A = VALID, B = UNRESOLVED → 测量尚无确定结果 → 冻结 change_class 仍为 NOT_ESTABLISHED
                            → 可以另记派生注释 UNDETERMINED
A = INVALID               → 不产生有效的科学测量结论 → 保留原始局部数据与无效原因
A = VALID, B = PASS       → 仍须独立审核 C1 专属建立条件
                            → 不得自动签发 C1_STORAGE_ELEMENT_ESTABLISHED
```

**⇒ 四类禁止的越界（凌翼 §4）：**

```text
· 将冻结 change_class=NOT_ESTABLISHED 改写成 UNDETERMINED
· 宣称冻结 prereg 已定义新的 UNDETERMINED 科学结果
· 用派生字段改变测量有效性、class selection 或证据接纳条件
· 未获授权前，将非规范注释升级为具有判定效力的 AuthorityGate 正式输出
```

**⇒ 认识论边界（凌翼原文）：**

> UNRESOLVED = 本次测量落入冻结的不确定区；
> NOT_ESTABLISHED = 本次没有建立正向 C1 类别。
> **没有建立，不等于已经证明不存在。**

⇒ 因此不得把冻结的 NOT_ESTABLISHED 重新解释为"确定没有发生存储写入"。

### 关于 `NOT_INSTANTIATED` 这个词（睫 NB-43）

```text

⇒ 它与 prereg 已有的 NOT_ASSESSED 【不是同义词】：
   · NOT_ASSESSED（prereg / evaluator.py L64, L72, L181）
     = 没有测。且 L64 明文排除 "attempted-but-not-run"。
   · NOT_INSTANTIATED（本文新造）
     = 轴 A = INVALID 之后"不产生结论"。
     而 INVALID 表示【执行/证据无效】，它本身不证明测量已实际发生：
     本文已将必需规则、witness 或来源证据缺失列为 invalidity。
     ⇒ 是否执行、是否采到数据，应另据运行记录判断，
       不能从 INVALID 反推出“已经测了”。
     那恰恰是 L64 排除在 NOT_ASSESSED 之外的东西。

⇒ 而 L1556 / L2007 各自的作用域必须写准（本轮核字节更正）：
   · L1556 位于 §24（POST_RESET_CLASS_RULE）内，
     说的是【post-reset 未尝试的 higher class】记为 NOT_ASSESSED，
     ⇒ 它约束的是 post-reset 语境，不是 pre-reset 轴 A/B/C。
   · L2007 位于 §32（Result Citation Discipline，L1966 起），
     约束的是【不得把字段拆开重拼】，
     ⇒ 它同时适用于本文的轴模型：三个轴的值不得被拆开重组为另一种 claim。

⇒ 因此本文与冻结词的关系是：
   · 本文不改变、不替换 NOT_ASSESSED 的任何冻结含义
   · 本文的 NOT_INSTANTIATED 是【外部接口的占位状态】：
     当执行/证据有效性轴 A 为 INVALID 时，B、C 不签发有效科学结论。
     它不改写冻结输出，不与 NOT_ASSESSED 互换；原始局部结果仍保留。
   · 二者作用域不同（post-reset higher class vs pre-reset 轴 C），
     不得互换，也不得据此推断对方的状态
```

**⇒ 而此前我把它们压成一列，会导致一个具体错误：**
```text
⇒ 读者会把 INVALID 与 FAIL 当成同一个枚举里的两个值
⇒ 于是"执行无效"与"科学负结果"变成可互换的
⇒ 而这正是 §13 L741 明文禁止的："不得把 protocol/execution invalidity 写成 L1 = FAIL"
```

**⇒ 与表三的对应关系（分轴后清晰）：**

```text
表三第 1-5 行  → 轴 A = INVALID（轴 B/C 不产生）
表三第 6 行    → 不签发任何轴
表三第 7 行    → 独立的【逐项】标记（见 §2.2c），不属于三轴
表三第 8 行    → 独立的【逐项】标记（见 §2.2c），不属于三轴
表三第 9 行    → 轴 A=VALID, 轴 B=FAIL, 轴 C=NOT_ESTABLISHED
表三第 10 行   → 轴 A=VALID, 轴 B=UNRESOLVED, 轴 C=UNDETERMINED（派生字段；change_class 冻结值仍为 NOT_ESTABLISHED）
表三第 11 行   → 轴 A=VALID, 轴 B=PASS, 轴 C=C1_STORAGE_ELEMENT_ESTABLISHED（若 R-1..R-10 全过）
```

## 2.2c 逐项标记与整体结果分离（睫 NB-35 / NB-36）

**⇒ 睫的两条裁定，我接受：**

```text
NB-35  NEUTRAL_REVIEWED 不得并入三轴，否则会成为"万能排除键"
       ⇒ 任何不想处理的边界外读取，都可以被标成"无因果路径"，然后消失
       ⇒ 而它消失的方式是【被记录】，不是【被删除】
       ⇒ 所以 T-13 三项（谁判 / 引用什么证据 / 何时封存）
          必须挂在 NEUTRAL_REVIEWED 这个标记本身上，不能挂在别处

NB-36  表三第 8 行"可纳入证据"不得等于任何轴的值
       ⇒ 三轴是【整体】结论（一个）
       ⇒ 第 8 行说的是【逐项】接受（可以有多个）
       ⇒ 若它等于 NOT_ESTABLISHED，"有一个证据被接受了"
          会以"C1 尚未成立"的名义出现
       ⇒ 而"尚未成立"听起来像【快成立了】，实际它只是"这一项被收下了"
```

**⇒ 因此另设两个【逐项】标记，与三轴分开，且允许同时存在多个：**

```text
EVIDENCE_ADMITTED        ← 某一条证据项被接受（不等于 C1 建立）
NEUTRAL_REVIEWED         ← 某一条边界外读取经独立审查确无相关因果路径
   必带三项（T-13）：谁判 / 引用什么证据 / 何时封存
```

## 2.2d 停用"正式 C1"一词（凌翼指出的歧义）

**⇒ 凌翼指出：v0.3 §2.4a 把"正式 C1"定义为"AuthorityGate 证明 C1 要素成立"，但 §12 的表述是「storage write 是目前最高被正向建立的 change class」——指的是【最终报告的类别】。**

**⇒ 于是我用一个新词解决了旧混淆，同时制造了新混淆。**

**⇒ 更正：停用「正式 C1」。改用两个独立术语：**

```text
C1_STORAGE_ELEMENT_ESTABLISHED    ← 单项证据成立（AuthorityGate 的输出，轴 C）
PRE_RESET_CHANGE_CLASS = C1       ← 最终 class（§13 L715-725 机制赋值）
⇒ 二者在 C2/C3 都不成立时才重合
```

**⇒ 本文所有出现「正式 C1」处，均应读作 `C1_STORAGE_ELEMENT_ESTABLISHED`。**

**⇒ 一条附注：**

> **我定义了"成功"的形态，却从没定义"失败"的形态。**
> **而一个只有成功分支的接口，无法被实现。**
> （睫补：它还会让"失败"在将来被【就近归类】到任何一个看起来像失败的格子里。）

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

## 2.4 BF-8 的旁路分析（结论已按知微/凌翼意见收窄）

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
⇒ 收窄后（知微、凌翼要求）：
   对已经能够读取并执行该代码的任意 Python 调用者，当前函数接口不认证 writer；只依赖该接口无法强制科学授权。

⇒ 两条结论必须分开：
   ① 函数接口层：当前接口不认证 writer（见上）；
      这是"接口缺少 writer 参数"的事实，不是"部署权限也无法限制"的结论。
   ② 正式消费边界层（谁能签发 C1_STORAGE_ELEMENT_ESTABLISHED）：
      **拟议可封闭**（设计假设），封点在【正式消费边界 + 合同层命名】（见 §4.1b / §3）；
      但封闭性本身 = **NOT ESTABLISHED**，须由负向测试（§8.4）证伪而非证实；
      且当前 T-18 仍 = NOT ESTABLISHED。
```

## 2.4a 术语对照表（已停用「正式 C1」）

**⇒ 凌翼指出：本节此前把「正式 C1」定义为「AuthorityGate 证明 C1 要素成立」，但 §12 的表述是「storage write 是目前最高被正向建立的 change class」——指的是【最终报告的类别】。**

**⇒ 于是我用一个新词解决了旧混淆，同时制造了新混淆。已更正：停用「正式 C1」。**

| 术语 | 精确定义 | 由谁产生 | 权威条款 |
|---|---|---|---|
| **`L1_local`** | `evaluate_basic_l1` 返回的局部计算结果（含 `change_class=C1`） | reference 函数 | 非规范别名（凌翼 NB-31） |
| **`C1_STORAGE_ELEMENT_ESTABLISHED`** | `episode-specific registered storage write` 这一条独立判据成立（轴 C） | AuthorityGate | §13 L722-724 的 C1 分支 |
| **`PRE_RESET_CHANGE_CLASS = C1`** | §13 的 **class selection 结果**（最终报告类别） | §13 L715-725 机制 | §12 L635-637 的语义 |

**⇒ 关键区分（必须记住）：**

```text
C1_STORAGE_ELEMENT_ESTABLISHED ≠ PRE_RESET_CHANGE_CLASS = C1
⇒ 二者在【C2/C3 都不成立】时才重合
⇒ 若 C2/C3 独立成立，前者可能为真，而后者的值是 C2/C3
⇒ 停用「正式 C1」：它既可能被读成前者，也可能被读成后者
```

**⇒ 本文其余各处用到「正式 C1」时，均应读作 `C1_STORAGE_ELEMENT_ESTABLISHED`。**

## 2.4b `__all__` 不是访问控制 —— 它不能用来论证旁路是否封闭

**⇒ 本节已更正（知微、凌翼均指出）。此前的表述把 `__all__` 当成"一道门"，这是错的。**

```text
afterglow_harness/__init__.py（209 字节）：
  __all__ = [
      "harness_constants", "storage", "readers",
      "writers", "observer", "perturbation_j",
  ]
  ⇒ 六项，不含 evaluator
```

**⇒ 但 `__all__` 的语义是：**

```text
__all__ 只决定 `from package import *` 时导入哪些名字。
它【不】限制 `from package import name` 这种显式导入。
它【不】提供任何调用权限校验。
⇒ 它不是访问控制机制。
```

**⇒ 因此：**

```text
✗ 旧表述：包层有白名单，但绝对导入"绕过"了它
✓ 更正：
   __all__ 与"谁能调用 evaluate_basic_l1"无关。
   不存在"绕过"——因为它本来就不管这件事。
   所以它不能作为"旁路是否封闭"的证据，无论哪个方向。
```

**⇒ 真正的事实只有一条：**

```text
evaluate_basic_l1 是模块级公开函数。
任何能读取并执行该代码的 Python 调用者，都可以写一行
    from evaluator import evaluate_basic_l1
⇒ 当前函数接口既不认证 writer，也不强制科学授权。
```

**⇒ 而这与"部署权限能否限制可执行主体"是另一个层次的问题，不能混为一谈。**
**⇒ 也不等于"正式消费边界不可能封闭"。**

```text
T-18 已更名：
  旧：T-18 MODULE_EXPORT_CONTROL            ← 命名错误（__all__ 不承担此功能）
  新：T-18 FORMAL_RESULT_CONSUMER_AUTHORIZATION = NOT ESTABLISHED
      含义：正式科学结果的签发与消费授权边界尚未建立。
      注：与"函数是否可被普通 Python 代码导入"无关。
```

## 2.4c `__init__.py` 的冻结核验（保留事实，删除结论性解读）

**⇒ 事实部分保留：**

```text
MANIFEST         grep "__init__"          → 零命中                    [终端核验]
role_registry    grep "__init__"          → 零命中                    [终端核验]
manifest_bind    COMPONENT_FILES（L85-107）→ 22 项，无 __init__.py     [读文件]
```

**⇒ 而解读必须收窄（知微指出）：**

```text
✗ 旧解读：包层的"导出控制"是一个可以被静默修改的表面
✓ 更正：
   · 上述 grep 只能说明它不在【逐文件冻结清单】里
   · 不能证明作者当初是有意遗漏还是无意遗漏（作者意图不能由 grep 判定）
   · 不等于它不受任何版本摘要约束
   · 更不等于当前已获修改授权
   · 也不应为了让 __all__ 成为安全白名单而补冻或改写它 —— 它不承担这种功能
```

**⇒ 若真实候选会执行包初始化代码，该代码及实际加载路径应纳入候选依赖与绑定审查。**
**⇒ 这是运行依赖问题，不是星号导入清单问题。**

## 2.4d episode-specific 是执行侧属性（睫 NB-41）

**⇒ 这是 §9 中 `BF9_EPISODE_SOURCE_BINDING = NOT ESTABLISHED` 那一格的理由，必须写在正文。**

```text
prereg §13 L722-724 的 C1 class rule 原文：
   "an episode-specific registered storage write is established
    in preregistered LITERAL_STORAGE_COMPONENTS"

⇒ 读这句话，会以为 "episode-specific" 是那个 write 在 STATE 上的属性。
⇒ 而字节说：那个 write 在 STATE 上只有"变了"和"没变"两件事。
   "哪一次"它一点都不知道（digest 输入域 24 字节，§7.2 禁 episode_id 进入）。

⇒ 所以 episode-specific 从来就不在 STATE 里。
⇒ 它从来就是【执行侧】的属性。
⇒ 该 schema 把 episode-specific 的证明责任，整体推给了执行侧。

⇒ 若 COND_6 那条链建起来 ⇒ episode/execution 来源绑定这一必要条件得到支持
                              （不等于 C1 建立；还须其余 R-1..R-10 全过）；
⇒ 若那条链建不起来 ⇒ C1 不可建立，而失败的原因不在 STATE，在 META↔执行 的绑定。
```

**⇒ 必须收窄的一点（知微 §3.2）：**

```text
✗ 旧写法：若 COND_6 那条链建起来 ⇒ C1 可建立
✓ 收窄为：
   COND_6 建立后，episode/execution 来源绑定这一必要条件得到支持；
   还须满足其余适用 gate 与独立 C1 class rule，才能建立注册存储写入证据。

⇒ 直接反例：执行身份与采集来源完整可信，但目标臂没有产生注册判据所要求的变化。
   ⇒ COND_6 可以成立，而科学结果仍可为 FAIL，不能签发 C1。
   ⇒ （依据：evaluator.py L237-245 的 h==0 分支）

⇒ 两类证据的分工（知微要求）：
   STATE 的独立观察 = 证明【发生了什么注册变化】
                     （包括 B 内容是否等于注册 payload，不只变化幅度）
   执行侧 META      = 证明【这些观察、writer、对象与本轮 episode/execution 的关联】
   ⇒ 两类证据共同承担 C1 的证明责任。
   ⇒ “证据重心在执行侧”不等于“可以弱化 STATE 内容核验”。
```
⇒ 因此：**C1 的证据重心在【执行过程】，不在【状态数据】。**


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
禁 1  L1_local == C1 不得被读成"C1_STORAGE_ELEMENT_ESTABLISHED 已建立"
禁 2  不得把 change_class 字段值替换成 L1_local（那是静默替换冻结字段）
禁 3  不得声明 L1_local ⟺ C1_STORAGE_ELEMENT_ESTABLISHED（那是把别名升级成等价）
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

| 角色 | 产出 | 是否可形成 C1_STORAGE_ELEMENT_ESTABLISHED | 边界依据 |
|---|---|---|---|
| **校准消费者**（`smoke_evaluator.py` / `recompute_from_ledger.py` / `fixtures.py` / `evidence_bundle.py` 现有路径） | 局部 `L1Result`（含 `change_class=C1`） | **否** | `PHASE_A` / `SCIENTIFIC_CLAIM_ELIGIBILITY = "NONE"`（fixtures.py L50-51；suite L159-160） |
| **证据采集者**（observer） | BEFORE/AFTER 原始字节 + digest + 采集阶段身份 | 否 | 只读；不参与判别 |
| **权威裁决者**（`C1AuthorityGate`，拟建） | `AuthorityResult` | **拟为唯一** | 须经注册与独立登记（T-16/T-17 未建立） |
| **正式结果存储** | AuthorityGate 的 C1 要素判定结果（**不是最终 `PRE_RESET_CHANGE_CLASS`**；后者由 §13 L715-725 机制写入） | 否（存储不生产） | 只接受受信入口写入 |
| **正式结果组装/引用者**（补，知微 §3 要求） | 按 §13 组装最终 class、生成正式 result tuple | **不能自行签发该要素**；仅验证并引用受信 AuthorityGate 的要素结果 | 须登记其输入来源、身份、权限与失败后果；须回答：能否接受用户提供的假结果、能否绕过权威来源、能否交叉拼接不同 execution 的结果。**当前 NOT ESTABLISHED** |
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
| 7 | 边界外读取，经独立审查**确无相关因果路径** | — | — | — | **逐项标记**：`NEUTRAL_REVIEWED`（**必带 T-13 三项**：谁判/引用什么/何时封存；睫 NB-35）。**不产生任何轴的值**，也不判 INVALID |
| 8 | 通路已登记 + 事件合规 + **有**因果路径 | — | — | — | **逐项标记**：`EVIDENCE_ADMITTED`（睫 NB-36）。**不等于任何轴的值**；"C1 尚未成立"与"这一项被收下"是两件事 |
| 9 | 全部 required structure 有效且已执行，测量为负 | 轴 A = VALID | 轴 B = **FAIL** | 轴 C = NOT_ESTABLISHED | `FAIL`（此时才允许） |
| 10 | 同上，落入不确定区 | 轴 A = VALID | 轴 B = **UNRESOLVED** | 轴 C = **NOT_ESTABLISHED**（冻结字段原样保留）<br>非规范派生注释：`derived.c1_element_establishment = UNDETERMINED` | `UNRESOLVED` |
| 11 | 同上，h≥2 且 payload 匹配，且 1-8 全过 | 轴 A = VALID | 轴 B = **PASS** | 轴 C = **C1_STORAGE_ELEMENT_ESTABLISHED**（若 R-1..R-10 全过） | AuthorityGate 输出轴 C；**最终 `PRE_RESET_CHANGE_CLASS` 仍由 §13 L715-725 机制另行赋值** |

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
✗ 旧：C1 要素必须依赖 evaluate_basic_l1 返回 C1
✓ 新：权威门消费的是【经该候选注册的判别实现的结果】。
      只有在证明 schema 与语义适用时，才可具体复用旧函数。
      参考校准成功不提供真实摘要的测量资格。
```

## 7.1 P-1 后续读取证据 vs C1 最小科学条件的明确分离（凌翼 §4 要求）
**⇒ 凌翼 §4 要求「P-1 后续读取证据与 C1 最小科学条件的明确分离」。下表给出该分离。**

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

### 8.1c 第三层 · 超出 prereg 的新增机制

| # | 移除哪一项 | 期望输出 | 理由 |
|---|---|---|---|
| N-07 | R-7 writer ≠ 注册主体 | `INVALID` | 超出 prereg：§4 冻结了三字段，但无核对机制 |
| N-08 | R-8 旧快照冒充本轮 after | `INVALID` | **属 gate 5 的具体化**（§31 L1948-1949 已要求 execution_id/hash）；本设计只是补核对机制，非新增条件 |
| N-09 | R-9 通路未登记且已发生 **且与本 claim 有因果路径** | `INVALID` | 凌翼 §4；§37 `UNREGISTERED_EPISODE_REINJECTION`。**须同时满足**：① 未登记 ② 已实际发生 ③ 引入先前 episode 信息 ④ 与本 claim 有因果路径。边界外、无因果路径者不得判停（见 N-17） |

### 8.1d 约束项 · 不得借用（跨层）

| # | 情形 | 期望输出 | 理由 |
|---|---|---|---|
| N-09a | R-10 C1 的 ATTRIBUTED 被借用去满足 C2 conjunct | C2 **不得**因此建立 | §16 L958："Basic L1 / C1 scope 的 D_ATTRIBUTION result 不得满足这一 conjunct" |

**⇒ 三层分开之后，有一条以前看不出来的区别现在显出来了：**

```text
第一层失败（N-01..N-03、N-05）⇒ 轴 A = INVALID ⇒ 整次执行无效
第一层中的 N-04 例外：
  · attribution 确定负结果 ⇒ 轴 B = FAIL（不是 INVALID）
  · 落入 indeterminate region ⇒ 轴 B = UNRESOLVED（不是 INVALID）
  · rule 缺失 / outcome 后改变 ⇒ 轴 A = INVALID
  ⇒ 【不得用“N-01..N-05 全为 INVALID”的概括句覆盖 N-04】
第二层失败（N-06）      ⇒ 只是 C1 要素未建立 ⇒ 若 C2/C3 独立成立，报告 C2/C3
第三层（N-07..N-09）    ⇒ N-07/N-09 判 INVALID；
                          N-08 属 gate 5 具体化，实现机制未提供 ≠ 规范无义务
```

## 8.2 充分性反向测试（凌翼 Q1_REVERSE_SUFFICIENCY = NOT ESTABLISHED）

| # | 情形 | 期望输出 |
|---|---|---|
| N-10 | **设计尚未实现**（R-7 机制未建立，未执行） | `NOT_ESTABLISHED`（不得 `ESTABLISHED`） |
| N-10a | **某次实际执行**缺少本 claim 必需来源证据 | 按适用条款记 `INVALID`（与 N-10 场景不同） |
| N-11 | R-1..R-6 全部满足，R-7..R-10 全过 | `ESTABLISHED`（= C1 要素成立；**不**等于最终 class = C1） |
| N-12 | 同 N-11，但 C2 独立成立 | AuthorityGate 仍只报 C1 要素成立；**最终 class 由 §13 机制赋为 C2**（不是 AuthorityGate 输出 C2） |
| N-13 | 同 N-11，但 C3 独立成立 | 同上；最终 class 赋为 C3（不是 AuthorityGate 输出 C3） |

**⇒ 关于 N-12 / N-13 的简写禁止（睫 NB-45）：**

```text
⇒ 轴 C 的值【不得简写为 "C1"】
   · 轴 C 只有 C1_STORAGE_ELEMENT_ESTABLISHED，没有 "C1"
   · "C1" 只属于 PRE_RESET_CHANGE_CLASS（§13 机制赋值）
⇒ 若在测试预期、日志、摘要中把轴 C 写成 "C1"
   ⇒ 就是把要素成立读成了最终类别成立
   ⇒ 正是 §2.2d 停用「正式 C1」要防的那件事
```

**⇒ 关于 N-11 的三点限定（凌翼 §4 要求）：**

```text
① 「期望拒绝」不等于「已经具有可验证的拒绝机制」
   ⇒ 本矩阵列的是【期望】，不是【已实现的检测能力】
② N-11 的预期 ESTABLISHED 是【待验证设计】，不是充分性已证明
③ N-11 的测试预期【不能由待测 AuthorityGate 自己生成】
   ⇒ 否则形成循环验证
   ⇒ 须由独立于被测 AuthorityGate 的主体给出预期
   ⇒ 该主体与判定程序 = NOT ESTABLISHED（T-18 相关）
```

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
| N-21 | 同 plan 引用下，替换 BEFORE/AFTER 原始字节后重新封存 | 拒绝。**检出依据不足**：仅校 plan 引用无法发现（plan 仍正确）。须校④层：原始事件承诺 / 事件来源 / 完整事件集合 / 受信封存身份（知微反例） |
| N-22 | 用改名把 `L1_local` 声明为 `C1` | 拒绝（NB-31 禁 3） |

**⇒ 全部 24 条（N-01..N-09a / N-10..N-13 / N-14..N-17 / N-18..N-22）：只列设计，未执行。**

---

# 9 · 状态（照录凌翼 §5，并补本版新增项）

```text
BF8_STATUS                        = OPEN
  ├ BF8_PATH_B_BYPASS_FREE        = NOT PROVEN（v0.2 原键，本版保留）
  ├ BF8_PATH_B_CLOSURE_WITHOUT_TOUCHING_EVALUATOR = 已撤回（原标 STRUCTURALLY_IMPOSSIBLE，范围过宽）
  ├ 函数接口层                       = 当前接口不认证 writer（事实）；不推导“部署权限也无法限制”
  ├ 正式结果消费边界               = NOT ESTABLISHED（本版 §4.1b 给出表一，凌翼判"边界未闭合"）
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
T_18_FORMAL_RESULT_CONSUMER_AUTHORIZATION = NOT ESTABLISHED（§2.4b 有定义；与函数可导入性无关）
T_19_RESULT_AXIS_STRUCTURE = RESOLVED (DESIGN_SCOPE_ONLY)（凌翼 2026-10-28 裁定：设计语义已收口，不等于实现或验证完成）
T_19_RESOLUTION_SCOPE        = DESIGN_ONLY
DERIVATION_INDEPENDENT_RECOMPUTATION = NOT VERIFIED
BF11_SEMANTIC_DECISION         = RESOLVED（凌翼 2026-10-28）
BF11_NON_NORMATIVE_DERIVATION  = ALLOWED_FOR_DESIGN
BF11_FROZEN_FIELD_REWRITE      = PROHIBITED
BF11_NORMATIVE_EXTENSION       = NOT AUTHORIZED

```text
⇒ 记账分离（凌翼 2026-10-28 明确要求）：
   T19 = RESOLVED 只说明【结果轴的定义与语义边界已收口】，
   ⇒ 不说明 AuthorityGate 可用
   ⇒ 不说明派生可独立复算（DERIVATION_INDEPENDENT_RECOMPUTATION = NOT VERIFIED）
   ⇒ 不说明消费者侧已建立（T-18 = NOT ESTABLISHED）
   ⇒ 不说明 C1 科学结论可签发

   ⇒ 禁止用"仅引用 T19=RESOLVED"推导出 AuthorityGate 可用或 C1 可签发。
```

AUTHORITY_RESULT_IMPLEMENTED   = NO

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
- 未把 `L1_local` 声明为等价于 C1_STORAGE_ELEMENT_ESTABLISHED
- 未宣称表一闭合
- 未把 h>=2 写成通用规则
- 未把 24 条负向测试说成已执行

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

---

# 12 · 收尾：本文边界在哪，下一步为什么是那两条链

**日期**：2026-10-30
**性质**：收尾说明。不新增规则，不改变本文任何已述设计。

## 12.1 本文到此为止能声明什么

**⇒ 设计层：三轴结构已收口。**

```text
T_19_RESULT_AXIS_STRUCTURE = RESOLVED (DESIGN_SCOPE_ONLY)   ← 凌翼 2026-10-28 裁定
BF11_SEMANTIC_DECISION     = RESOLVED
BF11_NON_NORMATIVE_DERIVATION = ALLOWED_FOR_DESIGN
BF11_FROZEN_FIELD_REWRITE  = PROHIBITED
BF11_NORMATIVE_EXTENSION   = NOT AUTHORIZED
```

**⇒ 而这是「定义完成」，不是「机制实现」，也不是「结果验证」。**
**⇒ 三类必须分开记账（凌翼明确要求）：**

```text
「这件事的定义是否完成？」   ⇒ T-19 = RESOLVED
「这件事的机制是否实现？」   ⇒ AUTHORITY_RESULT_IMPLEMENTED = NO
「这件事的结果是否经过独立验证？」 ⇒ DERIVATION_INDEPENDENT_RECOMPUTATION = NOT VERIFIED
```

## 12.2 本文没有做的那件事，正是下一步

**⇒ 本文把「每个条件是什么」写清了，但没写「它们怎样串成一条可检验的流程」。**

```text
本文做了：  把 R-1..R-10 拆成三层、把结果分成三轴、把四张表分开、列 24 条反例
本文没做：  一条 execution 从头到尾的证据流长什么样
            ——谁启动、谁写、谁观察、谁封存，哪份记录能区分本轮与旧记录
```

**⇒ 而 BF-8 与 COND_6 之所以一直 OPEN，缺的正是这个：**
**⇒ 不是缺规则，是缺「一条链长什么样」。**

**⇒ 因此凌翼裁定 §4 允许转向两条独立证据链：**

```text
链 A · Writer Attribution
   谁实际写入？写入了哪个对象？如何独立验证？
   ⇒ 对应本文 R-7（writer 关联）

链 B · Episode / Execution Binding
   本次写入对应哪一次执行？如何防旧证据重放？如何证明关联？
   ⇒ 对应本文 R-8（execution 来源绑定；§31 L1948-1949 已要求，属 gate 5 具体化）
```

**⇒ 两条链不是新规则，是把 R-7 / R-8 展开成可检验的流程。**

## 12.3 下一步文档

```text
文件：reports/review_history/两条证据链_设计草案_v0.1_20261030.md
依据：凌翼·T-19 状态确认（2026-10-28）§4
基准：本文 commit 1e753b4
性质：非冻结设计草案；不含实现，不声称已验证
```

**⇒ 它承接的是本文的哪几格：**

| 本文位置 | 被哪条链展开 |
|---|---|
| R-7（§2，writer 关联） | 链 A · A-M3 身份核对点 |
| R-8（§2，execution 来源绑定） | 链 B · B-M7 重放检测 |
| §2.4 BF-8 旁路分析 | 链 A · A-G1「冻的是应该，缺的是实际」 |
| §2.4d episode-specific 是执行侧属性 | 链 B · B-G5「META 侧关联从未建立」 |
| §5.0 三类对象（Plan / Event / Sealed） | 链 B · B-M1 / B-M3 / B-M5 |
| §8.4 旁路与伪造测试 | 链 A · A-N1..A-N6；链 B · B-N1..B-N7 |

## 12.4 本文的最终状态

```text
设计层已收口（本文）
   T_19_RESULT_AXIS_STRUCTURE   = RESOLVED (DESIGN_SCOPE_ONLY)
   三轴语义 / 派生条件 / 术语边界 = 已定

实现层未开始
   AUTHORITY_RESULT_IMPLEMENTED = NO
   DERIVATION_INDEPENDENT_RECOMPUTATION = NOT VERIFIED

科学层未建立
   BF8_STATUS                   = OPEN
   BF9_EPISODE_SOURCE_BINDING   = NOT ESTABLISHED
   COND_6                       = NOT ESTABLISHED
   C1_MEASUREMENT_CHAIN_QUALIFIED = NOT ESTABLISHED

门禁不变
   CODE_CHANGE                  = NOT AUTHORIZED
   IMPLEMENTATION_AUTHORIZATION = NONE
   SCIENTIFIC_EXECUTION         = MAY NOT START
   FROZEN_Q3_RC11               = UNCHANGED
```

## 12.5 一句

**本文回答的是「每个条件叫什么、边界在哪」。**
**两条链要回答的是「这些条件怎样在一次执行里被满足」。**

**⇒ 前者已经收口；后者刚刚开始画。**
**⇒ 而两者都不等于「C1 已建立」。**

