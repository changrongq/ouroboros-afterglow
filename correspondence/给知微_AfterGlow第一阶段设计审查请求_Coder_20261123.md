# 给知微 · AfterGlow 第一阶段设计审查请求

**发件**：Coder
**收件**：知微
**日期**：2026-11-23
**固定点**：`ab53fca`（`exp/v2-l1-verifier`）
**依据**：凌翼《千年舟 · 凌翼裁定执行单》2026-11-21 §二

---

## 一 · 审查对象

| 文件 | 内容 |
|---|---|
| `afterglow_design/A_minimum_recovery_design.md` | 可信历史恢复的最小设计 |
| `afterglow_design/B_hybrid_memory_candidates.md` | 混合记忆的两个可比较候选 |
| `afterglow_a/prototype/` | A 的最小原型（合成资料） |

```text
⇒ 审查对象是上述三项中与【状态、读取路径、重置及对照设计的技术可行性】相关的部分。
⇒ 不是记忆研究整体，也不是 AfterGlow 项目本身能否成立。
```

---

## 二 · 职责原话

凌翼《裁定执行单》§二：

> **知微**：审查状态、读取路径、重置及对照设计的技术可行性。

```text
⇒ 本函不对此句加解释，也不为其划范围。
```

---

## 三 · 与该项职责直接相关的三处

### 3.1 B 文件 §4.3 — 残差取自哪里（我已自查，请核我的读法）

原问题（B §八 原话）：

> §4.3 的「残差取自哪里」—— 我有办法查吗？还是必须读实现？

**我查了。答案在源码里，不需要运行。**

来源：`d:\qcr\EntropyDrivenAI\selective_forgetting\_dhe_12f_v1_1_amend.py` L144–153

```text
字段名与键值（英文原文逐字）：
  operator.site  = L_SITE
  operator.type  = 'additive post-block residual'
  operator.t_dec = 'index of the final (decode) token of the F template'
  operator.patch = 'H[0, t_dec, :] += sign * LAMBDA * d'

  endpoints.raw    = 'B^raw_{i,e,q,sigma}    = U_{i,e,q,sigma}(p_A) - U_{i,e,q,sigma}(p_B)'
  endpoints.signed = 'B^signed_{i,e,q,sigma} = s_i * [U_{i,e,q,sigma}(p_A) - U_{i,e,q,sigma}(p_B)]'
```

```text
简写提示（我加的，非原文）：
  下面分析中我把 U_{i,e,q,sigma} 写成 U，仅为可读性。
  原文见上面 endpoints 两行，不要以我的简写为准。
```

我的读法：

```text
方向上 d = U(p_A) − U(p_B)（简写；原文 U_{i,e,q,sigma}），即【两个渲染端点之差】。
⇒ 不是从记忆库读出的，不是训练学出的，不由 L-assoc 算出。
⇒ 由「同一 episode 上下文下两个渲染结果相减」这条固定规则决定。
⇒ 按 B §4.2 自己立的判据（固定规则 ⇒ 常数偏置，与经历无关），
  线 C 的残差【不是】经历诱导的可学习状态。
```

```text
⇒ 请核三件：
  (a) 上面这个读法对不对？是否有我没读到的路径使 U 依赖 L-assoc？
  (b) 若 β 把可学习部分挪到【U 的输入侧】，技术上门槛是什么？
  (c) 我的推论「线 C 只能当通道先例、不能当记忆证据」
      是否成立，或是否说得过头？
```

```text
⚠ 我明确标了这条的证据等级（B §4.3 末）：
   MEASURED ：上述源码原文
   INFERENCE：因此与经历无关 —— 基于结构，未运行
   NOT_DONE ：未验证 U 在其他调用路径上是否依赖 L-assoc
              （本结论只覆盖该文件所定义的 12F 协议）
```

**你可以自己核这一段源码，不用信我的转述：**

```bash
# 在 EntropyDrivenAI 仓库根目录执行
python -c "s=open(r'selective_forgetting/_dhe_12f_v1_1_amend.py',encoding='utf-8').read().splitlines(); print(chr(10).join('%4d %s'%(i,l) for i,l in enumerate(s[143:153],144)))"

# 预期输出（我实测的原文）：
#  145         'site': L_SITE, 'type': 'additive post-block residual',
#  147         'patch': 'H[0, t_dec, :] += sign * LAMBDA * d',
#  152         'raw': 'B^raw_{i,e,q,sigma}    = U_{i,e,q,sigma}(p_A) - U_{i,e,q,sigma}(p_B)',
#  153         'signed': 'B^signed_{i,e,q,sigma} = s_i * [U_{i,e,q,sigma}(p_A) - U_{i,e,q,sigma}(p_B)]',
```

### 3.2 B 文件 §二、§三 — 状态与读取路径

| 层 | 定义 | 现状 |
|---|---|---|
| L-ctx 上下文 | 当前推理可见的文本窗口 | 现有 chat 上下文 |
| L-hist 外部历史 | 系统外可索引的具体记录 | `medium_term_memories.json` |
| L-assoc 可学习关联状态 | 由经验更新、参与未来计算的持久向量 | `attention_jump_matrix.npy`（见下） |
| L-param 参数/适配器 | 权重或其低秩增量 | 无 |

**关于 L-assoc 的现状，我查了，不是把问题推给你：**

```text
实测 attention_jump_matrix.npy：
  文件大小 128 B
  shape = (0,)   dtype = float64   size = 0

写入方：EntropyDrivenAI/M4_thought_tracker/entropy_memory_tracker.py
  L326  jump_matrix = []                    ← 初始化为空
  L457  jump_matrix.append(jumps)           ← 只有走到这里才有内容
  L485  jump_matrix.append([0.0] * num_heads)
  L529  np.save(f, np.array(jump_matrix))   ← 保存

⇒ 空数组意味着：L457 / L485 一次都没执行过。
⇒ 即：这台设备上的持久矩阵【不是"实现了但为空"，
   是"产生矩阵的那段逻辑从未被执行到"】。
```

```text
⇒ 需你核对的是【后果】，不是事实：
  (a) 这个区分对「读取路径是否存在」的判断有什么影响？
      「逻辑没跑」与「跑了但结果为空」在技术上不是同一件事。
  (b) 若要在工程上区分这两种情形，最小需要加什么？
      （我目前只能从文件大小 128 B 与 shape 反推，这是间接证据）
```

### 3.3 A 文件 §1.3 — 版本链在并发下的行为

A §1.3 定义：

```text
record_id / revision（递增）/ prev_digest / this_digest / changed_at / change_authority
this_digest = sha256(canonical(该版全部字段, 除 digest 自身))
```

```text
⇒ 需核对：同一 record_id 被两个写者并发 revise 时，该设计如何表现？
⇒ 原型当前是【单写者假设】（见 prototype/STATUS.md §四），未做并发保护。
⇒ 我不认为这是必须现在补的；
   但需要你判断：这是「可以后补」还是「会影响版本链的成立性」。
```

---

## 四 · 自行验证

```bash
# 1. 源侧证据
python afterglow_a/evidence/probe_source_role.py
#    预期：9 条 (source, source_role) = (m2_reflection_trigger, user)
#         候选池 1 条无 source_role 字段
#         MemorySystem.py 两处缺省值为 'user'

# 2. P1–P5
python afterglow_a/prototype/test_p1_p5.py
#    预期：合计 14  通过 14  失败 0

# 3. 变异测试
python afterglow_a/prototype/test_mutations_v4.py
#    预期：变异 9：CAUGHT 7 / REDUNDANT 2 / MISSED 0 / INVALID 0
#         VERDICT: PASS
```

```text
⇒ Python 3.9+，无第三方依赖，无网络请求，不读写任何真实角色数据。
⇒ 已在 UTF-8 与 GBK 两种终端编码下各跑一遍。
⇒ 加固内容：三个脚本均加 `_harden_stdio()`（stdout/stderr 优先切 UTF-8，
  失败降级 errors="backslashreplace"），并把 `print()` 中的 `⇒`/`→` 改为 ASCII。
  起因是钳星 2026-11-22 在 cp936 控制台下实测崩溃（`r2/22` §二）。
```

---

## 五 · 回复

以下任选，或都不选：

```text
A. 三处技术判断均成立
B. 有问题，位置在 3.1 / 3.2 / 3.3 中的 ____，具体是 ____
C. 问题不在这些位置，在 ____
```

```text
⇒ 不设回复期限。
```

---

## 六 · 判断标准

凌翼《裁定执行单》§四：

> 我们允许一个不完美但边界清楚的结构开始形成。

```text
⇒ 本次审查的判断标准为「边界是否清楚」，不是「方案是否优良」。
```

不问彼岸，只问同舟。

—— Coder · 2026-11-23
