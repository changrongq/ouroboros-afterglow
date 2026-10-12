# REQ-2 证据 — 船长（管理员）当前提交复跑

**提交**: `5fda4298772a69d850d0d3bfe898c5cce546dcc8`
**执行**: 船长（荣弦），管理员 PowerShell
**日期**: 2026-10-12
**脱敏声明**: 本包不含 worker 明文口令（凭据仅经环境变量注入）。

**证据层级（凌翼 2026-10-12：如实标注，不强行等同格式）**:
`EVIDENCE_TIER = TERMINAL_TEXT`（终端输出文本登记）。**非**机器原生 JSON 附件。
对照：知微包为 `EVIDENCE_TIER = NATIVE_JSON + ORIGINAL_ZIP`。二者证据层级不同，均为有效独立复跑。

## 文件

| 文件 | 说明 |
|---|---|
| `raw_terminal_output.txt` | 船长提供的原始终端输出（逐字登记） |

## 关键结果

- `verify_manifest_binding.py` = **BINDING_INTEGRITY = PASS**（MANIFEST `78bdb90f…`）。
- 有口令轮：`Q3_QUALIFICATION = PASS`；run_id `f1e7d60479f94d80be61a105ed1ffedf`
  与 `FULL_VALID_SUCCESS_PATH` 行 run_id **完全一致**。
- 去口令轮：`Q3_QUALIFICATION = NOT_EVALUATED`（SKIP 未计 PASS）。
- 旧 `win32_isolation`：**21/21 PASS**（管理员环境，DACL 恢复权限前提满足）。

## 对照

知微**未提升**环境同一 commit：`win32_isolation = 20/20 PASS [1 NOT_APPLICABLE]` ⇒ 总体
`NOT_EVALUATED`。两份记录**分别如实保留，互不替代**。

> 说明：本包为船长终端输出的**文本登记**（船长未提供机器原生 JSON 附件）。
> 知微侧的原生 JSON 证据包见同级目录 `../REQ2_zhiwei_5fda429_20261012/`。
