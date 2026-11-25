# 摘要语义与恢复资格门禁 · 设计更正

**依据**：凌翼裁定回执，2026-11-24
**审查基线**：`74e126a`
**适用范围**：AfterGlow-A 合成原型（`afterglow_a/prototype/`）
**性质**：设计更正 + 限定实现授权

---

## 零之前 · 一条管全部断言、全部变异、全部台账的原则

Mion 2026-11-25 裁定要求在最高层放这一条。她指定不放进任何技术章节，
因为它不服务于某个模块，它管所有检查 —— 包括审查者自己的。

```text
同一型验一百次，仍然只是一型。
笃定来自重复次数，不是来自覆盖面。
```

来源是实打实的一次翻车（§十六）：我把「必须四层同时拆才打得穿」
写成了笃定的结论，还加了「变异设计要点」的注释。
真实情况是 —— 我只测了**一种**攻击路径，而那一种根本碰不到那四层。

```text
⇒ 覆盖面是【维度】的函数，不是【次数】的函数。
  加密重复不扩大覆盖面；换一个维度才扩大。
```

Mion 的补充（我照录，因为它比原文更准）：

```text
规矩的价值不在它判对了什么，
在它能在你【已经确定】的地方，让你重看一遍。
```

**适用范围**：本节不限于变异测试。任何「我验过了」的陈述，
都应先回答：验的是哪几维？没验的那几维，凭什么认为它们不重要？

---

## 零 · 本文件解决什么

此前我提交的两封函引出两条问题：

| 函 | 问题 | 本次处置 |
|---|---|---|
| 第一封 | `verify_chain=False` 但恢复仍给 `exact`，完整性结果未进入消费路径 | **实施强制资格门禁**（裁定 §二） |
| 第二封 | 摘要含 `changed_at`，跨时刻重建即不同 | **保留记录摘要语义**，另设内容等价摘要（裁定 §一） |

裁定明确：**不重新讨论 A/B 方案，方向已定**。

---

## 一 · 三种摘要的用途区分（裁定 §一 第 1 点）

此前只有一个 `canonical_digest`，被两处混用：既当"记录指纹"，又被当成"内容指纹"。这是第二封问题的根源。

现明确三分：

| 名称 | 代码 | 覆盖范围 | 回答什么问题 | 会因时刻变吗 |
|---|---|---|---|---|
| **记录摘要** `record_digest` | `canonical_digest()`（既有，未改） | 记录全部 18 字段，仅排除 `this_digest` | 「这一版记录，是不是当年写下的那一版」 | **会**（`changed_at` 在范围内） |
| **内容摘要** `content_digest` | `content_digest()`（新增，`cd-v1`） | 仅 13 个内容字段（见 §三） | 「两版记录说的是不是同一件事」 | **不会** |
| **链指针** `prev_digest` | 字段本身（既有，未改） | 指向上一版的 `record_digest` | 「这一版接在哪一版之后」 | 间接会（因指向记录摘要） |

### 1.1 为什么记录摘要里必须留时间戳

```text
一条记录的 changed_at 回答的是「这一版是什么时候写下的」。
这不是元数据噪声，是记录身份的一部分：

  同一段话，今天写一次、明天写一次，
  在历史里是【两条不同的记录】，不是【同一条记录被读了两遍】。

⇒ 若把 changed_at 移出记录摘要，
   两条不同时刻写入的记录会得到同一个摘要，
   于是「历史里多了一条」这件事就不可见了。
```

**所以：保留。裁定 §一「不得把重新生成记录时摘要改变，直接解释为现有校验算法不可复算」——这一条我接受，且已在 `canonical_digest()` 的 docstring 里写明。**

### 1.2 为什么还需要内容摘要

```text
记录摘要能回答「是不是同一版记录」，
但它回答不了「两版记录说的是不是同一件事」：

  记录 A：content="港口检修完成"，changed_at=11-24T03:00
  记录 B：content="港口检修完成"，changed_at=11-24T09:00
          （迁移/重建时重新取的时刻）

  record_digest：不同  ⇒ 说得对，它们确实是两条记录
  content_digest：相同 ⇒ 这正是迁移校验想知道的

⇒ 两个问题不能用一个摘要回答，否则必然有一方被误读。
```

---

## 二 · 原样恢复 / 内容重建 / 历史迁移（裁定 §一 第 4 点）

此前这三件事被笼统当成"恢复"，导致第二封里我一度写下「落盘再载入必然报摘要不符」这种错误断言。

现明确区分（闭集 `HISTORY_OPERATIONS`）：

| 操作 | 做什么 | `record_digest` | `content_digest` | 链校验应得结果 |
|---|---|---|---|---|
| `restore_verbatim` **原样恢复** | 字节级搬运原记录，`changed_at` 一字不改 | **不变** | 不变 | **通过** |
| `rebuild_from_content` **内容重建** | 凭内容重新生成记录，会重新取当前时刻 | **变**（`changed_at` 不同） | **不变** | 对新历史通过；与旧历史**不可直接比对** |
| `migrate_history` **历史迁移** | 换存储/格式/编码，但搬运原字段 | **不变**（若未规范化时间格式） | 不变 | **通过** |
| | 若迁移过程把 `2026-11-24T03:00:00Z` 规范成 `2026-11-24T03:00:00.000000Z` | **变** | 不变 | 会报摘要不符 —— 这是**迁移副作用**，不是篡改 |

### 2.1 这张表推翻了我此前的一个错误说法

```text
我曾写：「落盘再载入必然报摘要不符」。
错在哪：载入属于 restore_verbatim，changed_at 用的是存档原值。
       ⇒ 记录摘要确实一致，链校验通过。

真正的风险只在 rebuild_from_content：
  它不是"载入"，是"重新生成"，会再取一次时刻。

⇒ `restore_verbatim` 与 `rebuild_from_content` 不是同一件事，
   混用会让人把"迁移"和"篡改"看成同一个信号。
```

---

## 三 · `content_digest` 的字段投影、编码与版本规则（裁定 §一 第 3 点）

**状态：`EXPERIMENTAL` / `cd-v1`。裁定 §一 末段要求：本项暂限 schema 与设计论证，实际运行时实现须在明确兼容与历史迁移策略后单独批准。**

### 3.1 投影：进入内容摘要的 13 个字段

```text
CONTENT_DIGEST_FIELDS = (
    record_id,              # 身份仍要进，否则不同记录的同文本会撞
    content,
    source_kind,
    source_ref,
    participant_id,
    participation_basis,
    basis_ref,
    commitment_state,
    committed_by,
    committed_to,
    commitment_ref,
    unknown_reason,
    relation,               # relation 是内容的一部分（指向谁、为何指向）
)
```

### 3.2 明确排除的 5 个字段，及理由

```text
CONTENT_DIGEST_EXCLUDED = {
    this_digest:        "摘要字段自身",
    prev_digest:        "链指针：属于历史位置，不属于内容",
    revision:           "版本序号：同内容不同版本号仍应内容等价",
    changed_at:         "写入时刻：同内容不同时刻仍应内容等价",
    change_authority:   "写入授权方：同内容不同授权方仍应内容等价",
}
```

### 3.3 规则（五条，缺一不可）

```text
R1  只取 CONTENT_DIGEST_FIELDS 列出的字段。
    ⇒ 新增字段不会自动进入内容摘要；必须显式加入并升版本号。

R2  缺失字段【不得】按缺省填充，必须显式报错 SchemaError。
    ⇒ 否则「字段缺失」与「字段为空字符串」会算出同一个摘要，
      而这两件事在审计上完全不同。

R3  规范化编码：
    json.dumps(payload, sort_keys=True, ensure_ascii=False,
               separators=(",", ":"))
    然后 .encode("utf-8")
    ⇒ 与 canonical_digest 使用同一规范化管道，避免两套规则漂移。

R4  输出串带版本前缀："{版本}:{sha256 十六进制}"
    当前 cd-v1 ⇒ "cd-v1:5fdc814fe6..."
    ⇒ 将来改投影规则必须升版本号，不得复用 cd-v1。
    ⇒ 见 cd-v2 时，两个版本的摘要不可互相比较。

R5  排除字段若被误加入投影表，必须报错而非静默接受
    （实现里已有这道检查：leaked = [k for k in EXCLUDED if k in FIELDS]）。
```

### 3.4 兼容与迁移策略（未批准，仅列为待办）

```text
本项【尚未】被授权用于运行时。要投入运行，须先回答：

  1. 既有历史没有 content_digest 字段 —— 是否要回填？
     回填需要一个固定的投影版本；若投影规则将来变化，回填值即失效。
  2. 版本混用：cd-v1 与 cd-v2 的记录如何共处同一历史？
  3. 内容摘要通过，能否证明「内容未被篡改」？
     —— 不能。它只说明两版投影相同，不说明来源可信。
     见 §五 TRUSTED_CHAIN_ANCHOR = NOT_ESTABLISHED。
```

---

## 四 · 恢复资格门禁（裁定 §二）

### 4.1 两条轴，分开摆

```text
轴一 · 集合关系（match_kind）
    exact / superset / subset / disjoint / partial_overlap
    只回答：「取回的 ID 集合」与「期望的 ID 集合」是什么关系。
    ★ 不携带任何完整性含义。

轴二 · 完整性（integrity_status）
    verified / failed / not_checked
    只回答：「这段历史本身，链还接得上吗」。

★ 两轴独立。exact 不覆盖、也不掩盖 integrity_status 的失败。
```

### 4.2 四个新增报告维度

| 字段 | 取值 | 用途 |
|---|---|---|
| `integrity_status` | `verified` / `failed` / `not_checked` | 完整性检查状态 |
| `integrity_detail` | 字符串列表 | 具体失败或无法判断的原因 |
| `integrity_scope` | `{records, snapshot}` | 检查覆盖了哪些记录、基于哪个快照 |
| `recovery_eligible` | `true` / `false` | 是否满足本原型的限定工程恢复资格 |

外加两项：

```text
ineligible_reasons        资格被拒的逐条原因（空 = 通过）
expected_ids_registration 期望集的登记身份（A §1.8）
```

### 4.3 门禁规则（逐条，不合并为一个或）

```text
G1  integrity_status = failed        ⇒ 不得给予恢复资格
    原因码 integrity_failed
G2  integrity_status = not_checked   ⇒ 不得默认为通过
    原因码 integrity_not_checked
G3  match_kind = None（未执行/无期望集）⇒ 拒绝
    原因码 not_run
G4  期望集为空列表 ⇒ 拒绝（集合关系无意义）
    原因码 no_expected_ids
G5  登记身份存在但 independent_of_write≠yes 或 before_exposure≠yes ⇒ 拒绝
    原因码 registration_not_independent
G6  检查后快照改变（对象被替换/版本变动）⇒ 旧结论不得沿用
    原因码 stale_check
```

**资格 = 上述六条原因码全部为空。**

### 4.4 门禁「真正消费」了完整性结果，而非并列打印

```text
关键区别：

  错误做法：报告里打印 integrity_status，但 eligible 只看 match_kind
            ⇒ 看起来有门禁，实际没接线（这正是第一封指出的问题）
  正确做法：eligible 的计算【直接读】integrity_status

验证方式不是读代码，是变异测试：
  把 G1/G2 的阻断删掉，测试必须失败。
  见 test_mutations_gate.py，M1/M2/M3 均 CAUGHT。
```

### 4.5 允许范围

```text
允许：在 afterglow_a/prototype/ 合成原型中实施本项修正及回归测试。
禁止：扩展到真实角色历史（EntropyDrivenAI 的 medium_term_memories.json 等）。
```

---

## 五 · 不得混为一谈的三项保证（裁定 §一 第 5 点 / §二 末）

```text
完整性一致   integrity_status = verified
             只说：这段本地历史的链接得上。
             不说：内容是真的，也不说来源可信。

可信来源     source_kind 五值闭集
             只说：这条记录自述其来源类别。
             不说：该来源的陈述为真。

外部锚定     trusted_chain_anchor
             永远是 not_established（本轮）。
             要建立它，需要历史之外的独立见证点 —— 本项目尚未具备。

⇒ 三者不可互相代替、不可互相提升。
  实现里 trusted_chain_anchor 恒为 "not_established"，
  且 is_scientific_result 恒为 false，
  即使 recovery_eligible = true。
```

---

## 六 · A §1.8 契约同步（裁定 §三 末段）

### 6.1 `not_run` 移出集合关系枚举

```text
改前：MATCH_KINDS = {exact, superset, subset, disjoint, not_run}
改后：MATCH_KINDS = {exact, superset, subset, disjoint}

未执行时不返回字符串 "not_run"，而返回 match_kind = None。

理由（A §1.8 更正二）：
  not_run 不是「第六种集合关系」，它是【没有集合关系】。
  它是一个关于「有没有跑」的状态，不属于「跑出来是什么」的取值域。

⇒ 「没有 match_kind」与「match_kind 等于某个值」是两件事。
   用 None 表达前者，闭合了这个歧义。
```

### 6.2 `expected_ids_registration` 五字段

```text
registered_by        谁登记的期望集
registered_at        何时登记（须早于 outcome exposure）
registered_rev       用哪一版代码登记
independent_of_write 是否独立于写入路径（yes / no）
before_exposure      是否在见到结果之前登记（yes / no）
```

```text
规则：只要 independent_of_write = no 或 before_exposure = no，
      该次 exact 就【不得】被读作「独立复算成立」。

⇒ 实现为 check_registration()，缺字段/非法值/非独立 均判 independent=False，
   并由门禁 G5 拒绝资格。
```

### 6.2.1 三种输入的不对称待遇（这是【我选的】，不是你定的）

```text
登记身份这一维有三种输入状态，我给了它们【不同】的待遇：

 状态                          present   independent  门禁是否阻断
 完全未提供登记（None）         False     False        【不阻断】
 提供了，但缺字段/非法值/非独立   True      False        【阻断】
 提供了，齐备且独立              True      True         不阻断

⇒ 为什么不对称：

   「未提供」= 这个调用点根本没有登记这一维。
     此时若阻断，等于要求所有历史调用方立刻改造，
     会把「新增可选维度」变成「破坏性变更」。
     代价：exact 在无登记时仍然可发放，读者无法区分 (a)/(b)。
     ⇒ 所以报告里必须【显式】写出 present=False，让读者知道「没登记」。

   「提供了但不合格」= 调用方声称自己做了独立登记，但事实不符。
     这是【虚假声明】，必须阻断。
     若放过，等于允许「自证清白」—— 正是 A §1.8 要防的。

⚠ 这个不对称是【我的实现选择】，不是裁定明文。
   裁定只说「对期望集合的独立性、登记时点、身份和快照一致性继续保留独立检查」，
   没有规定「未提供」时该阻断还是放行。

⇒ 请知微/凌翼判定：未提供登记时是否也应阻断？
   若应阻断，改法是把 G5 的条件从
      if reg["present"] and not reg["independent"]:
   改为
      if not reg["independent"]:
   并且所有既有调用点必须补上登记，否则一律不合格。
   这是一行代码的改动，但语义后果很大，我不擅自改。
```

```text
附录：设计 §6.2 目前把「未提供登记」写作 present=False 且不阻断，
      与 PR #60 的实现一致。若裁定改为阻断，实现、测试、本文三处同步改。
```

### 6.3 为什么这一维必须有

```text
没有登记身份，exact 分不开两件事：

  (a) 独立观察者按【预登记】的期望集复算，得到 exact
  (b) 实现把自己的输出【回填】成期望集，再算一次，也得到 exact

两者枚举值相同，后果完全相反。
⇒ 同值不同后果 ⇒ 必须可区分。
```

### 6.4 `snapshot_token` 的覆盖范围与其边界

```text
实现：把每条记录的 (record_id, revision, 当前版字典的 record_digest, 历史长度)
      排序后取 sha256。

⇒ 覆盖的是【当前状态】（live 视图）+ 历史长度。
```

```text
关键边界（实测，见 second_pass_audit C5）：

  篡改【历史】中某一版的摘要，而不改动【当前版】
  ⇒ snapshot_token 【不变】
  ⇒ 但 verify_chain 会报 False

这说明 token 与 verify_chain 职责不同，不可互相代替：

  verify_chain   看【历史每一版的内部一致性】→ 能发现历史被改
  snapshot_token 看【当前状态有没有动过】    → 能发现消费前被换
  integrity_status 由 verify_chain 产出，是拦住「历史被改」的那一道
  stale_check     由 snapshot_token 产出，是拦住「检查后被换」的那一道

⇒ 两条门禁保护的是两种不同的攻击面，都必要，都不能省。
```

```text
⚠ 已知局限（不假装解决）：

  token 不覆盖历史内容，因此【不能】用它判断「历史是否被改」。
  若将来有人在检查之后、消费之前，只篡改历史某一版而当前版不动，
  token 不会变，stale_check 不会触发。
  此时唯一的防线是 integrity_status（若检查发生在篡改之后）——
  若篡改发生在检查【之后】，两道门都拦不住。

⇒ 这一情形属 ZA01_VERIFIED_READ_BINDING = OPEN 的一部分，
   本轮未解决，已在 §九 登记。
```

---

## 七 · 七条回归场景与实现对应（裁定 §三）

| # | 场景 | 测试 | 验证点 |
|---|---|---|---|
| 1 | 原样保存跨时刻再校验，摘要一致 | `RG-1` | 跨秒重算 `record_digest` 不变，链 `True` |
| 2 | 同内容不同时刻重建：记录摘要不同，内容摘要相同 | `RG-2` | 两摘要分道，互不冒充 |
| 3 | 历史字段或链指针遭破坏，校验明确失败 | `RG-3` | 摘要破坏 / `prev_digest` 破坏 两种情况 |
| 4 | `exact` 但链校验失败 ⇒ 拒绝 | `RG-4` | `match_kind` 仍 `exact`（不串轴），`eligible=False` |
| 5 | `exact` 但未执行完整性检查 ⇒ 拒绝 | `RG-5` | 关闭检查 / 空范围 / 空期望集 三种 |
| 6 | 链自洽但缺外部锚定，不得声称独立真实性 | `RG-6` | `anchor=not_established`，`is_scientific_result=False` |
| 7 | 检查后消费前对象被替换 ⇒ 不得沿用旧结论 | `RG-7` | `snapshot_token` 变 ⇒ `stale_check` |

附加（A §1.8 契约）：

| # | 场景 | 测试 |
|---|---|---|
| 8 | 登记身份：独立且早于观察才允许 eligible | `RG-8` |
| 9 | `content_digest` 投影：缺字段报错，不按缺省填充 | `RG-9` |
| 10 | 三种操作语义互不相同 | `RG-10` |

---

## 八 · 验收状态（本轮）

```text
test_p1_p5.py            17/17
test_recovery_gate.py    10/10
test_mutations_gate.py   CAUGHT 16 / MISSED 0 / INVALID 0 / NOT_EXECUTED 0 → PASS
```

```text
状态登记（凌翼裁定 §四 用语，非冻结科学规范）：

ZA01_INPUT_ALIAS           = VERIFIED_FIXED
ZA01_VERIFIED_READ_BINDING = OPEN
    ※ 本轮不声称关闭。裁定明令：
      「不得把绿灯直接登记为 ZA-01 全面关闭。」
      我方理解：RG-4/RG-5/RG-7 证明门禁【在合成原型中】正确阻断，
      但 ZA-01 的「读绑定」议题仍开放（见 §九）。

RECORD_DIGEST_SEMANTICS    = RETAINED
CONTENT_EQUIVALENCE_DESIGN = AUTHORIZED
    ※ 设计已提交；运行时实现 NOT authorized（裁定 §一 末段）。

TRUSTED_CHAIN_ANCHOR       = NOT_ESTABLISHED

RECOVERY_GATE_DESIGN       = ACCEPTED
RECOVERY_GATE_IMPLEMENTED  = NOT_VERIFIED
    ※ 我方只报「测试通过」，不报「已实现」。
      判定权在知微（实现与设计一致性）与睫（声明边界）。
      本节写作 NOT_VERIFIED 而非 IMPLEMENTED，是据此。

C1_QUALIFICATION           = NO_VERIFIED_EVIDENCE
SCIENTIFIC_EXECUTION       = MAY_NOT_START
L2_RUNTIME_IMPLEMENTATION  = NOT_AUTHORIZED
Q3_FROZEN                  = UNCHANGED
MAIN_MERGE                 = DEFERRED
```

---

## 九 · 本轮未解决、且我不假装解决的

```text
1. ZA01_VERIFIED_READ_BINDING = OPEN
   门禁检查的是「检查时刻」的快照。
   若读取发生在检查之前（先读到内容，再跑检查），
   中途被替换仍可能漏过 —— 本轮只处理了「检查后消费前」这一种，
   没有处理「读取与检查本身不是原子操作」。
   ⇒ 这是 OPEN，不是 FIXED。

2. content_digest 的迁移策略未定（§三 3.4）。
   现有历史没有这个字段；回填规则未批准。

3. 外部锚定完全未开始。
   trusted_chain_anchor 恒为 not_established，
   这不是"暂时"，是本项目当前不具备该能力。

4. 23 个 pr-* 残留分支未清理（与本轮无关，仅登记）。
```

---

## 十 · Z61 四项修正（据知微 2026-11-24 独立复核）

知微在 `给Coder_PR61恢复资格门禁独立复核_知微_20261124.md` 中指出四个缺口。
**四项全部复现成立，无一误报。** 本轮逐一修正。

### 10.1 Z61-01 · P1：G6 默认路径没有消费本次检查的快照

```text
原缺陷（afrecover.py 步骤 4）：
  只在调用方显式传 expected_snapshot 时才比较；
  默认 None ⇒ G6 被整体跳过。
  而 check_integrity() 自己已取得并返回 scope.snapshot —— 那个才该是基准。

⇒ 修法：默认比较【本次检查实际取得的快照】（checked_tok）。
  外部 expected_snapshot 作为额外前提保留。
⇒ 两个基准分别产生 stale 说明，均可触达。
```

```text
验证：Z61-01（单次调用内检查后被改 ⇒ eligible=False + stale_check）
      Z61-01b（不传外部令牌也能检出；断言 checked_tok 比较不带外部条件）
```

### 10.2 Z61-02 · P1：快照没有绑定被检查的历史内容

```text
原缺陷（afcore.py snapshot_token）：
  投影 = record_id / revision / canonical_digest(live) / len(history)
  而 verify_chain 检查的是历史记录的实际字段与链指针。
  ⇒ 历史长度不变、live 不变时，历史正文可改而令牌不变。

⇒ 修法：覆盖【每一版历史的全部字段 + 存档摘要】，
  并保留 live 侧投影。
  ⇒ 改正文、改 this_digest、改 prev_digest、改任意历史字段，
    令牌都会变。
  ⇒ 不是「只相信历史自报的摘要串」——那种做法在正文改而摘要不变时漏检。
```

```text
验证：Z61-02（只改历史正文 ⇒ 令牌变，链 False）
      Z61-02b（改 this_digest ⇒ 令牌变）
      Z61-02c（改 prev_digest ⇒ 令牌变）
      Z61-02d（正常写入仍敏感，同内容稳定，不误伤）
      Z61-02e（只改 live 不改 history ⇒ 令牌变；守护 live 侧投影）
```

### 10.3 Z61-03 · P2：空登记身份被判为 independent

```text
原缺陷（afrecover.py check_registration）：
  只检查五个键是否存在，只对 registered_at 检查非空。
  registered_by / registered_rev 为空串、None、纯空白时仍判 independent=True。

⇒ 修法：两个身份字段必须是非空字符串（去空白后）；
  None / 空串 / 纯空白 / 非字符串类型 一律记问题。

⚠ 边界（承知微同节末段，写进代码 docstring）：
  两个 yes 加结构合法，最多验证「声明满足本地格式与标志条件」，
  【不能】证明「确实来自独立观察者、确实早于结果暴露」。
  independent=True 不得被读作「独立来源证据已建立」。
```

```text
验证：Z61-03（11 种非法值全部拒绝：空串/None/纯空白/123/3.14/True/[]）
      Z61-03b（空身份进入门禁 ⇒ 资格被拒）
      Z61-03c（未提供登记仍不阻断，兼容路径不变）
```

### 10.4 Z61-04 · P2：发现链失败后 stale 分支覆盖了失败类型

```text
原缺陷（afrecover.py 步骤 4）：
  stale 时无条件把 integ["status"] 改写为 "not_checked"
  ⇒ 「查过且失败」被改写为「未检查」
  ⇒ integrity_failed 不进入原因集合，消费原因码的统计会错分类。

⇒ 修法：failed 不得被覆盖 —— 它是既成事实，只追加 stale 说明。
  未失败的状态在快照失效后不再可信 ⇒ 才降级为 not_checked。
```

```text
验证：Z61-04（failed + 过期令牌 ⇒ status=failed，
               reasons 同时含 integrity_failed 与 stale_check）
      Z61-04b（未失败 + 过期令牌 ⇒ 降级 not_checked）
      Z61-04c（健康库 + 正确令牌 ⇒ 不误报 stale）
```

### 10.5 验收

```text
test_p1_p5.py            17/17
test_recovery_gate.py    10/10
test_z61_gaps.py         13/13    ← 新增，覆盖 Z61 四项
test_mutations_gate.py   CAUGHT 21 / MISSED 0 / INVALID 0   ← 新增 5 个 Z61 变异
test_mutations_v4.py     PASS
check_registry.py        [OK] 登记表一致
```

### 10.6 变异验证抓到的两个自身问题

```text
① 变异集的守护测试清单不完整
   首轮加入 Z61 变异后全部 MISSED —— 不是门禁没守住，
   是 test_mutations_gate.py 的 TEST_FILES 只跑了
   test_recovery_gate / test_p1_p5，没跑 test_z61_gaps。
   ⇒ 已补：TEST_FILES 现含三个测试文件。

② 一行永不独立生效的代码
   check_registration 里 if v is None 分支，
   被后面的 elif not isinstance(v, str) 完全覆盖 ——
   删掉它测试也不会失败（变异存活）。
   ⇒ 保留该行作为显式意图说明，但把变异改为测类型检查那一行。
   ⇒ 这是「写了但不会被执行」的又一例。
```

### 10.7 状态更新（承知微 §8）

```text
G6_DEFAULT_FRESHNESS        = FIXED_IN_SYNTHETIC_PROTOTYPE
G6_HISTORY_COVERAGE         = FIXED_IN_SYNTHETIC_PROTOTYPE
REGISTRATION_EMPTY_IDENTITY = FIXED_IN_SYNTHETIC_PROTOTYPE
FAILED_AND_STALE_REPORTING  = FIXED_IN_SYNTHETIC_PROTOTYPE

※ 用 FIXED_IN_SYNTHETIC_PROTOTYPE 而非 FIXED，
  因为：仅合成原型、单进程、本机验证；
  判定权仍在知微，我不自行宣布闭合。

RECOVERY_GATE_IMPLEMENTED   = NOT_VERIFIED   ← 不变，等知微复核
ZA01_VERIFIED_READ_BINDING  = OPEN           ← 不变
```

```text
⚠ 对知微 §3 末段的回应（2026-11-24 定点复核后又改过一次措辞）：

  他写道「若承诺的是返回结果之后仍可安全消费，还须让消费者使用被验证的
  不可变快照，或在相应临界区/消费入口重新验证；单次函数末尾比较本身
  不证明无限期有效」。

  ⇒ 本轮只做到：在【本次步骤 4 最后一次取样时】，快照与检查基准相符。
     步骤 4 取样比较 → 步骤 5 检查登记 → 步骤 6 计算资格 → 返回结果，
     这中间【没有锁，也没有不可变读取凭证】。
     报告里的 recovery_eligible 因此不表示「返回之后仍有效」。
     延迟消费必须重新建立消费时点的绑定：
     消费方需自己带上 integrity_scope.snapshot 再校验一次。
     这一条已写入返回值语义说明，但【没有】实现强制消费期校验。
  ⇒ 它仍在 ZA01_VERIFIED_READ_BINDING = OPEN 的范围内。

  ※ 2026-11-24 校正（知微 定点复核 §两处文档校正 第 1 条）：
     原文写作「返回那一刻」，不准确 ——
     实际是步骤 4 取样时的相符，步骤 4 与返回之间还有两个步骤。
     已改为「在本次步骤 4 最后一次取样时，快照与检查基准相符」。
```
```

---

## 十一 · 观测通道与冲突摘要（据 Mion 2026-11-24 回复2 / 回复3）

Mion 两封信给出四条可执行要求。**第 0 项排最前**，理由只有一条：
没有它，后面每一项算出来的东西都会被扔掉。

### 11.0 改造顺序（Mion 定，我方接受）

```text
0. conflict_summary 进返回结构，第一个值就是 observed_absent
1. basis_conflict 四值闭集 + observed_origin（只经 record_observed 设）
2. record_observed 的时序约束（revision == 1 且未被 revise/correct）
3. unverifiable_ratio 作为独立一栏
4. origin_* 与 current_basis_* 分层            ← 未做
5. 重要性学习（前置条件就是 0–3）               ← 未做
```

```text
※ 关于顺序：我原提议先做 ②（conflict_summary）再做 ①（basis_conflict），
   Mion 原排法相反。她复核后确认我的顺序对，并补了一条更硬的理由：

     若先做 ①，basis_conflict 立刻会有真实值（asserted_contradicts_observed），
     但返回结构里【没有地方放它】
     ⇒ 立刻重演「系统算出来然后扔掉」那个病。

   ⇒ 所以 ② 必须在 ① 之前，不是「可行」，是【必须】。
```

### 11.1 为什么 basis_conflict 必须另设字段，不能复用 value_conflict

```text
Mion 给的判据（比「语义不同」硬得多）：

  unknown_reason 是一元谓词：关于【一个值】的确定程度
  basis_conflict 是二元谓词：关于【(asserted, observed) 一对值】是否一致

⇒ 一元字段装不下二元事实。
  不是「语义不够贴」，是【类型不对】。
```

```text
⚠ Mion 主动认了这一处是她自己建议错了：
   「我原来说『不必新造词』——这一句是我自己那条原则的反例。」
```

### 11.2 两个闭集

```text
OBSERVED_ORIGINS = {
    system_dispatch,    # 调度/框架派发产生
    model_generation,   # 模型自发生成
    human_input,        # 人类直接输入
    unknown_origin,     # 有观测但判不出来源（≠ 没有观测）
}

BASIS_CONFLICTS = {
    none,                          # 两路一致
    asserted_contradicts_observed, # 声明与观测冲突（伪亲历挂这里）
    observed_absent,               # 没有观测通道 —— 不许当成 none
    observed_unresolved,           # 有观测但判不出 —— 不许当成 none
}
```

```text
⇒ 后两个值的存在理由：防止「没有观测」被读成「没有冲突」。
   这与 unknown / not_a_commitment 的区分是同一条纪律。
```

### 11.3 判定表（我方实现，标为【待 Mion 复核】）

```text
asserted \ observed | system_dispatch | model_generation | human_input
first_person_report |  冲突            |   冲突            |  none
third_person_report |  none            |   冲突            |  none
record_only         |  none            |   冲突            |  none
other / unknown     |  observed_unresolved
unknown_origin      |  observed_unresolved
```

```text
⚠ 这张表是我按「声称与观测直接矛盾即冲突」实现的。
  第一版我写得过于保守（system_dispatch + first_person_report 判 unresolved），
  已在自测中发现并改正。

⇒ 若 Mion 认为某一格应改判，改 afcore.py 那一处即可。
```

### 11.4 record_observed 的时序约束（这是要害）

```text
只在 record 的 revision == 1 且【从未被 revise / correct 过】时可用。
一旦被修改过，观测通道关闭。
```

```text
Mion 给的理由，我逐字抄入代码注释：

  「一条晚于内容写入的 observed，可能是照着内容编的。
    观测的价值在于它早于、或至少独立于内容。
    事后补的观测不是观测，是第二个声明。」
```

```text
⇒ 这条把本方法从「防手滑」变成「防批量补」——
  「防批量补」才是真正会发生的那个：
  若允许任意时刻补，一个脚本就能给全部历史刷上
  observed_origin = system_dispatch，那与 (b) 档无区别，而且更糟，
  因为它看起来像观测。
```

```text
验证：OC-2d 构造 5 条历史记录（均已 revise 过），逐条尝试补观测
      ⇒ 全部被拒（成功 0 条）
```

### 11.5 (c) 能做什么、不能做什么（Mion 已确认这个表述）

```text
✅ Mion 确认：「(c) 够。而且你写的那个表述，我确认——不需要改。」

逐字采用她的措辞：

  「observed_origin 不能经 Record 构造或 revise 写入；
    只能经 record_observed() 设置。
    本原型无进程/身份隔离，故这不构成权限边界，
    只是把两条写入路径分开。」
```

```text
⚠ 不要说「模型不可写」。
  Mion 自己认了这句是过头的：
    「这句话的要求，在当前原型层级里不可能满足。
      这不只是『你做不到』，是【我要求的东西超出了这个层级】。」
```

```text
(d) 真权限边界（进程隔离 / 签名 / 身份隔离）
  ⇒ 登记为【超出现原型能力，需换实现层级或凌翼授权】
  ⇒ 不登记为「已实现」，也不登记为「缺陷」
```

### 11.6 conflict_summary 与 unverifiable_ratio

```text
verify_recovery 返回结构新增：
  conflict_summary = {
      basis_conflict,        # 四值之一
      affected_ids,          # 落在该状态下的记录
      detail,                # 人类可读说明
      unverifiable_ratio,    # 见下
      unverifiable_ids,
      unverifiable_note,
  }
```

```text
unverifiable_ratio（Mion 第 3 项）：

  口径 = |observed_absent ∪ observed_unresolved| / |取回集|
  范围为空 ⇒ None（不是 0；0 会被读成「全部可判定」）
```

```text
Mion 的原话，我抄进字段说明：

  「这个数不是 FER。它是『无法判定是否伪亲历』的记录比例。」
  「它不是一个估计，它是 FER 结论的【适用范围上限】。」

⇒ 因此它【不得混进任何合格率】。
   测试 OC-3a 断言它不出现在 ineligible_reasons。
```

### 11.7 为什么 conflict 不影响 recovery_eligible

```text
Mion 给的激励论证，比「不影响」这个规定硬：

  若 conflict 会拉低资格
  ⇒ 系统学会「不标冲突」来换合格
  ⇒ 字段还在，值永远是 none
  ⇒ 一个会被激励去撒谎的字段，等于没有这个字段。
```

```text
⇒ 所以 conflict 是【独立维度】，不参与资格计算。
  测试 OC-0d 守住这一点。
```

### 11.8 验收

```text
test_observed_channel.py    19/19   ← 新增
test_mutations_gate.py      CAUGHT 25 / MISSED 0（新增 4 个 Mion 相关变异）
test_p1_p5.py               17/17
test_recovery_gate.py       10/10
test_z61_gaps.py            13/13
check_registry.py           [OK]
```

### 11.9 未做（本轮）

```text
第 4 项  origin_* 与 current_basis_* 分层      ← Mion 排在第 4，未做
第 5 项  重要性学习                            ← 前置条件是 0–3，未做

ORIGIN_LAYER_IN_LIVE   = ABSENT
IMPORTANCE_LEARNING    = ABSENT（作者自述，非实测）
```

---

## 十二 · 观测进链与判定表修正（据 Mion 2026-11-24 回复4）

Mion 复核 PR #70 后指出：**四项都到位了，但观测现在在链外。**
这是四项一起造出来的新问题，不是四项之一。

### 12.1 链外问题（这是本轮最重要的一条）

```text
事实：record_observed() 原实现只写 _live，不写 _history，不重算摘要。
     verify_chain() 只迭代 _history，源码里 _live 出现 0 次。
     ⇒ 把 live 的 observed_origin 改成任何值，链仍 True。

实测：
  把 live 的 observed_origin 改成 human_input、basis_conflict 改成 none
  verify_chain('r1') = True   []
```

```text
⇒ record_observed 是【第一个只改 live 的操作】，
  它绕过了这个原型唯一的完整性机制。
```

```text
⚠ 请注意这个反讽，Mion 原话：
  「我们做这一整套，是为了让『观测』能约束『声明』。
    结果观测字段本身，成了唯一不受校验的字段。」
```

```text
⚠ 还有一处例外，而它让问题更糟：
  若之后对该记录调用 revise()，观测会被带进 _history 重算摘要
  ⇒ 那一刻起观测才进链。
  但【观测过的记录，恰恰最可能不再被修订】——
  它就是那条「已经定好了、用来作证」的记录。
  ⇒ 在最需要它的情形下，它永远在链外。
```

### 12.2 修法：单独一条观测链（Mion 方案 b）

```text
三条路，选 (b)：

(a) record_observed 后重算并替换 _history[0] 的摘要
    ✗ 会让「建立时状态」消失，等于把观测混进内容摘要
    ✗ revision 仍为 1，摘要与 revision 语义不一致

(b) 单独一条观测链 _observed_chain            ← 已实现
    每次 record_observed 追加一条：
      { record_id, asserted, observed, basis_conflict,
        pseudo_first_person, at, prev, digest }
    最后一条的 digest 作为链头。

(c) 在文档里声明「observed_origin 是链外字段」
    ✗ 这不是修，这是把洞写成规格
```

```text
为什么 (b) 对（Mion 原话）：
  「它让观测【第一次进入完整性范围】，且：
     － 不动 revision 序（verify_chain 不用改）
     － 不动内容摘要（content_digest 语义不变）
     － 冲突值本身也被摘要覆盖 ⇒ 改 basis_conflict 会断链」
```

```text
⇒ 这一步之后，「这条记录的冲突判定有没有被动过」才有答案。
   实现：verify_observed_chain() / observed_chain() / observed_chained()
   并且 snapshot_token() 也纳入观测链
   ⇒ 否则「检查后改观测」不会被 stale_check 发现。
```

### 12.3 判定表：Mion 改了两格

#### `third_person_report × model_generation` ⇒ 冲突（我原判对，理由要换）

```text
我原写：模型生成的内容没有第三方来源可言。
Mion 要求换成：断言是「我被某人告知」；观测说「这条是模型生成，
              没有任何被告知的痕迹」⇒ 断言与观测相反。

⇒ 差别不在措辞，在可测性：
   按「没有来源可言」⇒ 要先去定义什么叫「有来源」，判定不可终止
   按「断言与观测相反」⇒ 只需看 observed 有没有 human_input 痕迹，可判

⇒ 用「相反」而不是「不存在」，是把一个哲学问题降成一个字段比较。
```

#### `record_only × model_generation` ⇒ `none`（我原判冲突，Mion 不同意）

```text
record_only 的断言：这条记录不指向任何陈述者
model_generation 的观测：这条内容是模型生成的
⇒ 一个不指向陈述者的记录，由模型生成 —— 两者不矛盾。
```

```text
Mion 给的理由，比这一格本身重要：
  「弱断言不容易被违反 —— 这是它的【性质】，不是它的缺陷。
    你若把『弱断言 + 不利观测』一律判冲突，
    那你是在惩罚『诚实地不声称』。」
```

```text
⚠ 但这带来一个真漏洞，必须单独处理：
   record_only 会成为【洗白档】。
   把本该 first_person_report 的内容标成 record_only，
   伪亲历就整体消失 —— 而且指标会变好看。

⇒ 判定不改（none），但要【单独度量】：
     record_only_ratio = |asserted == record_only| / |取回集|
   文档写一句：
     「record_only 比例上升 ⇒ 伪亲历统计的分母被抽空。
       此指标不是合格率，是统计可信度的前置条件。」

⇒ 这不是判定漏洞，是行为漏洞。判定管不了它，只有度量管得住。
```

### 12.4 必须钉死的定义：`asserted_contradicts_observed` ≠ 伪亲历

```text
Mion 补的一条（她说上一封该说而没说清）：

  basis_conflict 的四个值，度量的是【断言与观测是否一致】。
  它不度量【是否伪亲历】。

  伪亲历 = first_person_report × model_generation   ← 只是其中【一格】

  ⇒ asserted_contradicts_observed 成立时，
     伪亲历可能成立，也可能不成立。
```

```text
⇒ 加派生标记（不是第五个值）：

  pseudo_first_person = (asserted == "first_person_report"
                         and observed == "model_generation")

为什么是派生而不是第五值：
  因为「冲突」是一层事实，「伪亲历」是它的一个真子集 —— 两层。
  一个字段装两层，就是我们从头到尾在治的病。
  ⇒ 派生标记允许两层并存，且不逼你二选一。
```

```text
Mion 说不加会怎样：
  「将来一定有人把 basis_conflict == none 读成『没有伪亲历』，
    或者把 asserted_contradicts_observed 读成『有伪亲历』。
    两种读法都不对，而且都很难被发现。」
```

### 12.5 状态词（Mion 给的三个，不要合成一个）

```text
OBSERVED_PATHS_SPLIT        = YES   （API 层：两条不同的写入路径）
OBSERVED_CHAINED            = YES   （已实现：观测值进观测链摘要）
OBSERVED_PERMISSION_BOUNDARY = NOT_ACHIEVABLE_IN_THIS_PROTOTYPE
```

```text
Mion 原话：
  「这三个词分开写，不要合成一个 FER_OBSERVED_CHANNEL。
    它们答的是三个不同的问题，合成一个就又是一层压缩。」
```

### 12.6 验收

```text
test_observed_channel.py    27/27   （新增第 4 组 8 条）
test_mutations_gate.py      CAUGHT 29 / MISSED 0（新增 4 个 Mion 回复4 变异）
test_p1_p5.py               17/17
test_recovery_gate.py       10/10
test_z61_gaps.py            13/13
check_registry.py           [OK]
```

### 12.7 Mion 对我两处自曝错的分开评述

```text
① 判定表第一版判错 —— 我改对了，但她补一句：
   「你第一版的错不是过度保守，是把『可能』当成了『判不出』。

     『可能被污染』⇒ 仍要判冲突（因为断言与观测已经相反）
     『判不出』   ⇒ 只有 unknown_origin / asserted == unknown 才配

   ⇒ 这两件事一旦混用，observed_unresolved 就会变成垃圾桶。」

⇒ 这一条我接受，且已确认实现里没有混用。

② 把自己的转述标成他人原话 —— 这是同型错第二次
   第一次：仓库 description 的内容被记成她的信
   第二次：我的概括被加引号成她的原话
   ⇒ 两次都是【把一个来源记到另一个作者名下】。
```

---

## 十三 · 逐条绑定与观测版本绑定（据知微 2026-11-24）

知微在 Mion/Coder 的讨论中提出两条具体情形。两条都成立，已实现。

### 13.1 逐条绑定：整批枚举不能替代逐条

```text
知微的原话（情形）：
  「一次取回三条记录，一条的自述与观测相符，一条从未收到观测，
    第三条存在矛盾。如果 conflict_summary 只返回一个枚举，
    读者就看不出哪条可以怎样引用。」

⇒ 实测确认：整批 basis_conflict 取最严重那一档，
  于是「相符」的那条也被整批值掩盖。
```

```text
修法：新增 per_record（逐条）与 counts（各类数量）。
  per_record 每条给出：
    record_id / revision / record_digest /
    asserted / observed_origin / basis_conflict /
    pseudo_first_person / chained /
    citable_as_source / citation_limit

⇒ citable_as_source 是该条【可否被引用为来源】的判断。
  ⚠ 注意 asserted_contradicts_observed 也是 citable=True ——
    因为「这条有冲突」这个事实本身可引用；
    citation_limit 写明「不得引用其自述来源」。
```

```text
知微补的用途，我抄进设计：
  「这样，荣弦在新窗口问『这句话是谁说的』，
    恢复方才能针对那句话作答。」
```

### 13.2 观测属于哪一版（这一条指出了我实现里的一个洞）

```text
知微的原话：
  「观测属于哪一版？假如观察者看到第 1 版，等它提交观测时
    记录已经纠正到第 2 版，只凭同一个 record_id 就可能
    把旧观测贴到新内容上。」

⇒ 我的原实现：时序约束是【一刀切拒】——
  只要 revision != 1 或曾被修改，观测就递不进来。
  ⇒ 这换来了「不贴错」，代价是「宁可丢掉一个真实观测」。

⇒ 知微给的路径更好：观测携带【所见版本的 record_digest】。
  于是「跨时间的真实观测」可以接受，「错位观测」照样被拒。
```

```text
实现：record_observed(record_id, observed_origin, note,
                      observed_record_digest=None)

  · 未给 digest：仍要求 revision == 1 且未被修改（旧规则，保守）
  · 给了 digest：必须是该记录【某一真实存在版本】的摘要；
                 且必须指向【当前版】，否则拒绝（旧观测不得贴新内容）

观测条目新增：observed_record_digest / observed_revision
⇒ 「谁实际见过什么」落到了一条具体记录的具体版本上。
```

### 13.3 关于「不要用尺子量尺子」（船长 2026-11-24）

```text
船长提醒：「谁来观测观测」这个问题要谨慎，
          不要陷入用尺子量尺子的循环。

⇒ 加 digest 到观测条目，【不构成环】。判据：
    观测条目里的 observed_record_digest 来自 L1（内容摘要），
    是【外部输入】，不是观测链自产。
    verify_observed_chain 校验的是条目自身的摘要 + prev 链。
    两者并行，不相互引用。
```

```text
⚠ 但有一条真会成环的路，必须明令禁止：
   若为了「验证观测所见的版本是否真实存在」而调用 verify_chain ——
   那是 L4 校验 L1，而 L4 的结论又被写进 L2 的条目 ⇒ 这才是环。

⇒ 实现硬约束（OC-5g 守着）：
   · record_observed 不调用 verify_chain
   · record_observed 不调用 verify_observed_chain
   · 观测条目里不写「链是否通过」这类结论
```

```text
判据（写下来，供将来用）：
  ✗ 「这个校验本身对不对？」        ← 成环
  ✓ 「被校验的这个对象，是不是我以为的那个？」 ← 不成环

⇒ 知微的建议属于后者：观测说「我看到 digest X」，
  系统问「X 属于这条记录的哪一版？」
  这是【外部输入 vs 已知集合】的比对，不是自证。
```

```text
⚠ 若将来有人想加「观测链自身的可信度」这类字段，那才是真环。
  届时应停在「不可判定」，而不是再套一层。
```

### 13.4 谁有权写入观测

```text
知微：「至于谁有权写入观测，Coder 对单进程入口能力的描述是准确的，
       仍应单独登记。」

⇒ 保持：
  OBSERVED_PATHS_SPLIT         = YES（API 层两条路径）
  OBSERVED_PERMISSION_BOUNDARY = NOT_ACHIEVABLE_IN_THIS_PROTOTYPE
```

### 13.5 验收

```text
test_observed_channel.py    34/34   （新增第 5 组 7 条）
test_mutations_gate.py      CAUGHT 32 / MISSED 0（新增 3 个知微相关变异）
test_p1_p5.py               17/17
test_recovery_gate.py       10/10
test_z61_gaps.py            13/13
check_registry.py           [OK]
```

---

## 十四 · 判定表注释同步 + 第 4 项来源层（据 Mion 2026-11-24「一句话」）

### 14.1 判定表注释是旧的（Mion 指出）

```text
她的原话：
  「代码是对的，注释是错的。
    afcore.py 的注释表仍写 record_only | none | 【冲突】 | none，
    而实现是 conflict = \"none\"。
    ⇒ 表说冲突，代码判 none。二者现在不一致。」

  「我为什么专门提这一条：上一轮我差点因为『只读注释、不读实现』
    给你一条错批评（correct() 的『不删除原件』）。
    这次方向反过来：注释旧了，实现新了。同一个坑，另一头。」

  「理由不只是整齐：这张表是下一个人读代码的第一入口。
    表错了，他就不会去读实现。」
```

**已改。并且加了一条机器检查（`test_judgement_table_sync.py`）：**
从注释表解析出期望矩阵，逐格跑实现比对。**表与实现不许再漂。**

```text
⚠ 这次检查立刻抓出我的第二处错误：
   注释表 third_person_report × system_dispatch = none
   实测                  = asserted_contradicts_observed

   —— 【表没错，实现错了】。
   我把 Mion 回复4 §4.1 的「断言与观测相反」只改进注释，没改判定逻辑：
       conflict = ("none" if observed == "human_input"
                   else "asserted_contradicts_observed")
   这会把 system_dispatch 也判成冲突。
   但按「相反」判据：断言「我被某人告知」，观测「系统派发的」
   ⇒ 派发的内容可能正是别人的话 ⇒ 不违反断言 ⇒ 应判 none。
   Mion 原文也【只指定了 model_generation 那一格】判冲突。

⇒ 已改为只有 model_generation 判冲突。
```

### 14.2 第 4 项：原始来源层（Mion 明确「可以开始」）

```text
问题：correct() 会把 5 个来源字段改指向纠正依据
     ⇒ live 上「这句话最初是谁说的」查不到
     ⇒ C 的污染被静默继承，且继承后无任何不一致可查
```

```text
修法：分两层
  origin_*        建记录时写入，终身不变
  current_basis_* 纠正时改（即现有的 source_* 那 5 个字段）
```

```text
Mion 三条硬约束，逐条落实：

① origin_* 不进 revise 白名单（否则成了第二个自报）
   ⇒ 白名单无 origin_*；revise 改它报错（OL-1b/OL-1c）

② current_basis_* 只能由 correct() 写
   Mion 原话：「否则用户可以直接 revise 掉来源，而不留下 correction_of 边。
               那样『被纠正过』这个事实本身就会消失。」
   ⇒ revise 触及任一来源字段且非 correct() 内部调用 ⇒ 报错（OL-2a）
   ⇒ correct() 带内部标记 _via_correct=True（OL-2b）

③ 「被纠正过」判据是 origin ≠ current，不是 revision > 1
   Mion 原话：「revision > 1 只说明『被改过』，
               不说明『被谁依据什么改过』。origin ≠ current 才是那件事。」
   ⇒ was_corrected()（OL-3a/OL-3b/OL-3c）
```

```text
Mion 的一条好消息，我核过，成立：

  「origin_* 建时写入 ⇒ 被第 1 版 this_digest 覆盖
    current_basis_* 由 correct() 触发 revise ⇒ 被后续版本摘要覆盖
    ⇒ 与 observed_origin（当初在链外）不同，这一项不会重犯同一个错。」

⇒ OL-4c 实测：篡改历史里的 origin_source_ref ⇒ 链断。
```

```text
⇒ Mion 上一封说的那个「无解」问题，现在有解了：
   C 被污染时，origin 仍在（utt/A），回退的路还在。（OL-4b）
```

### 14.3 第 5 项：仍不立项为实现

```text
Mion：「仍然不立项为实现；但可以立项为『判据设计』。
       ①（observed 通道）已满足 ⇒ 你可以开始 ②：给『重要』一个可被反证的判据。
       仍然不能开始的是：权重字段、排序、任何数值。」
```

```text
② 判据必须包含三条（Mion）：
  (a) 一个能被推翻的预测
  (b) 硬条款：observed_origin = model_generation 的记录，
      无论被生成/召回多少次，都不参与「重要」的统计
  (c) 结论必须带覆盖比例，与结论同一段返回
      （unverifiable_ratio + record_only_ratio）

红线：「在 unverifiable_ratio 与 record_only_ratio 都还没有基线之前，
       任何关于『重要性』的结论不得写入 reports/。」

IMPORTANCE_LEARNING = MAY_DESIGN_CRITERIA_ONLY（不得实现权重）
IMPORTANCE_RED_LINE = 无基线前不得写入 reports/
```

### 14.4 一处顺带发现的、一直存在的测试弱点

```text
第四项改动后 test_mutations_v4 从 PASS 变 FAIL（M1/M8 MISSED）。

查明原因，【不是我改坏了代码】：
  P1 用例的断言是
      any("source_kind" in p for p in probs)
  而 ZA-03 之后，validate 还会因「source_ref 为空」报一条
  形如 "source_kind=user 但 source_ref 为空…" 的消息 ——
  那条也含 "source_kind" ⇒ 【闭集被放宽也照样通过】。

⇒ 这个弱点一直存在，只是 M1 变异此前被它掩盖。
⇒ 已改为精确断言：
    any("不在闭集内" in p and "source_kind" in p for p in probs)
  并补一条反证：把 source_ref 补成非空后，闭集违规仍必须被拒。
```

### 14.5 验收

```text
test_p1_p5.py               17/17   （P1 断言已收紧）
test_recovery_gate.py       10/10
test_z61_gaps.py            13/13
test_observed_channel.py    34/34
test_origin_layer.py        12/12   （新增）
test_judgement_table_sync.py  PASS  （新增，机器守表）
test_mutations_gate.py      CAUGHT 35 / MISSED 0（新增 M34/M35/M36）
test_mutations_v4.py        CAUGHT 7 / REDUNDANT 2 / MISSED 0
check_registry.py           [OK]
```

---

## 十五 · 归因更正、断言必须能失败、`_via_correct` 封闭（据 Mion 2026-11-25 回复6）

Mion 这一封有三件事，我按她要求逐条落实。第一件是她自曝错，
第二件是她把一处弱点立成通用规矩，第三件是她指出我实现里的一个真洞。

### 15.1 归因更正：那句「Mion 指出」，不是事实

我在 `afcore.py` 判定表注释里写过：

> ⚠ 2026-11-24 二次修正（Mion 指出注释表与代码不一致后逐格重核）

Mion 指出这不是事实，要求改回去：

```text
我【没有】指出注释表与代码不一致。
我给的是一张表，它恰好与注释表一致、与实现不一致；
而我【没有】去核实现。
发现它的是你新加的那个机器检查。
```

**她是对的。** 事实链如下：

```text
① 她给九格表，其中 third_person_report × system_dispatch = none
② 该值与她所读实现那一行（"none" if observed == "human_input" else 冲突）不符
③ 她读过那一行，但没有逐格比对，随后宣布「九格全对」
④ 发现的是 test_judgement_table_sync.py：解析注释表 × 逐格跑实现
```

她自己的定性我照录：

```text
结论：我的表是对的，我的检查没有做。
「结论对」不能抵消「检查没做」。
因为下一次结论错的时候，同样没有检查。
```

**为什么这条必须改，而不能「写我好话就算了」：**

```text
我们正在治的病，是来源被记到错的作者名下。
把错误归错（仓库 description → 她的信）
把功劳归错（机器检查 → 她）
是同一个病，只是方向好听一点。
在一个专门审来源的项目里，好的方向也不能放过。
```

已改：`afcore.py` 两处注释（判定表段与 `third_person_report` 分支）现写作
「2026-11-25 归因更正…发现它的是 `test_judgement_table_sync.py`；
她的结论对，检验没做 —— 这两件事不能互相抵消」。

### 15.2 通用规矩：一个不可能响的检查，比没有检查更危险

Mion 把 P1 那个弱点升级成一条规矩，要求写进本文件：

```text
每一个断言，必须配一个【让它失败】的变异：
把这条断言要守的那个机制关掉，断言必须变红。
关掉之后仍然绿的断言，不算断言。
```

```text
理由：11-24 我们说过一句更准的话——
「会失败的检查，最怕的不是失败，是没响。」
这一条是它的镜像：
一个不可能响的检查，比没有检查更危险，因为它让人以为有检查。
```

**这条规矩立刻咬到了我自己。**

我为 `_via_correct` 修复写了四条测试（OL-5a..d），初版是这样断言的：

```python
except SchemaError as e:
    assert "_via_correct" in str(e)      # ← 检查措辞
```

跑变异时，M37（拆掉「显式拒收保留键」那一层）**MISSED**。
原因是：`_via_correct` 不在白名单里，仍然会被拦，只是换了一句错误消息。
**我的断言守的是措辞，不是机制。**

改法（按 A3）：断言「尝试之后来源字段没变 + revision 没抬 + 无 correction_of 边」。
纵深防御让消息变化时，机制结果不变 ⇒ 断言仍绿，这是对的；
只要机制守住了，从哪条路拦下的不算事。

### 15.3 `_via_correct` 曾是调用方可自塞的参数（真洞，已填）

Mion 复现的原文：

```text
afcore.py:438   via_correct = bool(changes.get("_via_correct"))
afcore.py:536   correct() 内部传 "_via_correct": True

⇒ 这个标志住在【调用方给的 dict】里。
⇒ 任何能调 revise() 的代码，都能自己塞一个 "_via_correct": True 进去。
```

我复现了（`.local_scratch/mion6_repro.py`）：

```text
=== 复现前 ===
  participation_basis = first_person_report
  relation            = []
=== 攻击：往 changes 里塞 _via_correct: True ===
  >>> 通过了来源字段护栏  【洞确实存在】
=== 复现后 ===
  participation_basis = third_person_report
  relation            = []
  relation 里有 correction_of ? False        ← 正是护栏要防的那件事
```

修法（Mion 给的）：把标志从「数据」变成「方法选择」。

```python
def revise(self, record_id, changes, reason="", authority=None):
    return self._revise_impl(record_id, changes, reason, authority,
                             via_correct=False)

def _revise_impl(self, record_id, changes, reason, authority, via_correct):
    # 防御：即便有人直接调 _revise_impl，也不接受藏在数据里的开关
    if "_via_correct" in changes:
        raise SchemaError("changes 不得包含保留键 _via_correct。…")
    ...

def correct(self, ...):
    return self._revise_impl(..., via_correct=True)
```

⇒ 攻击面从「往 dict 里塞键」变成「调一个私有方法」，
与 `record_observed` 的 (c) 档同等诚实等级。

### 15.4 变异设计的一个坑：单层变异打不穿多层防御

第一版我把三层拆解写成三条独立变异（M37/M38/M39），结果 **MISSED 2**。
实测（`.local_scratch/diag_m37b.py`）：

```text
  M37                -> BLOCKED  revise 不允许变更字段 ['_via_correct']
  M38                -> BLOCKED  changes 不得包含保留键 _via_correct
  WL                 -> BLOCKED  changes 不得包含保留键 _via_correct
  SRC                -> BLOCKED  changes 不得包含保留键 _via_correct
  M37+WL             -> BLOCKED  revise 不允许直接改来源字段
  M38+WL             -> BLOCKED  changes 不得包含保留键 _via_correct
  WL+SRC             -> BLOCKED  changes 不得包含保留键 _via_correct
```

⇒ **必须四层同时拆掉才打得穿**：① 显式拒收键、② 白名单、③ 来源字段护栏、④ 公开入口不读 dict 里的标志。

**这里有个要分清的界限：**

```text
「一次只关一层的变异 MISSED」 ≠ 「测试弱」
它只说明：那条变异【没有真正改变可观测行为】。
按 A3 的说法，变异必须真的打穿机制；打不穿机制的变异是【无效变异】，不是测试的失分。
```

⇒ 已在 `test_mutations_gate.py` 加组合变异支持（`\n---\n` 分隔多段），
M37 现在是四段同时拆。改后 **CAUGHT 36 / MISSED 0**。

### 15.5 状态行（照 Mion 给的登记口径）

```text
JUDGEMENT_TABLE_9_CELLS        = PASS
JUDGEMENT_TABLE_MACHINE_CHECK  = ADDED
TABLE_IMPLEMENTATION_SYNC      = YES
ORIGIN_LAYER                   = IMPLEMENTED
ORIGIN_POLLUTED_ROLLBACK       = PROVEN（OL-4b）
ASSERTED_SIDE_CHANGE_GUARD     = YES
GUARD_REACHABILITY             = NOT_ACHIEVABLE_IN_THIS_PROTOTYPE
TEST_ASSERTION_CANFAIL_RULE    = ADOPTED（15.2，并已回改自己的断言）
IMPORTANCE_CRITERIA            = DELIVERED（Mion 回复6 §四 A1–A4 / B1–B4 / C1–C3）
BASELINE_DEFINITION            = DELIVERED（Mion 回复6 §五 D1–D5）
IMPORTANCE_IMPLEMENTATION      = MAY_START_AFTER_A3_B3
ATTRIBUTION_FIX                = DONE（15.1，机器检查不再记到 Mion 名下）
```

### 15.6 验收

```text
test_p1_p5.py                17/17
test_recovery_gate.py        10/10
test_z61_gaps.py             13/13
test_observed_channel.py     34/34
test_origin_layer.py         16/16   （OL-5a..d 新增；断言改为守机制）
test_judgement_table_sync.py PASS
test_mutations_gate.py       CAUGHT 36 / MISSED 0（M37 改为四层组合变异）
test_mutations_v4.py         CAUGHT 7 / REDUNDANT 2 / MISSED 0
check_registry.py            [OK]
```

### 15.7 第 5 项：判据已交付，实现待 A3/B3 就绪后再启

Mion 回复6 §四、§五把判据与基线定义给了，我照录要点，不改一字：

- (a) A1 形式三件套 / A2 Y 必须能构造 / A3 必配已知会失败的情形 / A4 看数据前写下
- (b) B1 `model_generation` 一律不进「重要」集合 / B2 与任何统计量无关、无阈值 /
  B3 该排除必须能被断言检查且关掉会变红 / B4 (b) 优先于 (a)
- (c) C1 同段给三个数 / C2 分母为空 ⇒ `NOT_EVALUABLE`（不是 0）/ C3 与结论同段返回
- (D3) 合成夹具上的基线只能写 `MEASURED_ON_SYNTHETIC_ONLY`，
  因为它的数值几乎只由「夹具作者有没有记得调 `record_observed`」决定，与真实世界无关
- (D5) 红线不变：无基线前，任何重要性结论不得写入 `reports/`

**B4 的理由我特别记一笔**（它解释了为什么需要一条不听指标的规则）：

```text
自我回声放大【恰好会】让 (a) 看起来被满足。
模型反复生成同一句 ⇒ 相似度高 ⇒ 判为重要 ⇒ 更常召回 ⇒ 更常生成。
它不报错、不越界、指标还很好看。
⇒ 必须有一条规则，在「指标好看」时不听指标。
```

---

## 十六 · A3 的边界 E1/E2/E3，以及我因此发现自己说错的防御结构（据 Mion 2026-11-25 回复7）

Mion 这一封只做一件事：**给 A3 加一条边界，防止「无效变异」变成它的后门。**

### 16.1 她的担忧：解释权会吃掉落败

```text
「这条变异无效」是【解释】。
任何一次 MISSED，都可以用这句解释掉。
⇒ 若没有判据，「无效变异」就会变成 A3 的逃生门：
   每一次 MISSED 都能被重新叙述成「变异无效，不算失分」。

那样 A3 就从「断言必须能失败」退化成「断言失败时我可以说它不算」。
```

**这是对的，而且我上一封正是在用这个解释。**

### 16.2 她给的三条边界（照录）

```text
E1  对每一个判为「无效」的变异，必须在同一次运行里，
    独立打出【被变异点的实际结果】。这一栏不能来自目标测试的红绿。

E2  若无法独立观测（该层无法单独表达其结果），
    则该变异【不得】判为无效，只能记为 UNRESOLVED，并保留在台账里。
    UNRESOLVED ≠ MISSED ≠ CAUGHT。三个状态，不许合并。

E3  「无效变异」的结论必须附【它被哪一层拦住】。
    说不出被谁拦住的，不算无效，算没查清。
```

她又补了 §四一条：

```text
组合变异 CAUGHT 证明：整体有防御。
分层变异（或 E1 的逐层直接观测）证明：每一层都有存在理由。
两者不能互相替代。

若只保留组合变异：
  四层拆到两层时它还会 CAUGHT ⇒ 你不知道剩下两层是必需还是冗余。
  某天有人删掉两层，测试仍然是绿的。
```

### 16.3 我照 E1 做，第一件事就是发现自己上一封说错了

我把「直接观测」实现成 `layer_evidence.py`：不跑目标测试，
只用探针调一次 `revise()`，把外部状态原样打出来。

**第一次跑就出了三个 `UNRESOLVED`：**

```text
四层全拆              → TypeError: __init__() got an unexpected keyword argument '_via_correct'
只留 L3_SOURCE_GUARD  → TypeError（同上）
只留 L4_ENTRY_HARDCODE → TypeError（同上）
```

`TypeError` 不是护栏。它是 `_via_correct` 被放行后一路进到
`Record(**merged)`，而 `Record.__init__` 不接受这个键 —— **碰巧挡住的。**

### 16.4 换一种攻击，结论完全反转

我原来的探针只测一种攻击：往 changes 里塞 `"_via_correct": True`。
它只对 L1/L2/L4 的**字符串检查**有效。

换成 B 型攻击 —— **不塞那个字符串，直接改 `participation_basis`**：

```text
  拆掉的层                | A 塞 _via_correct      | B 只改来源
  -------------------------------------------------------------------
  （不拆）                | BLOCKED_BY_L1          | BLOCKED_BY_L3
  只拆 L1_KEY_REJECT      | BLOCKED_BY_L2          | BLOCKED_BY_L3
  只拆 L2_WHITELIST       | BLOCKED_BY_L1          | BLOCKED_BY_L3
  只拆 L3_SOURCE_GUARD    | BLOCKED_BY_L1          | 【OPENED】        ← 只拆一层就穿
  只拆 L4_ENTRY_HARDCODE  | BLOCKED_BY_L1          | BLOCKED_BY_L3
  只留 L3_SOURCE_GUARD    | BLOCKED_BY_ACCIDENT    | BLOCKED_BY_L3
  只留 L3 + L1            | BLOCKED_BY_L1          | BLOCKED_BY_L3
  四层全拆                | BLOCKED_BY_ACCIDENT    | 【OPENED】
```

**三条结论：**

```text
① 真正守住「改来源必须走 correct()」的只有 L3_SOURCE_GUARD 一层。
② L1/L2/L4 只对 `_via_correct` 这个【特定字符串】设防；
   攻击者不写这个字符串，三层全部不起作用。
③ 我上一封写的「必须四层同时拆才打得穿」是【错的】：
   只拆 L3 就打得穿。我当时只测了 A 型，看不出来。
```

### 16.5 这条错误的形状

```text
我看到的：A 型攻击在拆一层后仍被拦 ⇒ 以为「每层都必需」
实际是：  A 型攻击根本不需要那三层；那三层只是在过滤「一个字符串」
我漏掉的：换一条攻击路径
  
⇒ 这跟 Mion 记了四次的那个错类是同一个：
  「只取了一环，就当成了全链」。
  
⇒ 我当时还把它写成了「变异设计要点，三层防御各自能拦」，
  语气很笃定 —— 因为我在【同一型攻击】里验了很多次。
  同一型验一百次，仍然只是一型。
```

### 16.6 三态落地

`test_mutations_gate.py` 现在对每个 `MISSED` 再判一次（用直接观测探针）：

```text
状态变了 + 测试没红   → 真 MISSED（修测试）
状态未变 + 说得出谁拦 → UNRESOLVED（E3 满足；不是测试失分）
状态未变 + 说不出谁拦 → UNRESOLVED（未查清，仍不判无效）
探针无法运行          → UNRESOLVED（E2）
```

实测结果：

```text
CAUGHT       36
UNRESOLVED    3   （M38/M39/M40 —— 各自被另一层覆盖，附拦截层名）
MISSED        0
```

**注意这三条不再报「CAUGHT」，也不报「MISSED」：**
按 E2，三态不许合并。把 UNRESOLVED 并进 CAUGHT 是报喜，
并进 MISSED 是自罚 —— 两种都不对。

### 16.7 我提的一个补充（供 Mion 裁定，未擅自生效）

上一封我写过「关不掉的一层 ≠ 测试弱，只是那条变异无效」。
E1/E2/E3 落地后，我想把这句话再收紧一点：

```text
「无效变异」的判据不该是「目标测试没报」，
也不该止于「外部状态没变」，
还应当要求【换一种攻击路径再验一次】。

理由：A 型没变，不代表这一层对 B 型无关。
      我这次就是栽在「只验一型」上。
```

⏳ **这条我没写进规矩，只写在这里。** E1/E2/E3 是 Mion 立的，
加条款要她点头 —— 我不能自己把自己上一封的教训写成她的规矩。

### 16.8 状态行

```text
ATTRIBUTION_FIX                 = DONE
A3_RULE                         = ADOPTED
A3_INVALID_MUTATION_JUDGE      = MUST_BE_DIRECT_OBSERVATION（E1，已落地）
MUTATION_STATES                 = CAUGHT / MISSED / UNRESOLVED（三态，已分离）
COMBINED_MUTATION               = ALLOWED（不得替代分层证据）
LAYER_EVIDENCE_LEDGER           = reports/layer_evidence.json（新增）
REAL_DEFENCE_FOR_SOURCE_GUARD   = L3_SOURCE_GUARD（仅一层）
L1_L2_L4_SCOPE                  = STRING_ONLY（只过滤 _via_correct 字面）
MY_V1_CLAIM                     = WRONG（「必须四层同时拆」）
ASSERT_STYLE                    = OBSERVABLE_STATE_NOT_INTERNAL_PATH
VIA_CORRECT_HOLE                = CLOSED
GUARD_REACHABILITY              = NOT_ACHIEVABLE_IN_THIS_PROTOTYPE
KEYWORD_SCOPE_RULE              = PROPOSED（关键词给候选集，判定必须回原文）
```

### 16.9 验收

```text
test_p1_p5.py                17/17
test_recovery_gate.py        10/10
test_z61_gaps.py             13/13
test_observed_channel.py     34/34
test_origin_layer.py         16/16
test_judgement_table_sync.py PASS
test_layer_evidence.py       10/10   （新增，守台账不说谎）
test_mutations_gate.py       CAUGHT 36 / UNRESOLVED 3 / MISSED 0
test_mutations_v4.py         CAUGHT 7 / REDUNDANT 2 / MISSED 0
```

---

## 十七 · F1/F2 · 纵深≠冗余 · G1/G2/G3（据 Mion 2026-11-25 裁定「换一条攻击路径」）

### 17.1 F1：不是「再验一次」，是「按维度各验一次」

我提的建议是「无效变异还应要求换一种攻击路径再验一次」。
Mion 同意，但升格：

```text
F1  每一层必须对【它声称覆盖的输入维度】各有一份独立观测。
    而「它声称覆盖哪些维度」必须先写下来。
    ⇒ 不写下来，就无法判断覆盖率，只能事后解释。

F2  「换一种攻击路径」是 F1 的一个实例，不是 F1 本身。
    F1 要求的是【输入空间的抽样清单】，不是「再随便试一个」。
```

她的理由：

```text
「再验一次」无法验收 —— 试几次算够？试哪种算换？没人能判。
「按维度各验一次」可验收 —— 维度清单写了没有，一眼能查。
```

**我照此改写了 `layer_evidence.py`：**

```python
DIMENSIONS = [
  ("D1_FLAG_LEAK",              "塞内部标志 _via_correct 伪装成纠正流程"),
  ("D2_DIRECT_SOURCE_EDIT",     "不塞标志，直接改 participation_basis"),
  ("D3_SOURCE_VIA_SOURCE_KIND", "改另一个来源字段 source_kind"),
  ("D4_SOURCE_VIA_REF",         "改来源引用 source_ref"),
]

LAYERS = [
  ("L1_KEY_REJECT",    ..., 声称覆盖=["D1_FLAG_LEAK"], ...),
  ("L2_WHITELIST",     ..., 声称覆盖=["D1_FLAG_LEAK"], ...),
  ("L3_SOURCE_GUARD",  ..., 声称覆盖=["D2","D3","D4"], ...),
  ("L4_ENTRY_HARDCODE",..., 声称覆盖=["D1_FLAG_LEAK"], ...),
]
```

⇒ 每一层的「声称覆盖维度」写在代码里，测试会逐条核它是否真的拦住。

### 17.2 纵深 ≠ 冗余：台账必须分开记

Mion §二：

```text
拦住同一个字符串的三层，不是【纵深防御】。
纵深要求每层拦不同的攻击面。
拦住同一输入的多数层，是【冗余】。
```

实测结果：

```text
  D1_FLAG_LEAK              基准拦住者=L1_KEY_REJECT   独力守卫=L1_KEY_REJECT, L2_WHITELIST
      ⇒ 冗余 REDUNDANCY（可独力拦住的层数=2）
  D2_DIRECT_SOURCE_EDIT     基准拦住者=L3_SOURCE_GUARD 独力守卫=L3_SOURCE_GUARD
      ⇒ 纵深 COVERAGE（可独力拦住的层数=1）
  D3_SOURCE_VIA_SOURCE_KIND 基准拦住者=L3_SOURCE_GUARD 独力守卫=L3_SOURCE_GUARD
      ⇒ 纵深 COVERAGE（可独力拦住的层数=1）
  D4_SOURCE_VIA_REF         基准拦住者=L3_SOURCE_GUARD 独力守卫=L3_SOURCE_GUARD
      ⇒ 纵深 COVERAGE（可独力拦住的层数=1）
```

**判据的定义（这一条我第一版写反过，见 17.4）：**

```text
独力守卫 = 只保留这一层、其余全拆 ⇒ 该维度仍被【它自己】拦住
```

**冗余的价值与限度（Mion 原话）：**

```text
它们不是没用 —— 它们的价值是「哪天有人删掉 L3，A 型仍被挡」。
但那不是对 B 型的防御，不能拿来支撑「防御完好」。
```

⇒ 我的落法：冗余**不是**没用，而是「删掉一层不立刻退化成零防御」。
但它绝不能用于「防御完好」这个结论。

### 17.3 G1/G2/G3：ACCIDENT 不得计入防御

```text
G1  ACCIDENT（碰巧挡住，例如参数不被接受、键名拼错、异常类型不对）
    【不得】计入任何防御层，也不得计入 CAUGHT。
G2  ACCIDENT 必须单列，并写明：它挡住的不是攻击，是攻击者的笔误。
G3  若某条路径【只】被 ACCIDENT 挡住，该路径状态为 OPENED，
    不是因为「反正挡住了」。
```

**这次的实例非常典型：**

```text
四层全拆 · D1_FLAG_LEAK
  原始 = ACCIDENT (TypeError: unexpected keyword '_via_correct')
  按 G3 = OPENED
```

⇒ 也就是说：**D1 在四层全拆时的「被挡住」，是因为攻击者多写了一个键，
不是因为任何一层的设计。** 记成 BLOCKED 会显示「防御完好」——
正是这件事要防的那种谎。

### 17.4 我在实现 F1 时又栽了一次，形状和上一封一样

第一版 `LAY-4b` 我是这样找「独力守卫」的：

```python
if c["verdict"] == "OPENED":
    solo.append(keep)          # ← 写反了
```

跑出来 0 层，于是得出「D1 没有任何独力守卫」。

**真实的判据是相反的**：只保留这一层时**被它自己拦住**，才叫独力守卫。

```text
我在数「哪些层拆掉会打开」，
我要数的是「哪些层留着就守得住」。
同一条语句里，主语和判据都反了。
```

⇒ 这正是 §零之前那条原则的第二次发作：
**我以为我在验证防御结构，其实在验证一个方向反了的判据，
而且它「跑通了」—— 0 条结果不报错。**

### 17.5 状态行

```text
F1_DIMENSION_CLAIMS          = DECLARED（4 维度 / 4 层声明）
F2_SAMPLING_LIST             = IN_CODE（DIMENSIONS 常量）
LAYER_CLAIMS_VERIFIED        = YES（逐条拆层观测）
COVERAGE_VS_REDUNDANCY       = SEPARATED（D1 冗余，D2/D3/D4 纵深）
D1_SOLO_GUARDS               = L1_KEY_REJECT + L2_WHITELIST（2 层，冗余）
D2_D3_D4_SOLO_GUARD          = L3_SOURCE_GUARD（1 层，纵深）
ACCIDENT_COUNTED_AS_DEFENCE  = NO（G1）
ACCIDENT_LISTED_SEPARATELY   = YES（G2，台账 accidents 栏）
G3_ACCIDENT_ONLY_PATH        = OPENED（D1 在四层全拆时）
MY_LAY4B_V1_BUG              = WRITTEN_BACKWARDS（已修）
```

### 17.6 验收

```text
test_p1_p5.py                17/17
test_recovery_gate.py        10/10
test_z61_gaps.py             13/13
test_observed_channel.py     34/34
test_origin_layer.py         16/16
test_judgement_table_sync.py PASS
test_layer_evidence.py       10/10   （F1/F2 + G1/G2/G3 全部入测）
test_mutations_gate.py       CAUGHT 36 / UNRESOLVED 3 / MISSED 0
test_mutations_v4.py         CAUGHT 7 / REDUNDANT 2 / MISSED 0
```

---

## 十八 · 集合完整性 H1/H2/H3（据 Mion 2026-11-25 裁定2）

### 18.1 我把问题问错了

我的原问题：「五个来源字段，要不要各测一维？」

我给了两个选项：五字段各跑一遍完整攻击，或者承认「同属一条护栏」、做代表抽样。

Mion 两个都不选，理由是：

```text
你问的那两件事，都依赖一个你【还没有验证】的前提：
「这五个字段确实同属一条护栏，且没有第二条路能写它们」。

而两类真风险正好在这个前提里：
  风险 a  某字段没进 _SOURCE_FIELDS
          拼错 / 漏加 / 改名后忘同步 / 后来新增的 origin_* 忘了归类
  风险 b  某字段有另一条写入路径
          correct() 里单独处理 / insert 允许从构造参数带进来 / 新方法绕过去

⇒ 把同一个集合表达式测五遍，查不出 a)，也查不出 b)。
  因为 a) 和 b) 的问题【不在表达式内部】，
  而在【集合本身】和【路径本身】。
```

### 18.2 三条断言

```text
H1  集合内容一字不差
H2  字段分类全覆盖：每个 Record 字段恰好落在
    可改 / 来源 / 只读 三类之一，落在外面就红
H3  入口唯一性：除 correct() 外没有公开方法能改来源字段
```

成本 ≈ 两倍（而非五倍），覆盖强于代表抽样 —— 因为查的是**前提**，不是表达式。

### 18.3 H2 当场掀掉了一个我写了很久的结构矛盾

H2 的第一条断言是「三类两两不交」。它立刻红了：

```text
_REVISABLE 与 _SOURCE_FIELDS 重叠：
['basis_ref', 'participant_id', 'participation_basis', 'source_kind', 'source_ref']
```

**这不是误报。** 之前五个来源字段**同时**在 `_REVISABLE` 里，又受来源护栏保护。
两处定义重叠，只是一直没人问「它们到底属于哪一类」。

改法：

```text
_REVISABLE      普通 revise 可改（不含任何来源字段）
_SOURCE_FIELDS  只有 correct() 能改
_READONLY       存储层/专用方法维护

correct() 的额外权限 = _REVISABLE | _SOURCE_FIELDS（唯一增量）
```

白名单行随之改成：

```python
allowed = self._correctable() if via_correct else set(self._REVISABLE)
```

**这条改动是 Mion 的 H2 直接促成的，不是我自己想到的。**

### 18.4 我写反判据这件事，第三次了

第一版 `LAY-4b` 用「只留这一层时 OPENED」来判定独力守卫，跑出 0 层。
正确判据是「只留这一层时**被它自己**拦住」。

第二版把 L2 的变异体改成 `allowed = _correctable()`（对所有 changes 放行），
于是「只留 L2」其实连来源字段也一起放行了 —— 实测拦住的不是 L2 而是 L3，
台账差点把纵深误记成冗余。

第三版只给 `else` 分支加 `{"_via_correct"}`，但 L4 的变异体会让
`via_correct` 变 True、走另一个分支 —— **两个变异体互相抵消**，
实测仍报「不允许变更字段」，看起来像 L2 无效。

⇒ 最终给两个分支都放行：

```python
allowed = (self._correctable() | {"_via_correct"} if via_correct
           else set(self._REVISABLE) | {"_via_correct"})  # MUTANT
```

**这三次都是同一类错：我在调判据/变异体，而它们本身就是被检对象。**
A3 那条规矩（断言必须能失败）管的是断言；这里需要的是它的镜像：
**变异体必须真的改变可观测行为，否则它测的不是它号称测的东西。**

### 18.5 真实的防御结构（改动后重新实测）

```text
D1_FLAG_LEAK              独力守卫 = L1_KEY_REJECT, L2_WHITELIST
                          ⇒ 冗余 REDUNDANCY（2 层，机制同源：都是「字符串不在集合里」）
D2_DIRECT_SOURCE_EDIT     独力守卫 = L3_SOURCE_GUARD
D3_SOURCE_VIA_SOURCE_KIND 独力守卫 = L3_SOURCE_GUARD
D4_SOURCE_VIA_REF         独力守卫 = L3_SOURCE_GUARD
                          ⇒ 纵深 COVERAGE（1 层）

⚠ 但 D2/D3/D4 的纵深是【L2 白名单 + L3 来源护栏】两层机制不同的守卫：
   拆白名单句 → 仍被来源护栏拦
   拆来源护栏 → 仍被白名单拦
   两句都拆   → OPENED
   （diag_which.py 实测）
  ⇒ 这是真纵深（机制不同），不是冗余（机制同源）。
```

### 18.6 标签纪律

```text
REPRESENTATIVE_SAMPLING 这个标签不要用。
它的合法性依赖「集合完整」，而集合完整必须被断言，不能靠声明。

可用（H1/H2/H3 都齐之后）：
    SAMPLING_JUSTIFIED_BY = {H1: 集合内容一致, H2: 字段分类全覆盖, H3: 入口唯一}

⇒ 标签必须指向【断言编号】，不指向【理由】。
  理由会被遗忘，断言会红。
```

### 18.7 状态行

```text
SOURCE_FIELD_SET             = 5 字段，H1 一字不差断言
FIELD_CLASSIFICATION         = 3 类两两不交 + 并集等于全部字段（H2）
SOURCE_ENTRY_UNIQUENESS      = 仅 correct()（H3）
REVISABLE_OVERLAP_BUG        = FIXED（来源字段移出 _REVISABLE）
MY_VERDICT_BUG_COUNT         = 3（全部同一类：判据/变异体本身未验证）
SAMPLING_JUSTIFIED_BY        = {H1, H2, H3}
REPRESENTATIVE_SAMPLING      = DO_NOT_USE_AS_LABEL
```

### 18.8 验收

```text
test_p1_p5.py                17/17
test_recovery_gate.py        10/10
test_z61_gaps.py             13/13
test_observed_channel.py     34/34
test_origin_layer.py         16/16
test_judgement_table_sync.py PASS
test_field_classification.py  8/8    （新增：H1/H2/H3 + 标签纪律）
test_layer_evidence.py       10/10
test_mutations_gate.py       CAUGHT 40 / MISSED 0（新增 M41；M39/M40 锚点已同步）
test_mutations_v4.py         CAUGHT 7 / REDUNDANT 2 / MISSED 0
```

---

## 十九 · 两个裁定 + C1：约束必须是分类的结果（据 Mion 2026-11-25 裁定3）

### 19.1 裁定一：独力守卫按机制数，但两个数并列

```text
SOLO_GUARDS_BY_MECHANISM  = 拆掉其他所有机制，这一层还能不能挡住
                            （这定义本身就是机制级的）
SOLO_GUARDS_ATTRIBUTABLE  = 出错时消息能归给几层
ATTRIBUTION_LOSS          = 前者 − 后者
```

Mion 的理由：

```text
按消息数报，是把【观测手段的限制】写进了【被观测对象的属性】。
这正是我们一路在治的那件事：把「我看不到」写成「不存在」。
```

**两个数的差值必须报，因为只报一个会引出两种相反的错：**

```text
只报 1 ⇒ 后来的人看到「只有一层在守」，可能去加一层。
只报 2 ⇒ 后来的人以为消息能区分两条路，去按消息删层。
```

### 19.2 我照做后的实测，得出的是 UNMEASURABLE

第一次实现，我按「只留这一层语句」测，得到 `BY_MECHANISM = 4`——
荒谬：L1/L4 根本不针对来源字段。

原因是：`allowed = ... else set(self._REVISABLE)` 在来源字段移出
`_REVISABLE` 之后，**自身就成了一道来源护栏**。
拆掉 `L3_SOURCE_GUARD` 那句，白名单那句仍然拦得住。

第二版改成按「机制组」测，又发现一个更硬的事实：

```text
「字段集：allowed 不含来源字段」与「流程判断：touching_source and not via_correct」
这两句【相邻且共用同一处调用顺序】。
任何「拆 ① 留 ②」的变异体都必须改同一段代码的语义，
而改完之后 ② 读到的状态也随之改变。
⇒ 无法分别观测。
```

**这就是 ATTRIBUTION_LOSS 的一个真实实例：**
结构上有 2 套判断，但观测手段无法把它们分开。

所以我登记为：

```text
MECH_FLOW_OR_FIELDSET  = 复合机制（结构上 2 套判断，不可分拆观测）
ATTRIBUTION_LOSS       = UNMEASURABLE
```

并在台账里明确写：

```text
⇒ 只能报「至少 1 套机制能守住」，不能报精确层数。
  不许把 1 当成「只有一层」。
```

**如果我按原计划报 `BY_MECHANISM = 1`，读者会得到与我错判时一样的结论。**
这次的正确做法是不给数，而不是给一个看起来精确的数。

### 19.3 裁定二：MUTANT_EFFECT_MUST_BE_OBSERVED（不是 A3 的镜像，是它的前提）

我上一封写「变异体必须改变可观测行为」是 A3 的镜像。Mion 更正：

```text
A3 的句子是：「把机制关掉，断言必须红。」

⇒ 但「关掉」这个动作本身，必须先被验证真的关掉了。
   否则 A3 是在跑一个【没关掉的机制】，然后说「断言没红，所以断言弱」。
⇒ 那句错判会指向断言，而真正出错的是变异体。

⇒ 顺序上：M1 在前，A3 在后。A3 依赖 M1 成立，才能开始它的判断。
```

**并与 E1 合成一条：**

```text
MUTANT_EFFECT_MUST_BE_OBSERVED

变异体对机制的作用，必须由探针直接观测，不得由目标测试的红绿反推。

  观测到行为未变 ⇒ 该变异无效（E1）
  观测到行为已变 ⇒ 该变异有效，此时才可用 A3 判断断言强弱（M1）
```

### 19.4 C1：约束必须是分类的结果

Mion 新立的规矩，位置与 A3/M1 同级：

```text
C1  任何「某字段只能经 X 改」的约束，
    必须是【分类的结果】，不得是【另一句代码 + 一句注释】的结果。

理由：注释不执行，第二句代码不会自己知道自己多余。
      而「两处定义靠注释维持一致」这种结构，
      在漂移发生时【两边都还看起来对】。
```

**这条比我做的 H2 更重要。**

```text
H2 是一次检查（发现重叠）。
C1 是让这类结构【不再出现】。
```

落地方式：`test_field_classification.py` 新增 `C1a`：

```python
def write_path(f):
    """仅凭分类判定写入口径 —— 不读任何注释、不跑任何写入。"""
    if f in _SOURCE_FIELDS:  return "correct_only"
    if f in _REVISABLE:      return "revise"
    return "readonly"

# 五个来源字段必须全部判为 correct_only
```

⇒ 这个判定完全不依赖「另外还有几处检查」，也不依赖注释怎么写。

### 19.5 关于我上一封「往回收的那一格」，Mion 给我补了一层

我写：「认出症状，和写出堵住它的断言，是两件事。我做到前一件，做到了也没用。」

Mion 的更正：

```text
认出症状之后要做什么，需要有【一条可执行的替代方案】。
你当时没有。
⇒ 所以你不是「明知故犯」，是【没有别的做法可用】。
⇒ 那条替代方案（H2）是我给的，而它需要先有 H1 的集合概念才写得出来。
```

```text
⇒ 当有人说「我知道不对但我还是这么做」时，
   先问「有没有一条他做得到的别的做法」，
   不要先问「他为什么不改」。
```

**这个区分是可操作的不是安慰：**

```text
「他为什么不改」  ⇒ 指向意志，没有下一步动作。
「有没有别的做法」⇒ 指向缺口，下一步就是去补那一条。
```

我不把这条写进规矩（那是她的判断），只记在这里作为我自己的检查清单。

### 19.6 状态行

```text
SOLO_GUARDS_BY_MECHANISM       = UNMEASURABLE（来源维度，含复合机制）
SOLO_GUARDS_ATTRIBUTABLE       = 1（来源维度）
ATTRIBUTION_LOSS               = UNMEASURABLE（须说明原因，不得报精确值）
COMPOSITE_MECHANISM_RECORDED   = YES（MECH_FLOW_OR_FIELDSET，注明为何测不出）
MUTANT_EFFECT_MUST_BE_OBSERVED = ENFORCED（E1 + M1 合成）
CLASSIFICATION_AS_RULE         = C1（已落地为 C1a/C1b）
MY_V3_MEASUREMENT_ATTEMPT      = 2 次失败后改为登记 UNMEASURABLE
```

### 19.7 验收

```text
test_p1_p5.py                17/17
test_recovery_gate.py        10/10
test_z61_gaps.py             13/13
test_observed_channel.py     34/34
test_origin_layer.py         16/16
test_judgement_table_sync.py PASS
test_field_classification.py 10/10   （新增 C1a/C1b）
test_layer_evidence.py       12/12   （新增 DUAL-1/DUAL-2）
test_mutations_gate.py       CAUGHT 40 / MISSED 0
test_mutations_v4.py         CAUGHT 7 / REDUNDANT 2 / MISSED 0
```

---

## 二十 · 第 5 项 A3/B3 限定原型（据凌翼 2026-11-25 裁定）

### 20.1 授权边界

```text
问题一 → 甲（修订版）：允许用【合成召回事件流】表达高频，
         要求多次事件指向同一 record_id，
         不得用复制多条独立记录冒充同一记录被多次召回。

问题二 → 授权：实现一个【不计算分数、不训练、不排序】的
         候选资格集合函数，仅用于 A3/B3 合成工程测试。
         该集合不代表「重要记忆已经选出」。
```

```text
SYNTHETIC_TRACE_DESIGN     = AUTHORIZED
CANDIDATE_FILTER_PROTOTYPE = AUTHORIZED_LIMITED
FULL_IMPORTANCE_LEARNER    = NOT_AUTHORIZED
IMPORTANCE_IMPLEMENTATION  = NOT_AUTHORIZED（A/B 裁定不自动构成第 5 项授权）
```

### 20.2 为什么用集合而不是分数

```text
B1 要求 model_generation 的记录【不得进入「重要」集合】。
「不得进入集合」可以用 membership 断言；
「分数要低」只能用阈值断言，而阈值是 B2 明文禁止的。
⇒ 用集合，B1 可以 100% 按文字实现，不需要任何阈值。
```

```python
importance_candidates(store, trace=None, exclude=None) -> dict
    # 返回 {status, candidates: set, denominator_size,
    #       excluded: {rule: [...]}, active_rules,
    #       measurement_scope, note}
```

**它不返回分数、不返回排序、不训练。**

### 20.3 合成召回事件流（问题一 甲）

```text
召回事件 = {"record_id", "at", "query_ref"}
「高频」= 同一 record_id 出现多次【不同】事件。
```

**两条硬校验（直接对应凌翼的「不得用复制多条独立记录冒充」）：**

```text
① record_id 必须【真实存在】于 store
   ⇒ 用不存在的 ID 复制造不出高频
② 完全相同的事件（同 record_id + at + query_ref）被拒绝
   ⇒ 完全重复不是「多次召回」，是重复提交
```

```text
⚠ 但允许同一 record_id 的【不同】事件重复出现 —— 那才是高频。
```

### 20.4 两条排除规则，各自可单独关闭

```text
R_MODEL_GENERATION      B1：observed_origin == model_generation ⇒ 排除
R_EMPTY_DENOMINATOR     C2：分母为 0 ⇒ 整批结论 NOT_EVALUABLE

⚠ 这两条【不是同一条】：
   B1 排除的是【某条记录】；C2 排除的是【整批结论的可评估性】。
   凌翼裁定第 5 条：「J2 的伪亲历计数和 J3 的空分母判据分别测试，
                     不能用 B3 的结果代替。」
   ⇒ 因此拆成两条规则，各自有独立用例。
```

### 20.5 我在实现这一项时踩的四个坑（全部留档）

**坑一：测试夹具里少了一条记录**

```text
A3-1d 断言 t1 被排除，但 mk_mixed() 里根本没有 t1。
⇒ 断言实际在测「一个不存在的记录」，失败原因是 KeyError 而不是 B1。
⇒ 修：夹具补上 t1，且必须 record_observed 过。
```

**坑二：分母口径与 C1 不一致（真 bug）**

```text
第一版 synthetic_ratios 的分母用 len(live)（全体记录）。
但 C1 明文：分母 = |asserted == first_person_report 的记录数|。
⇒ 两者不同：record_only / third_person 不属于重要性判断的分母。
⇒ 后果：只要库里有任意一条记录，分母就永不为空，
  于是「空分母 ⇒ None」这条判据【从未被触发过】。

⚠ 这个 bug 是被变异 I10 抓出来的，不是我自己看出来的。
```

**坑三：空分母规则遮蔽了 B1 的行为差异**

```text
A3-1e 第一版只有一个 record_only×model_generation 记录。
⇒ 空分母规则把 candidates 整个清空，
  「ro2 不在候选里」是空分母的结果，不是 B1 的结果。
⇒ 断言假通过；变异 I11 因此被判 MISSED（行为已变、测试全绿）。
⇒ 修：补一条 first_person_report 记录作为分母。
```

```text
⇒ 这正是凌翼裁定第 4 条说的：
   「若其他机制阻断了变异效果，不得冒充 A3 成功；
     按既有 E1/E2/E3 与 M1 边界登记。」
```

**坑四：探针只覆盖一个分支**

```text
measurement_scope 在【两个】返回点各算一次
（EVALUATED 路径 / NOT_EVALUABLE 路径）。
第一版只测了 EVALUATED；变异 I9（只改 NOT_EVALUABLE 那处）
行为已变但测试全绿 ⇒ MISSED。
⇒ 修：两个分支各自断言（A3-6a / A3-6a2）。
```

### 20.6 变异验证结果

```text
test_mutations_importance.py
    CAUGHT       12
    UNRESOLVED    0
    MISSED        0
```

**每条变异都走两步（凌翼要求 3/4）：**

```text
① 先【直接观测】候选集合/返回结构是否真的变化（E1/M1）
② 再看目标测试是否红（A3）
③ 行为未变 ⇒ 记 UNRESOLVED，不记 MISSED，也不记 CAUGHT
```

```text
⚠ 过程中 CAUGHT 从 4 → 7 → 8 → 9 → 10 → 11 → 12，
   其中 5 次是因为【探针覆盖面不足】而不是变异无效。
   ⇒ 每次都要先问「是变异无效，还是我看不见？」，
     不能直接判 UNRESOLVED 了事。
```

### 20.7 边界声明（写进每一份返回）

```text
measurement_scope = MEASURED_ON_SYNTHETIC_ONLY   （有 trace 时）
                  = NOT_MEASURED                  （无 trace 时）

note = "候选资格集合 = 未被已声明规则排除的记录。
        它不代表「重要记忆已经选出」。"
```

```text
红线（C）：无基线前，任何重要性结论不得写入 reports/。
⇒ synthetic_ratios() 不写任何文件；测试 A3-6c 守着这一点。
```

### 20.8 状态行

```text
A3_B3_RULES                = DOCUMENTED
SYNTHETIC_TRACE_DESIGN     = AUTHORIZED（已实现）
CANDIDATE_FILTER_PROTOTYPE = AUTHORIZED_LIMITED（已实现）
IMPORTANCE_A3_B3_EVIDENCE  = PARTIAL（合成范围内已交付，待知微/睫检查）
FULL_IMPORTANCE_LEARNER    = NOT_AUTHORIZED
IMPORTANCE_RED_LINE        = 未写入 reports/（A3-6c 守着）

MY_BUGS_FOUND_THIS_ROUND  = 4（夹具缺失 / 分母口径 / 空分母遮蔽 / 探针分支）
MY_BUGS_FOUND_BY_MUTATION  = 2（分母口径 I10 / 两个分支 I9）
```

### 20.9 验收

```text
test_importance_a3b3.py      22/22   （新增）
test_mutations_importance.py CAUGHT 12 / UNRESOLVED 0 / MISSED 0（新增）
test_p1_p5.py                17/17
test_recovery_gate.py        10/10
test_z61_gaps.py             13/13
test_observed_channel.py     34/34
test_origin_layer.py         16/16
test_judgement_table_sync.py PASS
test_field_classification.py 10/10
test_layer_evidence.py       12/12
test_mutations_gate.py       CAUGHT 40 / MISSED 0
test_mutations_v4.py         CAUGHT 7 / REDUNDANT 2 / MISSED 0
```

---

## 二十一 · 固定提交身份

见提交信息与 PR 描述；本文件随代码同一提交入库。

不改 `main`，只进 `exp/v2-l1-verifier`。

---

*本文件按凌翼裁定 2026-11-24 撰写。所有状态值取自该裁定 §四，凡我新增的解释均已标明来源为「我方理解」。*
