# -*- coding: utf-8 -*-
"""BINDING 清单存在性检查 —— 勘误005 E-27

E-27 原文：
    凡写入 BINDING 的文档，必须在【同一动作】里确认它在仓库中存在
    （取一次 blob / 列一次目录），不得凭「我写过」或「我提过」记入。
    理由：BINDING 是一份【指向物】的清单，指向不存在的路径，
          等于让所有下游引用悬空。

⚠ 这条的由来：Mion 把「勘误005」当成已存在的文档引用了一整天，
  写进 BINDING、被我按信里摘要实现、通过了 —— 而那份文档【从未创建】。
  ⇒ 所以本检查不是形式主义，它抓过一次真实事故。

⚠ 执行范围（Mion 2026-11-28 §三 要求登记）：
  · 本检查【不是】独立 CI 入口 —— 本阶段没有 CI，不造假入口。
  · 执行方式：由 test_blayer_batch1.py 的 T-13 调用 ⇒ 谁跑测试谁触发。
  · 保护的是【跑过测试的提交】。
  · 不保护【没跑测试的提交】。
  ⇒ 因此报告不得写成「BINDING 已被校验」，
    只许写成「跑过测试时，BINDING 五份经 HEAD blob 核对」。

做法：对 BINDING 清单里每个文件名取一次 git blob。
      取不到 ⇒ 红。
      ⚠ 不检查「文件存在」（工作区可能有未提交的文件）；
        检查「在 HEAD 里存在」—— 因为 BINDING 是给出别人看的，
        别人看到的是提交，不是我的工作区。
      ⚠ 已知风险：本检查的【输入】是人工写的文件名。
        我曾把「附录A_沙盘证据搬录」写成「录入」，报了一次假 MISS。
        ⇒ 报 MISS 时先核自己的输入，再断定对方缺失。
"""
from __future__ import annotations

import os
import subprocess
import sys

#: BINDING 清单（逐项）
#:
#: v0.5（2df4517）起绑定从六份收回到【一份】：
#:   v0.4 + 附录A + 勘误004 + 005 + 006 已全部合并进 v0.5 正文。
#:   BINDING = A层_主设计v0.5_合并定稿_收口版_Mion_20261128.md（唯一）
#:
#: ⚠ 旧版文件仍在仓库里保留（Mion 明写「旧版全部保留、不覆盖」），
#:   但它们【不是】BINDING 的一部分。
#:   ⇒ 本清单只列 BINDING 实际指向的文件。
#:   ⇒ 若有人把旧勘误又列回来，本检查不会自动发现 ——
#:     那需要另一条「BINDING 只允许一份」的断言（见 T-13 ①）。
BINDING_DOCS = [
    ("v0.5", "A层_主设计v0.5_合并定稿_收口版_Mion_20261128.md"),
]

#: 已被合并进 BINDING、不得再单独列为 BINDING 的文件（保留在仓库，但不是绑定物）
SUPERSEDED_DOCS = [
    ("v0.4", "A层_主设计候选v0.4_合并定稿_Mion_20261128.md"),
    ("附录A", "附录A_沙盘证据搬录_Mion_20261128.md"),
    ("勘误004", "A层_v0.4_勘误004_Mion_20261128.md"),
    ("勘误005", "A层_v0.4_勘误005_Mion_20261128.md"),
    ("勘误006", "A层_v0.4_勘误006_Mion_20261128.md"),
]

DESIGN_DIR = "afterglow_design"


def _repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    # <root>/afterglow_a/prototype/
    return os.path.dirname(os.path.dirname(here))


def head_blob(rel_path: str, repo_root: str = None):
    """取 HEAD 里该路径的 blob sha。取不到返回 None。"""
    if repo_root is None:
        repo_root = _repo_root()
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD:%s" % rel_path],
            cwd=repo_root, capture_output=True, text=True,
            encoding="utf-8", errors="replace")
    except OSError:
        return None
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def check_binding_docs(repo_root: str = None) -> dict:
    """返回 { ok, results: [(标签, 文件名, blob_or_None)] }"""
    if repo_root is None:
        repo_root = _repo_root()
    results = []
    for label, fn in BINDING_DOCS:
        rel = "%s/%s" % (DESIGN_DIR, fn)
        blob = head_blob(rel, repo_root)
        results.append((label, fn, blob))
    ok = all(b is not None for _l, _f, b in results)
    return {"ok": ok, "results": results}


def main() -> int:
    print("=" * 78)
    print("E-27 · BINDING 清单存在性（取 HEAD blob，不取工作区）")
    print("=" * 78)
    rep = check_binding_docs()
    failing = []
    for label, fn, blob in rep["results"]:
        if blob is None:
            failing.append((label, fn))
            print("  [MISS] %-8s %s" % (label, fn))
        else:
            print("  [ OK ] %-8s %s  blob=%s" % (label, fn, blob[:8]))
    print()
    print("=" * 78)
    if failing:
        print("!! E-27 violated: %d 份 BINDING 文档在 HEAD 里不存在" % len(failing))
        for label, fn in failing:
            print("   - %s: %s" % (label, fn))
        print("   ⇒ BINDING 指向不存在的路径，所有下游引用悬空。")
        print("=" * 78)
        return 1
    print("%d 份 BINDING 文档全部存在（v0.5 起绑定只有一份）"
          % len(rep["results"]))
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
