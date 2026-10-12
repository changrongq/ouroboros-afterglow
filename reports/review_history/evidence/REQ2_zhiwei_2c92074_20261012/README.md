# 独立资格复跑证据 — 知微（未提升）@ 2c92074（BD-76 修复后）

**固定对象**: `2c92074a9808b1c9acd5ad5a36cba7a34e472892`
**执行/记录**: 知微
**日期**: 2026-10-12
**脱敏**: 不含明文口令（仅出现环境变量名 `AFTERGLOW_WORKER_PASSWORD`）。

## 结果（未提升令牌, admin_token=false）

| 轮次 | 结果 | exit | run-id |
|---|---|---|---|
| 冻结基线 | BINDING_INTEGRITY = PASS | 0 | — |
| 有口令 | FULL_VALID=PASS；总体 **NOT_EVALUATED** | 2 | `ecf37248756346cdaeb35e73eb6aab11` |
| reset_detail | 真实端到端 **fully VALID** | 0 | — |
| provenance_detail | **18/18 PASS**（含 BD-76） | 0 | — |
| 去口令 | FULL_VALID=SKIP；总体 **NOT_EVALUATED** | 2 | `3f53726ecf7b40109ab8edb76195e87d` |

- `q3_reset_chain 120/120`、`q3_adversarial 65/65`、`q3_provenance 18/18`、
  `q3_qualify --selftest 17/17`、worker 4/4、handle audit 5/5。
- 唯一未评估项：旧 `win32_isolation` DACL 恢复**权限前提**（`20/20 PASS [1 NOT_APPLICABLE]`）
  ⇒ 组件 SKIP ⇒ 总体 exit 2。**非 FAIL，也不记为完整 PASS。**

## 独立字节核对（知微侧）

- `independent_role_hashes.json`：十角色 **10/10 匹配**；
  `computed_digest == declared_digest == 450349115b71bc9013c7a79f91d9bdf5f1728f2cbae65b025eb35a66af56da36`。
- **`comparison.json`**：独立验证 `a47970b → 2c92074` 的变化**仅 `q3_provenance.py`**，
  **其余九个未变**（`other_nine_unchanged = true`）。
- `SHA256SUMS.json`：Coder 复核 **20/20 匹配**。
- `source_hashes_before.json`：执行前后源码 hash 一致（源码零修改）。

## BD-76 定向证据（`negative_controls.json` + `logs/provenance_detail.stdout.log`）

知微在**原版组件自测**上实机复核并确认：

- **BD-76 五条**：`bd76_five_pass = true`
  （RC12 折入 ⇒ `q3_lineage_digest` RAISES；`write_detached_record` RAISES；
   违例不写记录；9 角色 ⇒ RAISES；原集合恢复生成）。
- **V5-N1/N2**：`v5_seven_pass = true`。
- **V4-B1/B2/B3**：`v4_observed_pass = true`。
- `reset_detail`：真实 reset 链 **fully VALID** + `old worker terminated`。

## 文件

| 文件 | 说明 |
|---|---|
| `给Coder_固定2c92074知微资格复跑_20261012.md` | 知微报告正文 |
| `snapshot.json` / `results.json` | 固定对象 + 命令/退出码/run-id |
| `independent_role_hashes.json` | 知微独立重算的十角色 hash + digest |
| `comparison.json` | `a47970b→2c92074` 变更范围（仅 provenance） |
| `negative_controls.json` | BD-76 + V5-N1/N2 + V4-B1/B2/B3 实机负例 |
| `full_valid_with_credential.json` / `full_valid_reset_detail.json` | 本轮 FULL_VALID 产物 |
| `source_hashes_before.json` | 执行前源码 SHA-256（零修改证据） |
| `run_replay.py` | 记录器（无内置口令） |
| `logs/*.stdout.log` / `logs/*.stderr.log` | binding / with_credential / reset_detail / provenance_detail / without_credential 原始输出 |
| `SHA256SUMS.json` | 包内自校验 |
| `received_original.zip` | 收到的原始 zip（原件留存） |

> 归属：本包 = **知微（未提升）** 上下文；管理员上下文见 `../REQ2_captain_admin_2c92074_20261012/`。
> 两份**分别如实保留，互不替代**。
