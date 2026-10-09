# AFTERGLOW REFERENCE HARNESS / IMPLEMENTATION BINDING SPECIFICATION v0.1

## Ouroboros Project · 千年舟

```text
DOCUMENT_IDENTITY =
AFTERGLOW REFERENCE HARNESS / IMPLEMENTATION BINDING SPECIFICATION

STATUS = DRAFT SPEC
EXECUTION_AUTHORIZATION = NONE
IGNITION = PROHIBITED
SCIENTIFIC_CLAIM_ELIGIBILITY = NONE
```

**本文件不是、也不得被误认为实际 Implementation Binding。**

```text
本文件身份 = 图纸 / 执行框架 / known-answer qualification spec
本文件【不是】= 某一艘真船的施工登记表

真正的 IMPLEMENTATION_BINDING_MANIFEST
必须等实际 implementation 选出、所有 execution-critical 字段实例化之后
才由 Coder 产生，并明确挂在其所绑定的 SPEC hash 之下。
```

因此：

```text
本 SPEC 层允许冻结（在 closure review 通过后）。
IMPLEMENTATION_BINDING_MANIFEST 层在下一阶段产生，且不得预先冻结。
```

```text
PARENT_PREREG =
AFTERGLOW MVP PREREGISTRATION v0.1

PARENT_PREREG_SHA256 =
ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
```

```text
REVIEW HISTORY
v0.1 (initial draft)              BLOCKING = 1
  blocker: Reference Harness known-answer suite 未覆盖 L2（reset persistence）

v0.1 (L2 known-answer patch)      BLOCKING = 0 (subject to implementation review)
  closure: §15 补 V5a-e（L2 PASS/FAIL/UNRESOLVED/INVALID）+ V4b（ARCHITECTURALLY_NOT_IDENTIFIABLE）
           §15 修 V2（显式 MATCHED_OFF arm）+ V3（每 class >= 2 different episodes）
           §16 补 KNOWN_ANSWER_COVERAGE_INCOMPLETE gate

v0.1 (friend-review patch)        BLOCKING = 0 (subject to arch / false-PASS review)
  #1 §16 circular dependency      -> 两阶段 execution namespace（PHASE A / PHASE B）
  #2 Basic L1 no-write control    -> 三臂（A/B/C）+ 两条分离 pairwise contrast
  #3 known-answer oracle scale    -> §15.0 fixture requirement + V2/V3 唯一 expected oracle

v0.1 (jie-review patch)           BLOCKING = 0 (subject to final byte-level sign-off)
  BD-44 §16.3 L1=UNRESOLVED 缺 fixture -> §15 补 V0b PRE_RESET_INDETERMINATE + 修 V4b 覆盖声明
  BD-40 suite 不绑 binding 版本        -> §16.2.1 KNOWN_ANSWER_SUITE_BINDING_HASH
  BD-41 记账隔离 != 眼睛隔离           -> §16.1.1 Substrate Isolation
  BD-43 canonical bytes 不合规范       -> 全文重新发布为 UTF-8/no-BOM/LF/单尾换行 规范形式
  观察  ① 编号乱序                   -> V6 重命名为 V4b
        ② V0 只有 A 臂                -> 明写 A 即 attempted write arm
        ③ W_extra OFF 未定义           -> §6 固定 OFF = NOT INVOKED
        ④ V1 未写 L1=PASS              -> §15 V1 补 L1 = PASS

v0.1 (jie-BD45 patch)             BLOCKING = 0 (subject to final byte-level sign-off)
  BD-45 V0 的 B 违反 §3.1 arm 定义（应为 W_storage ON，而非 OFF）
        -> §15 V0 改为：B 仍为 §3.1 定义的 B，但 storage operation 预注册为 NULL/no-op
           （保留"无有效写入 ⇒ L1 FAIL"意图，且不改 §3.1）
  观察  ② coverage 矩阵              -> §15.9 Coverage Matrix（profile × canonical exit）
  观察  ① 五类段截断              -> 复核 canonical bytes，该段完整（渲染截断，非文件截断）

v0.1 (lingyi-closure patch)       BLOCKING = 0 (subject to closure review by Coder/钳星/睫)
  文件身份  本文件 = REFERENCE HARNESS / IMPLEMENTATION BINDING SPECIFICATION
            （图纸/框架/spec），不是实际 IMPLEMENTATION_BINDING_MANIFEST
            -> 抬头补 DOCUMENT_IDENTITY；MANIFEST 层下一阶段产生，不预先冻结
  BD-46 L2 C1 PASS path 无 fixture  -> §15 补 V5f RESET_VALID_PERSIST_C1
  BD-47 NOT_ASSESSED 无唯一 oracle  -> §15 V1/V5f 补 NOT_ASSESSED oracle + 覆盖声明收紧
  BD-48 V4 "至少一种" 未唯一冻结    -> §15 V4 改为 fixture family（每实例一个 exact defect）
  BD-40 封口（时间方向）           -> §16.2.2 qualifying suite 必须在 frozen binding hash 之后跑

v0.1 (BD49-BD50 patch)            BLOCKING = 0 (subject to ONE diff-scoped closure review)
  BD-49 V2 的 C3=NOT_ESTABLISHED 不可自推（单 episode 无 class，实为未 attempt）
        -> §15 V2 改为【完整 C3 attempt】：>=2 classes / >=2 episodes per class /
           member attributions valid / same-class reproducibility PASS /
           cross-class distinguishability determinately FAIL ⇒ C3 = NOT_ESTABLISHED
  BD-50 SPEC/MANIFEST 分家后 IMPLEMENTATION_BINDING_HASH 语义未定
        -> §16.2.1 IMPLEMENTATION_BINDING_HASH := IMPLEMENTATION_BINDING_MANIFEST_HASH；
           REFERENCE_HARNESS_SPEC_HASH 单独记、不得替代；
           qualifying suite 记 SPEC_HASH + MANIFEST_HASH；MANIFEST 反向引用 SPEC_HASH；
           任一实质变更 ⇒ 旧 PASS 作废
  STOP RULE（凌翼）: 本轮后只做 ONE diff-scoped closure review；
        BLOCKING=0 即冻 SPEC v0.1；真 false-pass 不得冻入；非阻塞项下移

v0.1 = FROZEN                       BLOCKING = 0
  冻结的 canonical bytes / SHA256 / 核验署名
  记载于冻结记录（不在本文件内自引，避免写注即改 hash）：
  REFERENCE_HARNESS_SPEC_v0.1_FROZEN_20261008.md

  边界: 不重开 frozen prereg / 不新增 scientific gate / 不进入 memory ontology
```

---

# 0. Purpose

本 Implementation Binding 的第一目标不是证明 memory。

也不是寻找最优的长期记忆机制。

第一目标是：

> 建立一个能够忠实执行 frozen Afterglow preregistration 的 reference implementation，使 C1 / C2 / C3 / L2、科学失败与 protocol invalidity 都能够被机器机械地区分。

本版本首先服务于：

```text
REFERENCE HARNESS
PROTOCOL VALIDATION
KNOWN-ANSWER TESTS
```

之后才允许进入：

```text
AFTERGLOW SCIENTIFIC CANDIDATE RUN
```

---

# 1. System Architecture

reference system 由三个主要计算部分组成：

```text
FROZEN_BASE_MODEL
LITERAL_STORE
AFTERGLOW_SUBSTRATE
```

另设独立：

```text
STATE_OBSERVER
PROVENANCE_RECORDER
EXPERIMENT_CONTROLLER
```

## 1.1 Frozen Base Model

```text
BASE_MODEL_WEIGHTS = FROZEN
BASE_MODEL_HASH = TO_BIND_BEFORE_IGNITION
```

任何 scientific execution 中：

```text
BASE_MODEL_HASH_MISMATCH
→ RUN INVALID
```

Afterglow v0.1 不允许通过修改 base-model weights 解释实验结果。

这只是本次实验的控制变量，不构成关于未来 memory mechanism 的本体论声明。

---

# 2. Registered System Boundary

`SYSTEM_BOUNDARY_MANIFEST` 至少包含：

```text
FROZEN_BASE_MODEL
LITERAL_STORE
AFTERGLOW_SUBSTRATE
REGISTERED_READ_PATH
REGISTERED_WRITE_PATH
```

以下属于系统外部实验基础设施：

```text
STATE_OBSERVER
PROVENANCE_RECORDER
EXPERIMENT_CONTROLLER
ANALYSIS_OUTPUT
```

它们不得向 registered substrate 注入未经注册的 state。

---

# 3. Literal Store

定义：

```text
LITERAL_STORE
```

只承担 episode 的 registered literal storage。

它保存：

```text
episode_identity
canonical episode payload
registered serialization
```

这些 episode payload 属于：

```text
LITERAL_STORAGE_COMPONENTS
```

Literal Store 的作用是让：

```text
W_storage(E)
```

在需要它相同的两臂中完全相同。

## 3.1 Three Arm Configurations

reference system 使用三个 arm configuration，全部从 matched registered baseline `S0` 分叉：

```text
A = NO_WRITE_CONTROL
    W_storage OFF
    W_extra   OFF

B = WRITE_ONLY / MATCHED_OFF
    W_storage ON
    W_extra   OFF

C = TARGET_ON
    W_storage ON
    W_extra   ON
```

三者必须满足：

```text
same registered baseline S0
same episode identity E
same registered storage path where storage is ON
```

## 3.2 Two Separate Pairwise Contrasts

科学关系固定为两条【分离】的 pairwise contrast：

```text
Basic L1 / C1:
    B vs A
    → D_ATTRIBUTION
    → ΔS_identity_masked

C2 / C3:
    C vs B
    → canonical ΔS_nonstorage
    → CAUSAL_CONTRAST_RULE
    → D_NONSTORAGE_BASELINE
```

因此：

```text
B vs A  回答：是否有 attributable registered write/change
C vs B  回答：在相同 storage pipeline 之外，是否有额外可归因 nonstorage change
```

冻结：

```text
不得构造一个混合的 A/B/C 三方 attribution。

Basic-L1/C1-scope ATTRIBUTED
MUST NOT satisfy C2/C3 attribution.
```

---

# 4. Afterglow Substrate

定义独立 persistent substrate：

```text
AFTERGLOW_SUBSTRATE
```

它：

1. 位于 preregistered system boundary 内；
2. 具有稳定 identity；
3. 能够被 Independent State Observer 单独读取；
4. 参与未来系统计算；
5. 不等同于 Literal Store；
6. 不包含纯 provenance / audit / timestamp metadata。

具体 substrate representation：

```text
TO_BIND_BEFORE_IGNITION
```

第一版优先选择：

```text
simple
deterministic
fully serializable
fully inspectable
```

而不是高复杂度、高自由度的 adaptive architecture。

---

# 5. Registered Read Path

为了使 `AFTERGLOW_SUBSTRATE` 真正属于 system state，而不是死日志，其内容必须实际参与未来计算。

定义：

```text
REGISTERED_READ_PATH:
AFTERGLOW_SUBSTRATE
→ fixed deterministic reader
→ future system computation
```

reader 本身：

```text
READ_OPERATOR_ID      = TO_BIND
READ_OPERATOR_VERSION = TO_BIND
READ_OPERATOR_HASH    = TO_BIND
```

该 read path 在 outcome exposure 后不得修改。

---

# 6. Write Operator

完整 write operator：

```text
W(E) =
W_storage(E)
+
W_extra(E)
```

其中：

```text
W_storage(E)
```

负责 literal episode storage。

而：

```text
W_extra(E)
```

是 Afterglow candidate transformation。

## W_extra OFF semantics

`W_extra(E) = OFF` 的 binding 层定义必须是：

```text
W_extra NOT INVOKED
```

而不是：

```text
W_extra invoked but identity transform
```

理由：若 OFF 是"调用但恒等"，则 W_extra 的 allocation / append / bookkeeping
副作用仍会进入 registered state，污染 ON/OFF contrast。

因此：

```text
OFF arm 不得为 W_extra 分配、追加或记账任何 registered state
```

（§15 V2/V3 fixture 在 fixture 层写 `OFF = 0`；本节把同一语义固定到 binding 层。）

## Arm C — TARGET_ON

```text
W_storage(E) = ON
W_extra(E)   = ON
```

## Arm B — WRITE_ONLY / MATCHED_OFF

```text
W_storage(E) = ON
W_extra(E)   = OFF  (NOT INVOKED)
```

## Arm A — NO_WRITE_CONTROL

```text
W_storage(E) = OFF
W_extra(E)   = OFF  (NOT INVOKED)
```

因此：

```text
C vs B 唯一允许的 intentional difference = W_extra intervention
B vs A 唯一允许的 intentional difference = W_storage intervention
```

不得把 C vs B 与 B vs A 混合成一个三方 attribution（见 §3.2）。

具体 `W_extra` scientific candidate：

```text
DEFERRED UNTIL REFERENCE HARNESS VALIDATION PASSES
```

reference validation 阶段可以使用 deterministic synthetic implementations，但这些结果不得被描述为 memory evidence。

---

# 7. State Schema

registered state 必须严格分成：

```text
STATE_FIELDS
META_FIELDS
VOLATILE_FIELDS
```

## STATE_FIELDS

至少包含：

```text
LITERAL_STORE_STATE
AFTERGLOW_SUBSTRATE_STATE
```

## META_FIELDS

至少包括：

```text
timestamp
execution_id
episode_identity
pair_identity
audit records
before_state_digest
after_state_digest
provenance digest
```

META_FIELDS 不进入 registered substrate state digest。

## VOLATILE_FIELDS

例如：

```text
runtime cache
temporary activation buffers
temporary process state
```

必须和 persistent registered substrate 分离。

---

# 8. State Observer

Independent State Observer 必须是独立于 write operator 的只读组件。

```text
observer != write operator
observer cannot write registered substrate
observer independently reads STATE_FIELDS
observer independently computes state identities
```

实现建议：

```text
separate read-only process/module
```

STATE_OBSERVER 的：

```text
identity
version
hash
```

必须在 ignition 前冻结。

---

# 9. Storage / Identity / Nuisance Masks

必须预先登记：

```text
IDENTITY_ONLY_COMPONENTS
LITERAL_STORAGE_COMPONENTS
STORAGE_PIPELINE_NUISANCE_COMPONENTS
```

第一版 nuisance 至少检查：

```text
byte count
serialized length
append pointer
allocation metadata
checksums
storage acknowledgement fields
storage-path counters
bookkeeping state
```

不得在 outcome 后新增 nuisance mask 来救结果。

---

# 10. STATE_DELTA_RULE

必须从 observer 取得的 registered states 机械产生：

```text
ΔS_registered
ΔS_identity_masked
ΔS_nonstorage
```

其中：

```text
ΔS_nonstorage
=
registered state change
after masking:

IDENTITY_ONLY_COMPONENTS
+
LITERAL_STORAGE_COMPONENTS
+
STORAGE_PIPELINE_NUISANCE_COMPONENTS
```

C2 / C3 的唯一 canonical outcome basis：

```text
ΔS_nonstorage
```

Reference Harness 禁止提供 alternative projection selector。

---

# 11. Causal Contrast

C2/C3 与 Basic L1 使用两条互不混合的 pairwise contrast。

## 11.1 Basic L1 / C1 contrast

对于每一个 Basic L1 / C1 logical evidence unit：

```text
same episode E
same baseline S0
same registered configuration
```

建立：

```text
B = WRITE_ONLY / MATCHED_OFF   (W_storage ON, W_extra OFF)
A = NO_WRITE_CONTROL           (W_storage OFF, W_extra OFF)
```

对比：

```text
B vs A
→ D_ATTRIBUTION
→ ΔS_identity_masked
```

它回答：是否存在 attributable registered write/change。

## 11.2 C2 / C3 contrast

对于每一个 C2/C3 logical evidence unit：

```text
same episode E
same baseline S0
same literal-storage path
same registered configuration
```

建立：

```text
C = TARGET_ON       (W_storage ON, W_extra ON)
B = MATCHED_OFF     (W_storage ON, W_extra OFF)
```

对比：

```text
C vs B
→ canonical ΔS_nonstorage
→ CAUSAL_CONTRAST_RULE
→ D_NONSTORAGE_BASELINE
```

它回答：在相同 storage pipeline 之外，是否有额外可归因 nonstorage change。

## 11.3 Non-mixture

```text
不得构造 A/B/C 混合三方 attribution。
Basic-L1/C1-scope ATTRIBUTED 不得满足 C2/C3 attribution requirement。
```

`pair_identity` 是 logical identity。

以下仅是 realization metadata：

```text
target_execution_id
matched_off_execution_id
baseline_state_id
phase
```

---

# 12. Discriminator Roles

三把尺子严格分层：

```text
Basic L1 / C1
→ D_ATTRIBUTION
→ ΔS_identity_masked

C2 / C3
→ D_NONSTORAGE_BASELINE
→ registered ON/OFF contrast over ΔS_nonstorage

C3 class structure
→ D_CONTENT_CONTRAST
→ T_CONTRAST_RESULT over frozen class evidence set
```

任何：

```text
Basic-L1/C1-scope ATTRIBUTED
```

不得满足：

```text
C2 / C3 attribution requirement
```

---

# 13. Reset Profile

第一版 reset 的工程原则：

```text
CLEAR input-side traces
PRESERVE registered substrate under test
```

候选清除对象包括：

```text
prompt/context carryover
KV/cache carryover
temporary runtime buffers
unregistered retrieval state
episode reinjection path
```

候选 preserve 对象：

```text
LITERAL_STORE
AFTERGLOW_SUBSTRATE
```

实际 reset procedure、clear/preserve table 与 compatibility tests：

```text
TO_BIND_BEFORE_IGNITION
```

reset 必须同时证明：

```text
declared-cleared counterfeit signal was actually removed
AND
declared-preserved registered substrate survived
```

---

# 14. Persistence

Persistence 不等于：

```text
file still exists
path still resolves
container still exists
```

它必须由 frozen `PERSISTENCE_MATCH_RULE` 对 class-specific tracked object 判定。

Reference Harness 必须支持：

```text
C1 storage-content persistence
C2 logical paired-evidence persistence
C3 class-structured evidence persistence
```

但第一轮 protocol-validation test 不要求三层都在同一次 run 中建立。

---

# 15. Reference Validation Profiles

正式 scientific candidate ignition 之前，Reference Harness 必须至少通过以下 known-answer tests。

这些 profiles 必须覆盖 preregistration 声称能够机械区分的【全部】canonical exits，
包括 pre-reset ladder（L1 / C1 / C2 / C3）与 post-reset ladder（L2 的 PASS / FAIL / UNRESOLVED / INVALID）。

## 15.0 Fixture requirement

每个 known-answer fixture 必须冻结自己的 rule bundle 与唯一 expected oracle。

不得只写设计意图（例如 `C3 should be reachable`、`C2 may be established`）。

每个 fixture 必须冻结：

```text
FIXTURE_ID
FIXTURE_RULE_BUNDLE_HASH

initial state
arm definitions
synthetic episodes

STATE_DELTA_RULE
CAUSAL_CONTRAST_RULE
measurement scale
normalization, if any
threshold / equivalence rule
indeterminate region

discriminator rules

EXPECTED_LEDGER_SEMANTICS
EXPECTED_L1_RESULT
EXPECTED_PRE_RESET_CHANGE_CLASS
EXPECTED_L2_RESULT
EXPECTED_POST_RESET_SUPPORTED_CLASS
EXPECTED_INVALIDITY_CODE, if applicable
```

必须给出【唯一 expected oracle】；`abs()` 等 alternative projection 若不属于该 fixture 的 rule bundle，
实现偷偷改用它时 known-answer validation 应 FAIL。

---

## V0 — NULL

```text
A = NO_WRITE_CONTROL           (W_storage OFF, W_extra OFF)
B = WRITE_ONLY / MATCHED_OFF   (W_storage ON-invoked, but storage operation is
                                preregistered NULL / no-op ⇒ zero-effect)
```

说明：Basic L1 的判定为 B vs A（§11.1）。

V0 的意图是"没有有效写入 ⇒ L1 FAIL"，因此 B 仍必须是 §3.1 定义的 B
（`W_storage ON`），但本次 `W_storage` 的 storage operation 被预注册为
**NULL / no-op（on-invoked, zero-effect）**，使 B 实际不产生任何 registered storage change。

因此 B vs A 的 difference = zero ⇒ 无 attributable registered change ⇒ L1 = FAIL。

预期：

```text
L1 = FAIL
```

不得：

```text
PASS
INVALID
```

除非测试本身故意破坏 protocol。

注意：不得把 V0 的 B 定义为 `W_storage OFF`；
那不是 §3.1 定义的 B。（不许用一个违反自己定义的例子，去验证自己的定义。）

---

## V0b — PRE_RESET_INDETERMINATE

构造：episode 导致的可归属 registered change 落在
frozen `STATE_DELTA_RULE` / discriminator 的【indeterminate region】内，
使预注册规则返回 INDETERMINATE，而非确定 PASS / FAIL。

```text
protocol valid
execution valid
prevalidation valid
result falls inside frozen indeterminate region
```

预期：

```text
L1 = UNRESOLVED
```

不得：

```text
L1 = PASS
L1 = FAIL
INVALID
```

目的：

```text
补齐 §16.3 pre-reset ladder 要求的 L1 = UNRESOLVED 一格；
验证 indeterminate 不得被压成 PASS / FAIL / INVALID。
```

---

## V1 — STORE_ONLY

```text
B = WRITE_ONLY / MATCHED_OFF (W_storage ON, W_extra OFF)
A = NO_WRITE_CONTROL         (W_storage OFF, W_extra OFF)

本 fixture 的 architecture 具备 higher-class identification capability，
但本次【没有 attempt】 C2 / C3。
```

预期：

```text
L1 = PASS
PRE_RESET_CHANGE_CLASS = C1

C2 = NOT_ASSESSED
C3 = NOT_ASSESSED
```

必须不能凭 literal storage 自动得到：

```text
C2
C3
```

不得把未 attempt 的 C2/C3 写成 `NOT_ESTABLISHED` / `FAIL` / `INVALID`。

Basic L1 的 B vs A 归因成立；C vs B 不存在（无 W_extra）。

---

## V2 — CONSTANT_EXTRA

```text
A = NO_WRITE_CONTROL (W_storage OFF, W_extra OFF)
B = MATCHED_OFF      (W_storage ON,  W_extra OFF)
C = TARGET_ON        (W_storage ON,  W_extra ON)
```

三臂必须满足：

```text
same E
same storage path (where storage is ON)
same baseline S0
```

V2 是一个【完整 C3 attempt】，不是只测 C2。因此它必须注册 content class 结构：

```text
>= 2 preregistered content classes
>= 2 different episodes per class
all member attributions valid
```

且 transformation 不依赖 content class：

```text
ΔS_nonstorage(C vs B) = constant K  (与 content class 无关, K != 0)
```

预期（唯一 oracle）：

```text
L1 = PASS
PRE_RESET_CHANGE_CLASS = C2

C3 = NOT_ESTABLISHED
```

其中 C3 的判定必须真跑 class 结构：

```text
same-class reproducibility          = PASS
cross-class distinguishability      = determinately FAIL
```

即：各 class 下 contrast 相同 ⇒ 同类可复现成立，但异类不可区分 ⇒ C3 负向。

因此这不是 `C3 = NOT_ASSESSED`（没做），而是 `C3 = NOT_ESTABLISHED`（做了、没过）。

V2 必须实际执行 A/B/C 三臂：Basic L1 由 B vs A 判定，C2 由 C vs B 判定；
C3 由 class 结构判定。只描述 target arm 不构成对 C2/C3 的验证。

---

## V3 — CONTENT_CONDITIONED_SYNTHETIC

使用 preregistered、matched 的 synthetic classes：

```text
Class A
Class B
```

每个 content class 至少包含：

```text
>= 2 different episodes
```

例如：

```text
A1, A2
B1, B2
```

保持已知 material nuisance controlled。

固定 fixture rule bundle（signed scalar）：

```text
OFF = 0

A1 ON = +1
A2 ON = +1
B1 ON = -1
B2 ON = -1

T_CONTRAST = ΔON - ΔOFF
measurement scale = signed
same-class equivalence  = exact equality
cross-class distinction = exact inequality
```

因此 canonical expected result（唯一 oracle）：

```text
A1 = +1
A2 = +1
B1 = -1
B2 = -1

same-class reproducibility = PASS
cross-class distinguishability = PASS
PRE_RESET_CHANGE_CLASS = C3
```

`abs()` 等 alternative projection 不属于该 fixture 的 rule bundle；
若实现改用它，known-answer validation 应 FAIL。

same-class reproducibility 必须使用【不同 episodes】（A1 vs A2、B1 vs B2）；
同一 episode replay 只能作为 repeatability control，不能替代 class-level generalization。

它：

```text
IS NOT memory evidence
IS NOT Afterglow mechanism evidence
```

---

## V4 — BROKEN_PROTOCOL (fixture family)

V4 是一个 fixture family，不是单一 fixture。每个实例 `V4.<n>` 必须唯一冻结：

```text
exact injected defect
exact attempted claim scope
EXPECTED_INVALIDITY_CODE
```

每次实例只允许【一个】预注册 defect，不得写"至少一种"。

第一版至少实例化以下之一（建议先做 observer-independence violation，先把 INVALID 分支跑通）：

```text
V4.1  rule missing
V4.2  hash mismatch
V4.3  observer independence violation
V4.4  post-outcome rule change
V4.5  provenance break
```

每个实例的预期：

```text
INVALID
EXPECTED_INVALIDITY_CODE = <该实例冻结的具体 code>
```

不得被写成 scientific FAIL。

若只声明"至少一种"而不唯一冻结 exact defect：

```text
V4 instance = UNDER-SPECIFIED
该实例不构成 known-answer oracle
```

---

## V4b — ARCHITECTURALLY_NOT_IDENTIFIABLE

构造一种 implementation：

```text
Basic L1 / C1 path = executable

BUT

same-E
same-storage-path
W_extra ON/OFF counterfactual
= architecturally impossible
```

预期：

```text
C1 = independently assessable

C2 = ARCHITECTURALLY_NOT_IDENTIFIABLE
C3 = ARCHITECTURALLY_NOT_IDENTIFIABLE
```

不得输出：

```text
C2 FAIL
C3 FAIL
INVALID
```

V4b 使 Reference Harness 覆盖 `ARCHITECTURALLY_NOT_IDENTIFIABLE` 这一类事实。

以下五类必须区分的事实，由 §15 全部 profiles 合并覆盖（而非仅 V0–V4）：

```text
NOT_ASSESSED                    ← V1 (C2/C3 NOT_ASSESSED) / V5f (post C2/C3 NOT_ASSESSED)
NOT_ESTABLISHED                 ← V2（C3 NOT_ESTABLISHED）/ V5b（post C3 NOT_ESTABLISHED）
ARCHITECTURALLY_NOT_IDENTIFIABLE ← V4b
UNRESOLVED                      ← V0b（L1）/ V5e（L2）
INVALID                         ← V4 / V5c
```

每一类都必须有一个 fixture 给出【唯一 oracle】，不得只以清单/措辞声称覆盖。
若某类无 fixture oracle：

```text
KNOWN_ANSWER_COVERAGE_INCOMPLETE
SCIENTIFIC_EXECUTION MAY NOT START
```

### 15.9 Coverage Matrix

（profile × canonical exit 对照；新增 fixture 时按矩阵查缺格，不必重读全文）

```text
profile | L1 PASS | L1 FAIL | L1 UNRES | PRE C1 | PRE C2 | PRE C3 | L2 PASS | L2 FAIL | L2 UNRES | L2 INVALID | ARCH_NOT_IDENT | NOT_ASSESSED | NOT_ESTABLISHED
V0      |         |    X    |           |        |        |        |         |         |          |            |               |              |
V0b     |         |         |     X     |        |        |        |         |         |          |            |               |              |
V1      |    X    |         |           |   X    |        |        |         |         |          |            |               |      X       |
V2      |    X    |         |           |        |   X    |        |         |         |          |            |               |              |      X
V3      |    X    |         |           |        |        |   X    |         |         |          |            |               |              |
V4      |         |         |           |        |        |        |         |         |          |     X      |               |              |
V4b     |         |         |           |   X    |        |        |         |         |          |            |      X        |              |
V5a     |         |         |           |        |        |        |    X    |         |          |            |               |              |
V5b     |         |         |           |        |        |        |    X    |         |          |            |               |              |      X
V5c     |         |         |           |        |        |        |         |         |          |     X      |               |              |
V5d     |         |         |           |        |        |        |         |    X    |          |            |               |              |
V5e     |         |         |           |        |        |        |         |         |     X    |            |               |              |
V5f     |         |         |           |        |        |        |    X    |         |          |            |               |      X       |
```

canonical exit 覆盖核对（§16.3）：

```text
L1 PASS        ← V1/V2/V3
L1 FAIL        ← V0
L1 UNRESOLVED  ← V0b
PRE C1         ← V1 / V4b
PRE C2         ← V2
PRE C3         ← V3
L2 PASS/C3     ← V5a
L2 PASS/C2     ← V5b
L2 PASS/C1     ← V5f
L2 FAIL        ← V5d
L2 UNRESOLVED  ← V5e
L2 INVALID     ← V5c
ARCH_NOT_IDENT ← V4b
NOT_ASSESSED   ← V1 (PRE C2/C3) / V5f (post C2/C3)
NOT_ESTABLISHED ← V2 (PRE C3) / V5b (post C3)
```

每个 canonical exit 与每个状态类都必须有 fixture 给出唯一 oracle。
无 oracle 的类 ⇒ `KNOWN_ANSWER_COVERAGE_INCOMPLETE`。

---


## Reset / Persistence Suite（L2）

正式 scientific candidate ignition 之前，Reference Harness 还必须通过覆盖 L2 全部 canonical exits 的 known-answer tests。

### V5a — RESET_VALID_PERSIST_C3

前置：

```text
PRE_RESET_CHANGE_CLASS = C3
reset valid
same frozen logical evidence set
all required post-reset measurements executed
```

post-reset C3 的六项条件全部重新成立。

预期：

```text
L2 = PASS
POST_RESET_SUPPORTED_CLASS = C3
```

目的：

```text
验证 C3 必须在 reset 后重新建立，而不是继承 pre-reset label。
```

---

### V5b — RESET_VALID_CLASS_COLLAPSE_TO_C2

前置：

```text
PRE_RESET_CHANGE_CLASS = C3
reset valid
```

post-reset：

```text
paired attribution survives
event-triggered nonstorage contrast survives
C2 persistence criterion passes

BUT

C3 same-class / cross-class structure no longer satisfies the frozen C3 rule
```

预期：

```text
L2 = PASS
POST_RESET_SUPPORTED_CLASS = C2

post-reset C3 = NOT_ESTABLISHED
```

这是唯一 oracle，不得只写含糊的 `<= C2`。

目的：

```text
验证：pre-reset C3 不自动继承；
      higher-class persistence failure 不抹掉 independently re-established lower class。
```

---

### V5c — RESET_INVALID_PRESERVE_FAILURE

构造：

```text
counterfeit / pre-reset clear-side signal = detectable
BUT
reset destroys or corrupts a component declared PRESERVE
```

预期：

```text
reset = INVALID
attempted post-reset interpretation:
L2 = INVALID
```

同时必须验证：

```text
previously valid pre-reset result is not retroactively erased
```

因此该 profile 的 oracle 是：

```text
pre-reset result remains separately valid
AND
L2 = INVALID
```

而不是笼统的：

```text
RUN INVALID
```

目的：

```text
验证 scientific failure != reset/protocol invalidity；
     且 lower-class 已建立结果不被 higher-class attempt 的 failure 追溯作废。
```

---

### V5d — RESET_VALID_DETERMINATE_NEGATIVE

构造：

```text
reset valid
all required frozen rules valid
all required measurements completed
persistence criterion gives a determinate negative result
no positive POST_RESET_SUPPORTED_CLASS established
```

预期：

```text
L2 = FAIL
```

目的：

```text
验证合法执行后的 persistence failure 不得被包装成 INVALID。
```

---

### V5e — RESET_VALID_INDETERMINATE

构造：

```text
reset valid
rules valid / frozen
required measurements completed
result intentionally falls inside the frozen indeterminate region
```

预期：

```text
L2 = UNRESOLVED
```

目的：

```text
验证 uncertainty / indeterminate 不得被压成 FAIL 或 INVALID。
```

---

### V5f — RESET_VALID_PERSIST_C1

构造：

```text
PRE_RESET_CHANGE_CLASS = C1
reset = VALID

episode-specific registered storage content
is re-observed after reset

PERSISTENCE_MATCH_RULE(C1) = PASS

本 fixture 的 architecture 具备 higher-class identification capability，
但本次【没有 attempt】 C2 / C3。
```

预期：

```text
L2 = PASS
POST_RESET_SUPPORTED_CLASS = C1

post-reset C2 persistence = NOT_ASSESSED
post-reset C3 persistence = NOT_ASSESSED
```

不得：

```text
POST_RESET_SUPPORTED_CLASS = C2 / C3
post-reset C2/C3 = NOT_ESTABLISHED / FAIL / INVALID
```

目的：

```text
覆盖 prereg 的独立 post-reset C1 path：
  episode-specific registered storage content persists ⇒ POST_RESET_SUPPORTED_CLASS = C1
且 C2/C3 根本未尝试时仍可合法 L2 = PASS。
这是此前 suite 未走过的 evaluator branch。
```

---

# 16. Execution Namespace and Ignition Boundary

执行被分为两个有明确依赖顺序的 namespace。
门禁只约束 `SCIENTIFIC_EXECUTION`，不约束 `HARNESS_VALIDATION_EXECUTION` 自身。

## 16.1 PHASE A — HARNESS_VALIDATION_EXECUTION

用途：

```text
synthetic known-answer fixtures only
same production evaluator / code path
test-only ledger / result namespace
SCIENTIFIC_CLAIM_ELIGIBILITY = NONE
```

依赖规则：

```text
known-answer PASS is NOT its own prerequisite
```

因此 Phase A 不需要先通过 known-answer suite 才能运行；
它自身使用完整、固定的 synthetic fixture configuration。

**入口引用（必读）：**

```text
本节受 §16.1.1 Substrate Isolation 约束。
"test-only namespace / SCIENTIFIC_CLAIM_ELIGIBILITY = NONE" 只是记账隔离；
可观测隔离见 §16.1.1。
```

### 16.1.1 Substrate Isolation（记账隔离 ≠ 眼睛隔离）

只在命名空间上隔离，不等于在【可观测访问】上隔离。

Phase A 必须满足 substrate isolation：

```text
NO_ACCESS  to real episode payload
NO_ACCESS  to real registered substrate
NO_ACCESS  to real reset
NO run on real literal store contents
NO run on real AFTERGLOW_SUBSTRATE contents
```

即：Phase A 即使跑在 same production evaluator / code path 上，
也不得读取、写入或 reset 任何真实 registered substrate 或真实 episode。

冻结原则：

```text
不许把"没写进账本"，当成"没看见"。

隔离的是命名空间，不是眼睛。
而冻结的全部意义，是在看见结果之前锁死判据。
一个跑在生产代码路径上的校验，
只要它扫过一次真实的东西——
那一刻就是结果曝光的那一刻。
无论账本上写不写。
```

若 Phase A 任何一次发生真实访问：

```text
outcome exposure 时点提前至该访问
SCIENTIFIC_EXECUTION MAY NOT START
```

Phase A 的结果：

```text
不得计为 scientific evidence
不得进入 scientific result namespace
```

## 16.2 PHASE B — SCIENTIFIC_EXECUTION

只有当 Phase A 完成后，才允许进入 Phase B。

Phase B 需要全部满足：

```text
all scientific execution-critical TO_BIND resolved
Implementation Binding frozen
STATUS_RULE_COVERAGE_PRECHECK = PASS
mandatory failure witnesses prevalidated
KNOWN_ANSWER_SUITE = PASS
```

**入口引用（必读）：** `KNOWN_ANSWER_SUITE = PASS` 受 §16.2.1 与 §16.2.2 约束：

```text
§16.2.1  IMPLEMENTATION_BINDING_HASH := IMPLEMENTATION_BINDING_MANIFEST_HASH
         （不是 SPEC hash）；qualifying suite 同时记 SPEC_HASH + MANIFEST_HASH
§16.2.2  qualifying suite 必须在 frozen MANIFEST hash 之后执行
         （MANIFEST 冻结前跑的 suite = NON_QUALIFYING DEVELOPMENT VALIDATION）
```

### 16.2.1 Suite–Binding Version Binding

`KNOWN_ANSWER_SUITE = PASS` 必须绑定到它所验证的 binding 版本。

```text
IMPLEMENTATION_BINDING_HASH
:=
IMPLEMENTATION_BINDING_MANIFEST_HASH
```

**注意对象身份（与抬头 SPEC/MANIFEST 分家一致）：**

```text
IMPLEMENTATION_BINDING_HASH 指 MANIFEST hash，不是 SPEC hash。

REFERENCE_HARNESS_SPEC_HASH
is separate and MUST NOT substitute for MANIFEST_HASH.
```

理由：§15 的 fixture 只冻结 measurement scale 等 fixture bundle 内的东西；
可变的 execution-critical TO_BIND 项（substrate representation /
READ_OPERATOR_HASH / BASE_MODEL_HASH / discriminator 实现）不在 fixture bundle 内。
这些项只在 **MANIFEST** 实例化后才被钉住；若 suite 绑定 SPEC hash，则被钉住的是一张
还画着空格的表，TO_BIND 仍可后填而 suite 仍沿用旧 PASS。

因此 qualifying suite 必须同时记录两者：

```text
KNOWN_ANSWER_SUITE_SPEC_HASH
KNOWN_ANSWER_SUITE_MANIFEST_HASH
```

并且 MANIFEST 自身反向引用其来源 SPEC：

```text
IMPLEMENTATION_BINDING_MANIFEST references REFERENCE_HARNESS_SPEC_HASH
```

（否则 MANIFEST 不知道自己从哪张图纸来，反向又漏一次。）

因此：

```text
suite 在 manifest v1 下 PASS
→ 若 SPEC 或 MANIFEST 任一【实质】变更
  （任一 execution-critical TO_BIND 被赋新值 / 任一规则实质改变）
→ suite MUST RERUN
→ 不得沿用旧 PASS
```

否则：

```text
SUITE_BINDING_HASH_MISMATCH
SCIENTIFIC_EXECUTION MAY NOT START
```

### 16.2.2 Qualifying Suite Run — Time Direction

时间方向固定为：先冻结 MANIFEST，再跑 suite。

```text
A qualifying KNOWN_ANSWER_SUITE run MUST capture
the already-frozen IMPLEMENTATION_BINDING_MANIFEST_HASH
(and the corresponding REFERENCE_HARNESS_SPEC_HASH)
before its first fixture executes.
```

即：

```text
先冻结 MANIFEST（SPEC 已冻结）
→ suite 读取 frozen SPEC_HASH + MANIFEST_HASH
→ 跑 fixtures
→ PASS
```

不得：

```text
先在 draft 上跑完
→ 后来 freeze
→ 把新 hash 填回旧 PASS
```

在 MANIFEST 冻结之前跑的 suite：

```text
NON_QUALIFYING DEVELOPMENT VALIDATION
```

它不得用于 SCIENTIFIC IGNITION。

因此正确的依赖顺序是：

```text
KNOWN_ANSWER_SUITE = PASS
→ prerequisite of SCIENTIFIC IGNITION
```

而不是：

```text
KNOWN_ANSWER_SUITE = PASS
→ prerequisite of running the known-answer suite     (circular, forbidden)
```

## 16.3 Coverage requirement

`KNOWN_ANSWER_SUITE = PASS` 要求 §15 的 profiles 全部通过，
且必须覆盖 preregistration 声称能够机械区分的【全部】canonical exits：

```text
pre-reset ladder : L1 = PASS / FAIL / UNRESOLVED ; CHANGE_CLASS = C1 / C2 / C3
post-reset ladder: L2 = PASS / FAIL / UNRESOLVED / INVALID
```

缺失任何一个 canonical exit 的 known-answer oracle：

```text
KNOWN_ANSWER_COVERAGE_INCOMPLETE
SCIENTIFIC_EXECUTION MAY NOT START
```

之后，才允许：

```text
SCIENTIFIC CANDIDATE IGNITION REVIEW
```

在 Phase B 条件满足之前：

```text
SCIENTIFIC_EXECUTION MAY NOT START
```

---

# 17. Deferred Scientific Candidate

以下内容故意不在 Reference Harness 阶段决定：

```text
actual Afterglow W_extra architecture
plasticity mechanism
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
```

这些不是被遗忘。

它们只是：

```text
NOT YET ENTITLED TO ENTER THE EXPERIMENT
```

---

# Closing

Reference Harness 的任务不是让系统看起来像会记忆。

它的任务是：

> **确保一台不会记忆的系统能够诚实失败；  
> 一个只会 storage 的系统只能得到 storage；  
> 一个恒定 transformation 不能冒充 content-conditioned effect；  
> 一个被故意破坏的实验必须被判 invalid。**

只有当实验机器学会正确地说“不”，

我们才把真正的 Afterglow candidate 放进去。
