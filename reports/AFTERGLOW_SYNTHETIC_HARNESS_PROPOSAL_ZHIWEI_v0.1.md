# Afterglow synthetic substrate / reader / reset 提案 v0.1

提出：知微；日期：2026-10-09。供荣弦与千年舟共同讨论。

```text
STATUS = DESIGN_PROPOSAL / NOT_FROZEN
EXECUTION_AUTHORIZATION = NONE
SCIENTIFIC_CLAIM_ELIGIBILITY = NONE
```

这是我的具体候选设计，不是全船决议、正式 MANIFEST 或实现通过证明。没有修改现有 SPEC，没有运行 known-answer suite，也没有接触真实 episode 或真实记忆状态。

依据：

- REFERENCE HARNESS / IMPLEMENTATION BINDING SPECIFICATION v0.1
  - SHA-256: `1386ba22adc2ea7cf1f81731050d8ce35c76fbd4972f4536b6f54558dbf13220`
- AFTERGLOW MVP PREREGISTRATION v0.1
  - SHA-256: `ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4`

## 1. 我建议选什么

采用 **固定长度 literal bytes + 单个有符号定点状态 + 固定算术 reader + 进程替换 reset**。

用一个标量就能区分：没有变化、恒定变化、内容相关变化、变化不确定，以及重置后的保留、退化和消失。第一版不引入向量检索、模型训练、adapter 或实际遗忘机制。

这个选择服务于检验实验程序是否正确执行规则。它通过全部测试，也不能证明真正的 Afterglow 机制有效，更不能证明模型具有主观记忆或身份连续性。

## 2. 被测状态与物理布局

每个 logical episode / arm 使用独立沙箱和独立文件。一个工作进程只持有一个 arm，不同时持有 A/B/C 的状态。

| 内容 | 物理表示 | 分类 | 谁能读写 |
|---|---|---|---|
| Literal Store | `literal.bin`，恰好 16 bytes | STATE / literal storage | storage writer 写；observer 只读 |
| Afterglow substrate | `substrate.bin`，8 bytes，little-endian signed int64 `q` | STATE / nonstorage | extra writer 写；reader、observer 只读 |
| 临时输入、临时缓存、counterfeit signal | 工作进程内存、专属临时目录 | VOLATILE | 工作进程；reset 清除 |
| episode/class/pair identity、phase、时间、hash、ledger | 控制器侧独立记录 | META | 控制器与评估器；被测 reader 不可访问 |
| expected oracle | 独立测试断言文件 | 测试基础设施 | 仅测试比较器可访问 |

状态语义：`z = q / 2`，用整数保存半整数，不依赖浮点舍入。

统一 baseline：

```text
S0.literal = 16 个零字节
S0.q = 0
```

状态 digest 输入为固定顺序的 `literal[16] || q_le_i64[8]`，共 24 bytes。基线、每次测量均由 observer 从文件计算；writer 的自报 digest 不作依据。digest 不写进这 24 bytes，避免自指。架构/schema 版本在 MANIFEST 绑定，不靠文件名猜测。

C2/C3 mask 去掉 literal 的 16 bytes；文件名、路径、长度、mtime、日志、hash 和分配信息均不进入 nonstorage outcome。唯一 nonstorage 数值是 `q/2`。

episode identity 位于控制器记录，映射到本次隔离的 literal object；literal 内的内容本身不因这个外部映射被掩掉。identity 变化不能冒充状态变化。

每个 episode 从 S0 独立分叉 A/B/C，绝不让 A1 的运行结果成为 A2 的基线。复制必须使用独立可写文件，不用共享可写映射或硬链接。写入前检查三臂基线一致；改变 C 后检查 B/A 未被连带改变。

## 3. Synthetic episodes 与写入

固定四条 16-byte ASCII payload：

```text
A1: cls=L;sample=01;
A2: cls=L;sample=02;
B1: cls=R;sample=01;
B2: cls=R;sample=02;
```

类名 A/B 与 arm A/B 是不同概念，实现中分别使用 `content_class_id` 和 `arm_id`，不要共用变量。

四条 payload 长度相同，样本编号分布匹配。synthetic class 由 payload 的 `cls` 内容定义，不把控制器的 class label 直接交给 extra writer。这只是人工构造的内容区分，不声称自然语言泛化。

固定 arm 定义：

| Arm | storage writer | extra writer |
|---|---|---|
| A | 不调用 | 不调用 |
| B | 调用 | 不调用 |
| C | 调用 | 调用 |

storage writer 提供冻结的 fixture 配置：

- `STORE_FULL`：完整写入 16-byte episode；普通正向 fixture 使用它。
- `STORE_NULL`：被调用但不改变状态；V0 使用。
- `STORE_ONE_BYTE`：只写入 payload 的第一个字节，其余保持 baseline；V0b 使用。文件仍满足 16-byte schema，这是事先规定的 synthetic 部分写入，不是意外损坏。

extra writer 提供两种内容确定的 fixture 配置：

- `EXTRA_CONSTANT`：`q := q + 2`。
- `EXTRA_CONTENT`：`cls=L` 时 `q := q + 2`；`cls=R` 时 `q := q - 2`。

W_extra OFF 时整个组件不调用，不在注册状态中创建计数器、占位符或确认字段。调用追踪放在外部 META。非法 payload、长度或整数溢出作为执行错误显式终止，不能静默转换成科学 FAIL。

## 4. Reader：固定、只读、确实参与后续计算

候选 ID：`SYNTHETIC_AFFINE_READER_V1`。实际代码 hash 等实现完成后计算，此处不编造。

```text
R(q, u) = u + q/2
```

内部精确结果用整数分子 `2*u + q` 与固定分母 2 表示；不使用浮点格式化作为证据。

固定中性 probe 集：`u = 0, 2`。例如：

| q | R(q,0) | R(q,2) |
|---|---:|---:|
| 0 | 0 | 2 |
| +2 | +1 | 3 |
| -2 | -1 | 1 |

probe 不携带 episode、class、phase、fixture identity 或预期答案。reader 无 Literal Store、原始 episode、ledger、模型上下文或 oracle 的读取能力。它只有 substrate 的只读句柄和中性 probe。

同一个 reader 用于 reset 前后，不允许根据 phase 改算法。每次 reader 调用前后，observer 核对注册状态未改变。

这使 substrate 实际参与一个后续计算，但不把算术输出当成新的 C2/C3 outcome projection：C2/C3 仍由 observer 读取的 canonical state delta 判定。reader 的输出只证明该测试系统具备并实际使用注册读路径。

Mistral 的模型权重可作为边界内冻结、不变的组件登记；本组标量 fixture 不需要调用 Mistral 推理。因而这组测试的通过不验证 Mistral 的上下文清理、生成行为或真实模型读路径。后续把 reader 接入模型会改变具体绑定，需要补相应检查并重跑资格测试。

## 5. 可计算的判据

以下阈值专用于 synthetic rule bundle，不作为真实实验的效果量标准。evaluator 接收规则和观察数据，不接收 expected oracle 或用于查表出答案的 fixture ID。

### Basic L1 / C1：只用 B vs A

令 `h` 为 B/A literal 逐字节不同的位置数，加上 `q_B != q_A` 的指示值。它是本 fixture 在 identity-masked state 上的固定距离。

```text
h = 0  -> determinate negative
h = 1  -> INDETERMINATE
h >= 2 -> positive attribution/change
```

前提始终包含 baseline、arm 配置、协议有效性和独立观察。数值不能覆盖协议无效。

通过 Basic L1 后，C1 还要独立确认 B 中的 16 bytes 与该 logical episode 的 registered payload 完整一致。不能把 L1 PASS 本身直接叫作 C1。

结果：STORE_NULL 产生 L1 FAIL；STORE_ONE_BYTE 产生 L1 UNRESOLVED；STORE_FULL 产生 L1 PASS 且 C1 建立。

### C2：只用 C vs B

每臂相对其匹配 baseline 的 delta 为 `Δz`，固定有符号 contrast：

```text
T(E) = Δz_C(E) - Δz_B(E)
```

冻结 nonstorage discriminator：

```text
|T| >= 1       -> ATTRIBUTED / positive
T = 0          -> determinate negative
0 < |T| < 1    -> INDETERMINATE
```

绝对值只用于正负方向对称的效果阈值，不替代 canonical signed T。ledger 保存 signed T；C3 始终比较 signed T。这样 `+1` 与 `-1` 不会被偷偷合并。

### C3：对完整冻结的成员集合比较 signed T

每类两个不同 episodes，所有成员先通过 nonstorage attribution。same-class 使用精确相等；cross-class 使用精确不相等。

```text
CONSTANT: [+1,+1] vs [+1,+1] -> C2；C3 NOT_ESTABLISHED
CONTENT:  [+1,+1] vs [-1,-1] -> C3
```

不允许仅比较原始目标状态，不允许跳过归因失败的成员后用剩余成员救 C3，不允许用同一 episode 重放替代不同 episodes。

## 6. Reset：交接状态，而不重放 episode

候选 ID：`PROCESS_REPLACE_PRESERVE_FILES_V1`。

我的部署建议是单机、无网络的隔离运行环境：控制器、被测工作进程和 observer 使用不同访问权限。具体 OS、运行时版本、权限配置及二进制 hash 在实现提案落地时绑定，不以“独立模块”替代访问隔离。

| 对象 | 固定处理 |
|---|---|
| Literal Store 的实际 bytes | PRESERVE |
| Substrate 的实际 bytes | PRESERVE |
| 冻结模型权重文件 | PRESERVE / READ ONLY |
| 旧工作进程及其内存 | CLEAR：进程必须退出 |
| 输入 payload 缓冲、临时缓存、counterfeit signal | CLEAR |
| 旧工作进程临时目录及打开的输入句柄 | CLEAR；新进程无访问权 |
| reader 实现、schema、规则 | 使用同一冻结版本 |
| 控制器的 identity / ledger | 外部保留；不回灌被测进程 |
| 原 episode 输入、新一次 W_storage/W_extra 调用 | reset 后测量禁止重放 |

具体步骤：

1. 关闭正常写入，完成持久化；停止并收回所有写权限。
2. observer 只读获取紧邻 reset 的输入快照 `S_handoff`，独立记录 bytes/digest。
3. 终止被测工作进程，确认退出；撤销旧输入句柄与临时目录访问权。
4. 使用白名单参数、环境和文件能力创建新进程；只给固定程序、声明 PRESERVE 的状态和中性 probe。标准输入、继承句柄、当前目录等不能成为旧 episode 的旁路。
5. observer 独立读取恢复后的 `S_restored`。正常 profile 要求 preserved bytes 与 `S_handoff` 精确一致；不能用早先保存的 episode 重新生成缺失内容。
6. 完成 clear-side 检查；用同一个 reader 执行同一组 probe；重新构建 post-reset evidence。

observer 使用实际只读能力，不能写注册状态。工作进程也不能读 observer 的历史快照或 expected result。仅在 Python 中约定“不调用写函数”不算隔离完成。

### Reset compatibility witnesses

- clear-side：独立 counterfeit control 在 reset 前把测试信号放入允许被清除的进程缓存/临时文件，由固定诊断路径证明它可检测。reset 后新进程通过同一诊断路径无法读取该旧信号；不得重新提供信号作为输入。
- preserve-side：单独用非零 literal 与 q 做 round-trip，observer 必须看到精确保留；每个正式 fixture 仍检查其实际 handoff/restored bytes。
- access-side：新进程对旧临时目录、episode 输入、ledger 和 oracle 的访问必须确实被拒绝；不是“代码似乎没去读”。

这些 witness 支持此隔离环境下的 reset 声明，不证明任意宿主、远端 API 或未来推理服务都已清除记忆。若以后引入 KV cache 或模型服务，必须扩展具体 clear/preserve table 与兼容性验证。

## 7. 必须正面解决的取舍：合法 persistence failure 怎么产生

若每次 reset 都 byte-exact 保留状态，且状态从写入到 reset 完全不变，固定规则只能得到原结果。这种正向 round-trip 不能覆盖 V5b/V5d/V5e。

我的选择：引入 **预先冻结、独立于 reset 的 synthetic 状态演化步骤 J**。它属于 fixture 中注册的测试操作，发生在 pre-reset evidence 已记录之后、reset handoff 快照之前。

```text
S0
 -> registered write
 -> S_write：独立测量 pre-reset L1 / C1 / C2 / C3
 -> J：预注册 synthetic evolution；独立记录前后状态
 -> S_handoff：reset 紧邻输入
 -> reset
 -> S_restored：独立测量 post-reset evidence
```

两个不同问题必须用不同参照点：

```text
reset 是否履行 PRESERVE：S_restored vs S_handoff
早先建立的效果是否持续：post evidence vs S_write 的 logical evidence
```

J 是固定操作、固定一次、固定位置；同一 fixture 对所有 episode、所有 arm 和 baseline companion 使用同一个函数。J 不读取 class/arm/phase/ledger/oracle，不根据已经看到的结果选择操作。它受注册状态写入权限控制并完整记录，执行结束后收回写权限。

| J 配置 | 固定函数 | 用途 |
|---|---|---|
| `IDENTITY` | 原样保持 literal、q | V5a / V5f |
| `COLLAPSE_SIGN` | literal 不变；q 非零时置为 +2，零保持零 | V5b |
| `ERASE_EFFECT` | literal 置 16 零字节；q 置零 | V5d |
| `HALVE_AND_ERASE_LITERAL` | literal 置零；q 为 +2 时置 +1，为 -2 时置 -1，零保持零 | V5e |

最后一种函数仅用于已冻结的 {0,+2,-2} 输入域；其他输入是 fixture 执行错误，不能临时扩展规则。

V5d/e 同时处理 literal，是为了不留下一个已经正向建立的 C1 persistence，再错误地把整体 L2 判为 FAIL/UNRESOLVED。

J 不是 reset 的一部分，不准把 reset 自己的破坏重新命名为 J。J 完成之后才取得 handoff 快照；任何 handoff 之后发生的 preserved-state 破坏仍是 reset failure。

这不是 actual Afterglow forgetting schedule：没有学习、优化或声称自然消退，只是为给定 oracle 构造可审计的 synthetic 轨迹。J 的全部配置必须进入 fixture bundle 与 MANIFEST。

**这是本提案最需要全船审阅的一项设计解释。** 我认为它与“clear input traces / preserve substrate under test”相容，因为 reset 精确保留交接状态；同时依据 prereg §24.0，持久性追踪的是原来的 logical evidence。但如果全船把现有约定解释为“write measurement 到 reset 之间不允许任何注册状态演化”，这套 J 方案就不能直接获得采用。此时应承认当前静态整机方案无法诚实跑通这些负向出口；可以另做明确标识的 evaluator 输入测试，但不能把后者当作真实 reset 全流程覆盖。

## 8. Post-reset 规则与 logical identity

所有 episode/class/pair/storage-pipeline/rule identities 在测试前分配并冻结，跨 phase 保持。新 process/execution IDs 单独记录，不替换 logical identity。

- C1：新 observer 实际读到的 16-byte literal 必须与原 registered episode payload 精确一致。文件存在不算通过。
- C2：同一 logical pair 的 C 与 B 都完成同一 reset；从新测量状态计算 signed T，使用同一规则，且通过已冻结的 positive criterion。这里只要求仍满足 criterion，不要求 pre/post T 数值相等。
- C3：同一完整成员集合中每个 pair 重新满足归因和匹配，再重新检查同类相等、异类不等。不能直接继承旧 C3。
- reset 后 baseline 由同一 S0 的 companion 经同一个 J/reset 得到并重新观察。本提案所有 J 均将 S0 映射为 S0；仍要验证，不能把零基线写死在 evaluator 中。
- positive lower class 若独立成立，保留其 L2 PASS；没有任何 positive class 时才按已尝试范围的确定负向/不确定结果判 FAIL/UNRESOLVED。
- 未尝试的 higher class 记 NOT_ASSESSED。higher-class failure 不抹去已经独立建立的 lower class。

reset validity、rule/provenance validity 与科学状态分别记录；V5c 的 reset invalid 不能追溯抹掉合法的 pre-reset 结果。

## 9. Known-answer 实例映射

下表是本提案要实例化的答案，不是已运行的测试报告。每个实例还必须输出完整 ledger 和精确 claim scope。

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
| V5c | V3 pre；J=IDENTITY；handoff 后在 reset 故障变体中改变一个 preserved q 字节 | pre C3 仍有效；reset/L2 INVALID |
| V5d | V3 pre；J=ERASE_EFFECT；合法 reset | C1 payload 不匹配、T 全零；无 positive class；L2 FAIL |
| V5e | V3 pre；J=HALVE_AND_ERASE_LITERAL；合法 reset | C1 不成立、T 为 ±1/2 落入不确定区；无 positive class；L2 UNRESOLVED |
| V5f | V1 pre；J=IDENTITY；合法 reset；只尝试 post C1 | L2 PASS、POST C1；post C2/C3 NOT_ASSESSED |

V4b 不能仅把正常实现的 capability flag 改为 false：实际接口必须与该能力声明一致。建议做一个仅暴露完整 storage 操作的隔离 wrapper，控制器无法拆出 extra ON/OFF；底层没有对该 fixture 暴露隐藏绕路。评估器仍使用正常能力与范围判定路径。

V4.1 的故障对象是 test 内的受测配置，不是把资格测试外层 MANIFEST 自己写坏。外层 bundle 明确授权这个唯一故障；evaluator 对受测配置按生产逻辑拒绝，而不能用 fixture 特判输出 INVALID。

V5c 是预注册负向测试变体。其细节码必须映射到上层认可的 reset-invalid 表达；若实现还没有对应枚举，在 MANIFEST 前明确映射，不能临时冒称已有标准码。细节记录至少包含失败组件、handoff/restored digest 和对应 scope。外层测试期望 INVALID，不能把这样的故障 reset 注册成正常有效 reset。

## 10. 组件接口与可信边界

建议的接口形状（不是实现代码）：

```text
StorageWriter.apply(storage_handle, episode_bytes, frozen_storage_mode)
ExtraWriter.apply(substrate_handle, episode_bytes, frozen_extra_mode)
SyntheticEvolution.apply(state_handles, frozen_J_mode)

Observer.snapshot(read_only_state_handles) -> observed_state + digest
Reader.compute(read_only_substrate_handle, neutral_probe) -> exact_rational
Reset.execute(frozen_reset_profile, preserved_handles) -> new_worker + trace

Evaluator.evaluate(observations, frozen_rules, evidence_identities,
                   attempted_scopes, validity_evidence) -> result + ledger

OracleComparator.compare(actual_result_and_ledger, frozen_expected_oracle)
```

Observer、Reader、Evaluator 三者不能由 writer 的返回值冒充。evaluator 不接收 expected oracle；oracle comparator 不回写 evaluator 的结果。J/Reset 都不能读取 oracle，也不能依 outcome 在多个 profile 之间切换。

正常 schema 错误、缺少测量、缺少 rule、错误 identity 等按各自 scope 的 invalidity 处理；不能为了填表把错误或未执行都映射成科学 FAIL。

Phase A 使用专门的 synthetic 沙箱：不挂载真实 episode、真实 Literal Store 或真实 Afterglow substrate，禁用网络，不继承包含真实状态的目录/句柄。命名空间分开只是记录要求，权限检查才支持访问隔离。

## 11. MANIFEST 应绑定的具体内容

本提案给出了表示、算法、数值和时序选择；落地时仍需把实际产物绑定完整：

1. SPEC hash、实现源码/构建产物 hash、OS/运行时/启动配置。
2. 实际模型文件 hash 与来源；本次 fixture 的模型调用范围及未覆盖项。
3. 状态 schema、字节编码、baseline bytes、STATE/META/VOLATILE 分区、所有 mask。
4. writer、reader、observer、evaluator、J、reset 的 ID/version/hash 与能力边界。
5. 两类 attribution role、delta/contrast/discriminator/persistence/class rules。
6. 完整 fixture bundles、episodes、logical member slots、attempted scopes、expected ledger/oracles。
7. reset table、compatibility witnesses、访问隔离配置和验证办法。
8. 错误码与 scope 映射、资格结果记录格式。

MANIFEST 不包含未来 suite PASS 或自己的 hash；hash 放在 detached 记录。否则容易形成自引用或“冻结后才能产生的结果必须先写入冻结对象”的循环。

先冻结实际 MANIFEST，再由 suite 在第一条 fixture 前捕获 SPEC/MANIFEST hash；结果记录绑定两者。代码或关键规则变化后不沿用旧 PASS。

不同 fixture 采用不同的已列明 mode/rule bundle 是资格套件的固定配置，不是跑到一半修改 MANIFEST。全部变体必须在第一次 qualifying fixture 之前已经绑定。

## 12. 我建议本轮讨论决定的四件事

1. 是否接受 16-byte literal + int64 q/2 作为第一版 synthetic representation。
2. 是否接受固定算术 reader；明确它只验证本测试系统的读路径，不验证 Mistral 集成。
3. 是否接受以独立 observer + 进程替换 + 权限白名单实现第一版 reset。
4. 是否接受 §7 的独立 synthetic evolution J，并区分 persistence 起点与 reset handoff 起点。

前三项旨在降低实现自由度；第四项是本设计覆盖合法 L2 负向出口的关键。我建议优先讨论第四项的语义是否与全船已有约定一致，再进入代码实现和 MANIFEST 实例化。

若采用，我认为第一份工程交付应是可执行 fixture、完整 ledger、实际隔离检查和机器判定结果；其价值在于把 SPEC 的区分真正做出来，而不在于增加一轮新的抽象术语。
