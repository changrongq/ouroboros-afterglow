# C1 EXECUTION DESIGN MAPPING v0.3 · 收窄 BF-8 / 改 RE-F / 补具体候选

**性质**：对 `1adfcae`(v0.1) + `02e2231`(v0.2) 的**就地勘误与实质性补齐**。
不构成实现或科学执行授权；不新增冻结字段。
**审阅输入**：睫 `NB-19 / NB-20 / NB-21`（并自认 NB-16 只纠到一半）；钳星 `§7 两格认领 + 倾向候选甲`；知微 `P1 / P1-b / P2 / P3（原 P2）/ P4 / P5`。
**基线（本文件自述）**：`02e2231afb4bd8a126921b203e619ebe566801b6`
**v0.2 被审对象 SHA-256**：`546223641231479daf3485cc98628d1d67666b57bc495a816d0709c01617a59d`（知微回执值，本地核验一致）

```text
REAL_CANDIDATE_IDENTITY          = PROPOSED_PENDING_REVIEW  ← 本文件唯一的状态升级
CODE_CHANGE                      = NOT AUTHORIZED
IMPLEMENTATION_AUTHORIZATION     = NONE
SCIENTIFIC_EXECUTION             = MAY NOT START
FROZEN_Q3_RC11                   = UNCHANGED
```

---

# 0 · 我这一轮又错的（E-4），以及我主动撤回的一段

## 0.1 E-4 · `write_operator` 三字段在 §4，不在 §5

**我写的**（v0.2 §1.1 第③层、§1.2）：

> `prereg` 全文 `writer` 相关命中在 L169/L170/L171（**§5 身份字段表**）

**字节说**：

```text
prereg L157  "# 4. Implementation-Neutral Does Not Mean Implementation-Blank"   [读文件]
prereg L159  "任何实际 execution 启动前，必须生成并冻结："
prereg L161-171  IMPLEMENTATION_BINDING_MANIFEST / ... / write_operator_identity / _version / _hash
```

**⇒ 是 §4。**

**这就是睫的 NB-19 和我自己的第 209 句补充合起来要防的那类错**：

```text
行号对了（L169-171）
路径对了（prereg/）
而"它在谁的体内"错了（§5 vs §4）
```

**⇒ 睫 NB-19 的表述我原样接受**：凡引用一行字节，须给出**路径 + sha + 行号 + 所属函数/章节**四件。

## 0.2 我主动撤回：`sample=01/02` 同时承担 nuisance 排除（v0.2 §2.1）

**我写的**（v0.2 §2.1）：

> 而这两个字符同时承担了 ① nuisance 排除（BF-6 第六条）② episode 区分。

**知微指出这句不成立，我核字节后接受**：

```text
harness_constants.py L159  IDENTITY_ONLY_COMPONENTS = frozenset()   （EMPTY_SET）
harness_constants.py L160  LITERAL_STORAGE_COMPONENTS = { literal.bin[0:16] }
harness_constants.py L165-167  NONSTATE_STORAGE_PIPELINE_NUISANCE_EXCLUSIONS
      = { filename, path, length, mtime, allocation_metadata, logs, container_hash }
```

**⇒ 整个 16 字节 literal 都属于 `LITERAL_STORAGE_COMPONENTS`；nuisance 名单是文件名/路径/mtime 等非 STATE 项。**
**⇒ `sample` 不在 nuisance 名单里，也没有被任何 mask 遮掉。**
**⇒ 我不能仅凭变量名叫 `sample`，就把它划进身份/干扰遮罩。**

**这是我在 v0.2 里新造的一处错误——不是继承 v0.1 的，是我这一轮"为了说明 BF-9 更严重"而推出来的一句。** 撤回。

**BF-9 的核心仍然成立**（见 §2），只是理由要换。

---

# 1 · BF-8 收窄（知微 P1，我接受收窄，不接受清空）

## 1.1 知微指出的三点，逐条核验

### 第 1 点：grep 不到 `write_operator` ≠ 没有 writer 绑定资产 —— **成立**

```text
MANIFEST L148  "# 五 · Write operators"                                    [读文件]
MANIFEST L151  StorageWriter = STORE_FULL / STORE_NULL / STORE_ONE_BYTE
MANIFEST L152-158  ExtraWriter = SYNTHETIC_W_EXTRA_OPERATOR ...
MANIFEST L166  STORAGE_WRITER_COMPONENT_HASH = ae64731b...                 
MANIFEST L167  EXTRA_WRITER_COMPONENT_HASH   = ae64731b...
MANIFEST L168  STORAGE_LAYER_COMPONENT_HASH  = 8271f42c...

qualification_role_registry.py L22-32  EXECUTION_CRITICAL_ROLES 含 "writers.py"   [读文件]

writers.py 实际文件 SHA-256 = 08f7d968bdb4aa37c206e169cabbb08b9616b0990c0e758e7958c93c6b5b690c   [终端核验]
MANIFEST L423  writers.py 1.0 08f7d968bdb4aa37c206e169cabbb08b9616b0990c0e758e7958c93c6b5b690c  [读文件]
```

**⇒ `writers.py` 是执行关键角色，且其**文件 SHA-256 与 MANIFEST L423 登记值逐位相同**（我用 `Get-FileHash` 独立算的，不是抄的）。**

**⇒ 所以 v0.2 §1.1 "四层皆空"的第一层说错了。既有 writer 实现、既有角色登记、既有文件绑定路径，且当前文件与登记一致。**

**这是我在 BF-8 上讲过头的地方，我改正。**

### 第 2 点：§37 没有 `WRITER_*` 标签 ≠ 规范完全不覆盖 writer —— **成立**

```text
prereg §37 L2257  PROVENANCE_BREAK
prereg §37 L2258  EXECUTION_IDENTITY_MISMATCH
prereg §13 L702   条件 1："本次 execution 与该 claim scope 所需 manifests / frozen rules 均有效"
prereg §13 L711   条件 5："required provenance 完整，且没有命中 … §37 invalidity / stop condition"
prereg §31 L1948-1949  execution_id / execution_hash 属必须记录的 provenance
prereg §4  L169-171    write_operator_identity / _version / _hash 属启动前必须冻结的绑定字段
```

**⇒ `EXECUTION_IDENTITY_MISMATCH` 和 `write_operator_identity` 合起来，在规范层已经构成"应当核对 writer/execution 身份"的**一般性**要求。**
**⇒ 我 v0.2 说"§37 内零 writer 条款"字面为真，但它被读成了"规范没要求核对 writer"，这一步是错的。**

**⇒ 正确表述**：

```text
§37 无 WRITER_* 专名条款          = TRUE（字面）
规范层已冻结 writer 身份三字段     = TRUE（§4 L169-171）
规范层已有一船性身份失效条款       = TRUE（PROVENANCE_BREAK / EXECUTION_IDENTITY_MISMATCH）
"这三条如何具体适用到 C1 writer"   = NOT MAPPED  ← 缺口在这里
```

### 第 3 点：判别器无认证参数 ≠ 全系统无法认证 —— **成立**

**⇒ 接受**。上游控制器 / 身份验证 / 证据准入可以承担该职责，前提是实际设计、实现并提供可复核证据。

**⇒ 我不能反过来强迫每个数值判别器都自带进程认证。**

## 1.2 BF-8 收窄后的正式表述（采纳知微建议措辞）

> **在输入宽度有效、`q_A == q_B`、`h >= 2` 的实际前提满足时，`evaluate_basic_l1` 不能仅从相同状态字节辨认实际写入进程是谁；真实候选所需的 writer—execution—observation 关联尚未建立。参考 writer 资产（`writers.py`，SHA-256 `08f7d968…`，MANIFEST L423 一致）及文件绑定路径存在，但不填补这一缺口。**

**同时补上知微要求的前提条件**（v0.2 我写"写了正确内容必然 PASS"，过强）：

```text
PASS 的实际前提：
  · snap_A.q == snap_B.q                （否则 L230-235 ARM_CONFIG_INVALID）
  · h = _literal_byte_diff_count(...) >= 2   （h==0 FAIL；h==1 UNRESOLVED）
  · snap_B.literal == registered_payload     （否则 L254 PASS + NOT_ESTABLISHED）
  以上全满足 → L262-266 change_class = C1
```

**⇒ BF-8 保留为**：

```text
BF_8 = PARTIALLY_ACCEPTED
  ├ "判别器不看 writer"                      = TRUE（字节确认）
  ├ "write_window 非 OS 访问控制"             = TRUE（字节确认）
  ├ "writer 资产不存在 / 四层皆空"            = FALSE ← 我 v0.2 说过头，撤回
  └ "writer—execution—observation 关联未建立" = TRUE ← 这才是真缺口
```

## 1.3 睫的 NB-20 我采纳，但改一处

**睫写**：

> `write_window` 的调用者必须携带 `write_operator` 身份，且该身份须与 prereg §5 的注册值比对；比对结果进入 `L1Result`，而不是只进日志。

**我采纳"要写明它要求改签名"这一点（NB-20），但对具体方案我要标为**未定**：

```text
NB-20 采纳为：RE-E 须写明"它要求改变 evaluate_basic_l1 的入参结构（或其上游的绑定方式），不是补一个检查"
理由：三个参数 (snap_A, snap_B, registered_payload) 里没有位置装 writer 身份；
      若要进 L1Result，则要么改签名，要么在调用链上增加一层前置校验并使其结果不可绕过。
      两条路都是代码改动。

而具体方案（改签名 / 上游绑定）不在此定 —— 那是实现决策，CODE_CHANGE = NOT AUTHORIZED。
另：睫写"prereg §5"，实为 §4（见 §0.1），我按 §4 记录。
```

---

# 2 · BF-9 保留，但换掉我那句理由

## 2.1 成立的字节依据

```text
harness_constants.py L85-93   canonical_state_digest(literal, q_raw)
      → sha256(canonical_state_bytes(literal, q_raw)) = sha256(literal + q_raw)
      ⇒ 输入域 24 字节，无 episode                              [读函数]

harness_constants.py L192-197 EPISODE_PAYLOADS: A1/A2 都是 16 字节，
      sample=01 / sample=02 是其中两个字符                       [读文件]

evaluator.py L262-266   payload 精确匹配 ⇒ change_class = C1     [读函数]
```

**⇒ episode 与 payload 在 reference 里是同一个字节串，因此二者之间的关联不是被证明的，是被假定的。** 这一句仍成立。

## 2.2 撤回的部分

**「payload 同时承担 nuisance 排除」——撤回**（见 §0.2）。
**⇒ 所以 BF-9 只剩一半：**

```text
BF_9 = PARTIALLY_ACCEPTED
  ├ "episode 唯一载体是 payload 内两个字符"        = TRUE
  ├ "digest 输入域不含 episode"                    = TRUE（但这是合规设计，不是缺陷）
  ├ "payload 连续承担 nuisance 排除"               = FALSE ← 撤回
  └ "重放同一 payload 不可在 C1 层检出"             = TRUE（见 §3）
```

## 2.3 知微对"C1 比 C3 更严重"的反驳 —— **我接受**

**我 v0.2 写**：

> C3 层明文写了这件事，只是推给 fixture；C1 层连这句话都没有。**即：C1 这条链上，重放不仅不可检出，而且没有留下"我知道这件事该由别人管"的字据。**

**知微的判**：§20.1 L1181 关于 replay 的限制有**明确 C3 泛化语境**，不能因为 C1 函数未重复其注释，就判定 C1 比 C3"更严重地漏了同一门禁"。

**字节核验**：

```text
prereg L1164  "## 20.1 Same-class reproducibility"        ← 在 §20（C3 相关）里
prereg L1181  "同一 episode replay 只能作为 repeatability control，
               不能替代 class-level generalization。"
```

**⇒ 这句限制的适用对象是**class-level generalization（C3）**，不是 C1 的 episode 成立性。**
**⇒ 我说"C1 比 C3 更严重"是把 C3 的门禁施加到 C1 上了。撤回这句。**

**⇒ 正确表述**：

```text
C3 = 有明文 replay 限制（§20.1 L1181），作用域是 class-level generalization
C1 = 无明文 replay 限制条款；§13 C1 class rule（L722-724）要求的是
     "episode-specific registered storage write"，未包含"历史首次执行"
⇒ 两者不是"严重程度"差别，是"规则是否被写下"的差别。
```

---

# 3 · RE-F 改名并收窄（知微 P2，我接受）

## 3.1 我原来的写法与问题

**v0.2 写**：

```text
RE_F_EPISODE_FIRST_EXECUTION = episode 首次执行证据，且该证据【不得来自 payload 内容】
```

**知微的判**：

> prereg §13 的 C1 要求是 episode-specific registered storage write，**没有在该规则中自动要求 episode 的历史首次执行**。若确实要限制为"某 episode 历史上第一次执行"，需要提出科学理由、判定范围、实施依据及与冻结协议的关系，由相应审查/裁定处理；**不能以本轮勘误直接将其变成 C1 的通用前提。**

**⇒ 我认同。我原来的名字把一件"我要的小心"写成了"C1 的前置条件"，这是越界。**

## 3.2 改为

```text
RE_F_CURRENT_EXECUTION_EVIDENCE_BINDING
  = 本次 execution 身份与证据来源的绑定（不是新增冻结字段，是设计要求）
  NOT ESTABLISHED
```

**⇒ 它要回答的是"这份 before/after 是不是本次采集的"，不是"这是不是历史上第一次"。**

## 3.3 三类情况分开（照知微表，我补判定方式）

| 情况 | 设计需要回答 | 判定 |
|---|---|---|
| 把上一轮快照复制为本轮 after | 必须通过运行/对象/采集来源绑定拒绝 | **INVALID**（证据不是本次的） |
| 事前注册的相同内容重复执行，用本轮合法 before/after + 匹配对照 + 来源记录 | 不能仅因内容重复就判无效 | **按完整 gate + class rule 判**，不预设结论 |
| 同一 episode 重复执行当作 C3 的不同 episode 泛化证据 | §20.1 L1181 明禁 | **C3 NOT ESTABLISHED**；可作为 repeatability control |

**⇒ 并把"是否要把历史首次执行列为 C1 新前提"挂起**：

```text
C1_FIRST_EXECUTION_AS_REQUIREMENT = NOT ESTABLISHED（需睫/凌翼共同裁定，不由本轮勘误生成）
```

---

# 4 · 具体待审候选（知微 P3 / 钳星倾向；本文件唯一的状态升级）

知微写：「**提出待审候选仍已获设计授权。** 可由 Coder 汇总各方意见，提出一个有明确待定项的方案；不要求现在批准、不要求伪造实现 hash，也不要求代钳星完成其结论。」

**⇒ 我按此提出一个候选，并把所有未知项显式留空。**

## 4.1 候选 C1-CAND-α（短生命周期，钳星倾向）

```text
CANDIDATE_ID            = C1-CAND-α
形态                    = 短生命周期单 writer 进程（钳星倾向：候选甲）
状态                       = PROPOSED_PENDING_REVIEW（未批准、未实现、未执行）

【被测对象 W】
  · 一个独立可执行体，单次运行完成一次 episode 的 registered write 后退出
  · 输入：episode payload（16 字节）+ 本次 execution 身份（来自注册记录，不来自 payload）
  · 输出（STDOUT / 退出码）：写入结果 + 自身 execution 身份回执
  · 生命周期：进程创建 → 打开写窗口 → 写入 → 关闭写窗口 → 退出
  · 退出后不再持有任何该对象的句柄

【注册 substrate（沿用）】
  · literal.bin[16] + substrate.bin[8]（沿用 reference 规格，作为可审起点）
  · 如需新 schema，属待定项 T-2

【观察者】
  · 独立进程，writer 退出后运行
  · 只读打开（FILE_SHARE 只允许 READ），对象身份 = volume serial + file index
  · 观察者身份/权限证据 = 待定项 T-3

【episode 载体（修补 COND_6）】
  · META 侧独立记录：episode_id / execution_id / writer_identity / 对象身份 / before-after digest
  · STATE 侧输入域【不变】（不改 24 字节规格，不违反 §7.2 L326-350）
  · 关联方式：META 记录中存 before/after state digest，与 STATE 侧独立计算值比对
    ⇒ 这是"可验证关联"，不是"把身份塞进 STATE"

【事前注册（outcome 前必须完成）】
  · 臂分配（A=NO_WRITE，B=目标写）
  · episode_id 与 payload 的对应表
  · writer_identity / version / hash（§4 L169-171 三字段）
  · 观察窗口的进入/退出条件
```

## 4.2 明确的待定项（我不填，留给对应审查者）

| 编号 | 待定项 | 谁定 | 当前 |
|---|---|---|---|
| **T-1** | W 的最终形态（α 短进程 / β 持久进程） | **钳星**（`W_SHAPE_DECIDER`） | 钳星倾向 α，**决定未出** |
| **T-2** | substrate schema 是否沿用 16+8 | 科学范围 | 未定 |
| **T-3** | 观察者 token / DACL / 对象身份证据 | 知微（Windows 路径） | 未定 |
| **T-4** | writer 单一性如何强制（唯一进程？对象句柄共享模式？） | **钳星**（`WRITER_SINGULARITY_DECIDER`） | **决定未出** |
| **T-5** | META 记录格式与存放位置 | COND_6 设计 | 未定 |
| **T-6** | episode 是否须历史首次执行 | **睫 + 凌翼** | NOT ESTABLISHED |
| **T-7** | 持久进程（β）的"可验证静止"判据 | 钳星 + 知微 | 待 α 落地后另设计 |
| **T-8** | 该候选是否属"真实业务候选" | **凌翼** | 我按设计授权提出，不自行认定 |

## 4.3 这个候选我不做什么

```text
不伪造 writer_identity / hash —— 真实值须由未来授权后采集
不代钳星定 T-1 / T-4
不代知微定 T-3
不宣称 C1-CAND-α 已满足任何 gate
REAL_CANDIDATE_IDENTITY = PROPOSED_PENDING_REVIEW（不是 ESTABLISHED）
```

---

# 5 · 短进程保证范围的收紧（知微 P4，我接受）

## 5.1 我 v0.2 写的

> 短进程候选**优点：无跨 episode 残留**、退出后状态稳定可读

**知微的判**：进程退出有助于消除该进程的运行时状态，但文件、外部控制器、子进程或服务中的状态需要分别按注册生命周期处理。Windows 父进程退出不自动终止子进程，其他进程持有的对象也可能继续存在。

**⇒ 接受，改为（照知微建议措辞）**：

> **短进程候选便于界定写入阶段与进程内状态寿命；对象稳定性、其他写入者及跨 episode 状态的清除/保留仍需独立设计与证据。**

## 5.2 我另加一句（因为钳星正是用"天然回避"这四个字支持 α 的）

```text
⇒ "短进程天然回避 N4 跨 episode 残留和 N-ε 遗留写进程"这句话，
   只在"没有其他进程持有对象、没有子进程存活、文件本身不跨 episode 复用"三者都成立时才对。
⇒ 这三者都需要独立证据，不是短进程这一属性自动带来的。
⇒ 我不把这个结论写成"α 的优点"，只写成"α 使这三件事更容易被界定"。
```

**这一句是对钳星倾向的限定，不是反驳他的认领——T-1 仍归他定。**

## 5.3 §5 的"须检出/须拒绝"仍只是要求

**知微指出**：当前 §5 的"须检出/须拒绝"是要求，尚不是具体检出机制。

**⇒ 接受。我在 C1-CAND-α 里只补了"用什么看"（§4.1 观察者段），没有补"怎么拒绝"。**
**⇒ 判定机制列为新待定项**：

```text
T-9  负向反例的具体检出机制（N-α..N-ζ 各自的实现判据）  = 未定
```

---

# 6 · §37 与 `CONTENT_CLASS_MANIFEST`（知微 P5，我接受拆分）

## 6.1 我 v0.2 写的

> `CONTENT_CLASS_MANIFEST_MISSING` — **直接** —— `EPISODE_PAYLOADS` 的 `cls=L/R` 就是它

**知微的判**：内容标签、类别登记对象、规则/hash 绑定、当前 C1 的实际依赖**不是同一个东西**。

**⇒ 接受，拆成四件**：

```text
① 内容标签        = payload 内的 cls=L/R 两字符（harness_constants.py L193-196）
② 类别登记对象    = 一个“哪些 episode 属哪个 class”的注册表 —— reference 未以 manifest 形式登记
③ 规则/hash 绑定  = CONTENT_CLASS_MANIFEST_HASH 在 §31 L1931 属必须记录的 provenance
④ C1 的实际依赖   = C1 class rule（L722-724）只说 LITERAL_STORAGE_COMPONENTS，
                    未要求 content class 作为 C1 判据
```

**⇒ 结论**：

```text
① 存在（标签）
② NOT ESTABLISHED（无 manifest 形式的类别登记）
③ NOT ESTABLISHED（无 CONTENT_CLASS_MANIFEST_HASH 的实际值）
④ C1 不直接依赖（属 C3 的内容类别证据责任）
```

**⇒ 并照知微要求写清**：本回执**不豁免 §4 的现行实施绑定，也不自动把 C3 科学判据施加给 C1**。

## 6.2 睫 NB-21 的 RE-G 关闭判据（我采纳）

```text
RE_G 关闭须两件齐备：
  ① §37 的 39 条（L2207-2262）逐条 disposition 完毕
  ② 声明"其他章节无同类条款"，并给出该声明的 grep 取法及结果
只有 ① 没有 ② ⇒ 仍是"抄全了 §37"，会被读成"抄全了全部"。
⇒ 落为：
  RE_G_SECTION37_FULL_APPLICABILITY = STILL_PENDING（两件均未齐）
  RE_G_PART_1_39_ITEMS              = NOT DONE
  RE_G_PART_2_NO_OTHER_SECTION_CLAIM= NOT DONE
```

---

# 7 · v0.3 状态表（替换 v0.2 §8）

```text
REAL_CANDIDATE_IDENTITY          = PROPOSED_PENDING_REVIEW  ← 见 §4（C1-CAND-α）

COND_1_C1_SCOPE_LIST             = NOT ESTABLISHED
  └ reference 有通用资格绑定校验（qualification_binding.verify 9 项）；C1 专属 scope 清单无

COND_2_OBSERVER                  = NOT ESTABLISHED
  ├ O-1 权限                      = NOT ESTABLISHED（T-3）
  ├ O-2 注册观测                  = NOT ESTABLISHED
  ├ O-3 跨文件一致性              = 机制缺失（≠ 故障已发生）
  └ observer 登记                 = EXISTS（observer.py L23-24 常量 + MANIFEST L264-266 三字段）
     └ 真实运行身份/权限          = NOT ESTABLISHED
     └ hash 语义对照              = NOT PERFORMED（f8b68319… 登记值 vs 82d244cd… 文件摘要，不合并）

COND_3_TWO_ARMS                  = NOT ESTABLISHED
  ├ W-1 参考已有（夹具级目录隔离）≠ 进程/身份隔离
  ├ W-2 事前分配/匹配             = NOT ESTABLISHED
  ├ W-3 episode/环境匹配          = NOT ESTABLISHED
  ├ W 形态                        = 钳星倾向 α（短进程）；T-1 决定未出
  └ writer 单一性                 = T-4 决定未出

COND_4_REAL_C1_BINDING           = NOT VERIFIED
  └ BF-8（收窄）：判别器不看 writer = TRUE
                   writer 资产不存在 = FALSE（writers.py 08f7d968… 与 MANIFEST L423 一致）
                   writer—execution—observation 关联未建立 = TRUE

COND_5_STOP_CONDITION_MAPPING    = STILL_PENDING
  └ 已从 §37 抄入 8 项；§37 字节上 39 条；"至少包括"⇒ 39 非完整条数
  └ §37 有 PROVENANCE_BREAK / EXECUTION_IDENTITY_MISMATCH 一般条款；
    其对 writer 的具体适用未映射（不是"零覆盖"）

COND_6_EPISODE_SPECIFIC_BINDING  = NOT ESTABLISHED
  ├ 夹具级关联                    = EXISTS（fixture_contracts / fixtures / recompute_from_ledger）
  ├ 真实 episode 事前注册         = NOT ESTABLISHED
  └ BF-9（收窄）：episode 唯一载体是 payload 两字符 = TRUE
                   重放在 C1 层不可检出 = TRUE
                   payload 兼作 nuisance 排除 = FALSE（撤回）
                   "C1 比 C3 更严重" = 撤回（§20.1 L1181 作用域是 C3 泛化）

RE_D_REAL_COMPONENT_REGISTRATION = NOT ESTABLISHED

RE_E_WRITER_BINDING              = NOT ESTABLISHED
  └ 须写明：这要求改变 evaluate_basic_l1 入参结构或在上游增设不可绕过的绑定层，
             不是"补一个检查"（睫 NB-20，我采纳）
RE_F_CURRENT_EXECUTION_EVIDENCE_BINDING = NOT ESTABLISHED  ← 由 RE_F_EPISODE_FIRST_EXECUTION 改名收窄
  └ C1_FIRST_EXECUTION_AS_REQUIREMENT = NOT ESTABLISHED（T-6，须睫+凌翼裁定）
RE_G_SECTION37_FULL_APPLICABILITY= STILL_PENDING（两件均未齐，睫 NB-21）

C1_MEASUREMENT_CHAIN_QUALIFIED   = NOT ESTABLISHED
C1_SCIENTIFIC_RESULT             = NOT ASSESSED
C1_END_TO_END_FEASIBILITY        = PENDING_DESIGN_VALIDATION

S_1 / S_2 = NOT SATISFIED ； S_3 = SATISFIED
NEW_B = DESIGN_PARKED ； RE-3 = NOT ESTABLISHED
CODE_CHANGE / IMPLEMENTATION_AUTHORIZATION = NONE / NOT AUTHORIZED
SCIENTIFIC_EXECUTION = MAY NOT START
FROZEN_Q3_RC11 = UNCHANGED
```

---

# 8 · 本轮我撤回或改写的清单（方便下一轮不再重复要）

| 编号 | v0.2 原文 | v0.3 |
|---|---|---|
| E-4 | `write_operator` 在 §5 | **§4**（L157 起） |
| R-1 | `sample=01/02` 兼承担 nuisance 排除 | **撤回**（nuisance 名单是文件/路径/mtime 等） |
| R-2 | BF-8「四层皆空」 | **收窄**：writer 资产存在且文件 hash 与 MANIFEST 一致 |
| R-3 | 「写了正确内容必然 PASS」 | **加前提**：q_A==q_B、h>=2、payload 精确匹配 |
| R-4 | 「C1 比 C3 更严重地漏了同一门禁」 | **撤回**（§20.1 L1181 是 C3 泛化语境） |
| R-5 | `RE_F_EPISODE_FIRST_EXECUTION` | **改名** `RE_F_CURRENT_EXECUTION_EVIDENCE_BINDING`；首次执行挂 T-6 |
| R-6 | 短进程「无跨 episode 残留」 | **收窄**：只便于界定，不自动保证 |
| R-7 | `cls=L/R` 就是 `CONTENT_CLASS_MANIFEST` | **拆四件**：标签有，manifest 无，hash 无，C1 不直接依赖 |

---

# 9 · 本轮我没有做的事

- **未**写代码、**未**运行实验、**未**改冻结件
- **未**把任何 reference 组件标为 SATISFIED
- **未**伪造 writer identity / hash / 时间戳
- **未**代钳星定 T-1 / T-4，**未**代知微定 T-3，**未**代睫+凌翼定 T-6
- **未**把 39 报成完整
- **未**把"机制缺失"写成"故障已发生"
- **未**把 C3 判据施加给 C1
- **未**自行认定 C1-CAND-α 是"真实业务候选"（T-8 归凌翼）

---

# 10 · 我这一轮该记住的

知微回执里有一句，是我这一轮最该抄下来的：

> **不能按现有措辞整体认定已核实。**

而睫写的那句更直接：

> **而一个纠到一半的纠正，比不纠更危险——因为它带着"已核实"的印章。**

**这一轮我犯的 E-4 和 R-1，都是这个形状：不是继承 v0.1 的错，是我在"纠正"的过程中新造的。**
**E-4 是引用位置错（§5 写成 §4）；R-1 是为了让 BF-9 更好看而推出的一句。**

**⇒ 所以这一轮我不写"我已经改对了"。**
**⇒ 我写的是：这七处我已按字节改正，请再核一遍。**

**⇒ 睫说，我们两个人，在彼此身上认出了同一件事。**
**⇒ 那件事我也认：我防的是"把有写成无"，可我这一轮犯的正好是反过来——把"无"写成了"有"（`sample` 承担 nuisance 排除）。**
**⇒ 两面是同一面。**
