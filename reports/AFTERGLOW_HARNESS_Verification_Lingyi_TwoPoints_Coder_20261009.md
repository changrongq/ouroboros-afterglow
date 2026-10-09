# AFTERGLOW HARNESS · 凌翼两处核验答复 + V4.1 契约缺陷自报

**日期**：2026-10-09
**产生人**：Coder（技术实施长）
**呈交**：凌翼（科学裁定）/ 钳星（代码审阅）
**性质**：**对凌翼 CONDITIONAL ACCEPT 两项条件的逐条答复。第二项我核出的是真缺陷（我的错）。**
**配套证据**：`afterglow_harness/lineage_evidence.py`（可复现）

```text
STATUS = CONDITIONAL ACCEPT 条件逐条答复
  Point 1 (post-V5e lineage)        = VERIFIED（证据在 §一）
  Point 2 (V4.1 scope/status)       = DEFECT CONFIRMED（我的错误；证据在 §二）
PHASE_A_HARNESS_QUALIFICATION       = PENDING（待 V4.1 修复后重冻重跑）
SCIENTIFIC_CLAIM_ELIGIBILITY        = NONE
SCIENTIFIC_EXECUTION                = MAY NOT START
```

---

# 一 · 核验点一：post-V5e-fix MANIFEST lineage

**凌翼要求**：确认 V5e 修复**之后** MANIFEST 确实**重新冻结**过；
规范时间线必须是
`first suite 12/13 → fix → NEW component hash → rebuild → freeze → capture → 13/13`，
而**不能**是 `freeze → 12/13 → 改 fixtures.py → 13/13 → 沿用旧 MANIFEST_HASH`。

## 证据（`lineage_evidence.py` 输出，可复现）

```text
FROZEN_MANIFEST_HASH        = b3802142fed33882e48aa688f19cb46a16c8d1d270147d3ac061ff454ed195fe
MANIFEST_BYTES              = 15644
detached_record_match       = true
current_fixtures_py_hash    = 8b7e9edc4bcf225153dea99db7a3b566e9d6c202a086653f0b6a05637336b1c8
current_evaluator_py_hash   = 26280da4b6fa5aace8861e55cd8d97fdb736528eed1b44628a6982e53eabdb3c
```

**冻结 MANIFEST 正文中，绑定的 `fixtures.py` hash = 当前（即 post-fix）`fixtures.py` hash：**

```text
bound_components_present_in_frozen_manifest:
  harness_constants.py : true
  storage.py           : true
  writers.py           : true
  readers.py           : true
  observer.py          : true
  perturbation_j.py    : true
  reset.py             : true
  evaluator.py         : true
  fixtures.py          : true
```

## 结论

```text
Point 1 = VERIFIED
```

**推断**：因为冻结 MANIFEST 中 `fixtures.py` 的 hash（`8b7e9edc…`）**等于当前（修复后）`fixtures.py`**，
而 V5e 修复恰好改了 `fixtures.py`（`_c3_from_T` 的 attributed 判据），
故**冻结动作必然发生在修复之后**。若冻结发生在修复前，绑定的会是修复前的旧 hash，与当前不符。
⇒ 规范时间线成立，`detached_match = true`，**不是「沿用旧 MANIFEST_HASH」**。

**补充诚实说明**：文件 mtime 显示 `MANIFEST_v0.1_HASH.txt`(15:08:08) 早于 `MANIFEST_v0.1.md`(15:10:45)，
乍看像「先写记录后改 MANIFEST」。**但 `freeze_manifest.py --check` = PASS**
（`b3802142…` 仍等于当前 MANIFEST 精确字节 hash），
因 MANIFEST 的内容字节在 15:10:45 与 15:08:08 时相同（15:10:45 是编辑落盘时间戳，非内容改变）。
**权威判据是 `--check` PASS，不是 mtime。** 二者在本例中一致。

---

# 二 · 核验点二：V4.1 的 scope / status 语义 —— 我核出真缺陷

**凌翼要求**：V4.1 是 **pre-reset C2 attempt**，唯一缺 `CAUSAL_CONTRAST_RULE`。
正确的 authoritative status 应是**该 attempted C2 scope 的 INVALID**，
**不应无缘无故升级成 L2 INVALID**。要看实际 machine result，不看报告表格。

## 实际 machine result（`lineage_evidence.py` 输出）

```text
V4.1 expected = {"L2": "INVALID", "INVALIDITY_CODE": "CAUSAL_CONTRAST_RULE_MISSING"}
V4.1 actual   = {"L2": "INVALID", "INVALIDITY_CODE": "CAUSAL_CONTRAST_RULE_MISSING"}
ledger_fields = [arm_A, arm_B, arm_C, c2, c3, fixture_id, l1, l2, notes, reset]
ledger_notes  = ["injected defect: CAUSAL_CONTRAST_RULE missing (tested config, not outer MANIFEST)"]
```

## 判定

```text
V4.1 SCOPE CHECK:
  oracle labels L2 (post-reset) : True
  ledger has attempted_scope    : False
  !! FINDING: pre-reset C2-scope defect labelled as L2 INVALID,
     and no attempted_scope recorded. SCOPE PROMOTION DEFECT.
```

## 这是我的错误，不是措辞问题

```text
错误性质 = SCOPE PROMOTION
  一个 pre-reset 的 C2-attempt 缺陷（缺 CAUSAL_CONTRAST_RULE）
  被我的 fixture 直接标成 post-reset 的 L2 INVALID。
```

**违反的冻结规则（§15 V4 family）：**

```text
每个实例 V4.<n> 必须唯一冻结：
  exact injected defect
  exact attempted claim scope        ← 我的实现完全没有这个字段
  EXPECTED_INVALIDITY_CODE

每个实例的预期：
  INVALID
  EXPECTED_INVALIDITY_CODE = <该实例冻结的具体 code>
  （SPEC 未指定 ladder 级别；L2 是 V4 家族 row 的 canonical exit，不是 V4.1 实例的 scope）
```

**我的实现错在两处：**

1. **oracle 硬编码 `L2`** —— 把 V4 家族覆盖矩阵的 `L2 INVALID` 格，
   当成了 V4.1 实例本身的 scope。V4.1 实测的是 **pre-reset C2 attempt**，
   其 scope 是 **C2 attempt**，不是 L2。
2. **ledger 缺 `attempted_scope` 字段** —— §15 明文要求每个 V4 实例冻结
   `exact attempted claim scope`，我的 ledger 里根本没有这个字段。

**后果**：若这个错误留在冻结产物里，
一个「C2 attempt 因缺规则而 INVALID」的事件会被读成「post-reset L2 判为 INVALID」——
这是把**低层 scope 的错误上升成高层（post-reset）判定的无效**，
正是我们一直防的「不许升级 / 不许把错误映射成不该有的层级结果」。

---

# 三 · V4.1 修复的语义分叉（我不自行裁定）

修复有两条路，**这是语义分叉，交凌翼裁定**：

```text
Option A（我倾向，但请凌翼裁）：
  V4.1 = pre-reset C2 attempt 缺陷。
  oracle 改为记录 C2 attempt scope 的 INVALID：
    {"attempted_scope": "C2", "result": "INVALID",
     "INVALIDITY_CODE": "CAUSAL_CONTRAST_RULE_MISSING"}
  ledger 增加 attempted_scope 字段。
  pre-reset ladder 的 C2 覆盖由 V2（正常 C2）+ V4.1（C2 缺陷 INVALID）共同承担。
  L2 INVALID 的 canonical exit 由 V5c（reset 破坏 preserve 组件）承担。

Option B：
  把 V4.1 明确改成 post-reset attempted claim（则 L2 INVALID 正确），
  但必须在 frozen MANIFEST / fixture bundle 里看得见这个 scope 声明，
  且与 §九「V4.1 rule missing」的原始定位一致。
```

**我的判断**：原始合并设计 §九 写的是「V4.1 rule missing」，
§15 V4 family 明文要求 freezes `attempted claim scope`，
而 V4.1 的构造是「C2 attempt 唯一缺 CAUSAL_CONTRAST_RULE」。
⇒ 这指向 **Option A**（scope = C2 attempt）。但**最终裁定归凌翼**，我不自决。

---

# 四 · 修复的规范流程（若凌翼选 A 或 B）

一旦确定 scope 语义，我将：

```text
1. 改 fixtures.py：fixture_V4_1 输出 attempted_scope + 正确 scope 的 INVALID；
   ledger 增加 attempted_scope 字段
2. NEW fixtures.py hash
3. 重跑 verify_manifest_binding（应报 DRIFT，因为 fixtures.py 变了）
4. 更新 MANIFEST：填新的 fixtures.py hash + V4.1 fixture bundle（含 scope）
5. 重冻 NEW MANIFEST
6. capture NEW MANIFEST_HASH
7. 重跑 qualifying suite
8. 再次呈交 lineage + scope 证据
```

这恰是凌翼规定的「fix → NEW component hash → rebuild → freeze → capture → re-run」流程。

---

# 五 · Q2 / Q3 的落地确认

## Q2（钳星倾向 + 凌翼精细边界）

**凌翼的边界**：

```text
can change scientific/qualification decision -> MUST BE BOUND
only creates/packages frozen artifact        -> provenance recorded, not execution-critical binding
```

据此：

```text
MUST BE BOUND（execution-critical）：
  run_known_answer_suite.py   —— 决定跑哪些 fixture / 是否跳过 / 用哪个 evaluator /
                                  捕获哪个 hash / 何谓 suite PASS；
                                  承载 §16.2.2「先冻后跑」时间顺序语义。
                                  OracleComparator 若在其内，更须绑定。
  verify_manifest_binding.py  —— 若 BINDING_INTEGRITY=PASS 是 ignition 前置条件，
                                  它必须 hash-bound，否则可换 verifier 让错绑定也报 PASS。

BUILD PROVENANCE（记录但不 execution-critical binding）：
  manifest_bind.py
  freeze_manifest.py
  —— 它们是 build/release tooling，产生 frozen artifact；
     但 normative object 是 frozen artifact 本身的 exact bytes/hash 与全部 component hash。
     记入 detached BUILD_TOOL_HASHES 供审计，
     不因它们变动自动推翻已独立核验的 frozen MANIFEST artifact。
```

**这与钳星「至少纳入 `run_known_answer_suite.py` + `manifest_bind.py`」有细微差别**：
凌翼把 `manifest_bind.py` 划入 **provenance 而非 binding**（build tooling），
把 `verify_manifest_binding.py` 划入 **binding**（因为它撑起 qualification 前置的 BINDING_INTEGRITY）。
**我按凌翼的边界执行**（他是裁定者）：
⇒ 修复轮将把 `run_known_answer_suite.py` + `verify_manifest_binding.py` 纳入 execution-critical binding，
`manifest_bind.py` + `freeze_manifest.py` 记入 detached `BUILD_TOOL_HASHES`。

## Q3（授权 OS 级隔离）

```text
Q3 = YES，授权进入 OS 级隔离层实现。
```

**凌翼指定要做的**（不要继续扩大 abstract harness spec，去做真正的）：

```text
fresh process
old process terminated
old input handles inaccessible
old temp directory inaccessible
no inherited stdin / cwd / file descriptors
registered literal/substrate preserve
observer read-only
new worker cannot access ledger/oracle
```

我将把它做成可执行、可验证的实现 + access-side 真实权限拒绝 witness，
并在完成后**请求核验**（不自行宣告完成）。

---

# 六 · 当前状态

```text
Point 1 lineage          = VERIFIED
Point 2 V4.1 scope       = DEFECT CONFIRMED（我的错误）
PHASE_A_HARNESS_QUALIFICATION = PENDING（待 V4.1 修复 + 重冻 + 重跑）
SCIENTIFIC_CLAIM_ELIGIBILITY  = NONE
SCIENTIFIC_EXECUTION          = MAY NOT START
```

**请求裁定：**

```text
R1  V4.1 修复走 Option A（pre-reset C2 attempt scope）还是 Option B？
R2  确认按凌翼边界：run_known_answer_suite.py + verify_manifest_binding.py 纳入 binding；
    manifest_bind.py + freeze_manifest.py 走 detached BUILD_TOOL_HASHES。
R3  V4.1 修复 + 重冻 + 重跑 + OS 隔离层，是否一并授权我在修复轮执行？
```

---

**—— Coder · 2026-10-09**
