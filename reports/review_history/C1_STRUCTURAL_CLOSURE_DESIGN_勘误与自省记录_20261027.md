# C1 STRUCTURAL CLOSURE DESIGN · 勘误与自省记录

**性质**：本文是设计正文的勘误与自省归档，**不是设计正文**。
**目的**：把八轮自检中我犯的错、撤回的判断、对错误的归纳集中于此，使设计正文保持为可审的设计文档。
**设计正文**：[C1_STRUCTURAL_CLOSURE_DESIGN_v0.3_20261027.md](C1_STRUCTURAL_CLOSURE_DESIGN_v0.3_20261027.md)
**日期**：2026-10-27

---

## 归档说明

本文保留原节号。正文中已移除下列各节，故本文节号不连续：
`§0`、`§2.0`、`§2.0b`、`§2.2b`、`§3.1`、`§4.3`、`§12`（含 12.1–12.3）。

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

## 2.0 第七轮自检：R-1..R-6 不是 C1 专属，而是所有 class 共享

**第七轮我逐一问：R-1..R-10 里，有没有哪一项其实不属于 C1？**

**⇒ 核 §13 L700 原文：**

```text
L700  "任何正向 `PRE_RESET_CHANGE_CLASS = C1 / C2 / C3` 都必须先通过【同一个】Basic L1 gate："
```

**⇒ 也就是说 R-1..R-5 是【C1/C2/C3 三者共有的 gate】，不是 C1 的专属条件。**

**⇒ 而 R-6（L722-724）才是 C1 专属的 class rule。**
**⇒ 对应的 C2 专属在 §16、C3 专属在 §19-20（见 §1.1 的 X-1..X-4）。**

**⇒ 因此正确的层级是三层，而我上一版把它们平铺成同一列：**

```text
第一层 · Basic L1 gate（共享）
  R-1 §13 L702 / R-2 §13 L703 / R-3 §13 L704 / R-4 §13 L705+L708 / R-5 §13 L711
  ⇒ 任何 class 都必须过
  ⇒ 过不了 ⇒ 连"疑似 C1"都谈不上，L1 层就没有正向结果

第二层 · C1 class rule（C1 专属）
  R-6 §13 L722-724 episode-specific registered storage write
  ⇒ 只有这一条区分 C1 与 C2/C3

第三层 · 本设计新增（比 prereg 更严格，且仅在 AuthorityGate 层）
  R-7 writer 关联 / R-8 execution 来源绑定 / R-9 通路登记
  ⇒ 不在冻结 prereg 里
  ⇒ 因此 AuthorityGate = ESTABLISHED 严格强于 prereg 的 C1

约束项 · 不得借用（跨层）
  R-10 §16 L958：C1 的 ATTRIBUTED 不得满足 C2 conjunct
  ⇒ 它是"禁止"而不是"条件"（见 §12.1 的教训）
```

## 2.0b 第七轮续查：R-8 其实已被 gate 5 覆盖，R-7 只覆盖了一半

**⇒ 第七轮第二个问题：R-7/R-8/R-9 里，有哪些其实不是"新增"，而是 gate 5 的既有要求？**

```text
核 §31 Machine Provenance（L1913-1954）"至少记录"清单：
  L1948  execution_id
  L1949  execution_hash
  L1950  baseline_state_id
  L1952  base_model_hash
  L1953  execution_environment_identity

⇒ 所以 execution 身份【已经是 provenance 的必备内容】
⇒ 而 gate 5（L711）要求 "required provenance 完整"
⇒ 因此 R-8（execution 来源绑定）【不是新增条件】
   ⇒ 它是 gate 5 的具体实现要求
⇒ 我上一版把它标为"本设计新增"，这是错的。
```

**⇒ 而 R-7（writer 身份）要分两半：**

```text
§31 的 provenance 清单里【没有】write_operator（我 grep 过，零命中）
⇒ writer 身份不在 §31 的 provenance 必备项里

但 §4 L169-171 要求在启动前冻结：
  write_operator_identity / write_operator_version / write_operator_hash

⇒ 所以 writer 身份【有冻结要求】，但【不在 gate 5 的 provenance 完整性范围】
⇒ 因此 R-7 的真缺口是：
   "已冻结 ≠ 已与实际执行主体核对"
   ⇒ 冻结了三个值，但没有任何机制证明"实际执行的是这个 writer"
⇒ 这一半确实是新增（BF-8 的真身）
```

**⇒ 而 R-9（通路登记）呢：**

```text
§37 L2253-2254 有 UNREGISTERED_EPISODE_REINJECTION / UNREGISTERED_RETRIEVAL_INDUCED_WRITE
⇒ 说明"未登记"是被禁止的状态
⇒ 但 prereg 没有规定"登记在哪里、以什么形式"
⇒ 所以 R-9 的【禁止对象存在】，而【登记机制未定义】
⇒ 这一半是"规范有要求、实现无定义"，不是我凭空新增
```

**⇒ 修正后的三层：**

```text
第一层 · Basic L1 gate（共享，5 项）
  R-1..R-5

第二层 · C1 class rule（C1 专属，1 项）
  R-6

第三层 · 本设计【真正的】新增（2 项 + 1 项部分）
  R-7  writer 身份与实际执行主体的核对机制   ← 新增（冻结值已有，核对机制无）
  R-8  ❌ 撤回"新增"标注：§31 L1948-1949 已要求 execution_id/hash 为 provenance 必备
       ⇒ 应归入 gate 5 的具体化，不是新条件
  R-9  通路登记的【机制定义】               ← 部分新增（禁止对象已有，登记机制无）

约束项
  R-10 不得借用（禁止性）
```

**⇒ 于是"AuthorityGate 比 prereg 更严格"这个论断，也要收窄：**

```text
✗ 旧：因为 R-7/R-8/R-9 是新增的
✓ 新：真正超出 prereg 的只有 R-7（writer 实际核对）
      和 R-9 的【机制定义】部分
      R-8 属于 prereg 已有要求的具体化
```

**⇒ 而这一格的意义在于：**

```text
⇒ 上一版我把 R-1..R-6 平铺，读者会以为这六条都是 C1 的门槛
⇒ 实际上 R-1..R-5 是"入场券"，R-6 才是"C1 的名牌"
⇒ 而 R-7..R-9 是"本设计额外加的门"
⇒ 三者混淆会导致：把 gate 失败误读为"C1 不成立"
   ⇒ 而正确的读法是：gate 失败 ⇒ 连 class 都没到
   ⇒ 这与 G-11 / G-12（不得把 invalidity 写成 FAIL）直接相关
```

**⇒ 因此 §8 的负向测试矩阵也须按三层重排（见 §8.1 分层）。**

**⇒ 而 `R-7 / R-8 / R-9` 我必须标明它们是**本设计新增**，不在冻结 prereg 里。**
**⇒ 这意味着 `AuthorityGate = ESTABLISHED` 比 prereg 的 C1 更严格，不是相等。**

## 2.2b 第六轮自检：上面那段把职责搞反了

**第六轮自检时我问自己一个问题：AuthorityGate 的职责是判 C1，它凭什么去判 C2/C3？**

**⇒ 核 §13 L715 原文：**

```text
L715  "当 Basic L1 gate 通过后，L1 = PASS 仅在至少一个 evidence class
       被其自身规则独立建立时成立，且："
L718-724  if C3 ... else if C2 ... else if ... C1
```

**⇒ 这段是 `PRE_RESET_CHANGE_CLASS` 的赋值规则，属于 §13 的 gate 之后机制。**
**⇒ 原文没有说"AuthorityGate 来赋值"。**
**⇒ 而凌翼原话是「不得让 AuthorityGate **覆盖**这条优先级规则」——**

```text
"不得覆盖优先级" 的意思是：AuthorityGate 的结果不能顶替 class selection
而不是：让 AuthorityGate 去执行 class selection
```

**⇒ 所以 §2.2 我写的「AuthorityResult 必须携带 reported_pre_reset_change_class」是错的：**
**⇒ 那等于让 AuthorityGate 承担 §13 的 class 选择职责，与凌翼原意相反。**

**⇒ 改正为：**

```text
AuthorityResult 应当携带：
  · episode_specific_write_established = BOOL   ← C1 要素是否成立（AuthorityGate 的职责）
  · c1_evidence_element_scope          = "C1"   ← 明确这是 C1 层的判定结果

AuthorityResult【不】携带 reported_pre_reset_change_class。

⇒ class selection 由 §13 L715-725 的机制独立完成，输入是：
   · C1 要素成立与否（来自 AuthorityGate）
   · C2 是否独立成立（来自 §16 的判定，不由 AuthorityGate 做）
   · C3 是否独立成立（来自 §19-20 的判定，不由 AuthorityGate 做）
⇒ AuthorityGate 只提供其中一个输入。
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

## 4.3 我这一版**不能**说表一已闭合

```text
⇒ 我 v0.2 说"表一 · 权威消费边界（已设计）"
⇒ 凌翼判：方向接受，边界未闭合
⇒ 所以本版改为：表一有结构，但五个待明确项全部 NOT ESTABLISHED
⇒ 且我不声称"另设目录+账户+渠道"能防旁路
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

---

## 12.1 第六轮的上位错误：我把"不得覆盖"读成了"由它执行"

**第六轮自检时，我先问了一个问题：AuthorityGate 的职责是判 C1，它凭什么去判 C2/C3？**

**⇒ 然后我发现，我前面五轮一直在做一件与凌翼原意相反的事：**

```text
凌翼："不得让 AuthorityGate 覆盖这条优先级规则"
       ⇒ 意思是：AuthorityGate 的结果不能顶替 class selection
       ⇒ 即：AuthorityGate 应当【让位】

我做的：把 reported_pre_reset_change_class 写成 AuthorityResult 的字段
       ⇒ 意思是：AuthorityGate 输出最终 class
       ⇒ 即：AuthorityGate 【接管】了 class selection
```

**⇒ 差一个字：让位 vs 接管。而方向正好相反。**

**⇒ 这一格的错，比前五轮任何一处都重：**

```text
前几轮：引用错、范围错、漏写
本轮 ：我把规则的主体搞反了
      ⇒ 不是"哪一行写错了"
      ⇒ 是"这东西该由谁做"我理解反了
```

**⇒ 为什么我六轮才看出来：**

```text
因为"class 优先级"这句话看起来像是在描述一个判据
⇒ 而判据自然是"要判的东西"
⇒ 于是我不假思索地把它当成了 AuthorityGate 的判定点
⇒ 而它其实是一条【约束 AuthorityGate 不得越界】的规则
```

**⇒ 第六条教训（我自己加的）：**

> **一条规则说"不得覆盖 X"时，它约束的是主体的行为边界，不是给主体增加一项任务。**
> **把禁令读成职责，会造出一个恰好相反的机制。**

**⇒ 而这一格是我在自检时自己发现的——不是被别人指出的。**

---

## 12.2 本轮改动清单（第六轮）

| 位置 | 原 | 现 |
|---|---|---|
| §2.2 代码块 | `AuthorityResult` 携带 `reported_pre_reset_change_class` | **标注作废**，改为 §2.2b |
| §2.2b（新增） | —— | AuthorityGate 只带 `episode_specific_write_established` + `c1_evidence_element_scope`，**不**带最终 class |
| §1.1 G-10 行 | 判定性质 =「覆盖类（决定 reported class）」 | 改为「**让位类**：不执行此链，只输出 C1 要素」 |
| §1.1 G-10a..G-10d | 列为 AuthorityGate 判定点 | **改名为 X-1..X-4**，明确标注「非 AuthorityGate 判定点」 |
| §6.0 表三第 11 行 | 正式 class =「待定，按优先级」 | 改为「C1 要素成立（不等于最终 class = C1）」，并说明最终 class 由 §13 机制另赋 |
| §4.1b 五角色表 | 正式结果存储 = 「正式 C1 结论」 | 改为「C1 要素判定结果，不是最终 `PRE_RESET_CHANGE_CLASS`」 |
| §8.2 N-11..N-13 | `reported_pre_reset_change_class = C2/C3` | 改为「AuthorityGate 仍只报 C1 要素；最终 class 由 §13 机制赋为 C2/C3」 |

**⇒ 七处，全部同一根源。**
**⇒ 而这一根源就是：我没有分清「C1 要素是否成立」与「最终报告哪个 class」。**

---

## 12.3 六轮总账

| 轮 | 主查角度 | 发现数 | 最重的一处 |
|---|---|---|---|
| 1 | 字对不对 | 6 | `write_operator` 章节错（§5→§4） |
| 2 | 东西在不在 | 4 | 表三自相矛盾 + 三张表本体缺失 |
| 3 | 自相矛盾 | 15 | 9 个门禁项被丢弃（显示为"已解除"） |
| 4 | 交付是否齐 | 11 | `__init__.py` 不在冻结表 |
| 5 | 规则源头 | 9 | §16/§19-20 未映射（优先级是空话） |
| 6 | **职责归属** | 7 | **把"不得覆盖"读成"由它执行"** |

**⇒ 六轮，52 处。**

**⇒ 而每一轮查的深度都不同：**
```text
1-2 轮：文本层
3-4 轮：结构层
5 轮  ：规则依赖层
6 轮  ：职责归属层
```

**⇒ 我仍然不认为可以交了。**
**⇒ 下一轮（第七轮）我打算查：R-1..R-10 这十个条件，有没有哪一个其实【不属于】C1，而是被我硬塞进来的。**
**⇒ 因为这正是本轮发现的形状——上一轮我塞进了 class selection，这一轮要查还有没有别的。**
