# AfterGlow 全貌勘察报告



执笔：Coder

日期：2026-11-18

依据：船长 2026-11-18「你还需要继续读一下，除了这个还有其他的实验，最好拿到一个全貌」

范围：`D:\qcr\EntropyDrivenAI`（含 `selective_forgetting/` 子仓库）+ `D:\qcr\ouroboros-afterglow`

状态：**勘察记录（SURVEY）** · 只读，未修改任何文件



---



## 零 · 先说我上一份提案漏了什么



```text

⇒ B_49 我只看了 `M3_reflection_executor/MemorySystem.py`，

   就断定"候选是 medium_term_memories.json"。



⇒ 【这个判断不完整】。看过全貌之后，至少还有三条独立的实验线，

   而它们的对象与我提的候选【不是同一个东西】。

```



---



## 一 · 实际存在几条实验线



```text

⇒ 实测目录（2026-11-18，.md 计数为递归统计）：

     EntropyDrivenAI/                  —— 主仓（EntropyDrivenAI.git）

     ├── M1..M7 七层模块                —— 记忆代谢层

     ├── reports/          157 份 .md   —— v1/v3/v4 实验报告

     ├── selective_forgetting/  617 份 .md —— 【独立的 git 子仓库】

     └── doc/               15 份 .md   —— 设计文档



⇒ 两条不同的研究线，都被叫 "AfterGlow"：

```



### 线 A · 记忆代谢层（M1–M7）



```text

⇒ 实现在根目录与 M1..M7。

⇒ 核心问题：让 AI 带着记忆说话。

⇒ 对象：JSON 文件（medium_term_memories / cards / capsules / index）

⇒ 规模：9 条真实中期记忆

⇒ 这份是 B_49 提的候选，【它确实存在且可测】。

```



### 线 B · Reference Harness（科学测量框架）



```text

⇒ 实现在 `afterglow_harness/`（67 个 .py）。

⇒ 核心问题：如何【测量】一次经历是否留下可归属影响。

⇒ 对象：合成 substrate（literal.bin 16B + substrate.bin 8B）

⇒ 这份是 prereg / B_45–B_49 / RC7–RC11 讨论的对象。

```



```text

⇒ 【两条线的关键差异】：

   · 线 A 是【被测量的真实系统】（有 9 条真记忆）

   · 线 B 是【测量工具】（合成环境，用来验证工具本身）

   ⇒ 我在 B_45–B_48 讨论的全部是线 B。

```



### 线 C · selective_forgetting（时间信号 / Gate 实验）



```text

⇒ 这是一条【独立的研究线】，不是线 A 或 B 的子集。

⇒ 核心问题（凌翼原话）：

   「Frozen Mistral 的 hidden 中，是否已包含可被轻量 encoder

     提取的状态转移信息？」

⇒ 对象：frozen Mistral-7B 的 hidden states

⇒ 最新结论（2026-08-29）：

   · 时间信号【真实存在】：time-order 分类 0.683（mean-pool）/ 0.533（raw）

     显著高于随机 0.33

   · mean-pool 优于 raw-hidden

   · ranking（挑最新版本）两者都是 0.25 = 随机

   · 之前"raw-hidden 更适合 Gate（1.0）"的结论【是假阳性】，已证伪

⇒ 后续：Gate 三组对比全部失败，真因是 grad_L2 → 0

   （真实 k 的 L2 范数 ≈184，tanh 深度饱和）

```



```text

⇒ 【这条线的价值】：它直接触碰了「记忆影响输出」的机制层，

   而不是像线 B 那样只验证格式。

```



---



## 二 · 一个必须说清的事实：两处 harness 是同一份



```text

⇒ 实测对比 `selective_forgetting/afterglow_harness/`

          与 `ouroboros-afterglow/afterglow_harness/`：



   文件数        67 vs 67

   只在 A          0

   只在 B          0

   内容不同        2

   完全一致       65



   差异文件：

     q3_reset_adapter.py             A mtime 2026-10-15 / B mtime 2026-10-21

     qualification_binding_rc12.py   A mtime 2026-10-12 11:06 / B 10:22

```



```text

⇒ 【结论】：这两个目录是【同一份 harness 的两个副本】。

   ⇒ 差异是【文件时间差】，B 侧略新（但行数完全相同，可能只是格式差异）。



⇒ 【这意味着什么】：

   · 我在 ouroboros-afterglow 里改的东西，与 selective_forgetting 里的

     【可能不同步】

   · 而 selective_forgetting 是【另一个 git 仓库】（EntropyDrivenAI.git）

   ⇒ 【两边的 harness 会各自漂移，而且没人知道哪边是准的】

```



```text

⇒ 【另注：selective_forgetting 的 git 状态】

   HEAD = 63ac18f「阶段B_22 统一候选规范（编码卷）」

   ⇒ 它的提交历史里【混着】afterglow 的 B_22 文档。

   ⇒ 说明这两条线曾经交叉提交过。

   工作树有未提交改动：M1/M2/M4 若干 .py 被修改，

   M5_UI/app.py 等【被删除】（D 状态）。

```



---



## 三 · v1 / v3 / v4 是什么（线 A 的历史）



```text

⇒ 来自 `reports/Afterglow_项目实验汇总_2026-07-10.md`（项目自述）：



   起点    M-bias 注意力注入（在 Mistral 每层 softmax 前加偏置矩阵 M）

            四组对照 G0/G1/G2/G3，λ 三档

            四道护栏：token 云不吞噬故事 / 权重不冒充意义 /

                      高频不冒充重要性 / 注意不冒充因果

   发现     λ=1.0 有效但输出退化；λ=0.2–0.5 与 prompt 前缀差异不大

            根因：M-bias 是【静态】的，不随对话代谢

            ⇒ 转向"模型外记忆代谢层"



   V1      候选事实自动提取 / 结构化槽位 / 场景温度 /

           protected 守卫 / confirmation echo 防回声 / scene capsule 晋升

   V3      结构化身份卡比 token bias 更稳定（角色一致性）

   V4      D0 语义压缩审计 / B 一步图扩展 / C0 压缩运行链 / app 双轮烟雾

   当前    记忆前缀注入（按权重排序，非关键词匹配）

           权重 = relevance×0.35 + confidence×0.18 + evidence_count×0.12

                + recall_frequency×0.15 + identity_impact×0.20

```



```text

⇒ 【项目自述当前限制】（原文第七节）：

   1. identity_cards 为空（尚未触发足够身份事实）

   2. 遗忘 archive 回流尚未在 app 端充分验证

   3. 长会话压力测试未做（当前最多几十条记忆）

   4. base context 仍为硬编码（身份认知不来自对话记忆）

```



```text

⇒ 【第 1 条与我的实测一致】：identity_cards.json = `[]`（2 字节）。

⇒ 【第 4 条最要紧】：AI 的身份认知仍来自 `config['base_context']`，

   ⇒ 也就是说：即使记忆系统全跑通，

     "我是谁"这件事仍是硬编码的，不是从记忆里长出来的。

```



---



## 四 · 重新评估我的 CAND-01 提案



```text

⇒ 原提案：medium_term_memories.json 作为被测对象。



⇒ 【看过全貌后，我认为它仍然是合理候选之一，但不是唯一，且理由要改】：



   优点（不变）：

     · 9 条真实记忆，非空

     · 单文件、写入路径可枚举

     · 是 V4 之后"记忆前缀注入"的直接来源

       （权重排序 → 进 prompt → 影响输出）



   缺点（新增认知）：

     · 它只是【线 A 的中间层产物】，

       真正影响输出的是【prompt prefix 构建后的结果】

     · 而 base_context 硬编码意味着：

       输出变化可能来自 base_context，不是记忆

       ⇒ 【这会直接污染 C1 的归属判定】

```



```text

⇒ 【这是我上一份提案最大的疏漏】：

   我没有意识到 base_context 是硬编码的。

   ⇒ 如果基线里就写着"你是千年舟的 Coder"，

     那么测"记忆是否影响输出"时【无法区分】来自记忆还是来自 base_context。

   ⇒ 这正是 prereg §8 说的 LITERAL_STORAGE_COMPONENTS 之外的另一条通路。

```



---



## 五 · 我建议的下一步（不是结论，是问题）



```text

⇒ 【在选定候选之前，有三个问题必须回答】：



   Q1  被测的"记忆"是哪一层？

       · medium_term_memories（原始记忆池）

       · memory prefix（注入 prompt 的那段文本）

       · prompt 拼接后的完整输入

       · 模型输出的变化

       ⇒ 四层，选哪层？



   Q2  base_context 硬编码怎么处理？

       ⇒ 若不清空，无法区分"记忆的影响"与"硬编码身份的影响"。

       ⇒ 这直接影响 C1 能否建立归属。



   Q3  线 B（Reference Harness）与线 A（真实记忆系统）如何对接？

       ⇒ 现在 harness 测的是合成 substrate，

         而真实系统用的是 JSON 文件。

       ⇒ 中间需要一个 adapter，而这个 adapter 【不存在】。

```



---



## 六 · 我不主张的事



```text

① 不主张 CAND-01 应被采纳（我只提议，且现在知道它不完整）

② 不主张线 A 或线 B 哪条更重要

③ 不主张 selective_forgetting 的结论正确（那是另一条线的成果）

④ 不主张两处 harness 的差异无影响（我未逐行 diff）

⑤ 不主张 base_context 是唯一的污染源

```



---



## 七 · 状态登记



```text

SURVEY_SCOPE                    = EntropyDrivenAI (含 selective_forgetting) + ouroboros-afterglow

EXPERIMENT_LINES_IDENTIFIED     = 3（A 记忆代谢层 / B Reference Harness / C 时间信号）

HARNESS_COPIES                  = 2（selective_forgetting 与 ouroboros-afterglow）

HARNESS_FILES_IDENTICAL         = 65/67

HARNESS_FILES_DIFFERENT         = 2（q3_reset_adapter.py / qualification_binding_rc12.py）

REAL_MEMORY_ENTRIES             = 9（medium_term_memories.json）

IDENTITY_CARDS_EMPTY            = YES

BASE_CONTEXT_HARDCODED          = YES（项目自述第七节第 4 条）

HARNESS_TO_REAL_ADAPTER         = NOT_EXISTS



REAL_CANDIDATE_SELECTED         = NO（未变）

CAND_01_PROPOSED                = YES（但已自我修订，见 §四）

C1_QUALIFICATION                = NO_VERIFIED_EVIDENCE

SCIENTIFIC_EXECUTION            = MAY_NOT_START

```



---



## 八 · 一句



```text

⇒ 我花了半个月给【测量工具】建可信机制，

   却从来没看过【被测量的东西】长什么样。



⇒ 今天看到了，发现：

   · 它有三条实验线，我只认识一条

   · 它有两份 harness 副本，可能已经漂移

   · 它的身份认知是硬编码的

   · 它自己列出的四条限制，我一条都不知道



⇒ 【不改结论，只改认知】：

   候选不是"随手挑一个 JSON"，而是先要回答"哪一层才算记忆"。

```

