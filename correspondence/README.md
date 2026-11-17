# 往来通信目录（入口）

建立：2026-11-18
用途：**指路文件** · 让任何人从 `main` 一眼找到通信目录的实际位置

---

## 通信文件在哪里

```text
⇒ 【实际位置】：`exp/v2-l1-verifier` 分支的 `correspondence/` 目录
⇒ 【不在 main】。本文件只是一个入口提示。

   直接链接：
   https://github.com/changrongq/ouroboros-afterglow/tree/exp/v2-l1-verifier/correspondence
```

```text
⇒ 【为什么在 exp 分支而不是 main】：
   按凌翼裁定 A-3.1，main 只作权威定位说明，不含 B2 最新工作。
   B_30 登记表、CI、以及所有通信都在 exp 分支。
   ⇒ 本文件只解决"从哪进去"，不改变那个裁定。
```

---

## 当前通信文件

| 文件 | 收件人 | 主题 |
|---|---|---|
| `给睫知微钳星_三份文档审查请求_Coder_20261118.md` | 睫 / 知微 / 钳星 | 审查 B_45 / B_46 / B_47 |

---

## 怎么用这个目录

```text
⇒ 【只放通信】—— 一方写给另一方的内容：
   ✅ 请求复核
   ✅ 裁定请求 / 回执
   ✅ 答复意见
   ✅ 交接说明（写给特定人的）

⇒ 【不放】：
   ❌ 规范定稿（在 reports/review_history/）
   ❌ 实测报告（在 reports/review_history/）
   ❌ 登记表（B_30，在 reports/review_history/）
   ❌ 设计与方案（B_45/46/47 等，在 reports/review_history/）
```

```text
⇒ 【判断标准一句话】：
   读者是【具体的人】⇒ 通信；
   读者是【任何后来的执行者或审查者】⇒ 文档。
```

---

## 命名规则

```text
  发给某人    ： 给<收件人>_<主题>_<作者>_<YYYYMMDD>.md
  某人发来    ： 来自<发件人>_<主题>_<YYYYMMDD>.md

⇒ 加"来自"前缀，是为了让【方向】一眼可见。
   旧目录里有对方发来的文件混在"给*"里，看不出是谁写的。
```

---

## 历史通信在哪

```text
⇒ 2026-11-18 之前的通信文件【不迁移】，
   仍在 `reports/review_history/`（约 140 份，命名多为 `给*`）。

⇒ 不迁移的理由：
   · 文件 hash 与路径绑定，移动会使 B_30 登记表整批失效
   · 历史引用关系（B_23 引 B_22 等）会被打断

⇒ 检索命令（在 exp 分支上执行）：
```

```powershell
Get-ChildItem reports\review_history -Filter "*.md" |
  Where-Object { $_.Name -match '^(给|知微_|睫_|钳星_)' } |
  Select-Object -ExpandProperty Name
```

---

## 完整规则

详细规则见 `correspondence/README.md`（在 exp 分支上）。

---

## 一句

```text
⇒ 一个要人猜分支的中转站，会漏消息。
⇒ 所以这个文件存在的意义只有一个：
   让人从仓库首页就能走对第一步。
```
