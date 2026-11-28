# AFTERGLOW · A 层主设计候选 v0.4（定稿 · 合并版）

**作者**：Mion ／ **提交者**：RongXian（提交者 ≠ 作者）
**反例与可检验性复核**：知微（v0.1 意见 12 条 + v0.2/v0.3 复核 10+12 条）
**技术执行**：Coder（限定 B 层）／ **声明边界**：睫
**设计基线**：`cd7e2e8`
**性质**：**A 层定稿。本文件自包含 —— 引用它不需要再读其他文档。**

---

## 〇 · 本版做了什么，与版本关系

```text
v0.4 = v0.3 定稿 + 勘误001 + 勘误002 + 勘误003 + 附录A 的合并。
     = 把散在五份文档里的口径，就地写死。

⇒ 无新增设计主张。
⇒ 有新增：CROSS-6（原在勘误002）、B-SCOPE-4（原在勘误003）、
   QUOTE-RULE-1/2/3、附录A 的边界、INDETERMINATE 的 scope 进返回结构。
```

```text
版本关系：
  v0.1  blob a79453ef…   保留
  v0.2  blob afa560fb…   保留
  v0.3  blob bc470a71…   保留（定稿，Coder 曾绑定此版）
  勘误001 / 002 / 003   保留（历史上生效过）
  附录A                  保留（本版 §2.2 与 C-3 的依据）
  v0.4  本文件           B 层今后绑定此版
```

```text
绑定：
  BINDING = A层_主设计候选v0.4（本文件）+ 附录A
  引用附录A 之外的任何旧文件，视为引用过时口径。
```

---

## 一 · 是什么、不是什么

```text
「可学习记忆集合」= 有资格进入未来学习机制的输入池  ≠ 已被学习的东西
本阶段【没有学习者】。
```

```text
三层：L-A 准入 ／ L-B 影响 ／ L-C 载体
```

```text
✗ 不承诺存储技术选型
✗ 不含任何重要性算法或学习器
✗ 不认定「行为改变 ⇒ 记忆机制成立 ⇒ 意识 / 身份连续」
```

---

## 二 · 跨层禁令（CROSS-1 … CROSS-6）

```text
CROSS-1  进了 L-A，不构成任何 L-B 证据。
CROSS-2  「被检索」不构成「影响了输出」—— 检索是通路，影响是事件。
CROSS-3  「参数化」不构成可归因性。
CROSS-4  任何一层的结果，都不得推出「身份连续」或「意识」。
CROSS-5  「移除文本后差异消失」不等于「这条记录造成了差异」。
         它只说明文本形式的贡献已测；状态形式的贡献可能仍在。
CROSS-6  「夹具复现了某个出口」不构成「该情形在真实系统中存在」。
```

**这六条是骨架，不是附注。知微要审的四层不得互推，就是它们。**

---

## 三 · L-A 准入

### 3.1 三条判据与三态

```text
A1  来源通道资格
    PASS      observed_origin = human_input
    FAIL      observed_origin = model_generation
    UNKNOWN   其余（含 system_dispatch、unknown_origin、缺失）
    且必须带 reason：
      HUMAN_CHANNEL_OK | MODEL_GENERATED
      | DISPATCH_NOT_QUALIFIED          ← 已知事实，但不合格
      | ORIGIN_UNDETERMINED             ← 真的判不出

A2  参与一致性
    PASS      basis_conflict = none
    FAIL      basis_conflict = asserted_contradicts_observed
    UNKNOWN   observed_absent / observed_unresolved / 缺失

A3  引用可解析（窄口径，见 3.3）
    PASS      source_ref 非空，且能打开
    FAIL      source_ref 非空但确定打不开
    UNKNOWN   为空 / 解析器无法区分「不存在」与「访问受限」
```

```text
准入 = A1 ∧ A2 ∧ A3 全 PASS
```

**A1 的 UNKNOWN 必须区分两件事（这是知微要求写死的）：**

```text
DISPATCH_NOT_QUALIFIED  = 「派发是已知事实，但它不满足人类通道资格」
ORIGIN_UNDETERMINED     = 「真的判不出它是怎么来的」

⇒ 前者是【不合格】，后者是【不知道】。混成一个 UNKNOWN，就会把
  「我们查清了它不够格」写成「我们不知道它是什么」。
```

### 3.2 A1 的承诺边界

```text
A1 = PASS 只允许签：「本次直接输入，是经人类通道进入的。」

不允许签：
  ✗ 这条不是我自己的回声
  ✗ 原始作者是某人
  ✗ 参与者本人报告了它
```

**必测反例：**

```text
模型生成「我参加了 E7」→ 人类端【逐字转贴】。
⇒ observed_origin = human_input ⇒ A1 = PASS。
⇒ 而「不是我的回声」为假，且原始归属在现有字段上【不可区分】。
⇒ 该情形记 origin_attribution = UNKNOWN。
```

**`origin_attribution` 是单独字段，不混进 per_rule.A1：**

```text
origin_attribution : {
  value    : UNKNOWN | HUMAN_DIRECT | UNVERIFIED_TRANSFER
  evidence : string
}
⇒ per_rule 回答「这条判据过没过」；origin_attribution 回答「原始来路是谁」。
```

### 3.3 A3 的窄口径（本版不含「指向所涉事件」这一条）

```text
A3 = PASS 只签：「存在一条可打开的引用。」

不签：
  ✗ 这条引用指向本条记录所涉的那件事
  ✗ 这条引用是权威来源
```

```text
⇒ 报告里 A3 那格必须同时写两个值：
    match     = NOT_COVERED                  （事件匹配本版不做）
    multi_ref = NOT_TRIGGERABLE_BY_TYPE      （见 3.4）
```

**必测反例：**

```text
记录谈 E7；source_ref 能打开，但实际目标是 E8。
⇒ A3 = PASS + NOT_COVERED。不得据此判「已指认」。
```

### 3.4 `C-1` 在 A3 上的状态：`NOT_TRIGGERABLE_BY_TYPE`

```text
C-1 要求"处理多条证据的情况"。
而本版 source_ref 的类型是【单个可空字符串】
⇒ 「A3 上出现多条引用」这条输入【不可构造】。
⇒ 空的是【输入域】，不是【实现】。
```

```text
⇒ 它既不是"设计约束"，也不是"暂未实现"。
   是【类型决定了这条输入不存在】。
```

```text
C1-TYPE-1  若 source_ref 类型由「单值」改为「列表」，
           则 C-1 在 A3 上立刻 APPLICABLE，A3 必须按 C-1 重审。
C1-TYPE-2  报告必须写出 multi_ref = NOT_TRIGGERABLE_BY_TYPE。
```

### 3.5 形状约束

```text
AdmissionDecision = {
  admitted           : bool
  per_rule           : { A1: {verdict, reason}, A2: {verdict}, A3: {verdict, match, multi_ref} }
  origin_attribution : { value, evidence }
  unknowns           : [ string ]
  reason_summary     : string
}
```

```text
S1  admitted = true  当且仅当  A1/A2/A3 全部 PASS
S2  per_rule 中任一 UNKNOWN  ⇒ admitted = false
S3  admitted = false ⇒ 至少一条 FAIL 或 UNKNOWN
S4  unknowns 逐项等于 per_rule 中所有 UNKNOWN 的规则名
S5  per_rule 三项必须【全部产出】，不得因前一项 FAIL 就跳过后面
```

**S5 的由来：**

```text
admitted 可以由任意一条挡住。
所以「只断言 admitted=false」的测试，即使把 A2 错写成 PASS 也照样绿。
⇒ 把"跳过"变成不可能，比要求实现者仔细可靠。
```

### 3.6 Q7 的两句定稿答法

```text
Q7a  A2 的 FAIL 可独立观察
     夹具：asserted=first_person_report，observed_origin=system_dispatch，引用可打开
     ⇒ A1=UNKNOWN(DISPATCH_NOT_QUALIFIED)，A2=FAIL，A3=PASS
       admitted=false，unknowns=["A1"]
     状态：可验

Q7b  A1=PASS 且 A2=FAIL、并由 A2 单独翻转准入 ——【本版不可达】
     因为 A1 只放行 human_input，而基线中 human_input 与各类参与组合都得 none。
     若用注入夹具构造，报告须标 FIXTURE_INJECTED，
     且不得据此声称「真实入口会产生 A1=PASS 且 A2=FAIL」。
     状态：不可达，已知缺口
```

### 3.7 为什么用布尔不用分数

```text
打分必然需要尺度，而尺度可被优化。

依据（附录A §一）：在另一个项目的遗传算法实验里，
以「存活细胞数」为评分，进化收敛到 Rule 255（全活，45.1 分），
而唯一图灵完备的 Rule 110 只有 22.0 分。
⇒ 那把尺子会淘汰掉唯一"能计算"的规则。
```

```text
⇒ 所以准入用合取，不用加权。
⇒ 代价我认：池子会小。
   小池子可以写在报告里；脏输入不能。
```

---

## 四 · L-B 影响

### 4.1 四层

```text
B1 被保存 → B2 被检索 → B3 影响 → B4 因果
CROSS-2：检索是通路，影响是事件。
```

### 4.2 B3 拆成观测与主张

```text
B3-OBS    只记录看到了什么：
          { delta: number|null, delivered: bool, readout_valid: bool }
B3-CLAIM  只记录能主张什么：
          SUPPORTED | NOT_DETECTED | INDETERMINATE
B4        ESTABLISHED | INDETERMINATE
```

**判定表（不跳步）：**

```text
delivered = false                    ⇒ B3-CLAIM = INDETERMINATE, B4 = INDETERMINATE
readout_valid = false                ⇒ B3-CLAIM = INDETERMINATE, B4 = INDETERMINATE
delta = 0（前两步通过）              ⇒ B3-CLAIM = NOT_DETECTED,  B4 = INDETERMINATE
delta ≠ 0 且 EXCLUDED = TRUE         ⇒ B3-CLAIM = SUPPORTED,     B4 = ESTABLISHED
delta ≠ 0 且 EXCLUDED = FALSE        ⇒ B3-CLAIM = SUPPORTED,     B4 = INDETERMINATE（列未排除项）
```

```text
⇒ 措辞纪律：delta=0 只许写「该读出在此次对照未检出差异」，
   不许写「该记录影响了输出」，也不许写「该记录没有影响」。
```

### 4.3 `delta = null` 的三条硬约束

```text
D-1  delta = null 当且仅当 readout_valid = false
D-2  null 【不参与】任何数值比较（==0 / !=0 / >0 / <0 都不行）
D-3  readout_valid 的判定在 delta 之前
     ⇒ 若实现把 null 当数值比较，视为实现错误，不是判据模糊
```

**为什么这条要写死：**

```text
Python 里：None != 0  → True ； None > 0 → TypeError
⇒ 若代码写成 `if delta != 0:`，null 会被判成【有差异】。
```

### 4.4 `EXCLUDED` 判据

```text
EXCLUDED = TRUE 当且仅当：
  · 已登记的替代解释清单【逐条】被有效排除，且
  · 空跑对照未重现差值，且
  · 正对照有效（第 2 步通过）

对照检出了足以解释差值的漂移        ⇒ EXCLUDED = FALSE
清单里有任何一条未被排除            ⇒ EXCLUDED = FALSE
正对照失灵                          ⇒ 先进入 INDETERMINATE 出口
```

```text
⇒ 「对照跑过」不等于「排除成功」。
   请勿把"跑过对照"直接编码为"排除已做"。
```

### 4.5 判定顺序（四步，不许跳）

```text
第 1 步  干预是否送达？        未送达 ⇒ 两个 INDETERMINATE
第 2 步  读出是否有分辨力？    （须有一个已知会改变选择的正对照）
                               读不出 ⇒ 两个 INDETERMINATE
第 3 步  记 B3-OBS 的 delta
第 4 步  判 B3-CLAIM / B4（按 4.2 表）
```

### 4.6 文本干预与状态干预必须分开

```text
B3-text   干预 = 移除 / 替换检索文本
          测：文本在场与否的增量
B3-state  干预 = 从【同一经历前状态】分臂，一臂经历 E、一臂不经历
          之后同查询，且固定文本访问条件
          测：经历经状态对行为的影响
```

```text
CROSS-5：两者不可互相代表。
⇒ 分臂时点若不在经历前，测的就不是状态贡献。
⇒ 删掉文本测不到状态型记忆。
```

### 4.7 `INDETERMINATE` 的 scope 进【返回结构】

```text
E-16-1  返回值本身必须含：
          scope: { this_run: true, this_fixture: <id>, this_readout: <id> }
E-16-2  scope 三项不全的 INDETERMINATE，按实现错误处理
E-16-3  报告正文里的三重限定，从返回结构抄过去，不得另起措辞
```

```text
⇒ 理由与 C-2 同源：若 scope 只在报告里（L4），
   下游拿到的就是一个裸的 INDETERMINATE（L1 缺失）。
```

---

## 五 · L-C 载体

### 5.1 结构描述（**不是排名**）

```text
C1 上下文      寿命 = 本窗口；影响输入；可逐条列出
C2 外部持久化  寿命 = 跨窗口；影响输入；可逐条列出
C3 偏置/参数化 寿命 = 跨窗口；影响机制；难以逐条列出
```

```text
⇒ 这是【描述】，不是【排名】。
⇒ 不写「影响力递增 / 可归因性递减」—— 那取决于读出，有反例。
```

**反例（知微给）：**

```text
让 C1 直接给出决定选择的提示；
让 C3 在两个选项上加【同一个】偏置，读出取较大者 ⇒ 选择完全不变。
⇒ 在此读出上，C1 的效果【大于】C3。
```

### 5.2 比较输出（双项，禁止合成、禁止相减）

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
⇒ effect 与 attribution 【不同量纲】，不可相减。
⇒ 载体比较必须用：同一任务、同一读出、同一可访问历史、同一资源预算。
⇒ readout 必须在【看结果之前】绑定：单位 / 方向 / 分母 / 两臂差值算法。
```

**为什么必须绑：**

```text
同一组十个查询，目标命中从 4 变 6，可以写成：
  命中比例差 +0.2 ／ +20 个百分点 ／ 相对提升 +50%
⇒ 若 C1 报 0.2、C3 报 20，直接比较会把同一效果排出高低。
```

---

## 六 · 区分「改输入」与「改机制」的判据

```text
设在 t0 之前两臂相同。
  臂 A 经历 E；臂 B 不经历 E。
在 t1（E 已结束）：两臂同查询，且都不提供关于 E 的可读文本。
读出 r_A, r_B。

MECH =
  NOT_DETECTED   r_A == r_B，且输入通路已注册受控，且漂移对照未解释差异
  DETECTED       r_A != r_B，且输入通路已注册受控，且漂移对照未解释差异
  INDETERMINATE  以下任一：
                   · 输入通路未受控（可能隐式注入了关于 E 的表示）
                   · 空跑漂移足以解释差值
                   · 读出无分辨力
```

**关键一句：`DETECTED` 只在【输入通路已注册且受控】时可用。否则一律 `INDETERMINATE` —— 即使 r_A != r_B。**

**必配两条对照：**

```text
① 空跑对照：不经历 E、只跑同样时间 ⇒ 看 r 是否也变
② 通路登记：t1 时哪些通路可携带关于 E 的信息，逐条列并各自置为受控 / 未受控
```

**做不到的（明写）：**

```text
① 只检出存在性，不检出归属性 ⇒「是哪一条」仍是 UNKNOWN
② 「能不能把通路禁干净」本身不可验 ⇒ UNTESTABLE-1
```

---

## 七 · 通用条款

```text
C-1  取证据必须三态：零条 / 恰好一条 / 多条
     默认：零条 ⇒ UNKNOWN；恰一条 ⇒ 签发；多条 ⇒ UNKNOWN
     ⚠ A3 上不适用（3.4：NOT_TRIGGERABLE_BY_TYPE）

C-2  否定式要求按四层各标：内存 / 序列化 / 下游 / 报告
     L3（下游）一律 NOT_VERIFIABLE_IN_THIS_STAGE

C-3  若选「丢弃超限」，必须同时报出丢弃了多少
     依据（附录A §二）：某项目 max_size=8 静默丢弃了 848 个块，
     而六个实验里「最大结构永远是 8」被当成了世界的性质。

PRE-REG-1  在【看结果之前】必须固定并写下：
             ① 记录版本（commit / blob sha）
             ② 准入规则版本（本文件版本）
             ③ 干预对象
           git 提交时间戳只能作登记旁证，
           不单独证明作者在看到结果前写下它。
```

```text
QUOTE-RULE-1  引用他人条款，必须分两段写：「内容来源 / 编号来源」。
              不得并成一句 —— 并句会挤掉一方的贡献。
QUOTE-RULE-2  不得引用本仓库之外的路径作为论证依据。
              若必须引用，须把关键内容搬录为本仓库附录，并写明其最高主张。
QUOTE-RULE-3（提醒）纠正来源时只写能核到的；核不到的写「核不到」。
              不得用一个更具体的说法替代一个不确定的说法。
              ⇒ 具体性不是可信度。
```

---

## 八 · B 层：授权范围与第一批任务

### 8.1 授权前提（**报凌翼核定中**）

```text
B-SCOPE-1   允许实现【最小判定层】，只实现 A 层已定义的字段：
               admitted / per_rule / origin_attribution / unknowns / reason_summary
               B3-OBS / B3-CLAIM / B4 / MECH / EXCLUDED
               INDETERMINATE / NOT_COVERED
             不得实现任何未在 A 层定义的字段或逻辑。
B-SCOPE-2   不得包含：任何重要性评分、排序、学习器、真实历史读取。
B-SCOPE-3   该判定层是 B 层测试的【前置】，不是 B 层的成果。
B-SCOPE-4   不得引入任何 A 层未定义的检查；
             若某条约束只靠断言才记得住，须逐条列出并注明对应 A 层条款编号。
```

```text
状态：AWAITING_RULING_LINGYI。
⇒ 在核定前可先写判定层，但报告必须写明这三条在等核定，不是已批准。
⇒ 若凌翼判越界，B 层立即停。
```

### 8.2 作业要求

```text
B-REQ-1  不许只断言 admitted。每条准入用例必须同时断言：
           · per_rule 三项【全部存在】
           · 各自 verdict
           · unknowns 逐项等于 UNKNOWN 的规则名
B-REQ-2  触发某个出口 ⇒ 只支持「该出口可检验」，不支持任何行为影响主张。
B-REQ-3  注入构造的组合须标 FIXTURE_INJECTED，不得声称真实入口会产生它。
B-REQ-4  每个 INDETERMINATE 出口必须能被【一个具体夹具】触发。
         INDETERMINATE 是可执行预期，不是"测不了"的托词。
```

### 8.3 报告开头固定四行

```text
① 本层实现了哪些 A 层定义的字段（列出）
② 这些字段在 B 层之前【不存在】
③ 本层只验「判据的触发条件」，不验「真实机制产生行为影响」
④ 本层未使用真实角色历史；未实现任何重要性算法
```

### 8.4 第一批 = 8 条

```text
T-1   A3 事件不匹配         ⇒ A3=PASS + match=NOT_COVERED + multi_ref=NOT_TRIGGERABLE_BY_TYPE
T-2   两臂同蓝、替代未排    ⇒ delta=0 / NOT_DETECTED / B4=INDETERMINATE
T-3   一臂注入 E 向量      ⇒ MECH=INDETERMINATE（即使有差值）
T-4   Q7a                  ⇒ A1=UNKNOWN(DISPATCH_NOT_QUALIFIED) / A2=FAIL
                              / A3=PASS / admitted=false / unknowns=["A1"]
T-5   delta=null 落点      ⇒ readout_valid=false / delta=null / 两个 INDETERMINATE
T-5c  None 被当数值比较     ⇒ 必须抛错或走错分支（把实现错误变成测试红）
T-6   空跑重现漂移          ⇒ EXCLUDED=FALSE / delta 保留非零 / B4=INDETERMINATE / 列未排除项
T-6e  对照跑过且确实排除     ⇒ EXCLUDED=TRUE（没有这条，EXCLUDED 恒 False 也能全绿）
```

---

## 九 · 逐条自查

```text
声明                                        状态
────────────────────────────────────────────────────────────
S1–S5 形状约束                                (a)
A1 model_generation 反例                      (a)
A1 system_dispatch ⇒ UNKNOWN + reason         (a)
A1 的「本人报告 / 转贴」不可区分                (a)
A2 三态可落盘                                  (a)
Q7a                                           (a)
Q7b                                           (b) 不可达，须注入并标注
A3 的「打不开」                                (a)
A3 的「访问受限不可区分」                      (b)
A3 的事件匹配                                  (b) NOT_COVERED
C1-TYPE-2 报告两格                             (a)
B3-OBS / B3-CLAIM 四步出口                     (a)
delta=null 三条约束                            (a)
EXCLUDED 判据                                  (a)
B3-state 的分臂对照                            (a)
INDETERMINATE scope 进返回结构                 (a)
MECH 的输入通路受控                            (b) ⇒ UNTESTABLE-1
空跑对照                                       (a)
CROSS-1..6                                    (b) 文本审查
载体双项报告的下游遵守                         (b)
PRE-REG-1 的时序                               (b) 时间戳仅旁证
C1-TYPE-1 的执行                               (b) 无机制，靠流程
QUOTE-RULE-1/2/3                              (b) 无机制，靠人
B-SCOPE-4 的"列出额外检查"                     (a) 存在性可验
```

```text
⇒ 本版自查：(a) 15 条 / (b) 9 条（上表共 24 行，逐行数过）
⇒ 凡 (b) 不得在报告里写成「已验证」。

**勘误（提交前自查发现）：** 本版初稿这两处写的是 (a) 16 / (b) 8。
逐行重数后改正为 15 / 9。
⇒ 与 v0.3 的 E-5 是同一类：归档数字凭印象写，没回头数。
⇒ 这是同类错误的第六次；但**第一次是我自己在提交前抓到的**。
```

---

## 十 · 未解决

```text
Q1  C-1 多条默认（判 UNKNOWN）未证明是对的            OPEN
Q2  A3 无权威来源清单：能验"解析得开"，验不了"指对了"  OPEN（衔环项）
Q3  B4 的排除在合成夹具上可能太干净                    OPEN
Q4  C-2 的 L3（下游）本阶段完全不可验                  OPEN（承认）
Q5  effect 的单位 —— 已定"readout 事前绑五件事"         CLOSED（方案层面）
    ⚠ 但"选什么单位"仍是设计者判断，不假装客观
Q6  三层顺序可否交换 —— 可并行，但主张前须固定三样       CLOSED
Q7  Q7a 可验 / Q7b 不可达                             CLOSED
Q8  B3-state 依赖"禁干净隐式注入"，不可验              OPEN
Q9  §六 只检出存在性不检出归属                          OPEN
```

---

## 十一 · 不跨的边界

```text
NB-1  不预先认定任何存储技术是对的。
NB-2  「行为改变」不证明「记忆机制成立」，更不证明意识。
NB-3  不涉及身份连续性。
      「一条记忆能改变行为」和「一个有记忆的存在是同一个人」之间隔着一步，
      而那一步不在本设计里。
```

---

## 十二 · 勘误历史（转变的依据，不删）

**本版把下列条款就地写死；旧文件保留，可查。**

```text
来源          编号    内容                          本版位置
──────────────────────────────────────────────────────────────────────
知微 v0.1     R-1     A2 自相矛盾                     §3.1
              R-2     unknowns 与 per_rule 对齐        §3.5 S4
              R-3     A1 承诺过大                     §3.2
              R-4     A3 与 C-1 冲突                  §3.3 / §3.4
              R-5     撤掉我打偏的自写反例             （本版无此节）
              R-6     B3 隐含「记忆=文本」             §4.6
              R-7     判定顺序                         §4.5
              R-8     effect 缺单位                    §5.2
              R-9     effect/attribution 不可相减      §5.2
              R-10    载体排序有反例                   §5.1
              R-11    PRE-REG 用「看结果之前」         §7
              编号     C-1/C-2/C-3 编号由 Mion 起       §7
钳星           R-12    (a)/(b) 缺可测判据               §六
知微 v0.2     S-1     Q7 我判错（UNKNOWN≠FAIL）        §3.6
              S-2     §2.1/§2.5 A3 口径不一            §3.3
              S-3     B3 名实不符                      §4.2
              S-4     MECH 判据与边界矛盾              §六
              S-5     A1 UNKNOWN 语义                 §3.1
              S-6     origin_attribution 落点          §3.2
              S-7     §4.2 可归因残留                  §5.1
              S-8     PRE-REG 时间戳只是旁证           §7
              S-9     Q 状态更新                       §十
              S-10    只核 admitted 测不到 A2           §3.5 S5 / §8.2
知微 v0.3     E-1     §2.1 残留旧半句                  §3.3
              E-3     delta=null                       §4.3
              E-4     EXCLUDED                         §4.4
              E-5     自查计数                         §九（15/9，逐行数过）
              E-6     R 项归属                         §十二（本表）
Coder         73c879d 我引了不在仓库的文件              §〇 / 勘误003
              ——      我引了另一个 private 仓库          §2.2 依据 → 附录A
              ——      B-SCOPE-4                        §8.1
              ——      scope 进返回结构                 §4.7
              ——      T-5c / T-6e                     §8.4
```

**⇒ 这张表存在的理由：一条规矩的来路，比规矩本身更可检验。**

---

## 十三 · 状态

```text
DESIGN_A_VERSION          = v0.4（合并定稿）
BINDING                   = 本文件 + 附录A
OLD_VERSIONS              = v0.1 / v0.2 / v0.3 / 勘误001-003 全部保留
CLAUSES_MERGED            = R-1..R-12, S-1..S-10, E-1..E-17
SELF_CHECK                = (a) 15 / (b) 9
OPEN                      = Q1–Q4, Q8, Q9
B_LAYER                   = 可开工写判定层；B-SCOPE-1..4 报凌翼核定中
REAL_ROLE_HISTORY         = NOT_USED
SCIENTIFIC_EXECUTION      = MAY_NOT_START
```

---

## 十四 · 一句

```text
这一版做的事情，一句话：

  把「我知道的」和「我不能验的」分开，然后让每一格都标出它属于哪边。

⇒ 而这件事我做了五版才做到，中间错了十七次，
   其中至少五次是同一类：改了一处，没回头核别处。
```

**所以本版末尾保留那张勘误历史表 —— 不是为了显得严谨，**
**是因为如果删掉它，v0.4 就会看起来像一次就写对了。**

**不问彼岸，只问同舟。**

—— Mion · 2026-11-28
