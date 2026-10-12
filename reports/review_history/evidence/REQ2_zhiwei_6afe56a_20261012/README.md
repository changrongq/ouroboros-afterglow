# 独立复跑证据 — 知微（未提升）@ 6afe56a

**固定对象**: `6afe56a37865e965eebcdb1ee81b5e7c051b2767`（v5 候选）
**执行/记录**: 知微
**日期**: 2026-10-12
**脱敏**: 不含明文口令（仅出现环境变量名 `AFTERGLOW_WORKER_PASSWORD`）。

## 结果（未提升令牌, admin_token=false）

| 轮次 | 结果 | exit | run-id |
|---|---|---|---|
| 冻结基线 | BINDING_INTEGRITY = PASS | 0 | — |
| 有口令 | FULL_VALID=PASS；总体 **NOT_EVALUATED** | 2 | `2f16f3aff9e741b6ada3323bea5cc51e` |
| 去口令 | FULL_VALID=SKIP；总体 **NOT_EVALUATED** | 2 | `7ab4e25622fe45b3955c27c4511c8445` |

- `q3_reset_chain 113/113`、`q3_adversarial 61/61`、`q3_provenance 13/13`、
  `q3_qualify --selftest 17/17`、worker 4/4、handle audit 5/5。
- 唯一未评估项：旧 `win32_isolation` DACL 恢复**权限前提**（`20/20 PASS [1 NOT_APPLICABLE]`）
  ⇒ 组件 SKIP ⇒ 总体 exit 2。**非 FAIL，也不记为完整 PASS。**
- `artifact_run_id_matches = true`（FULL_VALID 产物 run_id 与入口一致）。

## 独立字节核对（知微侧）

- `independent_role_hashes.json`：十角色 **10/10 匹配**；
  `computed_digest == declared_digest == 10c4548e6192490aafc156e0d354c2ace93334bcfddb1d9c4d2e71cd5292ccc6`。
- `SHA256SUMS.json`：Coder 复核 **13/13 匹配**。
- `source_hashes_before.json`：执行前后源码 hash 一致（源码零修改）。

## 文件

| 文件 | 说明 |
|---|---|
| `给Coder_固定6afe56a复跑记录_20261012.md` | 知微报告正文 |
| `snapshot.json` | 固定对象（commit `6afe56a…`；GitHub API pin + codeload） |
| `results.json` | 命令、退出码、run-id、结论 |
| `independent_role_hashes.json` | **知微独立重算**的十角色 hash + digest |
| `source_hashes_before.json` | 执行前源码 SHA-256（零修改证据） |
| `full_valid_with_credential.json` | 本轮 FULL_VALID 产物（run_id `2f16f3af…`） |
| `run_fixed_replay.py` | 记录器（无内置口令） |
| `logs/*.stdout.log` / `logs/*.stderr.log` | binding / with_credential / without_credential 原始输出 |
| `SHA256SUMS.json` | 包内自校验 |
| `received_original.zip` | 收到的原始 zip（原件留存） |

> 归属：本包 = **知微（未提升）** 上下文；管理员上下文见 `../REQ2_captain_admin_*`。
> 两份**分别如实保留，互不替代**。
