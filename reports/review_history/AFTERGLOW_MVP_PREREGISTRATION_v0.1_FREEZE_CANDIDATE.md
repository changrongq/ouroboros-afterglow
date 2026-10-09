# AFTERGLOW MVP PREREGISTRATION v0.1

## Ouroboros Project · 千年舟

**Status:** FREEZE-CANDIDATE / NOT FROZEN / NOT AUTHORIZED FOR EXECUTION  
**Purpose:** Preregistration for the first implementation-neutral Afterglow MVP  
**Scope:** attributable registered change, change classification, preregistered ON/OFF causal-contrast identification, and reset persistence  
**Explicitly Not Claimed:** MEMORY_QUALIFIED

---

# 0. Status, Authority, and Review Scope

本文件是一份实验预注册候选文本。

它：

- 不构成实验执行授权；
- 不构成 Memory Qualification Protocol；
- 不宣称任何 architecture 已经具有 memory；
- 不宣称 Afterglow 已经作为机制或现象存在；
- 不改变 Memory Constitution 的独立治理程序状态。

本文件只回答四个逐层递进的问题：

1. 一次被注册的经历，是否真的使 registered system 发生了一次可归属状态改变？
2. 在同一 episode / baseline / storage path 下，registered ON/OFF intervention 是否产生可归属的 nonstorage treatment contrast？
3. 在事前冻结的 outcome basis 与 contrast scale 下，ON/OFF treatment contrast 是否随 preregistered episode content class 稳定变化？
4. 已经建立的证据层级，是否能在一个明确注册、与实现相容、且被验证有效的 reset 后重新建立？

本文件中的 L1 / L2 是：

```text
ENGINEERING_GATES
PROTOCOL_LEVEL
```

它们不等同于：

```text
MEMORY_QUALIFICATION_GATE
```

因此：

```text
L1/L2 PASS != MEMORY_QUALIFIED
```

未来若启用 `MEMORY_QUALIFIED`，须由独立 Memory Qualification Protocol 定义并按适用治理程序授权。

---

# 1. Six Core Invariants

本 prereg 的核心不变量只有六条。

1. **经历造成的变化必须可归因。**
2. **storage 与额外 transformation 必须分开。**
3. **content-conditioned claim 必须比较事前冻结的 ON/OFF treatment contrasts，而不是 raw state、target-only delta 或事后选择的尺度。**
4. **reset 后的 claim 必须由 reset 后证据重新建立。**
5. **没测 / 没发现 / 无法归因 / 科学失败 / 协议无效不得互换。**
6. **所有判断规则必须先于 outcome 冻结。**

任何后续条款都只是为了让这六条机械可执行。

复杂度本身也会制造错误。

因此：

> **能删除一个 summary 字段解决的问题，不新增两个字段。**

---

# 2. Project / Phenomenon / Mechanism Separation

必须严格分离：

```text
PROJECT
PHENOMENON
MECHANISM
```

## 2.1 Project

```text
PROJECT_NAME = Afterglow
```

该名称：

```text
DOES NOT imply mechanism exists
DOES NOT imply phenomenon exists
DOES NOT imply memory has been qualified
```

## 2.2 Mechanism Candidate

逻辑机制位置暂称：

```text
PERSISTENT_WRITE_MECHANISM
PWL / equivalent future implementation
```

它不绑定：

```text
parameter update
adapter
rank
loss
attention bias
external persistent store
memory matrix
graph
vector
database
backbone plasticity
```

任何具体实现成功：

```text
IMPLEMENTATION SUCCESS != ONTOLOGICAL PROOF
```

---

# 3. Core Formal Model

使用最小状态模型：

```text
S_(t+1) = W(S_t, E)
```

其中：

- `E`：前瞻注册的 episode；
- `S_t`：write 前 registered substrate state；
- `W`：被测试的 write/change operator；
- `S_(t+1)`：write 后 registered substrate state。

未来计算抽象为：

```text
Y_future = F_theta(X_future, S)
```

本 MVP 不要求 `S` 或 `W` 属于任何特定工程实现。

---

# 4. Implementation-Neutral Does Not Mean Implementation-Blank

任何实际 execution 启动前，必须生成并冻结：

```text
IMPLEMENTATION_BINDING_MANIFEST
IMPLEMENTATION_BINDING_HASH
PARENT_PREREG_HASH

registered_substrate_identity
registered_substrate_version

write_operator_identity
write_operator_version
write_operator_hash

state_schema_version

state_delta_rule_id
state_delta_rule_hash

causal_contrast_rule_id
causal_contrast_rule_hash

state_observer_identity
state_observer_version
state_observer_hash

content_class_manifest_id
content_class_manifest_hash

content_class_evidence_set_id
content_class_evidence_set_hash

attribution_ledger_schema_id
attribution_ledger_schema_hash

discrimination_ruleset_id
discrimination_ruleset_hash

reset_profile_id
reset_profile_hash
reset_compatibility_manifest_hash

post_reset_class_rule_id
post_reset_class_rule_hash

persistence_match_rule_id
persistence_match_rule_hash

base_model_hash
execution_environment_identity
```

不得使用 substantive placeholder。

若任何 execution-critical rule 尚未实例化或冻结：

```text
RUN MAY NOT START
```

---

# 5. Registered System Boundary

执行前必须产生：

```text
SYSTEM_BOUNDARY_MANIFEST
REGISTERED_BOUNDARY_ID
BOUNDARY_HASH
```

本协议中的 “internal” 定义为：

> **inside the pre-registered agent/system boundary**

而不是：

> inside backbone weights only

因此 external persistent substrate 可以属于 registered system state，只要它：

1. 在 outcome exposure 之前进入 `SYSTEM_BOUNDARY_MANIFEST`；
2. 有稳定 identity；
3. 受 provenance 管理；
4. 实际参与未来计算；
5. 未在看到结果后才被重新划入 system boundary。

原则：

```text
Boundary must precede outcome.
```

boundary 之外的资源：

```text
IS NOT SYSTEM STATE
```

---

# 6. Base Model Experimental Freeze

本 v0.1：

```text
BASE_MODEL_WEIGHTS = FROZEN
BASE_MODEL_HASH = REGISTERED
```

这是：

```text
PROTOCOL-LEVEL EXPERIMENTAL CONSTRAINT
```

而不是：

```text
CONSTITUTIONAL INVARIANT
```

目的仅为控制变量和保持 causal attribution 可解释。

因此：

```text
BASE_MODEL_HASH_MISMATCH -> RUN INVALID
```

只表示本次 execution 违反 protocol。

不得解释为：

```text
base-weight plasticity is unconstitutional
```

本协议不宣称：

```text
memory cannot exist in backbone weights
```

---

# 7. State Identity

必须严格区分：

```text
STATE_FIELDS
META_FIELDS
VOLATILE_FIELDS
```

## 7.1 STATE_FIELDS

只有实际属于 registered substrate、且参与未来计算的注册内容进入：

```text
REGISTERED_SUBSTRATE_STATE_DIGEST
```

## 7.2 META_FIELDS

不得进入 substrate state digest：

```text
timestamp
wall-clock time
audit log
provenance record
sequence number
write_count
episode_id
file modification time

before_state_digest
after_state_digest
any digest derived from STATE_FIELDS
```

闭合规则：

```text
digest input  = STATE_FIELDS only
digest output = META_FIELD
```

digest 输出不得回灌进自己的输入。

## 7.3 Separate digests

至少分别产生：

```text
REGISTERED_SUBSTRATE_STATE_DIGEST
PROVENANCE_RECORD_DIGEST
VOLATILE_RUNTIME_DIGEST
```

三者不得混为一个 state identity。

---

# 8. Identity / Storage / Nuisance Decomposition

## 8.1 Identity-only components

以下内容单独出现，不足以建立 transformation：

```text
episode_id copy
episode hash copy
sequence-number copy
timestamp copy
direct identity-label copy
reversible episode-identity encoding
identity-equivalent re-encoding
```

必须事前登记为：

```text
IDENTITY_ONLY_COMPONENTS
```

换一层编码壳不得绕过本条。

## 8.2 Audit log != registered storage

必须区分：

```text
AUDIT_LOG
REGISTERED_STORAGE_SUBSTRATE
```

audit/provenance log 属 META。

但一个事前注册、位于 system boundary 内、参与未来计算的 persistent store，可以是合法 STATE substrate。

因此本协议既不宣布：

```text
storage can never be memory
```

也不允许：

```text
literal storage automatically proves transformation
```

## 8.3 Literal-storage components

必须事前登记：

```text
LITERAL_STORAGE_COMPONENTS
```

至少包括：

```text
verbatim episode-content copy
lossless reversible content encoding
append-only content record
```

## 8.4 Storage-pipeline nuisance components

必须事前登记：

```text
STORAGE_PIPELINE_NUISANCE_COMPONENTS
```

例如可能包括：

```text
byte-count fields
token-count fields
serialization-length fields
append pointers
allocation metadata
storage acknowledgements
checksums
storage-path counters
mechanically induced bookkeeping state
```

不能在 outcome 后把不喜欢的变化重新命名为 nuisance。

---

# 9. STATE_DELTA_RULE

执行前必须冻结：

```text
STATE_DELTA_RULE_ID
STATE_DELTA_RULE_HASH
```

该 rule 必须机械地产生至少：

```text
ΔS_registered
ΔS_identity_masked
ΔS_nonstorage
```

其中：

```text
ΔS_identity_masked
=
registered change after canonical masking of
IDENTITY_ONLY_COMPONENTS
```

以及：

```text
ΔS_nonstorage
=
registered change after canonical masking of
IDENTITY_ONLY_COMPONENTS
+
LITERAL_STORAGE_COMPONENTS
+
STORAGE_PIPELINE_NUISANCE_COMPONENTS
```

这里的 masking 是 registered state-delta operation。

它：

```text
DOES NOT assume state is a vector
DOES NOT mean arbitrary post-hoc subtraction
```

在本 v0.1 中：

> **`ΔS_nonstorage` 是所有 C2/C3 causal-contrast analyses 的唯一 canonical registered outcome basis。**

它不是：

```text
causal effect itself
proof of attribution
representation-independent latent mechanism
```

本 v0.1 不允许用另一个 “semantically equivalent projection” 替换它。

若某 implementation 无法直接在 canonical `ΔS_nonstorage` 上定义其 preregistered contrast analysis：

```text
PROTOCOL REVISION REQUIRED
NEW CANONICAL HASH REQUIRED
FINAL BLOCKING REVIEW RESTARTS
```

不得在 outcome exposure 后现场选择 alternative projection。

---

# 10. CAUSAL_CONTRAST_RULE

C2/C3 不构造一个需要被解释为“causal substance”的 state-like causal-effect object。

它们只评估事前冻结的 paired ON/OFF treatment contrast。

执行前必须冻结：

```text
CAUSAL_CONTRAST_RULE_ID
CAUSAL_CONTRAST_RULE_HASH
```

其 canonical inputs 为同一 episode `E` 下：

```text
ΔS_nonstorage(target_ON, E)
ΔS_nonstorage(matched_OFF, E)
```

其中 outcome basis 固定为 §9 的 canonical `ΔS_nonstorage`。

`CAUSAL_CONTRAST_RULE` 必须在 outcome exposure 前明确：

```text
treatment definition
ON/OFF pairing rule
baseline matching rule
replication structure
contrast statistic
normalization rule, if any
comparison scale
threshold / equivalence rule
uncertainty rule
indeterminate region
failure behavior
```

它可以输出一个 registered treatment-contrast result，记作：

```text
T_CONTRAST_RESULT(E)
```

但：

```text
T_CONTRAST_RESULT(E) != state object
T_CONTRAST_RESULT(E) != representation-independent causal essence
```

不得在 outcome exposure 后从多个 statistics / distances / normalizations / thresholds 中选择更有利者。

C3 的解释边界固定为：

> **C3 是相对于 preregistered outcome basis、contrast statistic 与 measurement scale 的 treatment-contrast heterogeneity claim。**

因此：

```text
C3 PASS
!= proof that the latent mechanism is intrinsically content-sensitive
   independent of the registered outcome representation or contrast scale
```

本 protocol 不要求证明存在一把 representation-independent 的“宇宙真尺”。

它只要求：

> 这把尺子在 outcome exposure 前已经冻结，并且结果出来后不得换尺子救 claim。

---

# 11. Independent State Observer

before / after state 必须由独立于 `W` 的 observer 采集。

冻结：

```text
state_observer_identity
state_observer_version
state_observer_hash
```

要求：

```text
observer != write operator
observer cannot write registered substrate
observer reads canonical STATE_FIELDS independently
observer computes state identities independently
```

`W` 不能认证自己已经改变 state。

---

# 12. Positive Evidence Ladder

本 prereg 只保留三个正向 evidence classes。

## C1 — STORAGE_WRITE_ESTABLISHED

C1 表示：

> **storage write 是目前最高被正向建立的 change class。**

它不表示：

> reality contains only storage change.

最强允许 claim：

```text
REGISTERED_STORAGE_WRITE_OBSERVED
```

因此 C1 是证据断言，不是世界断言。

## C2 — EVENT_TRIGGERED_NONSPECIFIC_CHANGE

C2 表示：

> 在 same-E / same-storage-path matched ON/OFF counterfactual 中，canonical `ΔS_nonstorage` 上存在可归属于 target intervention 的 registered treatment contrast；但尚未建立该 contrast 对 episode content class 的稳定依赖。

最强允许 claim：

```text
EVENT_TRIGGERED_NONSPECIFIC_CHANGE_OBSERVED
```

## C3 — CONTENT_CONDITIONED_TREATMENT_CONTRAST_HETEROGENEITY

C3 表示：

> 在同一个 frozen `CAUSAL_CONTRAST_RULE` 下，不同 preregistered episode-content classes 产生可复现、可区分、且逐成员可归因的 ON/OFF treatment-contrast results。

最强允许 claim：

```text
CONTENT_CONDITIONED_TREATMENT_CONTRAST_HETEROGENEITY_OBSERVED
```

C3 是 measurement-scale / outcome-representation conditional 的操作性 interaction claim。

它不表示：

> target mechanism 在脱离 registered outcome basis 与 contrast scale 后仍具有 representation-independent 的“内在内容敏感性”。

C1 / C2 / C3 都不是 memory ontology verdict。

---

# 13. L1 — Attributable Registered Change

L1 首先问：

> episode `E` 是否导致了可归属 registered change？

输出：

```text
L1 = PASS / FAIL / UNRESOLVED
PRE_RESET_CHANGE_CLASS = C1 / C2 / C3
```

`L1` 是所有正向 pre-reset class 的共同入口，但不是一个独立 evidence class。

任何正向 `PRE_RESET_CHANGE_CLASS = C1 / C2 / C3` 都必须先通过同一个 Basic L1 gate：

1. 本次 execution 与该 claim scope 所需 manifests / frozen rules 均有效；
2. §11 `Independent State Observer` 合法，并完成 registered before / after observation；
3. §28.1 preregistered `TARGET WRITE ARM` vs `NO-WRITE / MATCHED BASELINE CONTROL` 已实际执行；
4. frozen `D_ATTRIBUTION` 在该 §28.1 scope 的 canonical `ΔS_identity_masked` 上给出 Basic-L1/C1-scope：

```text
attribution_result = ATTRIBUTED
```

5. required provenance 完整，且没有命中与该 attempted claim 相关的 §37 invalidity / stop condition。

这里的 `D_ATTRIBUTION` 只产生 Basic L1 / C1 scope 的 attribution result；它不得满足 C2/C3 的 nonstorage attribution requirement。

当 Basic L1 gate 通过后，`L1 = PASS` 仅在至少一个 evidence class 被其自身规则独立建立时成立，且：

```text
if C3 is independently established under §§19–20:
    PRE_RESET_CHANGE_CLASS = C3
else if C2 is independently established under §16:
    PRE_RESET_CHANGE_CLASS = C2
else if an episode-specific registered storage write is established
        in preregistered LITERAL_STORAGE_COMPONENTS under the Basic L1 / §28.1 scope:
    PRE_RESET_CHANGE_CLASS = C1
```

因此 Basic L1 PASS 本身不得被引用为 C1/C2/C3；`PRE_RESET_CHANGE_CLASS` 必须来自对应 class rule。

若 required structure 均有效并已执行，而 frozen Basic L1 attribution rule 给出确定负结果：

```text
L1 = FAIL
```

若 required structure 均有效并已执行，而结果落入 preregistered indeterminate region：

```text
L1 = UNRESOLVED
```

若 required rule / manifest / witness 缺失、observer 不合法、rule 在 outcome 后改变或 provenance broken，则按既有 invalidity semantics 处理；不得把 protocol/execution invalidity 写成 `L1 = FAIL`。

禁止只传播裸：

```text
L1 PASS
```

---

# 14. Same-E / Same-Storage-Path Counterfactual

任何想进入 C2 或 C3 的 execution 都必须建立：

```text
TARGET ARM
same baseline S0
same episode E
same literal-storage path
W_extra = ON
```

以及：

```text
MATCHED OFF ARM
same baseline S0
same episode E
same literal-storage path
W_extra = OFF
```

两边唯一允许被有意改变的变量是：

```text
target additional transformation intervention
```

不得用：

```text
store(E_ctrl)
store(empty)
different serialization path
different storage implementation
```

替代同等级 counterfactual。

若 architecture 无法构造该反事实：

```text
C2 = ARCHITECTURALLY_NOT_IDENTIFIABLE
C3 = ARCHITECTURALLY_NOT_IDENTIFIABLE
```

它仍可建立 C1。

这不同于：

```text
NOT_ASSESSED
NOT_ESTABLISHED
UNRESOLVED
INVALID
```

不得互换。

---

# 15. Attribution Is a Relation, Not a Scalar

权威证据不是：

```text
ATTRIBUTED
```

这种 phase-level summary scalar。

权威证据是：

```text
ATTRIBUTION_LEDGER
```

其 schema 必须事前冻结：

```text
ATTRIBUTION_LEDGER_SCHEMA_ID
ATTRIBUTION_LEDGER_SCHEMA_HASH
```

每个 attribution entry 至少绑定：

```text
phase
episode_identity
content_class_identity

target_execution_id
matched_off_execution_id
pair_identity

baseline_state_id
storage_pipeline_identity

state_delta_rule_hash
causal_contrast_rule_hash

D_NONSTORAGE_BASELINE_ROLE_HASH

reset_profile_id
reset_profile_hash

attribution_result
```

其中这些字段的 persistence identity 语义固定如下：

```text
LOGICAL EVIDENCE IDENTITY
C2:
  episode_identity
  pair_identity
  storage_pipeline_identity
  state_delta_rule_hash
  causal_contrast_rule_hash

C3 additionally requires:
  content_class_identity
  CONTENT_CLASS_EVIDENCE_SET_HASH

REALIZATION METADATA
  phase
  baseline_state_id
  target_execution_id
  matched_off_execution_id
```

`pair_identity` 必须在 outcome exposure 前分配，并作为跨 phase 稳定的 logical ON/OFF pair key。pre-reset 与 post-reset 的 execution IDs 是该 logical pair 的不同 realization，不是 logical identity。

`baseline_state_id` 表示某次实际 measurement 的 substrate 起点，因此属于 realization metadata；它必须分别登记，但不得要求跨 reset 相同。

`storage_pipeline_identity` 是 registered experimental configuration identity。对于声称同一 registered storage path 下的 C2/C3 persistence，它不得在不同 phase 间被 outcome 后替换。

C2 本身不要求 content class。若某个 C2 evidence unit 并非同时属于 C3 attempt：

```text
content_class_identity = N/A
```

是合法且明确的值，不得被解释为漏填。

`attribution_result` 至少允许表达：

```text
ATTRIBUTED
DETECTED_UNATTRIBUTED
NOT_ASSESSED
N/A
```

`attribution_result` 的 authoritative producer 必须跟随该 entry 所服务的 claim scope；不得让一个低阶 scope 的 `ATTRIBUTED` 跨层复用。

Basic L1 / C1 scope：

```text
D_NONSTORAGE_BASELINE_ROLE_HASH = N/A
attribution_result is produced by the frozen D_ATTRIBUTION role
```

这里的 frozen `D_ATTRIBUTION_ROLE_HASH` 由 machine provenance 全局绑定；不为每个 entry 新增重复字段。

C2 / C3 nonstorage-attribution scope：

```text
D_NONSTORAGE_BASELINE_ROLE_HASH = <the frozen registered role hash>
attribution_result is produced by that D_NONSTORAGE_BASELINE role
```

因此：

```text
Basic-L1/C1-scope ATTRIBUTED
MUST NOT satisfy any C2/C3 attribution requirement.
```

`service_scope` 由 attempted claim、该 role-hash convention 与对应 evidence structure 机械推出；本 v0.1 不新增 `service_scope` 字段。

`ARCHITECTURALLY_NOT_IDENTIFIABLE` 不塞进 `attribution_result`；它表示当前 implementation 下没有可执行的 paired identification path，不是一次 attribution execution 的结果。

任何 human-facing scalar summary 若存在，只能标为：

```text
DERIVED / NON-AUTHORITATIVE
```

不能替 ledger 投票。

---

# 16. C2 Rule

C2 的 authoritative rule 直接查询 required attribution scope。

只有当 C2 所要求的 paired evidence 已实际执行，并且对应 ledger entries 满足：

```text
registered ON/OFF treatment contrast established
AND
D_NONSTORAGE_BASELINE_ROLE_HASH = <the frozen registered role hash>
AND
attribution_result = ATTRIBUTED
```

这里的 `ATTRIBUTED` 必须由该 frozen `D_NONSTORAGE_BASELINE` role 在 registered ON/OFF treatment-contrast result 上产生；Basic L1 / C1 scope 的 `D_ATTRIBUTION` result 不得满足这一 conjunct。

才可建立 C2。

若 required structure 缺失或 outcome 后改动：

```text
relevant result INVALID
```

若结构完整、实验已执行，但 registered treatment contrast / causal attribution 未建立：

```text
C2 = NOT_ESTABLISHED
```

不得把科学负结果包装成 protocol invalidity。

---

# 17. CONTENT_CLASS_MANIFEST

任何想获得 C3 的 experiment，必须在 outcome exposure 前冻结：

```text
CONTENT_CLASS_MANIFEST_ID
CONTENT_CLASS_MANIFEST_HASH
```

至少包括：

```text
class_definition_source
class identities
class definitions

episode identities
episode -> class assignment rule

same-class equivalence question
cross-class distinction question

known nuisance variables
known material nuisance moderators
matching / balancing / blocking / stratification / preregistered adjustment rules
moderator disposition table

baseline substrate identity

class-definition timestamp
reviewer identity
```

每一个在 ignition 前已知、且被判定为 material 的 nuisance moderator，都必须具有 preregistered disposition：

```text
CONTROLLED_BY_REGISTERED_DESIGN
```

或者：

```text
C3 = NOT_ASSESSED
```

不能以“没有写”表示“没有 moderator”。

若一个已知 nuisance 被事前判定为 non-material，也必须在 manifest 中列出并给出 preregistered rationale；不得 outcome 后因为结果不利而重新把它命名为 material / non-material。

若 outcome exposure 后才发现新的 plausible moderator：

```text
NO POST-HOC RESCUE OF CURRENT C3
```

它可以导致当前 claim 被限定、暂缓或未来 protocol revision，但不能用新的 adjustment 去加强或挽救当前 C3。

不允许：

```text
model output told us what clustered together
post-hoc clustering defined the class
results suggested a better grouping
```

不是让结果告诉我们输入原本属于哪一类。

---

# 18. CONTENT_CLASS_EVIDENCE_SET

C3 必须事前冻结：

```text
CONTENT_CLASS_EVIDENCE_SET_ID
CONTENT_CLASS_EVIDENCE_SET_HASH
```

该 evidence set 明确列出用于：

```text
same-class reproducibility
cross-class distinguishability
```

的所有 logical member slots。

每个 logical member slot 必须在 outcome exposure 前绑定其 `episode_identity`、`content_class_identity`、logical `pair_identity` 以及适用的 frozen rule/configuration identity。

phase-specific `target_execution_id` / `matched_off_execution_id` 只是该 logical slot 在对应 phase 的 realization；它们不得写入 `CONTENT_CLASS_EVIDENCE_SET` 的 logical identity，从而不得因为 reset 后产生新的 execution IDs 而改变 `CONTENT_CLASS_EVIDENCE_SET_HASH`。

默认所有 C3 member 必须从同一个 preregistered baseline substrate state 出发。

若研究 cumulative / trajectory-dependent state：

```text
NEW PROTOCOL REQUIRED
```

不得偷偷混入本 v0.1 C3 gate。

---

# 19. Every C3 Member Must Be Individually Attributed

对于：

```text
FOR EVERY e IN CONTENT_CLASS_EVIDENCE_SET
```

必须存在属于正确 phase 的 paired attribution evidence：

```text
target(e)
matched_OFF(e)
same baseline
same E
same storage path
```

且 attribution ledger 中：

```text
D_NONSTORAGE_BASELINE_ROLE_HASH(e) = <the frozen registered role hash>
attribution(e) = ATTRIBUTED
```

这里的 `ATTRIBUTED` 必须由 frozen `D_NONSTORAGE_BASELINE` 对该 member 的 ON/OFF treatment-contrast result 产生；Basic L1 / C1 scope 的 `D_ATTRIBUTION` result 不得替代它。

之后该 member 在同一个 frozen `CAUSAL_CONTRAST_RULE` 下得到的：

```text
T_CONTRAST_RESULT(e)
```

才有资格进入 C3 class comparison。

不能只给一条 episode 做 paired causal attribution，再让其他未归因 episode 参与 C3。

若某个 member 已登记、实验已执行，但 attribution 不是 `ATTRIBUTED`：

```text
C3 = NOT_ESTABLISHED
```

然后独立评估 C2。

这不是 protocol INVALID。

若 scope/evidence manifest 缺失或 outcome 后改变：

```text
relevant result INVALID
```

---

# 20. C3 Compares Treatment Contrasts, Not Raw State

C3 的 canonical comparison object 是：

```text
T_CONTRAST_RESULT(E)
```

它由同一个 frozen `CAUSAL_CONTRAST_RULE` 对：

```text
ΔS_nonstorage(target_ON, E)
ΔS_nonstorage(matched_OFF, E)
```

进行 preregistered contrast analysis 得到。

它不是：

```text
raw state
ΔS_registered
ΔS_identity_masked
ΔS_nonstorage(target only)
```

也不是 representation-independent 的 causal substance。

## 20.1 Same-class reproducibility

选择：

```text
different episodes
same preregistered content class
```

要求：

```text
T_CONTRAST_RESULT(E_A1) ~ T_CONTRAST_RESULT(E_A2)
```

其中 `~` 由事前冻结的 equivalence rule 决定。

同一 episode replay 只能作为 repeatability control，不能替代 class-level generalization。

## 20.2 Cross-class distinguishability

对于：

```text
class(E_A) != class(E_B)
```

要求：

```text
T_CONTRAST_RESULT(E_A) !~ T_CONTRAST_RESULT(E_B)
```

只有：

```text
same class -> reproducible/equivalent treatment contrasts
AND
different class -> distinguishable treatment contrasts
```

同时成立，才允许 C3。

## 20.3 Scale and Interpretation Ceiling

C3 的 canonical 含义是：

```text
CONTENT_CONDITIONED_TREATMENT_CONTRAST_HETEROGENEITY
```

也就是：

> 在 preregistered outcome basis、contrast statistic 与 measurement scale 下，ON/OFF treatment contrast 对 preregistered content class 呈现稳定异质性。

它不证明：

```text
intrinsic content sensitivity independent of measurement scale
representation-independent latent mechanism
all possible confounds are absent
```

OFF arms 在不同 content classes 下可以不同；本 v0.1 不要求一个额外的“OFF arms 必须不可区分”gate。

科学责任是冻结 measurement scale、控制已知 material moderators，并禁止 outcome 后换尺子救 claim。

---

# 21. Discriminator Roles

不得使用一个裸 `D` 吞并不同科学问题。

至少存在：

```text
D_ATTRIBUTION
D_NONSTORAGE_BASELINE
D_CONTENT_CONTRAST
```

每个 role 必须分别冻结：

```text
ROLE_ID
ROLE_VERSION
ROLE_HASH

algorithm_id
algorithm_version
algorithm_hash

INPUT_DOMAIN
comparison_population

threshold / equivalence_rule
indeterminate_region

FAILURE_SEMANTICS
```

其中：

```text
D_ATTRIBUTION
INPUT_DOMAIN = ΔS_identity_masked
```

回答 Basic L1 / C1 scope 的 registered change 是否可归属，并且只在该 scope 下产生 ledger `attribution_result`。它不得产生可供 C2/C3 消费的 nonstorage attribution result。

```text
D_NONSTORAGE_BASELINE
INPUT_DOMAIN = ON/OFF treatment-contrast result under frozen CAUSAL_CONTRAST_RULE
```

回答 paired intervention 是否在 canonical `ΔS_nonstorage` outcome basis 上建立了可归属 nonstorage treatment contrast，并且是 C2/C3 scope ledger `attribution_result` 的 authoritative producer。

职责顺序固定为：

```text
STATE_DELTA_RULE
-> produces canonical ΔS_nonstorage for ON and matched OFF

CAUSAL_CONTRAST_RULE
-> evaluates the preregistered ON/OFF treatment contrast

D_NONSTORAGE_BASELINE
-> evaluates whether that registered contrast establishes C2 evidence
```

不得让该 discriminator 在 raw ON/OFF state、target-only delta 与 registered treatment-contrast result 之间 outcome 后二选一。

```text
D_CONTENT_CONTRAST
INPUT_DOMAIN = T_CONTRAST_RESULT(E) over the frozen CONTENT_CLASS_EVIDENCE_SET
```

回答同一 frozen measurement scale 下 treatment contrast 是否呈现 preregistered content-class heterogeneity。

原则：

```text
same algorithm != same scientific rule
```

---

# 22. Reset Profile and Validity

每个 reset 必须冻结：

```text
RESET_PROFILE_ID
RESET_PROFILE_HASH

RESET_COMPATIBILITY_MANIFEST
RESET_COMPATIBILITY_HASH
```

同一 profile 中不得出现：

```text
CLEAR or PRESERVE
RESTART or NOT
OPTIONAL
AS NEEDED
```

核心原则：

```text
clear input-side traces
preserve substrate under test
```

若 reset 与 implementation 不相容：

```text
RUN MAY NOT START
```

counterfeit arm 在 reset 前必须具有可检测 signal；同时必须验证被声明 PRESERVE 的 registered substrate 没有被 reset 本身摧毁。

只有两项都通过，L2 才可解释。

---

# 23. Reset Rebuilds Evidence; It Does Not Inherit It

reset 前建立的 class、attribution、content structure 不自动继承到 reset 后。

因此：

```text
PRE_RESET_CHANGE_CLASS
```

与：

```text
POST_RESET_SUPPORTED_CLASS
```

是两个不同字段。

规则：

```text
POST_RESET_SUPPORTED_CLASS <= PRE_RESET_CHANGE_CLASS
```

reset 不能证明 reset 前从未建立过的更高 class。

---

# 24. POST_RESET_CLASS_RULE

执行前必须冻结：

```text
POST_RESET_CLASS_RULE_ID
POST_RESET_CLASS_RULE_HASH
```

它机械检查 reset 后证据。

## 24.0 PERSISTENCE_MATCH_RULE — Persistence Identity Closure

执行前已经由 manifest 冻结的：

```text
PERSISTENCE_MATCH_RULE_ID
PERSISTENCE_MATCH_RULE_HASH
```

必须具有可执行内容；只有 ID/hash 而缺少下列 mandatory semantics，按 `PERSISTENCE_MATCH_RULE_MISSING` 处理。

至少必须事前明确：

```text
tracked_object_by_attempted_class
logical_evidence_identity_by_class
realization_metadata_by_class
matching_function_by_class
matching / equivalence / acceptance threshold or region
indeterminate_region
failure_condition
```

不得把该 rule 定义为恒真，也不得把 store container 仍存在、path 仍可寻址、storage subsystem 仍挂载或 object handle 仍可解析，单独定义为 episode-specific storage persistence。

### C1 persistence scope

C1 的 tracked object 是对应 pre-reset write 所建立的 episode-specific registered storage content，以 `episode_identity` 绑定到该次 registered write。

post-reset 必须重新观察对应 episode-specific registered storage content，并由 frozen `PERSISTENCE_MATCH_RULE` 判定是否满足 preregistered persistence criterion。

```text
container survival
!=
episode-specific storage persistence
```

### C2 persistence scope

C2 追踪的不是一个新 state object，也不是一个 outcome 后自由描述的 contrast 数值。它追踪的是同一个 logical paired evidence unit 的 pre/post realizations。

C2 logical evidence identity 固定为：

```text
episode_identity
pair_identity
storage_pipeline_identity
state_delta_rule_hash
causal_contrast_rule_hash
```

其中 `pair_identity` 必须在 outcome exposure 前分配并跨 phase 稳定。

以下字段属于 phase-specific realization metadata，必须分别登记，但允许 pre/post 不同：

```text
phase
baseline_state_id
target_execution_id
matched_off_execution_id
```

若该 C2 evidence unit 并非同时属于 C3 attempt：

```text
content_class_identity = N/A
```

合法且不表示缺失。

post-reset `re-established` 的含义是：同一 logical evidence unit 被重新测量，继续使用同一 frozen `STATE_DELTA_RULE` / `CAUSAL_CONTRAST_RULE` 与 preregistered persistence criterion，并得到满足该 criterion 的 post-reset evidence。

它不要求 pre-reset 与 post-reset `T_CONTRAST_RESULT` 数值完全相等。

### C3 persistence scope

C3 追踪的是 frozen class-structured evidence，而不是单个 storage object 或单个自由 contrast。其 logical identity 至少绑定：

```text
CONTENT_CLASS_EVIDENCE_SET_HASH
CAUSAL_CONTRAST_RULE_HASH
and, for every logical member slot:
  episode_identity
  content_class_identity
  pair_identity
  storage_pipeline_identity
  state_delta_rule_hash
```

`CONTENT_CLASS_EVIDENCE_SET` 的成员是 ignition 前冻结的 logical member slots；phase-specific execution IDs 只是填入这些 slot 的 realizations，不得改变 evidence-set logical identity。

post-reset 必须对这些 logical member slots 各自重新测量 paired contrast，并重新建立 preregistered same-class / cross-class structure。

### Cross-class non-substitution

```text
C1 persistence evidence
MUST NOT satisfy, substitute for, or vote toward
C2 or C3 persistence.

C2 persistence evidence
MUST NOT satisfy, substitute for, or vote toward
C3 persistence.
```

lower-class persistence 只能支持其自身 class。

## 24.1 Post-reset C3

只有当：

1. C3 evidence set 中每个 logical member slot 的 target 与 matched-OFF realization 都跨相同 reset；
2. 每个 member 的 post-reset attribution ledger entry 均为 `ATTRIBUTED`；
3. 每个 member 使用相同 frozen `STATE_DELTA_RULE` 与 `CAUSAL_CONTRAST_RULE`，在 canonical `ΔS_nonstorage` outcome basis 上重新得到 post-reset `T_CONTRAST_RESULT(E)`；
4. `PERSISTENCE_MATCH_RULE` 将 pre/post realization 绑定到同一个 preregistered logical member slot，并判定相应 persistence criterion 成立；
5. same-class treatment-contrast reproducibility 再次 PASS；
6. cross-class treatment-contrast distinguishability 再次 PASS；

才可：

```text
POST_RESET_SUPPORTED_CLASS = C3
```

## 24.2 Post-reset C2

如果 C3 未建立，并且：

1. 完整的 paired post-reset attribution 已建立；
2. post-reset frozen ON/OFF treatment contrast 建立了 event-triggered nonstorage change；
3. `PERSISTENCE_MATCH_RULE` 通过 preregistered logical evidence identity 将该 post-reset realization 绑定到对应 pre-reset C2 evidence unit，并判定 persistence criterion 成立；

才可：

```text
POST_RESET_SUPPORTED_CLASS = C2
```

## 24.3 Post-reset C1

如果 higher-class persistence 未建立或未评估，且 `PERSISTENCE_MATCH_RULE` 对对应 episode-specific registered storage content 给出已建立的 persistence 判定：

```text
POST_RESET_SUPPORTED_CLASS = C1
```

C1 本身不得被解释为“nonstorage 不存在”。

## 24.4 No Positive Post-reset Class

对于实际 attempted post-reset claim，若完成其 required measurements 与 frozen rules 后没有任何 `POST_RESET_SUPPORTED_CLASS` 被建立：

```text
preregistered rule gives a determinate negative result
-> L2 = FAIL

result falls inside the preregistered indeterminate region
-> L2 = UNRESOLVED
```

若 required rule/manifest 缺失、required measurement 未执行、reset invalid 或 rule 在 outcome 后改变，则仍按 §25：

```text
L2 = INVALID
```

未尝试的 higher class 仍记为 `NOT_ASSESSED`；不得把它包装成 FAIL、UNRESOLVED 或 INVALID。

---

# 25. L2 Result Semantics

L2 结果按 `POST_RESET_SUPPORTED_CLASS` 与实际 attempted claim 的证据状态判定。

## L2 = PASS

表示：

> 某个明确的 `POST_RESET_SUPPORTED_CLASS` 已按 frozen rule 建立。

如果 C1 storage persistence 的证据完整，而 C2/C3 persistence 根本未尝试：

```text
L2 = PASS
POST_RESET_SUPPORTED_CLASS = C1
```

仍可合法建立。

authoritative execution record 必须把未尝试的 higher-class evidence 记为：

```text
NOT_ASSESSED
```

这不等于：

```text
C2 FAIL
C3 FAIL
L2 INVALID
```

## L2 = FAIL

仅当：

```text
reset valid
all required rules valid/frozen
required measurements for the tested claim completed
preregistered rule gives a determinate negative result
```

## L2 = UNRESOLVED

仅当：

```text
reset valid
rules valid/frozen
required measurements completed
result falls inside preregistered indeterminate region
```

## L2 INVALID

仅对实际 attempted claim，若：

```text
required measurement for that attempted claim not executed
required manifest/rule for that attempted claim missing
reset invalid
rule changed after outcome
```

则该 attempted claim 的 L2 interpretation 为 INVALID。

未尝试的 higher class 不因 `NOT_ASSESSED` 使已经独立建立的 lower-class L2 PASS 失效。

---

# 26. Persistence Claim Namespace

L2 claim 必须携带 class。

```text
C1 + L2 PASS
-> STORAGE_RESET_PERSISTENCE_OBSERVED
```

```text
C2 + L2 PASS
-> EVENT_TRIGGERED_CHANGE_PERSISTENCE_OBSERVED
```

```text
C3 + L2 PASS
-> CONTENT_CONDITIONED_TREATMENT_CONTRAST_HETEROGENEITY_PERSISTENCE_OBSERVED
```

不得使用一个裸：

```text
RESET_PERSISTENCE_OBSERVED
```

替所有 class 背书。

---

# 27. Counterfeit / Confounder Suite

至少冻结以下 control classes：

```text
N1 prompt/context carryover
N2 KV/cache carryover
N3 unregistered external retrieval
N4 episode reinjection
N5 retrieval-induced write
N6 random drift
N7 pure recency
N8 time/background change
N9 behavior-only counterfeit
N10 representation substitution
```

所有 control 都必须在 outcome exposure 前登记：

```text
CONTROL_ID
GATE_SCOPE
EXPECTED_PRECONDITION
EXPECTED_RESULT
FAILURE_CONSEQUENCE
```

核心原则：

```text
external != unregistered
behavior-looking-memory != registered write
retrieval != write unless explicitly registered
```

---

# 28. Class-Scoped Mandatory Failure Witness

Failure witness 的 scope 必须跟随实际 attempted claim。

必须冻结：

```text
L1_FAILURE_WITNESS_MANIFEST
L1_FAILURE_WITNESS_MANIFEST_HASH
```

同一个 manifest 可以登记不同 claim scope；不得把 higher-class witness 反向施加给 lower-class result。

## 28.1 C1 / Basic L1 Witness

C1 的最小 mandatory failure path 是：

```text
TARGET WRITE ARM
vs
NO-WRITE / MATCHED BASELINE CONTROL
```

它回答：

> attributable registered write/change 是否真的发生？

§13 Basic L1 gate 必须在这一 preregistered witness scope 上调用 frozen `D_ATTRIBUTION`；该调用产生的 `ATTRIBUTED` 只属于 Basic L1 / C1 scope。

它不要求：

```text
same-E ON/OFF nonstorage counterfactual
content-class contrast
```

因此 architecture 即使：

```text
C2 = ARCHITECTURALLY_NOT_IDENTIFIABLE
C3 = ARCHITECTURALLY_NOT_IDENTIFIABLE
```

仍可合法尝试并建立 C1。

## 28.2 Attempted C2 Witness

若要建立 C2，必须具备：

```text
same E
same storage path
W_extra ON/OFF counterfactual
```

若 architecture 本身无法构造该 structure：

```text
C2 = ARCHITECTURALLY_NOT_IDENTIFIABLE
C3 = ARCHITECTURALLY_NOT_IDENTIFIABLE
```

但 C1 result 仍独立可评估。

若 architecture 具备该 path、但本次 execution 没有尝试 higher class：

```text
C2 = NOT_ASSESSED
C3 = NOT_ASSESSED
```

这不是能力天花板，也不是 scientific FAIL。

如果某次 execution 声称已注册 C2-required structure，但该 required structure 实际缺失或 outcome 后改变：

```text
C2 attempt = INVALID
```

不自动抹掉已经独立合法建立的 C1。

若结构完整、实验执行完成，但 scientific condition 未通过：

```text
C2 = NOT_ESTABLISHED
```

不是 INVALID。

## 28.3 Attempted C3 Witness

若要建立 C3，才强制要求：

```text
CONTENT_CLASS_MANIFEST
CONTENT_CLASS_EVIDENCE_SET
same-class treatment-contrast reproducibility structure
cross-class treatment-contrast discriminative structure
per-member paired attribution
preregistered nuisance-moderator disposition
```

如果某次 execution 声称尝试 C3，但 preregistered C3-required witness/structure 缺失或 outcome 后改变：

```text
C3 attempt = INVALID
```

不自动抹掉已经独立合法建立的 C1/C2。

若结构完整、实验执行完成，但 scientific condition 未通过：

```text
C3 = NOT_ESTABLISHED
```

不是 INVALID。

## 28.4 Witness Registration Rule

对实际 attempted class 所需的 failure witness / contrast 若未注册：

```text
REQUIRED_CONTRAST_NOT_REGISTERED_FOR_ATTEMPTED_CLASS
-> that attempted class = INVALID
```

不得把“最高 class 所需 witness”解释为所有 lower classes 的通用启动条件。

failure witness 必须在 outcome exposure 前由独立 reviewer 确认：

```text
reachable
non-tautological
capable of distinguishing the attempted claim
```

## 28.5 Status Vocabulary Must Not Collapse Distinct Facts

以下状态不得互换：

```text
ARCHITECTURALLY_NOT_IDENTIFIABLE
NOT_ASSESSED
NOT_ESTABLISHED
UNRESOLVED
INVALID
```

分别表示：

```text
当前 implementation 下没有可执行 identification path
本次未尝试
已合法尝试但科学条件未建立
已完成但落入 preregistered indeterminate region
协议/执行结构无效
```

不得使用斜杠把不同后果的状态压成一个名字。

---

# 29. Scientific Failure vs Protocol Invalidity

以下是科学结果：

```text
NO_REGISTERED_CHANGE
TARGET_INSEPARABLE_FROM_CONTROL
CAUSAL_CONTRAST_NOT_ESTABLISHED
CONTENT_CONDITIONED_TREATMENT_CONTRAST_HETEROGENEITY_NOT_ESTABLISHED
```

以下是 protocol/execution invalidity：

```text
required rule missing
required scope/evidence manifest missing
rule changed after outcome
observer not independent
reset invalid
provenance break
```

原则：

```text
executed-and-negative != INVALID
missing/changed structure != scientific FAIL
```

---

# 30. Status Coverage Precheck

执行授权前必须运行：

```text
STATUS_RULE_COVERAGE_PRECHECK
```

确认本 protocol 的所有前瞻可达 evidence states 都能被 canonical ledger/result schema 表达。

若失败：

```text
STATUS_RULE_COVERAGE_PRECHECK_FAILED
RUN MAY NOT START
```

不得运行后才发现诚实结果无处登记。

---

# 31. Machine Provenance

机器 provenance 不得保存一个裸：

```text
change_class = C3
```

作为可脱离上下文传播的 authoritative field。

至少记录：

```text
L1_RESULT
PRE_RESET_CHANGE_CLASS

ATTRIBUTION_LEDGER_HASH

CONTENT_CLASS_MANIFEST_HASH
CONTENT_CLASS_EVIDENCE_SET_HASH

STATE_DELTA_RULE_HASH
CAUSAL_CONTRAST_RULE_HASH

D_ATTRIBUTION_ROLE_HASH
D_NONSTORAGE_BASELINE_ROLE_HASH
D_CONTENT_CONTRAST_ROLE_HASH

L2_RESULT
POST_RESET_SUPPORTED_CLASS

RESET_PROFILE_HASH
POST_RESET_CLASS_RULE_HASH
PERSISTENCE_MATCH_RULE_HASH

execution_id
execution_hash
baseline_state_id

base_model_hash
execution_environment_identity
```

必须生成：

```text
RESULT_TUPLE_HASH
```

`RESULT_TUPLE_HASH` 为 normative / required。

---

# 32. Result Citation Discipline

任何正式下游引用至少必须携带：

```text
L1_RESULT
PRE_RESET_CHANGE_CLASS
ATTRIBUTION_LEDGER_HASH

L2_RESULT
POST_RESET_SUPPORTED_CLASS

RESULT_TUPLE_HASH
```

若讨论 C2/C3，还必须能追溯到：

```text
CONTENT_CLASS_EVIDENCE_SET_HASH
CAUSAL_CONTRAST_RULE_HASH
relevant discriminator role hashes
```

其中 `CAUSAL_CONTRAST_RULE_HASH` 同时是该 C2/C3 claim 的 normative measurement-scale / contrast-definition identifier。

因此 C3 的引用不得脱离这个 hash 单独传播；否则会把 scale-conditional claim 伪装成 scale-independent claim。

不得从 ledger 中只摘：

```text
ATTRIBUTED
```

再从另一个字段摘：

```text
PERSISTENCE
```

拼成一条从未被实验整体建立过的 claim。

尤其禁止把 lower-class persistence result 与 higher-class 的 `NOT_ASSESSED`、`NOT_ESTABLISHED` 或其他字段拆开后重新拼接成 higher-class persistence claim。

```text
C1 persistence evidence MUST NOT be cited as C2/C3 persistence evidence.
C2 persistence evidence MUST NOT be cited as C3 persistence evidence.
```

---

# 33. Write / Persistence / Recall / Identity Separation

必须保持：

```text
WRITE / PERSISTENCE != RECALL / ARBITRATION
```

Afterglow / PWL 当前负责：

```text
leave and characterize registered change
```

Temporal Arbitration 负责：

```text
decide when / which past information or state to access
```

长期接口：

```text
DEFERRED UNTIL RECALL INTEGRATION
```

即使取得：

```text
CONTENT_CONDITIONED_TREATMENT_CONTRAST_HETEROGENEITY_PERSISTENCE_OBSERVED
```

仍然：

```text
CONTENT-CONDITIONED TREATMENT-CONTRAST HETEROGENEITY != IDENTITY CONTINUITY
```

C3 证明的是：

> 在冻结的 measurement scale 下，不同 preregistered content classes 对应不同的 ON/OFF treatment-contrast results。

它没有证明：

> 这些 contrast differences 属于同一条持续的“我”的轨迹。

因此：

```text
IDENTITY_CONTINUITY = NOT ESTABLISHED
```

继续保留。

---

# 34. DHE and Historical Boundaries

允许从 DHE 继承：

```text
methodological guards
engineering guards
causal probing techniques
negative-control ideas
known confounders
failure discipline
```

禁止继承为 Afterglow gate：

```text
d_M numerical value
12G polarity
12H polarity
shore-sign pattern
DHE-specific success/failure criterion
```

原则：

```text
Technical reuse != Criterion reuse
```

当前合法工程禁令：

```text
reconstruction similarity
MUST NOT serve as unqualified retention proxy
```

以及：

```text
representation similarity != arbitrability
```

不得升级成：

```text
compression is harmful
```

---

# 35. Historical M-Bias Status

2026-05-02 的：

```text
Memory Afterglow Layer Experiment
M-Bias Attention Injection
```

登记为：

```text
HISTORICAL_MECHANISM_CANDIDATE
```

scientific role：

```text
PERSISTENT_SALIENCE_BASELINE
ATTENTION_BIAS_BASELINE
CONTINUITY_LOOKING_BEHAVIOR_BASELINE
```

它不是：

```text
current Afterglow ontology
episode-induced write evidence
MEMORY_QUALIFIED mechanism
```

旧 success criteria 不得自动成为当前 gate。

---

# 36. Current Claim Ceiling

即使本 MVP 的最高 evidence class 和 reset persistence 都成功，当前仍不得声明：

```text
memory formed             = NOT ESTABLISHED
memory ontology           = NOT ESTABLISHED
persistent memory         = NOT ESTABLISHED
long-term retention       = NOT ENTERED
interference resistance   = NOT ENTERED
forgetting mechanism      = NOT ENTERED
identity continuity       = NOT ESTABLISHED
self-modification         = NOT ESTABLISHED
MEMORY_QUALIFIED          = NOT CLAIMED
```

合法最高表述：

C1：

> A preregistered episode produced an attributable registered storage write.

C2：

> Under the frozen `CAUSAL_CONTRAST_RULE`, a preregistered episode produced an attributable nonstorage ON/OFF treatment contrast beyond the same-episode literal-storage counterfactual.

C3：

> Under the frozen `CAUSAL_CONTRAST_RULE`, different preregistered episode-content classes showed reproducibly different attributable ON/OFF treatment contrasts on the canonical `ΔS_nonstorage` outcome basis.

C3 的正式规范名为：

```text
CONTENT_CONDITIONED_TREATMENT_CONTRAST_HETEROGENEITY
```

必须同时承认：

> This is a measurement-scale / outcome-representation conditional claim, not representation-independent proof of intrinsic content sensitivity.

若对应 post-reset class 被重新建立，只可增加：

> the corresponding evidence class was re-established after the valid registered reset.

---

# 37. Master Stop Conditions

至少包括：

```text
SYSTEM_BOUNDARY_CHANGED_AFTER_OUTCOME

STATE_FIELDS_CHANGED_AFTER_OUTCOME
IDENTITY_ONLY_COMPONENTS_CHANGED_AFTER_OUTCOME
LITERAL_STORAGE_COMPONENTS_CHANGED_AFTER_OUTCOME
STORAGE_PIPELINE_NUISANCE_COMPONENTS_CHANGED_AFTER_OUTCOME

STATE_DELTA_RULE_MISSING
STATE_DELTA_RULE_CHANGED_AFTER_OUTCOME

CAUSAL_CONTRAST_RULE_MISSING
CAUSAL_CONTRAST_RULE_CHANGED_AFTER_OUTCOME

CONTENT_CLASS_MANIFEST_MISSING
CONTENT_CLASS_MANIFEST_CHANGED_AFTER_OUTCOME

CONTENT_CLASS_EVIDENCE_SET_MISSING
CONTENT_CLASS_EVIDENCE_SET_CHANGED_AFTER_OUTCOME
KNOWN_MATERIAL_MODERATOR_WITHOUT_PREREGISTERED_DISPOSITION
POST_OUTCOME_NUISANCE_ADJUSTMENT_USED_TO_RESCUE_C3

ATTRIBUTION_LEDGER_SCHEMA_MISSING
ATTRIBUTION_LEDGER_SCHEMA_CHANGED_AFTER_OUTCOME
ATTRIBUTION_SCOPE_MISSING
ATTRIBUTION_SCOPE_CHANGED_AFTER_OUTCOME

DISCRIMINATION_RULESET_MISSING
DISCRIMINATION_RULESET_CHANGED_AFTER_OUTCOME

RESET_COMPATIBILITY_NOT_ESTABLISHED
RESET_PROFILE_CHANGED_AFTER_OUTCOME

POST_RESET_CLASS_RULE_MISSING
POST_RESET_CLASS_RULE_CHANGED_AFTER_OUTCOME

PERSISTENCE_MATCH_RULE_MISSING
PERSISTENCE_MATCH_RULE_CHANGED_AFTER_OUTCOME

L1_FAILURE_WITNESS_MANIFEST_MISSING
FAILURE_WITNESS_NOT_PREVALIDATED
REQUIRED_CONTRAST_NOT_REGISTERED_FOR_ATTEMPTED_CLASS

DIGEST_SELF_REFERENCE
STATE_OBSERVER_NOT_INDEPENDENT

UNREGISTERED_EPISODE_REINJECTION
UNREGISTERED_RETRIEVAL_INDUCED_WRITE

BASE_MODEL_HASH_MISMATCH
PROVENANCE_BREAK
EXECUTION_IDENTITY_MISMATCH

PROVENANCE_RESULT_TUPLE_INCOMPLETE
PROVENANCE_USES_UNPHASED_CHANGE_CLASS
```

按对应 scope 判：

```text
INVALID
```

注意：

```text
C3 evidence member executed but attribution != ATTRIBUTED
```

不是 stop condition。

它是：

```text
C3 NOT ESTABLISHED
```

并继续独立评估 C2。

---

# 38. Explicitly Deferred

本 v0.1 不决定：

```text
PWL architecture
parameter plasticity
adapter design
rank
loss
optimizer
learning rate

memory capacity
forgetting schedule
retention time scale
interference mechanism

importance weighting
emotional weighting
identity weighting

identity lineage mechanism
```

这些属于：

```text
IMPLEMENTATION / LATER CHARACTERIZATION / FUTURE QUALIFICATION
```

但：

```text
deferred != blank at execution time
```

实际 execution 所需字段必须在点火前冻结。

---

# 39. Frozen Methodological Sentences

> **First prove what changed.**

> **Then separate storage from the registered ON/OFF treatment contrast.**

> **Then compare preregistered treatment contrasts, not raw state or target-only deltas.**

> **Then ask whether the frozen treatment contrast differs by preregistered content class.**

> **After reset, rebuild the evidence; do not inherit the label.**

> **Only later ask whether any surviving structure deserves to be called memory.**

以及：

> **A system may remember by transforming, storing, restructuring, or by a mechanism we have not yet imagined. Ontology neutrality forbids us from choosing the winner before the evidence.**

> **Storing an episode is not evidence that anything beyond storage occurred.**

> **An event-triggered treatment contrast is not yet evidence of content-conditioned treatment-contrast heterogeneity.**

> **Different content classes showing different treatment contrasts is not yet evidence that those differences belong to the same continuing self.**

> **Not assessed is not not detected.**

> **Not detected is not unresolved.**

> **Unresolved is not invalid.**

> **Scientific failure is not protocol invalidity.**

> **Complexity itself can create error.**

> **If deleting one summary field solves the problem, do not add two more.**

> **A gate that cannot fail us is not a gate.**

---

# 40. Canonical Bytes and Final Review Procedure

本节属于 document-control procedure，不属于 scientific gate。

canonical file byte form 固定为：

```text
ENCODING = UTF-8
BOM = NONE
LINE_ENDING = LF
FINAL_NEWLINE = EXACTLY_ONE
HASH_ALGORITHM = SHA-256
HASH_INPUT = exact canonical file bytes
RENDERED_TEXT = NOT HASH INPUT
```

发布时必须同时给出：

```text
CANONICAL_BYTE_COUNT
CANONICAL_SHA256
```

byte count 是廉价第二校验，不替代 SHA-256。

final reviewer 必须：

1. 实际取得 canonical file bytes；
2. 自行计算 byte count；
3. 自行计算 SHA-256；
4. 与发布值逐项比较；
5. 只有一致才可声明：

```text
HASH_STATUS = INDEPENDENTLY_VERIFIED
REVIEWED_DOCUMENT_HASH = ...
BLOCKING = 0
```

若 reviewer 只能看到 rendered / inline text：

```text
HASH_STATUS = ATTESTED_ONLY
```

不得完成 byte-level final sign-off。

若：

```text
local_hash != declared_hash
```

则：

```text
HASH_STATUS = MISMATCH
REVIEW = INVALID
FREEZE = STOP
```

final blocking review 必须基于完整 canonical full text，而非 delta 摘要。

如果任何 final reviewer 审阅后正文发生 substantive change：

```text
NEW CANONICAL HASH REQUIRED
FINAL BLOCKING REVIEW RESTARTS
```

---

# 41. Freeze-Candidate Closing Principle

本 prereg 不负责定义“真正的记忆是什么”。

它只负责确保：

> **我们不能把 storage 叫成 transformation；  
> 不能把 raw state 或 target-only delta 叫成 registered treatment contrast；  
> 不能把 scale-conditional treatment-contrast heterogeneity 叫成 representation-independent intrinsic content sensitivity；  
> 不能把 reset 前的荣耀继承给 reset 后；  
> 不能把没测写成没有；  
> 不能把测不出来写成没发生；  
> 也不能因为我们很想找到记忆，就把证据说得比它实际更远。**

---

**AFTERGLOW MVP PREREGISTRATION v0.1**  
**STATUS = FREEZE-CANDIDATE / NOT FROZEN / NOT AUTHORIZED FOR EXECUTION**
