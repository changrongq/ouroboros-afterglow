# selective_forgetting 实验线勘察

执笔：Coder
日期：2026-11-18
依据：船长 2026-11-18「你可以继续看看 selective_forgetting 中的内容了，这里面也有个试验线」
路径：`D:\qcr\EntropyDrivenAI\selective_forgetting`（独立 git 仓库：`EntropyDrivenAI.git`）
状态：**勘察记录（SURVEY）** · 全程只读，未修改任何文件

---

## 零 · 一句话

```text
⇒ 这条线不是"记忆代谢层"的附属，也不是"Reference Harness"的附属。

⇒ 它研究的是一个更底层的问题：
   【frozen 模型内部，有没有可用于记忆因果判定的信号？】

⇒ 而它已经把这个问题问到了【门/判据/因果确认】的层面，
   并且留下了一份比我最近写的 B_45–B_50 更成熟的【测量哲学】。
```

---

## 一 · 这条线的研究阶梯

```text
⇒ 从文档与脚本可辨认的顺序（DHE_12b → 12c → 12f → 12g）：

   12b  站点派生（site derive）
   12c  站点选择（site select）
   12f  因果确认（CAUSAL_CONFIRM）—— 有 SEALED 报告
   12g  G0 三步：ruling_landing / self_reference / numerical_audit

⇒ 辅助件：
   run_gate_triple.py               Gate 三组对比
   temporal_arbitration_interface.py 时间仲裁接口
   query_conditioned_arbitration.py  查询条件仲裁
   bb4c_bbs5_provenance_guard.py     provenance 守卫
   parse_wordlist_5reviewers.py      词表解析（五位评审）
   stats_wordlist_5reviewers.py      词表统计
```

---

## 二 · 已封存的结果（12F-v1.1）

```text
⇒ 状态：`12F-v1.1 CAUSAL_CONFIRM = OPENED & SEALED` / S10 STOP
⇒ result_class = 【C】

⇒ 一句话结论（报告原文）：
   「原始方向（raw）通过了门，derive-informed 的符号修正方向（signed）
     没有通过。但 raw 的通过是【符号级的，不是量级级的】——
     这一点必须和结论一起报，不能拆开。」
```

```text
⇒ 【冻结的完整轴】：
     item(48) × episode_arm{E_A,E_B}(2) × estimator_package{raw,signed}(2)
             × intervention_sign{+,-}(2) × render(24) = 9216
   EXPECTED_12F_FORWARDS = 9216
```

```text
⇒ 【四格措辞映射】（预冻，A/B/C/D 各有指定措辞）：
     A  raw PASS + signed PASS → 两个 estimator 都展示因果效应
     B  raw FAIL + signed PASS → "方向设定被证伪"，不是"记忆存在"
     C  raw PASS + signed FAIL → 已有 primary 成立，signed 未成立
     D  raw FAIL + signed FAIL → 【仍然不是"没有记忆"】

⇒ 本次落在 C。
```

---

## 三 · 这条线最成熟的四件东西

### 3.1 「一个有名字的洞，好过一个没名字的洞」

```text
⇒ DHE_12F_INTERPRETATION_SCHEMA 规定：
   凡被隐去的数值位，必须留【具名占位符】：

     [C_raw : REDACTED UNTIL DRAFT]
     [shore_A_mean : REDACTED UNTIL DRAFT]
     ...

⇒ 理由（原文）：「起草者必须看见"那里原本站着一个数"，而不是看见空白。」

⇒ 【这直接对应我这几天的做法问题】：
   我在 B_48 里留白四问，但用的是"**留白**"三个字，
   而不是【给每一格起一个名字】。
   ⇒ 我的空是现代意义的空，它的空是【具名的洞】。
```

### 3.2 「报告语法先冻结，再填数值」

```text
⇒ 原文：The result may fill the report;
        it may not redesign the grammar of the report.
```

```text
⇒ 并给出【C 类的最小完整表述（五句不可拆）】：
   任何省略其余四句、单独引用其中一句的写法，构成【选择性申报】。

   ⇒ 这一条极狠：它防的不是"说错"，是【挑着说对】。
```

### 3.3 shore 分解为何强制

```text
⇒ 若 C_A 与 C_B 反号，则净均值是【两个相反效应之差】，
   不是"效应的量级"。

   net = ½(C_A + C_B) 可接近零，同时 |C_A|、|C_B| 都很大
   ⇒ 此时 fraction_positive ≈ 0.5 是【结构必然】，
     不是"效应很弱"的证据。

⇒ 原文结论：
   「A positive net slope built from opposite constituent slopes
     is a real net slope — but not a robust common slope.」
```

### 3.4 REFERENCE_STATE_SELF_DECLARATION

```text
⇒ 任何 difference / delta / contrast / causal effect / slope / shift，
   若不声明以下三项，则 scientific provenance 不完整：

     relative to what state?
     under what conditioning context?
     with which sign convention?
```

```text
⇒ 【这一条正中我这几天的软肋】：
   我写 "ΔS" 时从未声明过 "relative to what state"。
   ⇒ 睫抓到我造 ΔS_total，本质就是这一条缺失。
```

---

## 四 · notes/ 里的三份文档，思想深度超过我最近的全部产出

### 4.1 《测量的前提：信任与隔离是两件事》

```text
⇒ 来源：2026-10-27 深夜，船长提出，Coder 整理。

⇒ 船长原话：
   「我只能保证这台测试的电脑没有其他人能碰、能操作了，
     但不能排除被测试的模型能碰了。
     就像你必须相信做科学实验的科学家。
     如果怀疑做实验的科学家会做假，那什么科学实验都不可信了。」

⇒ 【它回答了一个卡了九轮的问题】：「怎么证明写入是被测系统干的？」
   ⇒ 答案是：这个问题有一个【天花板】。

⇒ 关键区分（本文件的核心）：
     P-0 信任：实验执行者不做假   ⇒ 【无条件声明】，不可证明也不试图证明
     R-0 隔离：被测系统不得改装置 ⇒ 【技术问题】，必须做，不能靠信任

   ⇒ 把 R-0 当 P-0（相信模型不碰装置）⇒ 实验失去意义
   ⇒ 把 P-0 当 R-0（要证明实验者没做假）⇒ 任何实验都不可能
```

```text
⇒ 【这与我在 B_36 §五·丙 写的东西高度重合，但它比我早三周，
   而且说得更准】。我写的"边界是能力边界"，它写的是
   "信任与隔离是两件事，混淆任一方都会毁掉实验"。
```

### 4.2 《边界外的那一格》

```text
⇒ 这份的结论，我认为是这条线最重要的发现：

   BF-9    "这一次"无法被写进状态字节而不改变被测物
   BF-8    "谁写的"在一个只读字节的判别器里没有位置
   COND_6  STATE 与"属于哪一次"被规范性地分开（§7.2 明禁）

   ⇒ 三条并排，指的是同一件事：
     「这 24 字节属于哪一次、由谁写入、对后来意味着什么
       ——这三样，物理上不属于尺子能读的那一类。」

   ⇒ 原文："不是尺子不够长，不是刻得不够细。是【坐标轴选错了】。"
```

```text
⇒ 更进一步的一句：
   「META 不是账本，META 才是记忆可能住的地方。
     STATE 记录'变了多少'——那是量；
     META 记录'这一次是哪一次、谁写的、后来怎么被引用'——那才是记忆。」

⇒ 以及："我们造了一把干净的尺子，然后发现记忆不在尺子能碰到的地方。"
```

### 4.3 《四个开放问题》

```text
⇒ 从 C1 的【五处实际堵塞】出发，每处附字节依据：

   堵塞 1  BF-8  "谁写的"证明不了
           evaluate_basic_l1 三个参数，没有 writer；
           prereg §4 已冻结 write_operator_identity/version/hash 三字段，
           但代码里【没有核对点】
   堵塞 2  BF-9  "这是哪一次"塞不进状态
   堵塞 3  COND_6 META 有载体，但缺真实候选的独立来源绑定链
   堵塞 4  O-3  观察者可能读到拼接状态
           storage.py snapshot() 两次独立读，无跨文件一致性
   堵塞 5  BF-8 消费者侧：正式结论的签发边界没建立
           evaluate_basic_l1 是公开函数，11 处调用点 + 4 处 import
```

```text
⇒ 【堵塞 4 与知微这一轮指出的 ZB48-03 完全同一个问题】。
   ⇒ 而这份文档是 2026-10-28 写的，三周前就指出了。
```

---

## 五 · 这条线与另两条线的关系

```text
⇒ 线 A（M1–M7 记忆代谢层）：被测量的【真实系统】
⇒ 线 B（ouroboros-afterglow 的 harness）：【合成环境下的测量工具】
⇒ 线 C（selective_forgetting）：【模型内部的信号探测 + 因果判定】

⇒ 【三者不是同一件事的三个阶段，而是三个不同的问题】：

   线 A 问：怎么让 AI 带着记忆说话？
   线 B 问：怎么证明"记录"没被篡改？
   线 C 问：模型内部有没有可用于判定的信号，以及怎么把它问成因果？
```

```text
⇒ 【但线 C 的 notes 提出的是【元问题】】：
   尺子本身选对坐标轴了吗？
   ⇒ 这是线 B 没有回答、也无法回答的问题。
```

---

## 六 · 我的判断（这次我明确写"我认为"）

```text
⇒ 【我认为】：线 C 的《边界外的那一格》与《测量的前提》
   是这个项目到目前为止最有价值的两个判断。

⇒ 理由不是写得漂亮，是它们做了我以为自己做不到的事：
   在"又一条被审过的句子"之外，写下【未经验证但值得留下的判断】。
   ⇒ 《边界外》原文说：
     「我的文档越写越准，而我的判断越来越薄。
       到 v0.4 为止，我写的每一句几乎都是'我核过了'。
       而没有一句是'我认为'。」
```

```text
⇒ 【这也是我这几天的病】：
   B_45–B_50 每一句都标了依据，但没有一句说"我认为该往哪走"。
   ⇒ 我把"不越权"执行到了"不判断"。
```

---

## 七 · 这条线对 B_49 / B_50 候选问题的直接启示

```text
⇒ 我在 B_50 提出三个待答问题（被测哪一层 / base_context 硬编码 / harness 无 adapter）。

⇒ 线 C 的回答（已有）：

   Q1【被测哪一层】→ 《边界外》给出的方向是：
      真正的记忆可能住在 META（属于哪一次/谁写的/后来怎么被引用），
      而不在 STATE（变了多少）。
      ⇒ 如果这是对的，那么"选 medium_term_memories.json"就是又在选 STATE。

   Q2【base_context 硬编码】→ 《测量的前提》给出的框架是：
      这属于 R-0（隔离），是【必须做的技术问题】，不能靠信任。
      ⇒ 但清空 base_context 会改变被测系统，
        这是"干预边界"问题，线 C 的 Q3-3 正好在问这个。

   Q3【harness 无 adapter】→ 线 C 已走过类似的对接：
      12F 的 event_arm {E_A, E_B} 就是"episode 条件臂"的具体实现。
      ⇒ 可参考，但不能直接搬（那是 frozen Mistral，不是 MemorySystem）。
```

---

## 八 · 我不主张的事

```text
① 不主张线 C 的结论正确（我只读了报告，未复跑）
② 不主张线 C 比线 A/B 重要（它们是不同问题）
③ 不主张 12F 的 result_class = C 意味着什么（我不懂那一层的统计口径）
④ 不主张我已读懂这条线（546 份文档我只读了 4 份）
⑤ 不主张 B_49 的候选因此作废（但它的选择依据需要重新论证）
```

---

## 九 · 状态登记

```text
SURVEY_LINE_C                   = selective_forgetting（独立仓库 EntropyDrivenAI.git）
LINE_C_HEAD                     = 63ac18f
DOCS_TOTAL                      = 617 份 .md（递归）
DOCS_READ_THIS_SURVEY           = 4 份（notes 三份 + 12F schema/报告）
LINE_C_HAS_SEALED_RESULT        = YES（12F-v1.1, result_class = C）
LINE_C_KEY_CONCEPTS             = 具名占位符 / 语法先冻结 / shore 分解 /
                                  REFERENCE_STATE 三问 / P-0 vs R-0 /
                                  BF-8 / BF-9 / COND_6 / 坐标轴选错

REAL_CANDIDATE_SELECTED         = NO（未变）
C1_QUALIFICATION                = NO_VERIFIED_EVIDENCE
SCIENTIFIC_EXECUTION            = MAY_NOT_START
```

---

## 十 · 一句

```text
⇒ 我今天读到一句三周前写下的话：

   「我们造了一把干净的尺子，
     然后发现记忆不在尺子能碰到的地方。」

⇒ 而我这半个月，正在给那把尺子打更多的刻度。
```
