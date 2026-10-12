# Q3 修正冻结候选 v4 —— B1/B2 判定修正（据凌翼 V3 复审）

**申请人**: Coder
**日期**: 2026-10-12
**依据**: 凌翼 LINGYI Q3 FREEZE REVIEW — V3（REVIEWED_COMMIT `866351e`）
**处置**: B1_NEGATIVE_VERDICT_GATE = FIXED；B2_RESET_ORDER = FIXED；B2_TRISTATE_VALID_GATE = FIXED；B3 = CLOSED（不变）
**RC11 冻结对象**: MANIFEST `78bdb90f…` —— **未改动**（处置 B：外部勘误）

---

## 一句话结论

凌翼的三处修正已落地并**定向复核通过**：B1 负对照现在**严格 CLEAN**（且要求句柄确实打开）；
B2 的 clear 动作/完成**前移到新 worker 之前**（未完成则**阻止**新 worker，不再事后写无效）；
`real_reset_required` 改为**严格三态**（未知 ⇒ INVALID，A33d 反例已翻转）。全量红转绿：
`reset_chain 102/102`、`adversarial 61/61`、`provenance 13/13`。

---

## §1 B1 修正（负对照判定）

- **改前**：`neg_clean = (neg_status != HANDLE_AUDIT_FOUND_TARGET)`
  ⇒ `ERROR`/`UNRESOLVED`/`None` 都被当成"无泄漏"（false-pass）。
- **改后**：
  - `neg_clean = (neg_status == HANDLE_AUDIT_CLEAN) and h2_opened`；
  - 负对照**必须**持有可继承句柄（`h2` 打开成功），否则 control 未运行 ⇒ 不成立。
- **边界说明（照凌翼）**：此**严格 CLEAN** 仅针对 **B1 受控负对照实验**，
  **不**取消 Profile B 对**正式运行期** `UNRESOLVED` 的有限豁免。

## §2 B2 修正（reset 时序 + 三态门禁）

- **时序**：clear 动作与完成校验**前移**到"旧 worker 终止 + 锁定"之后、**新 worker 启动之前**。
  新增 `clear_verified`（独立复核 targets 已消失）。**未完成则 `return`，不启动新 worker**（fail-closed）。
  ⇒ 正式满足 **旧 worker 终止 → clear 完成 → 新 worker 启动**。
- **三态**：`ResetChainResult.valid` 现要求 `real_reset_required` 是**字面 bool**；
  `UNEVALUATED/None/"true"/1/0` ⇒ **INVALID**（未知 ≠ 不需要 reset）。
  仅**预注册的首次启动**可合法为 `False`。
- **旧 worker 身份**：B2 成功链的旧 worker 现**以 afterglow_worker 账户真实启动**，
  并核实其 **token SID == 期望 SID**（不再只是裸子进程）。
- **新增负例**：clear 不完成 ⇒ `clear_verified=False` ⇒ 链 INVALID 且**新 worker 未启动**（无 attestation）。

## §3 B3（不变，已 CLOSED）

- `q3_provenance.assert_lineage_boundary()`：Q3 **恰 10** 角色，RC12 模块**排除**。
- 本候选 §4 只列 **10 个 Q3 角色**；RC12 归独立血统。

---

## §4 修正后的 Q3 冻结清单（10 角色）

| 文件 | bytes | sha256 |
|---|---|---|
| `q3_contract.py` | 11218 | `84081a36affa6a585b7dad7990609399c96361311a794d514f9f042126d4afe7` |
| `q3_access_matrix.py` | 14221 | `f9f6969516a25c64964430967654662d82645d9d6557d9b983e917a0e6c10a1f` |
| `q3_dacl.py` | 16085 | `d2a0c58ac0a9f54da0dad5a158113bef4af1b08475d7bf58940b54c65f745dad` |
| `q3_handle_audit.py` | 17116 | `7abfa23364dbdaf8268b824b96d852b9567c1d25976d065a534c68e6b3505591` |
| **`q3_reset_chain.py`** | 84000 | `746fe35a5bbed1f5b5c737769d6114965619414d3799688884c0dcb01a708e49` |
| `win32_isolation.py` | 30287 | `9108066fda402ac137aaa7ce258e7fb9349b59f37950f5a3f8f82d88c7dace7b` |
| **`win32_worker_process.py`** | 26530 | `9c8fbd93d82d7aa6b5c212ddfa5274f1384d89ba2c4520c37edf49ecb1e40915` |
| `q3_qualify.py` | 13653 | `804101a45e3598b20b1c240d0f6aca8f03f023f4af456b87dc7895f70cac9b69` |
| **`q3_adversarial.py`** | 16045 | `344daf77b0825da08cd7978eb6b24c0071178d188794347e09a4997421d6a308` |
| `q3_provenance.py` | 11369 | `a0a89f3c140e500216b58d90687a006d2888f90b3e2143c0c21e4fb5e79ba5f0` |

- **Q3_LINEAGE_DIGEST = 8677b5b8b10415ea8fe71b3c2c98027c86e68d7526ca2c56ea0b88d7fa7596d3**（仅这 10 个）
  （旧 `d2d28229…` 对应 B1/B2 **修正前**的源码；凌翼明言须在修正后重算，**不得沿用旧 digest**。）
- **RC12（独立血统）**：`qualification_binding_rc12.py` 7480 B `203ce8fab04df3d66f474cd2b3d2198d765fd553361ea1c24d68ce72eb8e91f7`
- 分离记录：`reports/Q3_PROVENANCE_DETACHED_20261011.txt`

## §5 定向回归结果

```
q3_reset_chain   102/102  (B1 三轮 + B2 真实链 + B2 不完成负例 + 三态)
q3_adversarial    61/61   (A33 系列三态；A33d 已翻转为"未知⇒INVALID")
q3_provenance     13/13   (B3 边界)
q3_qualify --selftest 17/17
Q3_QUALIFICATION = PASS
```

## §6 未变 / 边界

- **未重做** B1 正对照；**未重传** REQ-1/REQ-2 或任何已关闭归档。
- **未引入** 任务清单外的新审查系统。
- `INDEPENDENT_WINDOWS_REPLAY_OF_<new commit> = NOT YET VERIFIED`（待独立复跑）。
- RC11 字节未动；`verify_manifest_binding = BINDING_INTEGRITY PASS`。

## §7 请求裁决

1. B1 负对照严格化 / B2 时序 / B2 三态 是否**接受闭合**，可否授权**冻结 Q3 candidate**
   （锁定 §4 的 10 个哈希 + 新 digest `8677b5b8…`）？
2. 冻结后按 `Q3_POST_FREEZE_RUN = PROCEDURE APPROVED` 在管理员环境运行最终 qualification？
3. RC12 并行继续（本候选不含 RC12 角色）？

> Coder 不自行冻结、不自行点火。**新 digest 为待冻结候选身份**；实际冻结时须对最终源码重算核对。
