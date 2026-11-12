# -*- coding: utf-8 -*-
"""A16 五项显式验收（凌翼 2026-11-12 裁定 B-1 要求）。

为什么单独成文件：
  原来我把这段内联在 workflow 的 bash heredoc 里，
  但 YAML 块缩进 + heredoc 缩进极易出错，且本地无法直接跑。
  独立成 .py 后：CI 调它，本地也能直接跑同一份断言。

验收五项（裁定原文）：
    FAIL = 0
    SKIP = 0
    PENDING = 0
    ALL_REQUIRED_CASES = PASS
    EVIDENCE_IDENTITY = VERIFIED
另加：计数器守恒（total == pass+fail+skip+pending）

边界：本结论只覆盖该离线 L1 测试套件，
      不代表全部 L1 语义已充分覆盖。
"""
import sys, os, json, subprocess

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(HERE, "run_a16.py")


def main():
    r = subprocess.run([sys.executable, RUN, "--json"],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=HERE,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    rc, out, err = r.returncode, r.stdout, r.stderr

    # 先打印人类可读输出，便于日志阅读
    r2 = subprocess.run([sys.executable, RUN],
                        capture_output=True, text=True, encoding="utf-8",
                        errors="replace", cwd=HERE,
                        env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    print(r2.stdout)
    if r2.stderr.strip():
        print(r2.stderr)
    print("runner exit = %d" % rc)
    print()

    # 【必须先解析 JSON 再判退出码】：
    #   runner 非零退出时，summary 里到底哪一条不成立仍然有价值。
    #   若先 return 1，就看不到"是 PENDING≠0 还是 FAIL≠0"，
    #   验收脚本自己反而变成了「只说失败、不说哪条」。
    try:
        d = json.loads(out)
    except Exception as e:
        print("[FAIL] 无法解析 runner JSON: %s: %s" % (type(e).__name__, e))
        print(err[-400:])
        if rc != 0:
            print("[FAIL] runner 非零退出 (exit=%d)，且 JSON 不可解析" % rc)
        return 1

    s, m, res = d["summary"], d["meta"], d["results"]

    # 【知微 ZB31-02 修正 2026-11-12】
    #   原判定 ALL_REQUIRED_CASES 只写 `npass == len(res) and len(res) > 0`，
    #   即「返回的每一条都 PASS」，但没有核对：
    #     · 独立登记的必需 ID 是否都在（改名即漏）
    #     · ID 是否唯一（重复 X2 顶替 B1 仍是 47 条全 PASS）
    #     · summary 自报计数是否与 results 重算一致（报 48 而实为 47）
    #   实测三个反例当时全部被误判为通过。
    #   ⇒ 现改为调用共用校验 a16_result_check.validate()，
    #     与 mutate.py 使用同一套判据，避免「一处修好、另一处仍宽」。
    import a16_result_check as V
    ok_detail, problems, info = V.validate(d)

    npass = sum(1 for x in res if x.get("verdict") == "PASS")
    recount = info.get("recomputed", {}) if info else {}

    checks = [
        ("FAIL = 0", recount.get("FAIL") == 0, recount.get("FAIL")),
        ("SKIP = 0", recount.get("SKIP") == 0, recount.get("SKIP")),
        ("PENDING = 0",
         recount.get("OBSERVED_PENDING_RULING") == 0,
         recount.get("OBSERVED_PENDING_RULING")),
        ("ALL_REQUIRED_CASES = PASS",
         ok_detail and npass == len(res),
         "%d/%d（必需 %s 项，ID 完整/唯一/计数一致=%s）"
         % (npass, len(res), info.get("required_count", "?"), ok_detail)),
        ("EVIDENCE_IDENTITY = VERIFIED",
         m.get("evidence_ok") is True, m.get("evidence_detail")),
        ("计数器守恒（由 results 重算）",
         (not info) or (sum(recount.values()) == info.get("recomputed_total")),
         recount),
    ]

    bad = 0
    for name, ok, val in checks:
        print("  %s %-34s %s" % ("✅" if ok else "❌", name, val))
        if not ok:
            bad += 1

    if problems:
        print()
        print("  共用校验发现的问题：")
        for p in problems:
            print("    -", p)

    print()
    if bad or problems:
        print("[FAIL] 验收不成立（%d 项断言失败，%d 条问题）"
              % (bad, len(problems)))
        return 1
    if rc != 0:
        print("[FAIL] 五项断言全部成立，但 runner 退出码非零 (exit=%d)" % rc)
        print("       ⇒ runner 的退出逻辑与 summary 不一致，属实现缺陷")
        return 1

    print("⇒ 五项验收全部成立（本结论仅覆盖该离线 L1 测试套件，")
    print("   不代表全部 L1 语义已充分覆盖）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
