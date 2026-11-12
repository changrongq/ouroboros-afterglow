# -*- coding: utf-8 -*-
"""登记表 / 工作树 / HEAD 三方比对。

存在理由（B_30 第五节第 ③ 条）：
  一份不同步的登记表，【不会报错】。那就和「写了检查但不会响」同一个病。
  所以本脚本的唯一职责是：不一致时【非零退出并指出是哪一行】。

检查三件事：
  ① 表里每行的 blob == `git rev-parse HEAD:<path>` 的值
     ⇒ 保证表与【已提交内容】一致
  ② 表里每行的 blob == 该文件【工作树字节】算出的 git blob
     ⇒ 保证表与【磁盘现状】一致（能抓「改了但没提交」）
  ③ 表登记的路径都存在

退出码：
  0 = 三方一致
  1 = 存在不一致
  2 = 无法读取登记表（基础设施问题，不得视为通过）

边界：
  本脚本【不检查登记表自己的 blob】（登记表按设计不在表内，走 Coder 消息）。
  但【会检查表里 check_registry.py 自己那一行】——它已登记在表内，
  所以输出里会看到 `✅ check_registry.py …`。这两件事不要混。
  （睫 第三轮：原 docstring 写「不检查自己所在文件」，与实跑输出不符，已改。）
"""
import sys, os, re, subprocess, hashlib

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
REGISTRY = os.path.join(
    ROOT, "reports", "review_history",
    "阶段B_30_文件版本登记表_Coder_20261111.md")

# 表内只登记这些目录下的文件；用于把「文件名」还原成「仓库相对路径」
# 注：表里可以写【带子目录的路径】（如 `.github/workflows/x.yml`），
#     resolve() 会先按原样试，再退到各根目录拼接。
SEARCH_ROOTS = [
    os.path.join("reports", "review_history"),
    os.path.join("tools", "v2_l1_verifier"),
    os.path.join(".github", "workflows"),
]

ROW_RE = re.compile(r"^\|\s*`([^`]+)`\s*\|(.*\|\s*)`([0-9a-f]{40}|PENDING_FIRST_COMMIT)`\s*\|\s*$")

# 允许填 PENDING_FIRST_COMMIT 的值：
#   新文件在【首次提交前】无法知道自己的 blob（blob 由提交内容决定）。
#   ⇒ 这一格在首次提交前只能是占位符，提交后才可回填。
#   ⇒ 但【不能一直挂着】：若 HEAD 中已存在该文件而表里仍是 PENDING
#     ⇒ 视为不一致（否则「首次提交」会变成一个永远可以用的借口）。
PENDING = "PENDING_FIRST_COMMIT"


def git_blob_of_bytes(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(data) + data).hexdigest()


def head_blob(relpath: str):
    r = subprocess.run(["git", "rev-parse", "HEAD:%s" % relpath],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return r.stdout.strip() if r.returncode == 0 else None


def worktree_blob(relpath: str):
    """工作树文件的 blob，口径必须与 HEAD 一侧一致。

    ⇒ 【不能用原始字节算】：本仓库有 .gitattributes，git 会把工作树的 CRLF
      规范化为 LF 再入库。原始字节哈希与 HEAD blob 差的不是内容，是换行。
    ⇒ 所以这里直接调用 `git hash-object <path>`，让 git 自己按
      .gitattributes 规范化，避免「检查器与 git 口径不同」造成的假不一致。
    ⇒ 因此「与工作树一致」的准确含义是
      【经仓库属性处理后的 Git 对象一致】，不等于原始磁盘字节逐字节相等。
      （知微 第三轮 5.3 末段指出此点，已在此写明。）
    ⇒ 本函数【不再写死任何具体 blob 值】——写死的历史值会随文件改动过期，
      而且检查器抓不到自己 docstring 里那个过期值（睫 第三轮 格三）。
    """
    p = os.path.join(ROOT, relpath)
    if not os.path.exists(p):
        return None
    r = subprocess.run(["git", "hash-object", relpath],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    out = r.stdout.strip()
    return out if (r.returncode == 0 and len(out) == 40) else None


def resolve(fname: str):
    """把表里的文件名还原成仓库相对路径。

    ⇒ 先按【原样】当作仓库相对路径试一次：
      表里允许写 `.github/workflows/x.yml` 这种带子目录的路径。
    ⇒ 再退到各 SEARCH_ROOTS 拼接（兼容只写文件名的老行）。
    ⇒ 都不存在时，若原样路径看起来带目录，就原样返回，
      让调用方报「HEAD/工作树缺失」而不是拼出一个错误路径。
    """
    direct = fname.replace(os.sep, "/")
    if os.path.exists(os.path.join(ROOT, direct)):
        return direct
    for root in SEARCH_ROOTS:
        cand = os.path.join(root, fname)
        if os.path.exists(os.path.join(ROOT, cand)):
            return cand.replace(os.sep, "/")
    if ("/" in direct) or ("\\" in fname):
        return direct
    # 已删除文件：按 reports 路径猜，供存在性检查报出来
    return os.path.join(SEARCH_ROOTS[0], fname).replace(os.sep, "/")


def parse_rows(text: str):
    rows = []
    for line in text.splitlines():
        m = ROW_RE.match(line.strip())
        if m:
            rows.append((m.group(1), m.group(3)))
    return rows


def main():
    if not os.path.exists(REGISTRY):
        print("[INFRA] 找不到登记表: %s" % REGISTRY)
        return 2

    text = open(REGISTRY, encoding="utf-8").read()
    rows = parse_rows(text)
    if not rows:
        print("[INFRA] 登记表里解析出 0 行——表格格式可能被改了")
        return 2

    print("登记表: %s" % os.path.basename(REGISTRY))
    print("解析到 %d 行" % len(rows))
    print()

    bad = []
    pending = []
    for fname, declared in rows:
        rel = resolve(fname)
        h = head_blob(rel)
        w = worktree_blob(rel)

        if declared == PENDING:
            # 占位符只在【文件尚未进入 HEAD】时合法
            if h is not None:
                bad.append((fname, "表仍是 PENDING 但 HEAD 已有该文件（须回填）",
                            declared, h[:12]))
                print("  ❌ %-56s 表=%s 但 HEAD 已有 %s"
                      % (fname[:56], PENDING, h[:12]))
            else:
                pending.append(fname)
                print("  ⏳ %-56s 未首次提交（工作树=%s）"
                      % (fname[:56], (w or "-")[:12]))
            continue

        if h is None:
            bad.append((fname, "HEAD 中不存在", declared[:12], "-"))
            print("  ❌ %-56s HEAD 中不存在" % fname[:56])
            continue
        if h != declared:
            bad.append((fname, "表≠HEAD", declared[:12], h[:12]))
            print("  ❌ %-56s 表=%s HEAD=%s" % (fname[:56], declared[:12], h[:12]))
            continue

        # ---- 工作树缺失分支（知微 ZBR-01 第一层）----
        # 原代码写 `if w is not None and w != declared:` ——
        #   文件被删时 worktree_blob 返回 None，反而【绕过】了检查，
        #   随后照常打印 ✅，并宣称「与工作树完全一致」。
        # ⇒ 缺失必须判失败，且要与「哈希算不出」区分开。
        if w is None:
            if os.path.exists(os.path.join(ROOT, rel)):
                why = "工作树 blob 算不出（HASH_UNAVAILABLE）"
            else:
                why = "工作树文件缺失（FILE_MISSING）"
            bad.append((fname, why, declared[:12], "-"))
            print("  ❌ %-56s %s" % (fname[:56], why))
            continue
        if w != declared:
            bad.append((fname, "表≠工作树（改了未提交）", declared[:12], w[:12]))
            print("  ⚠️  %-56s 表=%s 工作树=%s（未提交改动）"
                  % (fname[:56], declared[:12], w[:12]))
            continue
        print("  ✅ %-56s %s" % (fname[:56], declared[:12]))

    print()
    if bad:
        print("不一致 %d 项：" % len(bad))
        for f, why, a, b in bad:
            print("   - %s | %s | 表=%s vs %s" % (f, why, a, b))
        print()
        print("[FAIL] 登记表与现实不一致")
        return 1

    # ---- 覆盖性检查：该登记的文件是否漏登记 ----
    # 理由：只校验「表里有的行」是不够的。
    #   删掉一行，其余行仍各自正确 ⇒ 不报错 ⇒ 漏登记的文件永远不会被核对。
    #   这正是「会失败的检查，最怕的不是失败，是没响」。
    #
    # 【知微 ZBR-01 第二层】：
    #   原实现只用 os.listdir 枚举【当前磁盘】上的文件。
    #   于是「删文件 + 删表行」同时发生时，该文件已不在「应检查」集合里，
    #   漏登记检查也不响 ⇒ 声称「15 行一致、覆盖无遗漏」。
    # ⇒ 现改为【三个来源的并集】：
    #   ① 固定 HEAD 树里的在役路径（文件丢了也还在 HEAD 里，能抓住）
    #   ② 工作树当前路径（能抓住新增未登记）
    #   ③ 表内已登记的路径（能抓住文件与行同时消失但 HEAD 仍有）
    #
    # 范围限定（不是全仓）：只要求【本阶段在役】的文件被登记 ——
    #   · tools/v2_l1_verifier/*.py  全部
    #   · review_history/阶段B_2[2-9]_*.md 与 阶段B_3*_*.md（B_22 起的规范链与记录）
    # 早于 B_22 的历史文档【不强制登记】，但它们若已被登记仍会被校验。
    registered = {resolve(f) for f, _ in rows}
    missing = []
    import re as _re
    PHASE_RE = _re.compile(r"^阶段B_(2[2-9]|3\d|[4-9]\d+)_.*\.md$")

    def in_scope(rel):
        fn = os.path.basename(rel)
        if rel.startswith("tools/"):
            return fn.endswith(".py")
        if rel.startswith(".github/"):
            return fn.endswith((".yml", ".yaml"))
        return bool(PHASE_RE.match(fn))

    def is_registry_itself(rel):
        return os.path.abspath(os.path.join(ROOT, rel)) == os.path.abspath(REGISTRY)

    candidates = set()

    # ① 固定 HEAD 树（用 ls-tree 枚举，不依赖磁盘）
    #   【必须用 -z】：默认输出会把非 ASCII 路径转成 "\351\230\266…" 八进制转义，
    #   于是中文文件名与任何匹配规则都对不上，这一源会静默变空 ——
    #   那样「删文件+删表行」仍然不响（实测过，正是知微 ZBR-01 第二层）。
    #   -z 用 NUL 分隔且不转义，得到的是真实字节。
    r = subprocess.run(["git", "ls-tree", "-r", "-z", "--name-only", "HEAD",
                        "tools/v2_l1_verifier", "reports/review_history",
                        ".github/workflows"],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    head_ok = (r.returncode == 0)
    if head_ok:
        for raw in r.stdout.split("\x00"):
            rel = raw.strip().replace(os.sep, "/")
            if rel:
                candidates.add(rel)
    else:
        print("[WARN] git ls-tree 失败，HEAD 源不可用（覆盖性将不完整）")
        print("       %s" % (r.stderr or "").strip()[:160])

    # ② 工作树当前路径
    for root in SEARCH_ROOTS:
        d = os.path.join(ROOT, root)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            rel = os.path.join(root, fn).replace(os.sep, "/")
            if os.path.isfile(os.path.join(ROOT, rel)):
                candidates.add(rel)

    # ③ 表内已登记路径
    candidates |= registered

    for rel in sorted(candidates):
        if not in_scope(rel):
            continue
        if rel.endswith(".bak") or os.path.basename(rel).startswith("__"):
            continue
        if is_registry_itself(rel):
            continue
        if rel not in registered:
            missing.append(rel)

    if missing:
        print()
        print("漏登记 %d 个文件（在役但表里没有）：" % len(missing))
        for m in missing:
            exists = os.path.exists(os.path.join(ROOT, m))
            print("   - %s%s" % (m, "" if exists else "   ← 工作树已缺失，但 HEAD 里仍在役"))
        print()
        print("[FAIL] 登记表覆盖不全")
        return 1

    print("[OK] 登记表 %d 行与 HEAD 及工作树完全一致" % len(rows))
    print("[OK] 覆盖性：该登记的文件无遗漏")
    if pending:
        print()
        print("⏳ 尚未首次提交 %d 项（表内为 PENDING_FIRST_COMMIT）：" % len(pending))
        for p in pending:
            print("   - %s" % p)
        print("   ⇒ 这些文件提交后必须回填真实 blob，否则下次运行会判为不一致。")
    print()
    print("⇒ 注意：本结论【只说明表与现实自洽且无遗漏】，")
    print("   不说明表里的值本身正确——那仍需三方独立跑一遍。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
