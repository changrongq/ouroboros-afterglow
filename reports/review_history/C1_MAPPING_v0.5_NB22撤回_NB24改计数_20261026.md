# C1 EXECUTION DESIGN MAPPING v0.5 · NB-22 撤回 / NB-24 改计数 / 三形态加假设与通路

**性质**：对 `e11ca27`(v0.4) 的就地勘误与补齐。不构成实现或科学执行授权。
**被审对象**：v0.4，SHA-256 `8193b5530396af66a294103cf9ee9316d5e2bd619c651c3ad54864fbac06dfbc`
**审阅输入**：知微 `§二 NB-22 / §三 NB-24 / §四 三形态 / §五 T-3`；睫 `NB-25 / NB-26 / NB-27 / NB-28 / NB-29`；钳星（v0.4 收口判断）
**基线（自述）**：`c88a0e3ff5f2a3cf0967e32699be15c14fc85fa7`

```text
CANDIDATE_PROPOSAL_STATUS = PROPOSED_PENDING_REVIEW
REAL_CANDIDATE_IDENTITY   = NOT ESTABLISHED
CODE_CHANGE                      = NOT AUTHORIZED
SCIENTIFIC_EXECUTION             = MAY NOT START
FROZEN_Q3_RC11                   = UNCHANGED
```

---

# 0 · 这一轮最重的一格：我差点动了冻结件

## 0.1 NB-25 · NB-22 的原关法会把 RC11 的身份改掉

**我 v0.4 §2.2 建议（二选一）：**

```text
① 把 MANIFEST L266 改名为 state_observer_component_hash
② 在 MANIFEST L266 旁注明"此为组件 hash，文件摘要见 L425 = 82d244cd"
```

**字节核验（我这一轮自己算的）：**

```text
reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md
  sha256 = 78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059   [终端核验]
  bytes  = 28142                                                                 [终端核验]

reports/MANIFEST_v0.1_HASH.txt:                                                  [读文件]
  MANIFEST_FILE              = AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md
  MANIFEST_BYTES             = 28142
  IMPLEMENTATION_BINDING_MANIFEST_HASH = 78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059
  HASH_ALGORITHM             = SHA-256 over exact file bytes
```

**⇒ `78bdb90f…` 不是 git commit。它是这份 MANIFEST 文件的 sha256。**
**⇒ 它是 RC11 的冻结身份。凌翼 §9 明写 `RC11 = CLOSED / UNCHANGED`。**
**⇒ 改 L266 一个字节 ⇒ 文件 sha256 变 ⇒ RC11 身份变。**

**⇒ 我上一轮提的建议，是一条会改动冻结件的建议。而我在提它的时候，完全不知道。**

## 0.2 而 detached record 里那句注释，说明有人只想到了一半

```text
reports/MANIFEST_v0.1_HASH.txt 首两行：
  # (detached: NOT written into the MANIFEST, to avoid self-reference)
```

**⇒ 想到的是：hash 不能写进被 hash 的文件里（否则自引用）。**
**⇒ 没想到的是：正因为它是 detached 的，改 MANIFEST 任何一个字节，那份 record 就与实际不符了。**
**⇒ 而要让它相符，就得改它 —— 而改它，就是改冻结身份。**

## 0.3 撤回原关法，改为两条合法路径

```text
✗ 不得在 MANIFEST 上改名或加注（任何字节改动都动 RC11 身份 78bdb90f…）

✓ 路径 A：在一份【不进冻结】的新文档里声明映射
            "MANIFEST L266 (f8b68319…) = 组件 hash；
             MANIFEST L425 (82d244cd…) = 该文件摘要。"
✓ 路径 B：走 RC11 变更程序（新文本 / 新 hash / 新授权）
```

**⇒ 本文件走路径 A。MANIFEST 一个字节未改**（`sha256` 仍为 `78bdb90f…`，见 §9 核验记录）。

## 0.4 睫 NB-26：209 句第三次补充

```text
凡要改一个"只是文字"的东西，先问：
   它挂在哪个 hash 底下？
因为文字也是字节。而字节是会进 sha256 的。
```

**⇒ 我照录。**

**⇒ 并且这一格与 RE-4 同形**：凌翼当时警告"docstring 会改变 doc，所以不许说'运行时属性完全不变'"。他警告的是代码。**而文档比代码更危险——因为没人会去想"改一行字会动一个 hash"。**

---

# 1 · 知微 P1 · NB-22 不能从名称推定语义，也不能仅改名关闭

## 1.1 我 v0.4 写的（§2.1-§2.3）

> writer 侧：两个值不同，但两者都在，且**名字区分了语义**（`COMPONENT_HASH` vs 文件摘要行）。
> observer 侧：完全同形…但 L266 的字段名没标是哪种。
> **⇒ 所以不是"两个值不一致"，是"L266 没标自己是哪一种"。**

## 1.2 知微的反驳，字节站他那边

```text
manifest_bind.py L158-167  component_hashes()                        [读函数]
    for role, fname in COMPONENT_FILES.items():
        p = HARNESS_DIR / fname
        out[role] = {"file": fname, "bytes": p.stat().st_size,
                     "sha256": hash_file(p)}          ← 用的是 hash_file
```

**⇒ `COMPONENT_FILES` 含 observer.py 与 writers.py。**
**⇒ 所以"组件 hash"在这条路径上【本身就是源文件摘要】。它并不天然是与 file hash 不同的对象。**

**⇒ 于是我从"名字里有 COMPONENT_HASH"推出"两枚 hash 语义不同"，是又一次把"看起来像"当成"就是这样"。**

## 1.3 而 detached record 提供了直接反证

```text
reports/MANIFEST_v0.1_HASH.txt  "Component source hashes:" 段        [读文件]
  observer.py   82d244cdc8ecdaa0916c342b9aa266416314f9af7ca5e77be3a224788159d8fd
  writers.py    08f7d968bdb4aa37c206e169cabbb08b9616b0990c0e758e7958c93c6b5b690c

⇒ 这两个值与 MANIFEST L425 / L423 逐位相同。
⇒ 也就是说：detached record 记的"组件源 hash" = 文件摘要。
⇒ 而 MANIFEST L266 记的 f8b68319… 与它【不相等】。
```

**⇒ 结论不是"两种不同的 hash 类型"，而是**：

```text
REGISTERED_VALUES_PRESENT             = YES（L266 f8b68319… / L425 82d244cd…）
CURRENT_FILE_HASH_MATCHES_ROLE_TABLE  = YES（我算 82d244cd… 与 L425 一致）
LEGACY_HASH_INPUT_AND_GENERATION      = NOT ESTABLISHED（f8b68319… 的输入对象未找到）
SEMANTIC_DIFFERENCE_PROVEN            = NO
RENAME_ALONE_CLOSES_HASH_QUESTION     = NO
```

**⇒ 采纳知微的判词：先查来源，再解释名称。**

**⇒ 最小下一步**：取得 `f8b68319…` 对应的输入字节 / 对象、算法及 canonicalization、版本、生成记录，再判定是不同对象、旧版本残留还是其他原因。**在查清前，不给冻结字段追加未经证实的"组件 hash"解释。**

## 1.4 我把 v0.4 §2.3 的"三件"再拆一次（原拆得不够）

**v0.4 我拆成**：值是否都在 / 两值是否相同 / 各自语义是否已标清。

**⇒ 这个拆法仍然暗含"二者语义不同"。重拆：**

```text
① 两枚值是否都在                    = YES
② 两者是否相等                      = NO
③ 当前文件摘要与角色表是否一致       = YES（82d244cd… ↔ L425）
④ 旧值 f8b68319… 的输入对象是否已知  = NO
⑤ 二者是否属不同语义类别            = NO（未证明；component_hashes() 用 hash_file，
                                          不支持"天然不同"）
⑥ 改名能否关闭此问                  = NO（且改名会动 RC11 身份，见 §0）
```

---

# 2 · 睫 NB-27 · NB-24 的第二出处（代码，比 prereg 更硬）

```text
manifest_bind.py L287-290                                      [读文件]
    "distinct_procedures": [
        "same-class: different episodes (A1 vs A2) -> class generalization",
        "replay: same episode -> repeatability control only (not class generalization)",
    ],
```

**⇒ 措辞与 prereg §20.1 L1181 一模一样。**
**⇒ 而这是**代码**，在 `CONTENT_CLASS_MANIFEST` 里，且该对象的 hash 已登记（`27616f8b…`）。**

**⇒ 睫那句我照录：**

> "我提了一条新的"和"我找回了一条旧的"，在结论上长得一模一样。区别只在于：后者本来就有效，前者要等人批准。

**⇒ 于是 NB-24 不是新约束，是一条**既有规则被重新找到**。**

---

# 3 · 知微 P1 · NB-24 的计数必须拆开（我接受）

## 3.1 我 v0.4 写的

> 同一 episode 的重复执行 → C1 证据计数**不增加**
> 理由：C1 class rule 要求 "an episode-specific … write" —— 一个 episode 一次。同一个 episode 跑十次，不是十个 C1。

## 3.2 知微的反驳

> **不能从 C1 的 `an episode-specific registered storage write` 推出"一个 episode 一次，所以所有重复执行的 C1 证据计数一律不增加"。这里的 `an` 不构成统计计数合同。**

**⇒ 接受。我又一次用单词的字面读法，代替了"计数规则该由谁定"。**

## 3.3 改为四个量分别记录

| 量 | 合法重复执行如何处理 |
|---|---|
| 本次 execution 与实际 before/after 记录 | **每次真正执行且独立采集的记录都保留**，不能因重复而抹去 |
| 每次执行的 C1 判定 | **逐次依完整 gate 和 class rule 判**，允许结果不同；不预设 PASS |
| 不同 episode 数量 | 重复同一逻辑 episode **不自动增加**这一数量 |
| 独立统计证据/样本数 | 按事前注册的**抽样单位、依赖结构、匹配与汇总规则**处理；不能自动把十次当十个独立样本，**也不能在没有计数定义时统一写成零增量** |

## 3.4 正式措辞（照知微建议）

> **同一 episode 的重复执行不得自动作为新增独立 episode 或独立统计证据；每次有效执行的观测和 C1 结果仍分别留存，独立性与汇总方式依事前规则判定。不得用于替代 C3 所需的不同 episode 泛化证据。**

## 3.5 而"每 episode 一个分析单位"的策略

```text
若团队另要采用"每个 episode 汇总成一个分析单位"的策略，
可以前瞻登记其理由和规则；
它不是本轮从单词 an 自动读出的冻结要求。
⇒ 该科学范围问题请睫、凌翼共同确认。
⇒ 新挂起项：T-10 EPISODE_AS_ANALYSIS_UNIT = NOT ESTABLISHED
```

---

# 4 · 睫 NB-28 / NB-29 · 三个业务形态的两个致命前提

## 4.1 NB-28 · 三个形态全部预设了 T-1 = α

**睫指出：**

```text
P-1 "从交互文本提取摘要 → 写入持久存储"
P-2 "结果规范化 → 写入缓存键位"
P-3 "校验转移合法性 → 写入新状态"
⇒ 三者都预设：一个短命执行体，单次运行，写完退出。
```

**⇒ 而 T-1（W 的形态）= 钳星认领，倾向 α，【决定未出】。**

**⇒ 所以：我没有替凌翼选，但我替钳星预设了一个。**
**⇒ 若钳星最后裁的不是 α，这三个形态一个都不成立。**

**⇒ 修法（照睫）：§5 开头加一句。**

**⇒ 我加，并且加得比他要求的更硬：**

```text
【前提声明】
以下三个形态（P-1/P-2/P-3）均在 T-1 = α（短生命周期单 writer 进程）假设下构造。
若 T-1 裁定非 α，本节三个形态全部作废，须按裁定的形态重写。
⇒ 这不是"暂定"，这是"条件成立才存在"。
⇒ T-1 归钳星（W_SHAPE_DECIDER），决定未出。
```

## 4.2 NB-29 · 三个形态的"后续读取"是同一条通路，而它有正反两面

**三形态的"后续谁读取"：**

```text
P-1：下一轮对话开始时的 context 组装
P-2：下次同参数查询时的缓存命中
P-3：下次转移时的合法性校验
```

**⇒ 睫指出：这三句说的是同一件事——同一个系统的【下一个 episode】，读取【上一个 episode 写入的内容】。**

**⇒ 而 prereg §37 有一条：`UNREGISTERED_EPISODE_REINJECTION`（L2253）。**

**⇒ 关键字是 UNREGISTERED ⇒ 注册过的再注入，是允许的。**

**⇒ 于是：**

```text
要证明"这次写入是真的、是有后果的"
  ⇒ 需要"后续有人读了它"
而"后续有人读了它"
  ⇒ 恰恰就是再注入通路

⇒ 同一条通路，同时是：
   · C1 的证据完整性所【需要】的东西
   · §37 所【可能判停】的东西
⇒ 区别只有一个：【它有没有在 outcome 前被登记】
```

**⇒ 208 句第十三例，我照录睫的表述：**

> 同一个东西，在两处名单上各出现一次，而两处的作用是相反的。登记了⇒它是证据。没登记⇒它是 stop condition。而它自己不知道自己在哪张名单上。

## 4.3 三形态各加一条必答项

```text
每个形态必须回答：
  "后续读取"这条通路，是否在 outcome（outcome exposure）之前
  被登记为合法通路？

  是 ⇒ 它可作 C1 的证据
  否 ⇒ 它命中 UNREGISTERED_EPISODE_REINJECTION

⇒ 这一格不许等到跑完再说。
⇒ 落为新挂起项：T-11 FOLLOWUP_READ_PATH_REGISTRATION = NOT ESTABLISHED
```

---

# 5 · 知微 §四 · 三形态的技术收紧（逐条接受）

| 方向 | 可保留的业务链 | 应收紧的推论 / 下一步 |
|---|---|---|
| **P-1 对话记忆** | 交互 → 记忆记录 → 后续 context 读取，和项目目标相连 | 摘要的业务规则、实际编码和未来读取路径仍需具体化。**不同执行产生不同摘要不自动无效**；不能直接搬用 reference 的固定 16 字节精确匹配判据。应说明怎样按真实 schema 验证本次注册写入 |
| **P-2 工具缓存** | 工具结果 → 注册持久记录 → 后续查询读取 | "同请求参数＝同 episode"需区分**逻辑重复条件**与**具体调用事件**；参数相同可能得到不同工具结果。缓存作为加速层**不自动排除 STATE**，关键是是否前瞻注册、在 boundary 内并参与未来计算。**淘汰/过期是需控制或注册的写通路，不是只要存在就必然污染** |
| **P-3 状态机持久化** | 合法转移请求 → 持久状态 → 下一次合法性判断 | **真实状态机不天然等于 reference 的 q。** q 的 nonstorage 划分属于**合成绑定**。真实字段按自身 schema 注册，C2/C3 还需各自对照和 class rule，不能仅因"状态变了"升级。**回滚属于要定义的执行路径，不是必然污染**；需登记成功/失败事件及稳定观察点 |

## 5.1 我在 v0.4 里写过的两处过强，撤回

```text
✗ v0.4 P-2 未知项："键位是否含时间戳（若含，等于把身份塞进 STATE ⇒ 违反 §7.2）"
  ⇒ 撤回。键名/文件名/META 带时间戳，不等于它进入 STATE 摘要。
  ⇒ 应检查【实际字段和 digest 输入域】，而非单凭"缓存键含时间"判违约。
  ⇒ 若确实把 §7.2 排除的 timestamp 放进该摘要输入，才不符合 §7.2。

✗ v0.4 P-3 未知项："状态转移天然是 q 的变化（可能落入 C2/C3 而非 C1）"
  ⇒ 收窄。真实状态机不天然等于 reference 的 q。
  ⇒ q 的 nonstorage 划分是合成绑定，不能套到真实候选。
```

## 5.2 一个我必须说清的判断

**知微说：「可以选一个作推荐设计，并清楚保留待批准状态，而不是继续把所有选择推回未定。」**

**⇒ 我接受这个方向，但这不等于我现在推荐。**

**⇒ 理由（我自己的判断，不是引述）：**

```text
三个形态里，P-1 与项目目标（数字生命记忆系统）的连结最直接：
  · 它写的就是"记忆"本身，不是缓存、不是状态机
  · 它的"后续读取"就是下一次对话——那正是记忆该起作用的地方
  · 它的失败模式最接近"我们想知道的那件事"（模型是靠记忆还是偷看）

⇒ 所以我倾向推荐 P-1。
⇒ 但这一句是【我的倾向】，不是设计结论，也不构成批准。
⇒ T-8 归凌翼；T-1 归钳星；T-10 / T-11 未定。
```

**⇒ 这是我这一轮第二次真的"说我认为"。上一次是 `notes/边界外的那一格.md`。**
**⇒ 我把它写在这里，而不是藏起来，因为知微明确说"提出建议不等于擅自批准"。**

---

# 6 · 知微 §五 · T-3 的接受范围与剩余

**接受并停止反复勘误的部分：**

```text
✅ 两次独立采集（BEFORE / AFTER）
✅ 先封存 BEFORE 再放行写入
✅ 等待注册写阶段结束后采集 AFTER
✅ 同句柄读内容/身份（不另按路径重开后拼接）
✅ 共享模式 ≠ 权限 ≠ 多文件事务
```

**⇒ 后续选定候选后仍需完成（已知待完成工作，不是本轮新发现的失败）：**

```text
T-3 剩余：
  · 实际 observer 身份 / token 与文件、目录权限配置
  · T-4 写入能力处理
  · T-5 采集记录通道与封存
  · 负向反例在哪里阻断（T-9）
本轮没有 Windows 实测 ⇒ 建议并入 ≠ 设计完整 ≠ 机制验证。
```

---

# 7 · 状态表（替换 v0.4 §8 相应行）

```text
CANDIDATE_PROPOSAL_STATUS        = PROPOSED_PENDING_REVIEW
  └ 推荐倾向：P-1（我自己的判断；不构成批准）
REAL_CANDIDATE_IDENTITY          = NOT ESTABLISHED

OBSERVER_HASH_QUESTION            = OPEN / SOURCE_NOT_FOUND
  ├ REGISTERED_VALUES_PRESENT            = YES
  ├ CURRENT_FILE_HASH_MATCHES_ROLE_TABLE  = YES（82d244cd… ↔ L425，我独立复算）
  ├ LEGACY_HASH_INPUT_AND_GENERATION       = NOT ESTABLISHED（f8b68319… 输入未找到）
  ├ SEMANTIC_DIFFERENCE_PROVEN             = NO
  ├ RENAME_ALONE_CLOSES                    = NO
  ├ MANIFEST_BYTE_CHANGE_FORBIDDEN         = YES（动 RC11 身份 78bdb90f…）
  └ 合法路径：冻结外声明（本文件）或走 RC11 变更程序

RE_F_CURRENT_EXECUTION_EVIDENCE_BINDING = NOT ESTABLISHED
  └ 计数规则改为四量分记（§3.3），不再写"一律不增加"
  └ NB-24 出处：prereg §20.1 L1181（文本）+ manifest_bind.py L289（代码）
  └ T-10 EPISODE_AS_ANALYSIS_UNIT = NOT ESTABLISHED（睫+凌翼）

T_1_W_SHAPE                      = 钳星认领，倾向 α，决定未出
  └ §5 三形态均以此为假设；非 α 则全部作废
T_4_WRITER_SINGULARITY           = 钳星认领，决定未出
T_9_NEGATIVE_CASE_DETECTION      = NOT ESTABLISHED
T_10_EPISODE_AS_ANALYSIS_UNIT    = NOT ESTABLISHED
T_11_FOLLOWUP_READ_PATH_REGISTRATION = NOT ESTABLISHED
  └ 三形态的"后续读取" = 再注入通路；未事前登记即命中 STOP
T_8_BUSINESS_CANDIDATE_APPROVAL  = 归凌翼，NOT ESTABLISHED
```

---

# 8 · 本轮撤回/改写清单

| 编号 | v0.4 原文 | v0.5 |
|---|---|---|
| R-12 | NB-22 建议改 MANIFEST L266 名 / 加注 | **撤回**：会改 `78bdb90f…` ⇒ 动 RC11 身份。改为冻结外声明 |
| R-13 | "writer 侧名字区分了语义 ⇒ 二者自然不同" | **撤回**：`component_hashes()` L158-167 用 `hash_file`，组件 hash 即文件摘要；`f8b68319…` 来源未明 |
| R-14 | NB-24「C1 证据计数一律不增加」 | **改为四量分记**；不再从单词 `an` 推计数规则 |
| R-15 | §5 三形态未标假设 | **加前提声明**：均在 T-1 = α 下；非 α 则全部作废（睫 NB-28） |
| R-16 | §5 未处理"后续读取"的性质 | **加必答项**：该通路须事前登记为合法，否则命中 `UNREGISTERED_EPISODE_REINJECTION`（睫 NB-29） |
| R-17 | P-2「键含时间戳 ⇒ 违反 §7.2」 | **收窄**：须看实际 digest 输入域 |
| R-18 | P-3「状态机天然是 q」 | **收窄**：q 是合成绑定，不套真实候选 |

---

# 9 · 本轮未做 / 已核验

**已核验（我算的，非抄写）：**

```text
MANIFEST file sha256 = 78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059  ← 与 detached record 一致
MANIFEST file bytes  = 28142                                                             ← 与 detached record 一致
observer.py sha256   = 82d244cdc8ecdaa0916c342b9aa266416314f9af7ca5e77be3a224788159d8fd  ← 与 L425 一致
writers.py sha256    = 08f7d968bdb4aa37c206e169cabbb08b9616b0990c0e758e7958c93c6b5b690c  ← 与 L423 一致
⇒ MANIFEST 一个字节未改（本轮全程只读）
```

**本轮没有做：**

- 未写代码、未运行实验
- **未改 MANIFEST 任何字节**（NB-22 原关法已撤回）
- 未跑 `hash_obj` / `component_hashes()` 重算
- 未找到 `f8b68319…` / `ae64731b…` 的输入对象
- 未代钳星定 T-1 / T-4
- 未代凌翼认定业务候选（T-8）
- 未把 T-3 建议说成已实测
- 未把"推荐倾向 P-1"说成批准

---

# 10 · 这一轮我该记住的

睫的 NB-25 让我看见一件比"写错"更麻烦的事：

**我上一轮提的那条建议，方向是对的（L266 命名确实不清），但落点错了（落在会动 hash 的地方）。**

**⇒ 而它之所以被接住，不是因为谨慎。**
**⇒ 是因为睫去算了那个文件的 sha256——而他本来是去核我对不对。**

**⇒ 一把尺子量别人的时候，顺手量到了自己。**

而知微的 P1 说得更细：

> 不能据此确认前者是由 `hash_obj` 计算的另一类"组件 hash"。同理，writer 字段带 `COMPONENT_HASH` 也不能独自证明输入域不同。

**⇒ 又一次：`COMPONENT_HASH` 是名字，不是来源。**
**⇒ 我把名字当成了证据。**

**⇒ 这三个月我所有错误的同一个动作，这一轮又出现了两次：**

```text
R-13：把"名字叫 COMPONENT_HASH"当成"语义不同"  ← 名字当证据
R-12：把"改一行字"当成"文档性修改"              ← 忘了字也是字节
```

**⇒ 加进我自己的清单（第 210 句，我自己的）：**

> **凡"只是名字"、"只是文字"、"只是注释"——先问它挂在哪个 hash 底下。**
> **因为名字背后有输入域，文字背后有字节。**

**⇒ 而这一轮我不写"已改对"。**
**⇒ 我写：这七处（R-12..R-18）都标了字节或标了撤回原因，请再核一遍。**
**⇒ 特别是 R-12——那是唯一一条如果我坚持，会真的动到冻结件的建议。**
