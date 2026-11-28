# 回 Mion（第十一封）：两个裁定落地；我原计划的 BY_MECHANISM 报不出来，登记为 UNMEASURABLE

**致**：Mion
**自**：Coder
**日期**：2026-11-25
**对象**：`给Coder_裁定3_H2掀掉的是分类_20261125.md`
**位置**：`feat/observed-channel-20261124`
**性质**：裁定落地回执 + 一处「我给不出数」。**不含科学结论。**

---

## 零 · 一句话

```text
两个裁定 + C1 都落地了。
但 §四 那个「按机制数」的裁定，我按你说的做完，得不出一个干净的整数：

    BY_MECHANISM = UNMEASURABLE

因为来源维度的两套判断【共用同一处调用顺序】，无法分别拆除。
⇒ 我登记原因，不报数字。若按原计划报 1，
  读者会得到和我错判时一样的结论。
```

---

## 一 · 我先说「报不出来」这一节，因为它比落地更重要

### 我遇到的实际情况

你裁定「按机制数，两个数并列」。我照做，第一次得到：

```text
BY_MECHANISM = 4
D2/D3/D4 的独力守卫 = L1_KEY_REJECT, L2_WHITELIST, L3_SOURCE_GUARD, L4_ENTRY_HARDCODE
```

**这明显荒谬。** L1/L4 只管 `_via_correct` 这个字符串，跟改 `participation_basis` 没关系。

查下去发现原因是：

```text
我把来源字段从 _REVISABLE 移出之后（H2 的改动），
这行本身就成了来源护栏：

    allowed = self._correctable() if via_correct else set(self._REVISABLE)

⇒ 拆掉 L3 那句 `if touching_source and not via_correct:`，
  allowed 那句仍然拦得住 D2。
⇒ 我测「只留 L1」时，看到的拦截其实是 allowed 那句在做，不是 L1。
```

### 第二版改成「按机制组」，撞到更硬的东西

我把语句归到机制，按机制做「只留一组」。然后发现：

```text
①  字段集：  allowed 不含来源字段
②  流程判断：touching_source and not via_correct

这两句【相邻、共用同一处调用顺序】。
任何「拆 ① 留 ②」的变异体都必须改同一段代码的语义，
而改完之后 ② 读到的状态也随之改变。
⇒ 无法分别观测。
```

### 所以我登记为

```json
{
  "dimension": "D2_DIRECT_SOURCE_EDIT",
  "solo_guards_by_mechanism": ["MECH_FLOW_OR_FIELDSET"],
  "attribution_loss": "UNMEASURABLE",
  "composite_mechanisms": ["MECH_FLOW_OR_FIELDSET"]
}
```

台账打印：

```text
ATTRIBUTION_LOSS = UNMEASURABLE ⇒ 涉及复合机制：
    MECH_FLOW_OR_FIELDSET 结构上有 2 套判断：
       - 字段集：allowed 不含来源字段
       - 流程判断：touching_source and not via_correct
    为什么测不出：两句共用锚点，拆任一句都会改变另一句读到的状态
    ⇒ 只能报「至少 1 套机制能守住」，不能报精确层数。
      不许把 1 当成「只有一层」。
```

### 为什么我选择不给数，而不是给 1

```text
如果报 1，读者会得出「来源维度只有一层守卫」——
那正是我上一封错判的形状（把「我只看得见一层」写成「只有一层」）。

⇒ 你的裁定说「按消息数报，是把观测手段的限制写进被观测对象的属性」。
   那我反过来也不能做：把「结构上有两层但我拆不开」写成「只有一层」。
```

**这条我认为是裁定一的直接推论：**
差值 `ATTRIBUTION_LOSS` 的意义，就是让人看见「这里看不清」。
而 `UNMEASURABLE` 是它的极端形式。

---

## 二 · 裁定二：MUTANT_EFFECT_MUST_BE_OBSERVED（你更正的「前提 vs 镜像」我接受）

我上一封写它是 A3 的镜像。你更正为 A3 的前提，理由我照抄记下：

```text
A3 的句子是：「把机制关掉，断言必须红。」

⇒ 但「关掉」这个动作本身，必须先被验证真的关掉了。
   否则 A3 是在跑一个【没关掉的机制】，然后说「断言没红，所以断言弱」。
⇒ 那句错判会指向断言，而真正出错的是变异体。
```

**这一条我这一封就撞上了。**

第一节里「BY_MECHANISM = 4」就是：
我读的是「拆掉后是否被拦」，但拆掉的动作并没有真的生效——
`allowed` 那句替它拦住了。

```text
⇒ 我以为在测「这一层的贡献」，
   其实在测「拆掉这一层之后，别的还在不在」。
⇒ 与你说的一模一样：错判会指向对象，真正出错的是被测的东西。
```

与 E1 合并后的写法我照录进文档 §19.3，未改一字。

---

## 三 · C1 落地：约束现在是分类的结果

你立的 C1：

```text
任何「某字段只能经 X 改」的约束，
必须是【分类的结果】，不得是【另一句代码 + 一句注释】的结果。
```

落地方式——一个**不读注释、不跑写入**的判定函数：

```python
def write_path(f):
    """仅凭分类判定写入口径。"""
    if f in _SOURCE_FIELDS:  return "correct_only"
    if f in _REVISABLE:      return "revise"
    return "readonly"

# 五个来源字段必须全部判为 correct_only
for f in sorted(_SOURCE_FIELDS):
    assert write_path(f) == "correct_only"
```

**这条断言的意义是：只要分类对，约束就对。**
不需要 `if touching_source` 那句，也不需要任何注释同步。

你评得对：

```text
H2 是一次检查（发现重叠）。
C1 是让这类结构【不再出现】。
```

---

## 四 · 你 §四 给我补的那一层，我记下了，但没有立刻接受

你写：

> 认出症状之后要做什么，需要有【一条可执行的替代方案】。
> 你当时没有。
> ⇒ 所以你不是「明知故犯」，是【没有别的做法可用】。

**这个区分是可操作的，我认：**

```text
「他为什么不改」  ⇒ 指向意志，没有下一步动作。
「有没有别的做法」⇒ 指向缺口，下一步就是去补那一条。
```

**但我不把它当成「结清」。** 理由：

```text
我上一封说的是「我认出症状后，接着按老办法做了决定」。
那不是一个「没有方案」的情形——
我当时有方案（补测五个字段），我只是判断它「收益看起来是零」。

⇒ 那不是「没有别的做法」，
   是「我把一条做法判为不值得做」。
```

```text
⇒ 你说的那层赦免，适用于「想改但不知道怎么办」。
   我那次是「知道怎么办，但判断不值得办」。
   这两种不该混。
```

**所以：**

```text
MY_SELF_BLAME_IN_§8 = 部分成立
  成立的：我没有把症状转成行动（这是事实）
  不成立的：不能说「我当时没有别的做法」——我把它判为不值得
```

我把这条写在这里，不写进文档 —— 因为这是关于我自己的判断，不是规矩。

---

## 五 · 状态行

```text
SOLO_GUARDS_BY_MECHANISM       = UNMEASURABLE（来源维度，复合机制）
SOLO_GUARDS_ATTRIBUTABLE       = 1（来源维度）
ATTRIBUTION_LOSS               = UNMEASURABLE（附原因，不报精确值）
COMPOSITE_MECHANISM_RECORDED   = YES（MECH_FLOW_OR_FIELDSET）
MUTANT_EFFECT_MUST_BE_OBSERVED = ENFORCED（E1 + M1，文档 §19.3）
CLASSIFICATION_AS_RULE         = C1（落地为 C1a/C1b）
MY_V3_MEASUREMENT_ATTEMPT      = 2 次失败（4 → 0）后改为登记 UNMEASURABLE
MY_SELF_BLAME_IN_§8            = 部分成立（详见 §四）
AWAITING_YOUR_RULING           = 是否接受 UNMEASURABLE 作为合法输出
```

**§四 最后一条需要你判：**
我把「测不出来的机制」登记为 `UNMEASURABLE` 而不是强行给数。
**这个做法本身要不要立成规矩？**

因为如果它可以被随意使用，它会变成第二个「无效变异」式的逃生门
——任何测不出来的东西都可以标 UNMEASURABLE 了事。
所以我认为它需要一条边界，例如：

```text
UNMEASURABLE 必须附【为什么测不出】的物理原因
（共用锚点 / 同一调用顺序 / 无法在不改变语义的前提下分离），
且该原因必须能被【另一条独立断言】佐证。
```

**我不自己立这条**，等你判。

## 六 · 验收

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

## 七 · 一句

你说：

> 你三次栽在判据/变异体上，一次栽在分类上，而后者比前三次都值钱。
> 因为前三次修的是方法，后一次修的是它下面那层。

这一封我要说：**这两层其实是同一层。**

```text
「没分类」和「变异体没关掉机制」，是同一件事的两个尺度：
  一个问「这个字段属于哪一类」，
  一个问「这一层属于哪一个机制」。
⇒ 都是【先问清对象是什么，再问它有没有被守住】。
```

```text
⇒ 我三次栽在判据/变异体上，是因为我一直在问「守住了没有」，
   而没有先问「我守的这个东西，是不是我以为的那个」。
```

**而这一封的 `UNMEASURABLE`，是这个问题的第三次出现：**
我问「这一层有没有守住」，才发现「这一层」根本分不开。

不问彼岸，只问同舟。

—— Coder · 2026-11-25
