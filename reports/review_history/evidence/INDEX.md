# Q3 原生证据包 — INDEX（REQ-2）

**归档人**: Coder
**日期**: 2026-10-12
**依据**: 凌翼 EVIDENCE RECEIPT REVIEW（REVIEWED_HEAD `5271b22`）
> "NATIVE EVIDENCE BUNDLE = NOT FULLY ARCHIVED" → 本目录即补齐。
**脱敏**: 全部文件**不含** worker 明文口令（凭据仅经环境变量注入；仅出现变量名）。

---

## 目录结构

```
reports/review_history/evidence/
├── INDEX.md                                   (本文件)
├── REQ2_zhiwei_5fda429_20261012/              知微 未提升环境复跑（原生 JSON + 日志）
│   ├── README.md
│   ├── snapshot.json / results.json
│   ├── source_hashes_before.json              复跑前 177 项源码 SHA-256（证明未改源码）
│   ├── full_valid_with_credential.json        本轮 FULL_VALID 产物（run_id 2d17082d…）
│   ├── run_req2.py                            复跑脚本（凭据仅经 env）
│   ├── logs/                                  binding / with_credential / without_credential 原始输出
│   ├── SHA256SUMS.json                        包内自校验（Coder 复核 12/12）
│   ├── 给Coder_REQ2当前提交复跑_20261012.md    知微报告正文
│   └── received_original.zip                  船长收到的原始 zip（原件留存）
└── REQ2_captain_admin_5fda429_20261012/       船长 管理员环境复跑（文本登记）
    ├── README.md
    └── raw_terminal_output.txt                船长原始终端输出（逐字）
```

## 双层哈希说明（凌翼 2026-10-12：务必保留，不可混用）

本目录存在**两套字节表示**，各有其 hash，**不可互相替代**：

1. **ZIP 内原始字节（CRLF）** —— 权威原始证据。`received_original.zip`（19,296 B，
   sha256 `cacb21d8e811f4e0ed2c198e630030f3afc86bc7d54282b68ae9ef2b0f7370d3`）内含 13 个
   文件条目；其 `SHA256SUMS.json` 记录的就是这层**原始 CRLF** 字节的 hash。
2. **GitHub 展开文本（LF 归一）** —— 为跨平台存储归一为 LF；下方"文件哈希"表即这层。

**验证事实（凌翼与 Coder 双方独立复核）**：
- ZIP 内 12 个条目 sha256 **全部匹配**其 `SHA256SUMS.json`（原始层自洽）。
- GitHub 展开文件 sha256 **全部匹配**本 `INDEX.md` 哈希表（存储层自洽）。
- 两套 hash 对同一内容**不同**，因为**字节表示不同**（CRLF vs LF）；**非篡改**。
- 复跑脚本 `run_req2.py` 与 3 个空 stderr 在两套表示中**字节相同**（无换行差异）。

> 纪律：引用证据时**注明是哪一层**。原始层（ZIP + SHA256SUMS）为准；存储层（GitHub）为可读副本。

---

## 文件哈希（SHA-256，GitHub 存储层 = LF 归一后字节）

| 文件（相对本目录） | bytes | sha256 |
|---|---|---|
| `REQ2_captain_admin_5fda429_20261012/raw_terminal_output.txt` | 3471 | `d998177a43f1f114ab63d55a891aea39f455db0036a9befa0a5a29ca8d6c1d55` |
| `REQ2_captain_admin_5fda429_20261012/README.md` | 1528 | `676d7fab322dc4e5be7509dd52d519c99548ec81a800a2e10006712db116328e` |
| `REQ2_zhiwei_5fda429_20261012/README.md` | 2552 | `db3242b73fcfd774e70f58d1ed7907c30bbf5900000891e13ff4be85dec3e112` |
| `REQ2_zhiwei_5fda429_20261012/snapshot.json` | 549 | `7d2c50074443957d9664c6c2f9a503523702a6de131d64a0ba957a736f057f2f` |
| `REQ2_zhiwei_5fda429_20261012/results.json` | 2250 | `1f360870594f71a0d6dbf981d418886e1134c222625ffd78dac11d746ec52bc1` |
| `REQ2_zhiwei_5fda429_20261012/source_hashes_before.json` | 22326 | `ab0e2c407bdf561dcf2513c67b6dc461009407814b3e5764267962417de3c7d2` |
| `REQ2_zhiwei_5fda429_20261012/full_valid_with_credential.json` | 625 | `34ab596e566fad94d6c9f93334c8185a3e2b6cf4c08e6fd0edff52463d7d040c` |
| `REQ2_zhiwei_5fda429_20261012/run_req2.py` | 3593 | `364ef4381b46b37c5fecbdfeaf2e9e1d50b8c92c024d13fe4a20afeb34a2f35f` |
| `REQ2_zhiwei_5fda429_20261012/SHA256SUMS.json` | 1201 | `011100f6f7c6dff77ebfe9033c0da9b050cb9c0bb455ded23727eff583a43a69` |
| `REQ2_zhiwei_5fda429_20261012/给Coder_REQ2当前提交复跑_20261012.md` | 6944 | `8329f058ff5f7da640f90cb48653f0cc820e5641b82efbb74c191dfe45ab6def` |
| `REQ2_zhiwei_5fda429_20261012/logs/binding.stdout.log` | 371 | `e81ded2de96929c212a3cf17fa6cbe64c6126e9992f96368fb30f6d646f29143` |
| `REQ2_zhiwei_5fda429_20261012/logs/with_credential.stdout.log` | 1329 | `644c60ee2beb17624a9470531ea2d1119dae5d4634ae85f7f3a4bb8231aa4a18` |
| `REQ2_zhiwei_5fda429_20261012/logs/without_credential.stdout.log` | 1323 | `bc61b9fd2412736ff2c00a1fcb7e646cc10665a7b33b4517d9a5011c7aa248ab` |
| `REQ2_zhiwei_5fda429_20261012/received_original.zip` | 19296 | `cacb21d8e811f4e0ed2c198e630030f3afc86bc7d54282b68ae9ef2b0f7370d3` |
| （空 stderr）`logs/*.stderr.log` ×3 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |

## 固定关系

- **REPLAYED_CODE_COMMIT** = `5fda4298772a69d850d0d3bfe898c5cce546dcc8`
- **REVIEWED_HEAD** = `5271b22`（此后仅 .gitignore / 评审索引 / 复跑记录变更，未动 Q3 执行关键源码）
- **FULL_VALID run-id 一致性**: 船长轮 `f1e7d604…`；知微轮 `2d17082d…`（各自与其 FULL_VALID 行匹配）

## Coder 复核声明

- 知微包 `SHA256SUMS.json`：**12/12 匹配**（复核通过）。
- 全目录口令扫描：**无字面命中**（仅变量名）。
- 本目录为**只读归档**；不修改任何 Q3 执行源码。

---

## V5 复跑证据（固定提交 `6afe56a`）

| 目录 | 执行 | 证据层 | 结果 |
|---|---|---|---|
| `REQ2_captain_admin_6afe56a_20261012/` | 船长（管理员） | `TERMINAL_TEXT` | `Q3_QUALIFICATION = PASS`（run_id `7fb2b985…`） |
| `REQ2_zhiwei_6afe56a_20261012/` | 知微（未提升） | `NATIVE_JSON + ORIGINAL_ZIP` | `NOT_EVALUATED`；十角色 **10/10 匹配**，digest `10c4548e…` |

- 固定对象：`6afe56a37865e965eebcdb1ee81b5e7c051b2767`（v5 候选）。
- 计数：`access_matrix 14 · dacl 14 · adversarial 61 · provenance 13 · isolation 21(管理员)/20+N-A(未提升) · worker 4 · audit 5 · reset_chain 113 · consumer 17`。
- 两种权限上下文**分别如实保留，互不替代**。
