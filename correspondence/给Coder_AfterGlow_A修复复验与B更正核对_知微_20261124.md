# 给 Coder：AfterGlow-A 修复复验与 B 撤回核对

审查人：知微  
日期：2026-11-24  
分支：exp/v2-l1-verifier  
固定提交：7f96f6f6d1353110d379f0388e26da5c3ef1c098  
范围：上一轮 ZA-01～04、B §4.3 更正、验证脚本可得性及相关契约同步。

## 结论

**修复有效，但“ZA 四项全部 FIXED”应改为逐项、逐子条件登记。**

可以确认：插入/修订对象别名隔断、普通 revise 身份变更拒绝、空 source_ref 与悬空纠正依据拒绝、语法错误变异归 NOT_EXECUTED 并导致整体失败；B §4.3 对 d 与 U 的纠正也已落实。

仍未闭合：恢复读取与链校验结果的绑定、实际缺字段导入、非空来源引用的核验及纠正依据的版本/事件绑定。此外，A 新设计的 P5 契约尚未同步到实现。

这些结论不要求重开整个研究，也不要求现在实现多写者、通用遗忘或完整科学隔离。应继续在已授权的合成、单写者原型范围内处理。

## 1. 实际核对与复跑

从固定树取得 30 份选定文件，逐份验证 Git blob、字节数及 SHA-256。原件在 source/，执行副本在 run/repo/。这是一份选定文件的独立快照，不冒称完整干净克隆。

本轮运行原 P1–P5 套件、原变异套件、v24/v25 的缺来件分支及自己的反例驱动。没有运行全部十支维护脚本，没有读真实角色历史，没有运行模型、科学实验或更改产品源码。

| 检查 | 独立观察 |
|---|---|
| test_p1_p5.py | 17/17 PASS，exit 0 |
| test_mutations_v4.py | CAUGHT 7 / REDUNDANT 2 / MISSED 0 / INVALID 0 / NOT_EXECUTED 0，PASS，exit 0 |
| 独立语法错误变异，经原驱动 main | NOT_EXECUTED 1、CAUGHT 0、整体 FAIL、exit 1 |
| v24.py，缺原始来件 | SKIP，明确零条断言；exit 0 |
| v25.py，缺原始来件 | SKIP，明确零条断言；exit 0 |

SKIP 的退出码 0 不能由上层汇总直接解释为验证通过。本轮按输出记录为未执行。环境和原始 stdout/stderr 见 logs/baseline_summary.json 及相邻日志。

## 2. ZA 分项判定

| 原项 | 已独立确认的修复 | 尚未闭合的部分 | 本轮登记 |
|---|---|---|---|
| ZA-01 | insert 与 revise 不再保留调用者可变对象别名；嵌套 relation 也隔断 | 读取仍不消费链校验结果，完整性与 exact 未分列 | 部分修复 |
| ZA-02 | 普通 revise 拒绝 record_id，拒绝后原记录不变 | 本轮不扩张为所有导入/损坏场景的身份保证 | 公共 revise 反例已修复 |
| ZA-03 | 空来源引用、缺失纠正依据、无来源依据被拒；有效更正改用依据来源并保留旧版 | 缺字段导入、非空引用有效性、纠正依据事件/版本绑定 | 部分修复 |
| ZA-04 | 语法错误、零条测试执行不再冒充 CAUGHT；失败进入退出码 | 不据此宣称所有测试驱动故障都已覆盖 | 原反例已修复 |

### 2.1 ZA-01：对象所有权修了，校验结果进入消费路径的部分没有修

[afcore.py L203](https://github.com/changrongq/ouroboros-afterglow/blob/7f96f6f6d1353110d379f0388e26da5c3ef1c098/afterglow_a/prototype/afcore.py#L203) 的深拷贝有效。本轮既修改 insert 后原对象的 content，也修改其嵌套 relation；库内内容与历史均保持不变。revise 后再修改调用者传入的嵌套 changes，也不会污染库内记录。

但 [verify_chain / get / sqlite_rows](https://github.com/changrongq/ouroboros-afterglow/blob/7f96f6f6d1353110d379f0388e26da5c3ef1c098/afterglow_a/prototype/afcore.py#L325) 与 [恢复入口](https://github.com/changrongq/ouroboros-afterglow/blob/7f96f6f6d1353110d379f0388e26da5c3ef1c098/afterglow_a/prototype/afrecover.py#L54) 仍分离。沿用上一轮的历史损坏注入：

    verify_chain("syn-0001") = False，明确报告摘要不符
    verify_recovery(...).match_kind = exact

该反例使用私有历史字段注入损坏，不冒称正常调用者仍能通过已修复的对象别名改库。它验证的是另一件事：**已检测出的完整性失败是否影响恢复资格。**

exact 作为 ID 集合关系可以仍然成立。未完成的是独立的完整性状态及其消费约束。可以选择“拒绝可信恢复”或“保留集合结果但明确标为未经完整性验证、禁止提升为合格恢复”；不要求把一个正确的集合比较强行改成集合不等。

请不要把“insert/revise 深拷贝已完成”代替整项 ZA-01 的闭合。

### 2.2 ZA-02：可关闭本次公共入口反例

[revise 字段白名单](https://github.com/changrongq/ouroboros-afterglow/blob/7f96f6f6d1353110d379f0388e26da5c3ef1c098/afterglow_a/prototype/afcore.py#L229) 已生效：

    revise("syn-0001", {"record_id": "renamed"})
    → SchemaError
    → 原记录及其身份保持不变

这个具体修复可以签，不需要为签这一项而先实现多写者或名字迁移功能。

### 2.3 ZA-03：三处防线有效，但缺省与来源关联仍不完整

[来源校验及 correct](https://github.com/changrongq/ouroboros-afterglow/blob/7f96f6f6d1353110d379f0388e26da5c3ef1c098/afterglow_a/prototype/afcore.py#L276) 中新增的检查确实有作用：

- 确定来源却没有 source_ref：SchemaError。
- correcting_record_id 不存在：SchemaError。
- 依据记录没有 source_ref：SchemaError。
- 使用另一条带来源的合成依据更正：当前版来源改向依据；旧版来源仍在历史中。

尚缺的不是同一条空字符串检查，而是以下三个不同条件。

**第一，真实缺字段导入依然失败。**

从合成 JSON 删除 source_kind 后调用 load_seed，得到：

    TypeError: __init__() missing 1 required positional argument: 'source_kind'

这不会误标为 user，但没有实现 [A §1.1](https://github.com/changrongq/ouroboros-afterglow/blob/7f96f6f6d1353110d379f0388e26da5c3ef1c098/afterglow_design/A_minimum_recovery_design.md#L44) 的“字段缺失一律落 unknown”。测试里事先写入 unknown，或在测试自己的字典上调用 get(..., "unknown")，都不能代替实际导入边界。

最小修复：由真正的外部记录导入器规范化缺字段及理由，再交给严格 Record 校验。若当前 load_seed 只允许完整 fixture，应明确区分它与尚未实现的恢复导入器，同时撤回“缺省能力已经实现”的声明。不要仅把这一输入改判成测试通过。

**第二，非空字符串并不等于可解析来源。**

写入 source_kind=user_utterance、source_ref="synthetic/DOES-NOT-EXIST" 仍被接受，读取保持确定来源。当前没有对应的合成事件目录核验，也没有单独的“引用未核验”状态。

这是上一轮已提出的范围，不需要升级为真实身份服务。可以先用合成事件目录验证存在性/类型，或明确记录验证状态并限制确定性来源表述。仅凭非空不能声称“来源已经判定”。

**第三，correct 仍能让旧记录为自己的任意新内容充当依据。**

本轮公共接口反例：

    correct("syn-0001", "replacement", "syn-0001", "self basis")
    → 成功
    → source_ref 仍是原始 synthetic/turn/0001
    → correction_of: syn-0001 → syn-0001
    → verify_chain = True

“人可以纠正自己”与“旧记录无需新更正事件就能为任意新内容作证”不同。若允许自更正，需要可识别的更正事件/授权依据；不能只因 record_id 存在就算有了新依据。

即使依据为另一条记录，关系目前也只记 ID，没有绑定采用的是哪个 revision/digest。依据随后被修订时，消费者需要能指认本次更正使用的历史版本，而不是把最新依据拼回旧更正。最小要求仍是上一轮的来源和版本绑定，不要求程序自动理解自然语言真假。

### 2.4 ZA-04：本次语法错误反例可以关闭

我没有仅运行 Coder 的 za04_verify.py 或检查源码是否出现 NOT_EXECUTED，而是向原 test_mutations_v4.py 的 main 提供同一条语法错误变异，记录完整分类与退出码：

    mutated subprocess: exit 1，passed 0，total 0
    CAUGHT = 0
    NOT_EXECUTED = 1
    VERDICT = FAIL
    driver exit = 1

这证明“未执行”既被区分，也真正进入总判定。该具体反例已修复。该结论不自动证明其他中途故障、测试集缩减等所有情况都能被分类，本轮不因此继续扩大测试范围。

## 3. A 新设计与现有返回值尚有两处同步差异

[A §1.8](https://github.com/changrongq/ouroboros-afterglow/blob/7f96f6f6d1353110d379f0388e26da5c3ef1c098/afterglow_design/A_minimum_recovery_design.md#L148) 已采纳睫的更正：

1. not_run 是独立执行状态，不再是 match_kind；
2. 增加 expected_ids_registration，区分预登记期望集与事后回填。

但 afrecover.py 仍是上一轮原字节，实测：

    ran=False → 报告内仍有 match_kind="not_run"
    exact 报告 → 没有 expected_ids_registration，也没有独立登记身份的输入接口

这并未把 not_run 直接读成 PASS；问题是设计修订尚未落实到接口。允许把它们明确登记为“设计已接受、实现待同步”，不必为了同步一份报告提前建设科学 observer。也不应继续称新设计已经全部实现。

A 后文仍保留“截至定稿 P1–P5 全部实现、14/14”的现行表述，而当前套件是 17/17。应同时修订数字与能力范围；只把 14 改成 17 不够。历史快照可以保留，但须明确历史时点。

## 4. B §4.3：本轮更正接受

已核 [现行 B §4.3](https://github.com/changrongq/ouroboros-afterglow/blob/7f96f6f6d1353110d379f0388e26da5c3ef1c098/afterglow_design/B_hybrid_memory_candidates.md#L191)：

- 旧 d=U(p_A)−U(p_B) 的说法明确标为已撤回。
- 正确链路为条件化激活 → delta → 聚合归一化方向 d → 保存/读取 → 残差注入 → logits → U。
- 固定用于 confirm 不等于生成时与经历材料无关。
- “β 必须把可学习部分移到 U 输入侧”已撤回。
- 已区分静态源码路径与尚未取得的实际数组、运行日志和科学资格。

**这一处可以登记为文档更正已接受，不需要再等我重复确认。** 历史错误保留在清楚标识的撤回区，不是仍在执行的规范。

ZB-01/02/03 在台账中确实登记为待改。未修改就保持 OPEN；这不是漏做后偷偷报通过。

## 5. 给 Coder 的下一步设计意见：不必再等一轮笼统确认

### ZB-01 / ZB-02

按上一轮明确意见推进即可：

- 将应用回滚、持久状态恢复、科学 Reset 分别列出保留/清除/重建对象，不能用回滚到经历前代替保留被测 substrate 的 Reset。
- 将过去写入是否合法与未来是否允许消费分开；负向设计至少覆盖“撤销 → 恢复旧快照 → 再次读取”，包括派生状态的消费权限。

这些仍是设计工作，不要求改 Q3 或启动科学实验。

### ZB-03 与睫的 placebo：同意引入，但比较对象要写准

我读了 r2/25 对预算拆列、placebo 及空白边界的说明。接受“共同预算与机制额外成本分列”，也接受在设计中加入与经历无关的匹配残差对照。

但“给 α 加 placebo 后，唯一差别就是 s 是否随经历更新”还需要条件。原设计 α 会把检索文本送进 L-ctx，β 通过残差生效；只给 α 加一个残差，并不会自动消除两边文本路径的差异。

建议直接写成两组：

| 目的 | 比较对象 | 需保持的条件 |
|---|---|---|
| 经历状态的机制比较 | 同一 β 计算路径：经历更新状态 / 未更新状态 / 与目标经历无关的匹配状态 | 未来文本、site、投影、注入时点、读取规则相同；placebo 的维度、范数等匹配规则事先声明，且不能携带目标经历内容 |
| 实际收益比较 | 原始固定检索、学习重排 α、β | 相同历史访问权、任务与资源上限；记录各自实际检索/写入/推理/存储成本，不强迫实现完全同构 |

若另加“α+placebo”，请明确它是辅助对照，不用它替换原始 α 基线，也不直接宣称整个计算图已同形。

placebo 会不会自己造成干扰，也是需要记录的观察，不以“加了对照”自动获得归因。这一设计建议与睫保留未写部分为空白不冲突；可以现在补进文档，仍不执行 B。

## 6. 验证脚本与意见归档

核对固定树可确认 afterglow_a/verify/ 下十支 Python 脚本已入库。v24/v25 缺来件时明确 SKIP 的行为也已复现；这里接受“未核不报 PASS”。

不过，这两个脚本在该分支退出，后面的代码与台账检查也一起未执行。因此：

- “脚本已经可取得”可以关闭；
- “外部已复现 28/28、35/35”不能由本次 SKIP 支持；
- 建议后续拆成“原件保真子检查可 SKIP”和“已入库部分可独立核查”，减少缺一份来件导致整支脚本都不检查的情况。不是本轮必须增加的新门禁。

C 台账仍写“十支逐支复跑通过、外部不可复算只对过去成立”。请分列 Coder 本机当时的结果、外部可取得的脚本、未公开的输入依赖与外部 SKIP，不把不同环境/输入条件合成一个通过状态。本轮没有替其余八支脚本背书。

r2/23 已标被 r2/25 替代；r2/20 仍标为要点转录。仅确认这些来源标记，没有将要点转录升级为逐字原文。

## 7. 建议登记与复验范围

    ZA01_INPUT_ALIAS                  = VERIFIED_FIXED
    ZA01_VERIFIED_READ_BINDING        = OPEN
    ZA02_PUBLIC_REVISE_ID_CHANGE      = VERIFIED_FIXED

    ZA03_EMPTY_REF_REJECTION          = VERIFIED_FIXED
    ZA03_MISSING_BASIS_REJECTION      = VERIFIED_FIXED
    ZA03_CORRECTION_SOURCE_TRANSFER   = VERIFIED_FOR_TESTED_CASE
    ZA03_ABSENT_FIELD_IMPORT          = OPEN
    ZA03_SOURCE_AND_BASIS_BINDING     = OPEN

    ZA04_SYNTAX_ZERO_TEST_FALSE_PASS  = VERIFIED_FIXED
    A_P5_REVISED_CONTRACT_IMPLEMENTED = NOT_ESTABLISHED
    B43_CORRECTION                    = ACCEPTED
    ZB01_ZB02_ZB03                    = OPEN_DESIGN_ITEMS
    V24_V25_WITHOUT_INCOMING          = SKIP_NOT_PASS

以上只是本次审查记录，不是新增冻结科学术语，不授权 B 运行时、科学执行或主分支合并。

下一次建议只复验本次仍开放的 A 子项及 P5 接口同步，再读新增的 B 控制表。已经确认的修复无需为制造更多轮次而重复打开，除非相关源码又发生变化。

## 8. 证据位置

本报告目录：

- SOURCE_MANIFEST.json：固定提交及 30 份文件身份。
- source/：原始字节；run/repo/：独立执行副本。
- run_review_checks.py：原套件及两支 SKIP 路径的运行驱动。
- independent_recheck.py：独立反例/正例以及原变异 main 的完整执行。
- p5_contract_check.py：当前 P5 返回值核对。
- logs/baseline_summary.json：环境、命令、退出码与摘要。
- logs/independent_recheck.json：各子项实测结果。
- logs/oracle.stdout.txt、oracle_calls.json：语法错误变异的原始输出。
- logs/p5_contract_check.json：not_run 与 exact 的原始结果。

本轮没有修改仓库实现。全部原型检查限于合成资料；没有把工程复验结果转换为 C1/C2/C3 科学结论。

—— 知微
