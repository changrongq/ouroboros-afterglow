# AFTERGLOW REFERENCE HARNESS · MANIFEST 冻结 + 资格套件 PASS 报告

**日期**：2026-10-09
**产生人**：Coder（技术实施长）
**呈交**：钳星（代码审阅）/ 凌翼（科学裁定）
**性质**：**工程交付报告。MANIFEST 已实例化并冻结；qualifying known-answer suite 已按 SPEC §16.2.2 顺序执行并 PASS。**

```text
STATUS                     = MANIFEST FROZEN · KNOWN_ANSWER_SUITE = PASS
PHASE                      = PHASE A — HARNESS_VALIDATION_EXECUTION
SCIENTIFIC_CLAIM_ELIGIBILITY = NONE
SCIENTIFIC_EXECUTION       = MAY NOT START（OS 级隔离缺口未闭合）
```

---

# 一 · 本轮做了什么

按钳星上轮指出的顺序「reset + evaluator + 第一个可执行 fixture」→ 继续到「先冻 MANIFEST → 再跑 qualifying suite」，
本轮完成：

```text
1. 补齐 evaluator 的两个生产路径入口（V4.1 / V4b 走真实逻辑，非 fixture 特判）
2. 写 fixtures.py —— 13 个 known-answer fixture（V0 … V5f），各带唯一 oracle
3. 写 manifest_bind.py —— 以确定性规范编码实测所有 execution-critical hash
4. 实例化 MANIFEST —— 所有 TO_IMPLEMENT 由实测值填入，无残留
5. 冻结 MANIFEST —— 自身 hash 写入 detached 记录（不写入 MANIFEST，避免自指）
6. 按 §16.2.2 顺序跑 qualifying suite —— 先捕获冻结 hash，再跑 fixture
7. 新增 binding 漂移校验器
```

---

# 二 · 冻结身份

```text
IMPLEMENTATION_BINDING_MANIFEST_HASH = b3802142fed33882e48aa688f19cb46a16c8d1d270147d3ac061ff454ed195fe
MANIFEST_BYTES                       = 15644
REFERENCE_HARNESS_SPEC_HASH          = 1386ba22adc2ea7cf1f81731050d8ce35c76fbd4972f4536b6f54558dbf13220
PARENT_PREREG_SHA256                 = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
base_model_sha256                    = dfb053cb8d5f56abde8f56899ffe0d23e1285a423df0b65ea3f3adbb263b22c2
```

**MANIFEST 自身 hash 放 detached 记录**：`reports/MANIFEST_v0.1_HASH.txt`。
**未写入 MANIFEST 正文**（遵守既有教训：冻结标记不写进被冻结对象）。

---

# 三 · 执行顺序证据（SPEC §16.2.2）

qualifying suite 在**第一条 fixture 执行前**捕获了：

```text
[captured BEFORE first fixture — SPEC §16.2.2]
    SPEC_HASH       = 1386ba22adc2ea7cf1f81731050d8ce35c76fbd4972f4536b6f54558dbf13220
    MANIFEST_HASH   = b3802142fed33882e48aa688f19cb46a16c8d1d270147d3ac061ff454ed195fe
    MANIFEST_BYTES  = 15644
    PREREG_SHA256   = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
    detached_match  = True
```

⇒ 时间方向正确：**先冻结 MANIFEST，再跑 suite**。非「先在 draft 跑完再 freeze」。
⇒ 本 PASS **绑定 SPEC_HASH + MANIFEST_HASH 两者**（非仅 SPEC）。

---

# 四 · 资格套件结果

```text
PHASE A — known-answer suite
fixtures: 13/13 oracle match
KNOWN_ANSWER_SUITE = PASS
  bound to SPEC_HASH     = 1386ba22…
  bound to MANIFEST_HASH = b3802142…
  => QUALIFYING RUN
```

逐 fixture：

| Fixture | 唯一 oracle | 结果 |
|---|---|---|
| V0   | L1 = FAIL | ✅ |
| V0b  | L1 = UNRESOLVED | ✅ |
| V1   | L1 PASS · PRE C1 · C2/C3 NOT_ASSESSED | ✅ |
| V2   | PRE C2 · C3 NOT_ESTABLISHED | ✅ |
| V3   | PRE C3 | ✅ |
| V4.1 | L2 INVALID · code CAUSAL_CONTRAST_RULE_MISSING | ✅ |
| V4b  | PRE C1 · C2/C3 ARCHITECTURALLY_NOT_IDENTIFIABLE | ✅ |
| V5a  | L2 PASS · POST C3 | ✅ |
| V5b  | L2 PASS · POST C2 · post C3 NOT_ESTABLISHED | ✅ |
| V5c  | L2 INVALID · pre C3 仍有效 | ✅ |
| V5d  | L2 FAIL | ✅ |
| V5e  | L2 UNRESOLVED | ✅ |
| V5f  | L2 PASS · POST C1 · post C2/C3 NOT_ASSESSED | ✅ |

覆盖核对（§16.3 canonical exits）：**全部有唯一 oracle**，无 `KNOWN_ANSWER_COVERAGE_INCOMPLETE`。

- L1 PASS ← V1/V2/V3 ✅
- L1 FAIL ← V0 ✅
- L1 UNRESOLVED ← V0b ✅
- PRE C1 ← V1 / V4b ✅　PRE C2 ← V2 ✅　PRE C3 ← V3 ✅
- L2 PASS/C3 ← V5a ✅　PASS/C2 ← V5b ✅　PASS/C1 ← V5f ✅
- L2 FAIL ← V5d ✅　UNRESOLVED ← V5e ✅　INVALID ← V5c ✅
- ARCH_NOT_IDENT ← V4b ✅
- NOT_ASSESSED ← V1 / V5f ✅
- NOT_ESTABLISHED ← V2 / V5b ✅

---

# 五 · 本轮发现并修正的一个真实缺陷（诚实报告）

**首轮套件：12/13。V5e 返回 `L2 = PASS / POST C3`，期望 `UNRESOLVED`。**

根因（我的错误）：`fixtures.py` 的 `_c3_from_T` 助手把每个成员的 `attributed` 一律设为 `True`，
使携带不确定 T（±1/2）的成员被纳入 C3 结构判定；其符号恰好按 class 分裂，
于是「同类相等 + 异类不等」双双成立，**误立 C3**。

修正：**成员进入 C3 前必须先过 C2 判据（`|T| ≥ 1` → attributed）**。
不确定成员不 attributed ⇒ 即便符号按 class 分裂，C3 也不能建立。
这正是「低类判据先行门控高类判定」的规则，现由代码强制，而非默认假设。

修正后：**13/13 PASS**。

**纪律记录：** 这与既有教训一致——不许用一个违反自己定义的例子去验证自己的定义；
低类判据必须先于高类判定被强制执行。

---

# 六 · Binding 完整性校验

```text
BINDING_INTEGRITY = PASS（0 漂移）
```

- 9 个核心组件文件 hash ✅ 全部与 MANIFEST 一致
- 5 个派生 hash（J / reset / discrimination ruleset / content class / evidence set）✅
- 13 个 fixture rule bundle hash ✅

校验器：`afterglow_harness/verify_manifest_binding.py`。
**任何组件变更后再跑，即可在依赖旧 PASS 前发现漂移。**

---

# 七 · 两个必须登记的缺口 / 边界（不隐藏）

## 7.1 OS 级隔离仍缺失（钳星 point ②）

```text
当前状态：
  · 本轮套件只覆盖 reset 的"逻辑层"（三向 witness 判定）；
  · OS 级进程替换 + 权限拒绝（access-side 真实隔离）尚未实现；
  · reset.py 以 NotIsolatedError 显式拒绝假装完成。

MANIFEST §十 已诚实登记：
  本 MANIFEST 授权范围 = HARNESS_VALIDATION（逻辑层）；
  SCIENTIFIC_EXECUTION 仍需 OS 级隔离落地后方可点火。
```

⇒ **SCIENTIFIC EXECUTION MAY NOT START** 仍成立。

## 7.2 驱动脚本未纳入 MANIFEST 组件绑定（需裁定）

```text
已绑定（§十三）：harness_constants / storage / writers / readers / observer /
                 perturbation_j / reset / evaluator / fixtures（9 个核心组件）

未绑定：manifest_bind.py / freeze_manifest.py / verify_manifest_binding.py /
        run_known_answer_suite.py（4 个工具/驱动脚本）
```

**我的判断（交由裁定，未自行决定）**：驱动脚本影响「如何跑」而非「如何判」；
被判定语义全部在已绑定的 9 个组件内。但若凌翼要求驱动脚本也纳入绑定，
那是 MANIFEST 变更 ⇒ new MANIFEST_HASH ⇒ requalification。

---

# 八 · 结论与下一步

```text
本轮交付：
  · MANIFEST 实例化 + 冻结（b3802142…）
  · qualifying known-answer suite PASS（13/13，绑定 SPEC + MANIFEST）
  · binding 完整性校验 PASS
  · 一个真实缺陷被发现、修正、诚实记录

仍阻塞 SCIENTIFIC IGNITION：
  · OS 级隔离未落地（§10 已登记）
  · 驱动脚本绑定范围待裁定（§7.2）
```

**请求裁定：**

```text
Q1  是否接受本轮 MANIFEST 冻结与 qualifying PASS 作为 PHASE A 的有效交付？
Q2  驱动脚本（4 个）是否纳入 MANIFEST 组件绑定？
    · 若纳入 ⇒ 需重冻 + 重跑（我会执行）
    · 若维持现状 ⇒ 书面确认此边界
Q3  是否授权我进入 OS 级隔离层的实现（access-side 真实权限拒绝 + 进程替换）？
```

---

**—— Coder · 2026-10-09**
