# 给凌翼 / 睫 / 知微：RC10 交付报告（Coder 呈）

**日期**：2026-10-10
**呈报人**：Coder（技术实施长）
**事由**：依凌翼 R1–R5 裁决执行 RC10。**RC9 = NOT CLOSED（保留审计）**，RC10 为新 lineage 对象。

---

## 0. 一句话结论

RC10 已构建、冻结、全量重跑。**凌翼 R5 的六个顶格 acceptance test 全部通过**；知微 RC9 复核的 4 个 P1 **全部闭合**（附独立复现输出）。目标不是"再增加证据"，而是"让已有 required 证据真正掌握门锁"。

```
PHASE_A_QUALIFICATION = PASS
```

---

## 1. RC10 冻结身份（LF-only）

```text
RC10_MANIFEST_HASH = d7a1a0bf425a29da7d35d08a09d6a6792695ade6c23d15fb83b06afa11fb4414
MANIFEST_BYTES     = 27638
EXECUTION_CRITICAL_ROLES = 20   （RC9 为 18；+evidence_contract.py +replay_adapter.py）
SPEC_HASH          = b7ec1fdca957b151aa2dd2323e155867710b8a1f3d39dfd16c75bdfed801fe33 (36719 B)
PARENT_PREREG      = ad0855b04561147685f41de2c3cf1529e669cf7535345862a5f9c8b30b40d5f4
```

---

## 2. R3 架构落地：单一纯裁决链 + 双入口

```
                      ┌─ PRODUCTION ingress (fixtures.py)
                      │     live runtime -> EvidenceBundle
Frozen Contract ──────┼──────────────────────────────────────┐
(evidence_contract)   │                                      ↓
                      └─ REPLAY ingress (replay_adapter.py)  PURE ADJUDICATOR
                            raw ledger + contract            evidence_bundle.evaluate_bundle
                            -> EvidenceBundle                -> GateResult
```

- **共享**：contract semantics、evidence schema validation、PRE / J / handoff / reset / reader / POST gate、INVALID dominance。
- **不共享**：EvidenceBundle 构造、source bytes、runtime objects、recorded actual result。
- **replay 绝不接受** ledger 自称的 `required_members / required_pre_class / attempted / shape` —— 全部来自 `evidence_contract.CONTRACT_BY_FIXTURE`。
- **账本只答**"观察到了什么"；**合同答**"本来应该观察什么"。

新增两个 execution-critical 文件：
- `evidence_contract.py`（**data-only**）：`REQUIRED_EVIDENCE_CONSUMPTION_MATRIX`、`AFFINE_PROBES={0,2}`、`LITERAL_PROBES={0,2}`、`REQUIRED_RESET_FIELDS`、`CONTRACT_BY_FIXTURE`(13)、每 shape 的 `expected_keys`。
- `replay_adapter.py`：`build_bundle_from_ledger` / `adjudicate_fixture_from_ledger` / `assert_exact_fixture_set`。

---

## 3. REQUIRED_EVIDENCE_CONSUMPTION_MATRIX（凌翼 R2 唯一新增结构要求）

数据落在 `evidence_contract.REQUIRED_EVIDENCE_CONSUMPTION_MATRIX`，每行四腿：`recorded_in / prod_gate / replay_gate / negative_test`。共 14 行，节选：

| required field | prod gate | replay gate | negative test |
|---|---|---|---|
| `reader_witness.affine["0"/"2"]` | `_independent_reader_ok`（探针键集精确相等） | 同链 | 删除 → Phase-A FAIL |
| `reader_witness.literal["0"/"2"]` | 同上 | 同链 | 删除 → FAIL |
| `reader_witness.raw_q`（**仅冗余交叉核对**） | 必须 == decode(S_restored.q_raw) | 同链 | 篡改 → FAIL |
| `reset_witness[arm].reset_valid` | reset gate（缺失/False/畸形 → INVALID） | 同链 | 删除 → INVALID |
| `reset_witness[arm].accepted_handoff` | `_validate_handoff_continuity`（字节级） | 同链 | 改一字节 → INVALID |
| `arms[arm].S_handoff` / `J_after` | `_validate_j_witness`（字节级） | 同链 | 改一字节 → INVALID |
| `S_restored`（verified-restored 对象同一性） | reset 对象同一性检查 | replay 重建后复查 | 改一字节 → INVALID |
| `fixture_id -> required_members` | `_validate_membership`（冻结集合相等） | **合同**决定，忽略账本 | 删成员 → INVALID |
| `fixture_id -> required_pre_class` | pre-class 前置 | **合同**决定，忽略账本 | C3→C2 → FAIL |
| `fixture_id -> attempted / shape` | `evaluate_bundle(attempted=…)` | **合同**决定，忽略账本 | 账本谎报 → replay 忽略 |
| `observed_fixture_ids`（精确 13 集） | suite 完整性 | replay 精确集相等 | 少一个 → FAIL |
| V4b separable 正对照（探针有效性） | `external_capability_probe` | adversarial 探针有效性 | 正对照未检出 → PROBE_INVALID |

> 一个字段只有同时满足 **RECORDED ∧ CONSUMED(prod) ∧ CONSUMED(replay) ∧ NEGATIVE-TESTED** 才有资格叫 REQUIRED EVIDENCE；否则只是日志。

---

## 4. 四条 P1 的闭合（RC9 → RC10）

独立复现脚本 `_verify_rc10_closure.py`，实机输出：

```
S3 empty reader probes -> protocol: INVALID l2: INVALID
   code: READER_WITNESS_INVALID: A1/READER_AFFINE_PROBE_SET: got [] required ['0', '2']
   §3 CLOSED
S5 V5a replay via contract L2: PASS ; contract required_pre_class for V5a: C3
   §5 CLOSED (contract-driven)
S6 probe on write(payload, extra_mode): True
   §6 CLOSED
S7 missing reset_valid -> protocol: INVALID l2: INVALID
   code: RESET_FIELD_MISSING: A1/A/reset_valid
   §7 CLOSED
```

**§3 reader**：`_independent_reader_ok` 现要求**探针键集精确相等**（`{}` / `{"0"}` / `{"2"}` / `{...,"999"}` 全非法 → FAIL）；expected **只从** `C.S_restored.q_raw`（`decode_int64_le`）与 `C.S_restored.literal` 独立推导；`raw_q` 降级为**冗余交叉核对**字段。假 reader（`return u`）在 q≠0 的 fixture 上必死。

**§5 replay**：`recompute_from_ledger` 由 **contract** 驱动；`required_pre_class` / members / attempted / shape 全取自 `CONTRACT_BY_FIXTURE`；强制 observed == 冻结 13 集；`recomputed_keys == expected_keys` 精确满足，零检查即 FAIL。

**§6 V4b**：`external_capability_probe` 改为 **STRUCTURAL（`inspect.signature` 真签名）+ BEHAVIORAL**，恒真的 `if False else False` 已删除；新增 `SeparableControlHandle` 正对照，探针必须对正对照返回 `separable_w_extra=True`，否则 `PROBE_INVALID`（不再是 V4b ANI PASS）。生产与 adversarial 使用**同一** `_OnlyWriteHandle` 对象类型。

**§7 reset**：`reset_valid` 列为**必填**（True→继续；False/缺失/畸形→INVALID）；`_reset_arm` 返回并被核验的 restored 对象**直接绑定**为 `S_restored`（对象链：reset-verified == S_restored == reader input == post evaluator input，机器验证相等）。

---

## 5. 凌翼 R5 六个顶格 acceptance test —— 全部 PASS

```
[PASS] R5-1 delete V5a/A1 affine[0] -> INVALID
[PASS] R5-1 delete V5a/A1 affine[2] -> INVALID
[PASS] R5-1 delete V5a/A1 literal[0] -> INVALID
[PASS] R5-1 delete V5a/A1 literal[2] -> INVALID
[PASS] R5-1 empty reader probes -> INVALID
[PASS] R5-1 extra affine[999] -> INVALID
[PASS] R5-1 corrupt raw_q cross-check -> INVALID
[PASS] R5-2 delete reset_valid -> INVALID
[PASS] R5-2 reset_valid=False -> INVALID
[PASS] R5-3 S_restored != verified-restored (1 byte) -> INVALID
[PASS] R5-6 missing member -> INVALID (MEMBER_SET)
[PASS] R5-4 ledger missing member -> replay fails closed (contract wins)
[PASS] R5-4 replay uses CONTRACT required_pre_class (V5a L2=PASS)
[PASS] R5-4 changed pre_class (C3 contract vs C2 data) -> replay INVALID
[PASS] R5-5 probe_is_valid() (detects positive control)
[PASS] R5-5 SeparableControlHandle -> separable_w_extra=True
[PASS] R5-5 CombinedOnlyHandle -> separable_w_extra=False
[PASS] R5-5 V4b production ANI output
[PASS] R5-5 production uses the probed public handle type
```
（外加保留的 RC7/RC8/RC9 攻击项。）

---

## 6. 全量重跑结果

```
[PASS] known_answer_suite       （13/13 ORACLE MATCH）
[PASS] adversarial_regression   （32/32）
[PASS] ledger_replay            （13/13 MATCH，contract-driven）
PHASE_A_QUALIFICATION = PASS

smoke_components 29/29 PASS ; smoke_evaluator 18/18 PASS
BINDING_INTEGRITY = PASS ; freeze_manifest --check = PASS
```

---

## 7. 诚实的再声明（不修饰）

- §3/§5/§6/§7 四条闭合为**实机复现**，输出原样粘贴。
- 本轮自身失误两处，**已在固定前修正，未污染结论**：
  1. 编辑工具写 CRLF，且删除+重建时旧内容被追加成"重复头"（`from __future__` 出现两次）——
     已按 seam 截断并全库扫描确认无重复头、无 CRLF；
  2. 最初误以为 `EvidenceBundle` 有 `attempted` 字段、`arms` 直接映射 `ArmPhase`，
     已用 `inspect` 校正为 arm→phase 映射。
- `verify_counterexamples.py` 为**陈旧非门禁脚本**（引用旧 `fixtures.fixture_V2` API，RC9 起即已失效），
  未被任何入口引用，**本次未删除**（lineage 纪律：历史对象不删）。

---

## 8. 请凌翼裁决

1. RC10 是否判为 **CLOSED**（六顶格 + 四 P1 均过）？
2. 是否授权进入 RC10 freeze 归档 + 同步 GitHub（保留 RC9 为审计对象，不改 `2a0737b`）？
3. 是否仍要求**独立复核**（知微 / 睫）后才可转 next phase？

> 我不自裁，等凌翼。

—— Coder 呈
