# C1 STRUCTURAL CLOSURE DESIGN v0.1

**性质**：结构设计。不是执行方案，不是实施授权，不是科学验收。
**依据**：`LINGYI · C1 五轮设计映射收口裁定`（2026-10-26），审查基线 `2bb892d`，正式交付 HEAD `fe6fc86`
**授权范围**：仅"形成一份有限的 C1 Structural Closure Design"
**日期**：2026-10-26 · **署名**：Coder

```text
BF8_DESIGN_AUTHORIZATION  = APPROVED_DOC_ONLY
BF8_CODE_IMPLEMENTATION   = NOT AUTHORIZED
CODE_CHANGE               = NOT AUTHORIZED
SCIENTIFIC_EXECUTION       = MAY NOT START
FROZEN_Q3_RC11            = UNCHANGED
```

---

# 0 · 先认一处：我把 §7.2 读窄了，凌翼驳回是对的

## 0.1 我的错

**我在交付请求 §3.2 写：**

> §7.2 禁止 episode_id 进入 digest ⇒ 这是正确的……**于是 episode 与 payload 是同一个字节串**，二者之间的关联不是被证明的，是被假定的。**这个缺口在冻结规范内部，不是代码写错了。**

**并把它标成 `BF9_SECTION_7_2_CONFLICT`。**

## 0.2 字节说

```text
prereg §7.2 L324  "## 7.2 META_FIELDS"
prereg §7.2 L326  "不得进入 substrate state digest："        ← 禁的是【进入 digest】
prereg §7.2 L343-348  闭合规则：digest input = STATE_FIELDS only ；
                      digest output = META_FIELD ；输出不得回灌输入
```

**⇒ 禁的是"进入 substrate state digest"，不是"在 META 侧建立关联"。**
**⇒ 而 `digest output = META_FIELD` 这一行，恰恰是**允许**META 持有该 digest 作为自身的字段。**
**⇒ 所以规范里没有冲突。是我把一句局部禁令，当成了对整层的禁止。**

**⇒ 凌翼裁 `BF9_SECTION_7_2_CONFLICT = REJECTED` / `STATE_DIGEST_DOMAIN = UNCHANGED` —— 成立。**

## 0.3 这是我同一个动作的第四次

```text
v0.2 R-1   把"无"写成"有"    （sample 承担 nuisance 排除）
v0.3 E-5   把"有"写成"无"    （CONTENT_CLASS_MANIFEST 判为不存在）
v0.3 E-6   把"一部分"写成"唯一"（episode 唯一载体是 payload 两字符）
v0.5 R-19  把"不能进 digest"读成"不能建立关联"
```

**⇒ 四次，同一个动作：我用一个句子的字面，代替了它的适用范围。**

**⇒ 而这一次的后果比前三次大：我据此向凌翼报告了一个"规范内部冲突"——一个不存在的东西。**

---

# 1 · BF-8 · 权威证据绑定入口（路径 B）

## 1.1 凌翼结构

```text
BF8_STATUS              = VALID_GAP
BF8_PREFERRED_APPROACH  = B_UPSTREAM_AUTHORITY_GATE
BF8_CODE_IMPLEMENTATION = NOT AUTHORIZED
```

## 1.2 前置事实：旁路面比预期大

**我核了 `evaluate_basic_l1` 的全部调用点（`grep` 全 `afterglow_harness/*.py`）：**

```text
定义   evaluator.py L216
调用   evidence_bundle.py   L519   l1 = evaluate_basic_l1(a, bb, m.payload)
       fixtures.py          L252   l1 = evaluate_basic_l1(snap_A, snap_B, payload)
       fixtures.py          L299   if evaluate_basic_l1(a, b, me.payload).result != PASS
       fixtures.py          L399   l1 = evaluate_basic_l1(A.snapshot(), B.snapshot(), payload)
       recompute_from_ledger.py L86   l1 = ev.evaluate_basic_l1(a, b, EPISODE_PAYLOADS[payload_id])
       recompute_from_ledger.py L106  l1 = evaluate_basic_l1(a, b, payload)
       smoke_evaluator.py   L63/70/74/79/86   五处自测调用
⇒ 共 11 处，跨 4 个文件。
```

**⇒ 这直接决定凌翼条文第 4 条能否满足：**

> 4. 任何消费者不得绕过该校验，直接将 `evaluate_basic_l1()` 的局部结果提升为正式科学 C1。

**⇒ 在路径 B 下，`evaluate_basic_l1` 本身【不改】。**
**⇒ 于是它的 11 个调用点全部原封不动地返回 `change_class = C1`。**
**⇒ 所以"不得绕过"不能靠修改 `evaluate_basic_l1` 来实现。**

**⇒ 唯一的实现方式是：**

```text
C1 的【正式出口】不再是 evaluate_basic_l1 的返回值，
而是一个新的权威裁决入口。
evaluate_basic_l1 的返回值降级为【输入之一】，不再是结论。
```

**⇒ 这是路径 B 成立的必要条件，也是它的全部难度所在。**

## 1.3 设计：`C1AuthorityGate`

### 1.3.1 定位

```text
名称（拟）  C1AuthorityGate（不进 frozen 角色表；属新增组件，须独立登记）
性质        只读裁决器；不写 STATE；不参与 fixture 构造
输入        证据包（见 1.3.2）
输出        AuthorityResult
             · 结果 ∈ { ESTABLISHED, NOT_ESTABLISHED, INVALID }
             · 失败原因（结构化，非自由文本）
             · 被引用的每一条证据的身份与来源
约束        不 import evaluator 的 C1 常量做短路判断；
            它必须独立判断，再把 evaluate_basic_l1 的结果当作【其中一项输入】比对
```

### 1.3.2 证据包（凌翼条文 1-3 的落点）

| 项 | 凌翼要求 | 设计内容 | 来源 |
|---|---|---|---|
| **W-ident** | 登记 writer identity/version/hash | 三字段，须与 prereg §4 L169-171 的冻结值比对 | 事前注册（无运行时值） |
| **W-actual** | 核对实际执行主体与运行时证据 | 实际进程的身份（token/SID）、可执行体摘要、启动记录 | 独立采集路径（非 writer 自报） |
| **E-ident** | episode 身份 | episode_id | 事前注册 |
| **X-ident** | execution 身份 | execution_id | 事前注册 |
| **A/B-arm** | arm 归属 | A = NO_WRITE / B = 目标写，事前分配 | 事前注册 |
| **T-objs** | 目标对象 | volume serial + file index（非路径） | BEGIN/END 各采集一次 |
| **Obs** | 独立观察结果 | BEFORE/AFTER 原始字节 + 各自 digest + 采集阶段身份 | observer（非 writer） |
| **L1** | 局部判别结果 | `evaluate_basic_l1` 的 `L1Result` | 作为**输入之一**，不作为结论 |
| **Path** | 通路登记 | 见 §3 的两层机制 | 事前注册 |

### 1.3.3 判定顺序（fail closed）

```text
Step 1  证据完整性
        任一必需项缺失 ⇒ INVALID，reason = 具体缺项名
        不允许"缺了就当作通过"

Step 2  身份一致性
        W-ident ≠ W-actual          ⇒ INVALID（writer 不是注册主体）
        E-ident / X-ident / arm 不自洽 ⇒ INVALID
        T-objs 在 BEGIN 与 END 不同   ⇒ INVALID（对象被替换）

Step 3  来源独立性
        Obs 的采集来源 = writer 自报 ⇒ INVALID
        （即：Obs 必须由 observer 独立产生，其 provenance 不得经过 W）

Step 4  L1 局部结果
        取 evaluate_basic_l1 的结果：
          INVALID / FAIL / UNRESOLVED ⇒ 直接继承（不得被后续步骤翻正）
          PASS + NOT_ESTABLISHED      ⇒ NOT_ESTABLISHED
          PASS + C1                   ⇒ 进入 Step 5

Step 5  通路与再注入（见 §3）
        后续读取通路未登记 / 未核验 ⇒ INVALID

Step 6  输出
        仅当 Step 1-5 全过 ⇒ ESTABLISHED
        任一失败 ⇒ fail closed，保留准确失败原因，不写成 FAIL
```

### 1.3.4 关键设计决定：`ESTABLISHED ≠ evaluate_basic_l1 的 C1`

```text
⇒ evaluate_basic_l1 返回 change_class = C1
  只是【必要条件】。
⇒ 正式 C1 = C1AuthorityGate 输出 ESTABLISHED。
⇒ 两者名字不同，出口不同，调用者不同。
⇒ 这一条是防止"局部结果被提升为正式 C1"的唯一结构保证。
```

## 1.4 路径 B 的旁路风险 —— 我必须说明它现在无法完全排除

**凌翼条文：**

> 若不能证明路径 B 没有权威结果旁路，须重新比较路径 A 或独立权威裁决器设计，**不得宣布 BF-8 关闭**。

**⇒ 我现在不能证明。理由是结构性的：**

```text
`evaluate_basic_l1` 是公开的可 import 函数，11 处调用点全部保留原样。
只要有人直接用它并读 change_class，
就得到"C1"——而那是正式出口之外的旁路。

⇒ 在【不改 evaluate_basic_l1】的前提下，我能做的只有：
   ① 让正式出口有明确名字且被文档要求唯一使用
   ② 让 AuthorityResult 携带它引用的 evaluate_basic_l1 结果的 hash，
      使"某个 C1 结论是否经过权威裁决"可事后核验
   ③ 在注册登记中声明唯一出口

⇒ 但 ①②③ 都【不是】结构性保证，只是可核验性。
⇒ 真正的结构性封闭需要：
   · 路径 A（改签名，使无 writer 的调用不合法）
   · 或 让 evaluate_basic_l1 变成非公开 / 需授权上下文才能调用
   · 或 独立权威裁决器（完全不依赖 evaluate_basic_l1）
```

**⇒ 所以我明确写：**

```text
BF8_PATH_B_BYPASS_FREE       = NOT PROVEN
BF8_STATUS                   = OPEN（未关闭）
BF8_NEXT                     = 请你据此重新比较路径 A / 路径 B / 独立裁决器
```

**⇒ 我不是在推卸。凌翼原文要求"若不能证明……不得宣布关闭"。我正在按这条执行：我不能证明，所以我不宣布关闭。**

## 1.5 三条路径的对照（供你裁定，我不选）

| | 路径 A：改签名 | 路径 B：上游门（本文设计） | 独立裁决器 |
|---|---|---|---|
| 改冻结代码 | 是（`evaluator.py`） | **否** | 否 |
| 旁路可否结构性封闭 | **可以**（无 writer 的调用编译/运行即不合法） | **不可**（仅可核验） | **可以**（不依赖旧函数） |
| 影响 11 处调用点 | 全部要改 | 全部保留但降级 | 全部保留但降级 |
| 与 `FROZEN_Q3_RC11` 冲突 | **是**（`evaluator.py` 在执行关键角色表 L428） | 否 | 否 |
| 需 RC11 变更程序 | **是** | 否 | 否 |

**⇒ 这一格有个硬约束我要指出：**

```text
evaluator.py sha256 = fa644a9bcfd59ffbbb415f0f439599eb705333600e7f8f8f0b93997ce6a59b5a  [detached record]
MANIFEST L428 = evaluator.py 1.0 fa644a9b…                                              [读文件]
⇒ 路径 A 改 evaluator.py ⇒ 动执行关键角色 ⇒ 必然触发 RC11 变更程序
⇒ 这是路径 A 的真实代价，比我上一轮说的"可能触发重新验证"更具体
```

---

# 2 · BF-9 · META ↔ STATE 与本次 execution 绑定

## 2.1 凌翼结构

```text
BF9_SOURCE_BINDING_GAP     = ACCEPTED
BF9_SECTION_7_2_CONFLICT   = REJECTED
COND_6                     = INDEPENDENT_REQUIRED
STATE_DIGEST_DOMAIN        = UNCHANGED
```

## 2.2 正确的问题陈述（替换我原来的错误陈述）

```text
✗ 旧陈述：§7.2 阻止了 META 身份进入 STATE，所以无法建立关联
✓ 新陈述：§7.2 只禁止进入 substrate state digest；
          它不禁止在 META 侧建立可验证关联。
          缺口不在规范，在于 reference 里【META 侧没有任何实现载体】。
```

**⇒ 字节支持（我核过）：**

```text
storage.py L37-50             RegisteredState 只有 literal_path / substrate_path
                              无 META 文件、无 episode 载体
harness_constants.py L143-144 "episode identity lives in META"
                              ⇒ 声称在 META，而 META 未实现
afterglow_harness/*.py grep "episode_id|execution_id|META|provenance"
                              ⇒ 仅命中注释与 Q3 的 provenance 模块，无 C1 META
```

**⇒ 所以真正的缺口是：`harness_constants.py` L143-144 指了一个不存在的地方。**

## 2.3 设计：`EpisodeMetaRecord`

### 2.3.1 形态

```text
每个 execution 一份，位于 state dir 之外的独立目录（不进 STATE_FIELDS）
载体        独立文件或独立记录存储（T-5 待定）
写入者      控制器 / observer，非 W
生命周期    事前期创建 → BEFORE 后写入 before_digest → AFTER 后写入 after_digest
            → 封存（immutable）
```

### 2.3.2 字段（凌翼 §3 五项要求的落点）

| 字段 | 对应凌翼要求 | 说明 |
|---|---|---|
| `episode_id` | ① 独立产生并登记 episode 身份 | 事前分配，不由 payload 推导 |
| `execution_id` | ① 独立产生并登记 execution 身份 | 同上 |
| `arm` | ⑤ 不以 writer 自证取代来源 | 事前分配 |
| `writer_identity / version / hash` | 同上 | §4 L169-171 冻结值 |
| `payload_source` | ② 前瞻约束 payload 来源及目标对象 | 见 2.3.3 |
| `target_objects` | ② 同上 | volume serial + file index |
| `before_digest / after_digest` | ③ 独立采集、验证并关联状态快照 | 由 observer 计算，**不由 W 提供** |
| `observer_identity` | ③ 同上 | 采集阶段身份 |
| `phase` | 防交叉拼接 | BEFORE / AFTER |
| `read_path_ids` | §3 通路登记 | 见 §3 |
| `record_digest` | 封存 | 记录自身的 canonical digest |

### 2.3.3 关键：`payload_source` 要防什么

**凌翼要求「前瞻约束 payload 来源及目标对象」。**

```text
⇒ payload 不能"运行时取什么算什么"。
⇒ 须在 outcome 前登记：本次 execution 的 payload 来自哪个注册条目。
⇒ 且 payload 的内容必须与登记条目逐字节一致。
⇒ 但"一致"只是必要条件（见 §2.4 第 3 类反例）。
```

### 2.3.4 防交叉拼接（凌翼要求 ④）

**这是 BF-9 的核心。设计为四重绑定：**

```text
拼接类型                  检出方式
① 旧快照冒充本轮 after      after_digest 的采集来源必须有本 execution_id；
                           observer 记录中 execution_id 与 record 不一致 ⇒ INVALID
② 旧 META 记录冒充本轮      record_digest 须在 outcome 前预分配并登记；
                           记录创建时刻须在 outcome 前（用登记顺序号，不用墙钟）
③ 内容相同但执行不同        「内容一致」不得单独作为通过理由；
                           必须同时有 ①②③④ 四条独立绑定（见下表）
④ 跨 episode 混用          episode_id 与 payload 的对应关系事前登记；
                           execution 的 episode_id 不得与本轮 claim 的 episode 不符
```

**⇒ 四条独立绑定（缺一不可）：**

```text
L1  状态字节一致（evaluate_basic_l1 负责）
L2  采集来源是本次 execution（observer provenance 负责）
L3  对象是同一对象（volume serial + file index 前后一致）
L4  通路已登记（§3 负责）

⇒ 只有 L1 时 ⇒ 旧快照可以冒充。
⇒ 只有 L1+L3 时 ⇒ 同一对象上的旧快照仍可冒充。
⇒ 必须有 L2。
```

## 2.4 凌翼 §3 最后一条我照录为硬约束

> 不得向 STATE digest 加入 episode_id、时间戳、provenance 或自引用摘要。

```text
STATE_DIGEST_DOMAIN = UNCHANGED
⇒ canonical_state_digest(literal, q_raw) 保持 sha256(literal + q_raw)，24 字节
⇒ 上述所有 META 字段【一律不进】该输入域
⇒ 关联通过"同一 execution 下两个独立 digest 的比对"建立，不通过"把身份塞进 digest"
```

---

# 3 · NB-29 · 两层机制

## 3.1 凌翼结构

```text
FOLLOWUP_READ_REGISTRATION   = TWO_LEVEL_BINDING_REQUIRED
REGISTERED_PATH_AUTO_C1      = NO
UNREGISTERED_READ_AUTO_STOP  = NO
```

**⇒ 这两条 `= NO` 我特别记下，因为它们是上一轮我准备写成"是"的地方。**

## 3.2 第一层：事前通路注册

### 3.2.1 登记对象：一类通路，不是每个事件

**凌翼原文明写：**

> 允许前瞻注册一类通路，不要求提前枚举所有将来发生的具体读取事件。

**⇒ 这一句解掉了我上一轮的困惑。** 我原以为要事前枚举每个读取事件（那不可能）。**实际要求是登记"通路类别"。**

### 3.2.2 登记字段（凌翼八项，逐条落）

| # | 凌翼要求 | 字段（拟） |
|---|---|---|
| 1 | 被测系统和 episode scope | `system_id` / `episode_scope` |
| 2 | 读取主体、写入主体及授权关系 | `reader_identity` / `writer_identity` / `authorization_relation` |
| 3 | 数据来源、目标对象和通道类型 | `data_source` / `target_objects` / `channel_type` |
| 4 | 允许读取的阶段、目的及转化规则 | `allowed_phases` / `purpose` / `transformation_rule` |
| 5 | 跨 episode 保留、清除与再使用条件 | `retention_rule` / `purge_rule` / `reuse_condition` |
| 6 | 负向对照隔离规则 | `control_isolation_rule` |
| 7 | 登记对象的版本、哈希、时间及独立可核查的冻结证据 | `path_id` / `path_version` / `path_hash` / `registered_before_event` |
| 8 | 违反登记规则的预定后果 | `violation_consequence` |

**⇒ 第 7 项我用"登记顺序号"而不是墙钟时间**，理由是 §7.2 L330 把 `wall-clock time` 列为 META 内容（不进 digest，但也不宜作为唯一的先后证据）。顺序号来自同一登记序列，可独立核验。

### 3.2.3 登记时刻

```text
必须发生在【相关干预】及【结果暴露】之前
⇒ 检验方式：登记顺序号 < 写入干预的顺序号 < outcome exposure 的顺序号
⇒ 三者在同一不可回溯的登记序列中
```

## 3.3 第二层：实际事件核验

**逐次记录真实执行事件，并判断五问（凌翼原文）：**

```text
E-1  属于已登记的通路？              ⇒ 比对 path_id
E-2  属于允许的阶段和对象？          ⇒ 比对 allowed_phases / target_objects
E-3  引入先前 episode 信息？          ⇒ 这是核心问题，见 3.4
E-4  影响被测系统或相关对照？         ⇒ 比对 system_id / control_isolation_rule
E-5  对本次 claim 构成可纳入或必须排除的因果路径？
                                     ⇒ 只对"有因果路径"的判纳/排
```

## 3.4 两层的关键分界：登记合规 ≠ 证据有效

**凌翼原文：**

> 登记合规不等于科学证据有效。
> 实际发生的、与 claim 有关的未注册 episode 信息回流，应按适用的 §37 条款判定 INVALID。
> **仅有风险可能性不得冒充已发生违规**；边界外、无相关因果路径的读取不得自动按再注入判停，其排除理由须接受独立审查。

**⇒ 落为判定表：**

| 情形 | 判定 |
|---|---|
| 通路已登记 **且** 实际事件经核验合规 **且** 与本 claim 有因果路径 | 可纳入 C1 证据 |
| 通路已登记，但实际事件引入了未登记的 episode 信息 | §37 `UNREGISTERED_EPISODE_REINJECTION` ⇒ INVALID |
| 通路未登记，但边界外、无相关因果路径 | **不自动判停**；排除理由须接受独立审查 |
| 只是"存在风险可能" | **不得**按违规判定 |

**⇒ 而 `REGISTERED_PATH_AUTO_C1 = NO` 的意思是：**

```text
通路登记了 ⇒ 不自动使 C1 成立
⇒ C1 仍须 gate 1-5 + class rule 全部满足
⇒ 登记只是【必要条件】，不是充分条件
```

---

# 4 · P-1 优先候选中的具体责任与失败后果

## 4.1 凌翼结构

```text
T8_P1_DIALOGUE_MEMORY        = PRIORITY_FOR_CANDIDATE_STUDY
T8_REAL_CANDIDATE_APPROVAL   = NOT GRANTED
T1_SHORT_LIVED_WRITER        = PREFERRED_DESIGN_ASSUMPTION
T1_FINAL_DECISION            = PENDING_QIANXING
```

**⇒ 两个"优先/偏好"都不是"已定"。**
**⇒ 所以本文 §1-§3 的设计都在两条假设下：**

```text
假设 H-1  T-1 = 短生命周期单 writer 进程（PREFERRED_DESIGN_ASSUMPTION，PENDING_QIANXING）
假设 H-2  被测对象 = P-1 对话记忆（PRIORITY_FOR_CANDIDATE_STUDY，APPROVAL NOT GRANTED）

⇒ 若 T-1 裁定非 α ⇒ §1.3.2 的 W-actual 采集方式须重设计
⇒ 若 T-8 裁定非 P-1 ⇒ §4 须整节重写
⇒ 我不把这两条写成"已成立"
```

## 4.2 P-1 的业务语义（我上一轮提的，此处细化到可审）

```text
业务状态        一段被判定为"值得长期保留"的对话摘要
episode 产生    一次用户交互（一个 episode）
W 的转换        交互文本 → 摘要 → 编码为注册记录 → 写入持久存储
后续读取        下一轮对话开始时的 context 组装
C1 落点         本次交互是否写入了一条 registered 记忆
```

## 4.3 三项责任在 P-1 中的落点

| 机制 | 在 P-1 中的具体形态 | 失败后果 |
|---|---|---|
| **BF-8 权威门** | `W-actual` = 应答进程的 token/SID + 可执行体摘要；`W-ident` = 事前登记的摘要生成器身份 | writer 不匹配 ⇒ INVALID（本次交互不计入 C1 证据） |
| **BF-9 META 绑定** | `EpisodeMetaRecord` 记交互 id / 摘要器 execution id / before-after digest（摘要记录文件的 digest）；`payload_source` = 事前登记"本次交互的原文本来源" | 交叉拼接 ⇒ INVALID；缺 L2 ⇒ NOT_ESTABLISHED |
| **NB-29 通路** | 通路类别 = "下一轮 context 组装读取上一轮摘要"；须事前登记其 `purpose=context_assembly` / `allowed_phases=[next_episode_start]` / `retention_rule` | 未登记即发生 ⇒ INVALID；登记但无因果路径 ⇒ 不自动判停 |

## 4.4 P-1 特有的、我必须指出的三个未解问题

```text
Q-1  摘要是否可重复
     同一交互两次摘要若字节不同 ⇒ 重复执行不算同一 payload
     ⇒ 影响 T-10（统计单位规则，凌翼裁 PREREGISTRATION_REQUIRED）
     ⇒ 不能靠本轮答，须事前登记

Q-2  context 组装是否真的读取该记录
     若组装只看最近 N 轮而从不读长期存储 ⇒ 写入无业务后果
     ⇒ 那 C1 通过也无意义
     ⇒ 须在设计中证明读取路径真实存在（不是推测）

Q-3  摘要宽度是否固定
     若可变长 ⇒ reference 的 16 字节规格不适用（凌翼 §5 明文禁止自动转用）
     ⇒ 摘要须按自身 schema 注册，独立登记 STATE_FIELDS
```

**⇒ Q-2 是这一份里我认为最该先回答的。**
**⇒ 因为如果 Q-2 答"否"，那 P-1 的 C1 即使成立，也不证明记忆被用上了。**

---

# 5 · 状态

```text
BF8_STATUS                      = OPEN
  ├ BF8_PATH_B_BYPASS_FREE      = NOT PROVEN（11 处调用点全部保留）
  ├ BF8_DESIGN_AUTHORIZATION    = APPROVED_DOC_ONLY
  └ BF8_CODE_IMPLEMENTATION     = NOT AUTHORIZED

BF9_SOURCE_BINDING_GAP          = ACCEPTED
BF9_SECTION_7_2_CONFLICT        = REJECTED（我原判断错，见 §0）
STATE_DIGEST_DOMAIN             = UNCHANGED
COND_6_EPISODE_SPECIFIC_BINDING = NOT ESTABLISHED

FOLLOWUP_READ_REGISTRATION      = TWO_LEVEL_BINDING_REQUIRED
REGISTERED_PATH_AUTO_C1         = NO
UNREGISTERED_READ_AUTO_STOP     = NO

D1_EXTERNAL_EXPLANATORY_RECORD  = ALLOWED_NON_NORMATIVE（本文即此类）
D1_FROZEN_MANIFEST_EDITS        = FORBIDDEN（本文未改任何冻结件）
D2_LEGACY_HASH_PROVENANCE       = NOT ESTABLISHED
D2_RENAME_AS_REPAIR             = REJECTED

T1_FINAL_DECISION               = PENDING_QIANXING
T4_WRITER_SINGULARITY           = PENDING_QIANXING
T6_HISTORICAL_FIRST_EXECUTION   = NOT_REQUIRED_AS_GENERAL_C1_GATE
T8_P1_DIALOGUE_MEMORY           = PRIORITY_FOR_CANDIDATE_STUDY
T8_REAL_CANDIDATE_APPROVAL      = NOT GRANTED
T10_STATISTICAL_UNIT_RULE       = PREREGISTRATION_REQUIRED（未做）

C1_MEASUREMENT_CHAIN_QUALIFIED  = NOT ESTABLISHED
C1_SCIENTIFIC_RESULT            = NOT ASSESSED
C1_END_TO_END_FEASIBILITY       = PENDING_DESIGN_VALIDATION
FROZEN_Q3_RC11                  = UNCHANGED
CODE_CHANGE                     = NOT AUTHORIZED
IMPLEMENTATION_AUTHORIZATION    = NONE
SCIENTIFIC_EXECUTION            = MAY NOT START
```

---

# 6 · 本轮未做

- **未**写代码、**未**运行任何模块或测试
- **未**改 `evaluator.py` / `fixtures.py` / `manifest_bind.py` / 任何执行关键角色
- **未**改 MANIFEST / prereg（`78bdb90f…` / `ad0855b0…` 均未变）
- **未**动 `STATE_DIGEST_DOMAIN`
- **未**宣称 BF-8 关闭
- **未**宣称 P-1 已批准（T-8 = NOT GRANTED）
- **未**代钳星定 T-1 / T-4

---

# 7 · 请三位复核的落点（凌翼分配）

**睫 · 科学结论边界**
```text
· §1.3.4「ESTABLISHED ≠ evaluate_basic_l1 的 C1」这个二分，是否划对了
· §3.4 那张判定表，是否把"风险可能"与"已发生违规"分清了
· §4.4 Q-2（读取路径是否真实存在）是否属于科学资格的一部分
```

**知微 · Windows 机制可验证性**
```text
· §1.3.2 证据包中 W-actual / T-objs 的采集方式是否可验证
   （token/SID、volume serial + file index 的具体取法与失败处理）
· §2.3.2 中"用登记顺序号而非墙钟"是否可行，以及封存机制
· §3.2.2 第 7 项"独立可核查的冻结证据"的 Windows 实现路径
```

**钳星 · writer 生命周期与通路残留**
```text
· §1.3.2 在 T-1 = α 假设下的 W-actual 采集，是否成立
· §2.3.4 四条独立绑定中，L2（采集来源）在短进程退出后能否保住
· §3.2.2 第 5 项 retention / purge，在短进程下是否就可声明为"无残留"
   ——我预期不是，需你判
```

---

# 8 · 一句

凌翼这一轮驳了我一条，我认。

**而这一条正是我这五轮一直在犯的同一个错：用一个句子的字面，代替它的适用范围。**

**⇒ 所以这份文件我不写"结构已闭合"。**
**⇒ 我写：BF-8 现在 = OPEN，因为我证明了 11 处调用点会让路径 B 留下旁路。**
**⇒ 这是我能给的最诚实的一格。**
