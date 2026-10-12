# Q3 修正冻结候选 v6 —— REAL_RESET 合同启动前强制（据凌翼 V5 复审）

**申请人**: Coder
**日期**: 2026-10-12
**依据**: 凌翼 LINGYI Q3 FINAL CANDIDATE REVIEW — V5（REVIEWED_HEAD `f13c1ec`, REPLAY `6afe56a`）
**处置**: `REMAINING_BLOCKING: REAL_RESET_CONTRACT_PRESPAWN_ENFORCEMENT` → **FIXED**
**RC11 冻结对象**: MANIFEST `78bdb90f…` —— **未改动**

---

## 一句话结论

合同写"REAL_RESET 必须证明旧 worker 终止",但门禁留了后门:**只给 clear_action、不给旧 PID,
也能进 REAL_RESET 并拿 `real_reset_ok=True`**。已修:**REAL_RESET 启动前必须确认旧 worker 确实存在且已终止**,
且**必需的 clear 集合必须完整**;两者都在新 worker 启动前 fail-closed。合同要求与实际门禁现在**严格相等**。

---

## §1 复现（修复前）

`classify_reset_mode(None, clear_fn)` → `REAL_RESET`,而：
- `REAL_RESET` 要求 `old_worker_required=True`;
- 但 `old_worker_pid=None` 时 `out.lifecycle_ok=True`（假设无旧 worker）;
- 门禁 `if reset_old_worker_required and lifecycle_ok is not True` ⇒ **不触发**。

⇒ **有 clear_action、无旧 PID ⇒ 通过 ⇒ `real_reset_ok=True`**。**确认属实。**

## §2 修复

### 2a 旧 worker 必须真实存在（合同强制）
- **合同**：新增 `RESET_MODE_INCONSISTENT`；`classify_reset_mode` 改为——**REAL_RESET 由"存在旧 worker"定义**;
  **clear_action 而无旧 worker ⇒ `INCONSISTENT`**（合同不可能的输入）。
- **门禁 (i)**：`INCONSISTENT` ⇒ `PRESPAWN_STOP` ⇒ 立即返回。
- **门禁 (ii)**：模式要求旧 worker 时,**`old_worker_pid` 必须非 None**(实际存在)**且** `lifecycle_ok is True`(已终止)。
  仅 `lifecycle_ok is True` **不再**足够。

### 2b 必需 clear 集合完整性（启动前）
- **门禁 (iv-pre)**：模式要求 clear 时,先用合同 `validate_clear_targets()` 校验**必需类别集合完整**;
  缺失 ⇒ `PRESPAWN_STOP` ⇒ 返回(**不启动新 worker**),不再留到运行后的 `clear_ok` 才判 INVALID。

### 2c 证据范围限定（凌翼要求写清）
- 启动前门禁**在 pre-reset 诊断探针之后**运行。故 **`attestation is None` 证明的是正式 post-reset worker 未启动**,
  **不**代表"任何 worker 账户子进程都没跑过"。此限定已写入 `q3_reset_chain` 文档串,避免把较窄证据说成较宽保证。

## §3 两条新负向回归（凌翼点名）

| 负例 | 输入 | 结果 |
|---|---|---|
| **V5-N1** 只有 clear_action、无旧 PID | 有效 clear + `old_worker_pid=None` | `reset_mode=INCONSISTENT`、`valid=False`、**`attestation=None`**、`PRESPAWN_STOP` |
| **V5-N2** 缺少 required clear 类别 | 真 live 旧 worker + 缺一必需类别的 clear set | `valid=False`、**`attestation=None`**、`reason` 含 `PRESPAWN_STOP ... clear set incomplete` |

（另：`V4-B2`/`V4-B3`/`B2 incomplete clear` 现改为带**真旧 worker** 的 REAL_RESET,以继续覆盖 clear 逻辑。）

## §4 修正后的 Q3 冻结清单（10 角色）

| 文件 | bytes | sha256 |
|---|---|---|
| **`q3_contract.py`** | 14195 | `e5fa13d09468bceebdccd088777e278226c37688dc9d574a167ff7b048b751dd` |
| `q3_access_matrix.py` | 14221 | `f9f6969516a25c64964430967654662d82645d9d6557d9b983e917a0e6c10a1f` |
| `q3_dacl.py` | 16085 | `d2a0c58ac0a9f54da0dad5a158113bef4af1b08475d7bf58940b54c65f745dad` |
| `q3_handle_audit.py` | 17116 | `7abfa23364dbdaf8268b824b96d852b9567c1d25976d065a534c68e6b3505591` |
| **`q3_reset_chain.py`** | 96136 | `f5b6db1ac7659cd3fdcd3d638e4611926b6793dfbd9d8686b9a4f23606faab06` |
| `win32_isolation.py` | 30287 | `9108066fda402ac137aaa7ce258e7fb9349b59f37950f5a3f8f82d88c7dace7b` |
| `win32_worker_process.py` | 26530 | `9c8fbd93d82d7aa6b5c212ddfa5274f1384d89ba2c4520c37edf49ecb1e40915` |
| `q3_qualify.py` | 13653 | `804101a45e3598b20b1c240d0f6aca8f03f023f4af456b87dc7895f70cac9b69` |
| **`q3_adversarial.py`** | 16684 | `f342beeb3833d06e047b628b591a6728aad12d6cb19181826541083fede16aef` |
| `q3_provenance.py` | 11369 | `a0a89f3c140e500216b58d90687a006d2888f90b3e2143c0c21e4fb5e79ba5f0` |

- **Q3_LINEAGE_DIGEST = ab12c396dee8c7eb9e28120732e8c8f17842e4f12344dd40d45d25781a206c50**（仅这 10 个）
  （旧 `10c4548e…` 因本合同强制修正作废,不沿用。）
- **RC12（独立血统）**：`qualification_binding_rc12.py` 7480 B `203ce8fab04df3d66f474cd2b3d2198d765fd553361ea1c24d68ce72eb8e91f7`

## §5 定向回归结果

```
q3_reset_chain   120/120  (含 V5-N1/N2 合同启动前负例)
q3_adversarial    65/65   (含 A35 系列 V5 分类)
q3_provenance     13/13
q3_qualify --selftest 17/17
Q3_QUALIFICATION = PASS
```

## §6 未变 / 边界

- **未重做** B1/B3;**未重开** RC11 或归档;**未重上传** 旧证据。
- `6afe56a` 两份复跑结果**完整留作 v5 历史证据**,不删不改。
- **v6 为修正后源码** ⇒ 需**重算 digest**(本申请 §4 已给) + 对**修订后的固定字节再做一次独立资格复跑**。
- RC11 字节未动;`verify_manifest_binding = BINDING_INTEGRITY PASS`。

## §7 请求裁决

1. `REAL_RESET_CONTRACT_PRESPAWN_ENFORCEMENT` 是否**接受闭合**,可否授权**冻结 Q3 candidate**
   （锁定 §4 的 10 个哈希 + 新 digest `ab12c396…`）？
2. 冻结后按已批准流程在新固定 commit 上由**荣弦/知微**做**一次独立资格复跑**（保留 PASS/run-id/FULL_VALID/失败对照）？
3. RC12 并行继续（本候选不含 RC12 角色）？

> Coder 不自行冻结、不自行点火。**新 digest 为待冻结候选身份**;实际冻结时须对最终源码重算核对。
