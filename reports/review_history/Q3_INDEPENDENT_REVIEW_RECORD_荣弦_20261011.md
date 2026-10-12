# Q3_INDEPENDENT_REVIEW_RECORD — 独立 Windows 复跑（第 7 步）

**记录人**: Coder（据荣弦/钳星提交的复跑结果整理）
**记录日期**: 2026-10-12
**依据**: 凌翼 Q3 REVIEW — "MANDATORY BEFORE Q3 FREEZE: Independent reviewer evidence"；
凌翼 Q3 R3 交接字段要求。

---

```
Q3_INDEPENDENT_REVIEW_RECORD
========================================================================
reviewer                     : 荣弦 (Rongxian)
reviewed_commit              : 1db6286  (待核：见 §环境适配说明)
contract_hash                : q3_contract.py 见 §provenance（本轮以 commit 固定）
profile_id / version         : API_NO_INHERIT_PROFILE / 1.0
profile_scope                : 仅"新 worker 未继承禁用句柄"；runtime_handle_audit
                               保持 UNRESOLVED/CLEAN 原样记录；FOUND_TARGET 恒 INVALID
------------------------------------------------------------------------
Windows version / build      : 独立 Windows 主机（与 Coder 主机不同）
caller SID category          : 交互式管理员（可调 CreateProcessWithLogonW；前提满足）
worker SID verification      : 通过（F3：SID 与 controller 不同、与期望账户一致）
prerequisite verdict         : MET（有口令时 q3_qualify PASS；无口令分支见下）
------------------------------------------------------------------------
component_test_counts        :
  q3_access_matrix.py        = 14/14 PASS
  q3_dacl.py                 = 14/14 PASS
  q3_adversarial.py          = 38/38 PASS
  q3_provenance.py           = 10/10 PASS
  win32_isolation.py         = 21/21 PASS
  win32_worker_process.py    = 4/4  PASS
  q3_handle_audit.py         = 5/5  PASS
  q3_reset_chain.py          = 84/84 PASS
adversarial_negative_results : 38/38 全部正确拒绝（无 regressed case）
FULL_VALID_SUCCESS_PATH      : PASS (profile=API_NO_INHERIT_PROFILE,
                               audit=HANDLE_AUDIT_CLEAN)
raw reset gate values        : valid=True；8 门禁全 True（clear/preserve/access/
                               handle/identity/lifecycle/matrix/dacl_restore）
runtime handle-audit status  : HANDLE_AUDIT_CLEAN
Profile B proof values       : 6 字段全 True（creation_api/startupinfo/inheritable
                               channels/non-inheritance/leak-control/no-known-handle）
------------------------------------------------------------------------
DACL restoration result      : OK（restore + 读回匹配）
cleanup result / residuals   : 无残留（checked_rmtree）
provenance verification      : verify_manifest_binding.py = PASS
                               （MANIFEST hash 78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059）
------------------------------------------------------------------------
overall PASS / FAIL / NOT_EVALUATED :
  有口令 : Q3_QUALIFICATION = PASS (exit 0)  ==> PASS
  无口令 : Q3_QUALIFICATION = NOT_EVALUATED (SKIP present; NOT a pass)  ==> NOT_EVALUATED ✅
new blocking findings        : 无（见 §环境适配说明，非科学规则问题）
reviewer conclusion          : 独立主机复跑成功；开发阶段门禁在异主机同样成立
========================================================================
```

---

## §环境适配说明（重要，如实记录）

荣弦在独立主机上的**唯一本地改动**是 `PUBLIC_PYTHON_DEFAULT`：

| 项 | 内容 |
|----|------|
| 改动文件 | `win32_worker_process.py`、`q3_reset_chain.py`（**两处**，非仅一处） |
| 改动内容 | `D:\Python39\python.exe` → `D:\Python\python.exe`（Python 3.9.8） |
| 性质 | **环境路径**，非科学规则/阈值/门禁 |
| 影响 | 无逻辑变化；仅指向该主机上 worker 可读的公共解释器 |

**这不是缺陷**，但它暴露了一个**可复现性接口问题**：冻结候选必须字节一致，而审阅者需要
指向自己的解释器。因此本轮已**修复该接口**（而非记录成特例）：

- 两文件新增**环境变量覆盖** `AFTERGLOW_PUBLIC_PYTHON`，默认回落到 Coder 主机路径。
- 审阅者**不再需要改动冻结源字节**即可指向自己的解释器 —— 符合凌翼"冻结精确源码"要求。
- 覆盖是**环境事实**（须在复核记录中记下实际使用的路径），不触碰任何门禁。

> 备注：荣弦的复跑在**改动前**的 `1db6286` 上完成，且两处均按文件要求改到同一路径，
> 因此与 Coder 侧结果**逐项一致**（14/14/38/10/21/4/5/84 + FULL_VALID PASS），
> 是有效的**独立复现**。下一位审阅者可直接用 `AFTERGLOW_PUBLIC_PYTHON` 覆盖，无需改源码。

---

## 无口令对照（凌翼 R3 / BD-70 纪律）

- `q3_qualify.py`（**无口令**）→ `Q3_QUALIFICATION = NOT_EVALUATED (SKIP present; NOT a pass)` ✅
- 说明：凭据依赖模块正确 SKIP，**SKIP 未被计为 PASS** —— 符合"未执行 ≠ 通过"。

---

## 状态

- **第 7 步独立 Windows 复跑**：✅ 已完成 1 次（荣弦，独立主机）
- **知微**（第二审查者）/ **睫**（静态源码复核）：仍待
- **Q3_DESIGN_FREEZE**：仍等凌翼授权（Coder 不会自行冻结）
- **SCIENTIFIC_EXECUTION = MAY NOT START**
- RC11_PHASE_A = PRESERVED
