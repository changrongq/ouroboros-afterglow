# Q3 DESIGN FREEZE — 正式冻结登记（REGISTRATION）

**登记人**: Coder
**日期**: 2026-10-12
**依据**: 凌翼 LINGYI Q3 DESIGN FREEZE RULING（2026-10-12）
> `Q3_DESIGN_FREEZE = AUTHORIZED`；`Q3_FREEZE_RECORD_PUBLICATION = PENDING`（本文件即登记）。

**状态声明**: 这是**设计冻结登记**,**不**等于 GitHub 已自动完成冻结,**不**授权科学实验点火。

---

## §1 冻结身份

| 项 | 值 |
|---|---|
| **REVIEWED_HEAD** | `8d09e628c3b21f8da1831aad52f5950fe400163a` |
| **FROZEN_CODE_COMMIT** | `2c92074a9808b1c9acd5ad5a36cba7a34e472892` |
| **Q3_EXECUTION_ROLES** | **10** |
| **Q3_LINEAGE_DIGEST** | `450349115b71bc9013c7a79f91d9bdf5f1728f2cbae65b025eb35a66af56da36` |
| digest 算法 | `sha256( join( sorted( role + " " + sha256(raw_bytes) + "\n" ) ) )` |

## §2 十角色清单（逐文件 SHA-256 + 字节数，从冻结 commit 字节读取）

| # | 角色 | bytes | sha256 |
|---|---|---|---|
| 1 | `q3_contract.py` | 14195 | `e5fa13d09468bceebdccd088777e278226c37688dc9d574a167ff7b048b751dd` |
| 2 | `q3_access_matrix.py` | 14221 | `f9f6969516a25c64964430967654662d82645d9d6557d9b983e917a0e6c10a1f` |
| 3 | `q3_dacl.py` | 16085 | `d2a0c58ac0a9f54da0dad5a158113bef4af1b08475d7bf58940b54c65f745dad` |
| 4 | `q3_handle_audit.py` | 17116 | `7abfa23364dbdaf8268b824b96d852b9567c1d25976d065a534c68e6b3505591` |
| 5 | `q3_reset_chain.py` | 96136 | `f5b6db1ac7659cd3fdcd3d638e4611926b6793dfbd9d8686b9a4f23606faab06` |
| 6 | `win32_isolation.py` | 30287 | `9108066fda402ac137aaa7ce258e7fb9349b59f37950f5a3f8f82d88c7dace7b` |
| 7 | `win32_worker_process.py` | 26530 | `9c8fbd93d82d7aa6b5c212ddfa5274f1384d89ba2c4520c37edf49ecb1e40915` |
| 8 | `q3_qualify.py` | 13653 | `804101a45e3598b20b1c240d0f6aca8f03f023f4af456b87dc7895f70cac9b69` |
| 9 | `q3_adversarial.py` | 16684 | `f342beeb3833d06e047b628b591a6728aad12d6cb19181826541083fede16aef` |
| 10 | `q3_provenance.py` | 13844 | `c0a919262e77105614b115e536292782be128e42b0de941b60a45c9b3e01da6d` |

- 机器可读副本：`reports/frozen/Q3_FROZEN_ROLES_2c92074.json`

## §3 RC12（独立血统，不入 Q3）

- `qualification_binding_rc12.py` —— 7480 B `203ce8fab04df3d66f474cd2b3d2198d765fd553361ea1c24d68ce72eb8e91f7`
- **RC12 = PARALLEL / SEPARATE LINEAGE**；**不**在 Q3 十角色集合与 digest 内。

## §4 RC11（历史冻结，不变）

- `reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md`
  —— 28142 B `78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059`
- **RC11_PHASE_A = CLOSED / HISTORICAL / DO NOT MODIFY**（本轮未动一字节）。

## §5 两份独立复跑索引（设计冻结的有效证据）

> **勘误（2026-10-13，可追溯；凌翼发现）**：本表原先把 `a47970b`(v6) 两行的 run-id
> **误写成了先前 `6afe56a`(v5) 的值**。现按**证据包实测**更正如下（不改其他字段、不重跑、不触碰冻结对象）：
> - `a47970b`(v6) 船长：`7fb2b985…` → **`208d760fc96b4f9b8b740df0373df371`**
> - `a47970b`(v6) 知微：`2f16f3af…` → **`07251e7445b740c0843941551140e5b1`**
> （`7fb2b985…`/`2f16f3af…` 分别为 `6afe56a`(v5) 船长/知微的值，属历史引用串行。）

| 提交 | 执行 | 结果 | run-id | 证据目录 |
|---|---|---|---|---|
| `a47970b` (v6) | 船长（管理员） | `Q3_QUALIFICATION = PASS` | `208d760fc96b4f9b8b740df0373df371` | `review_history/evidence/REQ2_captain_admin_a47970b_20261012/` |
| `a47970b` (v6) | 知微（未提升） | `NOT_EVALUATED`（DACL 权限前提 N/A） | `07251e7445b740c0843941551140e5b1` | `review_history/evidence/REQ2_zhiwei_a47970b_20261012/` |
| `2c92074` (BD-76) | 船长（管理员） | `Q3_QUALIFICATION = PASS` | `6a87237eaca74a99b966b804fbef7625` | `review_history/evidence/REQ2_captain_admin_2c92074_20261012/` |
| `2c92074` (BD-76) | 知微（未提升） | `NOT_EVALUATED`（DACL 权限前提 N/A） | `ecf37248756346cdaeb35e73eb6aab11` | `review_history/evidence/REQ2_zhiwei_2c92074_20261012/` |

- run-id 出处（实测）：`a47970b` 船长 `REQ2_captain_admin_a47970b_20261012/raw_terminal_output.txt` = `208d760f…`；
  `a47970b` 知微 `REQ2_zhiwei_a47970b_20261012/results.json` runs.with_credential = `07251e74…`。

- 计数（两轮一致）: `access_matrix 14 · dacl 14 · adversarial 65 · provenance 18 · reset_chain 120 · isolation 21(管理员)/20+N-A(未提升) · worker 4 · audit 5 · consumer 17`。
- 十角色独立哈希：知微 `independent_role_hashes.json` **10/10 MATCH**；凌翼独立重算 **10/10 MATCH**。
- `2c92074 → 8d09e62`：仅新增证据/报告/索引,**未改 Q3 执行源码**（知微 `comparison.json` 亦证 `a47970b→2c92074` 仅改 `q3_provenance.py`，其余九个未变）。

## §6 范围限制观察项（如实保留，不伪装成 PASS）

1. **第三方旧 worker 退出见证**：当前为 **controller 侧确认**（`old_worker_pid` 非自报 + 同步观察终止），
   **无第三方封条** ⇒ 标 **NOT_ASSESSED（第三方见证）**。
2. **OBS-A 运行级 `POSITIVE_CONTROL_ONLY` 产物标记**：**未实际见证** ⇒ 标 **运行 NOT_ASSESSED**。

> 这两项**不**追认为本轮设计冻结的既有阻塞条件；也**不**伪装成 PASS。

## §7 冻结纪律（自本登记起生效）

- ❌ **不得**修改 §2 的 10 个 Q3 冻结源码。任何改动 ⇒ **新血统 + 新 digest + 新资格**。
- ❌ **不得**因设计冻结通过而把 `SCIENTIFIC_EXECUTION` 改为允许。
- ⚠️ **BD-76 守卫边界（凌翼保留）**：`assert_lineage_boundary()` 不逐一核对角色**名称**是否属于批准的精确十条名单。
  ⇒ 冻结后**必须继续以外部锁定的十角色清单、逐文件 hash 与 lineage digest 作为最终身份依据**,
  **不能**把生成函数自己的输出当作独立授权。
- 🔒 冻结后**资格流程**若规定需再运行,则在**本登记之后**按批准程序执行;
  本轮两份独立复跑**已作为设计冻结的有效证据,不重复施工**。
- 🔜 **后续**:Q3 实际 reset adapter 集成 + 冻结后最终验收,仍按原定步骤**独立处理**。

## §8 状态

```text
Q3_DESIGN_FREEZE = AUTHORIZED
Q3_FREEZE_RECORD_PUBLICATION = REGISTERED (this document)
FROZEN_CODE_COMMIT = 2c92074a9808b1c9acd5ad5a36cba7a34e472892
Q3_LINEAGE_DIGEST = 450349115b71bc9013c7a79f91d9bdf5f1728f2cbae65b025eb35a66af56da36
RC11_PHASE_A = CLOSED / HISTORICAL
RC12 = PARALLEL / SEPARATE LINEAGE
SCIENTIFIC_EXECUTION = MAY NOT START
```
