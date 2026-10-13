# 证据包：Q3 reset adapter 隔离原型（REQ_adapter_153a86f_20261013）

**lineage**: `Q3_RESET_ADAPTER_INTEGRATION_V1`
**git HEAD**: `153a86f84ee747ff99f51a3bac94c9136b450c5b`
**日期**: 2026-10-13
**授权**: 凌翼 `LINGYI Q3 RESET ADAPTER V3 REVIEW` — `DESIGN_V3 = ACCEPTED AS PROTOTYPE BASELINE`；`ISOLATED_PROTOTYPE_IMPLEMENTATION = AUTHORIZED`。
**状态**: `REAL_EXECUTION_WIRING = NOT AUTHORIZED`；`SCIENTIFIC_EXECUTION = MAY NOT START`。

---

## 1. 这个包里有什么

| 文件 | 内容 |
|---|---|
| `raw_regression_output.txt` | `test_q3_reset_adapter.py` 的**完整原始控制台输出**（三层 A/B/C，23/23 PASS，exit 0） |
| `raw_verify_q3_freeze.txt` | `verify_q3_freeze.py` 原始输出（`Q3_FROZEN_IDENTITY = OK` + 交叉核对 OK） |
| `EVIDENCE.txt` | 本包概要：git HEAD、三个新文件的 LF-canonical SHA256、冻结父身份（RC11/Q3 digest） |

**新增源码**（在 `afterglow_harness/`，**未**触碰 RC11 / Q3 冻结十角色）：

| 文件 | sha256 (LF) | bytes |
|---|---|---|
| `q3_reset_adapter.py` | `4e5a48287439eb6bb1ef744ba36a88d8867da99ff4b175b5da42840359f01e3d` | 33303 |
| `test_q3_reset_adapter.py` | `6f6cff26a2d93802225c6fad0494c928b892c06caae6e26f1cbeb4fbe7a381c6` | 16549 |
| `q3_business_worker_entry.py` | `3b3ba34f875d669fa6197493c208b51e4fcd12c20185616573ba08dba5e2e79b` | 3699 |

**冻结父身份（不变）**：RC11 MANIFEST `78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059`（28142 B）；Q3 digest `45034911…`；`FROZEN_CODE_COMMIT = 2c92074…`。

---

## 2. 复现步骤（三方各跑一遍）

```powershell
# 1) 取冻结身份
cd <repo>/afterglow_harness
D:\qcr\EntropyDrivenAI\.venv\Scripts\python.exe verify_q3_freeze.py
#   期望: Q3_FROZEN_IDENTITY = OK (+ cross-check OK)

# 2) 运行适配器三层回归（真实跨账户需要凭据）
$env:AFTERGLOW_WORKER_PASSWORD = (Get-Content <path>\.secrets\afterglow_worker.txt)
D:\qcr\EntropyDrivenAI\.venv\Scripts\python.exe test_q3_reset_adapter.py
#   期望: ADAPTER_REGRESSION = PASS, exit 0
#   （若无凭据：Layer A/B 仍跑，Layer C SKIP => 退出码 2 = PARTIAL，不是 pass）
```

> **注意**：Layer C 需要 `AFTERGLOW_WORKER_PASSWORD`。若调用账户无法 `CreateProcessWithLogonW`
> （例如以 `nt authority\system` 运行），Layer C 会 **SKIP**（退出码 2），**不是** pass。

---

## 3. 请三位定向复核的关注点（凌翼指定）

### 睫 —— 证明语义 / 冻结边界
- Layer B 的负向是否**真的**"在冻结 Q3 计算前改输入而失败"，而非构造假结果？（看 `_call_q3_chain()` seam + 测试注入点）
- `r.valid is True` 合取是否**不可绕**（第 191 句）？`Q3_OK` 中间态是否**从不**被当成功消费？
- `REAL_RESET` 门禁是否确实挡住合法 `FIRST_START` 冒充（A2）？
- 对象绑定是否用 **OS 文件身份**（B1 拒绝 / B2 硬链接接受）？

### 知微 —— 独立 Windows 重放
- 独立重放本回归（含 Layer C 真实跨账户：worker SID ≠ 控制器）。
- 核对 DACL 时序（`_stage_boundary` 装 deny ACE → worker holding → 隔离证明 → release）。
- 失败回收：业务 worker 已启动但隔离失败时是否**及时终止 + 关句柄 + 失败产物不可再消费**。
- **已知诚实标注**：Layer C 在 `administrator` 下、以 `CreateProcessWithLogonW` 创建 `afterglow_worker`；须你独立确认这是**真实跨账户**。

### 钳星 —— 生命周期 / 失败安全
- holding→release 握手是否确保**隔离验收前业务代码不处理真实输入**（约束 #1）。
- `BusinessWorkerSupervisor` 是否**真实持有并核验** OS 身份/生命周期/资源（不是 `identity_bound=True` 布尔）。
- `terminate()` 幂等 + 无残留活进程；`_fail()` 单一失败契约（约束 #4/#5）。

---

## 4. 已知边界 / 不声称的内容

- **不是**最终 Windows 验收：Layer C 是原型级跨账户验证，须由知微独立重放确认。
- **不接线**：`REAL_EXECUTION_WIRING = NOT AUTHORIZED`。
- **不主张**：旧 worker PID 由 supervisor 权威持有（当前测试未跑真实旧 worker 终止路径，`old_worker_pid` 绑定就位但未在 C 层实测）。— 这是一个**已知待补**的用例，供钳星/知微点名。
- **不重跑冻结 Q3**：新证据只针对新增适配器 + 真实业务 worker（凌翼）。
