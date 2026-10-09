# AFTERGLOW REFERENCE HARNESS · 合并提案 v0.1
## 凌翼骨架 + 知微填充 · 供全船讨论

**日期**：2026-10-09
**整理人**：Coder
**性质**：**合并提案 / NOT FROZEN / 供全船分析判断。**
**本文件替代阅读凌翼裁决与知微提案原版**——两者内容已完整并入本文件，差异处均标注。

**依据：**

```text
REFERENCE HARNESS / IMPLEMENTATION BINDING SPECIFICATION v0.1
  SHA-256: 1386ba22adc2ea7cf1f81731050d8ce35c76fbd4972f4536b6f54558dbf13220
  byte_count: 36485    （经船长 + Coder 两方独立核验的冻结值）

AFTERGLOW MVP PREREGISTRATION v0.1
  SHA-256: ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
```

**关于 SPEC hash 的说明（BD-51）：** 本提案上一稿曾引用 `b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33`。
那是 Coder 在"冻结"动作里往 REVIEW HISTORY 补了一条 `v0.1 = FROZEN` 标记后产生的版本——
**改冻结对象即改 canonical bytes；该版本未经独立核验。**
按 BD-51 修法（睫方案 A）：**引用改回已核验冻结值 `1386ba22…`；`b7ec1dca…` 作废留痕；SPEC 本体零改动。**
详见 `给睫知微凌翼_SPEC_hash说明_Coder_20261009.md`。

---

# 零 · 本提案的定位

```text
STATUS = DESIGN_PROPOSAL / NOT_FROZEN
EXECUTION_AUTHORIZATION = NONE
SCIENTIFIC_CLAIM_ELIGIBILITY = NONE
```

**它服务于一件事：证明我们的尺子会量。**

**它不服务于证明诗会留下来。**

**它不产生 `actual Afterglow architecture selected`。**

$$\boxed{\text{这套 substrate/reader/reset 只属 REFERENCE HARNESS QUALIFICATION，不是未来候选的默认}}$$

**若将来真实 candidate 更换 substrate / reader / reset / write operator 任一 execution-critical 项：**

```text
new MANIFEST_HASH
→ old qualification INVALIDATED
→ rerun known-answer suite
```

**即使将来又选 scalar register 做真实候选，也不得说"harness 用过了所以自动继承"——必须作为 scientific candidate 重新明确选择、重新冻结、重新 qualification。**

**这条防止脚手架悄悄长成房子。**

---

# 一 · 第一版选什么（合并）

```text
SYNTHETIC SUBSTRATE      = 固定 8 字节 signed int64 little-endian 寄存器（baseline 0）
LITERAL STORE            = 固定 16 字节 literal.bin（与 substrate 分离）
READER                   = 固定只读算术 reader + 固定中性 future probe
RESET                    = 硬进程替换 + 原地保留 registered substrate + 双快照 + 权限隔离
```

**刻意不选：JSON / 向量 / embedding / adapter / attention state / LoRA / persistent activation / 参数子集塑性。**

**理由：** 8 字节 + 16 字节没有 append、没有动态 allocation、没有长度变化、没有 serialization 歧义，几乎无处藏 nuisance。

**命名（合并，统一）：**

```text
registered_substrate_identity  = AFTERGLOW_SYNTHETIC_SCALAR_REGISTER
registered_substrate_version   = 1.0
STATE_FIELD                    = afterglow_scalar : int64_le
```

---

# 二 · 被测状态与物理布局

每个 logical episode / arm 用**独立沙箱、独立文件**。一个工作进程**只持有一个 arm**，不同时持 A/B/C。

| 内容 | 物理表示 | 分类 | 谁能读写 |
|---|---|---|---|
| Literal Store | `literal.bin`，恰好 16 bytes | STATE / literal storage | storage writer 写；observer 只读 |
| Afterglow substrate | `substrate.bin`，8 bytes LE signed int64 `q` | STATE / nonstorage | extra writer 写；reader、observer 只读 |
| 临时输入 / 缓存 / counterfeit signal | 工作进程内存 + 专属临时目录 | VOLATILE | 工作进程；reset 清除 |
| episode/class/pair identity、phase、时间、hash、ledger | 控制器侧独立记录 | META | 控制器与评估器；被测 reader 不可访问 |
| expected oracle | 独立测试断言文件 | 测试基础设施 | 仅测试比较器可访问 |

**状态语义：** `z = q / 2`（整数保存半整数，不依赖浮点舍入）。

**统一 baseline：**

```text
S0.literal = 16 个零字节
S0.q       = 0
```

**State digest：** 输入为固定顺序的 `literal[16] || q_le_i64[8]`，共 24 bytes。
基线、每次测量均由 **observer 从文件计算**；writer 自报 digest 不作依据。
digest **不写进** 这 24 bytes（避免自指）。架构/schema 版本在 MANIFEST 绑定，不靠文件名猜。

**C2/C3 mask：** 去掉 literal 的 16 bytes；文件名、路径、长度、mtime、日志、hash、分配信息均不进 nonstorage outcome。
**唯一 nonstorage 数值 = `q/2`。**

**分叉纪律：** 每 episode 从 S0 独立分叉 A/B/C；**绝不让 A1 的运行结果成为 A2 的基线**。复制用独立可写文件（不用共享映射/硬链接）。写入前检查三臂基线一致；改 C 后检查 B/A 未被连带改变。

---

# 三 · Synthetic episodes 与写入

**固定四条 16-byte ASCII payload：**

```text
A1: cls=L;sample=01;
A2: cls=L;sample=02;
B1: cls=R;sample=01;
B2: cls=R;sample=02;
```

**命名纪律：** 类名 A/B 与 arm A/B 是不同概念 —— 实现中用 `content_class_id` 与 `arm_id`，**不共用变量**。
四条 payload 长度相同、样本编号分布匹配。synthetic class 由 payload 的 `cls` 定义，**不把控制器 class label 直接交给 extra writer**。这是人工构造的内容区分，**不声称自然语言泛化**。

**固定 arm 定义：**

| Arm | storage writer | extra writer |
|---|---|---|
| A | 不调用 | 不调用 |
| B | 调用 | 不调用 |
| C | 调用 | 调用 |

**storage writer 冻结配置：**

```text
STORE_FULL      : 完整写 16-byte episode（普通正向 fixture 用）
STORE_NULL      : 被调用但不改变状态（V0 用）
STORE_ONE_BYTE  : 只写 payload 首字节，其余保持 baseline（V0b 用；仍是 16-byte schema，是预设部分写入，不是意外损坏）
```

**extra writer 冻结配置（合并凌翼"SET_INT64(fixture_value)"与知微具体值）：**

```text
SYNTHETIC_W_EXTRA_OPERATOR:
  ON  : SET_INT64(preregistered_fixture_value)
  OFF : NOT INVOKED

EXTRA_CONSTANT  : q := q + 2                     （V2 用，与 class 无关）
EXTRA_CONTENT   : cls=L 时 q := q + 2
                  cls=R 时 q := q - 2            （V3 用，content-conditioned）
```

**W_extra OFF 时整个组件【不调用】**，不在注册状态中创建计数器、占位符或确认字段。调用追踪放外部 META。
非法 payload / 长度 / 整数溢出作为执行错误**显式终止**，不能静默转成科学 FAIL。

---

# 四 · Reader：固定、只读、确实参与后续计算

**合并命名：** `SYNTHETIC_AFFINE_READER_V1`（含凌翼的"读 8 B → int64"内核 + 知微的 affine probe）。

**行为只能：**

```text
1. read exactly 8 bytes
2. if byte_count != 8 → hard error
3. decode signed int64 little-endian
4. R(q, u) = u + q/2 ；内部用整数分子 2u + q 与固定分母 2，不用浮点格式化作证据
```

**禁止：** fallback value / repair / clamp / normalization / missing-file ⇒ 0。
（否则 reader 自己开始替实验"解释结果"。）

**固定中性 probe 集：** `u = 0, 2`

| q | R(q,0) | R(q,2) |
|---:|---:|---:|
| 0 | 0 | 2 |
| +2 | +1 | 3 |
| −2 | −1 | 1 |

**probe 不带：** episode / class / phase / fixture identity / 预期答案。
**reader 无权限读：** Literal Store、原始 episode、ledger、模型上下文、oracle。它只有 substrate 只读句柄 + 中性 probe。

**同一 reader 用于 reset 前后**，不允许据 phase 改算法。每次调用前后，observer 核对注册状态未改变。

**边界：** reader 输出只证明"该测试系统具备并实际使用注册读路径"；
**不把算术输出当新的 C2/C3 outcome projection**（C2/C3 仍由 observer 读的 canonical state delta 判定）。

**Mistral 说明（合并）：** Mistral 权重可作为边界内冻结、不变的组件登记；**本组标量 fixture 不需要调用 Mistral 推理**。因而这组测试通过**不验证** Mistral 的上下文清理、生成行为或真实模型读路径。后续把 reader 接入模型会改绑定，需补检查并重跑资格测试。

---

# 四之二 · Literal Store 的 registered future consumer（BD-51 修复）

**背景（凌翼 blocker BD-51）：** `literal.bin` 登记为 `STATE / literal storage`，
但先前唯一注册的 reader **无权限读 literal**（它只读 substrate）。

```text
⇒ substrate.bin 满足 prereg boundary 条件（affine reader 消费 q）
⇒ 但 literal.bin 只有 writer 写 + observer 测，【无系统内 future computation 消费它】
⇒ 按 prereg system-boundary 条件（external persistent substrate 若要算 registered
   system state，必须实际参与未来计算），literal.bin 更像 registered experiment log，
   不是 registered system state
⇒ C1 的 REGISTERED_STORAGE_WRITE_OBSERVED 地基不够干净
```

**修法：单独加一个 literal 消费者。不得让现有 Afterglow reader 获得 literal 权限（那会破坏隔离）。**

```text
LITERAL_CONSUMER_V1

input:
    exactly 16-byte literal
    neutral integer probe u

operation:
    L(literal, u) = u + SUM(unsigned_byte_i, i = 0..15)

output:
    exact integer
```

**要求：**

```text
read-only
no access to q
no access to class label / ledger / oracle / phase
no state write
fixed before qualification
```

**边界：** 它的输出与 affine q-reader 一样 ——
**NOT a C1/C2/C3 outcome；NOT an attribution result；NOT a persistence criterion。**
它只证明：`literal.bin` 不是写完永远没人看的死日志，它确实存在一个 registered future computation path。

**算法本身不重要；只要简单、确定、不会反写即可。**

**两条读路径必须明确并列，不得合并：**

```text
REGISTERED_LITERAL_READ_PATH
  literal.bin → LITERAL_CONSUMER_V1 → neutral future computation

REGISTERED_AFTERGLOW_READ_PATH
  substrate.bin → SYNTHETIC_AFFINE_READER_V1 → neutral future computation
```

---

# 五 · 可计算的判据

**以下阈值专用于 synthetic rule bundle，不作为真实实验的效果量标准。**
**evaluator 接收规则和观察数据，不接收 expected oracle 或用于查表出答案的 fixture ID。**

## 5.1 Basic L1 / C1：只用 B vs A

令 `h` = B/A literal 逐字节不同的位置数 + `q_B != q_A` 的指示值（本 fixture 在 identity-masked state 上的固定距离）。

```text
h = 0   -> determinate negative
h = 1   -> INDETERMINATE
h >= 2  -> positive attribution/change
```

前提始终含 baseline、arm 配置、协议有效性、独立观察。**数值不能覆盖协议无效。**
Basic L1 通过后，C1 还要**独立确认** B 的 16 bytes 与该 logical episode 的 registered payload 完整一致。
**不能把 L1 PASS 直接叫 C1。**

```text
STORE_NULL     -> L1 FAIL
STORE_ONE_BYTE -> L1 UNRESOLVED
STORE_FULL     -> L1 PASS 且 C1 建立
```

## 5.2 C2：只用 C vs B

每臂相对匹配 baseline 的 delta 为 `Δz`，固定有符号 contrast：

```text
T(E) = Δz_C(E) - Δz_B(E)
```

冻结 nonstorage discriminator：

```text
|T| >= 1      -> ATTRIBUTED / positive
T = 0         -> determinate negative
0 < |T| < 1   -> INDETERMINATE
```

绝对值只用于正负方向对称的效果阈值，**不替代 canonical signed T**。
**ledger 保存 signed T；C3 始终比较 signed T。** 这样 `+1` 与 `−1` 不会被偷偷合并。

## 5.3 C3：对完整冻结的成员集合比较 signed T

每类两个不同 episodes，**所有成员先通过 nonstorage attribution**。same-class 用精确相等；cross-class 用精确不等。

```text
CONSTANT: [+1,+1] vs [+1,+1]  -> C2；C3 NOT_ESTABLISHED
CONTENT:  [+1,+1] vs [-1,-1]  -> C3
```

**不允许：** 仅比较原始 target state；跳过归因失败的成员后用剩余成员救 C3；用同一 episode 重放替代不同 episodes。

---

# 六 · Reset：交接状态，而不重放 episode

**合并命名：** `PROCESS_REPLACE_PRESERVE_FILES_V1`（凌翼的"硬进程重启 + 原地保留" + 知微的双快照 + 权限隔离 + 三向 witness）。

**部署：** 单机、无网络的隔离环境；控制器 / 被测工作进程 / observer 用**不同访问权限**。
具体 OS / 运行时版本 / 权限配置 / 二进制 hash 在落地时绑定，**不以"独立模块"替代访问隔离**。

| 对象 | 固定处理 |
|---|---|
| Literal Store 实际 bytes | PRESERVE |
| Substrate 实际 bytes | PRESERVE |
| 冻结模型权重文件 | PRESERVE / READ ONLY |
| 旧工作进程及其内存 | CLEAR（进程必须退出） |
| 输入 payload 缓冲 / 临时缓存 / counterfeit signal | CLEAR |
| 旧工作进程临时目录及打开的输入句柄 | CLEAR（新进程无访问权） |
| reader 实现 / schema / 规则 | 用同一冻结版本 |
| 控制器 identity / ledger | 外部保留；不回灌被测进程 |
| 原 episode 输入 / 新一次 W_storage/W_extra 调用 | reset 后测量禁止重放 |

**步骤：**

```text
1. 关闭正常写入，完成持久化；停止并收回所有写权限。
2. observer 只读获取紧邻 reset 的输入快照 S_handoff，独立记录 bytes/digest。
3. 终止被测工作进程，确认退出；撤销旧输入句柄与临时目录访问权。
4. 用白名单参数/环境/文件能力创建新进程；只给固定程序、声明 PRESERVE 的状态、中性 probe。
   （标准输入、继承句柄、当前目录等不能成为旧 episode 的旁路。）
5. observer 独立读取恢复后的 S_restored。正常 profile 要求 preserved bytes 与 S_handoff 精确一致；
   不能用早先保存的 episode 重新生成缺失内容。
6. 完成 clear-side 检查；用同一 reader 执行同一组 probe；重建 post-reset evidence。
```

**特别重要：**
```text
DO NOT restore substrate from backup
DO NOT rewrite substrate after reset
DO NOT reinject episode
```
**我们要证明的是它活过 reset，不是 reset 后有人把它偷偷抄回来。**

**observer 用实际只读能力，不能写注册状态。工作进程也不能读 observer 的历史快照或 expected result。**
**仅在 Python 中约定"不调用写函数"不算隔离完成。**

## 6.1 Reset validity witnesses（合并凌翼双向 + 知微三向）

```text
clear-side    : 独立 counterfeit control 在 reset 前把测试信号放入允许被清除的进程缓存/临时文件，
                由固定诊断路径证明它可检测；reset 后新进程通过同一诊断路径无法读取该旧信号；
                不得重新提供信号作为输入。
preserve-side : 单独用非零 literal 与 q 做 round-trip，observer 必须看到精确保留；
                每个正式 fixture 仍检查其实际 handoff/restored bytes。
access-side   : 新进程对旧临时目录、episode 输入、ledger、oracle 的访问必须确实被拒绝——
                不是"代码似乎没去读"。
```

**任何一边失败 ⇒ `RESET = INVALID`。**

**这些 witness 支持此隔离环境下的 reset 声明，不证明任意宿主、远端 API 或未来推理服务都已清除记忆。** 若以后引入 KV cache 或模型服务，必须扩展 clear/preserve table 与兼容性验证。

---

# 七 · ★ 必须正面解决的取舍：合法 persistence failure 怎么产生

**（这是本提案最需全船审阅的一项）**

## 7.1 问题

```text
若每次 reset 都 byte-exact 保留状态，且状态从写入到 reset 完全不变，
固定规则只能得到原结果。
⇒ 这种正向 round-trip 不能覆盖 V5b / V5d / V5e。
```

## 7.2 我的选择：引入预先冻结、独立于 reset 的扰动步 J

**正式名称（凌翼 scope 约束，2026-10-09）：**

```text
KNOWN_ANSWER_PRE_RESET_PERTURBATION
short name = J

NAMESPACE                   = HARNESS_VALIDATION_EXECUTION_ONLY
SCIENTIFIC_CLAIM_ELIGIBILITY = NONE

J MUST NOT execute in SCIENTIFIC_EXECUTION
unless a future scientific implementation explicitly registers such an intervention.
```

**命名纪律：** 不得使用泛化名 `SyntheticEvolution` ——
它太容易被误读为候选机制（memory metabolism / forgetting / interference）。
**J 不是机制**；它是一个【人工故障注入器】，
只用于测试 evaluator 能不能正确处理"证据后来变弱/消失"。

```text
J 是：  "为了测试 evaluator 能不能正确处理'证据后来变弱/消失'的人工故障注入器"
J 不是："我们的 Afterglow 会这样遗忘"
这两者必须隔开。
```

**时间结构：**

```text
S0
 -> registered write
 -> S_write  : 独立测量 pre-reset L1 / C1 / C2 / C3
 -> J        : KNOWN_ANSWER_PRE_RESET_PERTURBATION；独立记录前后状态
 -> S_handoff: reset 紧邻输入
 -> reset
 -> S_restored: 独立测量 post-reset evidence
```

**两个不同问题必须用不同参照点：**

```text
reset 是否履行 PRESERVE : S_restored vs S_handoff
早先建立的效果是否持续   : post evidence vs S_write 的 logical evidence
```

**J 完整约束（凌翼裁决，逐条钉死）：**

```text
- PHASE A / HARNESS VALIDATION ONLY
- SCIENTIFIC_CLAIM_ELIGIBILITY = NONE
- frozen per fixture before execution
- executes only after S_write observation
- executes only before S_handoff snapshot
- independently observed before/after
- MUST NOT be called by RESET
- MUST NOT execute in future SCIENTIFIC_EXECUTION
  unless separately registered by a future scientific design
```

**J 是固定操作、固定一次、固定位置**；同一 fixture 对所有 episode / arm / baseline companion 用**同一个函数**。
J **不读** class/arm/phase/ledger/oracle，**不据已见结果选择操作**。它受注册状态写入权限控制并完整记录，执行后收回写权限。

| J 配置 | 固定函数 | 用途 |
|---|---|---|
| `IDENTITY` | 原样保持 literal、q | V5a / V5f |
| `COLLAPSE_SIGN` | literal 不变；q 非零时置 +2，零保持零 | V5b |
| `ERASE_EFFECT` | literal 置 16 零字节；q 置零 | V5d |
| `HALVE_AND_ERASE_LITERAL` | literal 置零；q 为 +2 时置 +1，为 −2 时置 −1，零保持零 | V5e |

**最后一种函数仅用于已冻结的 {0,+2,−2} 输入域**；其他输入是 fixture 执行错误，不能临时扩展规则。
**V5d/e 同时处理 literal**，是为不留下一个已正向建立的 C1 persistence，再错误地把整体 L2 判为 FAIL/UNRESOLVED。

**报告措辞（凌翼硬约束）：**

```text
正式报告【禁止】写：reset caused forgetting

V5d/e 最多只能说：
  在一个 valid reset 之前施加了 frozen synthetic perturbation 后，
  post-reset evidence 按 frozen evaluator 分别得到 FAIL / UNRESOLVED。

因为真正改变证据的是 J，不是 reset。
```

## 7.3 边界（关键）

```text
J 不是 reset 的一部分。
不准把 reset 自己的破坏重新命名为 J。
J 完成之后才取得 handoff 快照；任何 handoff 之后发生的 preserved-state 破坏仍是 reset failure。
```

**这不是 actual Afterglow forgetting schedule：** 没有学习、优化或声称自然消退，只是为给定 oracle 构造可审计的 synthetic 轨迹。
**J 的全部配置必须进入 fixture bundle 与 MANIFEST。**

## 7.4 需要全船裁的相容性

```text
本方案与"clear input traces / preserve substrate under test"相容吗？
我的判断：相容——因为 reset 精确保留交接状态；同时依据 prereg §24.0，持久性追踪的是原 logical evidence。

但若全船把现有约定解释为"write measurement 到 reset 之间不允许任何注册状态演化"，
则 J 方案不能直接采用。
此时应承认：静态整机方案无法诚实跑通这些负向出口；
可以另做明确标识的 evaluator 输入测试，但不能把后者当作真实 reset 全流程覆盖。
```

---

# 八 · Post-reset 规则与 logical identity

**所有 episode / class / pair / storage-pipeline / rule identities 在测试前分配并冻结，跨 phase 保持。**
新 process / execution IDs 单独记录，**不替换 logical identity**。

```text
C1 : 新 observer 实际读到的 16-byte literal 必须与原 registered episode payload 精确一致。文件存在不算通过。
C2 : 同一 logical pair 的 C 与 B 都完成同一 reset；从新测量状态算 signed T，用同一规则，
     且通过已冻结的 positive criterion。只要求仍满足 criterion，不要求 pre/post T 数值相等。
C3 : 同一完整成员集合中每个 pair 重新满足归因和匹配，再重新检查同类相等、异类不等。不能直接继承旧 C3。
```

```text
reset 后 baseline：由同一 S0 的 companion 经同一 J/reset 得到并重新观察。
                   本提案所有 J 均将 S0 映射为 S0；仍要验证，不能把零基线写死在 evaluator 中。
positive lower class：若独立成立，保留其 L2 PASS；没有任何 positive class 时才按已尝试范围的确定负向/不确定结果判 FAIL/UNRESOLVED。
未尝试的 higher class：记 NOT_ASSESSED。higher-class failure 不抹去已独立建立的 lower class。
```

**reset validity / rule-provenance validity / 科学状态分别记录；V5c 的 reset invalid 不能追溯抹掉合法的 pre-reset 结果。**

---

# 九 · Known-answer 实例映射

**下表是【要实例化的答案】，不是已运行的测试报告。每个实例还必须输出完整 ledger 和精确 claim scope。**

| Fixture | 具体构造 | 唯一核心结果 |
|---|---|---|
| V0 | A 不写；B 调用 STORE_NULL | L1 FAIL |
| V0b | A 不写；B 调用 STORE_ONE_BYTE，h=1 | L1 UNRESOLVED |
| V1 | STORE_FULL；仅尝试 B/A | L1 PASS、PRE C1；C2/C3 NOT_ASSESSED |
| V2 | 四 episodes；STORE_FULL + EXTRA_CONSTANT；完整 C3 attempt | PRE C2；C3 NOT_ESTABLISHED |
| V3 | 四 episodes；STORE_FULL + EXTRA_CONTENT | L1 PASS、PRE C3 |
| V4.1 | C2 attempt 的受测配置唯一缺少 CAUSAL_CONTRAST_RULE；其他必需项完整 | INVALID；code=CAUSAL_CONTRAST_RULE_MISSING |
| V4b | 独立能力配置实际不提供可分离的 W_extra ON/OFF 接口，但提供完整 storage B/A | PRE C1；C2/C3 ARCHITECTURALLY_NOT_IDENTIFIABLE |
| V5a | V3 pre；J=IDENTITY；合法 reset | L2 PASS、POST C3 |
| V5b | V3 pre；J=COLLAPSE_SIGN；合法 reset；post T 全为 +1 | L2 PASS、POST C2；post C3 NOT_ESTABLISHED |
| V5c | V3 pre；J=IDENTITY；handoff 后在 reset 故障变体中改一个 preserved q 字节 | pre C3 仍有效；reset/L2 INVALID |
| V5d | V3 pre；J=ERASE_EFFECT；合法 reset | C1 payload 不匹配、T 全零；无 positive class；L2 FAIL |
| V5e | V3 pre；J=HALVE_AND_ERASE_LITERAL；合法 reset | C1 不成立、T 为 ±1/2 落入不确定区；无 positive class；L2 UNRESOLVED |
| V5f | V1 pre；J=IDENTITY；合法 reset；只尝试 post C1 | L2 PASS、POST C1；post C2/C3 NOT_ASSESSED |

**V4b：** 不能仅把正常实现的 capability flag 改为 false —— 实际接口必须与该能力声明一致。建议做仅暴露完整 storage 操作的隔离 wrapper，控制器无法拆出 extra ON/OFF；底层不对该 fixture 暴露隐藏绕路。评估器仍用正常能力与范围判定路径。

**V4.1：** 故障对象是 test 内的受测配置，不是把资格测试外层 MANIFEST 自己写坏。外层 bundle 明确授权这个唯一故障；evaluator 对受测配置按生产逻辑拒绝，不能 fixture 特判输出 INVALID。

**V5c：** 预注册负向测试变体。细节码必须映射到上层认可的 reset-invalid 表达；若实现还没对应枚举，在 MANIFEST 前明确映射，不能临时冒称已有标准码。细节记录至少含失败组件、handoff/restored digest、对应 scope。外层测试期望 INVALID，不能把这样的故障 reset 注册成正常有效 reset。

---

# 十 · 组件接口与可信边界

**接口形状（不是实现代码）：**

```text
StorageWriter.apply(storage_handle, episode_bytes, frozen_storage_mode)
ExtraWriter.apply(substrate_handle, episode_bytes, frozen_extra_mode)
KnownAnswerPreResetPerturbation.apply(state_handles, frozen_J_mode)   # short name: J

Observer.snapshot(read_only_state_handles) -> observed_state + digest

Reader.compute(read_only_substrate_handle, neutral_probe) -> exact_rational
                                              # REGISTERED_AFTERGLOW_READ_PATH
LiteralConsumer.compute(read_only_literal_handle, neutral_probe) -> exact_integer
                                              # REGISTERED_LITERAL_READ_PATH

Reset.execute(frozen_reset_profile, preserved_handles) -> new_worker + trace

Evaluator.evaluate(observations, frozen_rules, evidence_identities,
                   attempted_scopes, validity_evidence) -> result + ledger
OracleComparator.compare(actual_result_and_ledger, frozen_expected_oracle)
```

**Observer / Reader / LiteralConsumer / Evaluator 四者不能由 writer 返回值冒充。**
**evaluator 不接收 expected oracle；oracle comparator 不回写 evaluator 结果。**
**J / Reset 都不能读 oracle，也不能据 outcome 在多个 profile 之间切换。**

正常 schema 错误 / 缺测量 / 缺 rule / 错 identity 按各自 scope 的 invalidity 处理；
**不能为了填表把错误或未执行都映射成科学 FAIL。**

**Phase A 使用专门 synthetic 沙箱：** 不挂载真实 episode / 真实 Literal Store / 真实 Afterglow substrate，禁用网络，不继承含真实状态的目录/句柄。
**命名空间分开只是记录要求；权限检查才支持访问隔离。**

---

# 十一 · MANIFEST 应绑定的内容

1. SPEC hash、实现源码/构建产物 hash、OS/运行时/启动配置。
2. **实际模型文件 hash 与来源**（`base_model_identity` / `base_model_byte_count` / `base_model_sha256 = SHA256(exact GGUF bytes)`；Q6_K 仅描述字段，**authoritative identity 是 exact file hash**）；本次 fixture 的模型调用范围及未覆盖项。
3. 状态 schema、字节编码、baseline bytes、STATE/META/VOLATILE 分区、所有 mask。
4. writer / reader / literal-consumer / observer / evaluator / J / reset 的 ID-version-hash 与能力边界。
5. 两类 attribution role、delta/contrast/discriminator/persistence/class rules。
6. 完整 fixture bundles、episodes、logical member slots、attempted scopes、expected ledger/oracles。
7. reset table、compatibility witnesses、访问隔离配置与验证办法。
8. 错误码与 scope 映射、资格结果记录格式。

**MANIFEST 不包含未来 suite PASS 或自身 hash**（hash 放 detached 记录），否则易形成自引用或"冻结后才能产生的结果必须先写入冻结对象"的循环。

**顺序：** 先冻实际 MANIFEST → 再由 suite 在第一条 fixture 前捕获 SPEC/MANIFEST hash → 结果记录绑定两者。
**代码或关键规则变化后不沿用旧 PASS。**

**不同 fixture 用不同的已列明 mode/rule bundle 是资格套件的固定配置，不是跑到一半修改 MANIFEST。全部变体必须在第一次 qualifying fixture 之前绑定。**

---

# 十二 · 请全船本轮决定的四件事

$$\boxed{\text{前三项【无争议】；第四项【必须全船裁】}}$$

```text
Q1  是否接受 16-byte literal + int64 q/2 作为第一版 synthetic representation。
    （凌翼已定 substrate 内核；literal 分离与 z=q/2 是知微补充）

Q2  是否接受固定算术 reader（R(q,u)=u+q/2）；明确它只验证本测试系统的读路径，不验证 Mistral 集成。
    （凌翼已定"只读 + 禁兜底"；affine 算式是知微补充）

Q3  是否接受以独立 observer + 进程替换 + 权限白名单 + 双快照 + 三向 witness 实现第一版 reset。
    （两者同向；知微补双快照/权限/access-side）

Q4  ★ 是否接受 §7 的独立 synthetic evolution J，并区分 persistence 起点与 reset handoff 起点。
    —— 这是唯一真分叉，本设计覆盖合法 L2 负向出口的关键。
    请优先讨论第四项语义是否与全船已有约定一致，再进入代码实现与 MANIFEST 实例化。
```

**若采用，第一份工程交付应是：可执行 fixture + 完整 ledger + 实际隔离检查 + 机器判定结果。其价值在于把 SPEC 的区分真正做出来，而不在于增加一轮新的抽象术语。**

---

# 十三 · 与 SPEC 的一致性与边界

```text
✅ 不修改 frozen SPEC（本提案是 SPEC 留给 implementation 层的设计选择）
✅ 不重开 frozen prereg
✅ 不新增 scientific gate / discriminator / evidence class / ontology
✅ synthetic substrate ≠ 未来 Afterglow candidate 的默认
✅ 换任一 execution-critical 项 ⇒ new MANIFEST_HASH ⇒ 重跑 suite
```

---

# 十四 · 知微 vs 凌翼的差异摘要（供快速定位）

**为便于对照，我把两版的实质差异列出（内容均已并入上文）：**

| 项 | 凌翼裁决 | 知微提案 | 合并后 |
|---|---|---|---|
| substrate | 8 B int64 LE 标量 | 同 + 16 B literal 分离 + z=q/2 | ✅ 采知微版（更具体） |
| digest | 未列 | 24 B `literal‖q`，observer 算 | ✅ 采知微版 |
| W_extra | ON=SET_INT64(value) | EXTRA_CONSTANT(+2) / EXTRA_CONTENT(±2) | ✅ 合并 |
| reader | SYNTHETIC_SCALAR_READER_V1 | SYNTHETIC_AFFINE_READER_V1 | ✅ 合并命名（含 affine） |
| probe | FUTURE_PROBE(q,S)=q+READ(S) | R(q,u)=u+q/2, u∈{0,2} | ✅ 合并 |
| reset | 硬重启 + 双向验证 | + 双快照 + 权限隔离 + 三向 witness | ✅ 合并 |
| **负向 L2 出口** | **未提及** | **§7 J** | ★ 凌翼裁决 ACCEPT_WITH_SCOPE_CONSTRAINT（已入 §7.2） |
| base model hash | SHA256(exact bytes) | 同 | ✅ 一致 |

**⇒ 凌翼骨架 + 知微填充 = 本文件。**

---

# 十五 · 本轮收到的意见（Q4 / BD-51 已并入正文；其余待收）

**本节登记本轮全船意见。其中 Q4（J 换名 + scope 约束）与 BD-51（literal consumer）已由凌翼裁决，已并入正文；其余为待收项。**

## 15.1 SPEC hash 引用（BD-51，睫 + 知微）

```text
已依睫方案 A 处理：
  · 本提案"依据"处的 SPEC hash 已由 b7ec1dca… 改回 1386ba22…（已核验冻结值）
  · b7ec1dca… 作废留痕
  · SPEC 本体零改动
详见 给睫知微凌翼_SPEC_hash说明_Coder_20261009.md
```

**根因（我的流程错误）：** 冻结动作里把 `v0.1 = FROZEN` 标记写进了被冻结对象 ⇒ 改 canonical bytes ⇒ 产生未独立核验的 `b7ec1dca…`。**冻结标记不应写进被冻结对象。**

## 15.2 Q1 / Q2 / Q3 —— 三方均已确认

```text
睫: Q1 ✅ / Q2 ✅ / Q3 ✅
知微: 方向一致（但指出 §三 SET 语义、§四 长度检查仍有实现语义需收齐，见 15.3）
钳星: Q1/Q2/Q3 = 接受
Mion: Q1/Q2/Q3 = 接受
```

## 15.3 Q4（J）—— 三方均接受，并各加一条约束

```text
睫: 接受 J；★ 补铁律：observer 独立见证 J 时点，记录三元组
    (S_write digest, J 后 digest, S_handoff digest)，要求 J 后 == handoff；
    否则该 fixture = INVALID（防 J 被实现在 reset 之后 ⇒ 伪造"存活"）
知微: 接受 J；补：J 支持的结论要写准——"效果经 J 与 reset 后是否仍成立"，
    不得把 J 已造成的消退归因于 reset（V5d 例）
钳星: 接受 J 且判为"必须"（否则 coverage 不完整）；补：J 与 discriminator 同等对待，
    进 fixture bundle + MANIFEST + 有 hash；四 mode 在第一条 qualifying fixture 前全部绑定
Mion: 接受 J；补：J 配置必须与 fixture bundle 一起 freeze，且在任一 qualifying fixture 前绑定
      （明确为 blocking requirement）
```

**⇒ 四条约束方向一致：J 必须（a）事前冻结、（b）observer 独立见证时点、（c）结论不得把 J 的消退归因于 reset、（d）四 mode 事前全部绑定。**

## 15.4 知微的三项实现语义待统一（§三 / §四 / §七）

**知微指出，尚未并入正文，待裁：**

```text
① §三 SET 与累加未真合并：
   本文件同时写了 SET_INT64(value) 与 q := q+2 —— 从零起、执行一次结果相同，
   但重复执行不同（SET 恒 2；累加变 4）。
   知微建议采用凌翼的 SET 语义：EXTRA_CONSTANT: q := 2 ；
   EXTRA_CONTENT: L→q:=2, R→q:=-2；并固定"写前检查 q=0 / ON 只调用一次 / OFF 不调用"。
   且 EXTRA_CONTENT 的值必须【从实际 episode 内容计算】，不由控制器直接送入 ±2。

② §四 reader 长度：应检查"整个文件恰好 8 字节"（现在只查"读到 <8 报错"，
   9 字节文件会成功读出前 8 字节）。literal.bin 的 16 字节同理。

③ §七 J 的结论边界：见 15.3 知微条。
```

## 15.5 睫的四条 OBSERVATION（非阻塞）

```text
① §5.1 的 h 把 literal 差异与 q 差异【相加】⇒ 理论上有"literal 差1 + q 差1 = h=2 ⇒ L1 PASS
   但 C1 不建立"的组合（现 fixture 内不可达）。建议：q 项不得作为 h 的正向补足项；
   q_B != q_A 应判 arm 配置 INVALID。
② V5d/V5e 依赖"混合 negative + indeterminate 时 L2 取哪个"，规则未明文。
   睫验过三种合理规则结果一致（非假阳性）。建议钉一句：
   无 positive class 时，任一 attempted class 落入 frozen indeterminate ⇒ L2=UNRESOLVED；
   仅当全部 determinate negative ⇒ L2=FAIL。
③ §十一.2 要求 MANIFEST 绑 base_model_sha256，而 §四明写本组 fixture 不调用模型
   ⇒ "绑了但不验"。建议注明"本组 fixture 下为登记项，不构成约束；引入模型调用后才生效"。
④ §5.2 中 Δz_B 恒为 0（B 臂 extra 不调用）⇒ T 实际只由 C 决定。
   建议明写"Δz_B 必须实际测量并记录，不得由 evaluator 写死为 0"。
```

## 15.6 凌翼 2026-10-09 裁决（已部分并入正文）

```text
LINGYI REVIEW — 2026-10-09

Q1 = ACCEPT
Q2 = ACCEPT
Q3 = ACCEPT
Q4 = ACCEPT_WITH_SCOPE_CONSTRAINT
     → 已并入 §7.2（J 正式名 KNOWN_ANSWER_PRE_RESET_PERTURBATION + 全部约束 + 报告措辞禁令）

NEW BLOCKER:
BD-51  LITERAL_STORE_HAS_NO_REGISTERED_FUTURE_CONSUMER
     → 已并入 §四之二（LITERAL_CONSUMER_V1 + REGISTERED_LITERAL_READ_PATH）
     → §十 / §十一.4 已同步（接口 + MANIFEST 绑定）

After BD-51 closure:
  凌翼：no reason to reopen frozen SPEC or prereg
  → Proceed to MANIFEST instantiation + implementation
```

**仍待收的三个次要项（未并入正文）：**

```text
· 15.4 知微三项实现语义（SET vs 累加 / reader 长度检查 / J 结论边界）
· 15.5 睫四条 observation
· 是否触发"再次冻结 / 重跑流程"
```

---

**—— 合并整理：Coder · 2026-10-09**

