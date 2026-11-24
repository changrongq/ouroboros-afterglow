# -*- coding: utf-8 -*-
"""验证 verify_both_enc.py 真的会失败（否则它是空转检查）。

做法：临时把 _harden_stdio 弄成 no-op，确认 GBK 下会重新崩溃。
"""
import sys, os, shutil, subprocess, tempfile
sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

tmp = tempfile.mkdtemp(prefix="gbkmut_")
try:
    # 复制整个 afterglow_a 与需要的文件
    shutil.copytree(os.path.join(ROOT, "afterglow_a"),
                    os.path.join(tmp, "afterglow_a"))

    tgt = os.path.join(tmp, "afterglow_a", "prototype", "test_mutations_v4.py")
    s = open(tgt, encoding="utf-8", newline="").read()

    # 变异：把 _harden_stdio 变成空函数
    old_body = """    for stream_name in ("stdout", "stderr"):
        st = getattr(sys, stream_name, None)
        if st is None:
            continue
        try:
            st.reconfigure(encoding="utf-8")
        except Exception:
            try:
                st.reconfigure(errors="backslashreplace")
            except Exception:
                pass"""
    new_body = "    return  # 变异：不做任何加固"
    patched, ok = False, False
    for o, n in ((old_body, new_body),
                 (old_body.replace("\n", "\r\n"), new_body)):
        if o in s:
            s = s.replace(o, n, 1); patched = True; break

    if not patched:
        print("!! 变异锚点未找到 —— 不能判定")
        sys.exit(2)

    # 同时把 print 里的 ASCII 化还原一部分（造一个纯 U+21D2 输出）
    open(tgt, "w", encoding="utf-8", newline="").write(s)
    print("已注入变异：_harden_stdio() 变 no-op")

    # 再把 `print("VERDICT:", verdict)` 之后加一行打印 U+21D2
    s2 = open(tgt, encoding="utf-8", newline="").read()
    s2 = s2.replace('    print("VERDICT:", verdict)',
                    '    print("\\u21d2 测试行")\n    print("VERDICT:", verdict)', 1)
    open(tgt, "w", encoding="utf-8", newline="").write(s2)

    env = dict(os.environ, PYTHONIOENCODING="gbk")
    p = subprocess.run([sys.executable, "afterglow_a/prototype/test_mutations_v4.py"],
                       cwd=tmp, capture_output=True, env=env, timeout=300)
    err = p.stderr.decode("utf-8", errors="replace")
    crashed = "UnicodeEncodeError" in err
    print("  GBK 下断言: rc=%d  崩溃=%s" % (p.returncode, crashed))
    if crashed and p.returncode != 0:
        print("  [OK] 变异后确实崩溃 ⇒ verify 脚本若存在会发现")
    else:
        print("  [XX] 变异后没崩 ⇒ 我的检查可能是空转")

    # 也验证源码层面：harden 被去掉后，之前的 4 行 ASCII 化是否还挡得住
    s3 = open(tgt, encoding="utf-8", newline="").read()
    print("  源码中 _harden_stdio 仍是 no-op:", "变异：不做任何加固" in s3)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
