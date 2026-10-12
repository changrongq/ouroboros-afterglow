# REQ-2 证据 — 船长（管理员）@ 2c92074（BD-76 修复后）

**固定对象**: `2c92074a9808b1c9acd5ad5a36cba7a34e472892`
**执行**: 船长（荣弦），管理员 PowerShell
**日期**: 2026-10-12
**脱敏**: 不含明文口令（凭据仅经环境变量注入）。

**证据层级**: `EVIDENCE_TIER = TERMINAL_TEXT`。

## 结果

| 轮次 | 结果 | run-id |
|---|---|---|
| 冻结基线 | BINDING_INTEGRITY = PASS | — |
| 有口令 | **Q3_QUALIFICATION = PASS** | `6a87237eaca74a99b966b804fbef7625` |
| 去口令 | **NOT_EVALUATED**（SKIP 未计 PASS） | `1a1809c2d6e84c4ba43e853fadeb1a0d` |

- `q3_provenance 18/18`（含 BD-76 守卫负例）、`q3_reset_chain 120/120`、
  `q3_adversarial 65/65`、`q3_qualify --selftest 17/17`。
- 旧 `win32_isolation`：**21/21 PASS**（管理员 ⇒ DACL 恢复权限前提满足）。
- FULL_VALID run_id 与入口 run_id **完全一致**。

> 文件：`raw_terminal_output.txt`（船长原始终端输出逐字登记）。
