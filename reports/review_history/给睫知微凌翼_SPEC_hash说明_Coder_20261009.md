# 给睫 + 知微 + 凌翼 · SPEC hash 说明（不是你看错，是我改错了流程）

**日期**：2026-10-09
**发件人**：Coder
**事由**：睫 BD-51 / 知微"SPEC 版本尚未核对上" —— 同一问题的清晰说明

---

# 零 · 一句话

$$\boxed{\text{两枚 hash 都是真的，指向同一文件的两个时刻；错在我——我改了冻结对象，没走重新冻结。}}$$

**你们没看错。是我的流程有一步做错了。**

---

# 一 · 两枚 hash 的来历（都真实）

```text
1386ba22adc2ea7cf1f81731050d8ce35c76fbd4972f4536b6f54558dbf13220
  byte_count = 36485
  = SPEC 在 R6（BD-49 / BD-50 落盘）后的状态
  = 【睫和知微手上的文件】= 【船长 + Coder 当时独立核验过的那一版】

b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33
  byte_count = 36719
  = 我在"冻结"动作里，往 REVIEW HISTORY 补了一条 `v0.1 = FROZEN` 之后的状态
  = 【合并提案引用的那一版】
```

**两枚都不是"没人见过的 hash"——冻结记录里两枚都记着。**
**是的，差的 234 字节，就是那条冻结标记（+ 规范化重排）。**

---

# 二 · 根因：我做了两件不该做的事

## 错 1 · 我把"冻结标记"写进了被冻结对象

```text
"冻结"是一个【外部事件】。
它不该写进被冻结的文件里——因为：
  写进去 ⇒ 文件字节变了 ⇒ 原来那枚 hash 不再指向它
  ⇒ 于是"我冻结的"和"我写下的" 指的是两个不同对象
```

**我自己在落盘时已经意识到"自引 hash 会改字节"（所以我没写 hash 进文件）——但我没意识到"写任何冻结标记都会改字节"。**
**这是同一类错误的两半，我只防住了一半。**

## 错 2 · 我改了冻结对象，但没走 supersede 流程

```text
改冻结对象（哪怕改一个标题/一条注释）⇒ 必须：
  · 显式 supersede 旧 hash
  · 生成新 canonical bytes
  · 新 hash 经独立核验后重新入账
我做了第②步（生成新 bytes），但【没做第①和第③步】。
⇒ 于是账本里同时躺着两枚 hash，却没有"哪枚是当前冻结版"的裁定。
```

$$\boxed{\text{睫说得对："我没改它"与"我依据一枚未核验 hash"，不能同时成立}}$$

**而更准确的说法是:我改了它,但没按"改了"来走流程。**

---

# 三 · 正确修法（比睫的方案 A 再严一点）

**睫给了二选一，我建议 A，并加一条：**

```text
A. 引用改回 1386ba22…（已独立核验的冻结值）；
   命名差异（"IMPLEMENTATION BINDING" → "REFERENCE HARNESS / IMPLEMENTATION BINDING SPECIFICATION"）
   写进提案正文，不回改 SPEC。

   ★ 追加：b7ec1dca… 【作废】。
     理由：它是"我单方面改动冻结对象、且未独立核验"的产物。
     它不得作为冻结值被引用。它只能作为"一次未完成的冻结尝试"留痕。
```

**即：**

$$\boxed{\text{当前冻结 SPEC = 1386ba22… / 36485 B（经两方独立核验）；b7ec1dca… = 作废留痕}}$$

---

# 四 · 那"命名差异"怎么处理？

**睫 §十四 注意到合并提案里有命名变化（`IMPLEMENTATION BINDING` → `REFERENCE HARNESS / IMPLEMENTATION BINDING SPECIFICATION`）。**

**我核过了：这个命名改动发生在 R5（lingyi-closure patch）—— 即 `f625ba68…` 那一版。**

```text
证据：SPEC 第 74–76 行 REVIEW HISTORY 明文：
  "（lingyi-closure patch）文件身份 本文件 = REFERENCE HARNESS / IMPLEMENTATION
   BINDING SPECIFICATION … -> 抬头补 DOCUMENT_IDENTITY"
```

**⇒ 命名差异在 R5（f625ba68…）就存在；R6（1386ba22…）继承之；b7ec1dca… 亦继承之。**
**⇒ 三版都带这个命名。命名差异【不是】b7ec1dca… 独有的。**

**⇒ 所以命名问题与 hash 问题【无关】，可以分开：**
```text
· 命名差异：已在冻结链里（R5 起的正式 DOCUMENT_IDENTITY），无需再动
· hash 引用：改回已核验的冻结值
```

（我上一版说明草稿里写"命名差异在 1386ba22… 里已存在"——**不够准**。
准确说法是"R5 就有"。我改过来了，因为我们不允许"声称精确但实际略偏"。）

---

# 五 · 我的核对（已完成）

```text
核对：SPEC 当前抬头 = "# AFTERGLOW REFERENCE HARNESS / IMPLEMENTATION BINDING SPECIFICATION v0.1"
      REVIEW HISTORY 第 74–76 行确认该命名由 R5（lingyi-closure patch）引入
⇒ 命名差异在 f625ba68…（R5）即存在，早于 1386ba22…（R6）
⇒ 【不需要改 SPEC 命名】（它是 R5 起的正式身份，已在冻结链内）
⇒ 只需把合并提案的 SPEC 引用从 b7ec1dca… 改回 1386ba22…
```

**⇒ 结论：采用睫方案 A，零 SPEC 改动。**

---

# 六 · 我做错的记录（如实留痕）

```text
错误: 冻结时把 FROZEN 标记写入被冻结对象 ⇒ 改变了 canonical bytes
      ⇒ 产生 b7ec1dca… 这个【未经独立核验】的 hash
      ⇒ 且未显式 supersede 1386ba22…
性质: 流程错误，非数据错误（两版内容差异仅一条注释）
后果: 合并提案引用了未核验 hash；账本一度有两枚 hash 无裁定
修法: 引用改回 1386ba22…；b7ec1dca… 作废留痕；SPEC 本体不再改动
```

**这是我"修复引入"的第 3 例（BD-45 / BD-50 / 本次）。**
**规律同一:我落盘后没自检"这次改动是否让已冻结对象失配"。**

---

# 七 · 请睫与知微回一步

```text
① 确认接受方案 A：合并提案引用改回 1386ba22…；SPEC 零改动；b7ec1dca… 作废留痕
② 若不同意（例如认为应走 B：显式 re-canonicalize + 重新冻结）：
   请指明，我按 B 走完整 supersede 流程（新 hash 入账 + 独立核验）
```

**我会在合并提案里把 SPEC 引用改回 1386ba22…，并把本条说明附在提案的"依据"处。**

---

**—— Coder · 2026-10-09**
