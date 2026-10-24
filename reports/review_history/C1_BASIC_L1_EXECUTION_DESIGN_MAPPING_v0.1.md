# C1 / BASIC L1 EXECUTION DESIGN MAPPING v0.1

**性质**：**设计映射**。不是执行方案的批准版本，不构成实现或科学执行授权。
**基线**：`277ab34eeae072e485b3e32a8bbe661bcc4d5584`
**授权**：凌翼 `LINGYI · C1 / Basic L1 可行性研究裁定`（2026-10-24）

```text
SCIENTIFIC_TARGET_TRACK     = REAL_REGISTERED_BUSINESS_CANDIDATE
SYNTHETIC_REFERENCE_ROLE    = INSTRUMENT_CALIBRATION_ONLY
REAL_CANDIDATE_IDENTITY     = NOT ESTABLISHED
COND_6_EPISODE_SPECIFIC_BINDING = INDEPENDENT_REQUIRED

CODE_CHANGE = NOT AUTHORIZED ； IMPLEMENTATION_AUTHORIZATION = NONE
SCIENTIFIC_EXECUTION = MAY NOT START ； FROZEN_Q3_RC11 = UNCHANGED
```

**取法约定**：本表每条"已有实现"均标注取法——
`[读文件]` = 读了该行原文；`[读函数]` = 读了函数体；`[读签名]` = 只读了函数签名与参数。

---

# 0 · 一个必须先说的结构性事实（它决定了整张表）

## 0.1 `RegisteredState` 不携带 episode identity

`storage.py` L37-49 `[读文件]`：

```python
class RegisteredState:
    """A single arm's registered state, backed by two files in a sandbox dir.
    One arm per process. A/B/C for a given episode each live in their own
    RegisteredState (their own directory) — they are never co-resident in one
    writable mapping."""
    def __init__(self, sandbox_dir):
        self.dir = Path(sandbox_dir)
        self.literal_path = self.dir / LITERAL_FILENAME
        self.substrate_path = self.dir / SUBSTRATE_FILENAME
        self._write_open = False
```

**构造参数只有目录。没有 episode id、没有 execution id、没有 member id。**

## 0.2 于是 COND_6 的绑定对象，在 reference 里不存在

```text
reference 的 Arm 用"目录名"区分 A/B（fixtures.py L94-98 `[读文件]`）
但"目录名"不是注册身份；它不在 STATE 里，也不进入任何 digest
⇒ META↔STATE 的绑定【在 reference 中没有实现】
⇒ COND_6 无法从 reference 继承任何东西
```

**这与 `IDENTITY_ONLY_COMPONENTS = EMPTY_SET` 的理由一致**（L142-144 `[读文件]`）：

> episode identity lives in META

**⇒ META 存在，但 reference 不建立它与 STATE 的可验证关联。**

**这是本表最重要的一格：它说明 COND_6 不是"待补"，而是"参考实现里根本没有这个机制"。**

---

# 1 · 映射表主体

## M-1 · COND_1 · C1 scope 冻结规则与清单

| 字段 | 内容 |
|---|---|
| **冻结条款** | §13 Basic L1 gate 条件 1（L702）："本次 execution 与该 claim scope 所需 manifests / frozen rules 均有效" |
| **参考实现** | `verify_q3_freeze.py` 校验 Q3 十角色 `[读文件]`；但 **无 C1 scope 规则清单的校验** |
| **真实候选** | 未定（`REAL_CANDIDATE_IDENTITY = NOT ESTABLISHED`） |
| **适用差异** | reference 的 Q3 十角色清单**不能**充当 C1 规则清单；Q3 哈希通过 ≠ C1 清单已核 |
| **角色与哈希** | Q3：10 roles，digest `45034911…` `[读文件]`；**C1 scope 无对应清单** |
| **缺失证据** | **COND_1_C1_SCOPE_LIST = NOT ESTABLISHED** |
| **最小验证方案** | 列出 C1 所需 manifest / frozen rule 的**逐项清单**，并与 prereg 条文一一对应（设计，不执行） |
| **失败后果** | 清单缺失或版本不符 ⇒ **INVALID** |

## M-2 · COND_2 · 独立 State Observer

| 字段 | 内容 |
|---|---|
| **冻结条款** | §11（L606-625）：observer ≠ write operator；cannot write registered substrate；reads canonical STATE_FIELDS independently；computes identities independently；W 不能自证 |
| **参考实现** | `StateObserver.snapshot()` / `.digest()` / `snapshot_paths(literal_path, substrate_path)` `[读函数]`；**无可写方法** `[读文件]` |
| **真实候选** | 未定 |
| **适用差异** | ① 无写方法 ≠ 无写**权限**（须 token/DACL 证据）；② `snapshot_paths` L49-50 两次独立 `read_bytes()` `[读函数]`，**无跨文件一致性**；③ 无 "registered before/after" 的登记机制 |
| **角色与哈希** | §11 要求 `state_observer_identity / version / hash` 三字段（L611-613）`[读文件]`；**reference 未产生这三者** |
| **缺失证据** | **O-1 权限**｜**O-2 注册观测**｜**O-3 跨文件一致性**｜observer identity/version/hash **全部 NOT ESTABLISHED** |
| **最小验证方案** | 同一 observer token 下读取成功；写入/追加/截断/替换/权限修改按范围被拒绝；保留原始错误码（**计划，不执行**） |
| **失败后果** | 权限未证 ⇒ **INVALID**；一致性不成立 ⇒ **INVALID**（不补零） |

## M-3 · COND_3 · TARGET WRITE ARM vs NO-WRITE / MATCHED BASELINE

| 字段 | 内容 |
|---|---|
| **冻结条款** | §13 条件 3（L704）：preregistered `TARGET WRITE ARM` vs `NO-WRITE / MATCHED BASELINE CONTROL` 已实际执行 |
| **参考实现** | `fixtures.py` L94-98 `Arm` 以独立目录构造 `RegisteredState` 并 `initialize_baseline()` `[读文件]`；`RegisteredState.write_window()` 控制写入开关 `[读文件]` |
| **真实候选** | 未定 |
| **适用差异** | **W-1** 目录隔离 ≠ 进程/身份隔离 `[读文件]`；**W-2** 分配/匹配/重复次数无事前注册机制；**W-3** episode/环境/背景匹配未设计 |
| **额外事实** | `write_window()` 是**同一对象上的开关**，只约束"经本对象写入"，**不阻止外部进程直接写文件** `[读函数]` |
| **角色与哈希** | 无 arm 身份、无分配记录 |
| **缺失证据** | **W-2 / W-3 NOT ESTABLISHED**；W-1 参考已有但**不构成隔离证据** |
| **最小验证方案** | 事前注册：臂分配、匹配条件、重复次数、起点确认；两臂独立工作区与独立观察 |
| **失败后果** | 分配后置 ⇒ **INVALID**；起点不可比 ⇒ **NOT_APPLICABLE** |

## M-4 · COND_4 · `D_ATTRIBUTION` 规则与判别实现

| 字段 | 内容 |
|---|---|
| **冻结条款** | §13 条件 4（L705-709）：frozen `D_ATTRIBUTION` 在 `ΔS_identity_masked` 上给出 `ATTRIBUTED`；L713 限定**只产 Basic L1 / C1 scope** |
| **参考实现** | `evaluator.evaluate_basic_l1(snap_A, snap_B, registered_payload)` L216-267 `[读函数]`：<br>· L230 `q_B != q_A` ⇒ `ARM_CONFIG_INVALID`<br>· L237 `h = _literal_byte_diff_count(...)`<br>· L240 `h==0` ⇒ FAIL｜L246 `h==1` ⇒ UNRESOLVED｜L253 `h>=2` 继续<br>· **L254 `snap_B.literal != registered_payload` ⇒ PASS 但 `change_class=NOT_ESTABLISHED`**<br>· **L262-266 payload 匹配 ⇒ `change_class=C1`** |
| **真实候选** | 未定 |
| **适用差异** | ① 16-byte literal、`h=0/1/≥2` 阈值、payload 精确匹配**均不得自动转用**到不同 schema；② `ΔS_identity_masked` 在此 harness 上 **identity mask 为空 ⇒ 不遮任何东西**（L153 `[读文件]`）；③ `\|T\|>=1` 属 **C2**（L24/L27 `[读文件]`），不是 C1 依据 |
| **角色与哈希** | `D_ATTRIBUTION_ROLE_HASH`（prereg L1937）**未在代码中绑定** `[读文件+读代码]` |
| **缺失证据** | **COND_4_REAL_C1_BINDING = NOT VERIFIED** |
| **最小验证方案** | 逐项核对 role hash / 规则 bundle hash / 文件 hash / 运行 provenance 四者的语义映射，**不因名称相近视为同一件事** |
| **失败后果** | role/hash 未绑定 ⇒ **INVALID** |

**注意**：M-4 的参考实现**已包含 C1 第五条之外的第六条判据**（payload 匹配）。**这是 reference 唯一一处真正实现"gate ≠ C1"的地方。**

## M-5 · COND_5 · stop condition 逐项适用

| 字段 | 内容 |
|---|---|
| **冻结条款** | §13 条件 5（L711）：required provenance 完整，且无命中与本次 claim 相关的 §37 invalidity / stop condition |
| **参考实现** | **无**——reference 未实现 stop condition 检查 |
| **真实候选** | 未定 |
| **适用差异** | prereg §37 明写"**至少包括**"（L2203），**无固定条数** |
| **角色与哈希** | provenance 链未建立 |
| **缺失证据** | **STOP_CONDITION_COMPLETE_MAPPING = STILL_PENDING** |
| **最小验证方案** | 逐项适用表：冻结条款 → C1 是否依赖 → 必需证据 → 触发后果 |
| **失败后果** | 条款缺席 ⇒ **INVALID**；**条款存在 ≠ 事件已发生**（当前全部 S-1） |

**已识别的 8 项**（`[读文件]`，L2210-2213 / L2237 / L2251 / L2253 / L2254）：

| 条款 | C1 依赖 | 备注 |
|---|---|---|
| `STATE_FIELDS_CHANGED_AFTER_OUTCOME` | 是 | 事后改动 |
| `IDENTITY_ONLY_COMPONENTS_CHANGED_AFTER_OUTCOME` | 是 | 事后改动 |
| `LITERAL_STORAGE_COMPONENTS_CHANGED_AFTER_OUTCOME` | 是 | 事后改动 |
| `STORAGE_PIPELINE_NUISANCE_COMPONENTS_CHANGED_AFTER_OUTCOME` | 是 | 事后改动 |
| `STATE_OBSERVER_NOT_INDEPENDENT` | 是 | 对应 M-2 |
| `UNREGISTERED_EPISODE_REINJECTION` | 是 | 对应 COND_6 / N-5 |
| `UNREGISTERED_RETRIEVAL_INDUCED_WRITE` | 是 | 对应 N-3 |
| `RESET_COMPATIBILITY_NOT_ESTABLISHED` | pre-reset C1 不直接依赖 | 不适用 |

## M-6 · COND_6 · episode-specific 绑定（**独立必需**）

| 字段 | 内容 |
|---|---|
| **冻结条款** | C1 class rule（L722-724）："an episode-specific registered storage write is established in preregistered `LITERAL_STORAGE_COMPONENTS`"；L727 明文 gate PASS ≠ C1 |
| **参考实现** | **无**。`RegisteredState.__init__(sandbox_dir)` 只收目录 `[读函数]`；`Arm` 用目录名区分 A/B `[读文件]`；**无 episode id / execution id / member id 落入 STATE 或 digest** |
| **真实候选** | 未定 |
| **适用差异** | **reference 的目录隔离不能充当 episode 绑定**；`IDENTITY_ONLY = EMPTY_SET` 的理由正是 "episode identity lives in META"（L142-144 `[读文件]`）——**而 META 与 STATE 的关联未建立** |
| **角色与哈希** | 无 episode role / 无 execution role |
| **缺失证据** | **COND_6_EPISODE_SPECIFIC_BINDING = NOT ESTABLISHED** |
| **最小验证方案** | 在 outcome **之前**定义：episode id 的产生规则、META 记录格式、STATE↔META 的可验证关联（如 payload 与 META 的一致性检验）、绑定时刻与证据留存。**不得通过改变 digest 输入域伪造关联**（凌翼明文） |
| **失败后果** | 关联缺失 ⇒ **INVALID**；关联事后建立 ⇒ 命中 `*_CHANGED_AFTER_OUTCOME` ⇒ **INVALID** |

## M-7 · RE_D · 真实候选三成分清单独立登记

| 字段 | 内容 |
|---|---|
| **冻结条款** | LITERAL_STORAGE_COMPONENTS 须"**preregistered**"（L723）；三条 `*_COMPONENTS_CHANGED_AFTER_OUTCOME`（L2211-2213） |
| **参考实现** | `harness_constants.py` L156-161 `[读文件]`：`STATE_FIELD_LITERAL` / `IDENTITY_ONLY_COMPONENTS`(空) / `LITERAL_STORAGE_COMPONENTS` / `NONSTORAGE_COMPONENT` |
| **真实候选** | 未定 |
| **适用差异** | **这三份清单属于 reference harness**。真实候选必须独立登记 |
| **角色与哈希** | reference 清单无注册身份/时间戳 |
| **缺失证据** | **RE_D_REAL_COMPONENT_REGISTRATION = NOT ESTABLISHED** |
| **最小验证方案** | 真实候选的三个成分清单 + `STATE_FIELDS`，在 outcome 前登记，带身份与时间戳 |
| **失败后果** | 借用 reference 清单 ⇒ **INVALID**（凌翼明文禁止） |

**三种"看似已登记"的形态，须分别登记原因**：

| 形态 | 与 M-7 的关系 |
|---|---|
| 登记晚了 | 有清单，时间戳在 outcome 后 |
| 没登记 | 无清单 |
| **借了别处的登记** | **有清单，但属 reference harness** |

---

# 2 · 真实候选：我必须说"未定"而不是编一个

凌翼要求：

> Coder 应在映射中提出具体候选及其身份、schema、生命周期、注册 substrate 和可复核依据。
> 在具体候选尚未通过设计审查之前：`REAL_CANDIDATE_IDENTITY = NOT ESTABLISHED`

## 2.1 我能提出的候选**类型**（不冒充已定身份）

| 维度 | 候选选项 | 需要谁定 |
|---|---|---|
| **substrate 形态** | (a) 沿用 `literal.bin[16] + substrate.bin[8]` | 科学范围 |
| | (b) 新 schema（长度、字段、编码不同） | 科学范围 + 需新绑定 |
| **W 的形态** | (a) 短生命周期进程（便于退出后读取） | 钳星 |
| | (b) 持久进程（需可验证静止阶段） | 钳星 + 知微 |
| **episode 载体** | META 文件 / 注册表 / 控制器内存 | COND_6 设计 |
| **写入主体** | 单一 writer 进程 | 钳星 |

## 2.2 我不提出的部分及理由

```text
REAL_CANDIDATE_IDENTITY = NOT ESTABLISHED
理由：候选身份涉及"被测系统是什么"——这是科学范围决定，
      不是我在设计映射里可以自行指定的。
      若我编一个候选，就会重现 v1 的毛病：
      在"现有的是什么"上给出比证据更快的结论。
```

**我只提供上述选项维度与各自的后果，不选定。**

---

# 3 · 参考实现能迁移什么、不能迁移什么

| 组件 | 可迁移 | 不可迁移 | 依据 |
|---|---|---|---|
| `canonical_state_bytes/digest` | 编码方式可作为**参照** | 16/8 字节规格不得自动套用新 schema | `harness_constants.py` L69/L85 `[读函数]` |
| `evaluate_basic_l1` 的**逻辑结构** | "先判 arm 有效、再判 h、再判 payload" 的顺序可参照 | `h=0/1/≥2` 阈值与 payload 精确匹配 | L216-267 `[读函数]` |
| `RegisteredState` 目录隔离 | 提供了"一臂一目录"的形态 | **不等于**进程/身份隔离 | `storage.py` L37-43 `[读文件]` |
| `write_window()` | 可用于"写入阶段"标记 | **不阻止外部写**，不能当作写能力边界 | L112-121 `[读函数]` |
| `StateObserver` | 无写方法的职责划分可参照 | **不证明**运行主体无写权限；**无**跨文件一致性 | `observer.py` L27-57 `[读函数]` |
| reference 三成分清单 | 格式可参照 | **真实候选须独立登记** | M-7 |

---

# 4 · 状态

```text
REAL_CANDIDATE_IDENTITY          = NOT ESTABLISHED
COND_1_C1_SCOPE_LIST             = NOT ESTABLISHED
COND_2_OBSERVER                  = NOT ESTABLISHED（O-1/O-2/O-3 全未建立）
COND_3_TWO_ARMS                  = NOT ESTABLISHED（W-2/W-3 未设计；W-1 参考已有≠隔离）
COND_4_REAL_C1_BINDING           = NOT VERIFIED（reference 实现存在）
COND_5_STOP_CONDITION_MAPPING    = STILL_PENDING
COND_6_EPISODE_SPECIFIC_BINDING  = NOT ESTABLISHED（reference 无此机制）
RE_D_REAL_COMPONENT_REGISTRATION = NOT ESTABLISHED

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

# 5 · 本轮我没有做的事

- **未**写代码、**未**运行实验、**未**改冻结件
- **未**把 reference 任何组件标为 SATISFIED（凌翼明文禁止）
- **未**编造真实候选身份
- **未**借用 reference 清单填补 RE_D
- **未**把 synthetic 结果转述为科学发现

---

# 6 · 提交三方程审查

**按凌翼指定**：
- **睫**：科学结论边界 / COND_6 归属 / C1 class rule / claim-scoped stop-condition 完整性
- **知微**：Windows 最小验证路径 / observer 权限 / 快照一致性 / reference↔真实候选技术差异
- **钳星**：两臂生命周期 / episode 边界 / 运行时残留 / 失败后资源状态

**本映射不构成实施授权或科学验收。**
