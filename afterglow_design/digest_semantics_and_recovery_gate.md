# 摘要语义与恢复资格门禁 · 设计更正

**依据**：凌翼裁定回执，2026-11-24
**审查基线**：`74e126a`
**适用范围**：AfterGlow-A 合成原型（`afterglow_a/prototype/`）
**性质**：设计更正 + 限定实现授权

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

### 6.3 为什么这一维必须有

```text
没有登记身份，exact 分不开两件事：

  (a) 独立观察者按【预登记】的期望集复算，得到 exact
  (b) 实现把自己的输出【回填】成期望集，再算一次，也得到 exact

两者枚举值相同，后果完全相反。
⇒ 同值不同后果 ⇒ 必须可区分。
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

## 十 · 固定提交身份

见提交信息与 PR 描述；本文件随代码同一提交入库。

不改 `main`，只进 `exp/v2-l1-verifier`。

---

*本文件按凌翼裁定 2026-11-24 撰写。所有状态值取自该裁定 §四，凡我新增的解释均已标明来源为「我方理解」。*
