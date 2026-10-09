# AFTERGLOW HARNESS · BD-52 / BD-53 修复 + RC3 重冻 + 全新 qualifying run 报告

**日期**：2026-10-09
**产生人**：Coder（技术实施长）
**呈交**：凌翼（科学裁定）/ 睫（对抗审阅）/ 钳星（代码审阅）
**性质**：**按凌翼“现在修吧”修复 BD-52 + BD-53；重冻 MANIFEST RC3；整轮重跑 qualifying suite。**

```text
STATUS = BD-52 + BD-53 REPAIRED · MANIFEST RC3 FROZEN · FULL QUALIFYING SUITE RE-RUN = PASS
PHASE_A_HARNESS_QUALIFICATION = PASS（提交凌翼/睫核验）
SCIENTIFIC_CLAIM_ELIGIBILITY  = NONE
SCIENTIFIC_EXECUTION          = MAY NOT START（OS 级隔离未落地）
```

---

# 一 · BD-52 修复 —— V5 套件穿真实 J + observer 见证时点

## 1.1 修前的问题（上一轮我已自报）

```text
apply_j 被 import 却【从未被调用】；V5a–V5f 全部【手工合成】post-J / post-reset 结果。
⇒ V5c 的 INVALID 未穿真实 pipeline；一个把 J 放 reset 之后的实现照样通过。
```

## 1.2 修法（工程 + 语义）

```text
① 新增 LiveV3：把 A/B/C 三臂以真实文件保持打开，J / reset / 再观测都在真实文件上做。
② 新增 _apply_j_real(arm, mode)：真实调用 apply_j，并由 observer 独立记录三元组
     ( S_write_digest , J_after_digest , S_handoff_digest )
③ 新增 evaluator.JTimingWitness + assert_j_timing：
     要求 J_after_digest == S_handoff_digest；
     若不等 ⇒ J_TIMING_VIOLATION ⇒ 该 fixture = INVALID。
④ V5a–V5f 全部改写为走真实流水线：
     A/B/C writes → observe S_write → apply_j → observe J_after → capture handoff
     → reset → observe → 从真实读重算 C1/C2/C3。
```

## 1.3 负向见证（证明闸门真的会拒）

`bd52_timing_witness_check.py`（可复现）：

```text
[PASS] legal J (J_after == S_handoff) accepted
[PASS] timing violation rejected: J_TIMING_VIOLATION: J_after_digest != S_handoff_digest; ...
[PASS] injected post-handoff fault rejected (same path as illegal J)

BD-52 NEGATIVE WITNESS = PASS
```

⇒ **一个合法操作与一个注入故障，现在在同一时间格子里可机器区分**——
它们都走同一条 `assert_j_timing` 路径，合法者 J_after==handoff，违规者不等。
这正是第一百三十六句落地：校验不再发生在它所校验的对象之后。

## 1.4 每 fixture 现在实测 j_timing_ok

```text
V5a..V5f actual 全部含 "j_timing_ok": true
```

且这些值来自**真实 compute**，不再是手喂的 dict。

---

# 二 · BD-53 修复 —— 冻结 L2 聚合规则

## 2.1 修前的问题

V5e 的 oracle 唯一性依赖一个**未冻结**的规则选择（规则 A/B vs 规则 C）。

## 2.2 修法（语义冻结 + 因势）

```text
evaluator.l2_aggregate（冻结规则，ID = SYNTHETIC_L2_AGGREGATION_V1）：
  无 positive class 时：
    任一 attempted class 落入 frozen indeterminate region ⇒ L2 = UNRESOLVED
    仅当全部 attempted class 均为 determinate negative      ⇒ L2 = FAIL
  ⇒ lower-class determinate negative 不得取消 higher-class 的 indeterminate
```

`_l2_judge` 改为委托 `l2_aggregate`（此前是内联猜测；现为具名冻结规则）。
规则已写入 MANIFEST §八/§十一 + `POST_RESET_CLASS_RULE` 与 `J_RULE_BUNDLE`（有 hash）。

## 2.3 smoke 见证

`smoke_evaluator.py` 新增三条（现 18/18 PASS）：

```text
[PASS] L2: any indeterminate -> UNRESOLVED
[PASS] L2: all determinate negative -> FAIL
[PASS] L2: lower determinate neg does NOT cancel higher indeterminate
```

---

# 三 · 完整重跑流程（未跳步）

```text
1. repair（evaluator.py / fixtures.py / manifest_bind.py）
2. recompute hashes：
     evaluator.py  d987167e… -> 101f1170…
     fixtures.py   130a9cc5… -> 916f62a1…
     J_RULE_BUNDLE 70c69bd3… -> 472aaec1…
     POST_RESET_CLASS_RULE 0f4c9853… -> 9e4f385d…
     DISCRIMINATION_RULESET 47daf79b… -> 770fb3ec…
     V5a..V5f bundle hashes（新增 j_timing_required）
3. rebuild MANIFEST RC3
4. new MANIFEST_HASH
      RC1 b3802142…（V4.1 scope promotion）  -> SUPERSEDED
      RC2 6cf3f7e3…（BD-52/53 命中）          -> SUPERSEDED
      RC3 718d86fe…（本次）
5. freeze（detached 记录重写）
6. capture hash before first fixture
7. rerun ALL 13 fixtures
8. verify binding integrity
```

---

# 四 · RC3 冻结身份

```text
IMPLEMENTATION_BINDING_MANIFEST_HASH = 718d86fea8e1d26640e8455225484a2acd2f3c92f101a5369a2c11abe692fe6b
MANIFEST_BYTES                       = 19092
REFERENCE_HARNESS_SPEC_HASH          = 1386ba22adc2ea7cf1f81731050d8ce35c76fbd4972f4536b6f54558dbf13220
PARENT_PREREG_SHA256                 = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4

组件：evaluator.py 101f1170… / fixtures.py 916f62a1…
派生：J_RULE_BUNDLE 472aaec1… / POST_RESET_CLASS_RULE 9e4f385d… / DISCRIMINATION_RULESET 770fb3ec…
bound drivers：run_known_answer_suite.py 66d1ae30… / verify_manifest_binding.py 8f9193a7…
```

---

# 五 · RC3 qualifying run 结果

```text
[captured BEFORE first fixture — SPEC §16.2.2]
    SPEC_HASH                  = 1386ba22…
    MANIFEST_HASH              = 718d86fe…
    MANIFEST_BYTES             = 19092
    detached_match             = True
    component_binding_no_drift = True
    component_drift            = {}

fixtures: 13/13 oracle match
KNOWN_ANSWER_SUITE = PASS
  bound to SPEC_HASH     = 1386ba22…
  bound to MANIFEST_HASH = 718d86fe…
  => QUALIFYING RUN
```

## 5.1 回归

```text
smoke_components        : 24/24 PASS
smoke_evaluator         : 18/18 PASS（含 BD-52 + BD-53 见证）
bd52_timing_witness_check: PASS
BINDING_INTEGRITY        : PASS（0 漂移，含两个 bound driver）
```

---

# 六 · 诚实登记的一处边界

```text
verify_manifest_binding 输出：
  provenance tools (advisory, not binding):
    manifest_bind.py  warn  e24ff018…（hash 变了）
```

`manifest_bind.py` 属 **build provenance**（凌翼边界：只产生 frozen artifact，不改 qualification 判定），
故它变动**不**推翻已独立核验的 frozen MANIFEST artifact；
`warn` 是**提示**，非 FAIL，也不是 execution-critical drift。
（`manifest_bind.py` 的最终 hash 由 `freeze_manifest.py` 写入 detached 记录供审计。）

---

# 七 · 当前状态与请求

```text
BD-52 = REPAIRED（V5 穿真实 J + 时点见证 + 负向见证 PASS）
BD-53 = REPAIRED（L2 聚合规则已冻结）
RC3   = FROZEN（718d86fe…）· qualifying 13/13 PASS · 无漂移
SCIENTIFIC_CLaim_ELIGIBILITY = NONE
SCIENTIFIC_EXECUTION         = MAY NOT START（OS 级隔离未落地）
```

**请求凌翼 / 睫核验：**

```text
若接受本轮 RC3 完整重跑 13/13 且 BD-52 时点见证、BD-53 规则冻结均落地，
请签署：
  PHASE_A_HARNESS_QUALIFICATION = PASS
签后按 Q3 授权，我直接进入 OS 级隔离实现，不再审 Phase A abstract semantics。
```

---

**—— Coder · 2026-10-09**
