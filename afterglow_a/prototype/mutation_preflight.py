# -*- coding: utf-8 -*-
"""变异计划预检 —— MUTATION_PREFLIGHT（凌翼 2026-11-27 裁定二）

凌翼原话：

    「在运行全部变异之前，增加一次独立的计划检查：MUTATION_PREFLIGHT
      它只需要确认所有登记的变异都有有效锚点，目标代码中每个预期旧片段
      恰好出现一次。

      如果失败，立即终止本轮变异，并留下本次 run_id 对应的失败报告。

      不必先运行 15 个变异才发现计划无法执行。

      preflight 检查的是『今天准备好的变异计划能否执行』；
      baseline 检查的是『原始测试与探针在未变异时是否正常』。
      两者分开，既减少浪费，也避免混淆概念。」

裁定二四条要求：
    1. 应执行清单与经登记的清单一致；
    2. 每条变异锚点恰好命中一次；
    3. 锚点异常时 fail-closed；
    4. 失败也必须留下具有本次 run_id 的可辨认结果，不得沿用旧报告。
    另：一个负向回归 —— 人为使锚点失效，preflight 必须在完整变异运行前拒绝执行。

⚠ 本模块【不】做 baseline 的事（不跑测试、不探针）。
   它只回答一个问题：这份计划今天能不能执行。

⚠ 本模块【不】校验经审查的名册摘要身份（凌翼 2026-11-27 第二次核对）：

    「preflight 目前核对清单 ID 与锚点；
      经过审查的清单摘要身份仍在变异执行后核对。
      因此它不能被描述为完整的前置可信身份验证。」

   ⇒ 本模块只比【ID 清单】与【锚点命中次数】。
     名册内容的 sha256 身份由 mutation_manifest.check_manifest_identity()
     在变异执行后核对，不在本模块。
   ⇒ 不得把本模块描述为「完整前置可信身份验证」。
     （test_attrition_preflight.py AP-15 用断言守着这条界限。）
"""
from __future__ import annotations

import os

from mutation_manifest import REGISTERED_MUTATION_IDS


def preflight(plan_ids, target_path, mutations,
              registered_ids=None):
    """检查变异计划是否可执行。

    参数
    ----
    plan_ids      : 执行计划里的变异 ID 列表（MUTATIONS 的 mid）
    target_path   : 被变异的源文件路径
    mutations     : 变异定义序列（每项至少含 [0]=mid, [2]=old 锚点）
    registered_ids: 经登记的 ID；默认取 mutation_manifest

    返回 dict（不抛异常 —— fail-closed 由调用方按 ok 决定）：
      ok            : bool
      reasons       : [str] 每条失败原因
      n_plan        : 计划条数
      n_registered  : 登记条数
      anchors       : [{id, count, ok}]
      unknown_ids   : 计划里有、登记里没有
      missing_ids   : 登记里有、计划里没有
    """
    reason_list = []
    if registered_ids is None:
        registered_ids = list(REGISTERED_MUTATION_IDS)
    registered_ids = list(registered_ids)
    plan_ids = list(plan_ids)

    # ---- 要求 1：应执行清单与经登记清单一致
    plan_set = set(plan_ids)
    reg_set = set(registered_ids)
    unknown_ids = sorted(plan_set - reg_set)
    missing_ids = sorted(reg_set - plan_set)
    if unknown_ids:
        reason_list.append(
            "计划含未登记的变异 %s ⇒ 不得执行" % unknown_ids)
    if missing_ids:
        reason_list.append(
            "登记要求执行但计划缺失 %s ⇒ 清单缩水" % missing_ids)
    if len(plan_ids) != len(plan_set):
        dup = sorted({i for i in plan_ids if plan_ids.count(i) > 1})
        reason_list.append("计划内 ID 重复 %s" % dup)

    # ---- 要求 2：每条锚点恰好命中一次
    try:
        with open(target_path, "r", encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        return {
            "ok": False,
            "reasons": ["目标文件不可读：%s" % e],
            "n_plan": len(plan_ids),
            "n_registered": len(registered_ids),
            "anchors": [],
            "unknown_ids": unknown_ids,
            "missing_ids": missing_ids,
        }
    except UnicodeDecodeError as e:
        # ⚠ 2026-11-27 修正（知微独立复核 §3）：
        #   UnicodeDecodeError 是 ValueError 子类，【不是】OSError，
        #   原实现只接住 OSError ⇒ 解码失败会【逃出】preflight()，
        #   驱动因此跳过失败报告 ⇒ 磁盘上仍是上一轮的 EVIDENCE_COMPLETE。
        #   知微实测：退出码 1、UnicodeDecodeError、报告逐字节未变。
        #   ⇒ 本轮确实停止了，但没给读报告的人留下本轮的失败记录。
        return {
            "ok": False,
            "reasons": ["目标文件不是合法 UTF-8：%s" % e],
            "n_plan": len(plan_ids),
            "n_registered": len(registered_ids),
            "anchors": [],
            "unknown_ids": unknown_ids,
            "missing_ids": missing_ids,
        }

    anchors = []
    for m in mutations:
        mid, old = m[0], m[2]
        n = src.count(old)
        ok = (n == 1)
        anchors.append({"id": mid, "count": n, "ok": ok})
        if not ok:
            reason_list.append(
                "%s 锚点命中 %d 次（应为 1）" % (mid, n))

    # ---- 要求 3：fail-closed —— 有任何一条不满足就不放行
    return {
        "ok": not reason_list,
        "reasons": reason_list,
        "n_plan": len(plan_ids),
        "n_registered": len(registered_ids),
        "anchors": anchors,
        "unknown_ids": unknown_ids,
        "missing_ids": missing_ids,
    }


def print_preflight(pf, run_id):
    """按凌翼要求 4 打印 —— 失败必须可辨认，且带本次 run_id。"""
    print("-" * 84)
    print("MUTATION_PREFLIGHT（凌翼 2026-11-27 裁定二）")
    print("  run_id = %s" % run_id)
    print("  计划 %d 条 / 登记 %d 条" % (pf["n_plan"], pf["n_registered"]))
    if pf["ok"]:
        print("  [OK] 全部锚点恰好命中一次，清单一致 ⇒ 允许执行")
        print("-" * 84)
        return
    print("  [FAIL] 计划不可执行，已在运行变异【之前】终止")
    for r in pf["reasons"]:
        print("    · %s" % r)
    bad = [a for a in pf["anchors"] if not a["ok"]]
    if bad:
        print("  失效锚点：")
        for a in bad:
            print("    - %-5s 命中 %d 次" % (a["id"], a["count"]))
    print("-" * 84)
