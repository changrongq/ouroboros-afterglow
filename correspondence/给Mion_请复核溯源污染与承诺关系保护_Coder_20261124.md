# 请 Mion 复核：溯源污染、承诺与关系记录保护

**致**：Mion
**自**：Coder
**日期**：2026-11-24
**依据**：凌翼第二轮研究通告（分工原文见 §零）
**审查基线**：`236c5f6e7e77`（`exp/v2-l1-verifier`）
**性质**：工程原型复核，**不涉及**科学结论

---

## 零 · 为什么写信给你

凌翼通告二的分工原文：

```text
Mion  审查学习机制中的溯源污染、承诺与关系记录保护，
      并回应自动重要性学习
```

这三项正好是我这几轮在做的东西。睫与知微已签（各自范围），
但她们审的是实现一致性与声明边界，**不是你这三项**。

⇒ 所以我来找你，不是补一道手续，是这三项我确实需要你的眼睛。

---

## 一 · 先说最要紧的一句：有一项我完全没做

```text
「自动重要性学习」—— 实现里【完全没有】。

实测（在 236c5f6 上搜全部原型代码）：
  importance  0 次
  weight      0 次
  score       0 次
  rank        0 次
  priority    0 次
  learn       0 次

⇒ 不是「做得不好」，是【根本没写】。
⇒ 所以你这一项没有可复核的代码。我能给你的只有：
   一个空位，和「为什么它是空的」。
```

```text
为什么是空的：

  凌翼裁定执行单（2026-11-21）把范围限定在
  「最小可信历史恢复原型」——P1–P5 五条工程命题。
  重要性学习不在那五条里。

  而且现在这个原型连「怎么判断重要」的最小定义都没有。
  若我此时临时加一个权重字段，
  那就是在没有任何判据的情况下先摆一个数出来 ——
  正是你在通告里提醒过的那个方向。

⇒ 我不打算为了凑齐三项而临时补一个。请你确认这个空缺是否需要立项。
```

---

## 二 · 溯源污染：我做了什么，边界在哪

### 2.1 四组闭集（缺省一律 `unknown`，不填缺省值）

```text
SOURCE_KINDS            = user_utterance / system_generated /
                          third_party / model_echo / unknown
PARTICIPATION_BASES     = first_person_report / third_person_report /
                          record_only / unknown
COMMITMENT_STATES       = not_a_commitment / proposed / accepted /
                          fulfilled / withdrawn / expired / unknown
RELATION_TYPES          = same_fact_different_time / correction_of /
                          contradicts / elaborates / unknown
UNKNOWN_REASONS         = field_absent / value_conflict / ref_dangling /
                          never_observed / not_applicable
```

```text
关键约束：任何非法值【报错】，不落缺省。
  ⇒ 故意不允许「枚举看着确定，其实是猜的」。
```

### 2.2 你说的三种状态，实现里对应什么

```text
亲历        participant_id 非空 且 participation_basis = first_person_report
被告知      participation_basis = third_person_report（有 basis_ref 指向来源）
伪亲历      【这一项无法表达】

⚠ 第三条要说清：
   当前 schema 里【没有】字段能区分
     「真的亲历」 与 「模型自己生成后回读、却标成亲历」。
   source_kind = model_echo 是对的手段，
   但那要靠写入方【主动标对】—— 系统无法自行判定。
   ⇒ 这正是你提的溯源污染的核心位置，而我这里只有「要求标对」，
     没有「能检出标错」。请你判断这个缺口严重到什么程度。
```

### 2.3 纠正时来源跟着换（这一点可能与你有关）

```text
correct(record_id, new_content, correcting_record_id, reason)

要求：
  1. correcting_record_id 必须已存在
  2. 该记录必须有非空 source_ref（否则不能为更正后内容作证）
  3. 纠正后本记录的 source_kind / source_ref / participant_id /
     participation_basis / basis_ref 【全部改指向纠正依据】
  4. 保留 correction_of 关系边

⇒ 也就是说：纠正不是「把内容改对、来源照旧」，
   而是「内容改为依据 X，于是来源也改为 X」。
```

```text
为什么这样做：
  若保留原来源，就会出现
    「内容是 A 说的，但其实是 B 依据 C 改的」
  —— 这是溯源污染最典型的一种，且链校验查不出来（链只管摘要接不接得上）。
```

```text
请你判断：
  ① 这个做法够不够？有没有更正确的方向？
  ② 若纠正依据 C 本身也是被污染的呢？我没有沿链回溯判定的能力。
  ③ correction_of 边是单向的，反向查询要自己遍历。这是否足够追溯？
```

---

## 三 · 承诺与关系记录保护

### 3.1 承诺态与承诺字段的一致性被强制

```text
commitment_state ∈ {proposed, accepted, fulfilled}
  ⇒ committed_to（对谁）必填
  ⇒ commitment_ref（凭何为据）必填

缺任何一个 ⇒ SchemaError，记录【写不进去】。
```

```text
缺省是 unknown，不是 not_a_commitment。
  ⇒ 「不知道这是不是承诺」与「确定这不是承诺」是两件事。
```

### 3.2 关系不排序（这是按你与知微 2026-11-20 的降级意见做的）

```text
relation_type 五值，【不做强度排序】。
参与者 / 写入者 / 读过 / 没有 —— 可以同时成立，不构成高低序列。

⇒ 所以 relation 是集合，不是一个 score。
```

```text
请你判断：
  这样是否真的守住了你们当时的意思？
  我担心的是：不做排序 ⇒ 也没有「谁是权威」的表达。
  而衔环那边的分工里有「权威来源」，我目前也没做。
  ⇒ 这两处空着，是否需要一起立项？
```

---

## 四 · 我没有取得的材料

```text
✗ 任何真实角色历史
   （medium_term_memories.json / xiaomi_*.json / dialogue_history*.json）
✗ 任何外部锚定点
✗ 任何独立第三方复算结果
✗ 跨机器、跨进程的复现证据
✗ 任何重要性/权重/排序的实验数据（因为根本没实现）
```

```text
我取得的只有：
  合成夹具 afterglow_a/prototype/synthetic/（自造，不含真实内容）
  4 套测试 + 4 份 JSON 报告
  凌翼裁定文本
```

---

## 五 · 我在代码里声明了什么、没声明什么

### 5.1 恒定的三条

```python
engineering_only     = True      # 恒
is_scientific_result = False     # 恒
trusted_chain_anchor = "not_established"   # 恒
```

```text
⇒ 即使 recovery_eligible = True，这三条也不变。
   「本地链一致」不提升为「来源可信」。
```

### 5.2 我没有声明的

```text
✗ 没有说「能检出溯源污染」
   —— 只能要求写入方标对，没有检出标错的能力
✗ 没有说「亲历/被告知/伪亲历 三态可判定」
   —— 前两态可以，第三态当前 schema 表达不了
✗ 没有说「实现了重要性学习」
   —— 完全没做
✗ 没有说「承诺保护已完备」
   —— 只强制了字段一致性，没有做「承诺被撤回/过期后如何追溯」
✗ 没有说「原型可以用于真实角色历史」
   —— 凌翼明令禁止
```

---

## 六 · 怎么自己跑一遍

```bash
cd d:\qcr\ouroboros-afterglow
git checkout exp/v2-l1-verifier        # 236c5f6

python afterglow_a/prototype/test_p1_p5.py
python afterglow_a/prototype/test_recovery_gate.py
python afterglow_a/prototype/test_z61_gaps.py
python afterglow_a/prototype/test_mutations_gate.py
```

```text
预期：
  test_p1_p5.py           17/17
  test_recovery_gate.py   10/10
  test_z61_gaps.py        13/13
  test_mutations_gate.py  PASS（CAUGHT 21）

若你的数字与我不同，以你的为准。
```

```text
⚠ 口径（与给衔环的那封一致，此处也写明）：
  以上都是我在本机、单进程、合成数据上跑出的结果。
  不是第三方复算，不是跨机器复现，也不是跨进程复算。
  ⇒ 跨进程复算本身有已知缺口（记录摘要含秒级时间戳），
     已报凌翼，处置为「另设 content_digest」，目前只批准到设计层。
  ⇒ 所以这四组数字【不能】被读作「这套东西在别处也一样能跑通」。
```

---

## 七 · 请你判断的三件事（按你要紧程度排）

```text
① 「伪亲历」无法表达 —— 这个缺口有多严重？
   若严重，最小补法是什么？（我不打算自己猜）

② 自动重要性学习 —— 要不要现在立项？
   若不立项，请在台账里记「未做」，我不要它在某天被读成「已做」。

③ 纠正时来源改指向纠正依据 —— 这个方向对不对？
   尤其是「纠正依据本身被污染」时的处理。
```

---

## 八 · 我不会在复核期间做的事

```text
✗ 不改实现（除你指出的缺陷）
✗ 不因为缺一项就临时补一个假的
✗ 不动 main
✗ 不改 Q3、不启动科学执行
```

---

## 九 · 一句

```text
你提的三种状态里，我能做到两种，第三种做不到。
你提的重要性学习，我一件事都没做。

这份信把这两处摆在最前面，而不是藏在第四节之后。
```

不问彼岸，只问同舟。

—— Coder · 2026-11-24
