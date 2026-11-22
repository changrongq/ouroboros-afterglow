# -*- coding: utf-8 -*-
"""
变异测试 v4 —— 修正 v3 对「纵深防御」的误判。

【v3 暴露的问题，必须记下来】
 v3 中 M3 / M3b 被判 MISSED，结论报 FAIL。
 实际查证后发现：这两处是【纵深防御】——
   prev_digest 为空这件事有两道独立检查守着：
     (1) Record.validate()      —— 写入时拒绝
     (2) Store.verify_chain()   —— 读历史时检出
   去掉任意一道，另一道仍会报错。
 ⇒ 所以「单点变异未被捕获」不等于「机制没守」。

【但这里有一个真正的危险，必须显式处理】
 如果我允许「没捕获就算纵深防御」，那我以后每漏一个都可以这么说。
 ⇒ 判定规则改成：
   · 变异未被捕获时，**不接受口头解释**
   · 必须在代码里注册该变异的 redundant_with 字段，指出【另一道检查是谁】
   · 并且由程序【实测】那道检查确实拦住了 —— 拦不住则仍是 MISSED
 ⇒ 没有注册 redundant_with 的未捕获变异，一律判 MISSED。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------- 输出加固
# 目的：在 Windows GBK(cp936) 控制台下也能完整跑完并给出判定，不因打印符号崩溃。
# 背景：钳星 2026-11-22 审查实测 —— 本脚本在 cp936 控制台打印 U+21D2 时
#       抛 UnicodeEncodeError，以 exit 1 退出。
#       判定数字其实已经算出来了，但观感是"失败"。
#       ⇒ 这不是逻辑错，是我把"跨平台可复算"写成了承诺，
#         却只在 UTF-8 终端里验证过。
# 处理：优先切 UTF-8；切不动则降级 errors="backslashreplace"，绝不因输出崩溃。
def _harden_stdio():
    for stream_name in ("stdout", "stderr"):
        st = getattr(sys, stream_name, None)
        if st is None:
            continue
        try:
            st.reconfigure(encoding="utf-8")
        except Exception:
            try:
                st.reconfigure(errors="backslashreplace")
            except Exception:
                pass


_harden_stdio()

# 每条：(名称, 文件, 锚点, 替换, 说明, redundant_with 或 None)
# redundant_with = 另一道检查的【实测探针】描述；若给了，程序会验证它确实拦得住
MUTATIONS = [
    ("M1 放宽 source_kind 闭集（加入 user）", "afcore.py",
     '"unknown",          # 显式未知',
     '"unknown",          # 显式未知\n    "user",             # 变异：放宽',
     "非法值不再被拒", None),

    ("M2 摘要忽略 content 字段", "afcore.py",
     "if k not in DIGEST_FIELDS_EXCLUDED}",
     'if k not in DIGEST_FIELDS_EXCLUDED | {"content"}}',
     "篡改内容查不出来", None),

    ("M3 取消 verify_chain 的 prev_digest 空值检查", "afcore.py",
     '                if not d["prev_digest"]:',
     '                if False:  # 变异',
     "历史侧链完整性检查失效",
     # 退路：删掉空值分支后，elif 分支会因 None != digest 而报错
     "prev_digest_none_by_elif"),

    ("M3b 取消 validate 的 prev_digest 一致性检查", "afcore.py",
     '        if self.revision > 1 and not self.prev_digest:',
     '        if False:  # 变异',
     "写入侧拒绝逻辑失效",
     # 退路：写入时放过，但读历史时 verify_chain 会检出
     "prev_digest_none_by_verify_chain"),

    ("M4 match_kind 恒返回 exact", "afrecover.py",
     "    if r == e:\n        kind",
     "    if True:  # 变异\n        kind",
     "分类恒为 exact", None),

    ("M5 not_run 被吞（未执行读成结果）", "afrecover.py",
     "    if not ran or expected is None:",
     "    if False:  # 变异",
     "未执行被读成结论", None),

    ("M6 工程测试被标成科学结果", "afrecover.py",
     '"engineering_only": True,',
     '"engineering_only": False,  # 变异',
     "工程冒充科学", None),

    ("M7 纠正改为原地覆盖（删除旧版）", "afcore.py",
     '        self._history[record_id].append(d)\n        self._write_log.append({"op": "revise"',
     '        self._history[record_id] = [d]  # 变异：覆盖\n        self._write_log.append({"op": "revise"',
     "旧版被删除，P3 应失败", None),

    ("M8 非法枚举不报错（静默放过）", "afcore.py",
     "        if self.source_kind not in SOURCE_KINDS:",
     "        if False:  # 变异",
     "P1/P4 的拒绝逻辑失效", None),
]


# ---- 纵深防御探针：在【变异后】的环境里，实测另一道检查还拦不拦得住
PROBE = r'''
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath("afcore.py")))
from afcore import RecoveryStore, Record, canonical_digest, SchemaError

PROBE_KIND = sys.argv[1]
SEED = "synthetic/records_seed.json"

def result(ok, msg):
    print("PROBE_RESULT:" + json.dumps({"ok": ok, "msg": msg}))
    sys.exit(0)

if PROBE_KIND == "prev_digest_none_by_elif":
    # 模拟一条 revision>1 且 prev_digest=None 的历史，摘要自洽
    st = RecoveryStore(); st.load_seed(SEED)
    st.revise("syn-0001", {"content": "v2"}, reason="t")
    st._history["syn-0001"][1]["prev_digest"] = None
    d = st._history["syn-0001"][1]
    d["this_digest"] = canonical_digest({k: v for k, v in d.items() if k != "this_digest"})
    ok, probs = st.verify_chain("syn-0001")
    result((not ok) and any("prev_digest" in p for p in probs),
           "verify_chain 拦住了: %s" % (probs,))

elif PROBE_KIND == "prev_digest_none_by_verify_chain":
    # 模拟：写入时放过空 prev_digest，但读历史时能不能被抓到
    st = RecoveryStore(); st.load_seed(SEED)
    st.revise("syn-0001", {"content": "v2"}, reason="t")
    st._history["syn-0001"][1]["prev_digest"] = None
    d = st._history["syn-0001"][1]
    d["this_digest"] = canonical_digest({k: v for k, v in d.items() if k != "this_digest"})
    ok, probs = st.verify_chain("syn-0001")
    result((not ok) and any("prev_digest" in p for p in probs),
           "verify_chain 拦住了: %s" % (probs,))

result(False, "未知探针 %s" % PROBE_KIND)
'''


def norm_try_patch(txt, old, new):
    for o, n in ((old, new),
                 (old.replace("\n", "\r\n"), new.replace("\n", "\r\n"))):
        if o in txt:
            return txt.replace(o, n, 1), True
    return txt, False


def run_in(d):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    p = subprocess.run([sys.executable, "test_p1_p5.py"], cwd=d,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=180)
    out = p.stdout + p.stderr
    passed = total = 0
    for line in out.splitlines():
        if line.startswith("合计"):
            parts = line.split()
            try:
                total = int(parts[1]); passed = int(parts[3])
            except Exception:
                pass
    return p.returncode, passed, total, out


def run_probe(d, kind):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    open(os.path.join(d, "_probe.py"), "w", encoding="utf-8").write(PROBE)
    p = subprocess.run([sys.executable, "_probe.py", kind], cwd=d,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", env=env, timeout=120)
    for line in (p.stdout + p.stderr).splitlines():
        if line.startswith("PROBE_RESULT:"):
            return json.loads(line[len("PROBE_RESULT:"):])
    return {"ok": False, "msg": "探针无输出: " + (p.stdout + p.stderr)[-200:]}


def main():
    print("=" * 78)
    print("变异测试 v4（含纵深防御实测）")
    print("=" * 78)

    rc, p0, t0, out0 = run_in(HERE)
    print("\n基线: %s/%s 通过 (rc=%d)" % (p0, t0, rc))
    if p0 != t0 or rc != 0:
        print(out0[-1200:]); print("!! 基线不绿"); return 1

    results = []
    for name, fname, old, new, hint, redundant in MUTATIONS:
        tmp = tempfile.mkdtemp(prefix="afmut4_")
        try:
            for f in os.listdir(HERE):
                p = os.path.join(HERE, f)
                if os.path.isfile(p) and f.endswith(".py"):
                    shutil.copy2(p, tmp)
            shutil.copytree(os.path.join(HERE, "synthetic"),
                            os.path.join(tmp, "synthetic"))

            tgt = os.path.join(tmp, fname)
            txt = open(tgt, encoding="utf-8", newline="").read()
            patched, ok = norm_try_patch(txt, old, new)
            if not ok:
                print("%-46s INVALID（锚点未找到）" % name[:46])
                results.append({"mutation": name, "status": "INVALID",
                                "hint": hint})
                continue
            open(tgt, "w", encoding="utf-8", newline="").write(patched)

            rc2, p2, t2, out2 = run_in(tmp)
            caught = (rc2 != 0) or (p2 != t2)
            nfail = t2 - p2

            if caught:
                status = "CAUGHT"
                print("%-46s CAUGHT  (%d 失败)" % (name[:46], nfail))
            elif redundant:
                pr = run_probe(tmp, redundant)
                if pr["ok"]:
                    status = "REDUNDANT"
                    print("%-46s REDUNDANT（纵深防御实测拦住）" % name[:46])
                    print("      -> " + pr["msg"][:80])
                else:
                    status = "MISSED"
                    print("%-46s MISSED（声称的退路也拦不住）" % name[:46])
                    print("      -> " + pr["msg"][:80])
            else:
                status = "MISSED"
                print("%-46s MISSED（无注册退路）" % name[:46])

            results.append({"mutation": name, "status": status, "hint": hint,
                            "redundant_with": redundant, "failed_cases": nfail})
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 78)
    c = {s: sum(1 for r in results if r["status"] == s)
         for s in ("CAUGHT", "REDUNDANT", "MISSED", "INVALID")}
    print("变异 %d：CAUGHT %d / REDUNDANT %d / MISSED %d / INVALID %d"
          % (len(results), c["CAUGHT"], c["REDUNDANT"], c["MISSED"], c["INVALID"]))

    bad = c["MISSED"] + c["INVALID"]
    if bad:
        print("\n!! 判定 FAIL")
        for r in results:
            if r["status"] in ("MISSED", "INVALID"):
                print("   - %s -> %s" % (r["mutation"], r["hint"]))
        verdict = "FAIL"
    else:
        print("\n所有变异要么被直接捕获，要么有【实测通过】的退路")
        print("=> 现有断言不是空转")
        verdict = "PASS"

    print("VERDICT:", verdict)
    print("=" * 78)

    out = os.path.join(HERE, "reports", "mutation_result.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"baseline": {"passed": p0, "total": t0},
                   "verdict": verdict, "counts": c,
                   "mutations": results}, f, ensure_ascii=False, indent=2)
    print("结果:", out)
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
