# -*- coding: utf-8 -*-
"""按台账表实际格式（编号标签 + blob）复算，验证 8 个值确为 SHA-1。"""
import sys, os, re, subprocess, hashlib, glob
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
C = open(os.path.join(ROOT, "afterglow_design/C_decision_ledger.md"), encoding="utf-8").read()

# 解析：| `NN` 标签 | `40hex` |
rows = re.findall(r"\|\s*`(\d{2})`[^|]*\|\s*`([0-9a-f]{40})`\s*\|", C)
print("解析到行数:", len(rows))

# 建立编号 → 文件路径映射
r2dir = os.path.join(ROOT, "discussions", "r2")
mapping = {}
for p in glob.glob(os.path.join(r2dir, "*.md")):
    base = os.path.basename(p)
    m = re.match(r"^(\d{2})_", base)
    if m:
        mapping[m.group(1)] = "discussions/r2/" + base

print("\n=== 逐行复算 ===")
m_sha1 = m_sha256 = 0
checked = 0        # 真正核过的行数
skipped = []       # 文件不在树内而跳过的编号
for num, val in rows:
    rel = mapping.get(num)
    if not rel:
        skipped.append((num, "本树无该文件"))
        print("  %s  SKIP（本树无 discussions/r2/%s_*.md）" % (num, num))
        continue
    r = subprocess.run(["git", "ls-files", "-s", rel], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    if not r.stdout.strip():
        skipped.append((num, "git 未跟踪"))
        print("  %s  SKIP（git 未跟踪该文件）" % num)
        continue
    sha1 = r.stdout.split()[1]
    blob = subprocess.run(["git", "cat-file", "blob", sha1], cwd=ROOT,
                          capture_output=True).stdout
    s256 = hashlib.sha256(blob).hexdigest()
    a = (sha1 == val)
    b = (s256[:40] == val)
    m_sha1 += a; m_sha256 += b
    checked += 1
    print("  %s  val=%s  SHA1=%s  sha256[:40]=%s"
          % (num, val[:10], "OK" if a else "XX", "OK" if b else "XX"))

n = len(rows)
print("\n合计 %d 行：实核 %d 行（SHA-1 匹配 %d，sha256[:40] 匹配 %d），跳过 %d 行"
      % (n, checked, m_sha1, m_sha256, len(skipped)))

# ---------------------------------------------------------------- SKIP 判定
# 若被核文件在本树中缺失（例如 exp 树只到 00-12，而台账引用 16/18/19/20/21），
# 则本脚本无法完成复算 —— 报 SKIP，不报 FAIL。
#   ⇒ 不报失败（那会误导为"数字错了"）
#   ⇒ 也不报通过（没核不能算核过）
if checked == 0:
    print()
    print("=" * 74)
    print("SKIP · 台账引用的 r2 文件在本树中全部缺失，无法做 SHA-1 复算")
    print("  跳过的编号: %s" % ", ".join(x[0] for x in skipped))
    print("  说明: 台账引用的 16/18/19/20/21 等文件不在本树的 discussions/r2 下")
    print("        （exp 树只到 00-12）。请在有完整 r2 的分支上复跑。")
    print("  ⇒ 本脚本未完成任何一行复算。SKIP != PASS。")
    print("=" * 74)
    sys.exit(0)

ok = bad = 0
def chk(c, m):
    global ok, bad
    if c: ok += 1; print("  [OK]", m)
    else: bad += 1; print("  [XX]", m)

print()
chk(n == 8, "表内 8 行（实得 %d）" % n)
chk(m_sha1 == checked, "已核行全部等于 git blob SHA-1（%d/%d）" % (m_sha1, checked))
chk(m_sha256 == 0, "无一等于 sha256[:40]（%d）" % m_sha256)
if skipped:
    print("  [note] 跳过 %d 行：%s"
          % (len(skipped), ", ".join("%s(%s)" % x for x in skipped)))
chk("（git blob SHA-1，40 位）" in C, "表头标签正确")
print("\n核对：OK %d，问题 %d" % (ok, bad))
sys.exit(0 if bad == 0 else 1)
