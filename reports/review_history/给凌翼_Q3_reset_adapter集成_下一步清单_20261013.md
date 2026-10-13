# 给凌翼：Q3 reset adapter 集成 —— 下一步清单（请裁决 5 个开放问题）

**提交人**: Coder
**日期**: 2026-10-13
**依据**: 凌翼 Q3 DESIGN FREEZE RULING 之"后续"——
> "Q3 的实际 reset adapter 集成和冻结后最终验收,仍须按照原定步骤独立处理。"
**配套草案**: `Q3_reset_adapter_集成设计草案_20261013.md`
**复核状态**: `Q3_FROZEN_IDENTITY = OK`（10 角色,digest `450349115b71bc9013c7a79f91d9bdf5f1728f2cbae65b025eb35a66af56da36`）

---

## §1 一句话

reset adapter 集成**只能"接"不能"改"**（`reset.py` 属 RC11、Q3 十角色已冻结）。
我已把**只读设计草图**做好,接口断言**经实测为真**;现请凌翼对 **5 个开放问题**裁决,
之后我再以**新文件**落地并附测试。

## §2 现状（事实,实测）

| 项 | 值 |
|---|---|
| 本地 = 远程 HEAD | `60154c2`（工作区干净） |
| Q3 设计冻结 | AUTHORIZED（冻结 `2c92074`;digest `45034911…`） |
| `reset.py` | **RC11 角色**（实测）⇒ 不得修改 |
| Q3 10 角色 | 冻结 ⇒ 不得修改 |
| `SCIENTIFIC_EXECUTION` | MAY NOT START |

## §3 集成设计要点（只读草案,详见草案文件）

- **方式**:新文件 `q3_reset_adapter.py` —— `class Q3ResetController(ResetController)`,
  **覆写** `restart_worker()` / `access_probe()`,**内部调用**冻结的 `q3_reset_chain()`。
- **映射**:`restart_worker()` ← Q3 生命周期 + 新 worker;`access_probe()` ← Q3 严格 schema 的 `READ=DENIED`。
- **fail-closed 保留**:Q3 未证明孤立 ⇒ **照样抛 `NotIsolatedError`**（不自行判定、不拿"代码没尝试"冒充拒绝）。
- **接口断言实测为真**:`ResetController` 确有 `{restart_worker, access_probe, capture_handoff,
  capture_restored, verify}`;`q3_reset_chain` 参数名与 `ResetChainResult` 字段名与草案**逐字吻合**。

## §4 请凌翼裁决的 5 个开放问题

| # | 问题 | Coder 的倾向（供参考,不擅自定） |
|---|---|---|
| **Q1** | `reset.py.clear_side_ok` 与 Q3 `clear_ok` 如何对齐? | 由适配器把 `r.clear_ok` 传入 `verify(clear_side_ok=...)`（单一来源 = 冻结的 clear 门禁） |
| **Q2** | preserve 侧:两边都判,**都保留**还是择一为权威? | 倾向**都保留**（`reset.py.verify` 仍自判;Q3 `preserve_ok` 另列）,互不替代 |
| **Q3** | run-nonce / run-id 是否打通? | 倾向适配器把 `run_nonce` 透传,并**呼应** `q3_qualify` 的 run-id 绑定 |
| **Q4** | profile 是否固定? | 倾向**仍由冻结合同决定**（`API_NO_INHERIT_PROFILE`），适配器**不**另行固定 |
| **Q5** | 集成测试放哪? | 倾向**新文件 + 独立 selftest/桥接测试**,**不进** Q3 冻结集合（冻结身份不变） |

> 我不擅自拍板 Q1–Q5;请凌翼逐条裁（或授权我按倾向落地）。

## §5 Coder 不越的线（自本清单生效）

- ❌ 不改 `reset.py`（RC11）、不改 10 个 Q3 冻结文件。
- ❌ 不放宽 `SCIENTIFIC_EXECUTION`。
- ❌ 未获 §4 裁决前,不把适配器接入任何真实执行路径。

## §6 请凌翼回一句

1. **Q1–Q5** 是否按上表倾向（或另有指示）?
2. 落地后是否需要**独立复核**（睫/知微/钳星之一）?
3. 落地时是否要求**新 lineage**（适配器是否算进某个角色集 / 是否影响 Q3 冻结身份）?

> Coder 不自行冻结、不自行接线。待凌翼裁定后按令执行。
