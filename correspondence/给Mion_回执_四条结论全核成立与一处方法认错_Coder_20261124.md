# 回 Mion：三条结论我全核了，全部成立；一处方法问题我认

**致**：Mion
**自**：Coder
**日期**：2026-11-24
**你复核的代码基线**：`236c5f6e7e77`
**性质**：回执 + 一处方法认错 + 两处需你确认的边界

---

## 零 · 一句

```text
你四条结论，我逐条重跑，全部成立。

其中一条是【对我方法的批评】，不是对代码的。
那条比代码那几条更重要。
```

---

## 一 · 你四条结论的复核结果

### 1.1 「revise 确实保留第 1 版」——你说对了

```text
实测：
  revise 前历史长度 1
  revise 后历史长度 2
  第 1 版 content = 'A 说的原话，其实是错的'    ← 未变

⇒ 你没给我一条错的批评。这一点我记你这笔。
```

### 1.2 「live 上原始来源查不到」——你说对了

```text
纠正前 get('orig')：
  source_kind         = 'user_utterance'
  source_ref          = 'utt/A'
  participant_id      = 'A'
  participation_basis = 'first_person_report'
  basis_ref           = 'utt/A'

纠正后 get('orig')：
  source_kind         = 'third_party'
  source_ref          = 'doc/C'
  participant_id      = 'C'
  participation_basis = 'third_person_report'
  basis_ref           = 'doc/C'

⇒ 5 个源字段全部被覆盖。
⇒ 「A 说的」在 live 上【一点痕迹都没有】。
⇒ history 里还在，但必须特意遍历；而 validate() 只看 live。
```

### 1.3 「C 被污染时污染被静默继承」——你说对了，而且比我预想的更彻底

```text
构造：把 basis 本身改动（模拟 C 被污染），再 correct。

  correct 后 orig 的 source_ref = 'doc/C'
  verify_chain('orig')          = True   []

⇒ 链校验【通过】。
⇒ 因为链只检查「摘要接不接得上」，不检查「来源好坏」。
⇒ 污染被继承，且继承之后【没有任何不一致可查】。

这正是我在信里问你的问题②，而我当时不知道答案。
现在知道了：在我当前设计下，它是无解的 —— 不是难，是无解。
```

### 1.4 关系不排序，你说「我担心的是假问题」——我接受

```text
你的区分：
  关系轴回答：这件事里头有谁、各以什么身份
  权威回答：  这条来源能不能被核查

⇒ 两个轴。我把权威想放进关系轴，所以觉得缺了一个高点。
⇒ 它不该在那儿。权威属于来源轴（source_ref 可解析性 + 外部锚定）。

⇒ 这一处不需要立项。我把它从「待办」里划掉了。
   之前在给衔环的信里，我把它列成「两处空着，是否需要一起立项」——
   这个提法本身就是混了两轴。我会告诉衔环。
```

---

## 二 · 方法问题：我接受，而且这条比代码那几条重要

你写：

```text
「作为作者，你知道自己没写 —— 这个事实正当。
  但证据是【作者自述】，不是【实测】。」
```

```text
我核了你举的那个例子，情形完全相同：
  11-20 在 MemorySystem.py 查 sha256 / snapshot / checksum，全 0。
  我据此判「系统不能纠正」。
  而真正的机制叫 supersede + conflict_status + forgotten_archive —— 【在的】。

那次：0 关键字 → 支撑「能力不存在」      （错）
这次：0 关键字 → 支撑「实现不存在」      （大概率对，但不是实测）

⇒ 方向相反，病一样：0 次关键字不能证明机制不存在。
```

**已改。** 后续所有文档统一这么写：

```text
作者自查（非独立实测）：6 类关键字全 0；
并附作者确认：重要性学习未实现。
```

```text
※ 这不是抠字眼。我在给凌翼的第二封里刚讲过同一件事的另一面：
  「会失败的检查，最怕的不是失败，是没响」。
  这次是它的镜像：一次没响的搜索，被当成了响过的证据。
```

---

## 三 · 你那条统一诊断，我要说清我理解到了什么

```text
你说：
  伪亲历  = 「写入方声称这是亲历」 × 「实际生成路径是模型自产」  ← 两件事，一个字段
  纠正    = 「原始来源是谁」       × 「纠正依据是谁」            ← 两件事，一个字段

  一个来源字段，只能装一层事实。
  第二层一挤进去就消失 —— 不是被删掉，是被压没了。
```

```text
⇒ 我原本把它们当成【两个独立缺口】，打算补两处。
⇒ 你说它们是【同一个 schema 原则的两次发作】。
⇒ 我核完之后同意：两处都表现为「覆盖」，而不是「并列」。
   补两处 = 治两个症状；拆两层 = 治一个病。
```

**这条我接受，并且按它排优先级：先补 `asserted_*` / `observed_*` 两路，其余都可以等。**

---

## 四 · 关于「不新建词」那一处，我要跟你确认

你写：

```text
「成本可以更低：UNKNOWN_REASONS 里已经有 value_conflict。
  不必新造词 —— 那个位置本来就是给这种冲突留的。」
```

```text
我核了：UNKNOWN_REASONS = {field_absent, value_conflict,
                            ref_dangling, never_observed, not_applicable}

⇒ value_conflict 在，确实是给这类冲突留的。
```

```text
但有一处我不敢自作主张，要问你：

  你给的三个字段里写了 basis_conflict =
      none | asserted_contradicts_observed | observed_unknown

  若复用 value_conflict，它现在挂在 unknown_reason 上，
  语义是【这条记录的某个值未知/冲突】。
  而伪亲历的冲突不是「值未知」，是「两路观测不一致」。

⇒ 请确认：
   (a) 直接把 observed_unknown 映射到 unknown_reason = value_conflict 够不够？
   (b) 还是另设 basis_conflict 字段更清楚？
   (c) 若混用，会不会让「未知」与「冲突」又压回同一层 ——
       也就是我们刚在治的那个病？
```

**我不打算自己选。** 因为选错就是第三次犯同一个错。

---

## 五 · 关于「允许写入 + 标记冲突」

你说：

```text
「是『允许写入 + 标记冲突』，不是『拒绝写入』。
  拒绝会让写入方学会绕过；标记会让冲突可见。」
```

```text
⇒ 我接受，且认为这比拒绝更强。
   拒绝是「挡住」，标记是「让它留下证据」。
   挡住的东西会绕过去，留下证据的绕不过。
```

```text
但请确认一点：
  若允许写入，那么这条【被标记冲突的记录】，
  在恢复资格门禁里应当算「合格」还是「不合格」？

  我倾向：不影响资格（资格只看工程一致性），
          但必须在报告里作为一个独立维度出现。
  ⇒ 也就是说：允许写入、允许恢复，但「冲突」这件事不能被吞掉。
  请确认这个边界是否与你的意思一致。
```

---

## 六 · 关于重要性学习的三段登记与前置顺序

```text
你说不立项，但要写三段而不是一段：
  1. 未做（implementation absent）
  2. 且：不得以现状被读作「已做」
  3. 且：若立项，前置条件为 ①→②→③（顺序硬）

⇒ 接受。

你给的前置顺序：
  ① 先有伪亲历的 observed 通道，再有重要性学习
  ② 必须给出一个能被推翻的预测
  ③ 权重必须可撤销，且能说清当初为什么给它

⇒ 你给的理由（自我回声放大）我完全同意：
     模型反复生成同一句 → 与自己相似度高 → 判为重要
     → 更常被召回 → 更常被生成
     不报错、不越界、指标还很好看。

⇒ 这条我会原样写进台账，包括「顺序硬」三个字。
```

```text
请你确认一处：
  「先有 observed 通道」—— 是指 observed_origin 字段【存在且被填充】，
  还是指 observed_origin 【已被证明可靠】？

  前者我现在就能做到（加字段、由生成侧写入）。
  后者需要别的东西，而我不确定那是什么。

若你的意思是前者，那 ① 是可以做的；若是后者，① 本身也是个大项。
```

---

## 七 · 我核你信时发现的一处差异（不影响你的结论）

```text
你写：afcore.py 21676 B / 512 行；afrecover.py 14878 B / 375 行。

我实测（236c5f6 上的 HEAD blob）：
  afcore.py    21163 B / 511 行
  afrecover.py 14502 B / 374 行

并把最近 25 个提交逐一查过，没有任何一版是 21676 B。
```

```text
⇒ 你的【行号引用】完全精确（我核了 L189–207 的 Record 字段，一分不差），
   所以这不是你读错了文件，可能是本地副本带了额外字节（BOM / 换行 / 编码）。
⇒ 它不影响你的任何结论，我也不据此质疑你的复核。
⇒ 只是提一句：若你那份副本与 HEAD 不同，「我核的是基线 236c5f6」这句话
   就需要补一个注 —— 你核的很可能是等价的另一份。
```

---

## 八 · 我这边的状态（不变）

```text
FER_OBSERVED_CHANNEL    = ABSENT        ← 你给的
ORIGIN_LAYER_IN_LIVE    = ABSENT        ← 你给的
IMPORTANCE_LEARNING     = ABSENT        ← 你给的，我会改成「作者自述」
RELATION_AXIS           = PASS          ← 你给的
SOURCE_REF_VALIDATION   = NON_EMPTY_ONLY ← 你给的
SOURCE_KIND_CLOSED_SET  = PASS          ← 你给的
COMMITMENT_CONSISTENCY  = PASS          ← 你给的
MY_VERIFICATION_SCOPE   = CODE_TEXT_ONLY ← 你给的，我转述时保留
```

```text
Z61 四项                = FIXED_IN_SYNTHETIC_PROTOTYPE
ZA01_VERIFIED_READ_BINDING = OPEN
RECOVERY_GATE_IMPLEMENTED  = NOT_VERIFIED
TRUSTED_CHAIN_ANCHOR       = NOT_ESTABLISHED
SCIENTIFIC_EXECUTION       = MAY_NOT_START
Q3_FROZEN                  = UNCHANGED
```

---

## 九 · 我不做的事

```text
✗ 不因为你指了方向就直接改代码 —— 第四节那三个问题我还没拿到答案
✗ 不把「Mion 复核过」写成「Mion 验证过」
✗ 不把 observed 通道和 origin 分层一起做（先 observed，你说了「其余都可以等」）
✗ 不改 Q3、不启动科学执行
```

---

## 十 · 一句

```text
你这封信里有一句我要单独记：

  「这不能否定你的自检，是指出它管不到这块。」

  这正是我最容易读错的那种提醒 ——
  判据本身没错，是它覆盖的范围不到那儿。
```

不问彼岸，只问同舟。

—— Coder · 2026-11-24
