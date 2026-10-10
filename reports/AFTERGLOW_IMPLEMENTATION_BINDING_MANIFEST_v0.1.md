# AFTERGLOW IMPLEMENTATION BINDING MANIFEST v0.1
## 实例化版 / INSTANTIATED — 待冻结

**日期**：2026-10-10
**产生人**：Coder（技术实施长）
**性质**：**MANIFEST 实例化版（RC11）。所有 execution-critical 字段已由 `manifest_bind.py` 实测填齐，无残留 `TO_IMPLEMENT`。**

```text
STATUS = INSTANTIATED MANIFEST (RC11) / PENDING FREEZE
EXECUTION_AUTHORIZATION = NONE
IGNITION = PROHIBITED
```

**RC11 修正说明（2026-10-10，知微 RC10 独立复核 → Coder 自行修复，属 Bug 非方向变更）：**
- §4 单入口目录错位（Bug）：`qualify_phase_a.py` 曾硬编码读 `RC9_ledgers`，而 suite 写当前版本目录；
  干净快照下 `PHASE_A_QUALIFICATION=FAIL`。**修法**：suite 写 `RC11_run_manifest.json`（记录本次实际
  ledger 目录 + 产物身份），单入口读取该 manifest 决定 replay 目录；不再跨脚本硬编版本目录。
- §5 V4.1/V4b 特殊判定被重算却未纳入比较。**修法**：为 V4.1/V4b 登记各自完整结果 schema，
  replay 落实 `recomputed_keys == expected_keys` 精确相等，并校验 actual 必需字段存在（缺≠None）。
- §6 精确 13 集只核对文件名。**修法**：核对 `filename stem == item.fixture_id == ledger.fixture_id`
  三源一致 + 内部 ID 唯一 + 精确等于冻结集。
- §7 reset preserve 规则未由原始字节重算。**修法**：门禁从 raw bytes 重算 `accepted_handoff ==
  verified_restored`（reset.py preserve 规则），`reset_valid` 只作待核对声明。
- §8 结构化派生：`GateResult` 增加显式子判定字段，生产/replay 都读结构字段，不从错误消息前缀猜状态。

**实例化方法：** 所有派生 hash 由 `afterglow_harness/manifest_bind.py` 的 `compute_all()` 经 SHA-256 规范编码实测产生；
组件文件 hash 为对应 `.py` 源文件 SHA-256。可复现：重跑该脚本即得同值（源码不变时）。

**本文件身份：**

```text
REFERENCE_HARNESS_SPEC        = AFTERGLOW REFERENCE HARNESS / IMPLEMENTATION BINDING SPECIFICATION v0.1
REFERENCE_HARNESS_SPEC_HASH   = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33
REFERENCE_HARNESS_SPEC_BYTES  = 36719

IMPLEMENTATION_BINDING_MANIFEST = 本文件
```

**（冻结时本 MANIFEST 反向引用上方 SPEC hash；hash 放 detached 记录，不写入本文件，避免自指。）**

**修正说明（2026-10-09）：** 此前 RC1/RC2/RC3 的 SPEC 锚点误写为 `1386ba22…` / 36485 B，
那是加冻结标记【之前】的状态（36485 B / 1664 行；副本已由睫实机复算留存，记为 **SUPERSEDED**，非"不存在"）。
船长裁定：锚点定为磁盘真值 = `b7ec1dca…` / 36719 B（与冻结记录§一、睫实机三方一致）。

---

# 一 · Parent bindings

```text
REFERENCE_HARNESS_SPEC_HASH = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33
PARENT_PREREG_SHA256        = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
```

---

# 二 · Base model identity（authoritative = exact file hash）

```text
base_model_identity   = D:\qcr\EntropyDrivenAI\mistral-7b-instruct-v0.1.Q6_K.gguf
base_model_byte_count = 5942064800
base_model_sha256     = dfb053cb8d5f56abde8f56899ffe0d23e1285a423df0b65ea3f3adbb263b22c2
base_model_desc       = "Mistral-7B-Instruct-v0.1 Q6_K"（仅描述字段，非 authoritative identity）
```

**本组 synthetic fixture 下为登记项，不构成约束**（SPEC §四：本组 fixture 不调用 Mistral 推理）。
**引入模型调用后才生效**；届时属 binding change，需重跑 qualification。

---

# 三 · Substrate / register

```text
registered_substrate_identity = AFTERGLOW_SYNTHETIC_SCALAR_REGISTER
registered_substrate_version  = 1.0

STATE_FIELD        = afterglow_scalar : int64_le
substrate physical = substrate.bin，恰好 8 bytes，little-endian signed int64 q
baseline           = 0

literal physical   = literal.bin，恰好 16 bytes
baseline           = 16 个零字节

canonical state digest input = literal[16] || q_le_i64[8]   （共 24 bytes）
digest 算法                  = SHA-256 over the 24-byte canonical input
                               （digest 由 24 bytes 派生，不写回那 24 bytes）
```

```text
STATE_SCHEMA_HASH = 9c31e92d07cbd933a243448b27a0df4d49ee4113e5de28ce44e38077d1b621d8
                    （= harness_constants.py SHA-256；schema/encoding 的实现载体）
```

---

# 四 · 域分区

```text
STATE_FIELDS    = { LITERAL_STORE_STATE (literal.bin 16B), AFTERGLOW_SUBSTRATE_STATE (substrate.bin 8B) }
META_FIELDS     = timestamp / execution_id / episode_identity / pair_identity / audit records /
                  before_state_digest / after_state_digest / provenance digest / 调用追踪
VOLATILE_FIELDS = 工作进程内存 / 临时缓存 / counterfeit signal / 专属临时目录
```

**C2/C3 mask：** 去掉 literal 16 bytes；文件名 / 路径 / 长度 / mtime / 日志 / hash / 分配信息均不进 nonstorage outcome。
**唯一 nonstorage 数值 = q/2。**

```text
STATE_FIELDS                         = { literal.bin[16], substrate.bin[8] }

IDENTITY_ONLY_COMPONENTS             = EMPTY_SET
     （本 harness 没有任何 identity-only content 写进 STATE；
       episode identity 等全在 META_FIELDS 里。故 identity mask 不掩任何东西。）
LITERAL_STORAGE_COMPONENTS           = { literal.bin[0:16] }
NONSTORAGE_COMPONENT                 = { substrate.bin q }
     （不要把 q 放进任何 mask 集合。）

NONSTATE_STORAGE_PIPELINE_NUISANCE_EXCLUSIONS =
     { filename, path, length, mtime, allocation metadata, logs, container hash }
     （它们登记为 nuisance，但本就不属于 STATE_FIELDS —— 不是 state-delta operand，
       故不会"从 STATE 里再被 mask 一次"。）
```

**由上述 decomposition 派生（canonical delta）：**

```text
ΔS_registered       = literal change + q change
ΔS_identity_masked  = ΔS_registered            （identity mask 为空 ⇒ literal 可见）
ΔS_nonstorage       = q change only            （literal storage 被 mask 掉 ⇒ 只剩 q）
```

**对齐验证（executed = frozen）：**

```text
Basic L1 : D_ATTRIBUTION         INPUT_DOMAIN = ΔS_identity_masked ⇒ literal change 可见 ✔
C2/C3    : D_NONSTORAGE_BASELINE INPUT_DOMAIN = ΔS_nonstorage     ⇒ q change 可见 ✔
```

**（BD-56 修正说明：此前 RC5 §四 误将 `{ literal.bin, substrate.bin }` 同为 IDENTITY_ONLY_COMPONENTS，
会同时掩掉 literal 与 q，导致 ΔS_identity_masked / ΔS_nonstorage 与"唯一 nonstorage 数值 = q/2"自相矛盾。
本版按凌翼最小修法：identity-only = EMPTY_SET；literal = literal storage；nonstorage = q only。）**

```text
DOMAIN_PARTITION_HASH = 498ab252ed36f19cfdc0c1799af2651be9c2065e9f0e88b123fbdc16d40c3ea5
```

---

# 五 · Write operators

```text
StorageWriter = STORE_FULL / STORE_NULL / STORE_ONE_BYTE（见 §六）
ExtraWriter   = SYNTHETIC_W_EXTRA_OPERATOR
                  ON  : SET_INT64(preregistered_fixture_value)
                  OFF : NOT INVOKED

  EXTRA_CONSTANT : q := 2            （与 class 无关）
  EXTRA_CONTENT  : cls=L → q := 2
                   cls=R → q := -2   （值从实际 episode 内容计算，不由控制器送入）

写入前检查 q = 0；ON 臂只调用一次；OFF 臂不调用；调用次数由外部 META 检查。
```

**（SET 语义，凌翼/知微统一；非累加。）**

```text
STORAGE_WRITER_COMPONENT_HASH = ae64731b322dc1c4e827d06562eacfbf83b42069d03ed9d4fbd502daaab0cc87
EXTRA_WRITER_COMPONENT_HASH   = ae64731b322dc1c4e827d06562eacfbf83b42069d03ed9d4fbd502daaab0cc87
STORAGE_LAYER_COMPONENT_HASH  = 8271f42c6a9116e8b079bd759bb6b2d75fb75ee189b97d1445f71bf0206db7b7
```

---

# 六 · Episodes / fixtures 配置（synthetic）

```text
A1: cls=L;sample=01;
A2: cls=L;sample=02;
B1: cls=R;sample=01;
B2: cls=R;sample=02;
（四条等长 16-byte ASCII）

content_class_id 与 arm_id 分别命名，不共用变量。

Arm A: storage 不调用 ; extra 不调用
Arm B: storage 调用   ; extra 不调用
Arm C: storage 调用   ; extra 调用

storage modes:
  STORE_FULL     : 完整写 16-byte episode（普通正向 fixture）
  STORE_NULL     : 被调用但不改变状态（V0）
  STORE_ONE_BYTE : 只写首字节，其余保持 baseline（V0b；仍 16-byte schema）
```

---

# 七 · Readers / consumers

```text
READ_OPERATOR_ID      = SYNTHETIC_AFFINE_READER_V1
READ_OPERATOR_VERSION = 1.0
READ_OPERATOR_HASH    = （= readers.py 文件 hash；唯一真值见 §十三 的 readers.py 行）

行为：读恰好 8 bytes（完整文件长度恰为 8）→ int64 LE → R(q,u)=u+q/2
      内部用整数分子 (2u+q) / 固定分母 2；禁 fallback/repair/clamp/normalization/missing⇒0
中性 probe 集 u ∈ {0, 2}；probe 不带 episode/class/phase/fixture identity/预期答案
reader 无权限读 literal / 原始 episode / ledger / 模型上下文 / oracle

LITERAL_CONSUMER_ID      = LITERAL_CONSUMER_V1
LITERAL_CONSUMER_VERSION = 1.0
LITERAL_CONSUMER_HASH    = （= readers.py 文件 hash；唯一真值见 §十三 的 readers.py 行）

行为：读恰好 16 bytes（完整文件长度恰为 16）+ 中性 u → L(literal,u)=u+SUM(unsigned_byte_i, i=0..15)
      禁 fallback/repair/clamp/normalization；无 q 访问；无 class/ledger/oracle/phase 访问；无写入

两条读路径并列不合并：
  REGISTERED_LITERAL_READ_PATH   : literal.bin → LITERAL_CONSUMER_V1 → neutral future computation
  REGISTERED_AFTERGLOW_READ_PATH : substrate.bin → SYNTHETIC_AFFINE_READER_V1 → neutral future computation
```

（两条读路径同属 `readers.py`，故共用其文件 hash。RC9：此处不再重复写死数值——唯一真值在 §十三。）

**粒度说明（睫 observation①）：** READ_OPERATOR 与 LITERAL_CONSUMER 共用同一文件 hash，
故无法表达"只改了 reader、literal consumer 未变"。当前为 fail-safe（任一改动 ⇒ 整文件 hash 变 ⇒ 两条路径都 requalify）。
**requalification 触发规则：`readers.py` 任一变动 ⇒ 两条读路径全部重验。**

---

# 八 · Perturbation J

```text
J_NAME      = KNOWN_ANSWER_PRE_RESET_PERTURBATION
J_SHORT     = J
NAMESPACE   = HARNESS_VALIDATION_EXECUTION_ONLY
SCIENTIFIC_CLAIM_ELIGIBILITY = NONE

约束：frozen per fixture before execution；only after S_write observation；
      only before S_handoff snapshot；independently observed before/after；
      MUST NOT be called by RESET；MUST NOT execute in SCIENTIFIC_EXECUTION
      （除非未来科学设计单独注册）

J modes（四者须在第一条 qualifying fixture 前全部绑定，有 hash）：
  IDENTITY                 : literal 不变；q 不变            [V5a / V5f]
  COLLAPSE_SIGN            : literal 不变；q 非零 → +2，零 → 0  [V5b]
  ERASE_EFFECT             : literal → 16 零字节；q → 0      [V5d]
  HALVE_AND_ERASE_LITERAL  : literal → 零；q ∈ {+2→+1, -2→-1, 0→0}  [V5e]
                             （仅定义在冻结输入域 {0,+2,-2}；其他输入 = fixture 执行错误）

J_RULE_BUNDLE_HASH = 472aaec1cb6b6b187f529163fffdc5c09137dd8ffc24df2b21817063e0ae70e4
J_COMPONENT_HASH   = d0920afdd9cc0a6bd14a45babb0da4468c7417a8c4ccd92896d0d66a7d06cc25

J 时点见证（BD-52，凌翼/睫裁定）：
  observer 必须独立见证 J 时点，记录三元组：
      ( S_write_digest , J_after_digest , S_handoff_digest )
  要求：J_after_digest == S_handoff_digest
  若不等 ⇒ J 未在 handoff 前完成 ⇒ 该 fixture = INVALID
  （并入 SPEC §7.2；此前仅登记在 15.3，未并入正文）
```

---

# 九 · Observer

```text
state_observer_identity = SYNTHETIC_OBSERVER_V1
state_observer_version  = 1.0
state_observer_hash     = f8b68319dc4b8731eb869035884ed8767ebc96c54e7bc28059a5a47e05c3cf52

要求：observer != write operator；只读，不能写 registered substrate；
      从文件独立读 STATE_FIELDS、独立计算 state identities
```

---

# 十 · Reset

```text
RESET_PROFILE_ID   = PROCESS_REPLACE_PRESERVE_FILES_V1
RESET_PROFILE_VERSION = 1.0
RESET_PROFILE_HASH = bf90552c73626ed449892ab2f1b9b4614cd97fd262ddb9b56e02ff7781058a8c
RESET_COMPONENT_HASH = d985c278330af1e552b545c791a32b351c83f51566c38b54321ce266374a9ca8
RESET_COMPATIBILITY_MANIFEST / HASH = 见下方 clear/preserve table（其内容 hash = RESET_PROFILE_HASH）

clear/preserve table:
  literal bytes            PRESERVE
  substrate bytes          PRESERVE
  模型权重文件             PRESERVE / READ ONLY
  旧工作进程及内存         CLEAR（进程退出）
  payload 缓冲 / 临时缓存 / counterfeit signal  CLEAR
  旧临时目录 / 输入句柄    CLEAR（新进程无访问权）
  reader / literal-consumer / schema / rules   使用同一冻结版本
  控制器 identity / ledger 外部保留；不回灌被测进程
  原 episode 输入 / 新写入调用   reset 后禁止重放

三向 witness：clear-side + preserve-side + access-side（见 SPEC/提案 §6.1）
任何一边失败 ⇒ RESET = INVALID

**命名消歧（睫 observation②）：** 逻辑层的 access-side 声明改名 **LOGICAL_ACCESS_DECLARATION**，
以免与未来 OS 级"真实权限拒绝"的 access-side witness 同名。
⇒ 逻辑层 = LOGICAL_ACCESS_DECLARATION；OS 级 = ACCESS_SIDE_WITNESS（真隔离，待实现）。

⚠ 已知实现缺口（诚实登记，不隐藏）：
  · 当前 reset.py 提供"逻辑层"三向 witness 判定（access 侧 = LOGICAL_ACCESS_DECLARATION）；
  · OS 级进程替换 + 权限拒绝（ACCESS_SIDE_WITNESS 的真实隔离）尚未实现，
    以 NotIsolatedError 显式拒绝假装完成；
  · 因此本 MANIFEST 授权范围 = HARNESS_VALIDATION（逻辑层）；
    SCIENTIFIC_EXECUTION 仍需 OS 级隔离落地后方可点火。
```

---

# 十一 · Discriminators / rules

```text
D_ATTRIBUTION        INPUT_DOMAIN = ΔS_identity_masked   （Basic L1 / C1）
D_NONSTORAGE_BASELINE INPUT_DOMAIN = signed T over ΔS_nonstorage （C2/C3）
D_CONTENT_CONTRAST   INPUT_DOMAIN = signed T over frozen class evidence set （C3）

STATE_DELTA_RULE_ID / HASH          = SYNTHETIC_STATE_DELTA_V1 / 7425a78f6645cf880a397c251d7554f09213622ca37c484a2f2b3a9bac5a53c2
CAUSAL_CONTRAST_RULE_ID / HASH      = SYNTHETIC_CAUSAL_CONTRAST_V1 / 73ced32e4cbf4856321a6939e5e767761d238c69966d93c7ce1d668cc05d834b
CONTENT_CONTRAST_RULE_ID / HASH     = SYNTHETIC_CONTENT_CONTRAST_V1 / 4004b914e8400d349758c29fd6a816b766a7220ad2737659f01e8c1a9a18240e
DISCRIMINATION_RULESET_ID / HASH    = SYNTHETIC_DISCRIMINATION_RULESET_V1 / 770fb3ec33a7f3976ed6dfc511419601f515956b638ceba47ec35ba9719f323a
POST_RESET_CLASS_RULE_ID / HASH     = SYNTHETIC_POST_RESET_CLASS_V1 / 9e4f385d342c0868f15db74a8972bb7dffc8e7985606165267fea7386c21fa05
PERSISTENCE_MATCH_RULE_ID / HASH    = SYNTHETIC_PERSISTENCE_MATCH_V1 / 69bf70b27f2835f3242d7255cc92e359a15053c0a7538c8811df5144c585394e

阈值（synthetic rule bundle 专用）：
  Basic L1: h=0 → neg ; h=1 → INDETERMINATE ; h>=2 → positive
     ★ h 计算式（钉死，防歧义）：
         h = B vs A 的 literal 逐字节不同位置数
         q 差异【不计入 h】（睫 observation①：q 项不得作为 h 的正向补足项；
         本 harness 中 q_B != q_A 是 ARM_CONFIG_INVALID，不是 h 的一部分）
  C2: |T|>=1 → positive ; T=0 → neg ; 0<|T|<1 → INDETERMINATE（ledger 存 signed T）

L2 聚合规则（BD-53，已冻结；无 positive class 时）：
  任一 attempted class 落入 frozen indeterminate region ⇒ L2 = UNRESOLVED
  仅当全部 attempted class 均为 determinate negative      ⇒ L2 = FAIL
  ⇒ lower-class determinate negative 不得取消 higher-class 的 indeterminate
  L2_AGGREGATION_RULE_ID = SYNTHETIC_L2_AGGREGATION_V1
```

**注①：** `DISCRIMINATION_RULESET` 为上述 rule bundles 的聚合视图；
hash 已由 `manifest_bind.py` 的聚合输出填定（上）。

---

# 十二 · Fixture bundles / oracles

```text
CONTENT_CLASS_MANIFEST_ID   = SYNTHETIC_CONTENT_CLASS_MANIFEST_V1
CONTENT_CLASS_MANIFEST_HASH = 27616f8b1f8b0bdcb82c0c1aeb6cb6d78c6d038c96817776cf96f0f16600c75a
CONTENT_CLASS_EVIDENCE_SET_ID   = SYNTHETIC_CONTENT_CLASS_EVIDENCE_SET_V1
CONTENT_CLASS_EVIDENCE_SET_HASH = d98d544c27ae76a334d9b5732ddfdbaba189ec790ab61943e8a436934324982c

L1_FAILURE_WITNESS_MANIFEST = V0（h=0 确定负向）+ V0b（h=1 不确定）
L1_FAILURE_WITNESS_HASH     = f241e93d4a68fb012f04e9217efcf8395b49225c6e1507f009cba5416247199c (V0)
                              8bbca27b277e447834b188569b95556e3a5906c5397c94528e25a5eb97ed27d2 (V0b)
（注：L1_FAILURE_WITNESS_HASH 与 §十二 V0/V0b 的 FIXTURE_RULE_BUNDLE_HASH 同值 ——
 系【复用同一对象】，非漏填另一枚 hash。）

fixtures: V0 / V0b / V1 / V2 / V3 / V4.1 / V4b / V5a / V5b / V5c / V5d / V5e / V5f
（oracle 见合并提案 §九 表）
```

**FIXTURE_RULE_BUNDLE_HASH（每个 fixture 各一套）：**

| Fixture | FIXTURE_RULE_BUNDLE_HASH |
|---|---|
| V0   | f241e93d4a68fb012f04e9217efcf8395b49225c6e1507f009cba5416247199c |
| V0b  | 8bbca27b277e447834b188569b95556e3a5906c5397c94528e25a5eb97ed27d2 |
| V1   | 6bad756609a8a45a2a184494ad02fbf5849539a642f4b4ef4e28abefa3a426aa |
| V2   | 84c686453cab5803704796a4cad1556e4b9d6f41edc03ad3905ff5e22b414eba |
| V3   | 9e5fb39bc0cf8a8334416acf998dfc071008bb0675a7a5eddc2a2681c696187b |
| V4.1 | 247f9e6f07e3645ba63a9c77d4cad1deb42b9156857fcab0fc5ecf42fe9e6c02 |
| V4b  | b35038e7059e49e46b94c2eb55ed09b7b2d617e7329d9aa8a531bc62f81e399f |
| V5a  | 9b989cb42f82e126cd70ddd0a774b200c571594d364a78e18d4a66315ceacaef |
| V5b  | 82d579b16599710b12959a27d37528c72d06564c7317e26c3cccdd3a5288f184 |
| V5c  | 62db6956f65c71503f08845a4ee9617e0c1343cb9279540f00c731a087e3e73d |
| V5d  | 04f141b31df9bd1240af85397394e9aa2bb4966d9996b48859fa0b8eb7da2930 |
| V5e  | 124809a20f36ba957774e7a9b5fff459a8462acde9899d7c1441db8a1884ecb9 |
| V5f  | ae6b16f6d389f049f41208f61f7a3b7dd63de8032d35eaff92a102b26e57ab5f |

**V4.1 唯一 oracle（凌翼 R1 裁定：留在 pre-reset C2 scope）：**

```text
attempted_scope : PRE_RESET / C2
  pre_reset_C1 = true ; pre_reset_C2 = true ; pre_reset_C3 = false ; post_reset = false

L1                     = PASS
PRE_RESET_CHANGE_CLASS = C1
C2_ATTEMPT             = INVALID
INVALIDITY_CODE        = CAUSAL_CONTRAST_RULE_MISSING
C3                     = NOT_ASSESSED
L2                     = N/A   （post-reset 未进入；“未进入 L2” ≠ L2 失败）
```

**MUST NOT emit `L2 = INVALID`。** post-reset invalidity 的 known-answer witness 是 **V5c**（reset invalid）。

**coverage 拆分：**

```text
V4.1 → pre-reset attempted C2 protocol INVALID（exact code: CAUSAL_CONTRAST_RULE_MISSING）
V5c  → attempted post-reset claim INVALID（reset invalid）
⇒ 两种不同 scope 的 invalidity 标定：pre-reset invalidity ≠ post-reset L2 invalidity
```

**schema 说明：** “未进入 L2” 用既有 `N/A`（不适用）表达，与 `NOT_ASSESSED`（没有测）区分，不混用；
evaluator 由 `attempted_scope` + 缺失 rule 推导 invalidity，不由 fixture ID 特判。

---

# 十三 · Component ID / version / hash 汇总

（即“实现源码/构建产物 hash”；对应提案 §十一 #1 的“实现源码 hash”。）

**（RC9：本表由单一登记表 `qualification_role_registry.py` 生成；
`qualification_binding` 与 `manifest_bind` 读取同一登记表。parser 只解析
BEGIN/END 之间的 EXECUTION_CRITICAL 段，不再吞 BUILD_PROVENANCE。
三源必须精确相等：registry == MANIFEST == 实际文件。）**

```text
EXECUTION_CRITICAL_ROLE_TABLE_BEGIN
harness_constants.py 1.0 9c31e92d07cbd933a243448b27a0df4d49ee4113e5de28ce44e38077d1b621d8
storage.py 1.0 76c376c6a413f47c8c68a6340f67b62d9ab2ba62c6807571600836ca7a59303b
writers.py 1.0 08f7d968bdb4aa37c206e169cabbb08b9616b0990c0e758e7958c93c6b5b690c
readers.py 1.0 2180f0d9747a4e1c21178f1d24244723538153ca126138163b0778813231f2b2
observer.py 1.0 82d244cdc8ecdaa0916c342b9aa266416314f9af7ca5e77be3a224788159d8fd
perturbation_j.py 1.0 28eeadc8aa77adc6be5ea453e5c5ef1f854877e437f492276cb2e9063bb11b49
reset.py 1.0 9b57cc3d59286c79f18de78b2467957c387bb4861ded6876106e05a79ddb6f21
evaluator.py 1.0 fa644a9bcfd59ffbbb415f0f439599eb705333600e7f8f8f0b93997ce6a59b5a
fixtures.py 1.0 9b70a02df4b3e9634aeab612930e38de931002c219db861a14df3bd730bee36d
fixture_contracts.py 1.0 b3137d9988660aa596f639afef5c1962edb525f4ec497dbdcd9f2ad69d86485e
evidence_contract.py 1.0 a55152de0887cece751d8ab185bd5c7ea174df409a4a38cb54b95c857f9e6cb2
evidence_bundle.py 1.0 29c1dc78963b13f61fc2faa756a20a05d0b9647dd8cebd13ec55c3ec18a450df
replay_adapter.py 1.0 6c0771f2952edc16db884527940852f4c2a7284492ebbdbdf78d462ed4cf9b3e
qualification_role_registry.py 1.0 1394c7f4fcb33319d17613a2770be04f599c14a25728b59c3a9b2316856bec0b
qualification_binding.py 1.0 6d624ce1b22fdb33d6ca0e28979899e112b89718082e68ecc67f602b688bcb88
run_known_answer_suite.py 1.0 70435fb058d6012ebb7fca91ad0c6c1531699ba998eb9c9326296e77e9e16c75
qualify_phase_a.py 1.0 3ca947700901d607a0ea6f22218c0e32c30bf7b8663c9d6b78606e9201f0a1a0
verify_manifest_binding.py 1.0 9448ef8f8eac751eba4b989a7de823921cf02a796b045a8699fae2dfb1fa331d
adversarial_regression.py 1.0 d2743520edc279a310bdb9b88810baeaf84adc106496e1882e0bd7752c4864a0
recompute_from_ledger.py 1.0 5203f0dee2f1c0fe32c9463bb67cab00d79b72171ab766447f89cc6115ffcd82
EXECUTION_CRITICAL_ROLE_TABLE_END
```

**BUILD PROVENANCE（记录但不 execution-critical binding；见 §十五 BUILD_TOOL_HASHES）：**

```text
manifest_bind.py          —— build/release tooling，产生 frozen artifact；不因变动自动推翻 artifact
freeze_manifest.py        —— build/release tooling，同上
```

---

# 十四 · Invariants

```text
PARENT_PREREG_SHA256        = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
REFERENCE_HARNESS_SPEC_HASH = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33
base_model_sha256           = dfb053cb8d5f56abde8f56899ffe0d23e1285a423df0b65ea3f3adbb263b22c2
```

**任一变更 ⇒ new MANIFEST_HASH ⇒ requalification。**

---

# 十五 · TO_IMPLEMENT 清账 + BUILD TOOL HASHES

```text
BASE_MODEL_HASH          ✅ 已定（dfb053cb…）
substrate representation ✅ 已定（8B int64 LE + 16B literal）
reader / literal-consumer 行为 + ID/version/hash ✅ 见 §七
reset profile + hash / compatibility manifest     ✅ 见 §十；OS 隔离缺口已诚实登记
J modes + rule bundle hash                        ✅ 见 §八（值不在此重复；唯一真值在 §八）
各 rule ID/HASH                                   ✅ 见 §十一（唯一真值在 §十一）
各 fixture bundle/HASH                            ✅ 见 §十二
observer ID-version-hash                          ✅ 见 §九
组件文件 ID-version-hash                          ✅ 见 §十三

无残留 TO_IMPLEMENT。
```

**（BD-55 修正：本节原误重复了 J / DISCRIMINATION 的旧值前缀，与 §八/§十一 的真值冲突。
按睫的修法，本节只引用章节、不重复写死数值；唯一真值位于 §八 / §十一。）**

**BUILD_TOOL_HASHES（provenance，供历史审计；非 execution-critical binding）：**

```text
manifest_bind.py     1.0  ae74a2710be7e9031a474ec3b67450d0ada485b1ba555d49c2925cf70e2d74e2
freeze_manifest.py   1.0  f748f8bdba40f4eaae82b8fc21cc98790c0807e0a7d42c783b3842cc912a0639
```

**变更历史（lineage）：**

```text
v0.1-instantiated   b3802142…（首轮实例化；含 V5e 修复后的 fixtures.py/evaluator.py）
                     —— 该版本 V4.1 = L2 INVALID，属 SCOPE PROMOTION 缺陷（凌翼 CONFIRMED）
v0.1-RC2            6cf3f7e3…（V4.1 修复为 pre-reset C2 scope；驱动脚本纳入 binding）
                     —— BD-52/BD-53 报告命中（睫）：V5 未穿真实 J、V5e oracle 不唯一
v0.1-RC3            BD-52：V5 套件穿真实 J + observer 见证时点三元组；
                     BD-53：冻结 L2 无 positive class 聚合规则
v0.1-RC4            SPEC 根锚点修正：1386ba22…（36485 B，加冻结标记前版本，SUPERSEDED）
                     -> b7ec1dca…（36719 B，磁盘真值；与冻结记录§一、睫实机三方一致）
                     船长裁定采用 b7ec1dca…
v0.1-RC5            BD-55 修正：§十五 去掉重复的旧值前缀（改引用 §八/§十一）；
                     措辞更正：1386ba22… = SUPERSEDED（非"不存在"）；
                     顺手落实睫 observation①/②/③/④（粒度注明 / witness 改名 / h 计算式 / 复用注明）
v0.1-RC6            BD-56 修正：§四 domain partition —— identity-only = EMPTY_SET；
                     literal = literal storage；nonstorage = q only；补 NONSTATE nuisance 声明。
                     同时：文件由 CRLF 转为 LF（与 SPEC 一致；canonical form 合规）。
v0.1-RC7            （本次）BD-57 + 知微 P1 修复：
                     · §2 源码绑定：全部 .py 转 LF（消除 CRLF⇄LF 漂移）；源码 hash 全部重算；
                        prereg 主路径改为与冻结值 ad0855b0… 对应的 FREEZE_CANDIDATE。
                     · §3 V2/V3 不再丢弃/写死 L1；从真实读到 actual。
                     · §4/BD-57 V5 post-reset 的 C1/C2/C3 从【reset 后】重新读取重建。
                     · §5 reset 覆盖全部 required 臂（A/B/C）；每个 member 的结果都保留。
                     · §7 observer + 两条 read 路径实际接通；reset witness 明确为逻辑声明。
                     · §6 资格 preflight：校验 9 组件 + 2 driver + 实际 SPEC/prereg 文件 + fixture 集合。
                     · §9 加固：C3 成员集校验；INVALID 传播；B 后置复读；V4b wrapper 语义。
v0.1-RC8            （本次）凌翼裁定 + 知微 RC7 复核全部 P1：
                     · PRE_EVIDENCE_GATE（源 = S_write；L1→C1→C2→C3；NO failure-default C3）
                     · POST_RESET_EVIDENCE_GATE（源 = S_restored only；INVALID 支配）
                     · J_GATE / RESET_GATE（任一失效 ⇒ INVALID）
                     · 单一冻结 oracle 源 = fixture_contracts.FROZEN_ORACLES（fixtures 只取 config）
                     · ledger = member × arm × phase 原始观察（recompute_from_ledger.py 可重算）
                     · manifest_bind.py 移出 qualification 运行时；qualification_binding.py 取而代之
                     · 绑定集合扩至全部运行时角色（非空、精确相等；空集必 FAIL）
                     · V4b 改为真正不可分离接口；reader 见证读非零 q
                     —— 新 MANIFEST_HASH 见 detached 记录
v0.1-RC9            （本次）凌翼 R1–R4 + 知微 RC8 复核 §11 全部收口（fail-open → fail-closed）：
                     · EVIDENCE_BUNDLE（evidence_bundle.py）= 唯一证据对象：member×arm×phase×raw×witness
                     · 单一公共链：member-set→arms/phases→S_write→PRE→required_pre_class
                       →J witness→J.S_handoff==RESET accepted handoff（逐字节）→reset
                       →S_restored→reader/literal witnesses→POST→L2；INVALID 全面支配
                     · 单一角色登记表 qualification_role_registry.py；§十三 用
                       EXECUTION_CRITICAL_ROLE_TABLE_BEGIN/END 标记；三源精确相等（registry==MANIFEST==实际文件）
                     · manifest_bind.py 移出运行时；qualify_phase_a.py = 唯一 PASS 入口
                     · recompute_from_ledger.py：REQUIRED_SCOPE；零检查 ⇒ FAIL；从原始字节重算 digest
                     · V4b = CombinedOnlyWriter + external_capability_probe（无公开 Arm/store/mode/selector）
                     · adversarial_regression.py = 16/16（含 RC9 全部反例）
                     —— 新 MANIFEST_HASH 见 detached 记录
```

---

**STATUS = INSTANTIATED MANIFEST (RC9) / PENDING FREEZE**
**—— Coder · 2026-10-10**
