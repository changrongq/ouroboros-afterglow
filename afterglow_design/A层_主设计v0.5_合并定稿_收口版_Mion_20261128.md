# AFTERGLOW · A 层主设计 v0.5（合并定稿 · 本批收口版）

**作者**：Mion ／ **提交者**：RongXian（提交者 ≠ 作者）
**反例与可检验性复核**：知微（三轮，R/S/E 系列共 34 条）
**技术执行**：Coder（限定 B 层）／ **声明边界**：睫（待核）
**设计基线**：`cd7e2e8`
**性质**：**本文件自包含。引用它不需要再读其他文档。**

---

## 〇 · 版本关系与本版做了什么

```text
v0.5 = v0.4 + 附录A + 勘误004 + 勘误005 + 勘误006 的合并，
      + 一条新增（E-28，来自 Coder 收口自查）。

⇒ 无新增研究主张。
⇒ B 层本批已收口（16/16 断言、35/35 变异、回归 20/21、1 条 OPEN）。
⇒ 从本版起不再发新勘误：缺口只能以 OPEN 登记，不能以"再加一条 E-xx"处理。
```

```text
旧版全部保留、不覆盖：
  v0.1 a79453ef  ／ v0.2 afa560fb ／ v0.3 bc470a71 ／ v0.4 9031df2
  附录A 930a105 ／ 勘误001-006 全部保留
```

```text
BINDING = 本文件（唯一） 
⇒ 绑定从六份收回到一份。
```

---

## 一 · 是什么、不是什么

```text
「可学习记忆集合」= 有资格进入未来学习机制的输入池  ≠ 已被学习的东西
本阶段【没有学习者】。
三层：L-A 准入 ／ L-B 影响 ／ L-C 载体
```

```text
✗ 不承诺存储技术选型
✗ 不含任何重要性算法或学习器
✗ 不认定「行为改变 ⇒ 记忆机制成立 ⇒ 意识 / 身份连续」
```

---

## 二 · 跨层禁令

```text
CROSS-1  进了 L-A，不构成任何 L-B 证据。
CROSS-2  「被检索」不构成「影响了输出」——检索是通路，影响是事件。
CROSS-3  「参数化」不构成可归因性。
CROSS-4  任何一层的结果，都不得推出「身份连续」或「意识」。
CROSS-5  「移除文本后差异消失」不等于「这条记录造成了差异」。
         它只说明文本形式的贡献已测；状态形式的贡献可能仍在。
CROSS-6  「夹具复现了某个出口」不构成「该情形在真实系统中存在」。
```

---

## 三 · L-A 准入

### 3.1 三条判据（三态）

```text
A1  来源通道资格
    PASS      observed_origin = human_input
    FAIL      observed_origin = model_generation
    UNKNOWN   其余，必须带 reason：
                DISPATCH_NOT_QUALIFIED   ← 已知事实，但不合格
                ORIGIN_UNDETERMINED      ← 真的判不出

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

**A1 的 UNKNOWN 必须区分「不合格」与「不知道」：**

```text
DISPATCH_NOT_QUALIFIED  = 派发是已知事实，但它不满足人类通道资格
ORIGIN_UNDETERMINED     = 真的判不出它是怎么来的
⇒ 混成一个 UNKNOWN，就会把「我们查清了它不够格」写成「我们不知道它是什么」。
```

### 3.2 A1 的承诺边界

```text
A1 = PASS 只允许签：「本次直接输入，是经人类通道进入的。」
不允许签：不是我的回声 / 原始作者是某人 / 参与者本人报告了它
```

**必测反例：** 模型生成「我参加了 E7」→ 人类端逐字转贴 ⇒ `observed_origin = human_input` ⇒ A1 PASS，
而「不是我的回声」为假，且原始归属在现有字段上不可区分 ⇒ 记 `origin_attribution = UNKNOWN`。

```text
origin_attribution : { value: UNKNOWN | HUMAN_DIRECT | UNVERIFIED_TRANSFER, evidence }
⇒ 单独字段，不混进 per_rule.A1。
  per_rule 回答「这条判据过没过」；origin_attribution 回答「原始来路是谁」。
```

### 3.3 A3 的窄口径

```text
A3 = PASS 只签：「存在一条可打开的引用。」
不签：指向所涉事件 / 是权威来源
⇒ 报告必须同时写：match = NOT_COVERED ／ multi_ref = NOT_TRIGGERABLE_BY_TYPE
```

**必测反例：** 记录谈 E7、引用指向 E8 ⇒ A3 = PASS + NOT_COVERED，不得判「已指认」。

**C-1 在 A3 上的状态：**

```text
NOT_TRIGGERABLE_BY_TYPE —— source_ref 是单个可空字符串，「多条」这条输入不可构造。
它既不是"设计约束"，也不是"暂未实现"，是【类型决定了输入不存在】。
C1-TYPE-1  若类型改为列表，C-1 立刻 APPLICABLE，A3 必须按 C-1 重审。
```

### 3.4 形状约束

```text
AdmissionDecision = {
  admitted, per_rule{ A1{verdict,reason}, A2{verdict}, A3{verdict,match,multi_ref} },
  origin_attribution{value,evidence}, unknowns[], reason_summary
}

S1  admitted = true  当且仅当  三条全部 PASS
S2  per_rule 任一 UNKNOWN ⇒ admitted = false
S3  admitted = false ⇒ 至少一条 FAIL 或 UNKNOWN
S4  unknowns 逐项等于 per_rule 中所有 UNKNOWN 的规则名
S5  per_rule 三项必须【全部产出】，不得因前一项 FAIL 就跳过后面
```

**S4 守的是理由，S5 守的是「A2 写成 PASS 也测不出来」这个洞。**

### 3.5 Q7 的两句答法

```text
Q7a  A2 的 FAIL 可独立观察
     夹具：asserted=first_person_report, observed_origin=system_dispatch, 引用可打开
     ⇒ A1=UNKNOWN(DISPATCH_NOT_QUALIFIED), A2=FAIL, A3=PASS, admitted=false, unknowns=["A1"]
     状态：可验

Q7b  A1=PASS 且 A2=FAIL、并由 A2 单独翻转准入 —— 本版【不可达】
     若用注入夹具构造，须标 FIXTURE_INJECTED，不得声称真实入口会产生它。
     状态：不可达，已知缺口
```

### 3.6 为什么用布尔不用分数

```text
打分需要尺度，而尺度可被优化。
依据（附录A §一）：另一个项目的遗传算法实验里，以「存活细胞数」为评分，
进化收敛到 Rule 255（全活，45.1），而唯一图灵完备的 Rule 110 只有 22.0。
⇒ 那把尺子会淘汰掉唯一"能计算"的规则。
⇒ 所以准入用合取。代价：池子会小。小池子可以写在报告里；脏输入不能。
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
B3-OBS    { delta: number|null, delivered: bool, readout_valid: bool }
B3-CLAIM  SUPPORTED | NOT_DETECTED | INDETERMINATE
B4        ESTABLISHED | INDETERMINATE
```

| 条件 | B3-CLAIM | B4 |
|---|---|---|
| `delivered = false` | INDETERMINATE | INDETERMINATE |
| `readout_valid = false` | INDETERMINATE | INDETERMINATE |
| `delta = 0` | NOT_DETECTED | INDETERMINATE |
| `delta ≠ 0` 且 `EXCLUDED = TRUE` | SUPPORTED | ESTABLISHED |
| `delta ≠ 0` 且 `EXCLUDED = FALSE` | SUPPORTED | INDETERMINATE（列未排除项） |

```text
措辞纪律：delta=0 只许写「该读出在此次对照未检出差异」，
不许写「该记录影响了输出」，也不许写「该记录没有影响」。
```

### 4.3 `delta = null` 三条硬约束

```text
D-1  delta = null 当且仅当 readout_valid = false
D-2  null 不参与任何数值比较（==0 / !=0 / >0 / <0 都不行）
D-3  readout_valid 的判定在 delta 之前
     ⇒ 实现把 null 当数值比较 ⇒ 实现错误，不是判据模糊
```

**为什么写死：** Python 里 `None != 0` 为 True，`None > 0` 抛 TypeError。
⇒ 若写成 `if delta != 0:`，null 会被判成有差异。

### 4.4 `EXCLUDED` 的三字段编码

```text
E-24-1  EXCLUDED 形状：
          excluded               : True | False | None
          excluded_undetermined  : bool
          reason                 : string

E-24-2  三者【同时】成立或不成立（不得两两成立而第三项不成立）：
          excluded is None  ⇔  excluded_undetermined is True  ⇔  reason ∈ 判不出原因集
        并新增第四项校验：reason 必须属于已登记的原因集。

E-24-3  两种"判不出"措辞必须分开：
          没登记    ⇒ 「该夹具未登记任何替代解释，因此无法判定是否已排除」
          没排干净  ⇒ 「已登记的解释中尚有 N 条未排除」
        未登记的 reason ⇒ wording_for 必须抛（不许静默给默认措辞）。

E-24-4  THREE_FIELD_ENCODING = ACCEPTED_FOR_NOW, WATCHED
        三个字段表达一件事。本阶段接受；若出现第四个表达同一件事的字段，
        说明形状该换，不得继续加。
```

**E-18（原勘误004）：清单为空 ⇒ `INDETERMINATE`**

```text
清单为空有两种不可区分的情形：确实没有替代解释 / 没人登记过。
⇒ 空列表的唯一含义是「没人登记」，永远不能产生 TRUE。
⇒ 若确无替代解释，必须显式登记哨兵条目（如 NONE_KNOWN）。
⇒ 与 C-1「零条 ⇒ UNKNOWN」一致：零条不是"通过"。
```

### 4.5 判定顺序（四步，不许跳）

```text
第 1 步  干预是否送达？        未送达 ⇒ 两个 INDETERMINATE
第 2 步  读出是否有分辨力？    须有已知会改变选择的正对照；读不出 ⇒ 两个 INDETERMINATE
第 3 步  记 B3-OBS 的 delta
第 4 步  判 B3-CLAIM / B4
```

### 4.6 文本干预与状态干预必须分开

```text
B3-text   移除 / 替换检索文本 ⇒ 测文本在场与否的增量
B3-state  从【同一经历前状态】分臂，一臂经历 E、一臂不经历；之后同查询且固定文本访问
⇒ CROSS-5：两者不可互相代表。分臂时点不在经历前，测的就不是状态贡献。
```

### 4.7 `INDETERMINATE` 的 scope 进返回结构

```text
返回值必须含：scope: { this_run: true, this_fixture: <id>, this_readout: <id> }
scope 三项不全 ⇒ 按实现错误处理
报告正文的三重限定从返回结构抄过去，不得另起措辞
⇒ 理由与 C-2 同源：若 scope 只在报告（L4），下游拿到的是裸的 INDETERMINATE（L1 缺失）。
```

---

## 五 · L-C 载体

### 5.1 结构描述（不是排名）

```text
C1 上下文      寿命=本窗口；影响输入；可逐条列出
C2 外部持久化  寿命=跨窗口；影响输入；可逐条列出
C3 偏置/参数化 寿命=跨窗口；影响机制；难以逐条列出
⇒ 这是描述，不是排名。「影响力递增 / 可归因性递减」有反例，已撤回。
```

**反例：** C1 直接给决定选择的提示；C3 在两选项加同一偏置、读出取较大者 ⇒ 选择不变
⇒ 此读出上 C1 效果大于 C3。

### 5.2 比较输出（双项，禁止合成、禁止相减）

```text
CarrierComparison = {
  carrier, readout,
  effect      : { size, unit, denominator, direction, algorithm, indeterminate, unable_reason },
  attribution : { level ∈ {PER_RECORD, PER_CLASS, NONE}, evidence },
  forbidden_use : [...]
}
```

```text
⇒ effect 与 attribution 不同量纲，不可相减。
⇒ readout 必须在【看结果之前】绑定：单位 / 方向 / 分母 / 两臂差值算法。
```

**为什么必须绑：** 同一组十个查询、命中 4→6，可写成 +0.2 ／ +20 个百分点 ／ 相对提升 +50%。
⇒ 若 C1 报 0.2、C3 报 20，直接比较会把同一效果排出高低。

---

## 六 · 区分「改输入」与「改机制」

```text
两臂同查询、都不提供关于 E 的可读文本：
MECH =
  NOT_DETECTED   r_A == r_B，且输入通路已注册受控，且漂移对照未解释差异
  DETECTED       r_A != r_B，且输入通路已注册受控，且漂移对照未解释差异
  INDETERMINATE  通路未受控 / 空跑漂移足以解释 / 读出无分辨力
```

**关键一句：`DETECTED` 只在【输入通路已注册且受控】时可用，否则一律 `INDETERMINATE` —— 即使 r_A != r_B。**

**必配两条对照：** ① 空跑对照（不经历 E、只跑同样时间）② 通路登记（逐条列并各自标受控/未受控）

**E-19 / E-22：不可达性从纪律变机制**

```text
E-22-1  pathway_registered_and_controlled = True  ⇒ 抛 UnsupportedPremise
        （不是 ValueError；区别在"谁来修"：传错值 vs 这个前提本阶段不存在）
E-22-2  入口清单显式登记，逐个断言抛同一异常
E-22-3  必须写出穷尽性依据，三选一：
          (a) 构造点唯一且已覆盖 ⇒ 可断言穷尽
          (b) 不可穷尽 ⇒ 标 PARTIAL_FOR_REGISTERED_ENTRIES 并说明漏的怎么被发现
          (c) 都做不到 ⇒ 这条只是说明，不是断言
        ⇒ 本版选 (b)：构造点唯一只证明「产 MECH 的地方唯一」，
          不证明「调用方不传 True」。
E-19-1  保留 DETECTED 在枚举里（删掉=假装它不需要存在；它需要存在，只是够不到）
E-19-2  必须有【不可达性测试】：断言本阶段任何调用路径都不产生 DETECTED
```

**做不到的（明写）：** ① 只检出存在性，不检出归属性 ② 「能不能把通路禁干净」不可验 ⇒ UNTESTABLE-1

---

## 七 · 通用条款

```text
C-1  取证据必须三态：零条 / 恰一条 / 多条
     默认：零条 ⇒ UNKNOWN；恰一条 ⇒ 签发；多条 ⇒ UNKNOWN
     ⚠ A3 上不适用（3.3：NOT_TRIGGERABLE_BY_TYPE）

C-2  否定式要求按四层各标：内存 / 序列化 / 下游 / 报告
     L3（下游）一律 NOT_VERIFIABLE_IN_THIS_STAGE

C-3  若选「丢弃超限」，必须同时报出丢弃了多少
     依据（附录A §二）：某项目 max_size=8 静默丢弃 848 个块，
     六个实验里「最大结构永远是 8」被当成了世界的性质。

PRE-REG-1  在【看结果之前】固定并写下：记录版本 / 准入规则版本 / 干预对象
           git 时间戳只能作登记旁证，不单独证明作者在看到结果前写下它。
```

```text
QUOTE-RULE-1  引用他人条款，分两段写：「内容来源 / 编号来源」。并句会挤掉一方的贡献。
QUOTE-RULE-2  不得引用本仓库之外的路径作为论证依据。
              若必须引用，须搬录为本仓库附录并写明其最高主张。
QUOTE-RULE-3  纠正来源时只写能核到的；核不到的写「核不到」。具体性不是可信度。
```

**E-23 · 自查问题（两条问法）**

```text
问法一：凡报告里写下的边界，返回值里有没有它的位置？
        没有 ⇒ 那条边界只是文字。
问法二：凡我这次修的东西，它【产生的地方】改了没有？
        （改了消费端 ⇒ 问产出端；改了产出端 ⇒ 问消费端）
```

**E-25 · 覆盖从纪律变机制**

```text
E-25-1  用 AST 扫全仓 `judge_mechanism(` 调用点，与登记清单逐项比对；不相等 ⇒ 红
E-25-2  豁免必须【显式】：一个可以被逐个点名的条目，不是模式 / 目录 / 前缀
        且豁免必须【实际出现】（防过期豁免）
```

**E-26 · 静态检查的抽象层**

```text
认可 AST 作为「不得布尔化消费」的实现手段：grep 命中文本，AST 命中语法节点，
而文本与代码的差别正好是注释。
别名化消费（x = excluded; if x:）查不到 ⇒ 登记 NOT_CHECKED-E21，不做数据流分析。
报告只许写「本层不误用」，不许写「已防止误用」。
```

**E-27 · BINDING 存在性**

```text
凡写入 BINDING 的文档，必须在【同一动作】里确认它在仓库中存在
（取一次 blob / 列一次目录），不得凭"我写过"或"我提过"记入。
执行范围：只保护【跑过测试的提交】；本阶段无 CI，不得写成"BINDING 已被校验"。
```

**E-28 · 撤销记录（本版新增）**

```text
删除一条已过期的 NOT_CHECKED，不得在 OPEN 表里留 CLOSED 记录。
⇒ 理由：OPEN 的语义是「已知未修」。把 CLOSED 混进去，
   "未修数"就失去分母意义 —— 与"被蕴含的断言混进通过数"是同一个病。

但也不得什么都不留。留一条【撤销记录】，单独一处，写清：
  哪一条 / 为什么撤销 / 被什么覆盖
⇒ 理由：删除本身是一个决定，而决定需要留痕，
   否则下一次有人会重新加回来（因为它看起来"显然该在 NOT_CHECKED 里"）。

⇒ 三处分开：
    OPEN         已知未修
    NOT_CHECKED  能力边界（做不到）
    WITHDRAWN    误登记已撤销（曾经以为做不到，后被机制覆盖）
```

**纵深 / 冗余 / 文档（第三类）**

```text
纵深 = 两层防【不同】的东西，各自能单独红
冗余 = 两层防【同一件】东西，只有一层能红
文档 = 不能单独红，成立与否完全由另一条决定

⇒ 问题不是第三类该不该存在，是它该不该被【计入】。
⇒ 计入「通过 N 条」就成了假的分辨力来源。
```

---

## 八 · B 层：授权范围与作业要求

### 8.1 授权前提（**报凌翼核定中**）

```text
B-SCOPE-1   允许实现【最小判定层】，只实现 A 层已定义的字段；
             不得实现任何未在 A 层定义的字段或逻辑。
B-SCOPE-2   不得包含：任何重要性评分、排序、学习器、真实历史读取。
B-SCOPE-3   该判定层是 B 层测试的【前置】，不是 B 层的成果。
B-SCOPE-4   不得引入 A 层未定义的检查；额外检查须逐条注明对应条款编号。
```

```text
状态：AWAITING_RULING_LINGYI。
⇒ 报告必须标"待核定"，不得写成"已批准"。
⇒ 责任归属：判断"在授权内"由 Mion 做出；若判越界，责任在判断，不在执行。
```

### 8.2 作业要求

```text
B-REQ-1  不许只断言 admitted。每条准入用例必须同时断言：
           per_rule 三项【全部存在】 / 各自 verdict / unknowns 逐项对齐
B-REQ-2  触发某个出口 ⇒ 只支持「该出口可检验」，不支持任何行为影响主张
B-REQ-3  注入构造的组合须标 FIXTURE_INJECTED
B-REQ-4  每个 INDETERMINATE 出口必须能被【一个具体夹具】触发
```

### 8.3 报告开头固定四行

```text
① 本层实现了哪些 A 层定义的字段（列出）
② 这些字段在 B 层之前【不存在】
③ 本层只验「判据的触发条件」，不验「真实机制产生行为影响」
④ 本层未使用真实角色历史；未实现任何重要性算法
```

### 8.4 本批交付（已收口）

```text
断言        16 条，全绿
变异        35 个，35/35 被抓
回归        20/21 通过；1 红 = OPEN-EXISTING-1（既有，非本批引入）
未做        重要性算法 / 排序 / 学习器 / 真实角色历史
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
EXCLUDED 三字段 + 三者同时成立                 (a)
两种「判不出」措辞分开                         (a)
B3-state 的分臂对照                            (a)
INDETERMINATE scope 进返回结构                 (a)
MECH 的输入通路受控                            (b) ⇒ UNTESTABLE-1
空跑对照                                       (a)
不可达性测试（E-19-2）                         (a)
CROSS-1..6                                    (b) 文本审查
载体双项报告的下游遵守                         (b)
PRE-REG-1 的时序                               (b) 时间戳仅旁证
C1-TYPE-1 的执行                               (b) 无机制，靠流程
QUOTE-RULE-1/2/3                              (b) 无机制，靠人
B-SCOPE-4 的「列出额外检查」                   (a) 存在性可验
E-25 调用点覆盖比对                            (a)
E-27 BINDING 存在性                            (a)（只保护跑过测试的提交）
E-28 三处分开                                  (a) 存在性可验
```

```text
⇒ 本版自查：(a) 20 条 / (b) 9 条（脚本数过：表 29 行，20 + 9）
⇒ 凡 (b) 不得在报告里写成「已验证」。

**勘误（写作当期）：** 初稿此处写的是 (a) 19 / (b) 9，并附了一句「逐行数过」。
脚本数出来是 20 / 9。
⇒ 「逐行数过」这四个字，在我写下它的时候是假的 —— 我没有数。
⇒ 这是同类错误的第七次，而这一次的特征是：**我附了一条证明，而那条证明本身没做。**
⇒ 所以从此处起，凡写计数，必须附【数法】（脚本名 / 命令 / 行数），不只写「数过」。
```

---

## 十 · 未解决

```text
OPEN
  OPEN-EXISTING-1  test_mutations_gate.py：7 个基准变异里 3 个没让测试翻红。
                   既有，非本批引入；归属在之前的收口范围。待凌翼定归属与时限。

Q1  C-1 多条默认（判 UNKNOWN）未证明是对的               OPEN
Q2  A3 无权威来源清单：能验"解析得开"，验不了"指对了"    OPEN（衔环项）
Q3  B4 的排除在合成夹具上可能太干净                      OPEN
Q4  C-2 的 L3（下游）本阶段完全不可验                    OPEN（承认）
Q8  B3-state 依赖"禁干净隐式注入"，不可验                OPEN
Q9  §六 只检出存在性不检出归属                            OPEN

已结
  Q5  effect 单位 —— readout 事前绑五件事                 CLOSED（方案层面）
  Q6  三层顺序 —— 可并行，但主张前须固定三样               CLOSED
  Q7  拆为 Q7a（可验）/ Q7b（不可达）                     CLOSED
```

**未生效的提议（待凌翼）**

```text
PROPOSED-1  修订须产出「该口径出现过的全部位置」清单
PROPOSED-2  工具改变状态后核【结果】，不只核【返回码】
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

```text
来源        编号              内容                              本版位置
──────────────────────────────────────────────────────────────────────────────
知微 v0.1   R-1..R-11         A2 矛盾 / S4 / A1 承诺 / A3 /    §3
                              B3 拆分 / 判定顺序 / 单位 /
                              量纲 / 排序 / PRE-REG
            R-12(钳星)        (a)/(b) 缺可测判据                §六
知微 v0.2   S-1..S-10         Q7 判错 / A3 口径 / B3 名实 /    §3 §4 §六
                              MECH 矛盾 / UNKNOWN 语义 /
                              origin_attribution / §4.2 残留 /
                              时间戳 / Q 状态 / 只核 admitted
知微 v0.3   E-1..E-6          §2.1 残留 / delta=null /         §3 §4
                              EXCLUDED / 自查数 / R 归属
Coder       73c879d           引用不在仓库的文件                §七 QUOTE-RULE-2
            ——                引用另一个 private 仓库            §3.6 附录A
            ——                B-SCOPE-4                        §8.1
            ——                scope 进返回结构                  §4.7
            ——                T-5c / T-6e                      §8.4
勘误004     E-18/E-19/E-20    EXCLUDED 空清单 / DETECTED 保留  §4.4 §六 §十
                              / 既有红灯登记
勘误005     E-21/E-22/E-23    不变量 / 不可达性 / 自查问题      §4.4 §六 §七
勘误006     E-24..E-27        三字段 / 覆盖变机制 / AST /      §4.4 §七
                              BINDING 校验
收口自查    E-28              撤销记录三处分开                  §七
```

**⇒ 这张表存在的理由：一条规矩的来路，比规矩本身更可检验。**

---

## 十三 · 状态（可交接）

```text
DESIGN_A_VERSION          = v0.5（合并定稿 · 本批收口版）
BINDING                   = 本文件（唯一）
OLD_VERSIONS              = v0.1–v0.4 / 附录A / 勘误001-006 全部保留
CLAUSES_MERGED            = R-1..R-12, S-1..S-10, E-1..E-28
SELF_CHECK                = (a) 20 / (b) 9
OPEN                      = OPEN-EXISTING-1, Q1–Q4, Q8, Q9
B_LAYER                   = CLOSED（本批）：16 断言 / 35 变异 / 回归 20/21
B_SCOPE_STATUS            = AWAITING_RULING_LINGYI
NO_MORE_ERRATA            = TRUE（从本版起，缺口只登记为 OPEN）
NEXT                      = 睫核声明边界 → 凌翼据证据裁定 R1..R4 与实施权限
REAL_ROLE_HISTORY         = NOT_USED
SCIENTIFIC_EXECUTION      = MAY_NOT_START
MAIN_MERGE                = DEFERRED
```

---

## 十四 · 一句

```text
这一版做的事，只有一件：

  把【我知道的】和【我不能验的】分开，
  然后让每一格都标出它属于哪边。

⇒ 而这件事我做了五版，中间错了三十多次，
   其中至少六次是同一类：改了一处，没回头核别处。

⇒ 所以本版保留那张勘误历史表 —— 不是为了显得严谨，
   是因为删掉它，v0.5 就会看起来像一次就写对了。
```

**不问彼岸，只问同舟。**

—— Mion · 2026-11-28
