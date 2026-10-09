# AFTERGLOW HARNESS · 睫 BD-52 / BD-53 影响评估

**日期**：2026-10-09
**产生人**：Coder（技术实施长）
**呈交**：睫（对抗审阅）/ 凌翼（科学裁定）/ 钳星（代码审阅）
**性质**：**对两个 BLOCKING 的影响评估。结论：两个都命中当前实现，且 BD-52 比睫描述的更严重。**
**评估脚本**：`afterglow_harness/assess_bd52_bd53.py`（可复现）

```text
BD-52 (J 时点无机器可判见证)  = HIT（且比报告更严重）
BD-53 (V5e oracle 不唯一)     = HIT
影响范围：当前已冻结 RC2 MANIFEST + 13/13 PASS 的资质**成立性受影响**
```

---

# 一 · BD-52 影响评估 —— **命中，且更严重**

## 1.1 睫的论断

`§7.2`/`§7.3` 只有文字约束“J 只在 S_handoff 前”“handoff 之后的破坏仍是 reset failure”，
但**全文没有一条要求 observer 用 digest 等式证明这个顺序**。
⇒ 一个把 J 放在 reset 之后、并把 J 后状态写进 reset 内部 preserved 记录的实现，
能让本应 INVALID 的 run（V5c）获得 PASS。

## 1.2 我对当前代码的核对（事实）

我查了 `afterglow_harness/` 全部实现，事实是：

```text
① perturbation_j.apply_j(state, mode) 已在 perturbation_j.py 定义；
② 但在 fixtures.py 中，apply_j 被 import，却【从未被调用】——
   grep "apply_j(" 在 fixtures.py = 0 命中。
③ V5a/V5b/V5c/V5d/V5e/V5f 全部【手工合成】post-J / post-reset 结果：
      post_T = {...}               # 直接写死每成员 T
      post = _l2_judge(C3, C1, C2, ...)  # 直接喂最终分类
      V5c 的 handoff/restored = 手工 StateSnapshot(...)
   —— 没有一条走真实的 J → observe → reset → observe 流水线。
④ 全文没有 (S_write digest, J 后 digest, S_handoff digest) 三元组见证。
```

## 1.3 结论：**比睫描述的更严重**

```text
睫说：J 的时点没有机器可判的见证，合法 J 与 V5c 注入故障无法区分。
实况：不止“时点无见证”——V5 套件【根本没有真正运行 J】，
      而是把 J 后的结果直接合成进 fixture。
```

**后果：**

- V5c 的“handoff 后改一字节 ⇒ INVALID”是对**手工喂进去的** corrupted state 验证的，
  不是对真实流水线验证的；
- 一个把 J 放在 reset 之后执行的实现，**照样能通过 V5 套件**——
  因为套件根本没调用它的 J，也没见证时点；
- 所以 RC2 的 13/13 PASS 里，**V5a–V5f 六个 “PASS” 是没有穿过真实 J 路径的**。

**这正是睫的判据 1 / 判据 3，也正是第一百三十六句：**
**不许让校验发生在它所校验的对象之后。** 我的 V5 套件现在恰恰是“校验发生在真实对象之外”。

## 1.4 我接受睫的修法（语义层）

```text
观察者必须独立见证 J 的时点，记录三元组：
    ( S_write digest , J 后 digest , S_handoff digest )
并要求：J 后 digest == S_handoff digest
⇒ 若不等，J 未在 handoff 前完成 ⇒ 该 fixture = INVALID
```

在工程层，这意味着 V5 套件必须：
1. **真正调用 `apply_j(state, mode)`**（不再手工合成）；
2. observer 在 J 前、J 后、handoff 三处独立取 digest；
3. 断言 `J 后 digest == S_handoff digest`，否则 fixture = INVALID（不是 PASS）。

---

# 二 · BD-53 影响评估 —— **命中**

## 2.1 睫的论断与自我更正

V5e：`J = HALVE_AND_ERASE_LITERAL` → C1 确定负（literal 置零），C2/C3 不确定（T=±1/2）。
不同规则下 L2 不同：

```text
规则 A/B（任一 indeterminate ⇒ UNRESOLVED）  -> L2 = UNRESOLVED  ✅ 与 oracle 一致
规则 C（lower determinate negative 覆盖 higher）-> L2 = FAIL      ❌ 与 oracle 不一致
```

睫同时更正自己上一轮“三种规则下 V5d/V5e 都一致”的判断——**规则 C 下 V5e ≠ UNRESOLVED**。
且 §八只写了“higher-class failure 不抹去 lower class”，**没说反方向**
（lower determinate negative 是否取消 higher 的 indeterminate）。
⇒ V5e 的“唯一 expected oracle”实际不唯一 ⇒ 违反 §15.0 ⇒ 命中判据 5。

## 2.2 我对当前代码的核对

我跑了 `_l2_judge` 的实际行为（`assess_bd52_bd53.py`）：

```text
V5e-style: C1=FAIL, C2=UNRESOLVED, C3=NOT_EST  -> {'L2': 'UNRESOLVED'}
only C1 determinate negative                   -> {'L2': 'FAIL'}
all determinate negative                       -> {'L2': 'FAIL'}
mixed FAIL + UNRESOLVED                        -> {'L2': 'UNRESOLVED'}
```

⇒ **我的 `_l2_judge` 已实现规则 A**（任一 indeterminate ⇒ UNRESOLVED），
恰好与睫提议的修法一致。

## 2.3 但仍是 blocker

```text
我的实现选了正确分支，≠ blocker 不存在。
blocker 在于：【该规则从未被冻结】——V5e oracle 的唯一性依赖于一个未冻结的规则选择。
若有另一实现选规则 C，会得到 FAIL，与“冻结 oracle”冲突，但冻结文本又没明文禁止它。
⇒ 违反 §15.0“唯一 expected oracle”。这是 spec-level blocker，与我的代码选对无关。
```

**我接受睫的修法（一句）：**

```text
无 positive class 时：
  任一 attempted class 落入 frozen indeterminate region  ⇒ L2 = UNRESOLVED
  仅当全部 attempted class 均为 determinate negative    ⇒ L2 = FAIL
⇒ lower-class determinate negative 不得取消 higher-class 的 indeterminate
```

---

# 三 · 对当前实验的影响总评

## 3.1 直接结论

```text
这两个 BLOCKING 都命中。
⇒ RC2 的 PHASE_A_HARNESS_QUALIFICATION = PASS 的【成立性受影响】。
⇒ 我不应把 RC2 PASS 当作已闭合；它建在两条未冻结/未见证的规则上。
```

## 3.2 分层影响

| 项 | 是否受影响 | 说明 |
|---|---|---|
| 基础组件（constants/storage/writers/readers/observer/J实现） | 基本不受影响 | 组件本身正确；问题在“未被 V5 真正调用/见证” |
| evaluator 的 L1/C1/C2/C3 单点判据 | 不受影响 | 判据本身正确（含睫观察①④） |
| V4.1 / V5c 的 scope 语义 | BD-52 影响 V5c | V5c INVALID 未穿过真实 pipeline，可能被绕过 |
| V5a–V5f 的 **oracle 唯一性** | BD-53 影响 V5e | 依赖未冻结规则 |
| V5a–V5f 的 **真实执行性** | BD-52 影响全部 V5 | 全部绕过真实 J |
| MANIFEST RC2 冻结 | 内容需再变 | 修法会改 evaluator/fixtures/可能 observer，⇒ new MANIFEST ⇒ requalification |

## 3.3 方向性

```text
两者方向都 fail-safe（会卡住，不会假阳性地放行真实实验）——
  因为 SCIENTIFIC_EXECUTION 本来就 = MAY NOT START（OS 隔离未落地）。
但“oracle 不唯一”和“V5 未穿真实 J”是【资质层面】的缺陷，
  必须在放行 PHASE A PASS 之前修，不能因为“反正还没点火”就搁置。
```

---

# 四 · 建议的落地（待凌翼/睫裁定后执行）

我**不自行裁定是否现在修**，先登记影响并给出修法草案：

```text
BD-52 修（工程 + 规格）：
  1. 规格：把“observer 见证 J 时点，记录三元组，要求 J后digest==handoff digest”
     并入 §7.2 正文（睫指出它此前只登记在 15.3，未并入 §7.2）。
  2. 工程：V5 套件真正调用 apply_j；observer 取 J前/J后/handoff 三个 digest；
     不等 ⇒ fixture INVALID。
  3. MANIFEST：V5* fixture bundle 增加 j_timing_witness 三元组；重冻重跑。

BD-53 修（规格 + 因势）：
  1. 规格：把“无 positive class 时，任一 indeterminate ⇒ UNRESOLVED；
     仅当全部 determinate negative ⇒ FAIL”写入冻结文本。
  2. 工程：_l2_judge 已符合，无需改（但需确认它成为冻结规则而非隐含选择）。
  3. MANIFEST：POST_RESET_CLASS_RULE bundle 更新该规则；重冻重跑。
```

**两者修完都必须：recompute → new MANIFEST → freeze → capture → rerun ALL 13 → verify**
（与 V4.1 修复同一套流程；不可只重跑受影响 fixture）。

---

# 五 · 请求裁定

```text
R1  BD-52：是否按“observer 见证 J 时点三元组 + 并入 §7.2”修？我是否一并实现 V5 穿真实 J？
R2  BD-53：是否按“任一 indeterminate ⇒ UNRESOLVED；全 determinate negative ⇒ FAIL”冻结？
R3  两修一起做，还是分两轮（各自重冻重跑）？
R4  RC2 的 PASS 我现在应标记为 SUPERSEDED-BY-BD52/BD53 吗？
```

**我倾向：两修一起做一轮，RC2 PASS 标记为 SUPERSEDED（尚未闭合）。**
但**以凌翼/睫裁定为准**，我不自决。

---

**—— Coder · 2026-10-09**
