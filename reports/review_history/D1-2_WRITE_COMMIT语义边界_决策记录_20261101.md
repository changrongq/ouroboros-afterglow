# D1-2 · WRITE_COMMIT 语义边界决策记录

**日期**：2026-11-01
**授权**：凌翼 D1-2（`D1_DESIGN_WORK = AUTHORIZED`，不含实施）
**性质**：**架构决策记录**。不实现、不改冻结件、不申请授权。

---

# 零 · 结论先行

```text
1. 建议【弃用】 WRITE_COMMIT 这个名称。
   ⇒ 它把四个不同事件压成了一个词，
     而当前实现只能产生其中两个。

2. 四个事件分开命名，且必须标注【可产生性】：
     WRITE_OPERATION_RETURNED    可产生
     STATE_WRITE_COMPLETED       可产生
     STATE_DURABILITY_CONFIRMED  【不可产生】当前无 fsync
     EVENT_RECORD_ACKNOWLEDGED   【不可产生】当前无记录者

3. 允许进入 SNAPSHOT 阶段的条件：
   ⇒ 只能基于【可产生】的事件，且不得越过它们声称更强的东西。
```

---

## 一 · 四个事件的当前可产生性（源码核对）

> **2026-11-01 修正（知微 Z-D1-06）**
> ```text
> ⇒ 原标题写「实测」，但本文§四已明写未运行任何实验。
> ⇒ 本节结论全部来自【读源码】，改为「源码核对」。
> ```

`[已核对源码]`

```text
事件                        当前实现能否产生      依据
WRITE_OPERATION_RETURNED    能                  storage.py L99-105 / L107-109 正常返回
STATE_WRITE_COMPLETED       能                  storage.py L59-61 with 退出即 close
STATE_DURABILITY_CONFIRMED  【不能】            storage/observer/writers fsync 计数 = 0
EVENT_RECORD_ACKNOWLEDGED   【不能】            记录者原语不存在
```

> **2026-11-01 修正（睫 · 209·二）**
> ```text
> 原写「storage.py L99 / L107 正常 return」——
> 但 L99 是 def write_literal，L107 是 def write_substrate，
> 【都是 def 行】，return 不在那两行上。
> ⇒ 语义可达（两函数确实正常返回），但行号指错。
> ⇒ 已改为 L99-105 / L107-109。
> ```
>
> ```text
> 另：睫指出「记录者原语总数 = 0」我只能证明【四个文件】内为 0，
> 不能证明全仓为 0（仓库文件清单取不到）。
> ⇒ 准确表述：storage / writers / observer / evaluator 四文件内零命中。
> ⇒ 全仓是否为零 = NOT VERIFIED。
> ```

```text
⇒ 这不是设计取舍，是【材料现状】。
⇒ 任何声称当前能产生后两个事件的表述都是错的。
```

---

# 二 · 逐问回答（凌翼五问）

## 问 1 · 哪个事件表示状态写入操作已经完成？

```text
答：STATE_WRITE_COMPLETED
    = storage.py L61 f.write(data) 完成且 L60 with 块正常退出（文件对象已关闭）
```

> **标记层级说明（知微 Z-D1-06 / 睫 209·二）**
> ```text
> ⇒ 本节结论来自【读源码】，不是【跑实验】。
> ⇒ 因此标 [已核对源码]，不标 [已实测]。
> ⇒ 标题里若出现「实测」二字，必须附固定运行证据；本文未运行任何实验。
> ```

**为什么不是 WRITE_OPERATION_RETURNED：**

```text
⇒ 函数返回可以发生在写入仍然只有部分成功的情形
  （例如 mode 分支提前 return、或异常被上层吞掉）。
⇒ 更关键：函数返回是【调用方视角】，
   STATE_WRITE_COMPLETED 是【文件对象视角】。
⇒ 前者不能推出后者。
```

```text
但要立刻说明它的边界：
⇒ STATE_WRITE_COMPLETED 【不】代表持久化。
   它只代表「数据已交给操作系统，文件句柄已关闭」。
⇒ 掉电或系统崩溃仍可能丢失。
```

## 问 2 · 哪个事件仅表示日志获得了确认？

```text
答：EVENT_RECORD_ACKNOWLEDGED
    = 记录者确认某条事件记录已持久化（fsync 返回）
```

```text
⚠ 关键约束：
⇒ 该事件【仅】关于【事件日志】，不关于【目标 STATE 文件】。
⇒ 两者是两个独立的持久化保证（协议 §3.4 已定）。
⇒ 不得从 EVENT_RECORD_ACKNOWLEDGED 推出 STATE_WRITE_COMPLETED，
   更不得推出 STATE_DURABILITY_CONFIRMED。
```

```text
⇒ 当前【无法产生】此事件，因为记录者不存在。
```

## 问 3 · 哪些条件必须满足才允许进入观察或快照阶段？

```text
分两级回答，因为材料分两级。
```

**级 A · 拟议的分臂条件（只用可产生的事件）**

> **2026-11-01 二次修正（知微 Z-D1-06）**
> ```text
> ⇒ 原标题写「当前可实现的条件」，但表内又要求「事件已记录」。
>    而 §四三层表已明写：当前只知动作可发生，记录能力尚未建立。
> ⇒ 已改名为【拟议的分臂条件】，能力状态引用 §四三层表。
> ```

> **2026-11-01 修正（知微 Z-D1-04）**
> 原文把 STATE_WRITE_COMPLETED 当作【无条件】前置。
> 而本文自己的 STORE_NULL 反例就说明这种事件可以不存在。
> **后果：不写入臂与零效果对照永远不能进入观察。**

```text
⇒ 规则必须限定为「本次注册计划要求的动作」，
   而不是「所有臂都必须有写入完成事件」。
```

**按注册语义分类（writers.py L82-84 / fixtures.py L167-179）：**

| 臂类型 | 应产生的事件 | 阶段完成依据（拟议） |
|---|---|---|
| 真写入（STORE_FULL / STORE_ONE_BYTE） | STATE_WRITE_COMPLETED | 目标绑定的真实写入路径正常完成并正常关闭 |
| STORE_NULL（调用但零效果） | WRITE_OPERATION_RETURNED，**无** STATE_WRITE_COMPLETED | 真实调用完成 + 关闭/能力边界成立（**不含**观察） |
| OFF / 未调用（如 A 臂不调用本次存储写入） | **两个都无** | 注册为不调用，且已核实确实未被调用 |
| 幂等写入（写入值 == 当前值） | STATE_WRITE_COMPLETED | 目标绑定的真实写入路径正常完成并正常关闭（**不是**「按调用判」） |

> **2026-11-01 二次修正（知微 Z-D1-04 / Z-D1-06）**
> ```text
> ① 原 STORE_NULL 行写「且已观察到状态未变」作为阶段完成依据。
>    ⇒ 这是【循环前置】：
>       允许 after 快照 → 需已观察 before/after 未变
>                      → 需已取得 after 快照 → 需允许 after 快照
>    ⇒ 已改：【允许观察】与【观察后是否满足零效果对照】分开。
>       前者不含观察；后者才依据独立的 before/after 观测核对。
>
> ② 幂等行原写「按调用判，非按效果」——比反例 3 的正确定义弱。
>    ⇒ 已改为「真实写入路径正常完成并正常关闭」。
>
> ③ 层名改为【拟议】阶段条件：
>    当前能力只支持「动作可发生」，记录能力尚未建立（见 §四三层表）。
> ```

**允许观察 vs 观察后的判定（两件事）：**

```text
允许进入观察/快照：
  · 注册动作已按语义完成（真实调用 + 关闭/能力边界）
  · 对象/执行身份一致
  · 适用的时序证据已成立（**【非】「若可得」**）
  ⇒ 【不】要求「已观察到状态未变」

【2026-11-01 三次修正（知微 R2）】
⇒ 原文写「时序证据成立（若可得）」。
⇒ 这把【必需条件】降成了【可选】：
   没有顺序证据时，该可以「不适用」而跳过，
   而 TIME_GATE 又要求必须阻断。
⇒ 已删「若可得」：适用时序证据未建立 ⇒ 该正式阶段门【不成立】、不得放行。
   （注：此指已定义的正式门，不把普通读文件动作说成不可能。）

观察后的零效果对照判定：
  · 依据独立的 before/after 观测核对状态变化
  · 发现变化 ⇒ 按适用对照规则处理
  ⇒ 此为【观察的产物】，不是观察的【前置】
```

```text
⇒ 共同门不应检查「所有臂都有写入完成事件」，
   而应检查：
     (a) 该臂已按【注册语义】结束
     (b) 对象/执行身份一致
     (c) 相应能力边界成立
     (d) 观察时序成立

⇒ 初始化基线属于【不同阶段的动作】，
   不能拿它冒充本次干预的写入完成。
```

```text
⚠ 不允许的做法：
  · 为放行而伪造写入事件
  · 把 no-write 分支无证据地默认通过
  · 修改冻结 fixtures

NO_WRITE_PATHS_REQUIRE_EVIDENCE = YES
```

**级 B · 若要有充分条件（需未来能力）**

> **2026-11-01 修正（知微 Z-D1-05）**
> 原文标题写「ALLOW_SNAPSHOT（充分）」，
> 暗示满足 (a)(b)(c) 就可以接受整个快照。
> **这是过度承诺。**

```text
两者必须分开：

  TIME_GATE_SUFFICIENT_FOR_STAGE_ADVANCE
    = TIME_GATE 的三项（定义见下），是【时序门】的局部充分条件

  ALLOW_SNAPSHOT_SUFFICIENT_FOR_CONSISTENT_SNAPSHOT
    = NOT ESTABLISHED（需另行成立的前提）
```

**静态反例（知微给出）：**

```text
注册 writer 已返回并关闭本地窗口，日志与顺序均成立；
但另一仍有写权限的主体在两次读取之间修改了对象。
⇒ 级 B 三项可全部满足，但快照并不一致。
```

```text
根源：storage.py L120-122 的 __exit__ 只调 _close_write_window()，
      后者改的是【进程内布尔值】，不是 OS 层权限撤销。
      L73-74 仍然是两次顺序读。
```

```text
⇒ 若要声称整体 ALLOW_SNAPSHOT 充分，必须另行引用：
    · 对象身份稳定
    · 观察权限成立
    · 写能力已被真正限制
    · 读取区间一致性
⇒ 本篇【不】重新设计整套隔离，只标注边界。
```

**TIME_GATE 三项的定义（2026-11-01 补齐，知微 Z-D1-05）：**

> ```text
> ⇒ 原文引「级 B 的三项」，但本版已删上一版的三项清单，
>    该引用失去定义。此处直接列出，不再引用旧清单。
> ```

```text
TIME_GATE（时序门）三项：

  (1) 该臂的注册动作已按语义完成
      ⇒ 与四类动作表一致
      ⇒ 【不】要求无条件的 STATE_WRITE_COMPLETED
        （STORE_NULL / OFF 臂本就不产生该事件）

  (2) WINDOW_CLOSE 已达 ACK_RECEIVED
      ⇒ 当前【不可产生】（无记录者、无收件证据链）

  (3) 顺序证据成立（ELIGIBLE_ORDER_EVIDENCE）
      ⇒ 当前【不可产生】（无时序号）
```

```text
⇒ (2)(3) 当前均不可产生
   ⇒ 故 TIME_GATE 当前 = NOT SATISFIABLE
⇒ 不得机械复原上一版的「无条件 STATE_WRITE_COMPLETED」作为 (1)
```

## 问 4 · 哪些保证目前无法建立？

```text
逐条列，不概括：
```

| 保证 | 状态 | 原因 |
|---|---|---|
| 状态写入已持久化 | **NOT ESTABLISHED** | 无 fsync |
| 日志已持久化 | **NOT ESTABLISHED** | 无记录者 |
| 写入发生在窗口内 | **NOT ESTABLISHED** | 无时序号 |
| 快照晚于窗口关闭 | **NOT ESTABLISHED** | 无时序号 |
| 快照原子性 | **NOT ESTABLISHED** | storage.py L73-74 两次独立读 |
| 崩溃后状态可恢复 | **NOT ESTABLISHED** | 无日志、无恢复流程 |
| 写入的实际持久化顺序 | **NOT ESTABLISHED** | 无顺序原语 |

```text
⇒ 七项全部 NOT ESTABLISHED。
⇒ 这不是悲观，是逐项核对后的结果。
```

## 问 5 · 是否应弃用含义不明确的 WRITE_COMMIT 名称？

**答：应当弃用。**

```text
理由一：它同时被用来指四个不同事件
  ⇒ 这正是 P0-3 与 D1-2 反复出现分歧的根源。

理由二：它暗示了一个当前不存在的保证
  "commit" 在日常语义中意味着「已确认提交」，
  而当前最多只能达到 STATE_WRITE_COMPLETED（未持久化）。

理由三：它是唯一一个【跨越两个持久化层】的名称
  ⇒ 日志层与状态层被它混成了一个词。
```

**建议的替代命名：**

```text
弃用：WRITE_COMMIT

改用（按需选择，不设统称）：
  WRITE_OPERATION_RETURNED      写函数返回
  STATE_WRITE_COMPLETED         状态文件写入完成
  STATE_DURABILITY_CONFIRMED    状态持久化已确认
  EVENT_RECORD_ACKNOWLEDGED     事件日志已确认

⇒ 若必须有一个【协议内】的锚点，
   应使用 STATE_WRITE_COMPLETED，
   并在每次使用时注明它不是持久化保证。
```

---

# 三 · 反例对照（凌翼要求「必要的反例对照」）

## 反例 1 · 用日志 ACK 冒充状态写入

```text
构造：记录者确认 WINDOW_CLOSE 已持久化，
      但目标 literal.bin 从未被写入。

错误实现：从 EVENT_RECORD_ACKNOWLEDGED 推出 STATE_WRITE_COMPLETED。

为何错：
  日志与状态是两个独立的持久化目标
  （协议 §3.4；storage.py L59-61 与记录者写的是不同文件）。

期望：必须被判为不可推出 ⇒ INVALID（若被当作证据使用）
```

## 反例 2 · 用函数返回冒充写入完成

```text
构造：writers.py storage_write 在 mode == STORE_NULL 时
      【被调用但什么都不写】然后 return。

事实依据 `[已核对源码]`：writers.py L82-84
      if mode == STORE_NULL:
          # called, but zero-effect: registered state is untouched.
          return                          （零效果）

错误实现：以函数返回作为「状态已写入」的证据。

为何错：
  STORE_NULL 下函数返回了，但状态一个字节没变。
⇒ 函数返回 ⇏ 状态写入。

期望：WRITE_OPERATION_RETURNED 存在而 STATE_WRITE_COMPLETED 不存在
      ⇒ 必须可区分，不得合并
```

## 反例 3 · 幂等写入

```text
构造：写入值等于当前值。

错误实现：以「摘要变化」作为 STATE_WRITE_COMPLETED 的证据。

为何错：
  COLLAPSE_SIGN 的语义是：非零 q → +2；q = 0 → 0。
  ⇒ 若 q 已为 +2，写入幂等，摘要不变。
  ⇒ 若 q 为 0，写入 0，同样幂等。
  ⇒ 两种情形下摘要都不变，但写入路径确实执行了（静态推理，非本篇实测）。

期望：STATE_WRITE_COMPLETED 必须由【真实写入路径正常完成】判定，
      不由【效果】判定，也不由【调用开始/计数】判定。
```

> **2026-11-01 修正（知微 Z-D1-06）**
> 原文结尾写「必须由【调用】判定」——这比问 1 的定义更弱。
> ```text
> ⇒ 调用后可能在 open、write 或 close 时异常，不能签发完成事件。
> ⇒ STORE_NULL 本身就是「调用了但什么都没写」的证据。
> ⇒ 正确表述：与目标对象绑定的真实写入路径【正常完成并正常关闭】。
> ```

**三层必须分开（知微 Z-D1-06）：**

```text
层 1  底层动作在正常路径可发生      ← 当前源码静态可判
层 2  有独立、可绑定的观测证据      ← 当前【无】
层 3  已形成并持久化协议事件        ← 当前【无】

⇒ 当前源码只支持层 1 的静态判断。
⇒ 因此「级 A：已记录 STATE_WRITE_COMPLETED」不能仅凭
   存在 with/open 路径就宣称已有【记录能力】。
⇒ 准确说法：
   STATE_WRITE_COMPLETED_CAN_OCCUR       = YES（静态）
   STATE_WRITE_COMPLETED_IS_RECORDED     = NOT ESTABLISHED
```

---

# 四 · 与既有裁定的关系

```text
⇒ 本记录【不】改变 O-1/O-2/O-3/O-4/O-6/O-7 任何一项。
⇒ 本记录【只】回答 D1-2 五问。
⇒ 与协议 §3.4（日志≠业务持久化）一致，且是其细化。
```

```text
⚠ 不得通过日志 ACK 冒充真实状态写入或持久化证明
   —— 这是凌翼 D1-2 的明令，本记录 §2 问 2 与 §3 反例 1 专门回应。
```

---

# 五 · 状态

```text
D1_2_WRITE_COMMIT_DEFINITION   = PROPOSED（待裁定）
WRITE_COMMIT_NAME              = RECOMMEND_DEPRECATE
WRITE_OPERATION_RETURNED       = PRODUCIBLE
STATE_WRITE_COMPLETED          = PRODUCIBLE
STATE_DURABILITY_CONFIRMED     = NOT PRODUCIBLE（无 fsync）
EVENT_RECORD_ACKNOWLEDGED      = NOT PRODUCIBLE（无记录者）

ALLOW_SNAPSHOT_NECESSARY       = DEFINED（级 A）
ALLOW_SNAPSHOT_SUFFICIENT      = NOT ESTABLISHED（级 B）

CODE_CHANGE                    = NOT AUTHORIZED
IMPLEMENTATION_AUTHORIZATION   = NONE
SCIENTIFIC_EXECUTION           = MAY NOT START
FROZEN_Q3_RC11                 = UNCHANGED
```

---

# 六 · 一句

```text
这五问其实只有一个答案：

四个事件里，当前真正能发生的只有两个。
而 WRITE_COMMIT 这个名称，
恰好让人以为另外两个也已经发生了。
```
