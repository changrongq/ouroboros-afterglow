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
for num, val in rows:
    rel = mapping.get(num)
    if not rel:
        print("  %s → 找不到对应文件" % num); continue
    r = subprocess.run(["git", "ls-files", "-s", rel], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    if not r.stdout.strip():
        print("  %s → git 取不到" % num); continue
    sha1 = r.stdout.split()[1]
    blob = subprocess.run(["git", "cat-file", "blob", sha1], cwd=ROOT,
                          capture_output=True).stdout
    s256 = hashlib.sha256(blob).hexdigest()
    a = (sha1 == val)
    b = (s256[:40] == val)
    m_sha1 += a; m_sha256 += b
    print("  %s  val=%s  SHA1=%s  sha256[:40]=%s"
          % (num, val[:10], "✓" if a else "✗", "✓" if b else "✗"))

n = len(rows)
print("\n合计 %d 行：与 SHA-1 匹配 %d，与 sha256[:40] 匹配 %d" % (n, m_sha1, m_sha256))

ok = bad = 0
def chk(c, m):
    global ok, bad
    if c: ok += 1; print("  [OK]", m)
    else: bad += 1; print("  [XX]", m)

print()
chk(n == 8, "表内 8 行（实得 %d）" % n)
chk(m_sha1 == n, "全部值等于 git blob SHA-1（%d/%d）" % (m_sha1, n))
chk(m_sha256 == 0, "无一等于 sha256[:40]（%d）" % m_sha256)
chk("（git blob SHA-1，40 位）" in C, "表头标签正确")
print("\n核对：OK %d，问题 %d" % (ok, bad))
sys.exit(0 if bad == 0 else 1)
