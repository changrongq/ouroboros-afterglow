# 知微 · RC9 独立复核

荣弦、Coder、凌翼、睫：

**RC9 修复了多项旧反例，18 项角色绑定也已对齐。但“所有 fail-open 已封死 / 七个 P1 全部闭合”仍不能确认。本轮剩余问题集中在四类：reader 证据完整性、reset 的 restored 连接、replay 合同一致性、V4b 能力探针。**

其中已经复现完整 Phase-A 流程的误通过：V5a/A1 的 reader 探针结果为空，known-answer、adversarial、ledger replay 仍全部通过，最终 `PHASE_A_QUALIFICATION=PASS / exit 0`。

## 1. 复核对象与方法

- 交付报告：`reports/review_history/给凌翼睫知微_RC9交付报告_Coder_20261010.md`，取得于 `4cdef8ef0f86b9a4862fd934bc7e17c5e7326bba`。
- **实际复核报告指定提交：`2a0737bf66368bd5c93c10facfa7a64c8bb3c98c`。**
- MANIFEST：26,705 bytes，`67dfb5380e8c3a0f6adaaa37372f339cf373202339324062b0aeefd16c7ec7aa`。
- SPEC：36,719 bytes，`b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33`。
- prereg：52,129 bytes，`ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4`。
- 所有 `.py` 无 CR 字节；原始快照的文件 hash 在测试前后不变。未修改仓库源码，未写 GitHub。

源码漂移只在独立副本进行；行为故障通过内存注入或复制后的 ledger 注入。后者检验 validator 能否拒绝错误/缺失证据，不声称绕过了源码 hash。完整流程反例的三个步骤都真实执行，未伪造返回码或 PASS 文本。

复现文件：

```text
review_rc9.py                 基线、旧反例、证据/ledger 变体、绑定漂移
review_rc9_pipeline.py        单次 reader 证据丢失穿过完整 Phase-A 流程
evidence/review-results.json
evidence/pipeline-results.json
evidence/qualification-encoding-results.json
evidence/*.log
```

重跑时为 `--out` 指定新的空目录：

```powershell
python review_rc9.py --repo <RC9快照目录> --out <新证据目录>
python review_rc9_pipeline.py --repo <RC9快照目录> --out <新流程证据目录>
```

## 2. 正常回归与已闭合项

| 检查 | 独立运行结果 |
|---|---|
| smoke_components / smoke_evaluator | 29/29 / 18/18 PASS |
| BD-52 witness | PASS |
| adversarial_regression | 16/16 PASS |
| binding verification | PASS，registry 与标记区角色表都是 18 项 |
| known-answer suite | 13/13，preflight PASS |
| 原始 ledger replay | PASS，各 fixture 均有非零检查 |
| qualify_phase_a | Windows 默认编码环境及完整 UTF-8 模式下均 PASS、exit 0 |

以下旧问题的具体修复已经验证成立：

1. 恒定 affine reader / literal consumer 现在让 V5a 输出 `READER_WITNESS_INVALID`，不再匹配 oracle。
2. V5b 使用 constant extra、未建立 pre-C3 时，生产路径输出 `PROFILE_PRECONDITION_FAILED / INVALID`；oracle 也已包含 pre-class。
3. J_after 与 handoff 不一致，以及 J handoff 与 reset 接收的 handoff 不一致，都会 INVALID。
4. 首个 reset 失败不再被覆盖；V5f reset 失败为 INVALID；少 B2 成员也不再降级为 PASS/C2。
5. wrong-V0、empty-actual、修改 J_after 原始字节的旧 ledger 反例，现在都 exit 1。
6. 两个曾漏验的脚本 `adversarial_regression.py`、`recompute_from_ledger.py` 发生磁盘字节变化，现在都使 preflight/known-answer 失败。实际空角色集调用 verifier 也失败。`manifest_bind` 未导入 qualifying 链。
7. V4b 原来的公开 `.arm` 已移除；`public_handle()` 的公开名称集合是 `write`。
8. reader 的 hash 字段已转为引用 §十三的单一文件身份，避免原来字段中的重复 hash 值。

编码记录：初次包装器仅设置 `PYTHONIOENCODING=utf-8`，Windows 父进程仍按 GBK 解码子进程，`qualify_phase_a.py:28` 出现 UnicodeDecodeError，随后 stdout=None 引发 TypeError。清除该单独设置、以及统一设置 `PYTHONUTF8=1` 后均通过。此项是环境兼容性限制，不将初次失败描述为默认环境的资格失败；日志全部保留。

## 3. [P1] reader gate 接受空探针集合，且 q 未绑定到 restored 原始字节

位置：`afterglow_harness/evidence_bundle.py:175–202`。

`_independent_reader_ok` 只遍历 `affine.items()` 和 `literal.items()`，没有要求冻结探针 `{0,2}` 全部存在。两个 dict 为空时，无比较也返回 True。affine 的期望值又取自 `reader_witness.raw_q`，没有证明它等于 C/S_restored 的 q_raw 解码值。

独立反例：

| 注入 | 生产 V5a | ledger replay |
|---|---|---|
| 保留 raw_q，清空 affine/literal 探针 dict | PASS/C3、oracle 匹配 | PASS |
| restored q 仍为 ±2；witness.raw_q 改为 0，affine 输出对应 u | PASS/C3、oracle 匹配 | PASS |

第一类还完成了整条入口复现：只在 known-answer 子进程中，让第一条 V5a/A1 观察丢失探针结果；其余观察正常。对抗回归在新的子进程中正常执行，ledger replay 则读取这个真实产出的不完整账本。

```text
preflight_ok = True
V5a/A1.reader_witness = {raw_q: 2, affine: {}, literal: {}}

known_answer_suite     PASS / exit 0
adversarial_regression 16/16 PASS / exit 0
ledger_replay         PASS / exit 0
PHASE_A_QUALIFICATION = PASS / exit 0
```

测试通过给启动步骤加入故障注入 bootstrap，实际调用未修改的 `qualify_phase_a.main()`；三个子进程返回的结果原样交给其聚合逻辑。所有源文件的 hash 仍与复制前一致。这检验的是本次运行的证据缺失能否阻止资格通过，不能由另一轮正常的 reader 测试替代。

修复验收：从冻结合同取得 required probes；缺失、重复或非法探针/值类型必须拒绝。affine 的期望值从已校验的 `C/S_restored.q_raw` 推导，witness 中的 raw_q 仅用于一致性核对；literal 路径同样要求完整探针集。将上述单次丢失故障跑到总入口，最终必须非零退出。

证据：`review-results.json` 的 `missing_reader*`、`unbound_reader_operand*`；`pipeline-results.json`、`pipeline-qualification.log` 及三个 `pipeline-*.log`。

## 4. [P1] reset flag 缺失仍被接受，已验证 restored 与实际 post 输入仍未连接

位置：`evidence_bundle.py:261–267`；`fixtures.py:185–191`。

两处尚未闭合：

1. 只在 `rw.get('reset_valid') is False` 时拒绝。删除该字段后 `.get()` 返回 None，继续执行；最后 actual 还会报告 `reset_valid=True`。
2. `_reset_arm` 返回 `(h,r,ok,reason)`，但 `r` 没有进入 bundle。S_restored 又从 `arm.snapshot()` 重新取得；validator 也没有重算 accepted_handoff 与 S_restored 的 preserve 关系。

反例 A：删除 V5a 所有 reset_witness 的 reset_valid 字段，其他原始观察保留。V5a 仍 PASS/C3、oracle 匹配；完整 ledger 集重算也 PASS。

反例 B：真实 reset 验证结束后、fixture 取得新的 snapshot 前，将每个 C 臂 q 加倍；返回原先已验证的 h/r/ok。

```text
A1/C accepted_handoff.q = 2
reset 返回的 r.q        = 2
实际 S_restored.q       = 4

reset_valid = True
L2 = PASS
POST_RESET_SUPPORTED_CLASS = C3
oracle_match = True
ledger replay = PASS
```

因此前半段 J→reset handoff 已接上，后半段 reset 返回对象→post 输入仍有断点。本项是逻辑层原始字节验证要求，OS 隔离仍按原计划另行实现。

修复验收：reset witness 必需字段及其类型要明确；缺失不是通过。保存实际验证的 restored 对象，绑定后续 reader/evaluator 的输入；若重新读取，须与该对象逐字节比对。replay 从原始 handoff/restored 重算 preserve 检查。clear/access 保持“逻辑声明”的准确标签，不冒充 OS 独立见证。

证据：`missing_reset_valid`、`restored_drift` 及其 `*_replay`，对应 `ledger-missing-reset-valid.log`、`ledger-restored-drift.log`。

## 5. [P1] replay 未恢复 frozen contract，仍能改变验证范围和绕过前置条件

位置：`recompute_from_ledger.py:25–35`、`:72–84`、`:142–187`。

“调用了同一个函数”目前不等于“执行了同一个合同”：

- 生产传入 required_pre_class，replay 明确传入空字符串，关闭该门禁。
- replay 的 required_members 从待审 observations.keys() 自行生成。
- shape / attempted 来自待审 ledger，未与 fixture_id 对应的冻结配置核对。
- V4.1 和 V4b 的 replay scope 只有 L1/pre-class，没有重算各自关键的 C2 invalidity / architectural 判定。
- 没有完整 fixture 集、重复/未知 ID 的资格级检查；缺字段用 `.get()` 比较也不构成严格 schema。

独立反例均在复制出的账本上执行，前三类使用完整 13 份 ledger 集，仅替换指定文件：

| 反例 | replay 结果 |
|---|---|
| V5b 的 S_write 改为 constant-extra，actual pre-class=C2；保留 required_pre_class=C3 的记录 | PASS；生产对此 profile 会 INVALID |
| V5a 换成 V1 的两臂观察、shape 和 actual，仅将 fixture_id 标为 V5a | PASS；把应验的 V5 范围降成两臂 L1 |
| V4.1 的 C2_ATTEMPT/INVALIDITY_CODE/L2 改错，V4b 的 C2/C3 改错 | PASS；关键字段未纳入 scope |
| 目录只剩一份合法 V1 ledger | PASS；没有标记为局部重算 |

这与“零检查”旧 bug 有区别：RC9 已经进行了若干字段检查，但**仍允许待审对象选择检查哪些字段，以及关闭哪些前置条件**。

修复验收：以 bound fixture_id→config contract 决定成员集、shape、attempted、required_pre_class 和必需结果 schema；ledger 只提供证据，不能授权降低范围。V4.1/V4b 必须保存并重建其特殊判定所需证据，不能只复算共同的 L1。qualifying replay 必须检查精确的 13 个 fixture 身份；若支持单 fixture 工具模式，应显式区分，不输出整套资格含义的 PASS。

同时让各 fixture family 的生产与重算共用同一判定入口：当前 two-arm、multi-member 路径仍各有单独代码，`_recompute_multi_member` 也重新实现了 ladder，不能据此声称所有判定都经同一条 EVIDENCE_BUNDLE 链。

证据：`ledger-absent-pre-c3.log`、`ledger-scope-substitution.log`、`ledger-wrong-v4-decisions.log`、`ledger-single-v1.log`。

## 6. [P1] V4b 的旧公开 Arm 洞已关，external probe 仍不会识别 write 参数中的 selector

位置：`fixtures.py:351–352`、`:405–417`。

目前探针检查少量方法名；参数检查这一行的值永远为 False：

```python
takes_selector = ... if False else False
```

并且实际 V4b 传给 probe 的是 `CombinedOnlyWriter` 对象，adversarial CE8 测的是 `w.public_handle()`，两个路径的测试对象并不一致。正常 writer 的公开 Arm 已隐藏，这一修复应保留；下述反例针对探针能否识别一个明确可分离的正对照。

给测试替身增加公开 `write(payload, extra_mode=EXTRA_CONTENT)` 参数：两次调用共享相同 storage 路径，分别选择 CONTENT/OFF。得到相同 literal、q=2/0。无需访问私有对象来调用这两种写入。

probe 仍报告 `separable_w_extra=False`；替换后的 V4b 仍报 `ARCHITECTURALLY_NOT_IDENTIFIABLE`，oracle 匹配。

修复验收：生产与对抗测试使用同一注册 handle；对注册的有限接口边界做真实参数/行为检查。至少加入“write 提供 ON/OFF selector”的可分离正对照和当前不可分离负对照，确保 probe 对两者给出不同结果。这里并不要求算法证明任意 Python 对象的绝对不可分离性；要求的是有限协议接口上的这个已知反例被正确识别。

证据：`review-results.json -> remaining.V4b_selector_missed`。该反例更换的是内存中的组件实现，不声称正常冻结 writer 已公开 ON/OFF 参数。

## 7. 对抗回归的证据措辞需要同步收紧

`adversarial_regression.py:139–144` 两个断言目前分别只是：

```python
len(qb.REQUIRED_RUNTIME_ROLES) > 0
len(rec.REQUIRED_SCOPE['reset_suite']) > 0
```

它们没有真的注入空角色集或运行错误 ledger。因此“16/16 PASS”的计数可复现，但不能把这两项表述成已经执行了对应攻击。我另行调用 verifier 注入空角色集，确实被拒；此处主要要求测试描述与实际覆盖一致。

旧 wrong-J 替换等历史反例建议继续保留在可运行回归中，而不是只保留报告。新回归的验收目标应直接是“生产路径/总入口拒绝”，并包括缺失、空集合、错误类型以及与正确原始对象不一致的 witness。

## 8. 本轮建议

保留 RC9 源码与交付作为本轮审计对象。下一版集中完成上述四类修复，再生成新冻结身份，并重跑原始回归与独立反例。

最优先的验收条件已经很具体：**只丢失 V5a/A1 的 reader 探针结果，完整 Phase-A 入口必须失败。** 然后依次验证 reset restored 断链、ledger 改 scope/关闭 precondition、可分离 writer 正对照。

OS 隔离和真实科学候选仍按已登记的后续阶段安排；本报告的结论仅限 reference harness 的完整性与资格判定。

—— 知微，2026-10-10
