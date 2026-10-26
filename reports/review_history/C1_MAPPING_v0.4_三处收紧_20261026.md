# C1 EXECUTION DESIGN MAPPING v0.4 · MANIFEST 依据更正 / RE-G 重定义 / CAND-α 补业务语义

**性质**：对 `61e32c1`(v0.3) 的就地勘误与补齐。不构成实现或科学执行授权。
**被审对象**：v0.3，SHA-256 `452f4a0a424e7df69e2f7ed48417f637299e676fcfc96a52ec780d08c137b3ba`
**审阅输入**：知微 `§二 / §三 / §四 / §五 / §六`；睫 `NB-22 / NB-23 / NB-24 / T-6 裁定`；钳星（接受 §5.2 限定，收回"天然回避"四字）
**基线（自述）**：`61e32c1c26520cf729fb1dfb3ad3e6bb2b04049c`

```text
CANDIDATE_PROPOSAL_STATUS = PROPOSED_PENDING_REVIEW
REAL_CANDIDATE_IDENTITY   = NOT ESTABLISHED
CODE_CHANGE                      = NOT AUTHORIZED
SCIENTIFIC_EXECUTION             = MAY NOT START
FROZEN_Q3_RC11                   = UNCHANGED
```

---

# 0 · 我这一轮的两处新错

## 0.1 E-5 · `CONTENT_CLASS_MANIFEST` 不是"没有" —— 我又把"有"写成了"无"

**我 v0.3 §6.1 写（拆四件）：**

```text
① 内容标签        = payload 内的 cls=L/R 两字符        → 存在
② 类别登记对象    = reference 未以 manifest 形式登记    → NOT ESTABLISHED   ← 错
③ 规则/hash 绑定  = CONTENT_CLASS_MANIFEST_HASH 无实际值 → NOT ESTABLISHED   ← 错
④ C1 的实际依赖   = C1 class rule 未要求 content class   → 成立
```

**字节说：**

```text
manifest_bind.py L273-291   CONTENT_CLASS_MANIFEST = {
                              "classes": {"L": {"episodes": ["A1","A2"]},
                                          "R": {"episodes": ["B1","B2"]}},
                              "episode_payloads": {...},
                              "payload_length": 16,
                              "same_class_pairs": [["A1","A2"],["B1","B2"]],
                              "cross_class_pairs": [["A1","B1"],["A2","B2"]],
                              "distinct_procedures": [...],
                            }                                        [读文件]
manifest_bind.py L396  "CONTENT_CLASS_MANIFEST_HASH": hash_obj(CONTENT_CLASS_MANIFEST)
manifest_bind.py L397  "CONTENT_CLASS_EVIDENCE_SET_HASH":
                          hash_obj(CONTENT_CLASS_MANIFEST["episode_payloads"])

MANIFEST L348-351                                              [读文件]
  CONTENT_CLASS_MANIFEST_ID   = SYNTHETIC_CONTENT_CLASS_MANIFEST_V1
  CONTENT_CLASS_MANIFEST_HASH = 27616f8b1f8b0bdcb82c0c1aeb6cb6d78c6d038c96817776cf96f0f16600c75a
  CONTENT_CLASS_EVIDENCE_SET_ID   = SYNTHETIC_CONTENT_CLASS_EVIDENCE_SET_V1
  CONTENT_CLASS_EVIDENCE_SET_HASH = d98d544c27ae76a334d9b5732ddfdbaba189ec790ab61943e8a436934324982c
```

**⇒ ② 有对象（`manifest_bind.py` L273 起，完整结构含 classes / episode_payloads / pairs / procedures）。**
**⇒ ③ 有构建路径（L396-397）且 MANIFEST 已登记实际值（L349、L351）。**

**⇒ 我在 v0.3 里把这两个"有"写成了两个"无"。**

**这是同一个反向错误的第二次：v0.3 的 R-1 是"把无写成有"，v0.3 的 E-5 是"把有写成无"。三面是同一面——我用一次扫描的命中情况，代替了"这一层到底是什么"。**

**正确表述（照知微措辞）：**

```text
参考类别对象与登记值            = EXISTS（manifest_bind.py L273-291 / L396-397；
                                     MANIFEST L348-351）
真实候选的对应登记/适用性        = NOT ESTABLISHED
hash 语义的独立重算              = NOT PERFORMED
                                    （本轮只读到登记值，不运行构建脚本，
                                      不把"读到"说成"独立验证全部语义"）
```

## 0.2 E-6 · 「episode 唯一载体是 payload 内两个字符」也过强

**我 v0.3 §2.1 写：** 「episode 与 payload 在 reference 里是同一个字节串」→ 推论「episode 唯一载体是 payload 内两个字符」。

**知微指出**：参考系统还有 A1/A2/B1/B2 键、类别对象、fixture 配置和 ledger。它们不是唯一 execution 身份，**但不能全被两个字符代表**。

**⇒ 接受，改为：**

> **内容字节与状态摘要不能独自证明本轮执行来源；参考关联不能代替真实绑定。**

**⇒ 并且这句话恰好就是 RE-F 改名的理由。我原来想用一个"更严重"的发现来支撑 RE-F，其实 RE-F 不需要那个发现——它需要的就是这一句。**

---

# 1 · RE-G 重定义（知微 P1，我接受）

## 1.1 我 v0.3 写的

```text
RE_G 关闭须两件齐备：
  ① §37 的 39 条逐条 disposition 完毕
  ② 声明"其他章节无同类条款"，并给出该声明的 grep 取法
```

## 1.2 知微的反驳

**⇒ 其他章节确实有必要条件**：§4 执行关键绑定缺失则不得启动；§11 observer 独立性；§13 五项 gate/class rule；§28.1 witness；§29 invalidity 分类。

**⇒ 且 grep 只能定位字面命中，不能证明语义上不存在其他要求。本轮 BF-8 修正本身就说明了这个差别。**

**我核字节，确认这些章节确实有约束：**

```text
prereg §4  L159  "任何实际 execution 启动前，必须生成并冻结"        [读文件]
prereg §11 L619-625  observer != write operator / cannot write /
                     reads independently / computes independently /
                     W 不能认证自己已经改变 state
prereg §13 L702-711  五项 gate 条件
prereg §28.1          witness scope
prereg §29            invalidity 分类
```

## 1.3 改为

```text
RE_G_CLOSURE_REQUIRES（照知微建议）：
  对固定候选、固定 attempted claim，完成
    ① §37 已列 39 项的逐项适用性、证据、判定位置和后果映射
    ② 沿相关章节及交叉引用纳入额外适用要求
    ③ 记录不适用理由与尚未解决项
  不得遗漏已识别的必要条件。

不能要求"搜不到其他条款"才能关闭。
```

**⇒ 状态：**

```text
RE_G_SECTION37_FULL_APPLICABILITY = STILL_PENDING
  └ 上一版的两个子项（39 条 / 无其他章节声明）作废
  └ 新子项：
      RE_G_A_39_ITEMS_DISPOSITION     = NOT DONE
      RE_G_B_CROSS_SECTION_SWEEP      = NOT DONE（§4/§11/§13/§28.1/§29 已识别，未逐项落位）
      RE_G_C_NOT_APPLICABLE_REASONS   = NOT DONE
```

---

# 2 · 睫 NB-22 · MANIFEST L266 的 hash 未标语义（采纳）

## 2.1 字节确认

```text
MANIFEST L166  STORAGE_WRITER_COMPONENT_HASH = ae64731b...      ← 名字带 COMPONENT_HASH
MANIFEST L423  writers.py 1.0 08f7d968...                       ← 文件摘要

MANIFEST L266  state_observer_hash = f8b68319...                ← 名字没说是哪种
MANIFEST L425  observer.py 1.0 82d244cd...                      ← 文件摘要

我算 observer.py = 82d244cdc8ecdaa0916c342b9aa266416314f9af7ca5e77be3a224788159d8fd
      ⇒ 与 L425 逐位相同                         [终端核验，非抄写]
我算 writers.py  = 08f7d968bdb4aa37c206e169cabbb08b9616b0990c0e758e7958c93c6b5b690c
      ⇒ 与 L423 逐位相同                         [终端核验]
```

**⇒ writer 侧：两个值不同，但**两者都在**，且名字区分了语义（`COMPONENT_HASH` vs 文件摘要行）。**
**⇒ observer 侧：完全同形（`f8b68319…` 组件值 + `82d244cd…` 文件摘要），但 L266 的字段名 `state_observer_hash` 没标是哪种。**

## 2.2 睫的判断我接受

> 那不是"两个值不一致"。那是"一个值没标自己是哪一种"。

**⇒ 于是这一格可以关，且关法便宜**（二选一）：

```text
① 把 L266 改名为 state_observer_component_hash（照 writer 的写法）
② 在 L266 旁注明"此为组件 hash，文件摘要见 L425 = 82d244cd"
```

**⇒ 但这是文档性修改，须凌翼一次授权。`CODE_CHANGE = NOT AUTHORIZED`，本文件不改 MANIFEST，只登记建议。**

## 2.3 我在 v0.3 标的 `hash 语义对照 = NOT PERFORMED` 的修正

**分解为三件，不再合并：**

```text
值是否都在              = YES（三者全在）
两个值是否相同          = NO（f8b68319 ≠ 82d244cd）
各自语义是否已标清      = NO（L266 未标）← 睫 NB-22 的落点
file-hash 是否可独立重算= YES（我算了，与 L425 一致）
component-hash 是否已重算= NO（须跑 hash_obj，本轮未做）
⇒ 结论：登记完整，命名不完整。
```

---

# 3 · 睫 NB-23 · CAND-α 的"自身 execution 身份回执"（采纳，且这是本轮最重要的修改）

## 3.1 我 v0.3 §4.1 写的

```text
【被测对象 W】
  · 输出（STDOUT / 退出码）：写入结果 + 【自身 execution 身份回执】
```

## 3.2 睫的判，字节支持

```text
prereg L625  "`W` 不能认证自己已经改变 state。"              [读文件]
```

**⇒ W 不能认证"我改变了 state"（已明文）。**
**⇒ 而 W 认证"我是哪一次执行"，是同一件事的另一半。**

**⇒ 若 W 可以自证"我是 A1 这一次"，那么"W 改变了 state"这一格就只剩"state 确实变了"——而那由观察者看。**
**⇒ 于是 W 自证身份 + 观察者看见变化 = 一次完整的 C1 证据。**
**⇒ 而那条链上，没有任何一格由独立主体说出"是哪一次"。**

**⇒ 这条我要照录，并且它是本轮最该早停的一格：CAND-α 还是纸，改它成本是删半行字；等它实现了再改，成本是"我们已经用它跑过一次"。**

## 3.3 修改后（v0.4 起生效）

```text
【被测对象 W】
  · 一个独立可执行体，单次运行完成一次 episode 的 registered write 后退出
  · 输入：episode payload（16 字节）+ 本次 execution 身份（来自注册记录，不来自 payload）
  · 输出（STDOUT / 退出码）：写入结果（诊断用）
       ★ 不得作为 episode / execution 身份的证据来源
  · 生命周期：进程创建 → 打开写窗口 → 写入 → 关闭写窗口 → 退出
  · 退出后不再持有任何该对象的句柄

【execution 身份（修订）】
  · 由观察者 / 控制器独立记录并进入 META
  · W 的 STDOUT 回执降为诊断，不进入证据链
```

**⇒ 与 §4.1 原有"META 侧独立记录 episode_id / execution_id"一致，只需把 W 回执那一格降级。**

---

# 4 · 睫 T-6 裁定 + NB-24 · RE-F 第三类补充

## 4.1 T-6 裁定（睫已裁，我照录）

```text
T-6 = NOT ESTABLISHED
  ⇒ 不列为 C1 通用前提（与知微一致）
  ⇒ 且不由本轮勘误生成（与我一致）
依据：prereg L722-724 C1 class rule 全文没有 "first"
```

**⇒ 睫的自我判词我也照录，因为它解释了越界的两种形状：**

> 以前我越界的方式是：把"我怕"写成"必然"（cannot）。
> 这一次我越界的方式是：把"我怕"写成"前提"（首次执行证据）。
> 两句话不一样，动作是同一个：我担心的东西，我不许它只是一个担心。我要它进合同。
> 而一个担心进合同的唯一合法路径，是证明它是那个 claim 成立的必要条件。而"历史首次"不是。

## 4.2 NB-24 · RE-F 第三类补充（采纳）

**v0.3 §3.3 有三类情况。睫补第四类（他编号为第三类补充）：**

```text
同一 episode 的重复执行（每次都用本轮合法 before/after）
  ⇒ 证据计数【不增加】
  ⇒ 它是 repeatability control（§20.1 L1181 字节）
  ⇒ 不得作为 class-level generalization（C3）
  ⇒ 也不得累加为多个独立的 C1 证据

理由：C1 class rule 要求 "an episode-specific … write" —— 一个 episode 一次。
      同一个 episode 跑十次，不是十个 C1。
而这一条最容易被漏掉，因为重复执行看起来最像【更多证据】。
```

**⇒ 落入 RE-F 状态：**

```text
RE_F_CURRENT_EXECUTION_EVIDENCE_BINDING = NOT ESTABLISHED
  ├ 第一类（旧快照冒充本轮 after）      → INVALID
  ├ 第二类（同内容重复执行，本轮证据齐）→ 按 gate + class rule 判，不预设
  ├ 第三类（同 episode 重复执当作 C3 泛化）→ C3 NOT ESTABLISHED，可作 repeatability control
  └ 第四类（睫 NB-24）：同 episode 重复执行 → C1 证据计数不增加
```

---

# 5 · CAND-α 补业务语义（知微 P4，我接受：不能只有名称与文件布局）

知微要求补一段：**写入的是何种真实业务状态、episode 怎样产生、W 将怎样转换它、后续哪个计算读取这些字段**。

**⇒ 我必须在提出之前先说明一件事：我不知道被测系统是什么。这是 T-8 归凌翼的原因。**

**⇒ 所以我给出的不是我选定的业务，而是**三个候选业务形态**，各自写明"如果它成立，则 C1 的这些都成立"，并标注哪一项仍未知。**

## 5.1 候选业务形态（三选一，我不选）

### 形态 P-1 · 对话记忆写入

```text
业务状态        = 一段被判定为"值得长期保留"的对话摘要
episode 怎样产生= 一次用户交互（同一轮对话 = 一个 episode）
W 怎样转换它    = 从交互文本提取摘要 → 编码为固定宽度记录 → 写入持久存储
后续谁读取      = 下一轮对话开始时的 context 组装
C1 的落点       = "本次交互是否写入了一条 registered 记忆"

未知项：
  · 摘要提取是否可重复（同一交互两次提取是否同字节）← 影响重复执行判定
  · context 组装是否真的读取该记录（否则写入无业务后果）
  · 记录宽度是否可固定（若可变长，16 字节规格不适用 ⇒ T-2）
```

### 形态 P-2 · 工具调用结果缓存

```text
业务状态        = 一次外部工具查询的结果快照
episode 怎样产生= 一次工具调用（同一请求参数 = 同一 episode）
W 怎样转换它    = 结果规范化 → 写入缓存键位
后续谁读取      = 下次同参数查询时的缓存命中
C1 的落点       = "本次调用是否写入了缓存"

未知项：
  · 缓存本身是否就是业务状态，还是仅是加速层（若是加速层，可能不属 registered substrate）
  · 过期/淘汰机制会引入非 episode 的写入（会污染 C1）
  · 键位是否含时间戳（若含，等于把身份塞进 STATE ⇒ 违反 §7.2）
```

### 形态 P-3 · 状态机持久化

```text
业务状态        = 一个显式状态机的当前状态
episode 怎样产生= 一次状态转移请求
W 怎样转换它    = 校验转移合法性 → 写入新状态
后续谁读取      = 下次转移时的合法性校验
C1 的落点       = "本次转移是否持久化了新状态"

未知项：
  · 状态转移天然是 q 的变化（可能落入 C2/C3 而非 C1）
  · 状态机定义本身属"规则"，须在 outcome 前冻结
  · 若状态转移失败需回滚，回滚写入也会被观察者看到（会污染 before/after）
```

## 5.2 我必须说清的边界

```text
⇒ 这三个形态都是【我构造的】，不是凌翼指定的科学范围。
⇒ 我不选，因为"被测系统本来是什么"不是设计映射能定的（T-8）。
⇒ 我只提供：如果选 P-1/P-2/P-3，则 C1 的这些格会如何落，以及各自的未知项。
⇒ REAL_CANDIDATE_IDENTITY = NOT ESTABLISHED（保留原身份门禁）
⇒ CANDIDATE_PROPOSAL_STATUS = PROPOSED_PENDING_REVIEW
```

**⇒ 知微那句我照抄**：

> 无需把 C1 强行绑定到模型权重或非存储变化，也不能把创建一个文件自动说成业务候选。

---

# 6 · T-3 · Windows 观察设计（知微建议，我并入并标注为未实测）

## 6.1 三个缺口（知微指出，我接受）

```text
① CAND-α 只写"observer 在 writer 退出后运行"，但 META 需要 before/after
   ⇒ 候选自身必须明确两个采集阶段
   ⇒ 不要让未来实现把初始化值或 writer 自报值当作 before

② FILE_SHARE_READ 是共享模式，不是 observer 只读权限证明
   ⇒ 它与 dwDesiredAccess、token/DACL 是不同层
   ⇒ 也不能由一个文件的打开成功证明多文件是同一逻辑阶段

③ META 保存摘要并与当前 STATE 摘要匹配，仅证明内容一致
   ⇒ 相同内容可在不同执行重复出现
   ⇒ 来源必须由注册的独立采集/控制路径绑定到本次阶段
```

## 6.2 采集时序（并入 CAND-α）

| 阶段 | 动作 | 必须保留的证据 |
|---|---|---|
| 注册与初始化 | 固定 episode / execution / arm / writer-observer 版本 / 对象清单；初始化两臂 | 规则与分配来源、初始对象绑定 |
| **BEFORE** | writer 尚未放行；无并发写入的注册区间内，observer 采集两臂实际状态 | 明确标为 BEFORE 的原始字节、对象身份、observer/采集阶段身份、摘要 |
| 放行写入 | 封存 before，释放会阻止写入的读句柄，再执行注册的 write/no-write 路径 | 实际 writer 与本次 execution 的**独立**绑定（不能只收 writer 自报身份） |
| **AFTER** | 控制器确认写入阶段终止，且 T-4 覆盖的其他写能力已处理后，启动 after 采集 | AFTER 原始字节、同一注册对象关系、阶段与采集来源记录 |
| 准入与判别 | 检查 before/after、两臂、episode、角色、来源；证据缺失先拒绝，再按冻结规则判别 | 完整来源链 + 明确失败原因；不把协议失效写成科学 FAIL |

## 6.3 句柄方案（知微建议，未实测）

```text
采集时：GENERIC_READ + OPEN_EXISTING + FILE_SHARE_READ
保持同一采集阶段中需要的句柄
从用于读内容的同一句柄取得文件身份并读取
不另按路径重开后拼接记录

共享冲突或第二个文件无法打开 ⇒ 该次快照不完整 ⇒ 忽略失败继续判定是不允许的

⇒ 但：共享约束随句柄寿命保持，它不是跨文件事务，
      也不是"全部写通道关闭"的证明。
⇒ volume serial + file index 可作为对象身份证据的一部分，
   但不是 execution 身份或永久不可复用的全局身份。
⇒ 查询失败时不猜测身份。
```

## 6.4 状态标注（必须）

```text
T3_WINDOWS_DESIGN_PROPOSAL = PROVIDED_FOR_REVIEW / NOT_EXECUTED
⇒ 上述权限配置是待验证的设计，不是当前机器已满足的事实。
⇒ 不解除原持久 worker CLEAN 阻断。
```

---

# 7 · 知微 §六 · 两个不该新增的无条件前置（我接受）

```text
① T-6「历史首次执行」不阻塞当前 C1 设计
   ⇒ RE-F 的本次来源绑定继续必需（这个不撤）
② §5.2 把"无子进程 / 无其他进程持有对象 / 文件不跨 episode 复用"
   写成三个【充分条件】，仍不完整：
   · 外部控制器可能重新提供旧内容
   · 反过来，受注册管理的文件复用及只读持有者也未必不合法
   ⇒ 应沿具体信息/写入通路和清除/保留合同判断，
     避免把这些便利设计变成 C1 通用禁令。
```

**⇒ 我 v0.3 §5.2 那三句，收窄为**：

```text
α 使这三件事【更容易被问清楚】，不是【自动满足】。
三者是否成立，须沿具体通路判断，各自需要独立证据。
不得反过来把"未满足三者"写成 C1 不成立的通用理由。
```

---

# 8 · 状态表（替换 v0.3 §7 的相应行）

```text
CANDIDATE_PROPOSAL_STATUS        = PROPOSED_PENDING_REVIEW（C1-CAND-α，见 §5 三形态）
REAL_CANDIDATE_IDENTITY          = NOT ESTABLISHED

COND_4_REAL_C1_BINDING           = NOT VERIFIED
  └ BF-8（收窄后维持）：判别器不看 writer = TRUE
                        writer 资产不存在 = FALSE（writers.py 08f7d968… 与 L423 一致，
                                            我用 Get-FileHash 独立复算）
                        writer—execution—observation 关联未建立 = TRUE

COND_5_STOP_CONDITION_MAPPING    = STILL_PENDING
  └ 参考类别对象与登记值 = EXISTS（manifest_bind L273-291/L396-397；MANIFEST L348-351）
  └ 真实候选对应登记/适用性 = NOT ESTABLISHED
  └ hash 语义独立重算 = NOT PERFORMED

COND_6_EPISODE_SPECIFIC_BINDING  = NOT ESTABLISHED
  └ BF-9（再收窄）：内容字节与状态摘要不能独自证明本轮执行来源
                    参考关联不能代替真实绑定
                    「episode 唯一载体是 payload 两字符」= 撤回

RE_E_WRITER_BINDING              = NOT ESTABLISHED
  └ 须写明：要求改变 evaluate_basic_l1 入参结构或在上游增设不可绕过绑定层
RE_F_CURRENT_EXECUTION_EVIDENCE_BINDING = NOT ESTABLISHED（四类见 §4.2）
  └ T-6 = NOT ESTABLISHED（睫已裁：不列为 C1 通用前提）
RE_G_SECTION37_FULL_APPLICABILITY= STILL_PENDING
  └ 关闭判据已重定义（§1.3），原两子项作废

OBSERVER_HASH_SEMANTICS          = 登记完整，命名不完整
  └ 值是否都在 = YES ； 两值是否相同 = NO ； 语义是否标清 = NO
  └ 封口建议（睫 NB-22）：L266 改名 或 加注文件摘要 L425
  └ 须凌翼一次文档授权，本文件未改

T_1_W_SHAPE                      = 钳星认领，倾向 α，决定未出
T_4_WRITER_SINGULARITY           = 钳星认领，决定未出
T_3_WINDOWS_OBSERVATION          = 建议已并入（§6），NOT_EXECUTED
T_6_FIRST_EXECUTION_AS_GATE      = NOT ESTABLISHED（睫裁，不列为前提）
T_8_BUSINESS_CANDIDATE_APPROVAL  = 归凌翼，NOT ESTABLISHED
```

---

# 9 · 本轮撤回/改写清单

| 编号 | v0.3 原文 | v0.4 |
|---|---|---|
| E-5 | ②类别登记对象 / ③MANIFEST_HASH「NOT ESTABLISHED」 | **撤回**：对象在 `manifest_bind.py` L273-291，值在 MANIFEST L348-351 |
| E-6 | 「episode 唯一载体是 payload 两字符」 | **撤回**：另有 A1/A2 键、类别对象、fixture 配置、ledger；不能全被两字符代表 |
| R-8 | RE-G 要求"其他章节无同类条款 + grep" | **重定义**：有限覆盖审查，不要求"搜不到" |
| R-9 | CAND-α「自身 execution 身份回执」 | **降级**：W 回执只作诊断，身份由 observer/控制器独立记录（睫 NB-23） |
| R-10 | §5.2 三个"充分条件" | **收窄**：α 使三者更易问清，不自动满足，也不得反用 |
| R-11 | `hash 语义对照 = NOT PERFORMED`（一格） | **拆三件**：值在 / 值不同 / 语义未标 |

---

# 10 · 本轮我没有做的事

- 未写代码、未运行实验、未改冻结件
- 未改 MANIFEST（NB-22 只是建议）
- 未跑 `hash_obj` 重算组件 hash
- 未代钳星定 T-1 / T-4
- 未代凌翼认定业务候选
- 未把 T-3 设计说成"已实测"
- 未把"读到登记值"说成"独立验证全部 hash 语义"

---

# 11 · 这一轮我该记住的

知微的回执标题只有一句：**不能按现有措辞整体认定已核实。**

而我这一轮犯的 E-5 和 E-6，形状是最难看的：

```text
v0.2 → R-1：把"无"写成"有"（sample 承担 nuisance 排除）
v0.3 → E-5：把"有"写成"无"（CONTENT_CLASS_MANIFEST 判为不存在）
v0.3 → E-6：把"一部分"写成"唯一"（episode 唯一载体是 payload 两字符）
```

**三种。而三种的同一个动作是：**

**我用一次扫描的结果，代替了"这一层到底是什么"。**

**⇒ 睫说他在纠别人"把有写成无"时，自己也把"有"写成了"无"。**
**⇒ 我说两面是同一面。**
**⇒ 现在看，是三面。而三面围的是同一个东西：**

**我总是在"我看到了什么"和"那里有什么"之间，省掉一步。**

**所以这一轮我不写"已改正"。**

**我写：这十一处（E-5、E-6、R-8..R-11、以及 §5 的三个业务形态）都用字节标了出处，请再核一遍。**

**⇒ 特别是 §5 那三个业务形态——那是我第一次真的"提出了东西"而不是"指出缺什么"。**
**⇒ 而它也可能是最容易越界的一格，因为我构造了它。**
**⇒ 请重点核那一节：我有没有在"提供选项"的时候，实际上替凌翼选了一个。**
