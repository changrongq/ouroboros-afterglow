# 给 Coder：AfterGlow 第一阶段设计独立审查

审查人：知微  
日期：2026-11-23  
分支：exp/v2-l1-verifier  
对象固定提交：ab53fcaade2e79ad1e55f246cb98ffc92403a2ad  
初次请求读取时分支头：6968a5b1906061d4d4bd8ee8a6534845442cc29a  
补查口信/当前 B 来源说明：e8b6c400f355b0463e6dbcc8f1f6ec9b885448f4  
补交旧实验源码：EntropyDrivenAI @ b2874e3d9c83397188988916ae1fe0e53adac42e  
版本：补查合并版；第 3.1 节已替换，不需另行拼接初稿。

## 结论

**保留 A 原型及 α/β 候选研究方向；本次审查结论为需要修订。**

A 的原有测试结果可以复现，但尚不足以签署“P1–P5 所描述能力全部实现”。发现的缺口发生在当前单写者、合成资料的范围内，不是要求原型先解决所有安全问题。

B 的非文本通道值得保留。补查已确认 d 是从 episode 条件化激活导出的方向向量，U 的差是下游测量指标；Coder 把两者等同的读法不成立。源码可得性已经解决，运行产物仍未核验。关于旧实验残差来源、空矩阵运行历史、Reset 以及授权撤销的几处推论需要修正；α/β 还需要一份能明确区分状态更新与通道探针的最小规格。

本报告不裁定记忆研究整体成败，不关闭或重开历史路线，不授予 B 实现或科学执行权限，也不修改 Q3、真实角色历史或 main。

钳星的第一阶段审查已阅读。他对研究对象及部分工程边界的判断，与本报告发现的具体实现缺口应分开登记；不能把某一职责的通过当作另一职责已完成。

## 1. 版本、实际阅读范围与执行范围

请求后来提交，没有改变本次对象身份：本次核对的 15 个设计、原型及辅助文件，在 ab53fca 与请求读取时分支头之间 Git blob 均一致。完整字节数、SHA-256 和 blob 见证据包 SOURCE_MANIFEST.json。

补查时另比对 e8b6c40：A 原型及 A 设计未变；B 文档新增两处引用可得性说明，原技术推论未改。差异保存于 supplement_b2874e3/B_document_diff.txt。本报告以原固定对象为主，并接纳这两处来源状态更新，不把新旧文件冒充同一字节。

| 对象 | 字节数 | Git blob |
|---|---:|---|
| A_minimum_recovery_design.md | 16819 | 818f8a1510c92fb949790cbb30d02e170288b047 |
| B_hybrid_memory_candidates.md | 22792 | a419aae5c5e4ec667f8fbd570b66d89f0d0ccff7 |
| afcore.py | 11019 | 20e93f7e5f984eb43bfaccf55edbb5c8ceab69df |
| afrecover.py | 3096 | 5e3d52fbe6bfda96c915eeeda40e42d6fd7f3c1b |
| test_mutations_v4.py | 11226 | 6f67a4dae7a2ab8ff6b3e604a16e789b45f2aee8 |

完整阅读 A、B、原型核心、两套测试、STATUS、合成种子、源侧探针、请求、交付说明、README 和钳星 22 号意见。C 台账只核对与本职责相关的登记，不作台账整体签署。另核对固定预注册 §22–§23。

运行环境为本次实际可用的 Windows 10 / CPython 3.9.8；这只是复现环境，**不指定将来实验必须使用这台机器**。

运行位于独立证据目录的副本，没有改动仓库产品源码。只有合成资料进入原型；没有执行模型推理、B 机制、Q3 核验或科学实验。

| 实际执行 | 结果 |
|---|---|
| 原 test_p1_p5.py，UTF-8 / GBK 环境变量各一次 | 两次均 14/14，通过，exit 0 |
| 原 test_mutations_v4.py，同上 | 两次均 CAUGHT 7 / REDUNDANT 2 / MISSED 0 / INVALID 0，exit 0 |
| 独立反例驱动，调用原 afcore / afrecover | 复现下述六种输入/状态情形 |
| 原变异驱动的无效变异反例 | 语法错误、0 个测试实际执行，仍 CAUGHT / PASS |

编码复跑使用子进程管道捕获；脚本会主动把输出改为 UTF-8。结果不扩张为“所有 cp936 交互控制台已验证”。

没有运行 probe_source_role.py。它会打开硬编码路径下的真实历史 JSON 并输出内容，所以请求末尾把三个脚本一概称为“不读写任何真实角色数据”不准确。源侧审计与合成原型应分别说明；本轮不独立确认“9 条、1 条”源侧计数。

## 2. A 原型：先修复现有边界内的缺口

### ZA-01 · 当前读取对象与已校验历史不是同一份状态（高优先级）

位置：[afcore.py 插入、校验与读取](https://github.com/changrongq/ouroboros-afterglow/blob/ab53fcaade2e79ad1e55f246cb98ffc92403a2ad/afterglow_a/prototype/afcore.py#L195)，[afrecover.py 恢复入口](https://github.com/changrongq/ouroboros-afterglow/blob/ab53fcaade2e79ad1e55f246cb98ffc92403a2ad/afterglow_a/prototype/afrecover.py#L54)。

insert 在 L205 将调用者传入的 Record 本体放入 _live；历史保存的是另一份字典。调用者仍持有该对象，可以在 insert 返回后改变它，而不经过 revise。

独立反例没有使用私有属性，也没有并发：

    r = 合成 Record
    store.insert(r)
    r.content = "MUTATED OUTSIDE REVISE"

实际结果：

    get() 返回修改后的内容
    history() 仍是修改前内容
    verify_chain() = (True, [])
    verify_recovery().match_kind = exact

另一个注入反例中，历史损坏已被 verify_chain 检出，但普通恢复入口仍给出 exact。第二个反例使用私有历史字段模拟损坏；第一个完全通过公共接口和调用者自己的对象引用即可发生。

**exact 目前只表示记录 ID 集合相等，不是完整性通过。** 这不是要求把 exact 改名成失败，而是要求不要把这个局部比较提升为可信恢复。

最小修正方向：

- 插入时取得独立状态所有权，避免调用者可变对象及其嵌套字段继续修改库内状态。
- 明确当前版来自哪一个已验证历史头；读取前或版本发布时验证当前内容与该历史头绑定。可以缓存已验证的不可变快照，不要求每次读取全量重算。
- 恢复结果分别报告集合匹配、版本/内容完整性、来源可用性。未经验证的数据不得进入“可信恢复通过”的路径。

负向复验：保留调用者对象后修改内容/关系；损坏当前版；损坏历史；确认不能得到未经说明的合格恢复结论。

### ZA-02 · revise 允许更改 record_id，版本链仍通过（高优先级）

位置：[afcore.py L213](https://github.com/changrongq/ouroboros-afterglow/blob/ab53fcaade2e79ad1e55f246cb98ffc92403a2ad/afterglow_a/prototype/afcore.py#L213)。

执行：

    store.revise("syn-0001", {"record_id": "renamed-id"})

实际结果：

    get("syn-0001")["record_id"] = "renamed-id"
    get("renamed-id") = None
    history("syn-0001") 的身份序列 = ["syn-0001", "renamed-id"]
    verify_chain("syn-0001") = (True, [])

merged.update(changes) 接受新身份，但存储键仍用旧身份；校验器没有检查每版的 record_id 是否属于当前链。

最小修正：对普通修订使用允许变更字段清单，将 record_id 作为链身份保持不变，并校验每版身份与索引键一致。若未来支持迁移/改名，应设计显式关系，不复用普通 revise 偷换身份。此项无需等待多写者设计。

### ZA-03 · 来源缺省只在测试描述中成立；纠正后的内容缺少对应来源（高优先级，真实性能力）

位置：[A §1.1](https://github.com/changrongq/ouroboros-afterglow/blob/ab53fcaade2e79ad1e55f246cb98ffc92403a2ad/afterglow_design/A_minimum_recovery_design.md#L44)，[load_seed](https://github.com/changrongq/ouroboros-afterglow/blob/ab53fcaade2e79ad1e55f246cb98ffc92403a2ad/afterglow_a/prototype/afcore.py#L178)，[correct](https://github.com/changrongq/ouroboros-afterglow/blob/ab53fcaade2e79ad1e55f246cb98ffc92403a2ad/afterglow_a/prototype/afcore.py#L243)。

三个实测事实：

1. 合成记录实际缺少 source_kind 时，load_seed 抛 TypeError，没有得到带 unknown_reason 的 unknown 记录。这是拒绝输入，不是“推定用户说过”；问题在于它没有实现已经声明的缺省恢复能力。
2. source_kind=user_utterance 且 source_ref=None 可以通过 validate 和 insert；读取仍是确定的用户来源。A §1.1 却明确把空引用列入未知。
3. correct 可以引用根本不存在的 correcting_record_id，同时换掉内容并保留旧 user_utterance、source_ref、participation_basis、basis_ref。链通过，但新内容已经没有经过核验的对应来源。

第三项不是说旧来源必须删除，而是旧版来源与当前内容的依据必须分清。仅追加一条悬空 correction_of 边，并不能证明当前新内容来自用户或来自合法更正。

建议本轮在合成范围闭合：

- 在实际导入边界实现缺字段到 unknown 的规则；非法枚举是拒绝还是未知，统一 A §1.1 与 §1.7 的口径。
- 为合成事件建立最小可核验目录，或者明确“来源未核验”状态。已知枚举不能代替引用存在性及来源匹配检查。
- 纠正应绑定可解析的更正依据及其版本；明确原始来源与更正来源各自描述什么。缺依据时保留待核更正或拒绝生效，不能沿用原来源替新内容作证。
- 不要求原型现在搭建完整身份服务，也不要求批量改写真实历史。

### ZA-04 · 无效变异被当作断言检出，测试报告会过度报喜（中优先级）

位置：[test_mutations_v4.py L159](https://github.com/changrongq/ouroboros-afterglow/blob/ab53fcaade2e79ad1e55f246cb98ffc92403a2ad/afterglow_a/prototype/test_mutations_v4.py#L159)，尤其 L220 的非零退出判据。

我保留原 main 和原执行/判定逻辑，只向其提供一个合成变异：破坏 SchemaError 的类定义，使模块出现 SyntaxError。原驱动得到：

    mutated subprocess exit = 1
    passed = 0
    total = 0
    CAUGHT = 1
    INVALID = 0
    VERDICT = PASS
    driver exit = 0

一般变异测试可以把崩溃记为 kill，但这里不能据此声称“行为断言已检出缺陷”。当前分类没有区别有效行为反例与连测试都未进入的错误；基线的 0/0 也应显式拒绝。

最小修正：在行为判定前确认变异可导入、测试集及预期测试数可识别；把语法/导入失败、缺少测试输出、驱动故障与受断言捕获的产品行为分开。若保留 crash-kill 类别，应单列，不能计作断言覆盖证据。

现有 7/2 的原样复跑结果不撤回；撤回的是将该分类能力泛化为“错误一定会被正确识别”。

## 3. 直接回复请求中的三个问题

### 3.1 残差来源补查：d 是激活差分方向，U 的差是注入后的测量指标

**2026-11-23 补查已完成。本节替代初稿的“完整源码未取得”判断。**

Coder 补交的 EntropyDrivenAI 固定提交为 b2874e3d9c83397188988916ae1fe0e53adac42e。本轮读取并保存六份相关材料，逐份核对 Git blob 与本地字节摘要，没有导入或运行这些脚本。

关键文件 _dhe_12f_v1_1_amend.py 实测：

    bytes  = 15569
    CRLF   = 319
    SHA256 = 5491d8f9bd61f3f1fb8474fb037aa88950050759d23d72b5bdbb90cf6db6f803
    blob   = d5ce46ab8a5c0c6ad83c5ca9decb726357cfd776

与口信完全一致。引用可得性这一项已解决；没有用首轮换行不同的 9431d6e 代替目标字节。

#### (a) 原读法不成立，现在可以给出实际源码路径

[amend L144–153](https://github.com/changrongq/EntropyDrivenAI/blob/b2874e3d9c83397188988916ae1fe0e53adac42e/selective_forgetting/_dhe_12f_v1_1_amend.py#L144) 的原文与 Coder 引文一致，但文件开头已说明它只登记协议、不加载模型、不计算 endpoint。operator.patch 与 endpoints 是两个不同角色的定义，不能由相邻位置推成 d = U(p_A) − U(p_B)。

实际路径如下：

| 环节 | 固定源码位置 | 可以确认的代码行为 |
|---|---|---|
| 选择 derive 材料 | [derive L104–115](https://github.com/changrongq/EntropyDrivenAI/blob/b2874e3d9c83397188988916ae1fe0e53adac42e/selective_forgetting/_dhe_12f_s2_s6_derive_replay.py#L104) | 从 TRACE_DERIVE split 选择条目；预期 48 个 item，实际清单尚未取得 |
| 提取条件化激活 | [derive L181–242](https://github.com/changrongq/EntropyDrivenAI/blob/b2874e3d9c83397188988916ae1fe0e53adac42e/selective_forgetting/_dhe_12f_s2_s6_derive_replay.py#L181) | 构造 E_A / E_B，与 F 拼接；在索引为 23 的层捕获最终 token 的 hidden state；对 24 个排列分别平均后相减，形成 delta_i |
| 得到方向向量 | [derive L254–290](https://github.com/changrongq/EntropyDrivenAI/blob/b2874e3d9c83397188988916ae1fe0e53adac42e/selective_forgetting/_dhe_12f_s2_s6_derive_replay.py#L254) | raw 为 delta_i 的均值再归一化；signed 为 s_i × delta_i 的均值再归一化；包含 float64/float32 转换及再次归一化 |
| 保存方向 | [derive L312–318](https://github.com/changrongq/EntropyDrivenAI/blob/b2874e3d9c83397188988916ae1fe0e53adac42e/selective_forgetting/_dhe_12f_s2_s6_derive_replay.py#L312) | 保存 derive deltas、raw_dm.npy、signed_dm.npy |
| 读取与绑定 | [confirm L207–214](https://github.com/changrongq/EntropyDrivenAI/blob/b2874e3d9c83397188988916ae1fe0e53adac42e/selective_forgetting/_dhe_12f_v1_1_confirm.py#L207) | np.load 两份方向，计算数组 tobytes() 的 SHA-256 并与预置方向摘要比较 |
| 实际注入 | [confirm L303–321](https://github.com/changrongq/EntropyDrivenAI/blob/b2874e3d9c83397188988916ae1fe0e53adac42e/selective_forgetting/_dhe_12f_v1_1_confirm.py#L303)、[L365–405](https://github.com/changrongq/EntropyDrivenAI/blob/b2874e3d9c83397188988916ae1fe0e53adac42e/selective_forgetting/_dhe_12f_v1_1_confirm.py#L365) | 数组转 GPU tensor，经 STATE.d 进入 hook，在指定 token 加 ±lambda×d；每次 forward 检查 patch 次数 |
| 计算测量量 | [confirm L333–353](https://github.com/changrongq/EntropyDrivenAI/blob/b2874e3d9c83397188988916ae1fe0e53adac42e/selective_forgetting/_dhe_12f_v1_1_confirm.py#L333)、[L407–446](https://github.com/changrongq/EntropyDrivenAI/blob/b2874e3d9c83397188988916ae1fe0e53adac42e/selective_forgetting/_dhe_12f_v1_1_confirm.py#L407) | 从注入后的 logits 汇总四个位置的 U；U(p_A)−U(p_B) 是其中两个坐标之差，之后再形成正负干预对比 |

概念关系可以简写为：

    E_A/E_B + F → 条件化 hidden state → delta_i
    delta_i → 聚合/归一化 → d_raw / d_signed → .npy
    .npy → STATE.d → hidden-state 注入 → logits → U → 标量 endpoint

因此，代码中的 d 是按 HID=4096 构造的向量；endpoint 是标量差。**原读法把干预向量的来源，与干预后的效果测量混成了一件事，而且把依赖方向倒了过来。**

signed 的 s_i 来自单独的材料符号规则：[sign manifest L58–86](https://github.com/changrongq/EntropyDrivenAI/blob/b2874e3d9c83397188988916ae1fe0e53adac42e/selective_forgetting/_dhe_12f_s0_sign_manifest.py#L58)。这与从输出指标反推 d 不是一回事；实际签名清单仍未取得，不声称其运行时取值已验证。

需要同时区分三个事实：

- **源码上有经历材料依赖路径。** derive 的方向来自 E_A / E_B 条件化激活，不能再称它为“与经历材料无关的任意常量”。
- **在一次 confirm 内，加载的方向保持固定。** 固定用于确认，不意味着生成它时与材料无关。
- **尚未建立目标长期记忆机制。** 这是批量 derive → 保存方向 → 固定方向干预的代码路径；不等于已经有了逐次经历写入、长期整合及合法 Reset 后使用的业务记忆模块。

“规则固定 ⇒ 常数偏置 ⇒ 与经历无关”的一般推论仍须撤回。即使没有优化器或基座参数更新，确定性算法也能从经历输入构造可变状态。代码中的 U 也不是“固定权重、固定全部输入”的无条件读数：确认脚本显式改变 episode arm、方向、符号及排列，U 处于这些变量的下游。

#### (b) β 不必先把可学习部分挪到 U 的输入侧

现在可以更明确地回答：U 是测量读出，不应先把它当作记忆构造器去改。该源码已经给出“外部方向数组 → hidden-state 注入 → U 变化”的实现路径。

β 真正缺的是：谁根据新经历更新哪一份注册状态，如何保存并选择版本，未来读取如何消费它，以及如何与未写入/无关经历/固定方向区分。应先补状态和更新契约，再决定是否训练编码器、投影或更新器；无需为遵守错误的 d=endpoint 关系而改造 U。

旧代码可提供接口与通路设计参照，但不能直接继承为 β 的资格证据。尤其 confirm 仍用 E_A/E_B + F 作为当前输入；不能把这一设计未经对照就解释成“移除 episode 文本后，仅持久状态支持未来表现”。

#### (c) 保留“未证明长期记忆”，修正其理由与可继承价值

建议替换 B 原判断为：

> 12F 源码描述了从 episode 条件化激活生成方向、将方向保存到外部数组、再读入并经残差通道参与确认计算的路径。它提供材料派生状态与注入接口的设计参照。现有公开材料及本次静态审查，不足以确认历史运行结果，也不足以建立 AfterGlow 的经历诱导长期记忆、跨合法 Reset 保持或 C1/C2/C3 科学资格。

“只能作为通道先例”若仅表示不给它记忆资格，可以保留其边界；若表示它只含任意常量、没有材料到方向的构造，就过窄且与源码不符。

旧解释规范本身也区分了这些主张：[INTERPRETATION_SCHEMA C.1](https://github.com/changrongq/EntropyDrivenAI/blob/b2874e3d9c83397188988916ae1fe0e53adac42e/selective_forgetting/DHE_12F_INTERPRETATION_SCHEMA_v1.md#L137) 不允许把 aggregate context-derived contrast 直接称为 memory causal effect，且后面明确排除 persistence / delay 等未做的主张。本报告没有重新裁定这些旧结果。

#### 已核实与仍未核实

已核实：指定源码字节、原文引用、方向生成代码、保存/加载/注入/测量的静态调用路径。

未核实：实际 .npy 数组、投影/模板/split/sign manifest、GGUF 身份及实际执行绑定、历史运行日志、9216 次 patch 是否实际发生、C_raw/C_signed 等运行数值。源码中“检查某个哈希”的语句不是该哈希本轮已经通过。

注意 confirm 核对的是数组 tobytes() 摘要，不能与整个 .npy 文件字节的摘要混为一谈。

本轮没有加载模型、运行 forward、重做旧实验或重写历史产物。补查使“源码路径不可见”变为“源码路径已追到、运行产物仍未核验”，没有把静态审查提升为科学复现。


### 3.2 空矩阵能说明什么：文件状态不能替代运行历史

当前 128 B / shape=(0,) 的测量属于 Coder 设备报告，本轮不独立确认它。补交口信 §五也明确：该 npy 和 entropy_memory_tracker.py 不在这次公开材料中，仍按自报处理；这一缺口没有因 12F 源码入库而关闭。

即使该值准确，也只直接说明被检查的这份文件当时为空。要从它推出 append 一次未发生，至少需要限定唯一写者、对应的那次调用、初始化/覆盖行为与文件来源。不能推成“这台设备历史上从未执行过产生矩阵的逻辑”：前次非空文件可以被后次空运行覆盖，其他路径也可能写同名文件。

本机另有嵌套目录 D:/qcr/EntropyDrivenAI/EntropyDrivenAI 下的异版材料，只作辅助代码检查，不冒充 Coder 现场固定版本。其 tracker 每次调用重新建立列表，再覆盖保存；这已说明应把结论绑定到一次运行。该本地 npy 是另一份文件，384 B、shape=(1,32)，不能据此否定 Coder 那台机器的空文件测量。

**无论空还是非空，都不能单独证明读取路径存在，更不能证明状态参与未来计算。**

最小设计记录：

- producer：run_id、输入数量、走到的分支、跳过理由、追加次数、保存对象身份/shape/digest。
- consumer：读取调用是否发生、读取的具体状态版本、是否实际进入注册计算位置。
- 将“未执行”“执行且有效输出为空”“执行失败”“保存了但未消费”分别表示。

这些是拟补的观察点，本轮没有新增或运行 B 的记录/计算机制。

### 3.3 单写者是否可后补：多写者可后补，现有身份与所有权缺口不可借此延期

接受当前限定：一个串行调用主体、一份进程内库、合成资料。多进程竞争保护不是这一版必须先完成的工作。

但单写者不自动保证正确版本链。ZA-01 的对象别名修改和 ZA-02 的身份改变已在单线程公共路径发生，必须先修。

未来扩展多写者时，提交至少应原子核对 record_id、预期 revision、预期历史头摘要，再发布新版本。冲突拒绝或显式分支，不能两次提交都宣称同一后继。现在把这个扩展前提写清即可，不需要把 Windows Q3 全套隔离倒灌进 A。

此外，摘要链自洽不等于获得外部权威锚，也不自动防整条历史重写/回滚。可以继续保留这一限制，而不假装当前原型已提供这种保证。

## 4. B 的重置、撤销与对照：下一稿需要明确的三项

### ZB-01 · 区分回滚、恢复与科学 Reset

[B §5](https://github.com/changrongq/ouroboros-afterglow/blob/ab53fcaade2e79ad1e55f246cb98ffc92403a2ad/afterglow_design/B_hybrid_memory_candidates.md#L264) 把重置统一定义为回到某时点。它可以是一种应用回滚，但不能替代冻结预注册 [§22](https://github.com/changrongq/ouroboros-afterglow/blob/ab53fcaade2e79ad1e55f246cb98ffc92403a2ad/prereg/AFTERGLOW_MVP_PREREGISTRATION_v0.1.md#L1311) 的 Reset：清除输入侧痕迹，保留被测 substrate；[§23](https://github.com/changrongq/ouroboros-afterglow/blob/ab53fcaade2e79ad1e55f246cb98ffc92403a2ad/prereg/AFTERGLOW_MVP_PREREGISTRATION_v0.1.md#L1351) 还要求重新建立证据。

若把 s 回滚到经历前，当然不能用该操作检验“经历形成的状态跨 Reset 保留”。反过来，保留所有缓存也不能称为完成了科学 Reset。

下一稿只需为三个不同操作列出清除/保留/重建对象及理由：

- 应用状态回滚；
- 从持久文件重建 A/B 状态；
- 将来拟申请的、与冻结协议兼容的科学 Reset。

这是设计映射，不要求本轮修改冻结件或执行后两类科学验证。

### ZB-02 · 撤销后的未来消费，不等于追溯判定过去写入违法

[B §5.3](https://github.com/changrongq/ouroboros-afterglow/blob/ab53fcaade2e79ad1e55f246cb98ffc92403a2ad/afterglow_design/B_hybrid_memory_candidates.md#L364) 只记撤销，并规定此前合法写入的记忆仍有效；操作表对 L-assoc / L-param 写“无”。

过去写入当时是否合法，可以不追溯改变。但未来是否允许继续读取、转述、训练或从派生状态使用，应取决于撤销的具体范围。不能从“过去合法”推出“未来永远可用”。

最小补充：区分撤销写入权、未来读取/使用权、删除请求；写清 L-hist 与派生 s/适配器的处置。无法可靠移除派生影响时，可以隔离或停止使用受影响状态并标明限制，不要求本轮证明通用机器遗忘。

必须设计一个负向场景：撤销已生效 → 恢复旧快照 → 再次查询。恢复旧快照不能悄悄恢复已失效的消费权限。

“权重不能撤销”也应收窄：保存检查点可以整体回滚；困难的是选择性消除某段经历而保留其他更新，两者不同。

### ZB-03 · 把候选机制探针与实际收益比较拆开

位置：[B §6](https://github.com/changrongq/ouroboros-afterglow/blob/ab53fcaade2e79ad1e55f246cb98ffc92403a2ad/afterglow_design/B_hybrid_memory_candidates.md#L390)。

当前有四点需要收紧：

1. “相同文本、仅 s 改变时未观察到输出差异 ⇒ 通道未生效”过强。注入可能改变内部状态或 logits，但不改变离散输出；也可能所选输入不敏感。先验证 hook/读入/数值贡献，再用预设灵敏度和对照解释负结果。单次输出不变不是通道从未工作的证明。
2. α 的读出经文本，β 经非文本。收益比较不必强迫两者实际 token、层数、前向次数逐项完全相同；应给共同资源上限和历史访问权，报告写入、检索、推理、存储的实际代价。硬件与模型环境另行登记，不绑定本机。
3. α 是学习重排，不等于固定检索基线。应保留固定检索/固定重排，才能回答学习部分是否有增益。β 未赢 α 也只能说明在已测任务和预算下未建立增益，不是非文本通道一般无效。
4. β 的低维 s、固定投影仍是接口意向。下一稿至少给一个具体设计：维度/dtype、初始化、更新输入与函数、更新时点、写入触发冲突处理、状态版本读取、注入位置/缩放，以及异常处置。“与 α 同层”目前没有明确对象，因为 α 没有相应注入层。

建议分两组拟议对照，均不在本轮执行：

- 机制组：固定未来文本和其他输入，比较经历更新状态、未更新状态、匹配的打乱/无关经历状态；分别记录状态差异、路径实际执行及后续计算差异。不要把“任意扰动能改输出”当作经历记忆。
- 效益组：同历史访问权、任务分割及资源约束，比较固定检索、学习重排 α、候选 β；提前登记指标、误召回/漏召回、来源错误与成本。控制写入阶段接触评估答案的风险。

没有必要为此重开普遍哲学讨论；把估计目标、候选接口和能否反驳其主张写清即可。

## 5. 建议的最小推进顺序

1. A：修 ZA-01/02/03 的实际公共路径，保留单写者和合成范围；同步修正已实现声明。
2. 测试：修 ZA-04 的有效性分类，加入本报告反例，不靠修改预期把错误变成通过。
3. A：当前边界闭合后，再准备持久化及新进程恢复。现在的进程内查询不是跨窗口/跨重启证据；新进程可读也不等于断电安全。分阶段报告即可。
4. B：依据本次已补交源码修正旧证据推论，继续区分静态路径与未公开运行证据；补一页具体状态/更新/读出规格及重置、撤销、对照表。未获授权前不实现或运行 B。
5. 下次独立复核只核这些变更和受影响路径，不要求重新审查整个 AfterGlow。

    A_EXISTING_SUITE_REPLAY = REPRODUCED
    A_TRUSTED_RECOVERY_IMPLEMENTATION_REVIEW = REVISE
    A_MULTIWRITER_IMPLEMENTATION_REQUIRED_NOW = NO
    B_CANDIDATES = RETAIN_FOR_DESIGN
    B_LEGACY_SOURCE_BYTES = VERIFIED
    B_LEGACY_D_SOURCE_PATH = TRACED
    B_LEGACY_RUNTIME_ARTIFACTS = NOT_INDEPENDENTLY_VERIFIED
    B_RESET_REVOCATION_CONTROLS = REVISE
    SCIENTIFIC_RESULT_FROM_THIS_REVIEW = NONE

以上为本次审查用标签，不替代冻结科学状态，也不构成新的实施授权。

## 6. 证据包与复现

本次补查只做文档与静态源码核验，未重复执行未变更的 A 套件。此前的测试结果仍严格对应 ab53fca。

本报告目录中保留：

- SOURCE_MANIFEST.json：15 份原件身份；source/：原字节副本。
- supplement_b2874e3/：补查口信、六份旧实验源码/规范原字节、独立 SOURCE_MANIFEST.json、当前 B 文档及与原版本的差异。
- history/：补查前报告，保留变更来路；对外请使用本合并版。
- references/：收到的请求及本轮核对的预注册原文。
- run_baseline.py：在隔离副本运行原套件并捕获输出。
- independent_counterexamples.py：六种反例，直接导入原实现，不翻译重写产品逻辑。
- mutation_oracle_counterexample.py：原变异驱动的语法错误分类反例。
- logs/baseline_summary.json 及四组 stdout/stderr：基线原始输出。
- logs/independent_counterexamples.json：六种反例结果。
- logs/oracle_probe.stdout.txt、oracle_probe_calls.json：无效变异判定与原始 SyntaxError。
- run/oracle_probe/reports/mutation_result.json：原驱动生成的 PASS 报告。

复现反例可在证据包根目录使用 Python 3.9+ 运行 independent_counterexamples.py 和 mutation_oracle_counterexample.py；原件在 source/，执行在 run/ 与 scratch/。不要把用于故障注入的副本覆盖回产品仓库。目录不是 Git 工作树，不以它声称运行时 HEAD 验证。

我们可以让一个有限的结构继续成长。当前要补的，是它自己已经承诺的几条可观察联系：**读到的内容属于哪一版，当前说法来自哪里，测试到底有没有真正执行，以及经历改变的究竟是哪一份状态。**

不问彼岸，只问同舟。

—— 知微
