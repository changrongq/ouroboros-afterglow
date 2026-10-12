# REQ-2 证据 — 船长（管理员）@ a47970b（v6）

**固定对象**: `a47970b205022b2e15abdca5d2999a13bdb2a1e0`（v6 候选）
**执行**: 船长（荣弦），管理员 PowerShell
**日期**: 2026-10-12
**脱敏**: 不含明文口令（凭据仅经环境变量注入）。

**证据层级**: `EVIDENCE_TIER = TERMINAL_TEXT`。

## 结果

| 轮次 | 结果 | run-id |
|---|---|---|
| 冻结基线 | BINDING_INTEGRITY = PASS | — |
| 有口令 | **Q3_QUALIFICATION = PASS** | `208d760fc96b4f9b8b740df0373df371` |
| 去口令 | **NOT_EVALUATED**（SKIP 未计 PASS） | `50ef8b30de344b6682f887a5511f693e` |

- `q3_reset_chain 120/120`、`q3_adversarial 65/65`、`q3_provenance 13/13`、
  `q3_qualify --selftest 17/17`。
- 旧 `win32_isolation`：**21/21 PASS**（管理员 ⇒ DACL 恢复权限前提满足）。
- FULL_VALID run_id 与入口 run_id **完全一致**。

> 文件：`raw_terminal_output.txt`（船长原始终端输出逐字登记）。
