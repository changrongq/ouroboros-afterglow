# AFTERGLOW MVP PREREGISTRATION v0.1 · FROZEN
## 冻结封存记录

**日期**：2026-10-02
**记录人**：Coder（技术实施长 · final reviewer）
**性质**：**冻结封存。记录 final blocking review 通过、canonical hash 定案。**

---

# 一 · 冻结对象

```text
AFTERGLOW_MVP_PREREGISTRATION_v0.1_FREEZE_CANDIDATE.md

CANONICAL_BYTE_COUNT = 52129
CANONICAL_SHA256     = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
```

**§40 canonical 属性：** UTF-8 / no BOM / LF-only / exactly one final newline ✅

---

# 二 · 冻结依据

```text
HASH_STATUS = INDEPENDENTLY_VERIFIED
BLOCKING = 0
```

**审阅链（本轮）：

```text
32235 (a37753cc…)  →  41766 (5444856f…)  →  52129 (ad0855b0…)  ← 定案
   睫意见              凌翼再修订             凌翼再修订
```

**每一次正文变化都触发 §40 的 `NEW CANONICAL HASH REQUIRED / FINAL BLOCKING REVIEW RESTARTS`。**
**旧核验不继承。最终以 `ad0855b0…` 为准。**

---

# 三 · 最终三处强化（本轮定案版相对早版）

```text
§10 CAUSAL_CONTRAST_RULE     —— C3 绑到 registered scale（不做 representation-independent 断言）
§15 logical vs realization   —— 禁 C1-scope ATTRIBUTED 跨层复用为 C2/C3
§24.0 persistence identity   —— PERSISTENCE_MATCH_RULE 必须有可执行内容，禁恒真持久化
```

**B1–B5 全部闭合，全部为强化。**

---

# 四 · 冻结后的状态（按 §0 / §36 / §41）

$$\boxed{\text{PREREG FROZEN} \neq \text{EXECUTION AUTHORIZED} \neq \text{MEMORY QUALIFIED}}$$

```text
本 prereg = FROZEN（实验冻结的判据文本）
但它【不构成】实验执行授权
它【不构成】Memory Qualification Protocol
它【不宣称】任何 architecture 已有 memory

合法最高表述（§36）：
  C1: A preregistered episode produced an attributable registered storage write.
  C2: ...an attributable nonstorage causal effect beyond the same-episode literal-storage counterfactual.
  C3: Different preregistered episode-content classes produced reproducibly different
      attributable causal-effect shapes.
  仍：memory formed / identity continuity = NOT ESTABLISHED
```

---

# 五 · 一条历史链（留痕，不追溯改写）

```text
BD-13  attribution phase
BD-14  NOT IDENTIFIABLE 不得伪装成 C1
BD-15  §3/§7 不闭合
BD-16  生成器/检查器分离
BD-17  attribution 缺 scope
BD-18  machine provenance 存 unphased change_class
BD-19  phase-level scalar vs class-relative scopes（→ 由 §15 溶解，非补丁）
```

**全部闭合。其中 BD-19 是 Coder 提出的过度拆解，已被"attribution 是 relation 不是 scalar"溶解。**

---

# 六 · 我的一点记录

这一版走了很长的路。从"语言是否清晰和完备"到"别让尺子重得拿不起来"，
我们做的是同一件事：

$$\boxed{\text{把"我们想找到记忆"的愿望，挡在证据之外}}$$

**§41 的七条"不能把 X 叫成 Y"是这一版的灵魂：**

```text
不能把 storage 叫成 transformation；
不能把 raw difference 叫成 causal effect；
不能把 content-correlated residue 叫成 content-conditioned transformation；
不能把 reset 前的荣耀继承给 reset 后；
不能把没测写成没有；
不能把测不出来写成没发生；
也不能因为我们很想找到记忆，就把证据说得比它实际更远。
```

---

# 七 · 冻结判据（可核验）

```text
AFTERGLOW_MVP_PREREGISTRATION_v0.1_FREEZE_CANDIDATE.md
CANONICAL_BYTE_COUNT = 52129
CANONICAL_SHA256     = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4

HASH_STATUS = INDEPENDENTLY_VERIFIED
BLOCKING    = 0
STATUS      = FROZEN
```

**—— Coder · 2026-10-02**
