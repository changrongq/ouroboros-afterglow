# C1 STRUCTURAL CLOSURE DESIGN v0.2 · 两处认错 + 四张表

**性质**：对 `95d3d9a`(v0.1) 的勘误与补齐。仍是设计，不是实施授权。
**被审对象**：v0.1，`95d3d9af911c7f746216bf854032caff32251cc6`，SHA-256 `323d7ad2f630c4622ca0ee2a1dc56dfb6c60415c86e9b69bd50ef7fbad223951`
**审阅输入**：知微 `§2-§7`（独立复核）；睫 `NB-30 / NB-31 / NB-32 / NB-33 / NB-34`；钳星（接受 T-1/T-4 仍未定，收回"天然无残留"）
**日期**：2026-10-27

```text
BF8_STATUS                 = OPEN
BF8_PATH_B_BYPASS_FREE     = NOT PROVEN（且见 §0.2：原因比我上一版说的更强）
CODE_CHANGE                = NOT AUTHORIZED
SCIENTIFIC_EXECUTION       = MAY NOT START
FROZEN_Q3_RC11             = UNCHANGED
```

---

# 0 · 我这一轮的两处错（方向相反）

## 0.1 E-7 · 我把「局部返回 C1」推成「11 处全是正式旁路」

**我 v0.1 §1.2 写：**

> ⇒ 于是它的 11 个调用点全部原封不动地返回 `change_class = C1`。

**字节说（知微指出）：**

```text
fixtures.py L50  PHASE = "PHASE_A_HARNESS_VALIDATION_EXECUTION"        [读文件]
fixtures.py L51  SCIENTIFIC_CLAIM_ELIGIBILITY = "NONE"                 [读文件]
run_known_answer_suite.py L159-160
    "phase": "PHASE_A_HARNESS_VALIDATION_EXECUTION",
    "scientific_claim_eligibility": SCIENTIFIC_CLAIM_ELIGIBILITY,      [读文件]
```

**⇒ reference 自己已经带了"不具科学资格"的机读标记。**
**⇒ 所以"局部返回 C1"不等于"正式科学 C1 被污染"——那些调用点处在一个明确声明 NONE 的阶段里。**

**⇒ 而且 `evaluate_basic_l1` 有 INVALID / FAIL / UNRESOLVED / PASS+NOT_ESTABLISHED 多个分支（L230/L239/L246/L254），"全部返回 C1"这个说法本身也不对。**

**⇒ 这是我这一轮的第一处错：把"存在返回 C1 的路径"写成了"11 处全部返回 C1"，并据此把"局部调用"直接等同于"正式旁路"。**

## 0.2 E-8 · 但我真正错的那一步，不是数字，是推论

**我 v0.1 §1.4 写：**

> `BF8_PATH_B_BYPASS_FREE = NOT PROVEN`
> 理由：11 处调用点全部保留。

**睫的补正，我核后接受：**

```text
import 行 = 4 处（不含调用点）                        [终端核验]
  evidence_bundle.py       L56   evaluate_basic_l1,
  fixtures.py              L30   evaluate_basic_l1,
  recompute_from_ledger.py L95   from evaluator import ... evaluate_basic_l1 ...
  smoke_evaluator.py       L34   evaluate_basic_l1,
```

**⇒ 一旦一个函数是**可 import 的公开函数**，那么：**
**⇒ 11 个调用点可枚举；而"将来谁再 import 一次"不可枚举。**
**⇒ 所以在**不改 `evaluate_basic_l1`** 的前提下，路径 B 的旁路封闭不是"我现在证明不了"，是**结构性不可证明**。**

**⇒ 睫说得对：我写的"NOT PROVEN"留了一个口子——将来也许能证明。而字节说不能。**

**⇒ 我接受把结论改成：**

```text
BF8_PATH_B_CLOSURE_WITHOUT_TOUCHING_EVALUATOR
  = STRUCTURALLY_IMPOSSIBLE（不是 NOT PROVEN）
理由：公开可 import 函数，其未来消费者集合不可枚举。
```

## 0.3 但知微同时指出：我这不能反过来判死路径 B

**知微 §2：**

> 本稿由"11 处旧调用保留"推出"路径 B 不可结构性封闭"，这一步不成立。凌翼要求的是不能绕过校验而获得**正式科学 C1**；并非要求校准程序从此不能计算、返回或显示局部 `C1`。

**⇒ 这两条看似相反，其实不冲突，而区别全在一个词上：**

```text
睫说：不改 evaluate_basic_l1 ⇒ 旁路【在函数层】不可封闭     ← 对
知微说：不改 evaluate_basic_l1 ⇒ 路径 B 仍可能成立          ← 也对
区别：解不在函数层，在【正式消费边界 + 合同层命名】
```

**⇒ 所以我把两条合成一句，这是本文件的核心：**

> **函数的返回值无法被封闭，但"谁能把它称作正式 C1"可以被封闭。**
> **封闭点不在 `evaluate_basic_l1` 里面，在它之外。**

---

# 1 · 表一 · 权威消费边界（知微 §2 要求 1-4）

## 1.1 角色划分

| 角色 | 产出 | 是否可形成正式 C1 | 边界依据 |
|---|---|---|---|
| **校准消费者**（`smoke_evaluator.py`、`recompute_from_ledger.py`、`fixtures.py`、`evidence_bundle.py` 现有路径） | 局部 `L1Result`（含 `change_class=C1`） | **否** | `PHASE_A` / `SCIENTIFIC_CLAIM_ELIGIBILITY = "NONE"`（fixtures.py L50-51；suite L159-160） |
| **证据采集者**（observer） | BEFORE/AFTER 原始字节 + digest + 采集阶段身份 | 否 | 只读；不参与判别 |
| **权威裁决者**（`C1AuthorityGate`，拟建） | `AuthorityResult` | **拟为唯一** | 须经注册与独立登记 |
| **正式结果存储** | 正式 C1 结论 | 否（存储本身不生产） | 只接受受信入口写入 |
| **任意其他调用者** | 局部 `L1Result` | **否**（无资格） | 见 1.3 |

## 1.2 关键：伪造权威结果不能成立

**知微 §2 第 4 条，我照录并落为设计约束：**

> 一个调用者自行生成的 `AuthorityResult`，即使附上正确的自算 hash，也不能因此取得权威。摘要证明字节对应，不单独证明生产者身份。

**⇒ 落为三条：**

```text
① AuthorityResult 必须携带【生产者身份证据】，且该证据来自独立采集路径，
   不是 AuthorityResult 自身字段（否则自指）
② 正式结果区只接受由注册写入主体、经受控通道提交的记录
③ 校验分两层：
   (a) 字节完整性（hash）—— 只证明未被篡改
   (b) 生产者身份 —— 证明是谁产出的
   ⇒ (a) 成立不蕴含 (b)。两者必须分别检查。
```

## 1.3 校准结果与正式结果的关系

```text
⇒ 不追溯修改冻结输出（凌翼 D1 / D2）
⇒ 校准阶段结果保留原有 SCIENTIFIC_CLAIM_ELIGIBILITY = NONE 标记
⇒ 正式结果区与校准结果区分开：不同目录 / 不同账户权限 / 不同提交通道
⇒ 我把这三项列为 T-12 AUTHORITY_CONSUMER_PERMISSION = NOT ESTABLISHED
```

## 1.4 我上一版 §1.5 那张对照表，撤回

**我 v0.1 写：**

| | 路径 A | 路径 B | 独立裁决器 |
|---|---|---|---|
| 旁路可否结构性封闭 | 可以 | 不可 | 可以 |

**知微 §2 末段：**

> 路径 A 增加 writer 参数，也不能单独证明参数可信；独立裁决器不调用旧 evaluator，也不能单独约束消费者。**三条路线都需要这一正式消费边界。因此 §1.5 的"A 可以 / B 不可 / 独立裁决器可以"不能作为已证比较。**

**⇒ 撤回该表。**

**⇒ 睫 NB-32 补的第三格我也接受：**

> "不依赖旧函数" ≠ "不依赖旧函数的结果"。若独立裁决器也取 `evaluate_basic_l1` 的结果作输入，它仍依赖；若完全重做判别，则有两套判别器的一致性问题。

**⇒ 改为（三条路线都同一前置）：**

```text
三条路线的共同必要条件：
  正式消费边界（表一）必须先成立。
  否则三条路线都留下同一个旁路。

三条路线的差异只在【函数层能否再收紧】：
  路径 A        ：可以收紧（改签名 ⇒ 无 writer 的调用不合法），但动 RC11
  路径 B        ：函数层不可收紧（§0.2），仅靠消费边界 + 合同命名
  独立裁决器     ：函数层可绕过（不调用旧函数），但须解决判别一致性（NB-32）
⇒ 而"A 能证明参数可信"不成立（知微）：加了 writer 参数，参数本身仍可能伪造。
⇒ 所以三者的可比性，都必须先过表一。
```

---

# 2 · 表二 · 证据时序与权限（知微 §3 要求）

## 2.1 三类对象必须分开（这是知微指出的直接冲突）

**我 v0.1 §2.3.2 要求 `record_digest` 在 outcome 前预分配并登记，同时又要求它覆盖含 AFTER 的最终内容。** 知微指出这不可能。

**⇒ 接受，改为三类对象：**

| 对象 | 何时固定 | 包含什么 | 谁能写 | 何时禁写 |
|---|---|---|---|---|
| **① 注册计划** `ExecutionPlan` | 相关干预及结果暴露**之前** | execution/episode/arm、候选与 writer 身份、payload 来源规则、目标对象与通路、观察及判定规则 | 受信登记者 | 计划确认后立即禁写 |
| **② 执行事件与观察证据** `ObservationEvent` | 对应阶段实际发生时（**只追加**） | 计划引用、受信采集来源、进程与对象绑定、各 arm 的 BEFORE/AFTER 原始数据与摘要、实际通路事件 | observer 独立采集路径 | **只追加，不可修改** |
| **③ 最终封存包** `SealedEvidence` | 所需证据收齐后、权威裁决前 | 对计划和事件集合的绑定、完整性状态、**最终包摘要** | 封存者 | 封存后不可改 |

## 2.2 命名更正（知微指出）

```text
⇒ 我在 v0.1 把"预分配的随机标识"叫 record_digest，那是错的名字。
⇒ 改为：
   record_identity  = 事前分配的随机/确定性标识（不是内容摘要）
   package_digest   = 最终封存包的内容摘要（事后才可计算）
```

## 2.3 digest 输入域三件事要分开（知微指出，我照录）

```text
① STATE digest 输入域不变：sha256(literal + q_raw)，24 字节            ← 冻结约束
② META 可以包含 STATE digest（§7.2 L347 digest output = META_FIELD）  ← 合规
③ package_digest 的 canonical 输入须【排除它自身】或放在包外           ← 防自引用
⇒ ①②③ 是三件不同的事，我 v0.1 混在一处。
```

## 2.4 先后顺序：自报整数不证明先后

**知微原文：**

> 登记顺序号可以使用，但一个自报整数或 `registered_before_event=True` 不证明先后。

**⇒ 我 v0.1 §3.2.2 用"登记顺序号"当顺序证据，不够。改为受信流程：**

```text
1. 受信登记者提交计划并取得【确认】（确认本身是独立记录）
2. 控制器收到该确认后才允许相关干预
3. observer 的事件只能追加到该计划对应的执行记录
4. 最终封存引用【原始注册承诺】+【全部必要事件】

⇒ 重试、崩溃、半成品均不得成为正式完整证据。
⇒ 若用哈希链，仍须独立可核查的链头/检查点及受信保管来源；
   可整条重写的链本身不能证明事前登记。
⇒ 保证依赖已声明的受信控制器与存储权限；
   不宣称能抵抗受信管理员蓄意改写。
```

**⇒ 知微另一句我也接受**：

> 选择序列号的理由应是建立可信事件顺序，不是"墙钟被列为 META，所以不宜使用"；序列号本身同样属于 META。

⇒ 我 v0.1 §3.2.2 说"理由是 §7.2 把 wall-clock 列为 META"，**这个理由错了。改用"需要可信事件顺序"这个理由。**

---

# 3 · 表三 · 完整判定表（知微 §5 + 睫 NB-33）

## 3.1 知微指出的三处冲突，我核后全部接受

```text
冲突 1  Step 4 对局部 FAIL/UNRESOLVED 直接返回，
        不再检查 Step 5 ⇒ 非法再注入可能被局部结果遮住
        prereg §13 L729/L735：只有 required structure 有效且已执行，
        才允许科学 FAIL/UNRESOLVED；缺失规则/witness/provenance broken ⇒ INVALID
        ⇒ 我 v0.1 的顺序错了。

冲突 2  Step 5 写"后续读取通路未登记 / 未核验 ⇒ INVALID"
        比凌翼裁定更宽（边界外无因果路径不应自动判停）
        ⇒ 我 v0.1 过宽。

冲突 3  AuthorityResult 集合只有 {ESTABLISHED, NOT_ESTABLISHED, INVALID}
        却要求"直接继承" FAIL/UNRESOLVED
        且 Step 1 缺证为 INVALID、§4.3 缺 L2 为 NOT_ESTABLISHED
        ⇒ 同一情形两种输出，调用者无法确定。
```

## 3.2 重做为三轴分离

**知微要求：区分「执行/证据有效性」「局部测量结果」「正式 class 是否建立」，并保留原始局部结果作为证据。**

| # | 情形 | 执行/证据有效性 | 局部测量结果 | 正式 class | 输出 |
|---|---|---|---|---|---|
| 1 | 已确认实际发生、与 claim 相关的**违规回流** | INVALID | — （保留原始记录） | 不建立 | `INVALID`，reason=`UNREGISTERED_EPISODE_REINJECTION` |
| 2 | 本次执行**缺失必须具备的**来源/通路核验证据 | INVALID | 保留（若有） | 不建立 | `INVALID`，reason=具体缺项名（**不写成"已观测到回流"**） |
| 3 | 必需规则 / witness / provenance broken | INVALID | 保留（若有） | 不建立 | `INVALID`（§13 L741） |
| 4 | 实际 writer ≠ 注册主体 | INVALID | 保留 | 不建立 | `INVALID`，reason=`WRITER_MISMATCH` |
| 5 | 对象在 BEGIN/END 间被替换 | INVALID | 保留 | 不建立 | `INVALID`，reason=`OBJECT_IDENTITY_CHANGED` |
| 6 | 仅**设计阶段存在未验证风险** | — | — | 不建立 | **不签发任何结论**；不得冒充实际违规，也不得冒充已执行的科学 FAIL |
| 7 | 边界外读取，经独立审查**确无相关因果路径** | 有效 | 正常 | 照常 | `NEUTRAL_REVIEWED`，保存排除依据（**睫 NB-33 第五行**） |
| 8 | 通路已登记 + 事件合规 + **有**因果路径 | 有效 | 正常 | 按规则 | 可纳入 C1 证据 |
| 9 | 全部 required structure 有效且已执行，测量为负 | 有效 | **FAIL** | 不建立 | `FAIL`（此时才允许） |
| 10 | 同上，落入不确定区 | 有效 | **UNRESOLVED** | 不建立 | `UNRESOLVED` |
| 11 | 同上，h≥2 且 payload 匹配，且 1-8 全过 | 有效 | **PASS** | **建立** | `ESTABLISHED`（须满足 §4 等价声明） |

## 3.3 睫 NB-33 第五行，我接受并加进表（第 7 行）

**睫原文：**

> 通路已登记 + 实际事件经核验合规 + 【无】因果路径 ⇒ **NEUTRAL**
> 无关 ≠ 违规。无关：既不让 C1 成立，也不让 C1 作废。违规：这次测量死了。
> 而这一格最容易被误杀，恰恰因为它全合规。

**⇒ 接受。这是我 v0.1 判定表漏的第五行。**

## 3.4 「有无因果路径」由谁判（睫第二格）

```text
✗ 自动判 ⇒ 须给可计算判据，而我没有
✗ 人判而不留痕 ⇒ 会变成事后可调的旋钮

✓ 设计：判定须由【独立审查者】作出，且
   · 判定记录必须引用具体证据（哪条通路、哪个阶段、读了什么）
   · 判定记录须封存进表二的 ③ SealedEvidence
   · 判定时刻须早于正式结果签发
⇒ T-13 CAUSAL_PATH_ADJUDICATION = NOT ESTABLISHED
```

## 3.5 排序更正（这是知微冲突 1 的解法）

```text
⇒ 有效性审查（第 1-5 行）必须【先于】任何正式结论签发。
⇒ 但局部测量本身可以先完成并保留（知微：一个已停止的无效 execution
   仍可保留先前取得的局部测量记录）。
⇒ 所以顺序是：
   局部测量（任何时候可做）
   → 有效性审查（签发前必须完成）
   → 正式裁决（若有效）
⇒ 而不是我 v0.1 写的：局部结果直接返回、跳过有效性审查。
```

---

# 4 · 表四 · P-1 最小具体绑定（知微 §6）

## 4.1 先答知微 §6.1 的 schema 问题

**知微指出我自相矛盾：§4.4 说真实摘要可能不适用 16 字节，§1.3 又把旧 `evaluate_basic_l1` 返回 C1 写成所有正式 C1 的必要条件。**

**⇒ 接受，改为：**

```text
✗ 旧：正式 C1 必须以 evaluate_basic_l1 返回 C1 为必要条件
✓ 新：权威门消费的是【经该候选注册的判别实现的结果】。
      只有在证明 schema 与语义适用时，才可具体复用旧函数。
      参考校准成功不提供真实摘要的测量资格。
```

## 4.2 P-1 的注册 payload 是哪一种（知微要求明确）

**知微：**

> 本轮注册 payload 是交互原文、预先固定的摘要，还是按前瞻规则产生的编码记录。§2.3.3 的"逐字节等于登记条目"不能同时指原文和摘要，也不能在看到写入结果后反向选一个相同 payload 来证明写入成功。

**⇒ 一个必须回答、且我不能自己答的问题**：

```text
P-1-PAYLOAD-IDENTITY = 未定，三选一：
  (a) 交互原文             ⇒ 变长，不能是 16 字节固定宽度（Q-3）
  (b) 事前固定的摘要        ⇒ 摘要何时产生？若在写入时才产生，则不是"事前"
  (c) 按前瞻规则产生的编码记录 ⇒ 规则须事前冻结；产出仍需可核
⇒ 无论哪一者，禁止在看到写入结果后反向选 payload。
⇒ 落为 T-14 P1_PAYLOAD_IDENTITY = NOT ESTABLISHED（须睫+凌翼裁定）
```

## 4.3 P-1 最小绑定表

| 项 | P-1 中的形态 | 状态 |
|---|---|---|
| **实际 writer 角色** | 待定：摘要生成器 / 编码器 / 持久写入者 是否同一进程。**不能默认等同**（知微 §4.1 指出我 v0.1 表格的混淆） | NOT ESTABLISHED（铰 T-1 / T-4） |
| **业务 STATE schema** | 若摘要变长 ⇒ 非 16+8；须独立登记 `STATE_FIELDS` / `LITERAL_STORAGE_COMPONENTS` / `IDENTITY_ONLY_COMPONENTS` | NOT ESTABLISHED（T-2） |
| **payload 来源规则** | 见 4.2，三选一 | NOT ESTABLISHED（T-14） |
| **真实判别接口** | 经该候选注册的判别实现；不复用旧函数的阈值 | NOT ESTABLISHED |
| **context 读取证据职责** | 见 4.4 | NOT ESTABLISHED（T-15） |

## 4.4 Q-2 的地位：睫把它抬高了，我接受

**我 v0.1 写：Q-2「属于科学资格的一部分」。**

**睫裁：属于 claim 的【定义性前提】。**

> 若无人读取 ⇒ 写入与不写入，在系统后续任何可观测行为上**不可区分**。
> 而一个不可区分的差异，不构成一个科学事实。
> 202 句说的是：不可能失败的动作，不是验证。
> 而这一句是它的孪生：**不可能产生后果的差异，不是事实。**
> 资格的一部分 ⇒ 可以在后面补
> 定义性前提   ⇒ 必须在 outcome 前回答

**⇒ 接受。并且睫要求的证明方式我也照录：**

```text
证明"这条通路真实存在"的方式：
  ✓ 必须是【一次观测】（一次真实的 context 组装记录）
  ✗ 不是设计论证
理由：设计论证可以证明"它应该被读"，只有观测能证明"它被读了"。
⇒ T-15 FOLLOWUP_READ_PATH_EXISTENCE_OBSERVED = NOT ESTABLISHED
```

## 4.5 知微 §6.2 的补充：path_id 不能代替实际读取证据

**知微：**

> 错误读取也可以带着正确标签；这些标签本身不证明读了什么、从何处来、送给了哪一臂。

**⇒ 接受。落为：实际事件必须绑定受信采集来源，不能只信 writer/reader 自报 `path_id`。**

**⇒ 知微提的有限候选我照录**：受控 context 组装入口，读取注册存储后独立记录源对象及其版本/来源 episode、实际读取与传入的数据绑定、读取主体、接收系统/arm、阶段与转化规则。

**⇒ 并附知微的一句限格**：

> 不能自动把业务收益、所有后续使用或更高层记忆效果加成 C1 的通用门槛。此处最终科学边界请睫判定。

---

# 5 · 睫 NB-31 · 合同层命名（我不裁，转呈凌翼）

**睫的判：**

> 旁路封闭只有两条路：① 技术封闭（路径 A / 完全独立裁决器）② 契约封闭（路径 B 唯一剩下的可能）
> 而 ② 的做法不是"封住调用"，是【改名】：
> 在合同层声明：`evaluate_basic_l1` 返回的 `change_class`，在科学输出语境下**不叫 C1**，改叫 `L1_local`。
> 而 C1 这个术语，在科学输出中只由 AuthorityGate 产生。
> ⇒ 这一格不需要改 `evaluator.py` 任何一个字节。
> ⇒ 而改名要动 prereg 里 C1 这个词的定义域 ⇒ **需 prereg 授权。**

**⇒ 我核了这与凌翼 D2 的关系，因为睫自己也指出这一格最危险：**

```text
D2_RENAME_AS_REPAIR = REJECTED（凌翼）
⇒ 禁的是【给冻结件改名以修复它】——替换一个已有的名字
⇒ 睫提的是【在合同层新增一个名字 L1_local】——不替换冻结件里的 C1
⇒ 两者形状极像，区别在于：替换 vs 新增
⇒ 但即便只是新增，也要动 prereg 中 C1 的定义域 ⇒ 须 prereg 授权
```

**⇒ 我不裁，转呈：**

```text
NB-31 呈请凌翼裁定：
  · 是否允许在【非冻结】文档中声明 L1_local / C1 的术语分工
  · 是否需要 prereg 层面授权（我的判断：需要，因为 C1 的定义域在 prereg）
  · 是否触及 D2 禁令（我的判断：不触及，因为是新增不是替换 —— 但请你确认）
```

---

# 6 · 睫 NB-30 · 旁路结论的准确表述

**我在 §0.2 已改成：**

```text
BF8_PATH_B_CLOSURE_WITHOUT_TOUCHING_EVALUATOR = STRUCTURALLY_IMPOSSIBLE
理由：公开可 import 函数，未来消费者集合不可枚举。
```

**⇒ 但按知微 §2 的纠正，我必须加上限定，否则这句话会被读成"路径 B 死了"：**

```text
完整表述：
  函数层旁路（谁能调用 evaluate_basic_l1）
    = 在不动 evaluator.py 的前提下，结构性不可封闭（睫 NB-30）
  正式 C1 旁路（谁能签发正式 C1）
    = 可以封闭，封点在【正式消费边界 + 合同层命名】（知微 §2 / 睫 NB-31）
⇒ 所以路径 B 的生命力不在函数层，在消费边界层。
⇒ 而这正是我 v0.1 漏掉的一半。
```

---

# 7 · 睫 NB-34 / 214 句 · 那两个 "= NO" 要带日期

**睫：**

> 按 214 句补半句：这两个 NO 请带上【由谁、何时】回来确认。否则它会变成一块诚实的墓碑——而墓碑上没有日期。

**⇒ 照录：**

```text
REGISTERED_PATH_AUTO_C1     = NO   （凌翼 2026-10-26 裁定，§4）
UNREGISTERED_READ_AUTO_STOP = NO   （凌翼 2026-10-26 裁定，§4）
⇒ 二者为冻结裁定的引述，非我的判断。
⇒ 若将来需变更，须由凌翼重新裁定，不由本文修订。
```

---

# 8 · 知微 §7 · 一处事实更正（我接受）

**我 v0.1 §2.2 写：**

> `afterglow_harness/*.py` grep `episode_id|execution_id|META|provenance` ⇒ 仅命中注释与 Q3 的 provenance 模块，**无 C1 META**

**知微指出过强。我核后接受：**

```text
fixtures.py L55-62  Ledger 承载 fixture_id / attempted_scope / observations /
                    gates / l2 / notes                            [读文件]
run_known_answer_suite.py L156-183  suite raw result + run manifest，
                    含 phase / scientific_claim_eligibility        [读文件]
⇒ 这些是 META 性质的载体。
⇒ 它们不等于真实候选已具备完整 COND_6，但不能写成"全无 META 载体"。
```

**⇒ 改为（照知微建议措辞）：**

> **尚未建立真实候选所需的独立 episode / execution 来源绑定链。**

---

# 9 · 状态

```text
BF8_STATUS                          = OPEN
  ├ BF8_PATH_B_BYPASS_FREE          = NOT PROVEN
  ├ 函数层封闭（不动 evaluator.py）   = STRUCTURALLY_IMPOSSIBLE（睫 NB-30）
  ├ 正式 C1 消费边界                 = NOT DESIGNED（本文件 §1 给出表一草案）
  └ BF8_CODE_IMPLEMENTATION          = NOT AUTHORIZED

BF9_SOURCE_BINDING_GAP              = ACCEPTED
BF9_SECTION_7_2_CONFLICT            = REJECTED（凌翼；我原判断错）
STATE_DIGEST_DOMAIN                 = UNCHANGED

COND_6_EPISODE_SPECIFIC_BINDING     = NOT ESTABLISHED
  └ 准确表述：尚未建立真实候选所需的独立 episode/execution 来源绑定链
    （META 载体在 reference 中存在：Ledger / suite manifest）

FOLLOWUP_READ_REGISTRATION          = TWO_LEVEL_BINDING_REQUIRED
REGISTERED_PATH_AUTO_C1             = NO（凌翼 2026-10-26）
UNREGISTERED_READ_AUTO_STOP         = NO（凌翼 2026-10-26）

T_1_W_SHAPE                         = PENDING_QIANXING（钳星：短进程不天然无残留）
T_2_SUBSTRATE_SCHEMA                = NOT ESTABLISHED
T_4_WRITER_SINGULARITY              = PENDING_QIANXING
T_5_META_RECORD_STORE               = NOT ESTABLISHED
T_9_NEGATIVE_CASE_DETECTION         = NOT ESTABLISHED
T_10_STATISTICAL_UNIT_RULE          = PREREGISTRATION_REQUIRED
T_12_AUTHORITY_CONSUMER_PERMISSION  = NOT ESTABLISHED  [新]
T_13_CAUSAL_PATH_ADJUDICATION       = NOT ESTABLISHED  [新]
T_14_P1_PAYLOAD_IDENTITY            = NOT ESTABLISHED  [新]
T_15_FOLLOWUP_READ_PATH_EXISTENCE_OBSERVED = NOT ESTABLISHED  [新]

C1AuthorityGate = ESTABLISHED ⟺ prereg §28.1 C1 class rule 满足
  = 本文提出，【须凌翼裁】（睫 Q-1）
NB_31_L1_LOCAL_NAMING             = 呈请凌翼裁

C1_MEASUREMENT_CHAIN_QUALIFIED      = NOT ESTABLISHED
C1_SCIENTIFIC_RESULT                = NOT ASSESSED
C1_END_TO_END_FEASIBILITY           = PENDING_DESIGN_VALIDATION
FROZEN_Q3_RC11                      = UNCHANGED
CODE_CHANGE                         = NOT AUTHORIZED
SCIENTIFIC_EXECUTION                = MAY NOT START
```

---

# 10 · 本轮未做

- 未写代码、未运行任何模块
- 未改 `evaluator.py` / `fixtures.py` / MANIFEST / prereg（`78bdb90f…` / `ad0855b0…` / `fa644a9b…` 均未变）
- 未宣称 BF-8 关闭，也未宣称路径 B 不可行
- 未代钳星定 T-1 / T-4
- 未代凌翼裁 NB-31 / 等价声明
- 未把"设计论证"当作"通路存在"的证明

---

# 11 · 这一轮我错了什么

**两处，方向相反：**

```text
E-7  把"存在返回 C1 的路径"写成"11 处全部返回 C1"
     ⇒ 忽视了 fixtures.py L51 SCIENTIFIC_CLAIM_ELIGIBILITY = "NONE"
     ⇒ 也忽视了函数的 INVALID/FAIL/UNRESOLVED 分支

E-8  把"我现在证明不了"写成最终结论
     ⇒ 而睫用一个我漏数的东西（4 行 import）把它推成了"结构性不可能"
     ⇒ 我数了 11 个调用，没数 4 个 import
     ⇒ 因为我只数了"它被用在哪"，没数"它可以被谁用"
```

**⇒ 而 E-8 的教训，和 E-7 是同一个形状：**

**我数的是"我看得见的那一层"，而结论落在"我看不见的那一层"。**

**⇒ 所以我这一版写的东西里，最不该被信任的，是我说"表一已经设计出来了"这一句。**
**⇒ 表一只是草案。而它本身也需要被审。**
**⇒ 我不写"结构设计已完整"。**
**⇒ 我写：四张表在这里，请逐张核——特别是表一，因为它是我第一次设计"边界"，而不是"发现缺口"。**
