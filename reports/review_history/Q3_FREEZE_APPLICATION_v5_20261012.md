# Q3 修正冻结候选 v5 —— B2_PRESPAWN_FAILURE_GATE 收口（据凌翼 V4 复审）

**申请人**: Coder
**日期**: 2026-10-12
**依据**: 凌翼 LINGYI Q3 REVIEW — V4（REVIEWED_COMMIT `cc3acbb`）
**处置**: `NEW REMAINING ISSUE: B2_PRESPAWN_FAILURE_GATE = BLOCKING` → **FIXED**
**RC11 冻结对象**: MANIFEST `78bdb90f…` —— **未改动**

---

## 一句话结论

凌翼那句边界现在在**所有失败分支**里都成立:**"如果 reset 没有成功,新的 worker 就不应该开始。"**
新增**统一启动前失败门禁**(旧 worker 生命周期 / 必需清除动作执行 / 清除完成证据),
任一失败即 INVALID 返回、**不创建新 worker**;并把"清除必需性"提升为**合同分类**。
三条负向回归(各断言 `attestation is None`)。

---

## §1 统一启动前门禁（`q3_reset_chain` 步骤 3b）

在任何新 worker 创建前,按顺序统一检查:

| # | 检查 | 失败 ⇒ |
|---|---|---|
| (i) | reset **模式**(合同分类)与其**要求** | — |
| (ii) | **旧 worker 生命周期**：模式要求旧 worker 时,必须证明已终止 | `PRESPAWN_STOP` ⇒ return |
| (iii) | **清除动作**：模式要求时,`clear_action` 必须**存在**且**成功执行** | `PRESPAWN_STOP` ⇒ return |
| (iv) | **清除完成**：目标必须消失,且**移除它们的动作确实跑了** | `PRESPAWN_STOP` ⇒ return |

任一失败 ⇒ 设 `real_reset_required=True, real_reset_ok=False`,填 `reason`,`**return**`(不启动新 worker)。

## §2 合同分类（clear 必需性,非事后推断）

`q3_contract.py` 新增:

- `RESET_MODE_FIRST_START`（预注册首次启动;不要求旧 worker / 不要求 clear）
- `RESET_MODE_REAL_RESET`（要求旧 worker + 必需 clear action + 必需 clear 验证）
- `classify_reset_mode(old_worker_pid, clear_action)`：由**显式输入**判定模式。
- `reset_mode_requirements(mode)`：每模式的要求表(**机器消费**)。

⇒ 清除的必需性由**合同分类**决定,**不再**从事后"输入是否缺失"推断是否可跳过。

## §3 三条负向回归（凌翼点名）

`q3_reset_chain` selftest 各补一条,均断言 **`attestation is None`**（无正式新 worker）:

| 分支 | 输入 | 结果 |
|---|---|---|
| **V4-B1** 旧 worker 终止失败 | 不可观测 pid + no-op terminator | `valid=False`, `attestation=None`, `reason` 含 `PRESPAWN_STOP` |
| **V4-B2** 有旧 worker 却无 clear_action | 真 live 旧进程 + `clear_action=None` | `valid=False`, `attestation=None`, `reset_mode=REAL_RESET` |
| **V4-B3** clear 抛异常但目标已消失 | action 先删后 `raise` | `clear_action_ran=False` ⇒ `valid=False`, `attestation=None`, `PRESPAWN_STOP` |

> V4-B3 是关键边界:**目标不存在 ≠ 清除成功**。`clear_verified` 现要求 `clear_action_ran is True` 且未抛异常;action 抛出即视为未证明。

## §4 修正后的 Q3 冻结清单（10 角色）

| 文件 | bytes | sha256 |
|---|---|---|
| **`q3_contract.py`** | 13460 | `90a136065ad38fe72c143fef347096eff929fdd67c45a88034f5f14323959ff5` |
| `q3_access_matrix.py` | 14221 | `f9f6969516a25c64964430967654662d82645d9d6557d9b983e917a0e6c10a1f` |
| `q3_dacl.py` | 16085 | `d2a0c58ac0a9f54da0dad5a158113bef4af1b08475d7bf58940b54c65f745dad` |
| `q3_handle_audit.py` | 17116 | `7abfa23364dbdaf8268b824b96d852b9567c1d25976d065a534c68e6b3505591` |
| **`q3_reset_chain.py`** | 91193 | `4278e314485aa9d87709215b12d1f46827b80295c6a41369dcad22191c29b1e2` |
| `win32_isolation.py` | 30287 | `9108066fda402ac137aaa7ce258e7fb9349b59f37950f5a3f8f82d88c7dace7b` |
| `win32_worker_process.py` | 26530 | `9c8fbd93d82d7aa6b5c212ddfa5274f1384d89ba2c4520c37edf49ecb1e40915` |
| `q3_qualify.py` | 13653 | `804101a45e3598b20b1c240d0f6aca8f03f023f4af456b87dc7895f70cac9b69` |
| `q3_adversarial.py` | 16045 | `344daf77b0825da08cd7978eb6b24c0071178d188794347e09a4997421d6a308` |
| `q3_provenance.py` | 11369 | `a0a89f3c140e500216b58d90687a006d2888f90b3e2143c0c21e4fb5e79ba5f0` |

- **Q3_LINEAGE_DIGEST = 10c4548e6192490aafc156e0d354c2ace93334bcfddb1d9c4d2e71cd5292ccc6**（仅这 10 个）
  （旧 `8677b5b8…` 因 B2 启动前门禁修正作废;**不得沿用旧 digest**。）
- **RC12（独立血统）**：`qualification_binding_rc12.py` 7480 B `203ce8fab04df3d66f474cd2b3d2198d765fd553361ea1c24d68ce72eb8e91f7`

## §5 定向回归结果

```
q3_reset_chain   113/113  (含 V4-B1/B2/B3 三条启动前阻断负例)
q3_adversarial    61/61
q3_provenance     13/13
q3_qualify --selftest 17/17
Q3_QUALIFICATION = PASS
```

## §6 未变 / 边界

- **未重做** B1 正对照；**未重开** RC11 或归档验收；**未引入**新审查系统。
- `INDEPENDENT_WINDOWS_REPLAY_OF_<new commit> = PENDING`（待独立复跑）。
- RC11 字节未动；`verify_manifest_binding = BINDING_INTEGRITY PASS`。

## §7 请求（凌翼已定两步顺序）

1. ✅ **本候选 = 修正后的精确十角色哈希 + 新 digest**（已就绪）。
2. ⏳ 请在**修复后的固定 commit** 上由**荣弦或知微**完成**独立 Windows 复跑**
   （保留完整 PASS、run-id、FULL_VALID、失败对照）,再提交最终冻结裁决。

> Coder 不自行冻结、不自行点火。**新 digest 为待冻结候选身份**;实际冻结时须对最终源码重算核对。
