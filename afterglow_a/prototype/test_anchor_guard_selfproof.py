# -*- coding: utf-8 -*-
"""锚点守卫的自证（Mion 2026-11-27 第二封 §一，A1）

Mion 的话：

    「『它刚刚响过一次』 ≠ 『它被守住了』。
     它响过：证明【当时】它能响。
     有测试守：证明【以后】它还能响。」

    「A1  一条变异：把 L755 的『0 命中 ⇒ INVALID』分支改成 pass / continue。
      ⇒ 驱动必须变红，或必须报出一个与已知答案相反的结论。
      ⇒ 关掉它之后仍然绿的，不算守住。」

⚠ 本文件测的是【驱动自己的检查】，不是被测代码。
  这是「用尺子量尺子」警戒线的正确用法：
  警戒的不是「量自己」，而是「量完自己还说合格」。
  ⇒ 这里的要求是：把守卫关掉后，必须有东西变红。

运行：python afterglow_a/prototype/test_anchor_guard_selfproof.py
"""
from __future__ import annotations

import inspect
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = []


def case(cid, name):
    def deco(fn):
        def run():
            try:
                d = fn()
                RESULTS.append((cid, name, True, d))
                print("  [PASS] %s %s — %s" % (cid, name, d))
            except AssertionError as e:
                RESULTS.append((cid, name, False, str(e)))
                print("  [FAIL] %s %s — %s" % (cid, name, e))
            except Exception as e:
                RESULTS.append((cid, name, False, repr(e)))
                print("  [ERR ] %s %s — %s" % (cid, name, e))
                traceback.print_exc()
        return run
    return deco


import test_mutations_importance as TM  # noqa: E402


# ================================================ A1 本体

@case("AG-1", "前置：apply_mut 对错锚点返回 False（守卫在）")
def ag1():
    """先证明守卫【当且仅当】锚点错时触发。

    用真实 apply_mut 跑一个必然 0 命中的锚点。
    需要临时目录，所以直接用 tempfile 复制。
    """
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        TM.copy_all(td)
        ok, note = TM.apply_mut(td, "__THIS_ANCHOR_DOES_NOT_EXIST__", "x")
    assert ok is False, "错锚点竟然返回成功 ⇒ 守卫不在"
    assert "0 次" in note, "报错文本未说明命中次数：%r" % note
    return "错锚点 ⇒ False / %s" % note


@case("AG-2", "A1 核心：把守卫改成 pass 后，驱动会放过错锚点")
def ag2():
    """⚠ 这是 Mion 要求的「关掉它之后仍然绿的，不算守住」。

    做法：复制驱动到临时目录，把 apply_mut 里的 `return False, ...`
    改成 `pass  # 关掉守卫`（于是 n != 1 时【不返回】，继续往下改文件），
    然后以【子进程】导入该副本，验证：
        · 关掉后 apply_mut 对错锚点返回 True（= 放过）
        · 而原版返回 False
    ⇒ 两者不同，说明守卫【确实在起作用】，不是装饰。
    """
    import tempfile
    import shutil

    guard = '        return False, "锚点出现 %d 次（应为 1）" % n'

    with tempfile.TemporaryDirectory() as td:
        src_p = os.path.join(HERE, "test_mutations_importance.py")
        with open(src_p, encoding="utf-8") as f:
            src = f.read()

        assert guard in src, (
            "守卫语句未找到，源码可能已改。当前 apply_mut 内容：\n%s"
            % inspect.getsource(TM.apply_mut))

        # 关掉守卫：让它不 return，继续往下执行（把文件原样"替换 0 次"）
        disabled = src.replace(
            guard,
            '        pass  # MUTANT: 守卫已关闭（A1 用）', 1)
        assert disabled != src, "替换失败"

        # 副本放【整份原型的拷贝目录】里 ——
        # 驱动用 HERE = dirname(__file__)，只拷一个文件会让 HERE 指向
        # 临时目录，copy_all 找不到 afcore.py。
        work = os.path.join(td, "proto")
        shutil.copytree(HERE, work,
                        ignore=shutil.ignore_patterns("__pycache__",
                                                      "reports", "*.npy"))
        copy_p = os.path.join(work, "tm_disabled.py")
        with open(copy_p, "w", encoding="utf-8", newline="\n") as f:
            f.write(disabled)

        # 在子进程里导入副本，避免污染本进程的模块缓存
        probe = (
            "import sys, tempfile\n"
            "sys.path.insert(0, %r)\n"
            "import tm_disabled as D\n"
            "with tempfile.TemporaryDirectory() as t:\n"
            "    D.copy_all(t)\n"
            "    ok, note = D.apply_mut(t, '__NO_SUCH_ANCHOR__', 'x')\n"
            "print('[PROBE] ok=%%s note=%%s' %% (ok, note))\n"
            % work
        )
        import subprocess
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run([sys.executable, "-c", probe],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace",
                           env=env, timeout=180)
        out = (r.stdout or "") + (r.stderr or "")
        assert "[PROBE]" in out, "探针未执行：%s" % out[-1200:]
        assert "[PROBE] ok=True" in out, (
            "关掉守卫后仍未放过错锚点 ⇒ 本反证失去意义。输出：%s"
            % out[-1200:])
    return "原版 False / 关掉守卫后 True —— 守卫有分辨力"


@case("AG-3", "A1 落点：守卫必须导致 INVALID 状态，而非静默继续")
def ag3():
    """守卫返回 False 之后，主循环必须把它记成 INVALID。

    只证明 apply_mut 返回 False 还不够 —— 若 main() 拿到 False
    仍然 continue 且不记行，那等于没拦。
    """
    src = inspect.getsource(TM.main)
    assert "if not ok:" in src, "main() 里没有对 apply_mut 失败的分支"
    assert '"INVALID"' in src, "main() 未把失败记成 INVALID"
    # INVALID 必须在 FAIL_STATES 里（否则不会让 verdict 变红）
    assert "INVALID" in TM.FAIL_STATES, (
        "INVALID 不在 FAIL_STATES ⇒ 即使记了 INVALID 也不会让证据失败")
    return "main() 有 not ok 分支 ⇒ 记 INVALID，且 INVALID ∈ FAIL_STATES"


@case("AG-4", "A1 端到端：真驱动对 15 个锚点各命中恰好一次")
def ag4():
    """守卫存在还不够，要证明【当前】15 个锚点全部有效。

    这是「守卫没误报」的那一半 —— 若守卫过严，正常锚点也会被拦。
    """
    target = os.path.join(HERE, TM.TARGET)
    with open(target, encoding="utf-8") as f:
        src = f.read()
    bad = []
    for m in TM.MUTATIONS:
        n = src.count(m[2])
        if n != 1:
            bad.append((m[0], n))
    assert not bad, "以下锚点不是恰好命中一次：%r" % bad
    return "15 个锚点均 count==1"


@case("AG-5", "反证：AG-4 不是空的 —— 构造一个错锚点必须被 AG-4 的逻辑抓到")
def ag5():
    """若 AG-4 的循环写错（比如永远不检查），它也会绿。
    这里用同一段逻辑跑一个【必然 0 命中】的锚点，必须被抓到。
    """
    target = os.path.join(HERE, TM.TARGET)
    with open(target, encoding="utf-8") as f:
        src = f.read()

    fake = [("FAKE", "d", "__DEFINITELY_NOT_IN_SOURCE__", "", set())]
    bad = [(m[0], src.count(m[2])) for m in fake if src.count(m[2]) != 1]
    assert bad == [("FAKE", 0)], (
        "AG-4 的检查逻辑对错锚点未报错 ⇒ AG-4 可能是空的。实测 %r" % bad)
    return "错锚点被抓到（count=0）"


# ================================================ 汇总
def main():
    print("=" * 80)
    print("锚点守卫自证（Mion 2026-11-27 第二封 §一 A1）")
    print("=" * 80)
    print()
    for f in (ag1, ag2, ag3, ag4, ag5):
        f()
    passed = sum(1 for r in RESULTS if r[2])
    total = len(RESULTS)
    print()
    print("=" * 80)
    print("合计 %d  通过 %d  失败 %d" % (total, passed, total - passed))
    print("=" * 80)
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
