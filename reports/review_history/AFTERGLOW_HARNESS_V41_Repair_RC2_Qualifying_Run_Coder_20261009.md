# AFTERGLOW HARNESS · V4.1 修复 + RC2 重冻 + 全新 qualifying run 报告

**日期**：2026-10-09
**产生人**：Coder（技术实施长）
**呈交**：凌翼（科学裁定）/ 钳星（代码审阅）
**性质**：**按凌翼 R1 裁定修复 V4.1 scope promotion 缺陷；重冻 MANIFEST；整轮重跑 qualifying suite（非只重跑 V4.1）。**

```text
STATUS = V4.1 REPAIRED · MANIFEST RC2 FROZEN · FULL QUALIFYING SUITE RE-RUN = PASS
PHASE_A_HARNESS_QUALIFICATION = PASS（提交凌翼核验升级）
SCIENTIFIC_CLAIM_ELIGIBILITY  = NONE
SCIENTIFIC_EXECUTION          = MAY NOT START（OS 级隔离未落地）
```

---

# 一 · 按凌翼 R1 修了什么

## 1.1 V4.1 唯一 oracle（凌翼裁定 = pre-reset C2 scope）

```text
attempted_scope : PRE_RESET / C2
  pre_reset_C1 = true ; pre_reset_C2 = true ; pre_reset_C3 = false ; post_reset = false

L1                     = PASS
PRE_RESET_CHANGE_CLASS = C1
C2_ATTEMPT             = INVALID
INVALIDITY_CODE        = CAUSAL_CONTRAST_RULE_MISSING
C3                     = NOT_ASSESSED
L2                     = N/A   ← “未进入 L2” ≠ L2 失败
```

## 1.2 实际 machine result（非报告表格）

```text
V4.1 actual : {"L1": "PASS", "PRE_RESET_CHANGE_CLASS": "C1", "C3": "NOT_ASSESSED",
               "C2_ATTEMPT": "INVALID", "INVALIDITY_CODE": "CAUSAL_CONTRAST_RULE_MISSING",
               "L2": "N/A"}
V4.1 scope  : {"pre_reset_C1": true, "pre_reset_C2": true,
               "pre_reset_C3": false, "post_reset": false}
V4.1 has L2 INVALID? False   ← MUST NOT emit 已满足
```

## 1.3 evaluator 是 scope 驱动，非 fixture 特判

新增 `evaluate_c2_attempt(rule_bundle, scope)`：

```text
· scope.pre_reset_c2 == False          -> result = NOT_ASSESSED（无 C2 可无效）
· scope.pre_reset_c2 == True 且缺 rule  -> result = INVALID（在该 C2 scope 上）
                                          invalidity_code = "<RULE>_MISSING"
· L2 由 scope.post_reset 派生：
     post_reset == False -> l2 = N/A   （ladder 从未进入）
     post_reset == True  -> l2 = INVALID / UNRESOLVED
```

⇒ invalidity **由 scope + 缺失 rule 推导**，不由 `fixture_id == "V4.1"` 输出。
任何具有该形状的 C2 attempt 走同一路径。

## 1.4 ledger 机械编码 attempted_scope

`Ledger` 新增字段 `attempted_scope`（沿用 frozen schema，语义值 `N/A`，不另造平行字段）：

```text
ledger.attempted_scope = {"pre_reset_C1": true, "pre_reset_C2": true,
                          "pre_reset_C3": false, "post_reset": false}
```

## 1.5 schema：用既有 `N/A` 表达“未进入 L2”

```text
NOT_ASSESSED = 没有测（prereg §H / BD16）
N/A          = 不适用（该 ladder 级别从未进入）
二者不得混用。V4.1 的 L2 = N/A（不适用），不是 NOT_ASSESSED，不是 INVALID。
```

---

# 二 · 覆盖拆分（凌翼裁定）

```text
V4.1 → pre-reset attempted C2 protocol INVALID
       exact code: CAUSAL_CONTRAST_RULE_MISSING
V5c  → attempted post-reset claim INVALID
       reset invalid
⇒ pre-reset invalidity ≠ post-reset L2 invalidity（两种不同 scope 的 invalidity 标定）
```

**实测验证：**

```text
V5c actual : {... "L2": "INVALID" ...}
V5c L2     : INVALID   ← L2 INVALID 的 known-answer witness 仍是 V5c
```

---

# 三 · 完整重跑流程（凌翼要求：不可只重跑 V4.1）

严格按凌翼规定的顺序执行：

```text
1. repair（改 evaluator.py / fixtures.py）
2. recompute component hashes
      evaluator.py  26280da4… -> d987167e…
      fixtures.py   8b7e9edc… -> 130a9cc5…
3. rebuild MANIFEST（填新 hash + V4.1 新 fixture bundle + 驱动脚本纳入 binding）
4. new MANIFEST_HASH
      旧 b3802142…（V4.1 = L2 INVALID，有 scope promotion 缺陷）
      新 6cf3f7e3…（RC2；V4.1 = pre-reset C2，scope 正确）
5. freeze（detached 记录重写）
6. capture hash before first fixture
7. rerun ALL 13 fixtures
8. verify binding integrity
```

## 3.1 驱动脚本纳入 binding（凌翼边界）

```text
MUST BE BOUND（能改变 qualification 判定）：
  run_known_answer_suite.py    66d1ae30…
     —— 承载 §16.2.2“先冻后跑”时间顺序语义；决定跑哪些 fixture / 用哪个 hash / 何谓 PASS
  verify_manifest_binding.py   8f9193a7…
     —— 撑起 BINDING_INTEGRITY=PASS 这个 ignition 前置条件

BUILD PROVENANCE（记录但不 execution-critical binding）：
  manifest_bind.py    7df004b4…（BUILD_TOOL_HASHES，供审计）
  freeze_manifest.py  6dd7bffE…（同上）
```

## 3.2 我在修复轮发现并修正的一个**驱动缺陷**（诚实报告）

**首轮修复后，suite 曾错误地盖出“QUALIFYING RUN”。**

根因：原 `capture_frozen_binding()` 只核 **MANIFEST 与 detached 记录**是否一致，
**没有核当前组件 hash 是否仍在 MANIFEST 中**。
于是改完 `fixtures.py`/`evaluator.py` 后，MANIFEST 文件本身没动，
旧 hash 仍自洽，就错误放行。

**这恰是凌翼警告的“把旧 13/13 PASS 接回来”风险。**

修正：`capture_frozen_binding()` 增加 **component drift 检测**
（每个 execution-critical 组件的当前 hash 必须在 MANIFEST 中）。
修正后，未重冻前它就正确报：

```text
component_binding_no_drift = False
component_drift = {'evaluator.py': False, 'fixtures.py': False}
BINDING NOT FROZEN / MISMATCH -> NON_QUALIFYING DEVELOPMENT VALIDATION
KNOWN_ANSWER_SUITE = FAIL
```

⇒ 修正+重冻后，才得到真正的 QUALIFYING PASS。

---

# 四 · RC2 冻结身份

```text
IMPLEMENTATION_BINDING_MANIFEST_HASH = 6cf3f7e3d266b8a3b765f0e36e0df28c4d084bedbb67e49ca928078e5cae53e8
MANIFEST_BYTES                       = 18079
REFERENCE_HARNESS_SPEC_HASH          = 1386ba22adc2ea7cf1f81731050d8ce35c76fbd4972f4536b6f54558dbf13220
PARENT_PREREG_SHA256                 = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
```

detached 记录：`reports/MANIFEST_v0.1_HASH.txt`（已重写为 RC2）。

---

# 五 · RC2 qualifying run 结果

```text
[captured BEFORE first fixture — SPEC §16.2.2]
    SPEC_HASH                    = 1386ba22…（未变）
    MANIFEST_HASH                = 6cf3f7e3…
    MANIFEST_BYTES               = 18079
    detached_match               = True
    component_binding_no_drift   = True
    component_drift              = {}

fixtures: 13/13 oracle match
KNOWN_ANSWER_SUITE = PASS
  bound to SPEC_HASH     = 1386ba22…
  bound to MANIFEST_HASH = 6cf3f7e3…
  => QUALIFYING RUN
```

逐 fixture 全部 ORACLE MATCH（含 V4.1 新 oracle：`L1 PASS / PRE C1 / C2_ATTEMPT INVALID / C3 NOT_ASSESSED / L2 N/A`）。

## 5.1 回归

```text
smoke_components : 24/24 PASS
smoke_evaluator  : 12/12 PASS
BINDING_INTEGRITY = PASS（0 漂移，含两个 bound driver）
```

---

# 六 · 当前状态

```text
Verification Point 1（post-V5e lineage）      = VERIFIED（凌翼已关闭）
Verification Point 2（V4.1 scope promotion）  = REPAIRED + 重冻 + 重跑验证
PHASE_A_HARNESS_QUALIFICATION                 = PASS（提交凌翼核验升级）
SCIENTIFIC_CLAIM_ELIGIBILITY                  = NONE
SCIENTIFIC_EXECUTION                          = MAY NOT START（OS 级隔离未落地）
```

**请求凌翼：**

```text
按你上一轮的口径——
若这轮完整重跑得 13/13 且 scope ledger 正确，你愿把
  PHASE_A_HARNESS_QUALIFICATION = CONDITIONAL
升级为
  PHASE_A_HARNESS_QUALIFICATION = PASS。

本报告即该轮的完整证据：
  · 13/13 oracle match（含 V4.1 新 scope oracle）；
  · component_binding_no_drift = True；
  · bound MANIFEST_HASH = 6cf3f7e3…（RC2，非旧的 b3802142…）；
  · 修复轮还额外暴露并修掉了一个“驱动不改 hash 就误放行”的缺陷。
```

若凌翼签署 `PHASE_A_HARNESS_QUALIFICATION = PASS`，
我将按 Q3 授权**不再审 Phase A 的 abstract semantics，直接进入 OS 级隔离实现**。

---

**—— Coder · 2026-10-09**
