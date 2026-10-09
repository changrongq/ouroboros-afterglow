# AFTERGLOW REFERENCE HARNESS / IMPLEMENTATION BINDING SPECIFICATION v0.1
## FROZEN · 冻结记录

**日期**：2026-10-08
**记录人**：Coder（技术实施长）
**签发依据**：凌翼 STOP RULE（apply BD-49+BD-50 → ONE diff-scoped closure review → BLOCKING=0 → FREEZE）

---

# 一 · 冻结对象

```text
AFTERGLOW IMPLEMENTATION BINDING v0.1.md
（= AFTERGLOW REFERENCE HARNESS / IMPLEMENTATION BINDING SPECIFICATION）

CANONICAL_BYTE_COUNT = 36719
CANONICAL_SHA256     = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33
LINES                = 1669
```

**注：** 冻结在 REVIEW HISTORY 中增补了 "v0.1 = FROZEN" 一条（不含自引 hash）。
该增补本身再次改变字节，故最终 hash 由 `1386ba22…` 变为 `b7ec1fdc…`。
**SPEC 不在文件内自引 hash**（写注即改 hash），故 hash 只记载于本冻结记录。

**canonical byte form（Coder 侧实机核验）：**

| 项 | 要求 | 实测 | 结果 |
|---|---|---|---|
| ENCODING | UTF-8 | UTF-8 | ✅ |
| BOM | NONE | head = 35 32 65（`# A`） | ✅ |
| LINE_ENDING | LF | CR = 0, LF = 1664 | ✅ |
| FINAL_NEWLINE | EXACTLY_ONE | tail = 128 130 10（`位。\n`） | ✅ |

**父对象复核：**

```text
PARENT_PREREG_SHA256 = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
                     （与 frozen prereg 逐字符一致，第 N 次独立复算通过）✅
prereg byte_count    = 52129 ✅
```

---

# 二 · 冻结依据（BLOCKING = 0）

| 项 | 状态 |
|---|---|
| BD-49（V2 完整 C3 attempt） | ✅ 闭合（判据 5 无命中） |
| BD-50（MANIFEST_HASH 钉死） | ✅ 闭合（判据 1 无命中） |
| 接线（入口引用子节） | ✅ 闭合（BD-38 同形不复发） |
| 格式（canonical byte form） | ✅ 合规 |
| STOP RULE | ✅ 满足（ONE diff-scoped closure review） |

**⇒ `BLOCKING = 0` ⇒ SPEC v0.1 冻结。**

---

# 三 · 核验归属（如实记录，不美化）

**这一处必须写清，因为它涉及一条我们在守的规矩。**

```text
睫 曾提交一版字节核验，其 hash 为 f625ba68… / 33415 B
⇒ 那是 R5（BD-45 版），不是 R6（BD-49/50 落盘版）
⇒ 与磁盘当前文件不符

船长确认：给睫看的是最新文件；睫调用工具计算的结果与 Coder 不一致；
          船长自行计算 ⇒ 与 Coder 结果一致（1386ba22… / 36485 B）
⇒ 判定为【睫侧技术障碍】，由船长代为完成该字节核验。
```

**因此本冻结记录的核验方署名如实写为：**

```text
字节级核验执行者 = 船长（Rongxian，代理睫完成）
                                        ← 不是睫自算，不得写成睫自算
Coder 侧独立复算  = 1386ba22… / 36485 B（与船长一致）
```

$$\boxed{\text{代理核验不得表述为被代理人的独立自算}}$$

**这与我们此前的原则同构（"不许把两个人抄同一份答案当成算了两遍"）——
此处是它的反向："不许把代理核验写成独立自算"。**

---

# 四 · 冻结后的状态

```text
AFTERGLOW REFERENCE HARNESS / IMPLEMENTATION BINDING SPECIFICATION v0.1
STATUS = FROZEN

EXECUTION_AUTHORIZATION = NONE
IGNITION = PROHIBITED
SCIENTIFIC_CLAIM_ELIGIBILITY = NONE
```

$$\boxed{\text{SPEC FROZEN} \neq \text{EXECUTION AUTHORIZED} \neq \text{IGNITION}}$$

**SPEC 冻结 = 图纸定稿；真正的 IMPLEMENTATION_BINDING_MANIFEST 下一阶段由 Coder 依实际代码填。**

---

# 五 · STOP RULE 后的纪律

```text
✅ 不再开新 beautification
✅ 不再追补非阻塞项（下移 downstream）
✅ 真 false-pass 无一冻入
✅ 非阻塞实现/schema 问题 → 下移
```

---

# 六 · 下一步（下一阶段）

```text
1. 由 Coder 依实际 implementation 产生 IMPLEMENTATION_BINDING_MANIFEST
   （填 §4/§5/§1.1/§13 的 execution-critical TO_BIND）
2. MANIFEST 反向引用本 SPEC hash（REFERENCE_HARNESS_SPEC_HASH）
3. 实现 Reference Harness（生产 evaluator / code path）
4. 实现 §15 全部 fixtures（V0 / V0b / V1 / V2 / V3 / V4.<n> / V4b / V5a–V5f）
5. PHASE A：对 frozen MANIFEST hash 跑 qualifying suite
   → KNOWN_ANSWER_SUITE = PASS
6. 才进入 PHASE B（scientific execution）审查
```

---

# 七 · 冻结判据（可核验）

```text
AFTERGLOW IMPLEMENTATION BINDING v0.1.md
CANONICAL_BYTE_COUNT = 36719
CANONICAL_SHA256     = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33

HASH_STATUS = INDEPENDENTLY_VERIFIED
  验方 = 船长（代理睫）+ Coder 独立复算（两方一致）
BLOCKING = 0
STATUS   = FROZEN
```

**—— Coder · 2026-10-08**
