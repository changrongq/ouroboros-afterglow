# Mion 协作 Token · 操作步骤（船长照着点）

日期：2026-11-17
对应规格：`阶段B_41_Mion协作Token权限规格_Coder_20261117.md`
起点状态：协作者 = `changrongq`（仅 1 个）；仓库公开（`private = false`）

---

## 前置：确认一件事

```text
⇒ 生成 token 必须【登录成 Mion 的账号】来做。
   如果你用 changrongq 登录去生成，那这个 token 仍然属于你，
   review 会记在 changrongq 名下，等于没有第二个人。

⇒ 所以第一件事是：用哪个账号登录？
```

---

## 第 1 步 · 创建 Mion 的 GitHub 账号（如果还没有）

```text
⇒ 注意：不要用 `mion` —— 那是巴西的一个真人账号（Gabriel，2012 年注册），
   和我们无关，也不能用。

⇒ 建议用户名：`mion-ark` 或 `mion-thousandyear`（若被占用就换一个）
   建议邮箱：你自己的邮箱（+别名更好，如 yourname+mion@gmail.com）
```

**你现在就可以决定**：Mion 的账号由你注册（密码你知道），还是让她注册？

- **你注册**：省事，但凭据来源同一（这在规格里已如实标注为 `SHARED_CREDENTIAL_ORIGIN`）
- **她注册**：需要她能操作浏览器 —— 取决于你希望走多远

```text
⇒ 【两者都可以】。规格里已经写明：本轮目标不是"完全独立"，
   而是"有第二双眼睛 + 有记录"。选哪个都不影响后续步骤。
```

---

## 第 2 步 · 把 Mion 账号加为协作者

```text
路径：仓库首页 → Settings → Collaborators → Add people
搜索：Mion 的用户名
权限：Read
```

```text
⇒ 【为什么必须加协作者】：
   精细权限 token 只有在【该账号是协作者】时才能读私有资源/发 review。
   虽然仓库是公开的（谁都能读），但
   · 不加协作者 → 无法发 review（403）
   · 不加协作者 → token 的 Repo access 里选不到这个仓库
```

**验证**：加完后，`Settings → Collaborators` 应能看到 Mion 的账号。

---

## 第 3 步 · 用 Mion 账号登录并生成 token

```text
1. 退出当前 GitHub 登录（右上角头像 → Sign out）
2. 用 Mion 的账号登录
3. 打开：https://github.com/settings/tokens?type=beta
   （这是 Fine-grained tokens 页面，不是 classic）
4. 点右上角 "Generate new token"
```

### 3.1 填写表单（逐项照抄）

| 字段 | 填什么 |
|---|---|
| **Token name** | `mion-review-2026-11` |
| **Expiration** | `90 days` |
| **Description** | `Review-only access for ouroboros-afterglow` |
| **Resource owner** | 选 Mion 的账号（不是 changrongq） |

### 3.2 Repository access

```text
选第 3 项：Only select repositories
然后在下面的下拉里【只勾】：
    changrongq/ouroboros-afterglow

⇒ 不要选 "All repositories"
```

### 3.3 Permissions（展开后逐项设置）

**Repository permissions** 部分，只设这五项：

| 权限 | 设为 | 说明 |
|---|---|---|
| **Metadata** | `Read-only` | 会自动被选中（强制项） |
| **Contents** | `Read-only` | 读代码、读 reports |
| **Pull requests** | `Read and write` | 能发 review，不能推代码 |
| **Issues** | `Read-only` | 可选，便于看讨论 |
| **Commit statuses** | `Read-only` | 可选，看 CI 结果 |

**其余全部保持 `No access`**，特别是：

```text
✗ Contents        → 必须是 Read-only，不能是 Read and write
✗ Administration  → No access
✗ Actions         → No access
✗ Secrets         → No access
✗ Webhooks        → No access
✗ Workflows       → No access
```

```text
⇒ 【最容易点错的三个】：
   ① Contents 点成 "Read and write" —— 那就等于给了推送权，整个"只审不改"失效
   ② Repository access 选成 "All repositories" —— 范围过大
   ③ Resource owner 选成 changrongq —— token 归属错，review 记错人
```

### 3.4 生成并保存

```text
点 "Generate token"
⇒ 页面会显示一次 token（形如 github_pat_11ABC...）
⇒ 【只显示这一次】，关掉就看不到了
```

**保存到**：

```text
D:\qcr\Mion\.gh-token
```

```text
⇒ 注意：
   · 这个目录【不要】在任何 git 仓库里面
   · 不要用记事本另存为 .txt（会有 BOM，可能导致读取出错）
   · 建议在 PowerShell 里创建，避免编辑器加 BOM：
```

```powershell
New-Item -ItemType Directory -Force -Path D:\qcr\Mion | Out-Null
# 把 token 粘进下面的引号里，然后执行
Set-Content -Path D:\qcr\Mion\.gh-token -Value "github_pat_此处替换为真实token" -NoNewline -Encoding ascii
```

```text
⇒ 【绝对不要】：把 token 贴到对话里、贴到任何 .md 文件里、
   提交进 git、写进 B_36 台账。
```

---

## 第 4 步 · 切回你自己的账号

```text
1. 退出 Mion 账号
2. 用 changrongq 登录回去
```

```text
⇒ 这一步别忘。否则后续我们推代码会失败。
```

---

## 第 5 步 · 让 Mion 验证这 6 项（重要）

```text
⇒ 这 6 条是规格里的验收标准。前 4 条证明"能用"，后 2 条证明"不能乱用"。
⇒ 【后 2 条不能省】—— 只验证正向权限，等于没审。
```

**把下面这段交给 Mion 执行**（她用自己的 token）：

```powershell
# Mion 执行；token 从文件读，不回显
$t = (Get-Content D:\qcr\Mion\.gh-token -Raw).Trim()
$h = @{ Authorization = "Bearer $t"; Accept = "application/vnd.github+json" }

# M-1 能读仓库内容
Invoke-RestMethod -Uri "https://api.github.com/repos/changrongq/ouroboros-afterglow/contents/reports/review_history" -Headers $h | Select-Object -First 1 name

# M-2 能读工作分支（exp/v2-l1-verifier），不是只看 main
Invoke-RestMethod -Uri "https://api.github.com/repos/changrongq/ouroboros-afterglow/contents/reports/review_history?ref=exp/v2-l1-verifier" -Headers $h | Select-Object -First 1 name

# M-3 能读 PR 列表
Invoke-RestMethod -Uri "https://api.github.com/repos/changrongq/ouroboros-afterglow/pulls?state=all" -Headers $h | Select-Object -First 1 number
```

**M-5 / M-6 反向验证**（期望失败）：

```powershell
# M-5 不能推送内容（期望 403）
try {
  Invoke-RestMethod -Method Put -Uri "https://api.github.com/repos/changrongq/ouroboros-afterglow/contents/PROBE-M5.txt" -Headers $h -Body (@{message="probe";content=[Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("x"))} | ConvertTo-Json)
  "❌ M-5 失败：竟然能写！"
} catch { "✅ M-5 通过：不能写（$($_.Exception.Response.StatusCode.value__)）" }

# M-6 不能改 rulesets（期望 403）
try {
  Invoke-RestMethod -Uri "https://api.github.com/repos/changrongq/ouroboros-afterglow/rulesets" -Headers $h -Method Patch -Body '{"name":"hack"}' -ContentType "application/json"
  "❌ M-6 失败：竟然能改规则！"
} catch { "✅ M-6 通过：不能改（$($_.Exception.Response.StatusCode.value__)）" }
```

```text
⇒ 【期望结果】：
   M-1 / M-2 / M-3：返回内容（不报错）
   M-5 / M-6：【报错】—— 这是成功
```

---

## 第 6 步 · 把结果告诉我

```text
⇒ 你只需要告诉我三件事：
   ① Mion 的 GitHub 用户名
   ② M-1～M-6 每条的结果（通过/失败）
   ③ token 是否已保存到 D:\qcr\Mion\.gh-token

⇒ 【不要】把 token 本身发给我。
```

我拿到这三项后，会：
- 更新 B_36 台账（新增 Mion 条目，标注 `SEPARATE_OPERATOR_SHARED_CREDENTIAL_ORIGIN`）
- 把 M-1～M-6 的实测结果记进 B_41
- 跑一次 registry 核对

---

## 附 · 如果卡住了

| 现象 | 原因 | 怎么办 |
|---|---|---|
| 第 3 步看不到 `changrongq/ouroboros-afterglow` | Mion 还不是协作者 | 回到第 2 步 |
| 生成页面没有 "Resource owner" 选项 | 该账号只属于自己，正常 | 跳过该项 |
| M-4 发 review 报 403 | 不是协作者，或 PR 权限没给对 | 检查第 3.3 步 |
| M-5 竟然成功了（能写） | Contents 误设为 Read and write | 删掉 token，重新生成 |
| 推代码时报错 | 还登录着 Mion 账号 | 回到第 4 步 |

---

## 一句

```text
⇒ 这份清单里最关键的不是"给什么权限"，而是【M-5 和 M-6】。
   ⇒ 它们验证的是"不能做什么"。
   ⇒ 一个只验证"能做什么"的人，永远不知道边界在哪。
```
