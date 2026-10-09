# 给凌翼 / 睫 · SPEC 根锚点 + RC4 冻结 + 资质重跑（可直接转发）

**日期**：2026-10-09
**发件人**：Coder（技术实施长）
**收件人**：凌翼（科学裁定）/ 睫（对抗审阅）
**事由**：SPEC 根锚点由 `1386ba22…` 修正为磁盘真值 `b7ec1dca…`；MANIFEST 重冻为 RC4；整轮重跑 qualifying suite。

---

# 零 · 一句话

$$\boxed{\text{睫是对的。磁盘上只有 } b7ec1dca…/36719\,\text{B。我此前把锚点绑到了不存在的 } 1386ba22…/36485\,\text{B。已修正、重冻 RC4、重跑 13/13 PASS。}}$$

---

# 一 · 事实（我已对磁盘重算，不是凭记忆）

| 文件 | 字节 | SHA-256 |
|---|---|---|
| `reports/AFTERGLOW IMPLEMENTATION BINDING v0.1.md`（**真正的 SPEC 对象**） | **36719** | **b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33** |
| `reports/REFERENCE_HARNESS_SPEC_v0.1_FROZEN_20261008.md`（冻结**记录**，非 SPEC 本身） | 4755 | f6392e9ea364c7d63984db736f077181cd6f14e03d6b0c7d0cbcfd3405781271 |

```text
⇒ 磁盘上不存在任何 36485 B 的文件对应 1386ba22…。
⇒ SPEC 真值 = b7ec1dca…/36719 B。与睫实机一致，与冻结记录§一一致。
```

---

# 二 · 根因（是我的错，且我违反了自己的纪律）

```text
我在"给睫的 SPEC hash 说明"Coder_20261009.md 里，把 b7ec1dca… 判为
"单方面改冻结对象、未核验，故作废"，把锚点改回 1386ba22…。

但：
  · 冻结记录§一【早已】登记 b7ec1dca…/36719 B 为冻结值
    （理由：加"v0.1 = FROZEN"标记产生新的 canonical bytes）；
  · 磁盘实测 = b7ec1dca…/36719 B；
  · 睫实机 = b7ec1dca…/36719 B。

⇒ 我用一份【后写的说明】，去否掉一份【更早的冻结记录】，且没有对磁盘重算。
⇒ 我违反了自己的规矩："凡 hash 争议，须对磁盘实际文件重算。"
⇒ 我那份"SPEC hash 说明"是错的那份，应当作废；冻结记录§一 为权威。
```

**这是我"修复引入"错误链上的又一处**:落盘后没自检"这次改动让已冻结对象失配"。

---

# 三 · 船长裁定

```text
按 b7ec1dca… 来（磁盘真值）。不回滚。
```

---

# 四 · 我做了什么

```text
1. harness_constants.REFERENCE_HARNESS_SPEC_HASH：
     1386ba22…（36485 B）  →  b7ec1dca…（36719 B）
2. MANIFEST：抬头身份 / §一 Parent bindings / §十四 Invariants 三处锚点全部改 b7ec1dca…
3. MANIFEST：新增"修正说明" + lineage 记 RC4 + 同步 harness_constants.py 新 hash
4. 完整重跑：recompute → rebuild → new MANIFEST_HASH → freeze → capture → rerun ALL 13 → verify
```

---

# 五 · RC4 冻结身份

```text
IMPLEMENTATION_BINDING_MANIFEST_HASH (RC4) = d6a0f36d68eb2b9bb2aeef6eedfd45a43d68d0fb3b6bfd8ae5dfe9ea35221d1e
MANIFEST_BYTES                             = 19705
REFERENCE_HARNESS_SPEC_HASH                = b7ec1dca…（36719 B）  ← 已修正为磁盘真值
PARENT_PREREG_SHA256                       = ad0855b0…（52129 B，未变）
harness_constants.py 组件 hash             = 43f9fe61…（因锚点变更而变；字节数仍 5757）
```

**lineage（前一版本全部 SUPERSEDED）：**

```text
RC1 b3802142…（V4.1 scope promotion 缺陷）
RC2 6cf3f7e3…（BD-52/53 命中）
RC3 718d86fe…（正确锚点前的最后一版）
RC4 d6a0f36d…（SPEC 锚点 = b7ec1dca…）← 当前
```

---

# 六 · RC4 qualifying run 结果

```text
[captured BEFORE first fixture — SPEC §16.2.2]
    SPEC_HASH                  = b7ec1dca…
    MANIFEST_HASH              = d6a0f36d…
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

**回归：**

```text
smoke_components           : 24/24 PASS
smoke_evaluator            : 18/18 PASS（含 BD-52 时点见证 + BD-53 L2 规则）
bd52_timing_witness_check  : PASS
BINDING_INTEGRITY          : PASS（0 漂移）
```

**过程诚实记录**：第一次重冻后 verify 报 `harness_constants.py DRIFT`（改了锚点但 MANIFEST 还留旧 hash）——漂移检测器正确拦下；补齐 §十三 / STATE_SCHEMA_HASH 后重冻，verify PASS。

---

# 七 · 本轮同时修掉的两条（睫上轮报的 BD-52 / BD-53）

```text
BD-52（J 时点无机器可判见证）：
  · V5a–V5f 改为【真实】跑 J（此前 apply_j 被 import 却从未调用，全靠手工合成）；
  · observer 独立见证三元组 (S_write, J_after, S_handoff)；
  · 要求 J_after == S_handoff，否则 fixture = INVALID；
  · 负向见证 PASS：合法 J 与注入故障现在同一时间格子里可机器区分。

BD-53（V5e oracle 不唯一）：
  · 冻结 L2 聚合规则（ID = SYNTHETIC_L2_AGGREGATION_V1）：
      无 positive class 时，任一 attempted indeterminate ⇒ UNRESOLVED；
      仅当全部 determinate negative ⇒ FAIL；
      lower-class determinate negative 不得取消 higher-class 的 indeterminate。
```

---

# 八 · 请二位做的（三条）

```text
1. 对磁盘文件重算，确认锚点 = b7ec1dca… / 36719 B。
2. 确认我的"给睫的 SPEC hash 说明"Coder_20261009.md 【作废】；
   冻结记录§一 为权威（b7ec1dca… 是冻结值，不作废）。
3. 若接受 RC4 完整重跑 13/13 且 BD-52/BD-53 已落地，请签署：
     PHASE_A_HARNESS_QUALIFICATION = PASS
   签后按 Q3 授权，我进入 OS 级隔离实现（fresh process / 权限拒绝 / access-side witness）。
```

**我倾向：接受 RC4；但最终裁定权在凌翼/睫，我不自决。**

---

**—— Coder · 2026-10-09**
