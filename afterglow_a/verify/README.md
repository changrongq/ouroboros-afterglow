# afterglow_a/verify —— 被引用过的验证脚本

这些脚本是审查意见里被实际引用过的。把它们入库，是为了让「我报过的数字」能被外部复跑。

## 为什么只有这几个

`.local_scratch/` 下曾有 140 支脚本，大部分是一次性调试件（改名、修错字、临时探测）。
只入被台账或审查函引用、能独立重现某个结论的那些。

⇒ 未入库的调试脚本不入库，不是遗漏，是它们不构成可复算证据。

## 清单

| 脚本 | 验证什么 | 结论数 |
|---|---|---:|
| `v_jie_all.py` | 睫三格 + 一句话级三处 | 28 |
| `v_table.py` | C 台账引用身份表 8 行逐行 SHA-1 复算 | 4 |
| `chk_mails.py` | 两封函结构（围栏 / 行尾 / 固定点 / 无自我剖白 / 表格不断裂） | 26 |
| `prereview.py` | 三份交付物完整性 + 审查者会问什么 | 37 |
| `verify_claims.py` | 函中所有数字与源码引用逐条复算 | 24 |
| `verify_both_enc.py` | UTF-8 / GBK 双终端编码下判定数字一致 | 6 |
| `v24.py` | 知微审查落盘 + ZA-01~04 四项修复核验 | 28 |
| `v25.py` | 睫成文落盘 + 三项待办落实核验 | 35 |
| `za04_verify.py` | ZA-04 修复的反证（旧逻辑算 CAUGHT，新逻辑判 NOT_EXECUTED） | — |
| `mut_gbk.py` | GBK 修复的非空转证明（把加固改回 no-op 会重新崩溃） | — |

## 怎么跑

```bash
# 在仓库根目录
python afterglow_a/verify/v25.py
python afterglow_a/verify/v_table.py
python afterglow_a/verify/verify_both_enc.py
```

```text
⇒ Python 3.9+，无第三方依赖。
⇒ 脚本内的 ROOT 由 __file__ 推出，不含本机绝对路径。
⇒ 部分脚本会读写 afterglow_a/prototype/reports/ 下的 JSON，属预期行为。
```

## 一条边界

```text
这些脚本证明的是【我自己报的数字与文件状态一致】，
不是【系统具备某种能力】。
⇒ 它们属工程检查，不是 C1/C2/C3 任何一级证据。
```
