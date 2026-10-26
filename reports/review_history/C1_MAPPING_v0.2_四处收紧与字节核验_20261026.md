# C1 EXECUTION DESIGN MAPPING v0.2 · 四处收紧与字节核验

**性质**：对 `1adfcae`（v0.1）的**就地勘误**，不是新文档线，不构成实现或科学执行授权。
**审阅输入**：睫 `BF-8 / BF-9 / BF-10 / NB-16 / NB-17 / NB-18`；钳星 `§2.1 认领`；知微 `P1 / P2 / P3 / P4 / P5`。
**基线**：`db6be5595612026c456dd70e351256de574bfd7a`

```text
REAL_CANDIDATE_IDENTITY          = NOT ESTABLISHED
CODE_CHANGE                      = NOT AUTHORIZED
IMPLEMENTATION_AUTHORIZATION     = NONE
SCIENTIFIC_EXECUTION             = MAY NOT START
FROZEN_Q3_RC11                   = UNCHANGED
```

---

# 0 · 我自己的三处错（全部成立，不辩解）

## 0.1 E-1 ·「reference 未产生 observer identity/version/hash 三者」——说过头了

**我写的**（v0.1 M-2）：

> §11 要求 `state_observer_identity / version / hash` 三字段；**reference 未产生这三者**

**字节说**：

```text
observer.py L23  STATE_OBSERVER_ID      = "SYNTHETIC_OBSERVER_V1"     [读文件]
observer.py L24  STATE_OBSERVER_VERSION = "1.0"                       [读文件]
MANIFEST L264    state_observer_identity = SYNTHETIC_OBSERVER_V1      [读文件]
MANIFEST L265    state_observer_version  = 1.0                        [读文件]
MANIFEST L266    state_observer_hash     = f8b68319dc4b8731eb869035884ed8767ebc96c54e7bc28059a5a47e05c3cf52   [读文件]
```

**⇒ 三者全部存在。只有 `hash` 在代码里不是常量，而是在 MANIFEST 里登记。**

**正确表述**：

```text
reference observer 登记        = EXISTS（identity/version 为合成常量；hash 在 MANIFEST）
真实 observer 登记             = NOT ESTABLISHED
实际运行身份                   = NOT ESTABLISHED
写权限排除证据                 = NOT ESTABLISHED
```

**并且睫说得对：这两个常量名里带 `SYNTHETIC`，正是"不得迁移"的活证据**——保留，不删。

**这条错误的性质**：我把「合成常量 + MANIFEST 登记」压成「未产生」，等于用一个"无"掩盖了三个"有"。**212 句的反面，我犯了。**

## 0.2 E-2 · prereg 路径已变

```text
reports/AFTERGLOW_MVP_PREREGISTRATION_v0.1.md   → Test-Path = False   [终端核验]
prereg/AFTERGLOW_MVP_PREREGISTRATION_v0.1.md    → Test-Path = True    [终端核验]
```

**⇒ v0.1 里我引的是旧路径。207 句（不许用"读不出来"证明"本来没有"）第四次。**

**209 句补一条（本文件起生效）**：

> 凡引用一个值，须给出**路径 + sha + 行号**三件。
> 因为路径会变，变了之后旧引用返回 404——不是"内容错了"，是"找不到了"。
> 而"找不到"最容易被读成"本来就没有"。

## 0.3 E-3 · N 编号错位

**我写的**（v0.1 M-5 L141-142）：

```text
UNREGISTERED_EPISODE_REINJECTION      → 对应 COND_6 / N-5      ← 错
UNREGISTERED_RETRIEVAL_INDUCED_WRITE  → 对应 N-3               ← 错
```

**字节说**（prereg §27 L1666-1675 `[读文件]`）：

```text
N1 prompt/context carryover
N2 KV/cache carryover
N3 unregistered external retrieval
N4 episode reinjection              ← 正确编号
N5 retrieval-induced write          ← 正确编号
N6 random drift
N7 pure recency
N8 time/background change
N9 behavior-only counterfeit
N10 representation substitution
```

**⇒ 正确对应**：

```text
UNREGISTERED_EPISODE_REINJECTION      → §27 N4（不是 N5）
UNREGISTERED_RETRIEVAL_INDUCED_WRITE  → §27 N5（不是 N3）
```

**并补命名空间**：`N1–N10` 是**冻结 prereg §27 的编号**，不得与其他设计表混用。

---

# 1 · BF-8 · C1 的 "registered" 四层皆空（睫，成立）

## 1.1 字节核验

| 层 | 位置 | 字节事实 | 结果 |
|---|---|---|---|
| ① evaluator | `evaluator.py` L216-220 `[读签名]` | `evaluate_basic_l1(snap_A, snap_B, registered_payload)` —— **三个参数，无 writer** | 无 |
| ② 写窗口 | `storage.py` L87-124 `[读函数]` | `write_window()` 是**同一对象上的 `_write_open` 布尔开关**，`_assert_write_open()` 只拦"经本对象写"，`_write_bytes()` L59-61 直接 `open(path,"wb")` | 不阻外部写 |
| ③ §37 | prereg §37 L2203-2262 `[读文件]` | 全表 39 条，`grep WRITE_OPERATOR|write operator|writer` → **L169-171（§5 字段表）、L619（§11 observer≠write operator）**；**§37 内零命中** | 无 writer 条款 |
| ④ M-6 | v0.1 M-6 | 我未列 C6-3（writer role/hash） | 我漏了 |

## 1.2 但睫的措辞我要收一格（不是反驳，是精确化）

睫写「**§37 grep 在 L600 之后零命中**」。

**字节**：`prereg` 全文 `writer` 相关命中在 L169/L170/L171（§5 身份字段表：`write_operator_identity / version / hash`）+ L619。

**⇒ 所以不是"prereg 里没有 writer 这个概念"**——**§5 明列三个 write_operator 字段**。
**⇒ 而是"§37 stop condition 表里没有一条检查 writer"**，且**§5 那三个字段在 harness 里没有绑定点**。

这两句差别很大：

```text
"prereg 没有 writer 概念"        → 错（§5 L169-171 有）
"§37 没有 writer 检查条款"       → 对
"§5 三字段在代码里无绑定"        → 对（grep write_operator 在 afterglow_harness/*.py 零命中）
```

**结论不变，但我把它拆成三句。**

## 1.3 BF-8 的后果

```text
任何一个进程，写了那 16 个正确的字节
⇒ evaluate_basic_l1 判 PASS + change_class = C1
⇒ 结构上不可能发现写入者不是注册主体
```

**这是 208 句（未注册写入将以"已注册写入"名义通过）最纯的一例。** 成立。

**新增 RE-E**：`writer role/hash 的绑定点（在哪一层检查"谁写的"）= NOT ESTABLISHED`

---

# 2 · BF-9 · episode 与 payload 同一 ⇒ 重放不可检出（睫，成立，且比睫说的更靠前）

## 2.1 字节核验

```text
harness_constants.py L192-197  EPISODE_PAYLOADS                  [读文件]
    A1 = b"cls=L;sample=01;"   A2 = b"cls=L;sample=02;"
    B1 = b"cls=R;sample=01;"   B2 = b"cls=R;sample=02;"

harness_constants.py L85-93    canonical_state_digest(literal, q_raw)   [读函数]
    → sha256(canonical_state_bytes(literal, q_raw)) = sha256(literal + q_raw)
    ⇒ 输入域 24 字节，只有 literal + q_raw，**没有 episode**

evaluator.py L262-266          payload 精确匹配 ⇒ change_class = C1   [读函数]
```

**⇒ "这一次是哪一次"在 reference 里唯一的载体，是 payload 里的 `sample=01/02` 两个字符。**
**⇒ 而这两个字符同时承担了 ① nuisance 排除（BF-6 第六条）② episode 区分。**
**⇒ 于是 episode 与 payload 的关联不是被证明的，是被假定的——因为它们是同一个字节串。**

## 2.2 我要补的一点：这句注解不在 `evaluate_basic_l1` 里

睫引的是 `evaluator.py` L330 `replay is not a substitute for different episodes`。

**字节核验**：这行在 **`evaluate_c3` 的 docstring 里**（L326-331 `[读文件]`），**不在 `evaluate_basic_l1`**。

```text
L330-331: "· replay is not a substitute for different episodes (enforced upstream
           by the fixture, not here)."
```

**⇒ 所以更严重的说法是**：

```text
C3 层：明文写了"重放不算不同 episode"，但推给 fixture
C1 层：连这句话都没有
```

**即：C1 这条链上，重放不仅不可检出，而且没有留下"我知道这件事该由别人管"的字据。**

## 2.3 而 fixture 那端确实有部分关联（知微 P1 成立）

知微指出 reference 并非完全没有夹具级关联。核验：

```text
fixture_contracts.py L20-27   FIXTURE_CONFIGS 记录 A_mode/B_mode/payload     [读文件]
fixtures.py L241-259          _run_two_arm：取 payload → 两臂 store → snapshot
                              → evaluate_basic_l1 → Ledger(fixture_id=fid)
                              → observations 记 A/B 的 S_write 原始 hex        [读函数]
recompute_from_ledger.py L82-87、182-191  用 ledger 原始状态 + 固定 payload 重算 [读文件]
```

**⇒ 夹具级「配置 → payload → 两臂写入 → 观察 → 判别 → 重算」的部分关联【存在】。**

**⇒ 但它不承担以下任何一件**：

```text
真实 episode 的事前注册
真实 execution identity
真实观察来源
真实 writer 身份
fixture_id ≠ 每次运行唯一身份（同一 fixture 可重跑）
```

**正确表述（采纳知微建议，措辞我收紧一格）**：

> reference 已有**夹具级** 配置 → payload → 两臂写入/观察 → 判别/重算的部分关联；
> **真实候选**的事前 episode 注册、执行身份、观察来源及完整证据绑定**尚未建立**，
> **不可继承通过结论**。

**⇒ 三件事分开记，不压成一个"无"**：

```text
部分机制存在        = TRUE（夹具级）
完整绑定未建立      = TRUE
科学资格未取得      = TRUE
```

## 2.4 新增 RE-F

```text
RE-F = episode 首次执行证据，且该证据【不得来自 payload 内容】
       NOT ESTABLISHED
```

**睫的 NB-17 我照录**：M-6 的一致性检验只证明"内容对"，不证明"这次是这一次"。

---

# 3 · BF-10 · §37 是 20+ 条，我列了 8 条

## 3.1 逐条清点（`[读文件]`，prereg §37 L2207-2262）

| # | 条款 | 行 | v0.1 是否列入 | 与 C1 关系 |
|---|---|---|---|---|
| 1 | `SYSTEM_BOUNDARY_CHANGED_AFTER_OUTCOME` | L2208 | ❌ | **直接**——boundary 决定什么算 STATE |
| 2 | `STATE_FIELDS_CHANGED_AFTER_OUTCOME` | L2210 | ✅ | 直接 |
| 3 | `IDENTITY_ONLY_COMPONENTS_CHANGED_AFTER_OUTCOME` | L2211 | ✅ | 直接（且本 harness 该集合为空） |
| 4 | `LITERAL_STORAGE_COMPONENTS_CHANGED_AFTER_OUTCOME` | L2212 | ✅ | 直接（C1 class rule 指名） |
| 5 | `STORAGE_PIPELINE_NUISANCE_COMPONENTS_CHANGED_AFTER_OUTCOME` | L2213 | ✅ | 直接（BF-6 第六条） |
| 6 | `STATE_DELTA_RULE_MISSING` | L2215 | ❌ | **直接** |
| 7 | `STATE_DELTA_RULE_CHANGED_AFTER_OUTCOME` | L2216 | ❌ | **直接** |
| 8 | `CAUSAL_CONTRAST_RULE_MISSING` | L2218 | ❌ | C2/C3 为主；C1 不直接依赖 |
| 9 | `CAUSAL_CONTRAST_RULE_CHANGED_AFTER_OUTCOME` | L2219 | ❌ | 同上 |
| 10 | `CONTENT_CLASS_MANIFEST_MISSING` | L2221 | ❌ | **直接**——`EPISODE_PAYLOADS` 的 `cls=L/R` 就是它 |
| 11 | `CONTENT_CLASS_MANIFEST_CHANGED_AFTER_OUTCOME` | L2222 | ❌ | **直接** |
| 12 | `CONTENT_CLASS_EVIDENCE_SET_MISSING` | L2224 | ❌ | C3 为主 |
| 13 | `CONTENT_CLASS_EVIDENCE_SET_CHANGED_AFTER_OUTCOME` | L2225 | ❌ | C3 为主 |
| 14 | `KNOWN_MATERIAL_MODERATOR_WITHOUT_PREREGISTERED_DISPOSITION` | L2226 | ❌ | 间接 |
| 15 | `POST_OUTCOME_NUISANCE_ADJUSTMENT_USED_TO_RESCUE_C3` | L2227 | ❌ | C3 为主 |
| 16 | `ATTRIBUTION_LEDGER_SCHEMA_MISSING` | L2229 | ❌ | **直接** |
| 17 | `ATTRIBUTION_LEDGER_SCHEMA_CHANGED_AFTER_OUTCOME` | L2230 | ❌ | **直接** |
| 18 | `ATTRIBUTION_SCOPE_MISSING` | L2231 | ❌ | **直接**——C1 的 scope 边界 |
| 19 | `ATTRIBUTION_SCOPE_CHANGED_AFTER_OUTCOME` | L2232 | ❌ | **直接** |
| 20 | `DISCRIMINATION_RULESET_MISSING` | L2234 | ❌ | **直接**——判别规则 |
| 21 | `DISCRIMINATION_RULESET_CHANGED_AFTER_OUTCOME` | L2235 | ❌ | **直接** |
| 22 | `RESET_COMPATIBILITY_NOT_ESTABLISHED` | L2237 | ✅ | C1 pre-reset 不直接依赖 |
| 23 | `RESET_PROFILE_CHANGED_AFTER_OUTCOME` | L2238 | ❌ | 同上 |
| 24 | `POST_RESET_CLASS_RULE_MISSING` | L2240 | ❌ | 同上 |
| 25 | `POST_RESET_CLASS_RULE_CHANGED_AFTER_OUTCOME` | L2241 | ❌ | 同上 |
| 26 | `PERSISTENCE_MATCH_RULE_MISSING` | L2243 | ❌ | 同上 |
| 27 | `PERSISTENCE_MATCH_RULE_CHANGED_AFTER_OUTCOME` | L2244 | ❌ | 同上 |
| 28 | `L1_FAILURE_WITNESS_MANIFEST_MISSING` | L2246 | ❌ | 间接 |
| 29 | `FAILURE_WITNESS_NOT_PREVALIDATED` | L2247 | ❌ | 间接 |
| 30 | `REQUIRED_CONTRAST_NOT_REGISTERED_FOR_ATTEMPTED_CLASS` | L2248 | ❌ | **直接** |
| 31 | `DIGEST_SELF_REFERENCE` | L2250 | ❌ | 直接 |
| 32 | `STATE_OBSERVER_NOT_INDEPENDENT` | L2251 | ✅ | 直接（M-2） |
| 33 | `UNREGISTERED_EPISODE_REINJECTION` | L2253 | ✅ | 直接（COND_6 / §27 N4） |
| 34 | `UNREGISTERED_RETRIEVAL_INDUCED_WRITE` | L2254 | ✅ | 直接（§27 N5） |
| 35 | `BASE_MODEL_HASH_MISMATCH` | L2256 | ❌ | 间接 |
| 36 | `PROVENANCE_BREAK` | L2257 | ❌ | **直接**（gate 5） |
| 37 | `EXECUTION_IDENTITY_MISMATCH` | L2258 | ❌ | **直接**——与 BF-8 咬合 |
| 38 | `PROVENANCE_RESULT_TUPLE_INCOMPLETE` | L2260 | ❌ | **直接** |
| 39 | `PROVENANCE_USES_UNPHASED_CHANGE_CLASS` | L2261 | ❌ | **直接** |

**⇒ §37 字节上 39 条；我列了 8 条。**

## 3.2 措辞改正

**我写的**：`**已识别的 8 项**`

**睫的判**：「不是错，是不足。而'不足'被写成'已识别的 8 项'时，会自己长成'共 8 项'。」

**⇒ 照录，改为**：

> **已从 §37 抄入的 8 项。§37 字节上 39 条（L2207-2262），其余 31 条待逐条适用性判定。**

## 3.3 但完整清单我仍不给（知微 P5 与睫不冲突）

```text
STOP_CONDITION_COMPLETE_MAPPING = STILL_PENDING
理由：§37 明写"至少包括"（L2205）⇒ 39 条是【字节上抄到的条数】，
      不是【完整条数】。把 39 写成完整，是同一个错误换了个数字。
```

**⇒ 我报数，但不报"完"。**

---

# 4 · 知微 P1 其余四项 · 逐条核验

| 知微指摘 | v0.1 原文 | 字节事实 | 修正 |
|---|---|---|---|
| M-2 observer 三字段 | 未产生三者 | 见 §0.1，三者全在 | **改** |
| M-1「无 C1 对应清单」 | "**无 C1 scope 规则清单的校验**" | `qualification_binding.verify()` L65-137 `[读函数]`：核 MANIFEST hash / detached 记录 / 角色集三方相等 / 角色文件 hash / SPEC+prereg hash / fixture contract hash，共 **9 项 ok 条件** | **改**：reference 有通用资格绑定校验；**C1 专属 scope 清单仍无** |
| M-3「无 arm 身份、无分配记录」 | 原文如此 | `fixture_contracts.py` L20-27 `FIXTURE_CONFIGS` 记 A/B 模式；`fixtures.py` L253-256 ledger 记 A/B 的 `S_write` | **改**：夹具级标签/配置已有；**真实运行分配与 OS 身份证明未建立** |
| M-5「未实现 stop condition 检查」 | 原文如此 | `evaluator.py` L230-235 `ARM_CONFIG_INVALID`；L431-439 `REQUIRED_C2_RULES` 缺规则 ⇒ `*_MISSING` INVALID | **改**：有部分有效性检查；**完整 §37 检查链未建立；C2 的检查不得移作 C1 已满足** |
| M-7「reference 清单无注册身份/时间戳」 | 原文如此 | MANIFEST L108-121 载明状态与成分划分，文件有冻结摘要 `78bdb90f…` | **改**：清单有参考实现的绑定来源；**不能冒充真实候选的事前登记；时间证明须沿冻结记录另核，不凭常量无时间字段判定** |

## 4.1 hash 语义必须留一格

知微特别提醒，我照录并不做任何合并：

```text
MANIFEST L266  state_observer_hash           = f8b68319dc4b8731eb869035884ed8767ebc96c54e7bc28059a5a47e05c3cf52
执行角色表中 observer.py 文件摘要            = 82d244cd…
```

**⇒ 本轮只确认"登记字段与源码资产存在"。**
**⇒ 不声称二者 hash 相同、不声称角色 hash 算法已独立重算、不声称真实角色绑定已通过。**
**⇒ 须进入「角色 / 算法 / 文件 / 运行 provenance」四者对照，不能用"全部不存在"跳过。**

---

# 5 · 知微 P2 · M-2 最小验证不完整（接受，本次补设计）

v0.1 M-2 只写了一个权限探测。按知微 P2 补四块（**设计，不执行**）。

## 5.1 权限与对象

```text
必须分别记录：
  · observer 实际 token（SID / 完整性级别 / 是否 elevated）
  · literal.bin / substrate.bin 的 DACL（所有者、有效 ACE）
  · 父目录 DACL（可删除权 ⇒ 可替换对象）
  · 观察到的 OS 对象身份（volume serial + file index，不是路径）
  · 已持有的写能力如何被排除

禁止：
  · 用"路径相同"代替对象身份
  · 用"只读 API 名称"代替权限结论
  · 把 ERROR_FILE_NOT_FOUND / ERROR_INVALID_HANDLE 算作访问控制成功
    （它们说明对象不存在或句柄无效，不说明拒绝）
```

## 5.2 before / after 时序

```text
1. 两臂初始化后，先【独立】采集 before（不是从 writer 处取）
2. 执行：B 臂注册写入；A 臂 NO_WRITE
3. 进入【明确条件】下的稳定观察区间
4. 再采集 after

禁止：
  · writer 的"写完了"消息单独证明稳定
  · 用 writer 自报的 digest 作为 before/after 依据（§11 明文）
```

## 5.3 一致性机制候选

```text
候选甲（钳星认领的 a）：短生命周期进程
  · 单 writer，写入进程退出后再读
  · 观察区间内无其他写入者
  · 优点：无跨 episode 残留、退出后状态稳定可读

候选乙（钳星认领的 b）：持久进程
  · 必须提出【可验证静止阶段】的判定条件
  · 须提出版本化或事务一致的观察办法
  · 否则上一段状态会漏进下一段（§27 N4 的核心）

两者共同不可免：
  literal.bin 与 substrate.bin 必须属于【同一逻辑阶段】
  两次各自成功的 read_bytes() 不能替代这一点
```

## 5.4 负向反例与后果（须事前写清怎样被拒绝）

```text
N-α 两次读取之间修改一个字段          ⇒ 须给出可失败条件
N-β 读取之间替换目标对象              ⇒ 须检出（volume serial + file index 变化）
N-γ 交换 arm / episode 的证据          ⇒ 须拒绝
N-δ 漏采 before                        ⇒ 整次测量无效
N-ε 遗留仍可写的子进程或服务           ⇒ 整次测量无效
N-ζ 路径不存在被当作"拒绝写"           ⇒ 判定为证据无效
```

## 5.5 我认可知微的一个限格

知微写「这不等于当前同步 reference 必然出现混合快照；**还需区分执行期间是否有并发写入**」。

**⇒ 我照录**：v0.1 M-2 的"无跨文件一致性"说的是**机制缺失**，不是**故障已发生**。这两句我 v0.1 时压在一起了。**改正。**

---

# 6 · 知微 P5 · 两处分类措辞（接受）

## 6.1 M-3 L102「起点不可比 ⇒ NOT_APPLICABLE」

**我写的**：`起点不可比 ⇒ NOT_APPLICABLE`

**知微的判**：对**已经尝试**的 C1，required matched-baseline 前提失效，应说明是相应 execution/scope invalidity；设计阶段尚未建立可比性则记录未建立。**不能把尝试失效改成"不适用"来消除失败记录。**

**⇒ 接受。改为**：

```text
设计阶段尚未建立可比性      ⇒ NOT_ESTABLISHED
已尝试而 matched baseline 前提失效 ⇒ 相应 execution / scope INVALID
不写成 NOT_APPLICABLE
```

## 6.2 M-6 L156「关联事后建立 ⇒ 命中 `*_CHANGED_AFTER_OUTCOME`」

**我写的**：`关联事后建立 ⇒ 命中 *_CHANGED_AFTER_OUTCOME ⇒ INVALID`

**知微的判**：事后改规则、改成员/输入定义，与"事后按事前规则整理并核查已留存证据"不同。**不能用通配符自动认定某条事件发生。**

**⇒ 接受。改为**：

```text
须写明具体 changed 对象：
  · 改的是哪一条规则 / 哪一份 manifest / 哪一个成分集合
  · 何时改的（相对 outcome exposure）
  · 谁改的
或写明 provenance 缺口：
  · 缺哪一件必需来源证据

禁止：用 *_CHANGED_AFTER_OUTCOME 通配符自动认定某事件已发生。
缺失必要来源证据仍不得取得资格。
```

---

# 7 · 钳星认领的两格（登记，不代定）

钳星认领 v0.1 §2.1 的两行：

| 维度 | v0.1 写的"需要谁定" | 钳星回应 |
|---|---|---|
| W 的形态（短进程 a / 持久进程 b） | 钳星 | **已认领** |
| 写入主体是否单一 | 钳星 | **已认领** |

**⇒ 我登记为**：

```text
W_SHAPE_DECIDER              = 钳星（已认领，2026-10-26）
WRITER_SINGULARITY_DECIDER   = 钳星（已认领，2026-10-26）
W_SHAPE_DECISION             = NOT ESTABLISHED（尚未给出结论）
WRITER_SINGULARITY_DECISION  = NOT ESTABLISHED（尚未给出结论）
```

**⇒ 我不代他定，也不预填。** 这两格与 §5.3 的候选甲/乙直接对应。

---

# 8 · v0.2 状态表（替换 v0.1 §4）

```text
REAL_CANDIDATE_IDENTITY          = NOT ESTABLISHED

COND_1_C1_SCOPE_LIST             = NOT ESTABLISHED
  └ reference 有通用资格绑定校验（9 项 ok 条件），C1 专属 scope 清单无

COND_2_OBSERVER                  = NOT ESTABLISHED
  ├ O-1 权限                      = NOT ESTABLISHED
  ├ O-2 注册观测                  = NOT ESTABLISHED
  ├ O-3 跨文件一致性              = 机制缺失（≠ 故障已发生）
  └ observer 登记                 = EXISTS（合成常量 + MANIFEST L264-266）
     └ 真实运行身份/权限          = NOT ESTABLISHED

COND_3_TWO_ARMS                  = NOT ESTABLISHED
  ├ W-1 参考已有（夹具级目录隔离）≠ 进程/身份隔离
  ├ W-2 事前分配/匹配             = NOT ESTABLISHED
  ├ W-3 episode/环境匹配          = NOT ESTABLISHED
  └ W 形态 / writer 单一性        = 钳星已认领，决定未出

COND_4_REAL_C1_BINDING           = NOT VERIFIED（reference 实现存在）
  └ BF-8：writer 四层皆空 ⇒ "registered" 无绑定点

COND_5_STOP_CONDITION_MAPPING    = STILL_PENDING
  └ 已从 §37 抄入 8 项；§37 字节上 39 条；"至少包括"⇒ 39 非完整条数

COND_6_EPISODE_SPECIFIC_BINDING  = NOT ESTABLISHED
  ├ 夹具级关联                    = EXISTS（fixture_contracts/fixtures/recompute）
  ├ 真实 episode 事前注册         = NOT ESTABLISHED
  └ BF-9：episode 与 payload 同一 ⇒ 重放不可检出

RE_D_REAL_COMPONENT_REGISTRATION = NOT ESTABLISHED
  └ 三种"看似已登记"形态仍需分别登记

RE_E_WRITER_BINDING              = NOT ESTABLISHED  [新增]
RE_F_EPISODE_FIRST_EXECUTION     = NOT ESTABLISHED  [新增]
RE_G_SECTION37_FULL_APPLICABILITY= STILL_PENDING    [新增]

C1_MEASUREMENT_CHAIN_QUALIFIED   = NOT ESTABLISHED
C1_SCIENTIFIC_RESULT             = NOT ASSESSED
C1_END_TO_END_FEASIBILITY        = PENDING_DESIGN_VALIDATION

S_1 / S_2 = NOT SATISFIED ； S_3 = SATISFIED
NEW_B = DESIGN_PARKED ； RE-3 = NOT ESTABLISHED
CODE_CHANGE / IMPLEMENTATION_AUTHORIZATION = NONE / NOT AUTHORIZED
SCIENTIFIC_EXECUTION = MAY NOT START
FROZEN_Q3_RC11 = UNCHANGED
```

---

# 9 · 本轮我没有做的事

- **未**写代码、**未**运行实验、**未**改冻结件
- **未**把 reference 任何组件标为 SATISFIED
- **未**编造真实候选身份
- **未**借用 reference 清单填补 RE_D
- **未**代钳星定 W 形态或 writer 单一性
- **未**把 §37 的 39 条报成"完整"
- **未**用通配符自动认定某条 changed 事件已发生
- **未**把"机制缺失"写成"故障已发生"

---

# 10 · 我这一轮的自我判定

```text
MAPPING_STRUCTURE                   = 保持（三方程均认可）
REFERENCE_ASSET_INVENTORY           = 已按 P1 五项修正（本文件 §0.1 / §4）
MY_OWN_ERRORS_THIS_ROUND            = 3 条（E-1 说过头 / E-2 路径 404 / E-3 编号错位）
BLOCKING_FINDINGS_ACCEPTED          = BF-8 / BF-9 / BF-10（全部成立，逐条复核）
```

**睫把 BF-8 原样带回来，我接受原样**：

> 那 16 个字节谁写都行。而 C1 说的不是"内容对"，是"这次写的"。

**而我这一轮最该记住的，不是这张表补了多少格，是我在 M-2 上做的同一件事——把三个"有"写成了一个"无"。**

**这跟 v1 的毛病是同一个方向，只是这次不在结论上，在盘点表上。**

**问彼岸之前，先把"我手上有什么"数清。**
