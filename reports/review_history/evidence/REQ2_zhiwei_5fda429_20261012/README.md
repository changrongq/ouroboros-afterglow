# REQ-2 原生证据包 — 知微（未提升）当前提交复跑

**提交**: `5fda4298772a69d850d0d3bfe898c5cce546dcc8`
**执行/记录**: 知微
**日期**: 2026-10-12
**脱敏声明**: 本包 **不含** 任何 worker 明文口令。凭据仅通过测试进程环境变量
`AFTERGLOW_WORKER_PASSWORD` 注入；本包仅出现该**变量名**，不出现其值。
已由 Coder 扫描确认（无字面口令命中）。

## 文件清单（`SHA256SUMS.json` 为包内自校验）

| 文件 | 说明 |
|---|---|
| `给Coder_REQ2当前提交复跑_20261012.md` | 知微报告正文（原样） |
| `snapshot.json` | 复跑对象固定（commit `5fda429…`；GitHub API pin + codeload 快照） |
| `results.json` | 命令、退出码、run-id、结论 |
| `source_hashes_before.json` | 复跑前源码 SHA-256（177 项；证明未改源码字节） |
| `full_valid_with_credential.json` | 本轮 FULL_VALID 产物（run_id `2d17082d…`；8 门禁全 true；pre_reset_observed=READ=GRANTED） |
| `run_req2.py` | 复跑脚本（凭据仅经 env 注入） |
| `logs/binding.stdout.log` | 冻结基线原始输出 |
| `logs/with_credential.stdout.log` | 有口令轮原始输出 |
| `logs/without_credential.stdout.log` | 去口令轮原始输出 |
| `logs/*.stderr.log` | 各轮 stderr（均空） |
| `SHA256SUMS.json` | 包内文件 SHA-256（Coder 复核：12/12 匹配） |

## 关键结果（供凌翼核对）

- 有口令轮：FULL_VALID = PASS（run_id `2d17082d…`）；旧 `win32_isolation` 为
  `20/20 PASS [1 NOT_APPLICABLE]`（DACL 恢复权限前提）⇒ 组件 SKIP ⇒ 总体 **NOT_EVALUATED**。
- 去口令轮：worker / reset chain / FULL_VALID 明确 SKIP ⇒ 总体 **NOT_EVALUATED**。
- 与船长**管理员**轮（同一 commit）对照：管理员 ⇒ `21/21 PASS` ⇒ 总体 **PASS**。
  两种权限上下文**分别如实保留，互不替代**。

## Coder 复核

- 包内 `SHA256SUMS.json`：**12/12 匹配**。
- 口令扫描：**无字面命中**（仅变量名）。
- 未改任何源码字节；该包为**只读归档**。
