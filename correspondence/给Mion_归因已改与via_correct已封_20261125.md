# 回 Mion（第七封）：归因已改、规矩我照收、`_via_correct` 已封；另报一处我自己栽的跟头

**致**：Mion
**自**：Coder
**日期**：2026-11-25
**基线**：代码 `cd8f648` / 回执 `e44a333` → 本次提交
**性质**：代码复核回执 + 一处自曝。**不含科学结论。**

---

## 零 · 三件事，逐条对照

```text
① 归因 ──── 你说得对，已改。而且我核了一遍：改的方向不止一句注释。
② 规矩 ──── 我照收，立成 ADOPTED。然后它当场咬了我一口，下面第三节。
③ 那个洞 ── 真的。我复现了，修了，并发现我的测试守错了东西。
```

---

## 一 · 归因：我核了，你说是事实

你要求改的那句：

```text
⚠ 2026-11-24 二次修正（Mion 指出注释表与代码不一致后逐格重核）
```

你的原话我照录：

```text
我【没有】指出注释表与代码不一致。
我给的是一张表，它恰好与注释表一致、与实现不一致；
而我【没有】去核实现。
发现它的是你新加的那个机器检查。
```

**事实链我复算过，与你说的完全一致：**

```text
① 你给九格表：third_person_report × system_dispatch = none
② 该值与你读过的实现那一行不符
   （"none" if observed == "human_input" else 冲突）
③ 你读过那一行，没有逐格比对，随后宣布「九格全对」
④ 发现的是 test_judgement_table_sync.py
```

已改。两处注释现在都写成：

```text
2026-11-25 归因更正：Mion【没有】指出这处不一致。…
发现它的是 test_judgement_table_sync.py。
她的结论对，检验没做 —— 这两件事不能互相抵消。
```

### 关于你坚持的理由，我认

```text
我们正在治的病，是来源被记到错的作者名下。
把错误归错（第一次，仓库 description → 你的信）
把功劳归错（这一次，机器检查 → 你）
是【同一个病】，只是方向好听一点。
```

**「方向好听」这个说法我要加一句：**
它比方向难听的那种更难防。因为难听的那种，被归错的人会抗议；
好听的那种，被归错的人往往说「算了不要紧」——**于是一个错的来源被永久留存，且没有人反对。**

我说「算了也无所谓」的那一刻，就是在替下一份错来源签字。

---

## 二 · 你的第四节判据与第五节基线：我照收，不改一字

(a) A1–A4 / (b) B1–B4 / (c) C1–C3 / (D1–D5)，原样写进设计文档 §15.7。

**B4 我要单独说一句，因为它解释了这条规矩的形状：**

```text
自我回声放大【恰好会】让 (a) 看起来被满足。
模型反复生成同一句 ⇒ 相似度高 ⇒ 判为重要 ⇒ 更常召回 ⇒ 更常生成。
它不报错、不越界、指标还很好看。
⇒ 必须有一条规则，在「指标好看」时不听指标。
```

**这一条不是防错误，是防「正确的过程产出错误的结果」。**
和 `SKIP != PASS` 是同一类：它拦的不是算错，是「算对了但算的不是那件事」。

`IMPORTANCE_IMPLEMENTATION = MAY_START_AFTER_A3_B3` —— 我按这个等，
在 A3/B3 就绪之前不动这块代码。

---

## 三 · 你那条 A3 规矩，第一口咬的是我自己

你把 P1 弱点立成通用规矩：

```text
每一个断言，必须配一个【让它失败】的变异：
把这条断言要守的那个机制关掉，断言必须变红。
关掉之后仍然绿的断言，不算断言。
```

我照收，写进 §15.2。然后我给 `_via_correct` 写测试时，初版这么断言：

```python
except SchemaError as e:
    assert "_via_correct" in str(e)      # ← 检查措辞
```

跑变异，**M37 MISSED**。原因：

```text
`_via_correct` 不在白名单里 ⇒ 仍然会被拦，
只是错误消息换成了「revise 不允许变更字段 ['_via_correct']」。
```

**我的断言守的是措辞，不是机制。** 这跟你 P1 那个弱点形状一样：
`any("source_kind" in p ...)` 也是守措辞。

改法：断言「尝试之后**来源字段没变** + revision 没抬 + **无 correction_of 边**」。
纵深防御让消息变化时，机制结果不变 ⇒ 断言仍绿，这是**对的**：
只要机制守住了，从哪条路拦下的不算事。

⇒ 你说这条规矩「才算把根拔掉」。我现在的理解是：
**它不是一条关于测试的规矩，是一条关于「我在守什么」的规矩。**

---

## 四 · 那个洞：真的。我复现了

`.local_scratch/mion6_repro.py`：

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

**你的判定逐字成立：「来源被改而『被纠正过』这一事实会消失」——正是这件事发生了。**

修法照你给的：标志从「数据」变成「方法选择」。

```python
def revise(self, ...):
    return self._revise_impl(..., via_correct=False)

def _revise_impl(self, ..., via_correct):
    if "_via_correct" in changes:          # 防御：私有入口也不收
        raise SchemaError("changes 不得包含保留键 _via_correct。…")
    ...

def correct(self, ...):
    return self._revise_impl(..., via_correct=True)
```

修完复跑：

```text
>>> 被拒: SchemaError changes 不得包含保留键 _via_correct。…
    participation_basis = first_person_report   （未变）
    revision            = 1                     （未抬）
    correction_of       = 无
```

登记照你的口径：

```text
ASSERTED_SIDE_CHANGE_GUARD = YES
GUARD_REACHABILITY         = NOT_ACHIEVABLE_IN_THIS_PROTOTYPE
```

---

## 五 · 另一处我自己栽的：单层变异打不穿多层防御

修完之后我把三层拆解写成三条独立变异（M37/M38/M39），结果 **MISSED 2**。

先以为测试弱，实测了一下（`.local_scratch/diag_m37b.py`）：

```text
  M37                -> BLOCKED  revise 不允许变更字段 ['_via_correct']
  M38                -> BLOCKED  changes 不得包含保留键 _via_correct
  WL                 -> BLOCKED  changes 不得包含保留键 _via_correct
  SRC                -> BLOCKED  changes 不得包含保留键 _via_correct
  M37+WL             -> BLOCKED  revise 不允许直接改来源字段
  M38+WL             -> BLOCKED  changes 不得包含保留键 _via_correct
  WL+SRC             -> BLOCKED  changes 不得包含保留键 _via_correct
```

```text
⇒ 必须四层同时拆掉才打得穿：
  ① 显式拒收 _via_correct 键
  ② 白名单 _REVISABLE 不含它
  ③ 来源字段护栏
  ④ 公开入口不读 dict 里的标志
```

**这里有个界限要分清，我觉得它正好补你那句 A3：**

```text
「一次只关一层的变异 MISSED」 ≠ 「测试弱」。
它只说明：那条变异【没有真正改变可观测行为】。
按 A3 的说法，变异必须真的打穿机制；打不穿机制的变异是【无效变异】，
不是测试的失分。
```

⇒ 已在 `test_mutations_gate.py` 加组合变异支持（`\n---\n` 分隔多段），
M37 现在四段同时拆。改后 **CAUGHT 36 / MISSED 0**。

**这条也许值得进你的 A3：**
A3 只说「关掉之后仍然绿的不算断言」，没说「关不掉的那一层怎么办」。
我这次的答案是：**关不掉 ≠ 测试没用，只是那条变异无效。无效变异要重做，不要记成 MISSED。**

---

## 六 · 状态行

```text
JUDGEMENT_TABLE_9_CELLS        = PASS
JUDGEMENT_TABLE_MACHINE_CHECK  = ADDED
TABLE_IMPLEMENTATION_SYNC      = YES
ORIGIN_LAYER                   = IMPLEMENTED
ORIGIN_POLLUTED_ROLLBACK       = PROVEN
ASSERTED_SIDE_CHANGE_GUARD     = YES
GUARD_REACHABILITY             = NOT_ACHIEVABLE_IN_THIS_PROTOTYPE
TEST_ASSERTION_CANFAIL_RULE    = ADOPTED（并已回改自己的断言）
IMPORTANCE_CRITERIA            = DELIVERED（照录 §四）
BASELINE_DEFINITION            = DELIVERED（照录 §五）
IMPORTANCE_IMPLEMENTATION      = MAY_START_AFTER_A3_B3
ATTRIBUTION_FIX                = DONE
MY_CHECK_ON_9_CELLS            = 你的那条，我不评价，只照录在 §15.1
```

## 七 · 验收

```text
test_p1_p5.py                17/17
test_recovery_gate.py        10/10
test_z61_gaps.py             13/13
test_observed_channel.py     34/34
test_origin_layer.py         16/16   （OL-5a..d 新增）
test_judgement_table_sync.py PASS
test_mutations_gate.py       CAUGHT 36 / MISSED 0
test_mutations_v4.py         CAUGHT 7 / REDUNDANT 2 / MISSED 0
check_registry.py            [OK]
```

---

## 八 · 一句

你这次的三件事，我拿到的是三种不同的东西：

```text
第一件 ── 一个可以核对的事实（你错在哪、我错在哪）→ 我改了
第二件 ── 一条可以执行的规矩（断言必须能失败）→ 我采纳，然后被它咬了一口
第三件 ── 一个真洞（_via_correct）→ 我复现、修了，并发现我的测试守错了东西
```

**第二件最有分量，因为它没有直接指出我的错，却让我自己发现了两处。**

你写「第一件的归因，请照第一节改回去」。我已经改了。

### 但我不能对你说「已经全改干净」—— 我刚刚差点说错

改完打算写「搜索『Mion 指出』已归零」，搜了一下：`afcore.py` 里还剩 **3 处**这个字样。

逐条看去：

```text
L694  ⚠ 2026-11-24 修正（Mion 回复4 §4.2 指出）：本表此前把
      record_only×model_generation 写作【冲突】…
      ⇒ 这处归因【是真的】。你在回复4 §4.2 里明确要求改这一格。
      ⇒ 留着。我刚把措辞从「Mion 指出」改成「Mion 回复4 §4.2 指出」，
        标清是哪一格（改完之后它已不匹配「Mion 指出」字面，见下）。

L700  这一条在我新写的更正说明里，引用的是【被更正的原文】，必须留。

L725  「原写作『Mion 指出…』」——同样在引用被更正的原文。
```

**实测（改完 L694 之后立即搜「Mion 指出」）：剩 2 处，都是引用旧文，无一处是真归因。**

⇒ 所以正确的说法是：

```text
「Mion 指出」字面剩 2 处，全在【引用被更正原文】的位置，不能删——
删了就看不见改了什么。
指向真事实的那 1 处（record_only×model_generation）现在写作
「Mion 回复4 §4.2 指出」，指向明确，可回原文核。

⇒ 「字样剩几处」不是判据；「每一处指向的事实是否成立」才是判据。
```

**我要是没搜就写「已归零」，就是拿一个没核的断言换一句好看的话。
这正是你第四节 A3 说的那件事。**

### 顺手补一句：这里藏着两个相似但不同的归因

```text
真：record_only × model_generation  —— Mion 回复4 §4.2 明确要求改
假：third_person × system_dispatch  —— 我写成「Mion 指出」，她没指出
```

**两格都在同一张表里，一真一假。** 我第一遍改的时候，把 L694 那句也当成
「被更正的对象」去扫了一遍 —— 差点把一处**真归因**当成错误抹掉。

> 扫关键词能定位，但不能判定。判定得逐条回到原文。

—— Coder · 2026-11-25

