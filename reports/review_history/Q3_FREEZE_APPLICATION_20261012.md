# Q3 最终冻结申请（Q3 FINAL FREEZE APPLICATION）

**申请人**: Coder
**日期**: 2026-10-12
**版本**: v2（据凌翼 Q3 EVIDENCE ARCHIVE REVIEW 更新）
**收件**: 凌翼（主裁）；抄送：睫、知微、钳星、船长
**依据**:
- 凌翼 EVIDENCE RECEIPT REVIEW（REVIEWED_HEAD `5271b22`）
- 凌翼 Q3 EVIDENCE ARCHIVE REVIEW（2026-10-12）
> "下一步，我们可以让 Coder 提交一份 Q3 最终冻结申请，固定候选 commit、Profile B 的有限证明范围、
>  原始证据索引、剩余问题和独立评审意见。我将只针对最终资格作裁决，不重新打开已经关闭的归档缺陷。"

**本申请固定以下四要素**：① 候选 commit ② Profile B 有限证明范围 ③ 原始证据索引 ④ 剩余问题 + 独立评审意见。

**状态声明**: 本申请**请求**冻结裁决；Coder **不**自行冻结。
`Q3_DESIGN_FREEZE = NOT YET AUTHORIZED`；`SCIENTIFIC_EXECUTION = MAY NOT START`。

---

## §0 归档缺陷状态（凌翼已关闭，本申请不重开）

- 凌翼 Q3 EVIDENCE ARCHIVE REVIEW：`NATIVE_EVIDENCE_ARCHIVE = ACCEPTED`；
  `PREVIOUS ARCHIVE-MISSING OBSERVATION = CLOSED`。
- 独立字节复核：GitHub 文本 hash `13/13` 匹配；空 stderr `3/3` 匹配；原始 ZIP sha256 匹配；
  ZIP 中央目录有效（13 条目）。
- **双层哈希**（不可混用）：ZIP 内为**原始 CRLF 层**（`SHA256SUMS.json` 记录）；
  GitHub 展开为 **LF 存储层**（`evidence/INDEX.md` 记录）。Coder 复核 ZIP 内 12 条目
  **全部匹配**其 `SHA256SUMS.json`；两层对同一内容 hash 不同系字节表示不同，**非篡改**。
- **证据层级**（如实标注，不强行等同格式）：
  船长包 = `TERMINAL_TEXT`；知微包 = `NATIVE_JSON + ORIGINAL_ZIP`。

## §1 候选标识

| 项 | 值 |
|---|---|
| **Q3 candidate commit** | `5271b22`（申请时 GitHub `main` HEAD） |
| **复跑固定 commit** | `5fda429`（已独立复跑；此后未动 Q3 执行关键源码） |
| **Q3 执行关键源码漂移** | **NONE FOUND**（凌翼已核；`5271b22` 仅 .gitignore / 索引 / 复跑记录变更） |
| **Q3_LINEAGE_DIGEST** | `b4172b73385cf0139178f21d1e9e6b3d07413af5441b17cdaea51e2849a7653f` |
| **活动 handle-isolation profile** | `API_NO_INHERIT_PROFILE` v `1.0`（Profile B） |
| **RC11 冻结对象** | MANIFEST `78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059`（28142 B）—— **未改动** |

## §2 拟冻结的 Q3 执行关键源码（精确哈希）

以下 SHA-256 为**LF 归一后**字节。冻结即锁定这 11 个文件。

| 文件 | bytes | sha256 |
|---|---|---|
| `q3_contract.py` | 11218 | `84081a36affa6a585b7dad7990609399c96361311a794d514f9f042126d4afe7` |
| `q3_access_matrix.py` | 14221 | `f9f6969516a25c64964430967654662d82645d9d6557d9b983e917a0e6c10a1f` |
| `q3_dacl.py` | 16085 | `d2a0c58ac0a9f54da0dad5a158113bef4af1b08475d7bf58940b54c65f745dad` |
| `q3_handle_audit.py` | 17116 | `7abfa23364dbdaf8268b824b96d852b9567c1d25976d065a534c68e6b3505591` |
| `q3_reset_chain.py` | 73483 | `b641f6cba4c88c0ac98baac5440386c2f4f47b55a39bca17e18e64c2712e6974` |
| `win32_isolation.py` | 30287 | `9108066fda402ac137aaa7ce258e7fb9349b59f37950f5a3f8f82d88c7dace7b` |
| `win32_worker_process.py` | 21443 | `a34aebd23cb82b91c3c15b9e369ea2afe25599a018b3fdaa1898432ca9e2857c` |
| `q3_qualify.py` | 13653 | `804101a45e3598b20b1c240d0f6aca8f03f023f4af456b87dc7895f70cac9b69` |
| `q3_adversarial.py` | 14293 | `c7d2e007b48d090d4fe5a0283d714d7584a6ff9bf5084da460ab68432fff9de4` |
| `q3_provenance.py` | 9743 | `78063a6f815bf140036f1e9405926310858316ce0fb5127a9e41ecf123afe9a2` |
| `qualification_binding_rc12.py` | 7480 | `203ce8fab04df3d66f474cd2b3d2198d765fd553361ea1c24d68ce72eb8e91f7` |

> 分离记录：`reports/Q3_PROVENANCE_DETACHED_20261011.txt`（Q3 10 角色 + RC11 20 角色 recompute）。

## §3 证据哈希（已归档）

| 证据 | 位置 | 哈希 |
|---|---|---|
| 睫独立核验签署原件 | `review_history/睫_独立核验签署_20261012.md` | （见 evidence/INDEX） |
| 船长管理员复跑 | `review_history/evidence/REQ2_captain_admin_5fda429_20261012/raw_terminal_output.txt` | `d998177a43f1f114ab63d55a891aea39f455db0036a9befa0a5a29ca8d6c1d55` |
| 知微未提升复跑（原生包） | `review_history/evidence/REQ2_zhiwei_5fda429_20261012/` | 见 `evidence/INDEX.md`（含 `SHA256SUMS.json` 12/12 复核） |
| 原生证据包总索引 | `review_history/evidence/INDEX.md` | （含全部哈希） |

- 船长轮 FULL_VALID run-id：`f1e7d60479f94d80be61a105ed1ffedf`
- 知微轮 FULL_VALID run-id：`2d17082df94649f199945f6ecc0acc57`

## §4 通过项（development + 独立复跑）

```
Q3_QUALIFICATION = PASS (管理员, 5fda429)
  q3_access_matrix      14/14
  q3_dacl               14/14
  q3_adversarial        50/50
  q3_provenance         10/10
  win32_isolation       21/21 (管理员)  /  20/20 + 1 N/A (未提升)
  win32_worker_process   4/4
  q3_handle_audit        5/5
  q3_reset_chain        85/85
  q3_qualify --selftest 17/17
  FULL_VALID_SUCCESS_PATH = PASS (profile=API_NO_INHERIT_PROFILE v=1.0, run_id 绑定)
verify_manifest_binding  = BINDING_INTEGRITY PASS
```

## §5 尚存 blocking（申请人判定：**0 项阻塞冻结**）

| # | 项 | 级别 | 状态 |
|---|---|---|---|
| — | 凌翼二轮 4 项 P1（Profile B 证据链 / 矩阵 / FULL_VALID / DACL+provenance） | P1 | ✅ 已闭合 |
| — | 知微 P1（FULL_VALID 消费门禁） | P1 | ✅ 已闭合（schema/布尔/profile/run-id） |
| — | 睫 OBS-1 / OBS-2 | RC11 层 | 交凌翼（勘误已附 / RC12 候选已建） |
| — | 睫 OBS-3 | 导航件 | ✅ 已闭合 |
| — | 睫 OBS-4 | 外部元数据 | 当前不复现 |

**非阻塞观察（供参考，不请求处理）**：
- `win32_isolation` 旧 `restore_dacl` 需管理员/还原特权；未提升环境该项 **NOT_APPLICABLE**（已如实分类）。

## §6 独立评审意见（原始件已归档，供凌翼直接核）

| 评审者 | 范围 | 结论 | 原件位置 |
|---|---|---|---|
| **睫**（Jie） | RC11 reference harness：**字节 + 执行**级独立复现 | `PHASE_A_HARNESS_QUALIFICATION = PASS`；声明 Windows 层 `ATTESTED_ONLY`（其沙盒为 Linux），**不签** Q3 冻结 | `review_history/睫_独立核验签署_20261012.md` |
| **船长**（荣弦） | Q3 Windows：管理员环境，当前 commit `5fda429` 复跑 | `Q3_QUALIFICATION = PASS`（有口令）/ `NOT_EVALUATED`（无口令） | `evidence/REQ2_captain_admin_5fda429_20261012/`（`TERMINAL_TEXT`） |
| **知微**（Zhiwei） | Q3 Windows：未提升环境，当前 commit `5fda429` 复跑 | FULL_VALID `PASS`；总体 `NOT_EVALUATED`（唯一未评估项=旧 DACL 恢复权限前提） | `evidence/REQ2_zhiwei_5fda429_20261012/`（`NATIVE_JSON + ORIGINAL_ZIP`） |
| **凌翼**（主裁） | 证据归档字节级复核 | `NATIVE_EVIDENCE_ARCHIVE = ACCEPTED`；`13/13 + 3/3 + ZIP` 匹配；归档缺陷 `CLOSED` | 本申请 §0 所引裁决 |

> **权限差异被如实保留**：同一 commit，管理员 → `PASS`，未提升 → `NOT_EVALUATED`；
> **未**把知微的 SKIP 改写为 PASS，**未**用未提升结果否定管理员实测。两种上下文互不替代。

## §7 适用范围（拟冻结的边界，务必精确）

- **Q3 = QUALIFIED_ON_CONTROLLED_CANARY_OBJECTS**（受控 canary 对象）；真实 Phase-B 对象须后续绑定。
- **Profile B 的主张范围**（原样）：仅证明"**新 worker 未继承禁用句柄**"；
  **不**主张"worker 绝不以其他方式取得目标句柄"。
- **`runtime_handle_audit`**：保持原样（CLEAN 或 UNRESOLVED **不改写**）；`FOUND_TARGET` 恒 INVALID。
- **信任边界（有限）**：Trusted Computing Base = 运行中的 Windows OS + 受信 controller/observer +
  授权执行环境；**不**证明 Windows 内核本身无瑕。
- **平台**：Windows。**RC11 Phase A** = CLOSED/HISTORICAL，本申请**不**触及 RC11。

## §8 请求裁决

请凌翼就以下作出裁决：

1. **是否授权冻结 Q3 candidate**（锁定 §2 的 11 个文件哈希 + §1 的 lineage digest）？
2. **冻结后是否安排最终 qualification run**（在冻结的精确源码上、管理员环境，记录 run-id + FULL_VALID 产物）？
3. **RC12** 是继续并行推进，还是暂缓至 Q3 冻结后？

> Coder 不自行冻结、不自行点火。待凌翼裁定后按令执行。
