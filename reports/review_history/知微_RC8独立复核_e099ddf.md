# 知微 · RC8 独立复核

荣弦、Coder、凌翼、睫：

**结论：RC8 的重构和多项修复已经实证成立；“R1–R4 / 知微六点全部闭合、全部反例已拒”的结论尚不成立。建议保留 RC8 的原始交付与本轮证据，完成以下修复后以新候选重新绑定、重跑。**

这份结论针对 reference harness 的工程验收，不对数字生命、意识或科学候选作裁定。OS 隔离是交付报告已经明确登记的下一阶段事项，本次不把它另算作新发现。

## 1. 对象、方法与证据范围

- 交付报告：`reports/review_history/给凌翼睫知微_RC8交付报告_Coder_20261010.md`，取得于 GitHub `fcf28438f9ba1661a112e6e83cf2e8d1138fe715`。
- **按报告指定快照复核：`e099ddf444bd74ea0820788a656cb67a0a5e97d9`。**
- MANIFEST：25,165 bytes，SHA-256 `61cbfd9f78e545ef5bc8f0bdd87fd10064721dea06d0de879537a2e6ca5a99ed`。
- SPEC：36,719 bytes，SHA-256 `b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33`。
- prereg：52,129 bytes，SHA-256 `ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4`。
- 所有 Python 源文件无 CR 字节。源快照运行前后逐文件 SHA-256 一致；测试新增产物另记，未修改源码，也未写 GitHub。

复核脚本：本目录 `review_rc8.py`、`review_rc8_followup.py`。机器结果：`evidence/review-results.json`、`evidence/followup-results.json`，以及对应 `.log`。

故障注入使用内存 mock，检查判定逻辑能否识别错误行为；它不是“攻破文件 hash”的证明。另有磁盘源码漂移测试，全部在独立副本执行。这两类证据下文分别说明。

## 2. 已确认的进展

我独立重跑得到：

| 原版检查 | 结果 |
|---|---|
| smoke_components | 29/29 PASS |
| smoke_evaluator | 18/18 PASS |
| BD-52 timing witness | PASS |
| adversarial_regression | 15/15 PASS |
| verify_manifest_binding | PASS |
| known-answer suite | 13/13，preflight PASS，exit 0 |
| recompute_from_ledger | 输出 PASS；其覆盖范围有下文限制 |

以下修复确实成立，不应撤销或反复重做：

1. pre 计算已经使用 S_write；no-op storage 不再使 V2/V3 建立原来的 C2/C3。
2. J_after 与所记录 S_handoff 不一致时，V5a 现在输出 L2=INVALID。
3. 首个 required reset 失败不再被后续成员覆盖；12 个 member×arm reset 都执行。
4. V5f reset 无效现在输出 INVALID，不再是科学 FAIL。
5. qualifying driver 的 oracle 已来自 `fixture_contracts.FROZEN_ORACLES`；fixtures 不再手抄 expected。
6. `manifest_bind` 没有进入 qualifying 导入链。实际调用 verifier 时，空 required-role 集会失败；改动 `qualification_binding.py` 或 `writers.py` 的副本也会被 preflight 拒绝。
7. 原始观察已经按 member×arm×phase 保存；reader 确实被调用，并且包含非零 q。这是后续修复的可用基础。

## 3. [P1] reader 异常只被测试脚本看见，没有进入资格判定

位置：`afterglow_harness/fixtures.py:231`、`:348`；`adversarial_regression.py:98–112`。

`reader_witness` 保存实际输出，但生产判定没有检验它。CE6 自己比较 `raw_q` 与 reader 输出，发现不一致便把该项测试写成 PASS；没有断言生产路径拒绝该 fixture 或 suite。

复现：

```python
with patch.object(fixtures, 'affine_read', lambda path, u: Fraction(u)):
    driver.main()
```

结果：`preflight_ok=True`、**13/13 oracle match、KNOWN_ANSWER_SUITE=PASS、exit 0**。把 `literal_consume` 换成恒为 0 也一样。

这证明的是运行时错误行为仍未被判定链挡住，不是说磁盘上修改 readers.py 能绕过 hash。

修复验收：让 reader 的输出关系、操作数一致性和必要的只读见证进入正式 validation gate；同一个公共 gate 也用于 ledger 重算。错误 reader 必须使资格验收失败，不能只在测试脚本中留下一个 `bad=True`。读路径检查仍是协议/实现验证，不应把 reader 输出直接当成新的科学 C1/C2/C3 指标。

证据：`constant-reader-suite.log`、`constant-literal-suite.log`。

## 4. [P1] V5 的前置 class 没有纳入验收，错误 profile 仍匹配 oracle

位置：`fixture_contracts.py:58–59`；`fixtures.py:331–366`。对应 SPEC §15 V5a/V5b 的前置 `PRE_RESET_CHANGE_CLASS=C3`。

PRE gate 现在正确算出较低 class，但 V5 oracle 不检查这个前置结果：

| 故障注入 | 实际 pre | 实际 post / L2 | fixture oracle |
|---|---|---|---|
| V5a storage no-op | NOT_ESTABLISHED | C3 / PASS | 仍匹配 |
| V5b extra 固定为 EXTRA_CONSTANT | C2 | C2 / PASS | 仍匹配 |

进一步只对 V5b 注入 constant-extra，其他 fixture 正常，**完整 driver 仍 13/13、preflight PASS、suite PASS、exit 0**。

这里不主张“一切较低 pre 都必须让一般性的 post 科学判定失败”。问题是：V5b 本来要检验“已建立的 C3 在 reset 后降为 C2”，现在“从未建立 C3”也能通过同一个 known-answer profile。该测试因而没有证明它声称覆盖的路径。

修复验收：将各 fixture 的必要前置条件、attempted scope 和成员完整性纳入 canonical contract/验收；V5b constant-pre 必须导致该 fixture 与 suite 不通过。生产 evaluator 仍按观察作判定，不按 fixture ID 造答案。

证据：`review-results.json` 的 `V5a_noop_storage` / `V5b_constant_pre`，以及 `constant-pre-suite.log`、`followup-results.json`。

## 5. [P1] ledger 重算仍可零检查 PASS，且未核实原始字节与 witness 的一致性

位置：`recompute_from_ledger.py:58`、`:90–94`、`:113–134`。

正常运行已经显示：V0、V0b、V1、V2、V3、V4.1、V4b 共 **7/13** 都是 `matched_keys=0`。非 V5 形状直接返回 `{}`；V4b 本身没有存入原始 observations。

独立反例：

1. 只给一份 V0 ledger，并把实际 L1 从 FAIL 改为 PASS：重算仍 `PASS / exit 0`，matched_keys=0。
2. V5a 的 actual 清成 `{}`：重算仍 `PASS / exit 0`，matched_keys=0。比较器只比较“actual 恰好有的 key”。
3. 修改 V5a 各 C 臂 J_after 的 `q_raw`，保留旧 digest，同时删除 reset_witness 中的 `reset_valid`：重算仍 `PASS / exit 0`、matched_keys=7。它比较缓存的 digest 字符串，没有从原始 bytes 重算；缺失 reset flag 也没有被当作缺失证据。

修复验收：逐类定义必需观察 schema、必需结果字段和成员/fixture 完整集合；缺失、重复、未知字段身份或未实现的重算路径不得获得 MATCH。重算 digest 并连接各阶段；reset 的 preserve 判定必须由原始对象重新验证。clear/access 可继续明确标记为逻辑声明，不能借此宣称 OS 独立验证。若暂时只支持某个 scope，应明确输出 PARTIAL/NOT_IMPLEMENTED，而不是整套 PASS。

证据：`baseline-recompute.log`、`ledger-wrong-v0.log`、`ledger-empty-actual.log`、`ledger-stale-digest.log`。

## 6. [P1] J 的 handoff 与 reset 的 handoff 尚未连接为同一对象

位置：`fixtures.py:203–224`、`:334–348`。

当前分别检验：

```text
J_after == 早先记录的 S_handoff
reset 自己重新捕获的 handoff == reset 自己的 restored
```

中间缺少“早先的 S_handoff == reset 接收的 handoff”。此外，ledger 的 S_restored 又取了一次 `arm.snapshot()`，未必就是 reset 已验证的 returned restored。

反例在 J witness 完成后、reset 捕获 handoff 前，把每个 C 臂的 q 加倍。A1/C 的 q 从 2 变成 4；旧 S_handoff digest 与 reset_witness.handoff_digest 不同。结果仍为 **j_timing_ok=True、reset_valid=True、L2=PASS/C3、V5a oracle 匹配**。

这是逻辑层可检出的阶段断链，与尚未实现 OS 隔离是两件事。

修复验收：每个 member×arm 的 handoff 只有一个明确身份，连接 J witness、reset 输入、reset 返回的 restored、post evaluator 和 ledger；一旦出现未经允许的 handoff 后状态变化，protocol gate 必须 INVALID。保存原始 snapshots，而不是只保存一条自报 valid 标志。

证据：`review-results.json -> remaining.unlinked_reset_handoff`。

## 7. [P1] “INVALID 支配”尚未覆盖公共 gate 内部的测量无效

位置：`gates.py:126–128`、`:210–224`。

若冻结的四成员集少了 B2，`evaluate_c3` 已正确返回 `PAIR_ENDPOINT_MISSING / INVALID`；但 PRE 使用 `C3 if ... else C2`，POST 随后又因剩余 T 都满足 attribution 输出 **L2=PASS/C2**。

独立调用与 V5b 少成员注入都得到：

```text
pre_class = C2
post_C3 = INVALID
L2 = PASS
POST_RESET_SUPPORTED_CLASS = C2
```

V5b 的完整 oracle 在此例会失配，因为它要求 post_C3=NOT_ESTABLISHED；本条不声称“少成员还能通过整套 oracle”。它证明公共 gate 仍把 protocol INVALID 降成正结果，与本轮明确承诺的 INVALID dominance 不一致。

合法完整测量后 C3=NOT_ESTABLISHED，可以独立支持 C2；冻结证据集缺员造成的 INVALID，不能走同一降级分支。

修复验收：公共入口先校验所需成员、pair、测量与 schema 完整性，传播 attempted scope 内的 INVALID；不得用非 C3 的兜底分支覆盖它。

证据：`review-results.json -> missing_member_recompute`、`followup-results.json -> missing_member_V5b`。

## 8. [P1] 绑定角色集合不相等，两个列入绑定的脚本漂移仍不阻止 qualifying

位置：`qualification_binding.py:29–44`、`:56–64`、`:90–103`；MANIFEST §十三。

实际计数：

- MANIFEST §十三：**16** 个角色。
- verifier 的 REQUIRED_RUNTIME_ROLES：**14** 个。
- 漏检：`adversarial_regression.py`、`recompute_from_ledger.py`。
- parser 扫整份 MANIFEST，还把 BUILD_PROVENANCE 两个文件解析进来，`frozen_role_count=18`；这不是 18 个 qualification 角色。

`role_set_equal` 实际比较的是“14 个硬编码角色中，哪些文件存在”，没有比较“MANIFEST 声明的角色集 == required 角色集”。

在独立副本中，分别给上述两个漏检脚本追加一行注释，使源 hash 与冻结表不符。两次完整运行均仍 **KNOWN_ANSWER_SUITE=PASS、QUALIFYING RUN、exit 0**。相比之下，同样改动 qualification_binding.py 或 writers.py 会正确失败。

修复验收：精确解析 authoritative role-map 的范围；将 manifest roles、required roles、实际待验证文件角色三者校验为明确的同一集合，并逐项 hash。若决定某些脚本只属于 advisory，应先在新候选中一致地改合同与交付声明，不能把它们写在 execution-critical 表里却漏验。

证据：`mut-adversarial_regression.log`、`mut-recompute_from_ledger.log`、`followup-results.json -> section13_roles`。

## 9. [P1] V4b 仍通过公开接口暴露可分离写入

位置：`fixtures.py:435–441`、`:462–475`。

新版删除了 combined_write 的 extra_mode 参数，但保留公开 `self.arm`，其 `store()` 与 `extra()` 可独立调用。`capability_surface()` 固定返回 `('write',)`，然后靠该自报 tuple 不含 extra_mode 判定 ANI。

不需要反射、私有属性或绕过 OS 权限即可构造：

```python
on.write(payload)
off.arm.store(payload, STORE_FULL)
```

两边 literal 相同，q 分别为 2 和 0；而 V4b 仍输出 ARCHITECTURALLY_NOT_IDENTIFIABLE 并匹配 oracle。ON 的 write 内部调用的也正是同一 Arm.store 存储路径。

修复验收：明确测试对象的可调用边界，确保公开能力实际与声明相符；不向调用方暴露底层可分离 writer/Arm，并增加针对完整公开接口的反例。此要求仅涉及当前接口层，未要求本轮提前实现 Python/OS 安全沙箱。若本意只是“协议只授权 write 这一入口”，应在合同中把这个限定写清，而不能把接口自述直接等同于整个架构没有可分离能力。

证据：`review-results.json -> remaining.V4b_public_arm`。

## 10. [P2] 一并整理的身份/叙述问题

1. 交付报告称 17 个运行时角色，另一处又写 15 个；实际 §十三列了 16 个。请从同一个角色清单生成统计。
2. MANIFEST §七的 `READ_OPERATOR_HASH` / `LITERAL_CONSUMER_HASH` 仍为 `83cbc20b…`，且文字说明它就是 readers.py 的整文件 hash；§十三及实际文件则为 `2180f0d9…`。同一冻结对象对同一身份给了两种值。请新候选中统一生成字段和汇总表，避免旧字段残留；不要直接改 RC8 冻结字节。

## 11. 建议的最小验收顺序

1. 先定义统一、可验证的 member×arm×phase 证据对象：必需字段、阶段连接、reset 和 reader witnesses。
2. 公共 gate 校验该对象并传播 INVALID；qualifying 和 ledger replay 都用它。
3. canonical fixture contract 同时约束 profile 前置条件与结果；重算覆盖完整约定 scope，零检查不能 PASS。
4. 修复 V4b 公开能力边界；角色 map、各处 hash 字段从一份数据生成。
5. 在新候选重冻前，把本报告反例的验收目标写成“生产路径拒绝 / 重算拒绝 / preflight 拒绝”，再运行原版回归和独立反例。

本轮留下的主要问题都是可复现的实现判定缺口，不需要重开全部哲学讨论或修改 frozen SPEC 来解释。公共 gate 与原始账本的方向可以保留；下一步是把已经记录下来的异常真正接进验收。

—— 知微，2026-10-10
