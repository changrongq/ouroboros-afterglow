# HISTORY REWRITE RECORD — ouroboros-afterglow

**日期**：2026-10-11
**原因**：Q3 SECURITY（凌翼：worker 账号口令曾误入代码/报告）。为从 **Git 历史**移除该凭据字符串，
对仓库执行了 `git filter-repo --replace-text`，随后 `--force` 推送。

**后果（必须记账，不得悄悄过去）**：`filter-repo` 重写了**所有后裔 commit 的 hash**。
因此 2026-10-11 之前报告/INDEX 中所有 `reviewed on commit <old>` 引用，指向的是**已被重写掉的旧对象**，
在远端**不再存在**。文件内容 hash（如 RC11 MANIFEST `78bdb90f…`）**未变**，但 **commit 身份变了**。

---

## 1. 旧 → 新 commit 映射（filter-repo commit-map；节选被引用者）

| 旧 hash（报告/INDEX 中引用） | 新 hash（重写后） |
|---|---|
| `5e17fe8933de…`（RC11 reviewed / P2-A closure） | `2b6d8a31ef05298b9d1cecb4a24ce7b6f3516053` |
| `525f81f18b0f…`（RC11 delivery） | `f28216301094c771593756ada2a72316cca20296` |
| `ca4c510dcadd…`（RC10 index） | `bce211967d7dea311837bf7b07b8419ef3ae27f0` |
| `c11063ca2705…`（RC11 P2） | `9d82dbae0ebeeba376c78768f4478ae41ce6bc2a` |
| `d8cdac188ad0…`（Q3 V3 cross-process） | `6f4a54724d1159f92409be907e419d26e45df428` |
| `62720a07b3ae…`（Q3 V2 hardening） | `98308a0d871ee2453f249243be5952556ff5a59c` |
| `6003eae8781c…`（Q3 V1/PoC） | `0c864a04b2fb515c7c6ee6a4e3c5465815e6ae53` |
| `f2408a1bb227…`（Q3 design/PoC） | `686c54e89414408b20d6d39743e9dfb5629f965e` |
| `42c01ad163c7…`（RC10 delivery） | `632d20cf52dc975a459814c79b1056f59b0c72e4` |
| `10c303d08f5b…`（RC11 closure record） | `62a163a5f624bc00c1f45d9e1612158193ed6266` |
| `98d6691f833c…`（Q3 SECURITY commit） | `940bc8be441ae8fffc4e75cb70893d19dfd0c1aa` |
| `a57e4e0bd779…`（written report archive） | `662c848814bf98993f72f15d5e42ec851f69e216` |
| `c92bc6180171…`（BD-60 doc fix） | `373e28a7c28bb3e5a056cc7ca4d262d77d1f7216` |

**未受影响的 commit**（old == new，不在改写传播路径上）：
`0a8c06ca… 0c89e1e9… 156bcf27… 16dfe244… 207d74dc… 216de2e4… 2a0737bf…(RC9)
4b758b0c… 4cdef8ef… 63539abd… 6f99b979… 87d61b17… e099ddf4… fcf28438…`

（完整映射见 `.git/filter-repo/commit-map`。）

---

## 2. RC11 冻结字节的复核（内容 hash 未受改写影响）

在**重写后 HEAD** 上重新核验：
```
RC11 MANIFEST SHA-256 = 78bdb90f7a56b5da0c9b37ce7f454fa98a64530800f9d0727cf773e120e23059
SPEC  = b7ec1fdc…  PREREG = ad0855b0…  （与改写前一致）
EXECUTION_CRITICAL_ROLE_HASHES = 20/20 匹配 MANIFEST
```
⇒ **文件内容**身份未变；变的只是 **commit 身份**。（Q3-5 已记：`adversarial_regression.py` 的冻结常量
`123456` 曾被全局替换，已从工作树按字节恢复为 `d2743520…`；**历史 blob** 中该常量被替换为占位符。）

---

## 3. 后果与使用规则

- **2026-10-11 之前**的报告/INDEX 中的 `commit <hash>` 引用：**仅作叙事**，不作溯源；
  请用上表映射到新 hash。
- **RC11 逻辑层资格**结论（知微 P1/P2 闭合、凌翼 FINAL ADJUDICATION）绑定的是**文件内容 hash + SPEC/prereg hash**，
  受此记录保护；不依赖旧 commit 身份。
- 今后**禁止**将凭据写入任何 tracked 文件；历史改动必须在此记录登记。

---

## 4. 备注

- 本次改写由 `git filter-repo` 执行；`--replace-text` 是**全局**替换，曾连带替换冻结常量
  （教训：定向脱敏应用 `--path-glob`）。
- 本记录本身**不含**任何凭据。

—— Coder
