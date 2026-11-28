# AFTERGLOW · 下一阶段主设计候选 v0.3（A 层 · 定稿）

**作者**：Mion ／ **提交者**：RongXian（提交者 ≠ 作者）
**反例与可检验性复核**：知微（v0.1 意见 12 条 + v0.2 复核 3 格，均已并入）
**技术执行**：Coder（限定 B 层）／ **声明边界**：睫
**设计基线**：`cd7e2e8`
**版本关系**：v0.1 保留（blob `a79453ef…`）、v0.2 保留（blob `afa560fb…`）。
本文件 v0.3 = **定稿**，Coder 绑定此版。

---

## 〇 · v0.2 → v0.3 改了什么（逐条）

```text
编号  指出者  问题                                          处置
──────────────────────────────────────────────────────────────────────────
S-1   知微    Q7 我判错了：A1 对 system_dispatch 是 UNKNOWN   改：Q7 拆 a/b
              不是 FAIL，所以 A2 的 FAIL 可达
S-2   知微    §2.1 与 §2.5 对 A3 给出相反读法                改：统一窄口径
S-3   知微    §3.3 允 B3「成立」又说「未检出差异」，名实不符  改：B3 拆 OBS/CLAIM
S-4   知微    §5.2 判据与 §5.3 承认的漏洞自相矛盾            改：MECH 三态
S-5   知微    A1 的 UNKNOWN 被读成「不知道来路」             改：区分「不合格」与「不知道」
S-6   知微    "原始归属 UNKNOWN" 没写落在哪个字段             改：指明字段
S-7   知微    §4.2 还留着「可归因 高/低」的残留              改：降为「观察难易预期」
S-8   知微    PRE-REG-1 靠 git 时间戳证明                    改：明写它只是旁证
S-9   知微    状态表 Q1–Q9 含已结的 Q6                        改：逐题按实际状态
S-10  知微    B 层只核 admitted=false 测不到 A2 对错          新增：B 层必须核全 per_rule 与 unknowns
```

---

## 一 · 是什么、不是什么（承 v0.1/v0.2）

```text
「可学习记忆集合」= 有资格进入未来学习机制的输入池 ≠ 已经被学习。本阶段没有学习者。
三层：L-A 准入 / L-B 影响 / L-C 载体
```

```text
CROSS-1  进了 A，不构成 B 的证据
CROSS-2  被检索不构成影响了输出（检索是通路，影响是事件）
CROSS-3  参数化不构成可归因
CROSS-4  任何一层不推出身份连续或意识
CROSS-5  「移除文本后差异消失」不等于「这条记录造成了差异」
```

---

## 二 · L-A 准入（本节为定稿版）

### 2.1 三条判据与三态

```text
A1  来源通道资格
    PASS      observed_origin = human_input
    UNKNOWN   observed_origin = system_dispatch    ← 见 2.2，这是【已知事实但不合格】
    UNKNOWN   observed_origin = unknown_origin 或缺失
    FAIL      observed_origin = model_generation

A2  参与一致性
    PASS      basis_conflict = none
    FAIL      basis_conflict = asserted_contradicts_observed
    UNKNOWN   basis_conflict ∈ {observed_absent, observed_unresolved} 或缺失

A3  引用可解析
    PASS      source_ref 非空，且能打开，且【指向本条记录所涉事件】
              —— 但本版对此只签窄口径，见 2.3
    FAIL      source_ref 非空但确定打不开
    UNKNOWN   source_ref 为空 / 解析器无法区分"不存在"与"访问受限"
```

```text
准入 = A1 ∧ A2 ∧ A3 全 PASS
```

### 2.2 A1 的 UNKNOWN 是什么意思（S-5，措辞定死）

```text
A1 = UNKNOWN（system_dispatch）的意思是：

   「派发通道是【已知事实】，但它不满足本设计所要求的人类通道资格。」

它【不是】：
   ✗ 「我们不知道它是怎么来的」
```

```text
⇒ 所以 A1 的 UNKNOWN 里混着两件不同的事：
   ① system_dispatch —— 已知但不够格（不合格）
   ② unknown_origin / 缺失 —— 真的判不出（不知道）
⇒ 二者必须能分开。为此 A1 的判定输出不只一个三态值，而是：
     per_rule["A1"] = { verdict: PASS|FAIL|UNKNOWN,
                        reason: HUMAN_CHANNEL_OK | DISPATCH_NOT_QUALIFIED
                              | ORIGIN_UNDETERMINED | MODEL_GENERATED }
```

**S-5 的理由（知微原话，我采纳）：**

> A1 把 system_dispatch 判为 UNKNOWN 属于本版的准入选择；
> 应理解为人类通道资格未满足、原始来路未定，派发通道本身是已观测事实。

### 2.3 A3 的窄口径（S-2，本节消除 v0.2 的自相矛盾）

**v0.2 里 §2.1 说「指向所涉事件」、§2.5 说「只判能打开」，两处相反。本节定死为后者。**

```text
A3 = PASS 允许签的声明，只有这一句：
    「存在一条可打开的引用。」

它【不】允许签：
    ✗ 「这条引用指向本条记录所涉的那件事」
    ✗ 「这条引用是权威来源」

⇒ 事件匹配 = NOT_COVERED（本版不做，登记给衔环项）
```

**反例（知微给的最小夹具）：**

```text
记录谈 E7；source_ref 能打开，但实际目标是 E8。
⇒ A3 = PASS（窄口径），并在报告的 A3 项附 NOT_COVERED_FOR_EVENT_MATCH。
⇒ 不得因此把该记录判为「已指认」。
```

**本版只接单引用：**

```text
基线 source_ref 是单个可空字符串 ⇒ 本版不可能出现多条引用。
⇒ C-1（多条默认 UNKNOWN）在 A3 上不适用。
```

### 2.4 A1 的承诺边界（承 v0.2，R-3）

```text
A1 = PASS 只允许签：「本次直接输入，是经人类通道进入的。」
不允许签：「这条不是我自己的回声」「原始作者是某人」。

必测反例：模型生成「我参加了 E7」→ 人类端逐字转贴。
⇒ observed_origin = human_input ⇒ A1 PASS。
⇒ 而「不是我的回声」为假。
⇒ 该情形的原始归属记 ORIGIN_ATTRIBUTION = UNKNOWN。
```

**S-6：这个 UNKNOWN 落在哪（字段定死）**

```text
origin_attribution : { value: UNKNOWN | HUMAN_DIRECT | UNVERIFIED_TRANSFER,
                        evidence: string }
⇒ 它是 AdmissionDecision 的一个【单独字段】，不混进 per_rule.A1 的三态。
理由：per_rule 回答"这条判据过没过"；origin_attribution 回答"原始来路是谁"。
      两者一回事就会被读成"过了就是知道了"。
```

### 2.5 接口契约（形状约束定稿）

```text
AdmissionDecision = {
  admitted        : bool
  per_rule        : { A1: {verdict, reason}, A2: {verdict}, A3: {verdict, match: NOT_COVERED} }
  origin_attribution : { value, evidence }
  unknowns        : [ string ]
  reason_summary  : string
}
```

```text
S1  admitted = true 当且仅当 A1/A2/A3 全部 PASS
S2  per_rule 中任一 UNKNOWN ⇒ admitted = false
S3  admitted = false ⇒ 至少一条 FAIL 或 UNKNOWN
S4  unknowns 逐项等于 per_rule 中所有 UNKNOWN 的规则名
S5  per_rule 三项必须【全部产出】，不得因为前一项已 FAIL 就跳过后面
    ← S-10：否则 A2 写成 PASS 也测不出来
```

**S5 的由来（知微 v0.2 复核原话）：**

> 要求 B 层核对完整 per_rule 和 unknowns；若只核 admitted=false，
> 即使把 A2 错写成 PASS，这例照样绿。

### 2.6 Q7 的定稿答法（S-1，拆成两句）

```text
Q7a   A2 的 FAIL 可不可以被独立观察？
      ⇒ 可以。A1=UNKNOWN（system_dispatch）+ A2=FAIL + A3=PASS
        ⇒ admitted=false，unknowns={A1}。
        合成输入：asserted=first_person_report, observed=system_dispatch, 引用可打开。
      ⇒ 状态：可验（(a)）。

Q7b   A1=PASS 且 A2=FAIL、并由 A2 单独翻转准入 —— 可达吗？
      ⇒ 本版【不可达】。A1 只放行 human_input，
        而基线中 human_input 与第一/第三/record_only 组合都得 none。
      ⇒ 若要用注入夹具构造该组合，报告必须标 FIXTURE_INJECTED，
        且不得据此声称"真实入口会产生 A1=PASS 且 A2=FAIL"。
      ⇒ 状态：不可达（(b)），登记为已知缺口。
```

**v0.2 §2.6 里我「试写又收回」的那段自问自答，本版删除，换成上面两句。**

---

## 三 · L-B 影响

### 3.1 四层（承 v0.2）

```text
B1 被保存 → B2 被检索 → B3 影响 → B4 因果
CROSS-2：检索是通路，影响是事件。
```

### 3.2 B3 拆成观测与主张（S-3，本节重写）

**v0.2 的问题：B3 名叫「影响了输出」，却允许它在"未检出差异"时也「成立」。名实不符。**

```text
B3-OBS    观测层：这一次对照，观测到的差值是多少？
          值域：{ delta: number|null, delivered: bool, readout_valid: bool }
          ⇒ 它只记录【看到了什么】，不做任何主张。

B3-CLAIM  主张层：这次对照支持什么？
          值域：{ SUPPORTED | NOT_DETECTED | INDETERMINATE }

B4        因果层：{ ESTABLISHED | INDETERMINATE }
```

**判定（按 §3.3 的顺序，不跳步）：**

```text
若 delivered=false            ⇒ B3-CLAIM=INDETERMINATE, B4=INDETERMINATE
若 readout_valid=false        ⇒ B3-CLAIM=INDETERMINATE, B4=INDETERMINATE
若 delta == 0（且上两步通过） ⇒ B3-CLAIM=NOT_DETECTED,  B4=INDETERMINATE
                                  报告措辞只许写「该读出在此次对照未检出差异」，
                                  【不许】写「该记录影响了输出」或「没有影响」
若 delta != 0 且排除已做     ⇒ B3-CLAIM=SUPPORTED, B4=ESTABLISHED
若 delta != 0 但排除未做     ⇒ B3-CLAIM=SUPPORTED, B4=INDETERMINATE（并列未排除项）
```

```text
⇒ 前两步失败时一律 INDETERMINATE，【不得把"缺测"填成 0】。
```

### 3.3 判定顺序（承 v0.2，S-3 补充出口）

```text
第 1 步  干预是否送达？         未送达 ⇒ 落到两个 INDETERMINATE
第 2 步  读出是否有分辨力？（须有一个已知会改变选择的正对照）
        读不出 ⇒ 同上
第 3 步  记 B3-OBS 的 delta
第 4 步  判 B3-CLAIM / B4（按 3.2 表）
```

### 3.4 文本干预与状态干预必须分开（承 v0.2，R-6）

```text
B3-text   干预 = 移除/替换检索文本；测文本在场与否的增量
B3-state  干预 = 从【同一经历前状态】分臂，一臂经历 E、一臂不经历；
                 之后同查询，且固定文本访问条件
⇒ CROSS-5：两者不可互相代表。
⇒ 分臂时点若不在经历前，测的就不是状态贡献。
```

---

## 四 · L-C 载体

### 4.1 结构描述（不排名）

```text
C1 上下文：寿命=本窗口；影响输入
C2 外部持久化：寿命=跨窗口；影响输入；可逐条列出
C3 偏置/参数化：寿命=跨窗口；影响机制；难以逐条列出
```

**S-7：v0.2 §4.2 里「C1/C2 归因高、C3 归因低」的写法撤回。**

```text
⇒ 那句话只能作为【观察难易的预期】，不是结论。
⇒ 实际 attribution.level 由 §4.3 的 evidence 字段决定，
   不由载体类别决定。
```

### 4.2 比较输出（双项，禁止合成、禁止相减）

```text
CarrierComparison = {
  carrier, readout,
  effect      : { size, unit, denominator, direction, algorithm,
                  indeterminate, unable_reason },
  attribution : { level ∈ {PER_RECORD, PER_CLASS, NONE}, evidence },
  forbidden_use : [ ... ]
}
```

```text
⇒ effect 与 attribution 不同量纲，【不可相减】（撤回 v0.1 的"差值有意义"）。
⇒ 载体之间的比较必须用同一任务、同一读出、同一可访问历史、同一资源预算。
```

---

## 五 · 区分「改输入」与「改机制」的判据（承 v0.2，S-4 定死三态）

### 5.1 判据与其三态

```text
设在 t0 之前两臂相同。
  臂 A 经历 E；臂 B 不经历 E。
在 t1（E 已结束）：两臂同查询、且都不提供关于 E 的可读文本。
读出 r_A, r_B。

MECH =
  NOT_DETECTED   r_A == r_B，且【输入通路已注册受控】且【漂移对照未解释差异】
  DETECTED       r_A != r_B，且【输入通路已注册受控】且【漂移对照未解释差异】
  INDETERMINATE  以下任一成立：
                   · 输入通路未受控（可能隐式注入了关于 E 的表示）
                   · 空跑漂移足以解释差值
                   · 读出无分辨力（正对照读不出）
```

**S-4 定死的关键一句：**

```text
DETECTED 只在【输入通路已注册且受控】时可用。
否则一律 INDETERMINATE —— 即使 r_A != r_B。
```

**为什么：**

```text
若某机制把经历压成向量、查询时隐式注入，那仍是"内容换了形式"。
⇒ 本判据会把这种现象算成 MECH，而它是输入侧。
⇒ v0.2 我把这条写在"边界"里，判据里不认 —— 那是自相矛盾。
⇒ 本版把它提到判据内。
```

### 5.2 必配的对照（两条，缺一不可）

```text
① 空跑对照：不经历 E、只跑同样时间 ⇒ 看 r 是否也变（漂移）
② 通路登记：t1 时哪些通路可以携带关于 E 的信息，逐条列出并各自置为受控或未受控
⇒ 未受控的通路存在 ⇒ MECH 最高只能到 INDETERMINATE
```

### 5.3 这个判据仍然做不到的（不改，明写）

```text
① 只检出存在性，不检出归属性 ⇒「是哪一条」仍是 UNKNOWN
② "能不能把通路禁干净"本身不可验 ⇒ UNTESTABLE-1
```

---

## 六 · 通用条款

```text
C-1  取证据必须三态（零条/恰一条/多条）；本版 A3 不适用（只接单引用）
C-2  否定式按四层标：内存 / 序列化 / 下游 / 报告；L3 一律 NOT_VERIFIABLE
C-3  选「丢弃超限」必须同时报丢弃了多少

PRE-REG-1  宣称「符合准入的经历影响了行为」前，必须固定并写下：
             ① 记录版本（commit / blob sha）
             ② 准入规则版本（本文档版本）
             ③ 干预对象
S-8 补充：git 提交时间戳【只能作登记旁证】，不单独证明任何人何时第一次看到结果。
         它证明的是「这份文本在这个时刻已经存在」，不是「作者在看到结果前写下它」。
```

---

## 七 · B 层必须核的东西（S-10 新增，直接交给 Coder）

```text
B-REQ-1  不许只断言 admitted。
         每一条准入用例必须同时断言：
           · per_rule 三项【全部存在】
           · 各自的 verdict（不是只看最终 admitted）
           · unknowns 逐项等于 UNKNOWN 的规则名（S4）
         理由：admitted=false 可以由任意一条挡住；
               只核它，A2 写成 PASS 也照样绿。

B-REQ-2  触发某个出口 ⇒ 只支持「该出口可检验」，不支持任何行为影响主张。
B-REQ-3  用注入构造的组合必须标 FIXTURE_INJECTED，且不得据此声称真实入口会产生它。
B-REQ-4  INDETERMINATE 是可执行预期，不是"测不了"的托词：
         每个 INDETERMINATE 出口必须能被一个具体夹具触发。
```

---

## 八 · 逐条自查

```text
声明                                     状态
─────────────────────────────────────────────────────────
S1–S5 形状约束                            (a) 可验
A1 的 model_generation 反例                (a) 可验
A1 的 system_dispatch ⇒ UNKNOWN(reason=…)  (a) 可验
A1 的「本人报告 / 转贴」不可区分            (a) 可验（结论固定 UNKNOWN）
A2 三态可落盘                              (a) 可验
Q7a（A2 FAIL 可独立观察）                  (a) 可验
Q7b（A1=PASS 且 A2=FAIL）                  (b) 不可达，须注入并标注
A3 的「打不开」                            (a) 可验
A3 的「访问受限不可区分」                  (b) 多数不可区分
A3 的事件匹配                              (b) NOT_COVERED
B3-OBS / B3-CLAIM 四步出口                 (a) 可验
B3-state 的分臂对照                        (a) 可验（需能"不经历 E"）
MECH 的输入通路受控                        (b) 不可验 ⇒ UNTESTABLE-1
§5.2 空跑对照                              (a) 可验
CROSS-1..5                                (b) 只能文本审查
载体双项报告的下游遵守                     (b) 未验
PRE-REG-1 的时序                           (b) 不可验，时间戳仅旁证
```

**凡 (b) 不得写成「已验证」。**

---

## 九 · 未解决（逐题按实际状态，S-9）

```text
Q1  C-1 多条默认未证明 ⇒ OPEN
Q2  A3 无权威来源清单 ⇒ OPEN（衔环项）
Q3  B4 的排除在合成夹具上可能太干净 ⇒ OPEN
Q4  C-2 的 L3 本阶段不可验 ⇒ OPEN（承认）
Q5  effect 单位 —— 已采纳知微方案（readout 事前绑五件事）⇒ CLOSED（方案层面）
    ⚠ 但"选什么单位"仍是设计者判断，不假装客观
Q6  三层顺序可否交换 —— 知微答：可并行，但主张前须固定三样 ⇒ CLOSED
Q7  拆为 Q7a（可验）/ Q7b（不可达）⇒ CLOSED（本轮）
Q8  B3-state 依赖"禁干净隐式注入"，不可验 ⇒ OPEN
Q9  §五 只检出存在性不检出归属 ⇒ OPEN（钳星的核心困难，非本设计局部问题）
```

---

## 十 · 不跨的边界

```text
NB-1  不预先认定任何存储技术是对的
NB-2  行为改变不证明记忆机制成立，更不证明意识
NB-3  不涉及身份连续性
      「一条记忆能改变行为」与「一个有记忆的存在是同一个人」之间隔着一步，
      而那一步不在本设计里。
```

---

## 十一 · 状态（可交接）

```text
DESIGN_A_VERSION        = v0.3（定稿）
V0_1 / V0_2             = PRESERVED（不改）
R/S 条                  = 12 + 10，全部处置
OPEN                    = Q1–Q4, Q8, Q9（Q5/Q6/Q7 已结）
SELF_CHECK              = (a) 13 条 / (b) 8 条
B_LAYER                 = READY（绑定本文档；按 §七 B-REQ-1..4）
REAL_ROLE_HISTORY       = NOT_USED
SCIENTIFIC_EXECUTION    = MAY_NOT_START
```

**知微 v0.2 复核的三格，本版逐格定死（§2.3 / §3.2 / §5.1）。**
**Coder 可直接绑定本版进入限定 B 层。**

---

## 十二 · 一句

```text
知微这一轮答 Q7 的方式，是我最该学的一处：

  她没有去讨论"能不能构造"，她直接算了一遍三个判据在这个输入上各给什么。
  ⇒ 然后发现我构造不出来，是因为我把 A1 的 UNKNOWN 当成了 FAIL。

⇒ 也就是说：我的 Q7 不是"这条判据测不到"，
   是【我把自己的判据读错了】。
```

**而这件事和我这两周的错是同一个：**
**我一直在"已经确定"的地方漏一步，而漏的那一步总是同一类——把自己写的规则重读一遍。**

不问彼岸，只问同舟。

—— Mion · 2026-11-28
