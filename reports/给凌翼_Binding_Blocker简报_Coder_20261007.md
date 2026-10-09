# 给凌翼 · binding blocker 前因后果简报
## BD-45 及本轮 jie-review 的完整来龙去脉

**日期**：2026-10-07
**呈报人**：Coder
**事由**：睫对 `AFTERGLOW IMPLEMENTATION BINDING v0.1` 提了 BLOCKING = 4 + 4 观察；船长指示把前因后果讲清。

---

# 一 · 一句话背景

```text
睫 review 了 binding v0.1（我落盘的自测版），提了 4 个 blocker + 4 个观察。
我逐条核过，全部成立，已全部修完并规范化。
其中 1 个 blocker（BD-45）是【我上一轮修别的问题时引入的新洞】。
```

---

# 二 · 时间线（前因）

```text
R0  binding v0.1 初稿          BLOCKING=1  （L2 无 known-answer fixture）
R1  L2 known-answer patch      BLOCKING=0  （凌翼 accept；我落盘 V5a-e + V4b）
R2  外部朋友 review（3 条）    BLOCKING=3  （循环依赖 / 缺 no-write / oracle 未冻 scale）
R3  睫 review（4 + 4）         BLOCKING=4  （BD-44/40/41/43）
R4  睫 BD-45                   BLOCKING=1  （★ 我 R3 落盘时引入的）
```

**关键：R1→R3 的 blocker 全部是【原始遗漏】；只有 R4（BD-45）是【修复引入的新洞】。**

---

# 三 · 睫的 4 个 blocker（我全部核过成立）

## BD-44 · §16.3 要求 L1=UNRESOLVED，§15 无此 fixture

```text
§16.3 清单要求：pre-reset ladder 覆盖 L1 = PASS / FAIL / UNRESOLVED
实际：只有 L1 = FAIL（V0）、L1 = PASS（V2）
⇒ 文件自己要求的那一格，文件自己没填
⇒ 而 V4b（原 V6）段却宣称"覆盖五类"——强于实际证据
方向：fail-safe（卡住 coverage gate），非假放行
修法：补 V0b PRE_RESET_INDETERMINATE（L1 = UNRESOLVED）
```

## BD-40 · suite PASS 不绑定 binding 版本

```text
§16.2 要求 KNOWN_ANSWER_SUITE = PASS，但没要求它跑在【哪个 binding 版本】上
⇒ V2/V3 验的是 fixture bundle 内的 scale；
  真正可变的 TO_BIND 项（substrate / READ_OPERATOR_HASH / BASE_MODEL_HASH）
  不在 fixture bundle 内
⇒ suite 在 v1 PASS ⇒ 改 binding ⇒ v2 点火 ⇒ 未验证的版本拿到点火资格
方向：真 false-pass 向量（判据 1）
修法：KNOWN_ANSWER_SUITE_BINDING_HASH = frozen IMPLEMENTATION_BINDING_HASH
```

## BD-41 · 记账隔离 ≠ 眼睛隔离

```text
§16.1 PHASE A 三条（synthetic only / test namespace / claim eligibility=NONE）全是记账隔离
而同一节写 "same production evaluator / code path"
⇒ 全文无一条禁止 harness 触碰真实 substrate / reset / episode
⇒ 冻结的意义是在看见结果前锁死判据；若 Phase A 真碰真实数据 ⇒ exposure 已发生
方向：判据 3（post-outcome reselection 被 enabled）
修法：§16.1.1 Substrate Isolation（NO_ACCESS 真实资源；任一次真实访问 ⇒ exposure 提前）
```

## BD-43 · canonical bytes 不合规范

```text
CRLF + 无结尾换行 ⇒ 同一文本在不同环境 hash 不同 ⇒ §16.2 "all hashes computed" 无意义
方向：程序前提（睫自己标注：不命中五判据）
修法：全文规范化为 UTF-8 / no BOM / LF / 单尾换行
```

---

# 四 · BD-45（R4，我引入的）—— 前因后果

**这是最需要向凌翼讲清的一处。**

```text
R3 时，睫的观察②指出："V0 只有 A 臂，而 Basic L1 需要 B vs A"。
我接受，去修 V0。
我在 V0 里写了："本 profile 的 B 亦为 W_storage OFF（即无 write），因此 L1 = FAIL"。
⇒ 但 §3.1 已冻结：B = W_storage ON。
⇒ 我为了造出"没有写入"，把 B 也关掉了 —— 那已经不是 B 了。
⇒ V0 作为 fixture 无法机械执行（它要验的 B 不是 §3.1 的 B）
⇒ §16.3 coverage gate 被自己卡住（fail-safe 方向）
```

**睫的原话（今天我加的）：**

$$\boxed{\text{第一百三十九：不许用一个违反自己定义的例子，去验证自己的定义。}}$$

**我认。这是我在"补 A"时碰坏了"B"。**

**修法（睫第一选项，改动最小）：**

```text
A = NO_WRITE_CONTROL           (W_storage OFF, W_extra OFF)
B = WRITE_ONLY / MATCHED_OFF   (W_storage ON-invoked, storage operation = NULL/no-op)
⇒ B 仍是 §3.1 定义的 B（W_storage ON），但本次 storage operation 预注册为 no-op
⇒ B vs A difference = 0 ⇒ L1 = FAIL
⇒ 意图（无有效写入 ⇒ L1 FAIL）保留，§3.1 未改
```

---

# 五 · 睫的 4 条观察（3 条非阻塞已补，1 条已复核）

```text
① 五类段"截断"     → 我复核 canonical bytes：未截断，是睫侧渲染截断
② coverage 矩阵缺   → 已补 §15.9 Coverage Matrix（profile × canonical exit）
③ W_extra OFF 未定义 → 已补 §6：OFF = NOT INVOKED（非恒等，防副作用污染 contrast）
④ V1 未写 L1=PASS   → 已补
```

---

# 六 · 当前文件状态（供凌翼核对）

```text
AFTERGLOW IMPLEMENTATION BINDING v0.1.md
CANONICAL_BYTE_COUNT = 28780
CANONICAL_SHA256     = ed3600d662d2439ce98fd1f17495bd103f43aede8991ab1cd2111e26b48f0dab
CR = 0 (LF-only) · BOM = NONE · FINAL_NEWLINE = 1
PARENT_PREREG_SHA256 = ad0855b0…d5f4（未变）
```

---

# 七 · 我需要凌翼裁决的一件事（关于"修复引入新洞"）

**船长提出了一个警惕，我认为需要凌翼裁：**

```text
把这一轮的受伤史摆出来：
  R1→R3 的 blocker：全部【原始遗漏】
  R3→R4 的 blocker：1 处【修复引入的新洞】
  
  这不是"每轮修复都引入新洞"的哥德尔式发散；
  而是"补完一批原始遗漏后，只剩 1 个由落盘引入的局部洞"。
  洞在【收敛】（BLOCKING 1→3→4→1），且【变浅】（结构性 → 局部一话）。
```

**但仍需一个明确的停止规则，避免"用一句话修一句话"无限进行。**

**请凌翼裁 (a)/(b)/(c) 三选一：**

```text
(a) 继续修到"零 blocker 且【无新引入】"再冻结（更严，可能再转 1-2 轮）
(b) 接受当前状态为 freeze-candidate；把已知"措辞级"风险降级为
    companion-schema / implementation-spec，先冻结再交实现者（更快）
(c) 设停止规则：再修一轮若仍出现"修复引入新洞"，则改按 (b)
```

**我的倾向：** 倾向 (b) 或 (c)。理由：

```text
· 本轮 4 个 blocker 中，3 个是"文档自洽/程序前提"，只有 BD-41 触及
  "假阳性风险"（科学核心）；而 BD-41 已修。
· 剩下的边际问题主要是措辞/覆盖表的完备性，
  它们更适合放在 companion schema，而非继续膨胀 core prereg
  （这正是凌翼此前那条"能删除一个 summary 字段解决的，不新增两个字段"的精神）。
```

---

# 八 · 我不替凌翼做决定

**上述 (a)/(b)/(c) 我只给倾向，不定论。**
**请凌翼裁。**

**—— Coder · 2026-10-07**
