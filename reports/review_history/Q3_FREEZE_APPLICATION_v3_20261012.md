# 给凌翼：Q3 最终冻结申请 v3 —— B1/B2 证明缺口闭合 + B3 血统边界整理

**报告人**: Coder
**日期**: 2026-10-12
**依据**: 凌翼 Q3 FREEZE ADJUDICATION（2026-10-12, REVIEWED_HEAD `281704f`）
**新 blocking 处置**: B1 = LEAK_POSITIVE_CONTROL_NOT_ACTUALLY_EXERCISED / B2 = REAL_RESET_SUCCESS_PATH_NOT_DEMONSTRATED / IDENTITY = Q3 10 vs RC12 separate
**RC11 冻结对象**: MANIFEST `78bdb90f…`（28142 B）—— **未改动**

---

## 一句话结论

凌翼指出的**两处证明缺口 + 一处血统边界**已**真正闭合**：B1 现在是一次**真实的句柄泄漏正对照**（子进程实际继承 + 探针识别 + 注册路径对照）；B2 现在是一条**真实 reset 成功链**（旧 worker 真实存在 → 清除动作实际删除 → 新 worker → 全链 VALID）；B3 已把 Q3（10 角色）与 RC12（独立血统）**机器强制分离**。

---

## §1 B1：泄漏正对照「真的发生了」

**凌翼的判据**：旧版只"打开了可继承句柄就关闭"，证明的是 `controller_opened_inheritable_handle`，**不是**"检测器能发现一次真实泄漏"。

**已修**（`win32_worker_process.leak_positive_control`，**真两轮实验**）：

| 轮次 | 做什么 | 预期 | 实测 |
|---|---|---|---|
| **POSITIVE** | controller 持有可继承句柄 → 用 `CreateProcessW(bInheritHandles=TRUE)` 启动子进程 → **子进程存活期间**枚举其句柄表 | 必须 `HANDLE_AUDIT_FOUND_TARGET`（检测器看见真实泄漏） | ✅ `detected=True` |
| **NEGATIVE** | 同一可继承句柄 → 用**注册路径** `CreateProcessWithLogonW`（无句柄列表）启动 → 审计 | 必须 NOT FOUND | ✅ `clean=True`（`HANDLE_AUDIT_CLEAN`） |

- 实测 detail：`positive(inheriting child) detected=True [HANDLE_AUDIT_FOUND_TARGET]; negative(registered API) clean=True [HANDLE_AUDIT_CLEAN]`
- `ok = detected AND neg_clean` ⇒ 现在是**真命题**，不是恒真。
- 调试中还修了一个真实陷阱：禁止对象的 `CreateFileW` 若 `share=0`，会把审计自身的身份读取挡掉（假 `HANDLE_AUDIT_ERROR`）；已加 `FILE_SHARE_READ|FILE_SHARE_WRITE`。
- **正对照与正式路径分离**：控制泄漏发生在**一次性子进程**里，不碰正式 worker 隔离路径。

## §2 B2：真实 reset 成功链

**凌翼的判据**：旧版成功路径里 clear target 在调用**之前**就被 `unlink`，且没有 old worker（首启 N/A），**不能**证明 reset 本身完成了清除与更替。

**已修**（`q3_reset_chain` 新增 `clear_action` 回调 + `real_reset_*` 门禁）：

- 新门禁：只要给了 `clear_action` **或** `old_worker_pid`，就要求 `real_reset_required=True`，且
  `real_reset_ok = clear_action_ran AND lifecycle_ok AND clear_ok`，并 AND 进 `.valid`。
- **新增真实成功链自测**（全部通过）：
  1. clear targets **reset 前真实存在**（未预删）；
  2. **真实 old worker 进程存活**（`subprocess.Popen`）；
  3. reset **动作**（`clear_action`）**实际删除** targets（`clear_action_ran=True`）；
  4. **可信 observer 事后验证** targets 已消失（`clear_ok=True`）；
  5. old worker **真实终止**（`lifecycle_ok=True`，`taskkill` 后 `poll() is not None`）；
  6. **整链 `res_b2.valid is True`**。
- 负例：无 `clear_action` 且无 old worker ⇒ `real_reset_required=False`（N/A 不误判）。

## §3 B3：冻结身份边界（Q3 10 / RC12 独立）

**凌翼的判据**：申请 §2 列了 11 文件（含 `qualification_binding_rc12.py`），而 `q3_provenance.Q3_EXECUTION_CRITICAL` 只有 10 ⇒ 把两个血统放进同一张冻结清单。

**已修**：
- **机器强制**：`q3_provenance.assert_lineage_boundary()` —— 要求 `Q3_EXECUTION_CRITICAL` **恰 10 个**且**不含** `FOREIGN_LINEAGE_MODULES`（= RC12 模块）。13/13 自测含 B3 断言。
- **冻结申请 v3 §2 只列 10 个 Q3 角色**；`qualification_binding_rc12.py` 移入 **RC12 独立血统**（单独 hash，不并入 Q3 digest）。
- **Q3_LINEAGE_DIGEST 只按 10 个 Q3 文件生成**（不含 RC12）。

---

## §4 冻结清单（v3：Q3 = 10 角色）

| 文件 | bytes | sha256 |
|---|---|---|
| `q3_contract.py` | 11218 | `84081a36affa6a585b7dad7990609399c96361311a794d514f9f042126d4afe7` |
| `q3_access_matrix.py` | 14221 | `f9f6969516a25c64964430967654662d82645d9d6557d9b983e917a0e6c10a1f` |
| `q3_dacl.py` | 16085 | `d2a0c58ac0a9f54da0dad5a158113bef4af1b08475d7bf58940b54c65f745dad` |
| `q3_handle_audit.py` | 17116 | `7abfa23364dbdaf8268b824b96d852b9567c1d25976d065a534c68e6b3505591` |
| **`q3_reset_chain.py`** | 80597 | `b9604815ee3dbafd2e5f0a4debdf107f9e9c7344c96998cfda40ae83bcb8b244` |
| `win32_isolation.py` | 30287 | `9108066fda402ac137aaa7ce258e7fb9349b59f37950f5a3f8f82d88c7dace7b` |
| **`win32_worker_process.py`** | 25722 | `cff8412a0204fe85001a341d85a71ac35c76ab76f0e1f09688524f5dc19b86ee` |
| `q3_qualify.py` | 13653 | `804101a45e3598b20b1c240d0f6aca8f03f023f4af456b87dc7895f70cac9b69` |
| **`q3_adversarial.py`** | 15736 | `eba518c096200858a4d70ce13fd8b7716203ae203014e0a8caf88a3eba5fbf7e` |
| **`q3_provenance.py`** | 11369 | `a0a89f3c140e500216b58d90687a006d2888f90b3e2143c0c21e4fb5e79ba5f0` |

- **`Q3_LINEAGE_DIGEST = d2d282298d01c0cadbb87d5823ea416c136792ce2da86940b174bafd2cda0ff2`**（仅这 10 个）
- **RC12（独立血统，不并入 Q3）**：`qualification_binding_rc12.py` 7480 B `203ce8fab04df3d66f474cd2b3d2198d765fd553361ea1c24d68ce72eb8e91f7`

## §5 定向回归（B1/B2/B3 相关）

- `q3_reset_chain`：**97/97**（新增 B1 三轮 + B2 真实链 8 项断言）。
- `q3_adversarial`：**57/57**（新增 A33 系列 B2 门禁、A34 系列 B3 边界）。
- `q3_provenance`：**13/13**（新增 B3 断言）。
- 全量 `Q3_QUALIFICATION = PASS`（8 组件 + 消费门禁 17/17）。

## §6 未变

- **B1/B2 之外**未重开任何已闭合项（知微 P1 / 二轮 4 P1 / 归档均保持 CLOSED）。
- RC11 字节未动；`verify_manifest_binding = BINDING_INTEGRITY PASS`。

## §7 请凌翼裁决

1. **B1/B2/B3 是否接受闭合**，可否授权冻结 Q3 candidate（锁定 §4 的 **10 个**哈希 + lineage digest）？
2. 冻结后按已批准的 `POST_FREEZE_QUALIFICATION_PROCEDURE` 在管理员环境运行最终 qualification？
3. RC12 并行推进按已批准节奏继续（本申请不含 RC12 角色）？

> Coder 不自行冻结、不自行点火。
