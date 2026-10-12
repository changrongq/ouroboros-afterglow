# 独立资格复跑证据 — 知微（未提升）@ a47970b（v6）

**固定对象**: `a47970b205022b2e15abdca5d2999a13bdb2a1e0`（v6 候选）
**执行/记录**: 知微
**日期**: 2026-10-12
**脱敏**: 不含明文口令（仅出现环境变量名 `AFTERGLOW_WORKER_PASSWORD`）。

## 结果（未提升令牌, admin_token=false）

| 轮次 | 结果 | exit | run-id |
|---|---|---|---|
| 冻结基线 | BINDING_INTEGRITY = PASS | 0 | — |
| 有口令 | FULL_VALID=PASS；总体 **NOT_EVALUATED** | 2 | `07251e7445b740c0843941551140e5b1` |
| reset_detail（真 reset 链） | 真实端到端 **fully VALID** | 0 | — |
| 去口令 | FULL_VALID=SKIP；总体 **NOT_EVALUATED** | 2 | `bf0de5b560db4dbf858473dc4b96d2eb` |

- `q3_reset_chain 120/120`、`q3_adversarial 65/65`、`q3_provenance 13/13`、
  `q3_qualify --selftest 17/17`、worker 4/4、handle audit 5/5。
- 唯一未评估项：旧 `win32_isolation` DACL 恢复**权限前提**（`20/20 PASS [1 NOT_APPLICABLE]`）
  ⇒ 组件 SKIP ⇒ 总体 exit 2。**非 FAIL，也不记为完整 PASS。**

## 独立字节核对（知微侧）

- `independent_role_hashes.json`：十角色 **10/10 匹配**；
  `computed_digest == declared_digest == ab12c396dee8c7eb9e28120732e8c8f17842e4f12344dd40d45d25781a206c50`。
- `SHA256SUMS.json`：Coder 复核 **17/17 匹配**。
- `source_hashes_before.json`：执行前后源码 hash 一致（源码零修改）。

## 定向负例独立复核（`negative_controls.json`）

知微在**原版组件自测**上实机复核并确认：

- **V5-N1/N2**（本合同启动前强制新增）：`v5_all_pass = true`（7 条全 PASS）。
- **V4-B1/B2/B3**：`v4_all_observed_pass = true`（10 条全 PASS）。
- `reset_detail`（`logs/reset_detail.stdout.log`）：真实 reset 链
  `real end-to-end run fully VALID` + `B2: old worker terminated` ⇒ 真实 lifecycle 达成。

## 文件

| 文件 | 说明 |
|---|---|
| `给Coder_固定a47970b知微资格复跑_20261012.md` | 知微报告正文 |
| `snapshot.json` / `results.json` | 固定对象 + 命令/退出码/run-id |
| `independent_role_hashes.json` | 知微独立重算的十角色 hash + digest |
| `negative_controls.json` | V5-N1/N2 + V4-B1/B2/B3 实机负例 |
| `full_valid_with_credential.json` / `full_valid_reset_detail.json` | 本轮 FULL_VALID 产物 |
| `source_hashes_before.json` | 执行前源码 SHA-256（零修改证据） |
| `run_replay.py` | 记录器（无内置口令） |
| `logs/*.stdout.log` / `logs/*.stderr.log` | binding / with_credential / reset_detail / without_credential 原始输出 |
| `SHA256SUMS.json` | 包内自校验 |
| `received_original.zip` | 收到的原始 zip（原件留存） |

> 归属：本包 = **知微（未提升）** 上下文；管理员上下文见 `../REQ2_captain_admin_a47970b_20261012/`。
> 两份**分别如实保留，互不替代**。
