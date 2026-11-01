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

# 一 · 四个事件的当前可产生性（实测）

`[已核对源码]`

```text
事件                        当前实现能否产生      依据
WRITE_OPERATION_RETURNED    能                  storage.py L99/L107 正常 return
STATE_WRITE_COMPLETED       能                  storage.py L59-61 with 退出即 close
STATE_DURABILITY_CONFIRMED  【不能】            storage/observer/writers fsync 计数 = 0
EVENT_RECORD_ACKNOWLEDGED   【不能】            记录者本身不存在（原语总数 = 0）
```

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

**级 A · 当前可实现的条件（只用可产生的事件）**

```text
ALLOW_SNAPSHOT 需要：
  (a) 该次写入已记录 STATE_WRITE_COMPLETED
  (b) 写入窗口已关闭（storage.py L112-124 __exit__ 已执行）
  (c) 快照发生时刻晚于窗口关闭

⇒ (a)(b) 当前可产生。
⇒ (c) 当前【不可判定】——没有时序号，无 fb 序。
```

```text
⇒ 因此级 A 是【必要条件】，不是充分条件。
⇒ 满足 (a)(b) 仍【不足以】声称快照合法。
```

**级 B · 若要有充分条件（需未来能力）**

```text
ALLOW_SNAPSHOT（充分）需要：
  (a) STATE_WRITE_COMPLETED 已发生
  (b) 记录者确认 WINDOW_CLOSE 已达 L3（EVENT_RECORD_ACKNOWLEDGED）
  (c) 且顺序证据成立（协议 §4.2b 的 ELIGIBLE_ORDER_EVIDENCE）

⇒ (b)(c) 当前均不具备。
⇒ 故当前 ALLOW_SNAPSHOT(充分) = NOT ESTABLISHED
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
构造：写入值等于当前值（已实测，摘要不变）。

错误实现：以「摘要变化」作为 STATE_WRITE_COMPLETED 的证据。

为何错：
  COLLAPSE_SIGN on q=+2 → 摘要不变，但写入确实发生了。

期望：STATE_WRITE_COMPLETED 必须由【调用】而非【效果】判定
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
