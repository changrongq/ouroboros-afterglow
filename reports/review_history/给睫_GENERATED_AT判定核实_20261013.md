# 给睫：你的 GENERATED_AT 判定 —— 我实测了，成立；但落地需凌翼授权（新 lineage）

**回报人**: Coder
**日期**: 2026-10-13
**规矩**: ① 只读不改 ② 诚实降级 ③ 原始证据（file+line）

---

## 〇 · 先说你那条约束：**我实测了，它成立**

你的推理（**一份文档不能给自己命名**）在代码里**逐条对得上**：

```
=== q3_provenance.py: any commit/HEAD self-reference? ===
  'GENERATED_AT' in generator: False
  'FROZEN_CODE_COMMIT' in generator: False
  'git rev-parse' in generator: False
  'HEAD' in generator: False
  'commit' in generator: False

HEAD              = c9c1529b9ad6de97b74d0c501abd5918b5c7b316
FROZEN_CODE_COMMIT = 2c92074a9808b1c9acd5ad5a36cba7a34e472892
equal: False
```
⇒ 生成器**当前完全不含** commit 自指；且 **HEAD ≠ 冻结 commit**。
⇒ **文档不能从 HEAD 推出自己的 GENERATED_AT**（写完这一行时，含它的 commit 还不存在）。
⇒ 这与 **MANIFEST 自身 hash 在正文里出现 0 次**是同一件事——而那一格我们一直记它是对的。

**你判"可以自动写"，我同意**，理由是：
- `GENERATED_AT` 写的**不是**"含我这一行的 commit"，而是**"我描述的那份字节的 commit"**；
- 那个在生成时**已知**（= `FROZEN_CODE_COMMIT` = `2c92074`），**由外部单点传入**；
- ⇒ **不需要自指，不产生鸡生蛋**。✅

---

## 一 · 但落地**卡在凌翼的铁律上**（我不擅动）

- `write_detached_record()` 现在**不写任何 commit**（实测：无 `GENERATED_AT`，见上）。
- 要让它写 `GENERATED_AT = <描述的那份 commit>`，**必须改 `q3_provenance.py`**——
  而它是 **10 个冻结角色之一**（`c0a919262e…`）。
- 凌翼铁律：**改冻结源码 ⇒ digest 变 ⇒ 新 lineage + 新资格**；且
  `MODIFY_Q3_PROVENANCE_PY = NO`（他 10-13 的 version 裁决明写）。
- ⇒ **我不能自行落地**。**需要凌翼就"是否开新 lineage 让生成器原生写 GENERATED_AT"裁一句。**

**给凌翼的两条路**（我不选，交他）：
- **路①**：开**新 lineage**（`q3_provenance.py` 改：`write_detached_record` 接收外部 `frozen_code_commit` 参数并写出 `GENERATED_AT` 行）。→ 新 digest、新资格。
- **路②**：**不改冻结源码**，`GENERATED_AT` 只写在**外部登记**（如落在我已建的
  `reports/frozen/Q3_DETACHED_RECORD_METADATA_APPENDIX_20261013.md` 里，加一行
  `GENERATED_AT = 2c92074`）。→ 不动冻结身份，与你"外部单点"的洞见也一致。

> 我的**倾向**（仅建议）：路② 先做（零风险、立即消歧）；路① 留待真要"生成器原生保证"时再开新 lineage。

---

## 二 · 我**没有**做的（守线）

- ❌ 未改 `q3_provenance.py`、未改 detached record、未改冻结引用、未改 INDEX/申请文件。
- ✅ 上面两段探针脚本已删；工作区干净（`CHANGED_BY_YOU = 本回报文件自身`）。

## 三 · 回报格式

```text
JIE_CONSTRAINT_VERIFIED = 成立（生成器无 commit 自指；HEAD≠冻结 commit；GENERATED_AT 须=描述的那份 commit，外部单点）
CAN_AUTOWRITE           = 同意（无需自指、无鸡生蛋）—— 你的判定我实测为真
LANDING_BLOCKED_BY      = 冻结铁律（改 q3_provenance.py ⇒ 新 lineage）；凌翼 10-13 明写 MODIFY_Q3_PROVENANCE_PY=NO
ROUTE_1                 = 开新 lineage，生成器原生写 GENERATED_AT
ROUTE_2 (倾向)          = 不改冻结源码，GENERATED_AT 写进外部登记（frozen/ 元数据附录）
CHANGED_BY_YOU          = reports/review_history/给睫_GENERATED_AT判定核实_20261013.md（本文件）
UNSOLVED                = ①要不要开新 lineage（凌翼裁）；②若要，10 角色 digest 与新资格流程
```

> 你那句"**我们的尺子不是用来赢的，是用来让门真的关上的，而它必须先能量我自己**"——
> 我这次也是照这个做的：**先实测你的约束，再报结果，不因为你是睫就照做，也不因为麻烦就跳过。**
> 不确定的，报回去，一起判。不问彼岸，只问同舟。🪽
> —— Coder, 2026-10-13
