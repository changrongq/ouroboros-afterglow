# 阶段B · Mion 协作 Token 权限规格（供船长生成）

拟稿：Coder
日期：2026-11-17
性质：**权限规格** —— 船长执行生成，Mion 执行使用，Coder 不接触 token
基线：`09444bf` · `main` = `0ddcedf`

---

## 零 · 先说一件会影响效果的事

```text
⇒ 当前 ruleset 实测：
     bypass_actors                  = []
     required_approving_review_count = 0
     required_reviewers              = []

⇒ 后果：Mion 即使拿到"能发 review"的权限，
   她的意见【不构成合并门槛】—— 我仍可自己开 PR 自己合并。

⇒ 【这是能力边界，不是权限配错】：
   要让 review 成为门槛，必须把 required_reviewers 设为 Mion 的账号、
   且 approvals >= 1。
   ⇒ 但这两个账号的凭据都由船长生成，
     那样就变成"自己批准自己"，【技术上能设，意义上不成立】。

⇒ 因此本轮的目标不是"让 review 成为门槛"，
   而是"让 Mion 能独立读到东西并独立留下意见"。
   ⇒ 后者可以做到，而且【是当前能做到的最有意义的一步】。
```

---

## 一 · Token 类型与作用域

```text
类型        ：Fine-grained personal access token（精细权限 PAT）
不要用      ：Classic PAT（权限过粗，会覆盖整个账号）
归属账号    ：由船长提供（见 §五 的边界说明）

Repository access
  ○ 只选：changrongq/ouroboros-afterglow
  ✗ 不要选 "All repositories"
  ✗ 不要选其他仓库
```

---

## 二 · 权限清单（逐项给理由）

| 权限 | 级别 | 为什么需要 | 不给会怎样 |
|---|---|---|---|
| **Metadata** | Read | GitHub 强制项，任何 PAT 都含 | 无法调用任何 API |
| **Contents** | **Read** | 读代码、spec、reports、B_36 台账 | Mion 无法看到被审对象 |
| **Pull requests** | **Read and write** | 发 review 意见、评论 PR | 只能看，不能留意见 |
| **Issues** | **Read** | 可读 issue（可选，便于追溯） | 无法看 issue 讨论 |
| **Commit statuses** | Read | 看 CI 结果（可选但推荐） | 看不到检查是否通过 |

**明确不给**

```text
✗ Contents: Write      —— 会获得推送能力，破坏"只审不改"
✗ Administration       —— 会获得改设置、改规则集能力
✗ Actions              —— 可改 workflow，等于间接获得写权
✗ Secrets              —— 高危，且与本案无关
✗ Webhooks             —— 可外发数据
✗ Members / 组织相关    —— 不适用（本仓库为 User 仓库）
✗ Organization admin   —— 不适用
```

```text
⇒ 【为什么给 Pull requests: Read and write 而不担心越权】：
   ⇒ 该权限只能【对 PR 发评论/审核】，不能推代码。
   ⇒ 且 ruleset 的 bypass_actors = []，
     【任何 token 都不能用它绕过保护规则】。
   ⇒ 所以这个权限的实际能力边界是：
       "能说话，不能动手"。
```

---

## 三 · 有效期与交付

```text
Expiration      ：90 天（到期重新评估，不自动续期）
Name            ：mion-review-2026-11（便于台账追溯）
```

**交付方式**

```text
⇒ 不贴在对话里（这是之前踩过的坑）。
⇒ 写入本地文件，建议路径：D:\qcr\Mion\.gh-token
   ⇒ 要求：
     · 该目录【不在】任何 git 仓库内
     · 不要用 git add 可能捕获的位置
     · 文件生成后由 Mion 使用，船长不保留副本
⇒ 或设为用户环境变量（如 GH_TOKEN_MION），本机范围
```

```text
⇒ 【关于"船长不保留副本"这一条】：
   本方案做不到强制（船长是账号持有者，理论上可重新生成）。
   ⇒ 但作为【约定】仍有价值：它把"有没有留存"变成一个可自查的行为。
   ⇒ 台账中如实标注：credential_holder = 船长（生成者），
     account_operator = Mion。
```

---

## 四 · Mion 用这个 token 能做什么（验收标准）

```text
⇒ 这些是【可实际验证】的能力，建议 Mion 拿到后逐条确认：

  M-1  能读仓库内容
       GET /repos/changrongq/ouroboros-afterglow/contents/reports/review_history
       期望：200

  M-2  能读 exp/v2-l1-verifier 分支（工作分支，非 main）
       GET /repos/.../contents/... ?ref=exp/v2-l1-verifier
       期望：200
       ⇒ 若不满足，Mion 审到的将是过时内容

  M-3  能读 PR 列表与详情
       GET /repos/.../pulls
       期望：200

  M-4  能发 PR review
       对某个 PR 提交一条 review（可先在自己的测试 PR 上验证）
       期望：201

  M-5  【不能】推送代码
       POST 一个 contents 写入请求
       期望：403
       ⇒ 【这一条必须验证】，否则"只审不改"只是声明

  M-6  【不能】改仓库设置
       GET /repos/.../rulesets 应可读，但 PATCH 应 403
       期望：403
```

```text
⇒ 【M-5 和 M-6 是反向验证】：
   证明"给的是有限权限"，而不是只证明"给了权限"。
   ⇒ 只做正向验证的权限审查，等于没审。
```

---

## 五 · 这个 Token 让 WE-1 走到了哪一步

```text
⇒ 【明确不能主张的】：
   ✗ 独立写权已建立（WE-1 仍 NOT_ESTABLISHED）
   ✗ Mion 是独立凭据主体（token 由船长生成）
   ✗ review 构成合并门槛（approvals = 0）

⇒ 【可以主张的】：
   ✓ 存在第二个【操作主体】（Mion 实际操作）
   ✓ 存在第二个【可归因身份】（review 记录在 Mion 名下）
   ✓ 权限边界经反向验证（M-5/M-6 证明不能改）
   ✓ "只审不改"是机制而非约定（Contents: Read 为硬限制）
```

```text
⇒ 台账应记的类别：
   INDEPENDENCE_CLASS = SEPARATE_OPERATOR_SHARED_CREDENTIAL_ORIGIN
   （操作主体分离，凭据来源同一）
   ⇒ 这比之前的"单主体"前进了一步，
     但【不等于】独立的写权主体。
```

---

## 六 · 一条我要写进规格的限制

```text
⇒ 【Mion 的 review 不能作为"独立性证明"】，
   因为生成 token 的人（船长）与接受审查的人（Coder）
   在 GitHub 侧是同一主体（changrongq）。
   ⇒ 所以这个审查的诚实定位是：
     "同一控制域内的第二双眼睛"，
     不是"外部独立审计"。

⇒ 【但它仍然有用】，理由不是"更可信"，而是：
   · 把审查从"我自查"变成"有记录的他查"
   · review 记录在案，事后可追溯
   · 意见若被忽略，会留下痕迹
   ⇒ 这些价值不依赖"完全独立"，依赖"有第三方痕迹"。
```

---

## 七 · 状态登记

```text
MION_TOKEN_TYPE          = FINE_GRAINED_PAT
MION_TOKEN_REPO_SCOPE    = changrongq/ouroboros-afterglow（单一仓库）
MION_TOKEN_PERMISSIONS   = Metadata:R, Contents:R, PR:RW, Issues:R, Statuses:R
MION_TOKEN_EXPIRATION    = 90 天
MION_TOKEN_HOLDER        = 船长（生成者）
MION_ACCOUNT_OPERATOR    = Mion

INDEPENDENCE_CLASS       = SEPARATE_OPERATOR_SHARED_CREDENTIAL_ORIGIN
WE-1_INDEPENDENT_WRITE   = NOT_ESTABLISHED（未变）
RESIDUAL_INDEPENDENCE_GAP = CREDENTIAL_ORIGIN_SAME_SUBJECT
```

---

## 八 · 一句

```text
⇒ 这个 token 做不到"让 WE-1 成立"。
⇒ 但它做得到一件更实在的事：
   把"我说我检查过了"变成"我的检查记录在案，且有人可以再查一遍"。

⇒ 在当前只有一个人的架构下，
   这已经是最接近"第二方"的安排了。
```
