# REQ-2 证据 — 船长（管理员）@ 6afe56a（v5）

**固定对象**: `6afe56a37865e965eebcdb1ee81b5e7c051b2767`（v5 候选）
**执行**: 船长（荣弦），管理员 PowerShell
**日期**: 2026-10-12
**脱敏**: 不含明文口令（凭据仅经环境变量注入）。

**证据层级**: `EVIDENCE_TIER = TERMINAL_TEXT`（终端输出文本登记）。
对照：知微包 `EVIDENCE_TIER = NATIVE_JSON + ORIGINAL_ZIP`。二者层级不同，均为有效独立复跑。

## 结果

| 轮次 | 结果 | run-id |
|---|---|---|
| 冻结基线 | BINDING_INTEGRITY = PASS | — |
| 有口令 | **Q3_QUALIFICATION = PASS** | `7fb2b985067048c7a1e1e531b4aea8b1` |
| 去口令 | **NOT_EVALUATED**（SKIP 未计 PASS） | `0e4388950676480dbdf1d925b2209f6c` |

- `q3_reset_chain 113/113`、`q3_adversarial 61/61`、`q3_provenance 13/13`、
  `q3_qualify --selftest 17/17`。
- 旧 `win32_isolation`：**21/21 PASS**（管理员环境 ⇒ DACL 还原权限前提满足）。
- FULL_VALID run_id 与入口 run_id **完全一致**。

## 对照

知微**未提升**同一 commit：`win32_isolation 20/20 PASS [1 NOT_APPLICABLE]` ⇒ 总体
`NOT_EVALUATED`。两份记录**分别如实保留，互不替代**。

> 文件：`raw_terminal_output.txt`（船长原始终端输出逐字登记）。
