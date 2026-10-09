# AFTERGLOW HARNESS · SPEC 根锚点修正 + RC4 重冻 + qualifying run 报告

**日期**：2026-10-09
**产生人**：Coder（技术实施长）
**呈交**：船长 / 睫 / 凌翼
**性质**：**按船长裁定，SPEC 根锚点由 1386ba22… 修正为磁盘真值 b7ec1dca…；重冻 RC4；整轮重跑。**

```text
STATUS = SPEC ROOT ANCHOR CORRECTED · MANIFEST RC4 FROZEN · QUALIFYING SUITE RE-RUN = PASS
SCIENTIFIC_CLAIM_ELIGIBILITY = NONE
SCIENTIFIC_EXECUTION         = MAY NOT START（OS 级隔离未落地）
```

---

# 一 · 修正了什么

```text
旧锚点（错）：REFERENCE_HARNESS_SPEC_HASH = 1386ba22…（36485 B）
     —— 磁盘上【不存在】36485 B 的 SPEC 文件；这是我"SPEC hash 说明"错判的产物。

新锚点（对）：REFERENCE_HARNESS_SPEC_HASH = b7ec1dca…（36719 B）
     —— 磁盘真实 SPEC 对象 = reports/AFTERGLOW IMPLEMENTATION BINDING v0.1.md
     —— 与冻结记录§一、睫实机，三方一致。
```

**改动点：**

```text
1. harness_constants.py：
     REFERENCE_HARNESS_SPEC_HASH  1386ba22… -> b7ec1dca…
     （新组件 hash = 43f9fe61…，字节数仍 5757）
2. MANIFEST：抬头身份、§一 Parent bindings、§十四 Invariants 三处锚点全部改 b7ec1dca…
3. MANIFEST：新增"修正说明" + lineage 记 RC4
4. MANIFEST：STATE_SCHEMA_HASH / §十三 harness_constants.py 行同步为新 hash
```

---

# 二 · 根因（我的流程错误）

```text
我在"给睫的 SPEC hash 说明"里，把 b7ec1dca… 判为"单方面改冻结对象、未核验，故作废"，
并把锚点改回 1386ba22…。
但——
  · 冻结记录§一【早已】登记 b7ec1dca…/36719 B 为冻结值（理由：加冻结标记产生新 canonical bytes）；
  · 磁盘实测 = b7ec1dca…/36719 B；
  · 睫实机 = b7ec1dca…/36719 B。
⇒ 我用一份【后写的说明】，去否掉一份【更早的冻结记录】，且没有对磁盘重算。
⇒ 后果：RC1/RC2/RC3 全部绑了悬空值 1386ba22…。
```

**我违反了自己的纪律：凡 hash 争议，须对磁盘实际文件重算。** 上一轮我没重算就写了说明。

---

# 三 · 完整重跑流程

```text
1. 改锚点（harness_constants.py + MANIFEST 三处）
2. recompute：harness_constants.py 810265fd… -> 43f9fe61…
3. rebuild MANIFEST RC4
4. new MANIFEST_HASH
      RC1 b3802142…（V4.1 scope promotion）-> SUPERSEDED
      RC2 6cf3f7e3…（BD-52/53 命中）       -> SUPERSEDED
      RC3 718d86fe…（正确锚点前最后一版）  -> SUPERSEDED
      RC4 d6a0f36d…（SPEC 锚点 = b7ec1dca…）
5. freeze（detached 记录重写）
6. capture hash before first fixture
7. rerun ALL 13 fixtures
8. verify binding integrity
```

**过程诚实记录：** 第一次重冻后 verify 报 `harness_constants.py DRIFT`
（我改了锚点，但 MANIFEST 还留着旧 hash）——漂移检测器正确拦下；
补齐 §十三 / STATE_SCHEMA_HASH 后重冻，verify PASS。

---

# 四 · RC4 冻结身份

```text
IMPLEMENTATION_BINDING_MANIFEST_HASH = d6a0f36d68eb2b9bb2aeef6eedfd45a43d68d0fb3b6bfd8ae5dfe9ea35221d1e
MANIFEST_BYTES                       = 19705
REFERENCE_HARNESS_SPEC_HASH          = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33
REFERENCE_HARNESS_SPEC_BYTES         = 36719
PARENT_PREREG_SHA256                 = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
components：harness_constants.py 43f9fe61… / evaluator.py 101f1170… / fixtures.py 916f62a1…
```

---

# 五 · RC4 qualifying run

```text
[captured BEFORE first fixture — SPEC §16.2.2]
    SPEC_HASH                  = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33
    MANIFEST_HASH              = d6a0f36d68eb2b9bb2aeef6eedfd45a43d68d0fb3b6bfd8ae5dfe9ea35221d1e
    MANIFEST_BYTES             = 19705
    detached_match             = True
    component_binding_no_drift = True
    component_drift            = {}

fixtures: 13/13 oracle match
KNOWN_ANSWER_SUITE = PASS
  bound to SPEC_HASH     = b7ec1dca…（磁盘真值）
  bound to MANIFEST_HASH = d6a0f36d…
  => QUALIFYING RUN
```

## 回归

```text
smoke_components       : 24/24 PASS
smoke_evaluator        : 18/18 PASS
bd52_timing_witness    : PASS
BINDING_INTEGRITY      : PASS（0 漂移）
```

---

# 六 · 请睫/凌翼做的

```text
1. 核验 RC4 锚点 = b7ec1dca… / 36719 B（对磁盘文件重算确认）
2. 确认我的"给睫的 SPEC hash 说明"Coder_20261009.md 作废——
   该文件错判 b7ec1dca… 作废；冻结记录§一 为权威。
3. 若接受，（此前 CONDITIONAL 的）资质升级为：
     PHASE_A_HARNESS_QUALIFICATION = PASS
   签后按 Q3 授权，进入 OS 级隔离实现。
```

---

**—— Coder · 2026-10-09**
