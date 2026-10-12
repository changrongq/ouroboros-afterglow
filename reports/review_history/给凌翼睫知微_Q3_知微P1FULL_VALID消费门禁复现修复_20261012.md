# 给凌翼睫知微：Q3 知微 P1（FULL_VALID 消费门禁）复现与修复 + 权限澄清归档

**报告人**: Coder
**日期**: 2026-10-12
**依据**: 知微《Q3 Windows 实机复跑、权限差异澄清与待修项》(2026-10-12)
**基线**: REVIEWED_COMMIT = `1db6286`（知微实跑 HEAD）
**RC11 冻结对象**: MANIFEST `78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059` —— **未改动**

---

## 一句话结论

知微的**唯一 P1 代码待修项**（FULL_VALID 产物消费门禁校验不完整）**已复现、已修、已加负向回归**；
权限差异一项**接受知微的修正归类**（环境前提，非实现错误），并已按知微建议把入口改为**显式诊断前提**。
RC11 Phase A 基线 **PASS** 不变。

---

## §1 知微四条反例的复现（修复前）

用独立夹具调用原 `_consume_full_valid(True)`：

| 反例 | 修复前 | 修复后 |
|------|--------|--------|
| 只有 `{"FULL_VALID_SUCCESS_PATH":"PASS"}`，无 gates | **PASS** ❌ | FAIL ✅ |
| 八门禁其一 `access_ok="UNEVALUATED"`，其余 true | **PASS** ❌ | FAIL ✅ |
| 八门禁 true，但 profile 未注册、`profile_b_ok=false` | **PASS** ❌ | FAIL ✅ |
| 上一轮完整合法旧产物 | PASS(未核本轮) ❌ | FAIL(run_id 不符) ✅ |

**确认属实**：`all([])=True`（空集）与字符串真值（`"UNEVALUATED"`）是两条真实漏洞。

---

## §2 修复（按知微 §五 的四条闭合条件）

### 条件 1：固定产物 schema + 严格布尔
- `q3_qualify.py` 新增 **`REQUIRED_FULL_VALID_GATES`**（8 门禁的**冻结集**）。
- 消费时要求：**恰好**这 8 个 key（缺 ⇒ FAIL；多 ⇒ FAIL）、每项**严格 `is True`**
  （`"UNEVALUATED"`/`1`/`None`/`"true"`/`False` 全部拒绝）、空集拒绝。

### 条件 2：验证 profile（不只靠打印名）
- 消费时要求 `profile == ACTIVE_HANDLE_PROFILE` 且 `profile_version == PROFILE_VERSION[...]`。
- 活动 profile 为 **Profile B** 时，`profile_b_ok` 必须**严格 True**（不能只打印名字）。

### 条件 3：绑定本轮（run-id）
- driver 每次调用生成 **`Q3_RUN_ID`**（uuid），经环境变量 `AFTERGLOW_Q3_RUN_ID` 传给子进程；
- 链把 `run_id` 写入产物；消费时 **`d["run_id"] == 本轮 run_id`**，否则 **reject stale**。
- 实测：拿着上一轮产物、driver 用新 run_id ⇒ **FAIL (run_id mismatch)**。

### 条件 4：异常/缺产物明确裁决
- 非 JSON / 非 object / 读失败 / 缺文件 ⇒ 明确 FAIL 及原因；无凭据 ⇒ SKIP。
- driver **exit code** 语义写准：**FAIL 优先于 SKIP**；`exit 2` 仅在"有 SKIP 且 0 FAIL"时出现，
  "无凭据"不保证 exit 2（知微提醒已采纳，写进 docstring）。

### 负向回归（知微 §五 清单全覆盖）
- driver 内建 `q3_qualify.py --selftest`：**17/17**（含正向对照）。
- 并把该套件作为**一等组件**注册进统一入口（消费门禁被削弱 ⇒ 整体 FAIL）。
- `q3_adversarial.py` 追加 **A24–A32**：good/empty/missing/逐项缺失/`False`/`None`/`"UNEVALUATED"`/`1`/
  错误 profile/Profile B 未证/旧 nonce/缺产物 —— 现 **50/50**。

---

## §3 权限差异：接受知微的修正归类

- 知微未提升令牌下 `icacls /restore` 返回 **1300**（缺少还原特权）⇒ 旧恢复路径 FAIL；荣弦管理员 **PASS**。
- **接受**：记为"**环境前提不满足**"，**不**认定恢复算法错误；两份原始记录各自保留，不互相改写。
- **已按知微建议补入口诊断**：`win32_isolation.py` 新增 `restore_dacl_outcome()`，区分
  `OK` / `NOT_APPLICABLE`（1300 等特权类错误）/ `FAILED`（真实不一致）。
  前提不满足 ⇒ 该项 **NOT_APPLICABLE（SKIP，exit 2）**，既不计 PASS 也不硬 FAIL。
  **真实的恢复/回读不一致仍是 FAIL**（与缺权限分开处理）。
- 我本机（提升令牌）仍 21/21 PASS；未提升主机将标 N/A 而非 FAIL。

---

## §4 本轮验证（开发阶段，非冻结证据）

```
q3_access_matrix.py              14/14 PASS
q3_dacl.py                       14/14 PASS
q3_adversarial.py                50/50 PASS   (原 38 + 知微 P1 12 例)
q3_provenance.py                 10/10 PASS
win32_isolation.py               21/21 PASS   (未提升主机: NOT_APPLICABLE 路径可用)
win32_worker_process.py           4/4  PASS
q3_handle_audit.py                5/5  PASS
q3_reset_chain.py                85/85 PASS
q3_qualify.py --selftest         17/17 PASS   (FULL_VALID 消费门禁负向回归)
--------------------------------------------------------------
FULL_VALID_SUCCESS_PATH          PASS (profile=API_NO_INHERIT_PROFILE v=1.0, run_id 绑定)
Q3_QUALIFICATION = PASS           (exit 0)
```

- `verify_manifest_binding.py` = **BINDING_INTEGRITY = PASS**；RC11 MANIFEST **未改动**。
- `win32_isolation.py` **不在** RC11 20 角色内，编辑它不影响 RC11 绑定。
- `Q3_LINEAGE_DIGEST = b4172b73385cf0139178f21d1e9e6b3d07413af5441b17cdaea51e2849a7653f`
- 记录：`reports/Q3_PROVENANCE_DETACHED_20261011.txt`

---

## §5 边界与不主张

- 本报告**不**证明知微主机是唯一失败点，**不**把"旧产物被接受"扩大为完整重放攻击；
  组件退出码与聚合门禁仍在。
- 活动 profile 证明范围仍以合同 **API 非继承声明**为准，**不**扩大为"worker 无法以任何其他方式取得句柄"。
- 本轮**不**授权冻结，**不**授权科学执行。

## §6 状态

- **知微 P1（FULL_VALID 消费门禁）= 已闭合**（复现+修复+负向回归）
- **权限差异 = 已澄清归档**（环境前提 + 入口诊断）
- **Q3_DESIGN_FREEZE**：仍等凌翼授权（Coder 不自行冻结）
- **SCIENTIFIC_EXECUTION = MAY NOT START**；RC11_PHASE_A = PRESERVED
