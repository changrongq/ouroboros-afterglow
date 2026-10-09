# AFTERGLOW MVP PREREGISTRATION v0.1

## Ouroboros Project · 千年舟

**Status:** FREEZE-CANDIDATE / NOT FROZEN / NOT AUTHORIZED FOR EXECUTION  
**Purpose:** Preregistration for the first implementation-neutral Afterglow MVP  
**Scope:** attributable registered change, change classification, causal-effect identification, and reset persistence  
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
2. 这次改变中，哪些只是 storage，哪些是 storage 之外可归属于 target mechanism 的 causal effect？
3. 不同 episode content classes 是否稳定地产生不同的 causal-effect shapes？
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
3. **content-conditioned claim 必须比较 causal effect，而不是 raw state。**
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

causal_effect_rule_id
causal_effect_rule_hash

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

---

# 10. CAUSAL_EFFECT_RULE

C3 不比较 raw `ΔS_nonstorage`。

必须比较 paired causal effect。

执行前必须冻结：

```text
CAUSAL_EFFECT_RULE_ID
CAUSAL_EFFECT_RULE_HASH
```

该 rule 的输入至少为：

```text
ΔS_nonstorage(target_ON)
ΔS_nonstorage(matched_OFF)
```

输出：

```text
CAUSAL_EFFECT(E)
```

抽象记为：

```text
Δ_causal(E)
=
Effect(
  ΔS_nonstorage(target_ON, E),
  ΔS_nonstorage(matched_OFF, E)
)
```

`Effect` 不预设是向量减法。

`CAUSAL_EFFECT_RULE` 必须在 outcome exposure 前明确：

```text
input representation
pair alignment rule
shared-component handling
difference/equivalence semantics
output representation
indeterminate behavior
failure behavior
```

尤其必须声明：

> **ON/OFF 两臂共享成分如何被处理。**

若这一点未冻结：

```text
RUN MAY NOT START
```

不得 outcome 后选择一种更有利的 Effect 运算。

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

> 在 same-E / same-storage-path counterfactual 之外，存在可归属于 target additional mechanism 的 nonstorage causal effect；但尚未证明该 causal effect 的形状被 episode content class 稳定塑形。

最强允许 claim：

```text
EVENT_TRIGGERED_NONSPECIFIC_CHANGE_OBSERVED
```

## C3 — CONTENT_CONDITIONED_TRANSFORMATION

C3 表示：

> 不同 preregistered episode-content classes 产生可复现、可区分、且逐成员可归因的 causal-effect shapes。

最强允许 claim：

```text
CONTENT_CONDITIONED_TRANSFORMATION_OBSERVED
```

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
target additional transformation mechanism
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
NONSTORAGE_CAUSAL_ATTRIBUTION = NOT IDENTIFIABLE
```

它仍可建立 C1，但 C2/C3 不可由该 execution 建立。

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
causal_effect_rule_hash

D_NONSTORAGE_BASELINE_ROLE_HASH

reset_profile_id
reset_profile_hash

attribution_result
```

`attribution_result` 至少允许表达：

```text
ATTRIBUTED
DETECTED_UNATTRIBUTED
NOT_ASSESSED
N/A
```

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
causal effect detected
AND
attribution_result = ATTRIBUTED
```

才可建立 C2。

若 required structure 缺失或 outcome 后改动：

```text
relevant result INVALID
```

若结构完整、实验已执行，但 causal attribution 失败：

```text
C2 NOT ESTABLISHED
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
matching / balancing rules

baseline substrate identity

class-definition timestamp
reviewer identity
```

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

的所有 episode / execution members。

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
attribution(e) = ATTRIBUTED
```

之后该 member 的：

```text
Δ_causal(e)
```

才有资格进入 C3 class comparison。

不能只给一条 episode 做 causal attribution，再让其他未归因 episode 参与 C3。

若某个 member 已登记、实验已执行，但 attribution 不是 `ATTRIBUTED`：

```text
C3 NOT ESTABLISHED
```

然后独立评估 C2。

这不是 protocol INVALID。

若 scope/evidence manifest 缺失或 outcome 后改变：

```text
relevant result INVALID
```

---

# 20. C3 Compares Causal Effects, Not Raw State

C3 的比较对象统一为：

```text
Δ_causal(E)
```

不是：

```text
raw state
ΔS_registered
ΔS_identity_masked
ΔS_nonstorage(target only)
```

## 20.1 Same-class reproducibility

选择：

```text
different episodes
same preregistered content class
```

要求：

```text
Δ_causal(E_A1) ~ Δ_causal(E_A2)
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
Δ_causal(E_A) !~ Δ_causal(E_B)
```

只有：

```text
same class -> reproducible/equivalent causal effects
AND
different class -> distinguishable causal effects
```

同时成立，才允许 C3。

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

回答 registered change 是否可归属。

```text
D_NONSTORAGE_BASELINE
INPUT_DOMAIN = paired causal-effect construction inputs / result
```

回答 target additional mechanism 是否产生可归属 nonstorage effect。

```text
D_CONTENT_CONTRAST
INPUT_DOMAIN = Δ_causal(E)
```

回答 causal-effect shapes 是否 content-conditioned。

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

## 24.1 Post-reset C3

只有当：

1. C3 evidence set 中每个 member 的 target 与 matched-OFF arm 都跨相同 reset；
2. 每个 member 的 post-reset attribution ledger entry 均为 `ATTRIBUTED`；
3. 使用同一个 frozen `CAUSAL_EFFECT_RULE` 重新得到 post-reset `Δ_causal(E)`；
4. same-class reproducibility 再次 PASS；
5. cross-class distinguishability 再次 PASS；

才可：

```text
POST_RESET_SUPPORTED_CLASS = C3
```

## 24.2 Post-reset C2

如果 C3 未建立，但完整的 paired post-reset causal attribution 建立了 event-triggered nonstorage causal effect：

```text
POST_RESET_SUPPORTED_CLASS = C2
```

## 24.3 Post-reset C1

如果 higher-class persistence 未建立或未评估，但 registered storage persistence 已建立：

```text
POST_RESET_SUPPORTED_CLASS = C1
```

C1 本身不得被解释为“nonstorage 不存在”。

---

# 25. L2 Result Semantics

## L2 = PASS

表示：

> 某个明确的 `POST_RESET_SUPPORTED_CLASS` 已按 frozen rule 建立。

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

若：

```text
required measurement for the attempted claim not executed
required manifest/rule missing
reset invalid
rule changed after outcome
```

如果 C1 storage persistence 的证据完整，而 C2/C3 根本未尝试：

```text
POST_RESET_SUPPORTED_CLASS = C1
```

仍可合法建立。

这不等于 C2/C3 FAIL。

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
-> CONTENT_CONDITIONED_TRANSFORMATION_PERSISTENCE_OBSERVED
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

# 28. Mandatory Failure Witness

L1 必须具有明确失败路径。

必须冻结：

```text
L1_FAILURE_WITNESS_MANIFEST
L1_FAILURE_WITNESS_MANIFEST_HASH
```

若 required contrast 未注册：

```text
CONTRAST_NOT_REGISTERED
RUN INVALID
```

failure witness 必须在 outcome exposure 前由独立 reviewer 确认：

```text
reachable
non-tautological
capable of distinguishing tested paths
```

---

# 29. Scientific Failure vs Protocol Invalidity

以下是科学结果：

```text
NO_REGISTERED_CHANGE
TARGET_INSEPARABLE_FROM_CONTROL
CAUSAL_EFFECT_NOT_ESTABLISHED
CONTENT_CONDITIONING_NOT_ESTABLISHED
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
CAUSAL_EFFECT_RULE_HASH

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
CAUSAL_EFFECT_RULE_HASH
relevant discriminator role hashes
```

不得从 ledger 中只摘：

```text
ATTRIBUTED
```

再从另一个字段摘：

```text
PERSISTENCE
```

拼成一条从未被实验整体建立过的 claim。

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
CONTENT_CONDITIONED_TRANSFORMATION_PERSISTENCE_OBSERVED
```

仍然：

```text
CONTENT-CONDITIONED TRANSFORMATION != IDENTITY CONTINUITY
```

C3 证明的是：

> 不同经历留下不同的 causal-effect shapes。

它没有证明：

> 这些不同形状属于同一条持续的“我”的轨迹。

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

> A preregistered episode produced an attributable nonstorage causal effect beyond the same-episode literal-storage counterfactual.

C3：

> Different preregistered episode-content classes produced reproducibly different attributable causal-effect shapes.

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

CAUSAL_EFFECT_RULE_MISSING
CAUSAL_EFFECT_RULE_CHANGED_AFTER_OUTCOME

CONTENT_CLASS_MANIFEST_MISSING
CONTENT_CLASS_MANIFEST_CHANGED_AFTER_OUTCOME

CONTENT_CLASS_EVIDENCE_SET_MISSING
CONTENT_CLASS_EVIDENCE_SET_CHANGED_AFTER_OUTCOME

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
CONTRAST_NOT_REGISTERED

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

> **Then separate storage from additional causal effect.**

> **Then compare causal effects, not raw state.**

> **Then ask whether the content of the experience shaped those effects.**

> **After reset, rebuild the evidence; do not inherit the label.**

> **Only later ask whether any surviving structure deserves to be called memory.**

以及：

> **A system may remember by transforming, storing, restructuring, or by a mechanism we have not yet imagined. Ontology neutrality forbids us from choosing the winner before the evidence.**

> **Storing an episode is not evidence that anything beyond storage occurred.**

> **An event-triggered change is not yet evidence that event content shaped the change.**

> **Different experiences leaving different causal-effect shapes is not yet evidence that those shapes belong to the same continuing self.**

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
> 不能把 raw difference 叫成 causal effect；  
> 不能把 content-correlated residue 叫成 content-conditioned transformation；  
> 不能把 reset 前的荣耀继承给 reset 后；  
> 不能把没测写成没有；  
> 不能把测不出来写成没发生；  
> 也不能因为我们很想找到记忆，就把证据说得比它实际更远。**

---

**AFTERGLOW MVP PREREGISTRATION v0.1**  
**STATUS = FREEZE-CANDIDATE / NOT FROZEN / NOT AUTHORIZED FOR EXECUTION**