# -*- coding: utf-8 -*-
"""
AfterGlow-A 最小原型 · 可信历史恢复的最小实现

对应命题 P1–P5（见 afterglow_design/A_minimum_recovery_design.md §3.2）：
  P1  来源五值闭集，缺省 unknown
  P2  修改留上一版摘要，链可校验
  P3  纠正后旧版仍在，且可指认
  P4  能报告「不知道」而不自动填值
  P5  恢复后取回结果与期望集对比，区分 exact/superset/subset/disjoint/not_run

边界（凌翼裁定 §三）：
  - 只用合成资料，不读真实角色历史
  - 只做工程一致性，不声称任何科学结论
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------- 枚举闭集

SOURCE_KINDS = {
    "user_utterance",   # 用户明确说过的原话
    "system_generated", # 系统自动生成（摘要/反思/模板）
    "third_party",      # 第三方材料
    "model_echo",       # 模型自身输出被回读
    "unknown",          # 显式未知
}

PARTICIPATION_BASES = {
    "first_person_report",
    "third_person_report",
    "record_only",
    "unknown",
}

RELATION_TYPES = {
    "same_fact_different_time",
    "correction_of",
    "contradicts",
    "elaborates",
    "unknown",
}

COMMITMENT_STATES = {
    "not_a_commitment",
    "proposed",
    "accepted",
    "fulfilled",
    "withdrawn",
    "expired",
    "unknown",
}

MATCH_KINDS = {"exact", "superset", "subset", "disjoint"}
# 凌翼裁定 2026-11-24 §三 + A §1.8 更正二：
#   not_run 不是「第六种集合关系」，它是【没有 match_kind】。
#   已从闭集移出，改由 verify_recovery 用显式状态表达。
#   （此前 MATCH_KINDS 含 not_run，与设计文本不一致，本轮追平。）

UNKNOWN_REASONS = {
    "field_absent",
    "value_conflict",
    "ref_dangling",
    "never_observed",
    "not_applicable",
}

# ---------------------------------------------------------------- 观测通道
#
# Mion 2026-11-24 回复2 §一 / 回复3 §一：
#
#   basis_conflict 与 unknown_reason 是【元数不同】的两个字段：
#     unknown_reason  是一元谓词：关于【一个值】的确定程度
#     basis_conflict  是二元谓词：关于【(asserted, observed) 一对值】是否一致
#   ⇒ 一元字段装不下二元事实。不是「语义不够贴」，是【类型不对】。
#
#   ⇒ 必须另设字段，不得复用 unknown_reason = value_conflict。

# 系统侧观测到的生成来源。由 record_observed() 设置，不经 Record 构造。
# ⇒ 命名避免「可信」含义：这里只说「系统看到它从哪来」，不说「这来源可信」。
OBSERVED_ORIGINS = {
    "system_dispatch",   # 由调度/框架派发产生
    "model_generation",  # 模型自发生成
    "human_input",       # 人类直接输入
    "unknown_origin",    # 有观测但判不出来源（≠ 没有观测）
}

# 两路观测的一致性。
# ⚠ 后两个值的存在理由：防止「没有观测」被读成「没有冲突」。
#   这与 unknown / not_a_commitment 的区分是同一条纪律。
BASIS_CONFLICTS = {
    "none",                          # 两路一致
    "asserted_contradicts_observed", # 声明与观测冲突（伪亲历挂这里）
    "observed_absent",               # 没有观测通道 —— 不许当成 none
    "observed_unresolved",           # 有观测但判不出 —— 不许当成 none
}

# 凌翼裁定 2026-11-24 §一 第 4 点：明确区分三种操作。
# 它们对记录摘要的影响【不同】，不可混为一谈。
HISTORY_OPERATIONS = {
    # 原样恢复：字节级搬运，changed_at 等字段一字不改
    # ⇒ 重算 record_digest 必然一致
    "restore_verbatim",
    # 内容重建：凭内容重新生成记录，会重新取 _now()
    # ⇒ record_digest 会变，content_digest 应不变
    "rebuild_from_content",
    # 历史迁移：换存储/换格式/换编码，但仍搬运原字段
    # ⇒ 若不动 changed_at，record_digest 应一致；
    #    若迁移过程规范化了时间戳格式，record_digest 会变
    "migrate_history",
}


class SchemaError(Exception):
    """任何枚举字段取值不在闭集内 ⇒ 报错，不落缺省。"""


# ---------------------------------------------------------------- 摘要

DIGEST_FIELDS_EXCLUDED = {"this_digest"}


def canonical_digest(record: Dict[str, Any]) -> str:
    """对记录做规范化摘要（排除摘要字段自身）。

    ⚠ 语义（凌翼裁定 2026-11-24 §一）：
    这是【版本记录摘要 record_digest】，不是内容摘要。
    changed_at 属于记录身份的一部分，因此同内容不同时刻重建会产生不同摘要。
    ⇒ 这种差异【不是】算法不可复算，而是记录身份确实变了。

    要比较「内容是否等价」，请用 content_digest()，见下。
    """
    payload = {k: v for k, v in record.items() if k not in DIGEST_FIELDS_EXCLUDED}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


# ---------------------------------------------------------------- 内容等价摘要
#
# 凌翼裁定 2026-11-24 §一：允许增设独立的 content_digest，
# 但【本轮只限 schema 与设计论证】；运行时实现须在明确兼容与
# 历史迁移策略后单独批准。
#
# ⇒ 因此本函数标为 EXPERIMENTAL，且默认不被链校验使用。
#   verify_chain() 仍只用 record_digest，旧链算法未被改动。

CONTENT_DIGEST_VERSION = "cd-v1"

# 内容摘要的字段投影：只取「这条记录说了什么」，
# 不取「它何时被写、由谁写、上一版是谁」。
CONTENT_DIGEST_FIELDS = (
    "record_id",      # 身份仍要进，否则不同记录的同文本会撞
    "content",
    "source_kind",
    "source_ref",
    "participant_id",
    "participation_basis",
    "basis_ref",
    "commitment_state",
    "committed_by",
    "committed_to",
    "commitment_ref",
    "unknown_reason",
    "relation",       # relation 是内容的一部分（指向谁、为何指向）
)

# 明确【不进入】内容摘要的字段，及其理由。
# 这三个字段描述「这一版如何产生」，不描述「它说了什么」。
CONTENT_DIGEST_EXCLUDED = {
    "this_digest": "摘要字段自身",
    "prev_digest": "链指针：属于历史位置，不属于内容",
    "revision":    "版本序号：同内容不同版本号仍应内容等价",
    "changed_at":  "写入时刻：同内容不同时刻仍应内容等价",
    "change_authority": "写入授权方：同内容不同授权方仍应内容等价",
}


def content_digest(record: Dict[str, Any]) -> str:
    """内容等价摘要（EXPERIMENTAL，cd-v1）。

    投影规则（必须与 CONTENT_DIGEST_FIELDS 完全一致，缺一字段即报错）：
      1. 只取 CONTENT_DIGEST_FIELDS 列出的字段；
      2. 缺失字段【不得】按缺省填充，必须显式报错 ——
         否则「缺字段」与「字段为空」会算出同一个摘要；
      3. 规范化：json.dumps(sort_keys=True, ensure_ascii=False,
         separators=(",", ":"))，UTF-8 编码；
      4. 摘要串以版本前缀开头，便于将来区分 cd-v1 / cd-v2。

    ※ 本函数不参与 verify_chain；改用它需要单独立项批准（裁定 §一 末段）。
    """
    missing = [k for k in CONTENT_DIGEST_FIELDS if k not in record]
    if missing:
        raise SchemaError(
            "content_digest 缺字段 %s —— 不得按缺省填充，"
            "否则「字段缺失」与「字段为空」不可区分" % (sorted(missing),))
    # 同时排除本该排除的字段被误纳入的情况
    leaked = [k for k in CONTENT_DIGEST_EXCLUDED
              if k in CONTENT_DIGEST_FIELDS]
    if leaked:
        raise SchemaError(
            "内容摘要字段表混入了应排除字段 %s" % (sorted(leaked),))
    payload = {k: record[k] for k in CONTENT_DIGEST_FIELDS}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")
    return "%s:%s" % (CONTENT_DIGEST_VERSION, hashlib.sha256(blob).hexdigest())


# ---------------------------------------------------------------- 记录

@dataclass
class Record:
    record_id: str
    content: str
    source_kind: str
    source_ref: Optional[str]
    participant_id: Optional[str]
    participation_basis: str
    basis_ref: Optional[str]
    commitment_state: str
    revision: int
    prev_digest: Optional[str]
    changed_at: str
    change_authority: str
    relation: List[Dict[str, Any]] = field(default_factory=list)
    unknown_reason: Optional[str] = None
    committed_by: Optional[str] = None
    committed_to: Optional[str] = None
    commitment_ref: Optional[str] = None

    # ---- 观测通道字段（Mion 2026-11-24 回复2 §一）
    # ⚠ 这两个字段【不应】由调用方在构造 Record 时直接给定。
    #   正确路径是 store.record_observed()。
    #   但 dataclass 无法真正阻止关键字传参，
    #   所以在 validate() 里加：insert() 时若二者非 None ⇒ 拒绝。
    #   ⇒ 这不是权限边界（同进程可绕过），只是把「随手填」变成「写不进去」。
    observed_origin: Optional[str] = None
    basis_conflict: Optional[str] = None

    # ---- 原始来源层（Mion 2026-11-24 §二 第 4 项）
    #
    # 问题：correct() 会把 source_kind/source_ref 等 5 个字段【改指向纠正依据】，
    #      于是 live 上「这句话最初是谁说的」就查不到了，
    #      而 C 的污染会被静默继承且无任何不一致可查。
    #
    # ⇒ 分两层：
    #      origin_*        建记录时写入，终身不变
    #      current_basis_* 纠正时改这里（实际就是现有的 source_* 那 5 个字段）
    #
    # ⇒ 「被纠正过」= origin ≠ current，不再是 revision > 1。
    #   revision > 1 只说明「被改过」，不说明「被谁依据什么改过」。
    #
    # ⚠ 硬约束（Mion 三条之一）：
    #   origin_* 【不进 revise 白名单】，只在 insert 时设定，之后终身不变。
    #   否则它就成了第二个可改的来源字段 —— 也就是第二个自报。
    origin_source_kind: Optional[str] = None
    origin_source_ref: Optional[str] = None
    origin_participant_id: Optional[str] = None
    origin_participation_basis: Optional[str] = None
    origin_basis_ref: Optional[str] = None

    def validate(self) -> List[str]:
        """返回问题列表。空列表 = 通过。任何不在闭集内的值都算问题。"""
        problems: List[str] = []

        if self.source_kind not in SOURCE_KINDS:
            problems.append(
                "source_kind=%r 不在闭集内（P1/P4 违规）" % (self.source_kind,))
        if self.participation_basis not in PARTICIPATION_BASES:
            problems.append(
                "participation_basis=%r 不在闭集内" % (self.participation_basis,))
        if self.commitment_state not in COMMITMENT_STATES:
            problems.append(
                "commitment_state=%r 不在闭集内" % (self.commitment_state,))
        for rel in self.relation:
            rt = rel.get("relation_type")
            if rt not in RELATION_TYPES:
                problems.append("relation_type=%r 不在闭集内" % (rt,))

        # unknown 必须带得住的理由（可不填，但填了必须在闭集内）
        if self.unknown_reason is not None and self.unknown_reason not in UNKNOWN_REASONS:
            problems.append("unknown_reason=%r 不在闭集内" % (self.unknown_reason,))

        # ZA-03（知微 r2/24）：来源枚举不能代替引用存在性。
        # 除 unknown 外，任何来源都应有非空 source_ref；
        # 否则「来源已判定」是假的，只是枚举值看着确定。
        if self.source_kind != "unknown" and not (self.source_ref or "").strip():
            problems.append(
                "source_kind=%s 但 source_ref 为空（A §1.1 把空引用列为未知）"
                % self.source_kind)

        # 承诺态与承诺字段的一致性
        if self.commitment_state in {"proposed", "accepted", "fulfilled"}:
            if not self.committed_to:
                problems.append(
                    "commitment_state=%s 但 committed_to 为空（§1.5 要求）"
                    % self.commitment_state)
            if not self.commitment_ref:
                problems.append(
                    "commitment_state=%s 但 commitment_ref 为空（§1.5 要求）"
                    % self.commitment_state)

        # 首版 prev_digest 必须为 None，不能是空串
        if self.revision == 1 and self.prev_digest is not None:
            problems.append("revision=1 但 prev_digest 非 None（§1.3 要求）")
        if self.revision > 1 and not self.prev_digest:
            problems.append("revision=%d 但 prev_digest 为空（§1.3 要求）"
                            % self.revision)

        if self.revision < 1:
            problems.append("revision < 1")

        # 观测字段（Mion 2026-11-24）：闭集校验。
        # ⚠ 「不得经构造器填入」这条约束放在 insert() 里检查，
        #   不放在 validate()：因为 record_observed() 内部改 live 时
        #   要构造带这两个字段的 Record。
        if self.observed_origin is not None:
            if self.observed_origin not in OBSERVED_ORIGINS:
                problems.append(
                    "observed_origin=%r 不在闭集内" % (self.observed_origin,))
        if self.basis_conflict is not None:
            if self.basis_conflict not in BASIS_CONFLICTS:
                problems.append(
                    "basis_conflict=%r 不在闭集内" % (self.basis_conflict,))

        return problems

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------- 存储

class RecoveryStore:
    """最小可信历史存储。

    - 写入不覆盖：同一 record_id 的新版进入版本链
    - 每次写入前先校验 schema
    - 摘要链可校验
    """

    def __init__(self, authority: str = "synthetic-fixture"):
        self.authority = authority
        self._live: Dict[str, Record] = {}          # 当前版
        self._history: Dict[str, List[Dict[str, Any]]] = {}  # 全版本
        self._write_log: List[Dict[str, Any]] = []
        # ---- 观测链（Mion 2026-11-24 回复4 §三）
        # 与 _history 分开：观测不进内容链，但有自己的一条链。
        self._observed_chain: Dict[str, List[Dict[str, Any]]] = {}
        self._observed_chain_head: Dict[str, str] = {}

    # ---- 载入合成种子
    def load_seed(self, path: str) -> int:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        n = 0
        for raw in data.get("records", []):
            rec = Record(**{k: v for k, v in raw.items()})
            probs = rec.validate()
            if probs:
                raise SchemaError("%s: %s" % (rec.record_id, "; ".join(probs)))
            d = rec.to_dict()
            d["this_digest"] = canonical_digest(d)
            self._live[rec.record_id] = rec
            self._history.setdefault(rec.record_id, []).append(d)
            n += 1
        return n

    # ---- 写入新记录（首版）
    def insert(self, rec: Record) -> str:
        if rec.record_id in self._live:
            raise ValueError("已存在，请用 revise(): %s" % rec.record_id)
        if rec.revision != 1:
            raise ValueError("insert 只接受 revision=1")
        # 观测字段只能经 record_observed() 设置，不得从构造参数带进来。
        # ⇒ 这不是权限边界（同进程可绕过），只是把「随手填」变成「写不进去」。
        if rec.observed_origin is not None or rec.basis_conflict is not None:
            raise SchemaError(
                "observed_origin / basis_conflict 不得经 Record 构造写入；"
                "请用 store.record_observed()。"
                "（本原型无进程隔离，此约束是语义约束，不是权限边界）")
        probs = rec.validate()
        if probs:
            raise SchemaError("; ".join(probs))
        # ---- 原始来源层：建时写入，终身不变（Mion 2026-11-24 §二）
        #   correct() 只改 current_basis_*（即 source_* 那 5 个），
        #   不改 origin_* ⇒ 「最初是谁说的」永远可查。
        if rec.origin_source_kind is None:
            rec.origin_source_kind = rec.source_kind
            rec.origin_source_ref = rec.source_ref
            rec.origin_participant_id = rec.participant_id
            rec.origin_participation_basis = rec.participation_basis
            rec.origin_basis_ref = rec.basis_ref
        d = rec.to_dict()
        d["this_digest"] = canonical_digest(d)
        # ZA-01（知微 r2/24）：取得独立状态所有权。
        # 不能把调用者传入的 Record 本体放进 _live ——
        # 调用者仍持有该对象，可在 insert 返回后不经 revise 直接改它，
        # 造成 get() 与 history() 不一致而 verify_chain 仍通过。
        _body = {k: v for k, v in d.items() if k != "this_digest"}
        owned = Record(**copy.deepcopy(_body))
        self._live[rec.record_id] = owned
        self._history.setdefault(rec.record_id, []).append(copy.deepcopy(d))
        self._write_log.append({"op": "insert", "record_id": rec.record_id,
                                "digest": d["this_digest"],
                                "at": _now()})
        return d["this_digest"]

    # 普通 revise 允许变更的字段白名单。
    # ZA-02（知微 r2/24）：record_id 是链身份，不得经普通 revise 偷换。
    # 若将来要支持改名/迁移，应设计显式关系，而不是复用 revise。
    _REVISABLE = {
        "content", "source_kind", "source_ref", "participant_id",
        "participation_basis", "basis_ref", "commitment_state",
        "committed_by", "committed_to", "commitment_ref",
        "relation", "unknown_reason",
    }
    # ⚠ observed_origin / basis_conflict 不在白名单内：
    #   一旦写入，不得经 revise 修改（Mion 2026-11-24）。
    #   否则「观测」可以被事后改写，等于没有观测。

    # ---- 修订（不覆盖：旧版保留）
    def revise(self, record_id: str, changes: Dict[str, Any],
               reason: str = "", authority: Optional[str] = None) -> str:
        cur = self._live.get(record_id)
        if cur is None:
            raise KeyError(record_id)

        # 内部标记（correct() 调用时置 True），先取出，不参与白名单校验
        via_correct = bool(changes.get("_via_correct"))
        changes = {k: v for k, v in changes.items() if k != "_via_correct"}

        illegal = set(changes) - self._REVISABLE
        if illegal:
            raise SchemaError(
                "revise 不允许变更字段 %s（允许：%s）。"
                "record_id 等身份字段不得经普通 revise 变更。"
                % (sorted(illegal), sorted(self._REVISABLE)))

        # ---- 来源字段只能由 correct() 改（Mion 2026-11-24 §二 第 ② 条）
        #
        # 「否则用户可以直接 revise 掉来源，而不留下 correction_of 边。
        #   那样『被纠正过』这个事实本身就会消失。」
        _SOURCE_FIELDS = {"source_kind", "source_ref", "participant_id",
                          "participation_basis", "basis_ref"}
        touching_source = _SOURCE_FIELDS & set(changes)

        if touching_source and not via_correct:
            raise SchemaError(
                "revise 不允许直接改来源字段 %s。"
                "否则来源被改而『被纠正过』这一事实会消失。"
                "请改用 correct()（它会加 correction_of 边并改来源）。"
                % (sorted(touching_source),))

        cur_d = cur.to_dict()
        prev_digest = canonical_digest(cur_d)

        merged = copy.deepcopy(cur_d)
        merged.update(changes)
        merged["revision"] = cur.revision + 1
        merged["prev_digest"] = prev_digest
        merged["changed_at"] = _now()
        merged["change_authority"] = authority or self.authority

        rec = Record(**merged)
        probs = rec.validate()
        if probs:
            raise SchemaError("; ".join(probs))

        d = rec.to_dict()
        d["this_digest"] = canonical_digest(d)
        _body = {k: v for k, v in d.items() if k != "this_digest"}
        self._live[record_id] = Record(**copy.deepcopy(_body))
        self._history[record_id].append(copy.deepcopy(d))
        self._write_log.append({"op": "revise", "record_id": record_id,
                                "from": prev_digest, "to": d["this_digest"],
                                "reason": reason, "at": _now()})
        return d["this_digest"]

    # ---- 纠正（语义包装：加 correction_of 边，不删除原件）
    def correct(self, record_id: str, new_content: str,
                correcting_record_id: str, reason: str) -> str:
        """ZA-03（知微 r2/24）：

        原实现可以引用根本不存在的 correcting_record_id，
        同时换掉内容却保留旧的 source_kind / source_ref ——
        链通过，但新内容没有经过核验的对应来源。

        现改为：
          1. correcting_record_id 必须已存在（否则拒绝生效）；
          2. 该记录必须带有非空 source_ref；
          3. 纠正后本记录的来源改指向【纠正依据】，不再是原始来源，
             并保留 correction_of 边供追溯。
        """
        cur = self._live.get(record_id)
        if cur is None:
            raise KeyError(record_id)

        basis = self._live.get(correcting_record_id)
        if basis is None:
            raise SchemaError(
                "纠正依据不存在：%s。缺依据时不得让纠正在沿用原来源的情况下生效。"
                % correcting_record_id)
        if not (basis.source_ref or "").strip():
            raise SchemaError(
                "纠正依据 %s 没有可核验的 source_ref，不能为更正后内容作证。"
                % correcting_record_id)

        rel = list(cur.relation) + [{
            "relation_type": "correction_of",
            "from_id": record_id,
            "to_id": correcting_record_id,
            "relation_basis": reason,
        }]
        return self.revise(
            record_id,
            {
                "content": new_content,
                "relation": rel,
                # 来源改指向纠正依据，不再沿用原始来源
                # （origin_* 不动 ⇒ 最初来源仍可查，见 was_corrected()）
                "source_kind": basis.source_kind,
                "source_ref": basis.source_ref,
                "participant_id": basis.participant_id,
                "participation_basis": basis.participation_basis,
                "basis_ref": basis.basis_ref,
                # 内部标记：告诉 revise 这次来源改动是纠正流程的一部分
                "_via_correct": True,
            },
            reason="correction: " + reason)

    # ---- 观测通道（Mion 2026-11-24 回复2 §一 / 回复3 §一、§二）
    #
    # ⚠ 这条路径买到的【不是「防填」】，是：
    #     「观测写入必留痕，且与内容写入是两次不同的调用」。
    #   不要叫它「通道」——「通道」暗示隔离，这里没有隔离。
    #
    # ⚠ 它【不构成权限边界】：
    #    本原型是单进程 Python 库，任何 import afcore 的代码都能调本方法。
    #    真正的权限边界（进程/身份隔离）超出本原型层级，
    #    登记为 OBSERVED_PERMISSION_BOUNDARY = NOT_ACHIEVABLE_IN_THIS_PROTOTYPE。

    def record_observed(self, record_id: str, observed_origin: str,
                        note: str = "",
                        observed_record_digest: Optional[str] = None) -> None:
        """记录一次【系统侧】对生成来源的观测。

        时序约束（Mion 2026-11-24 回复3 §一，这是本方法的要害）：

          只在 record 的 revision == 1 且【从未被 revise / correct 过】时可用。
          一旦被修改过，观测通道关闭。

        ⇒ 理由：一条晚于内容写入的 observed，可能是照着内容编的。
          观测的价值在于它【早于、或至少独立于】内容。
          事后补的观测不是观测，是第二个声明。

        ⇒ 这条约束把本方法从「防手滑」变成「防批量补」。
          「防批量补」才是真正会发生的那个：
          若允许任意时刻补，一个脚本就能给全部历史刷上
          observed_origin = system_dispatch，那与 (b) 档无区别，
          而且更糟 —— 因为它看起来像观测。
        """
        if observed_origin not in OBSERVED_ORIGINS:
            raise SchemaError(
                "observed_origin=%r 不在闭集内（允许：%s）"
                % (observed_origin, sorted(OBSERVED_ORIGINS)))

        cur = self._live.get(record_id)
        if cur is None:
            raise KeyError(record_id)

        # ---- 观测属于哪一版？（知微 2026-11-24）
        #
        # 问题：只凭 record_id，旧观测会被贴到新内容上。
        #   观察者看到第 1 版，等他提交观测时记录已纠正到第 2 版，
        #   只凭同一个 record_id 就可能把旧观测记到新内容名下。
        #
        # ⇒ 要求观测携带【所见版本的 record_digest】。
        #   若给出，必须是该记录【某一真实存在版本】的摘要。
        #
        # ⚠ 不解环（船长「不要用尺子量尺子」）：
        #   这里只读 _history 里已有的 this_digest 做集合比对，
        #   【不调用 verify_chain】，也【不把链校验结论写进条目】。
        #   ⇒ 比对的是「外部输入 vs 已知集合」，不是自证。
        hist = self._history.get(record_id, [])
        known_digests = {d.get("this_digest"): d.get("revision")
                         for d in hist}
        observed_rev = None

        if observed_record_digest is not None:
            if observed_record_digest not in known_digests:
                raise SchemaError(
                    "观测所指版本的摘要 %s 不属于记录 %s 的任何一版；"
                    "这条观测是错位的（observer 看的那份已不存在或非本记录）。"
                    % (str(observed_record_digest)[:12], record_id))
            observed_rev = known_digests[observed_record_digest]
            # 观测必须指向【当前版】才能用于当前冲突判定
            if observed_rev != cur.revision:
                raise SchemaError(
                    "观测所指是第 %d 版，而当前是第 %d 版；"
                    "旧观测不得贴到新内容上。"
                    "若要在当前版上判定，须重新观测。"
                    % (observed_rev, cur.revision))

        # ---- 时序约束（放宽后）
        #
        # 原实现：revision != 1 或曾被修改 ⇒ 一律拒绝。
        # 那会【宁可丢掉一个真实观测】，也不接受可能错位的观测。
        #
        # 知微指出的路径更好：
        #   观测携带所见版本 digest ⇒ 可以判断它属于哪一版，
        #   于是「跨时间的真实观测」可以接受，
        #   而「错位观测」照样被拒。
        #
        # ⇒ 现行规则：
        #   · 未给 digest：仍要求 revision == 1 且未被修改（旧规则，保守）
        #   · 给了 digest：必须指向当前版（上面已校验）；
        #     此时允许 revision > 1 —— 因为版本已被明确绑定
        if observed_record_digest is None:
            if cur.revision != 1:
                raise SchemaError(
                    "记录 %s 已是第 %d 版；未指明所见版本摘要的观测"
                    "只允许在首版上使用。请给出 observed_record_digest。"
                    % (record_id, cur.revision))
            if self._was_modified(record_id):
                raise SchemaError(
                    "记录 %s 曾被 revise/correct 过；未指明所见版本的观测"
                    "不得事后补。请给出 observed_record_digest。" % record_id)

        if cur.observed_origin is not None:
            raise SchemaError(
                "记录 %s 已有 observed_origin=%r；观测是一次性的，不得覆盖。"
                % (record_id, cur.observed_origin))

        # --- 计算冲突（二元：asserted vs observed）---
        # asserted 侧 = participation_basis（写入方声称「多近」）
        # observed 侧 = observed_origin（系统看到它从哪来）
        #
        # 判定表（与下方实现逐格对应；改动须两处同步）：
        #
        #   asserted \ observed | system_dispatch | model_generation | human_input
        #   first_person_report |  【冲突】        |    【冲突】      |  none
        #   third_person_report |  none            |    【冲突】      |  none
        #   record_only         |  none            |    none          |  none
        #
        # ⇒ 「声称第一人称亲历，但系统看到是派发/模型生成」= 冲突。
        #   这不是「判不出」——断言与观测直接相反。
        #
        # ⇒ 「声称第三人称转述，但系统看到是模型生成」也判冲突：
        #   断言是「我被某人告知」，观测说「没有被告知的痕迹」
        #   ⇒ 断言与观测相反。
        #   ⚠ 不要写成「模型生成的内容没有第三方来源可言」——
        #     那要求先定义「什么叫有来源」，判定不可终止。
        #     用「相反」而不是「不存在」，是把哲学问题降成字段比较。
        #
        # ⇒ record_only 全程判 none：
        #   它的断言是「不指向任何陈述者」，模型生成不违反这个断言。
        #   弱断言不容易被违反，这是它的性质，不是缺陷；
        #   把「弱断言 + 不利观测」一律判冲突，是在惩罚诚实地不声称。
        #   ⚠ 但这会让 record_only 成为「洗白档」⇒
        #     用 record_only_ratio 单独度量（见 afrecover.summarize_conflicts）。
        #
        # ⚠ 2026-11-24 修正（Mion 指出）：本表此前把 record_only×model_generation
        #   写作【冲突】，而实现已改判 none —— 表与代码不一致。
        #   备注：这张表是下一个人读代码的第一入口；表错了，他就不会去读实现。
        observed = observed_origin
        asserted = cur.participation_basis

        if observed == "unknown_origin":
            conflict = "observed_unresolved"
        elif asserted == "unknown":
            conflict = "observed_unresolved"
        elif asserted == "first_person_report":
            conflict = ("none" if observed == "human_input"
                        else "asserted_contradicts_observed")
        elif asserted == "third_person_report":
            # Mion 2026-11-24 回复4 §4.1：
            # 判冲突的根据是【断言与观测相反】，不是「模型生成的内容
            # 没有第三方来源可言」。后者要求先定义「什么叫有来源」，
            # 判定不可终止；前者只需看 observed 有没有 human_input 痕迹。
            #
            # ⚠ 2026-11-24 二次修正（Mion 指出注释表与代码不一致后逐格重核）：
            #   原代码写作
            #       conflict = ("none" if observed == "human_input"
            #                   else "asserted_contradicts_observed")
            #   这会把 system_dispatch 也判成冲突 —— 但按「相反」判据：
            #     断言「我被某人告知」
            #     观测 system_dispatch「系统派发的」
            #     ⇒ 派发的内容【可能】是别人说的话 ⇒ 不违反断言 ⇒ 应判 none
            #   Mion 原文只指定了 model_generation 那一格判冲突，
            #   没有说 system_dispatch 要判冲突。
            #   ⇒ 按「相反」判据：只有 model_generation 与断言相反。
            conflict = ("asserted_contradicts_observed"
                        if observed == "model_generation" else "none")
        elif asserted == "record_only":
            # Mion 2026-11-24 回复4 §4.2：
            # record_only 的断言是「不指向任何陈述者」，
            # 模型生成的内容【不违反】这个断言 ⇒ 判 none。
            # 弱断言不容易被违反，这是它的性质，不是缺陷；
            # 把「弱断言 + 不利观测」一律判冲突，是在惩罚诚实地不声称。
            # ⚠ 但 record_only 会成为洗白档 ⇒ 用 record_only_ratio 单独度量。
            conflict = "none"
        else:
            conflict = "observed_unresolved"

        # 伪亲历的派生标记（Mion 2026-11-24 回复4 §五）
        # ⚠ 不是第五个 basis_conflict 值：
        #   「冲突」是一层事实，「伪亲历」是它的一个真子集 —— 两层。
        #   一个字段装两层，就是我们从头到尾在治的病。
        pseudo = (asserted == "first_person_report"
                  and observed == "model_generation")

        _body = cur.to_dict()
        _body["observed_origin"] = observed_origin
        _body["basis_conflict"] = conflict
        owned = Record(**copy.deepcopy(
            {k: v for k, v in _body.items() if k != "this_digest"}))
        self._live[record_id] = owned

        # ---- 观测链（Mion 2026-11-24 回复4 §三 方案 b）
        #
        # ⚠ 原实现只写 _live，不写 _history、不重算摘要
        #   ⇒ verify_chain 只迭代 _history，从不看 _live
        #   ⇒ 观测字段成了【唯一不受校验的字段】
        #   ⇒ 这很讽刺：整套东西是为了让观测约束声明，
        #     结果观测本身成了链外的东西。
        #
        # ⇒ 修法：单独一条 _observed_chain，不动 revision 序，
        #   不动内容摘要（content_digest 语义不变）。
        #   冲突值本身也进摘要 ⇒ 改 basis_conflict 会断链。
        prev = self._observed_chain_head.get(record_id)
        entry = {
            "record_id": record_id,
            # 知微 2026-11-24：观测属于哪一版？
            # ⇒ 携带所见版本的 record_digest 与 revision，
            #   使「谁实际见过什么」落到一条具体记录的具体版本上。
            "observed_record_digest": observed_record_digest,
            "observed_revision": observed_rev,
            "asserted": asserted,
            "observed": observed,
            "basis_conflict": conflict,
            "pseudo_first_person": pseudo,
            "at": _now(),
            "prev": prev,
        }
        entry["digest"] = canonical_digest(entry)
        self._observed_chain.setdefault(record_id, []).append(entry)
        self._observed_chain_head[record_id] = entry["digest"]

        self._write_log.append({
            "op": "record_observed", "record_id": record_id,
            "asserted": asserted, "observed": observed,
            "basis_conflict": conflict, "note": note, "at": _now(),
        })

    def observed_chain(self, record_id: str) -> List[Dict[str, Any]]:
        """该记录的观测链（每次 record_observed 一条）。"""
        return [copy.deepcopy(e)
                for e in self._observed_chain.get(record_id, [])]

    def verify_observed_chain(self, record_id: str) -> Tuple[bool, List[str]]:
        """校验观测链：链接与摘要是否自洽。

        Mion 2026-11-24 回复4 §三：
          「这一步之后，我想问的那个问题才有答案：
            『这条记录的冲突判定有没有被动过？』」
        """
        chain = self._observed_chain.get(record_id, [])
        problems: List[str] = []
        if not chain:
            # 没有观测不是错误，是 observed_absent —— 由上层表达
            return True, []

        prev = None
        for i, e in enumerate(chain):
            recomputed = canonical_digest(
                {k: v for k, v in e.items() if k != "digest"})
            if recomputed != e.get("digest"):
                problems.append("第%d条观测摘要不符：记录 %s ≠ 重算 %s"
                                % (i + 1, str(e.get("digest"))[:12],
                                   recomputed[:12]))
            if e.get("prev") != prev:
                problems.append("第%d条观测 prev 未指向第%d条摘要"
                                % (i + 1, i))
            prev = e.get("digest")
        return (len(problems) == 0), problems

    def observed_chained(self, record_id: str) -> bool:
        """该记录的观测是否已进入观测链。"""
        return bool(self._observed_chain.get(record_id))

    def pseudo_first_person(self, record_id: str) -> bool:
        """该记录是否已被判为伪亲历（派生标记，非第五个枚举值）。"""
        chain = self._observed_chain.get(record_id, [])
        if not chain:
            return False
        return bool(chain[-1].get("pseudo_first_person"))

    def _was_modified(self, record_id: str) -> bool:
        """该记录是否曾被 revise / correct 过。

        判据：写日志里存在该 id 的 revise 操作，或历史长度 > 1。
        """
        for e in self._write_log:
            if e.get("record_id") == record_id and e.get("op") == "revise":
                return True
        return len(self._history.get(record_id, [])) > 1

    def was_corrected(self, record_id: str) -> bool:
        """该记录是否【被纠正过】—— 不是「被改过」。

        Mion 2026-11-24 §二 第 ③ 条：
          「分层之后，『被纠正过』的判据必须是 origin ≠ current，
            不能是 revision > 1。

            revision > 1 只说明『被改过』，不说明『被谁依据什么改过』。
            origin ≠ current 才是那件事。」
        """
        rec = self._live.get(record_id)
        if rec is None:
            return False
        return any([
            rec.origin_source_kind != rec.source_kind,
            rec.origin_source_ref != rec.source_ref,
            rec.origin_participant_id != rec.participant_id,
            rec.origin_participation_basis != rec.participation_basis,
            rec.origin_basis_ref != rec.basis_ref,
        ])

    def origin_of(self, record_id: str) -> Dict[str, Any]:
        """该记录【最初】的来源（origin_* 五字段），与当前来源并列给出。"""
        rec = self._live.get(record_id)
        if rec is None:
            return {}
        return {
            "origin_source_kind": rec.origin_source_kind,
            "origin_source_ref": rec.origin_source_ref,
            "origin_participant_id": rec.origin_participant_id,
            "origin_participation_basis": rec.origin_participation_basis,
            "origin_basis_ref": rec.origin_basis_ref,
            "current_source_kind": rec.source_kind,
            "current_source_ref": rec.source_ref,
            "current_participant_id": rec.participant_id,
            "current_participation_basis": rec.participation_basis,
            "current_basis_ref": rec.basis_ref,
            "was_corrected": self.was_corrected(record_id),
        }

    # ---- 链校验
    def verify_chain(self, record_id: str) -> Tuple[bool, List[str]]:
        hist = self._history.get(record_id, [])
        problems: List[str] = []
        if not hist:
            return False, ["无历史"]
        for i, d in enumerate(hist):
            expect_rev = i + 1
            if d["revision"] != expect_rev:
                problems.append("第%d版 revision=%s，应为 %d"
                                % (i + 1, d["revision"], expect_rev))
            recomputed = canonical_digest(
                {k: v for k, v in d.items() if k != "this_digest"})
            if recomputed != d["this_digest"]:
                problems.append("第%d版摘要不符：记录 %s ≠ 重算 %s"
                                % (i + 1, d["this_digest"][:12], recomputed[:12]))
            if i == 0:
                if d["prev_digest"] is not None:
                    problems.append("首版 prev_digest 应为 None")
            else:
                if not d["prev_digest"]:
                    problems.append("第%d版 prev_digest 为空（§1.3 要求非空）"
                                    % (i + 1))
                elif d["prev_digest"] != hist[i - 1]["this_digest"]:
                    problems.append("第%d版 prev_digest 未指向第%d版摘要"
                                    % (i + 1, i))
        return (len(problems) == 0), problems

    # ---- 读取
    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        d = self._live.get(record_id)
        return d.to_dict() if d else None

    def history(self, record_id: str) -> List[Dict[str, Any]]:
        return [copy.deepcopy(d) for d in self._history.get(record_id, [])]

    def sqlite_rows(self) -> List[Dict[str, Any]]:
        """全部当前记录（供查询）。"""
        return [d.to_dict() for d in self._live.values()]

    def snapshot_token(self) -> str:
        """当前库状态的指纹，用于识别「检查后对象被替换」。

        凌翼裁定 2026-11-24 §三 第 7 条：
          检查完成后、结果被消费前若发生对象替换或版本改变，
          不能沿用旧检查结果。

        ⚠ Z61-02（知微 2026-11-24 §4）：原实现只取
             record_id / revision / canonical_digest(live) / len(history)
          而 verify_chain 检查的是【历史记录的实际字段与链指针】。
          历史长度不变、live 不变时，历史正文可被改动而令牌不变 ——
          这正是需要检出的情形。

        ⇒ 现改为覆盖【每一版历史的实际内容】：
             对每一版 d，取其完整字段（排除 this_digest 之外的都保留），
             与 this_digest 一并纳入。
          ⇒ 改正文、改摘要串、改 prev_digest、改任意历史字段，
            都会改变本令牌。
          ⇒ 不是「只相信历史自报的摘要串」——那样正文改而摘要不变就漏了，
            因为这里把每一版的全部字段都纳入投影。

        说明：本函数只是【本地一致性】指纹，不表达任何外部真实性。
        """
        parts = []
        for rid in sorted(self._history):
            hist = self._history[rid]
            # 每一版：全部字段 + 存档摘要。
            # 不排除 this_digest —— 摘要串本身被改也必须反映出来。
            ver_parts = []
            for d in hist:
                ver_parts.append(json.dumps(
                    d, sort_keys=True, ensure_ascii=False,
                    separators=(",", ":")))
            parts.append([rid, ver_parts])
        # 同时纳入 live 侧（防止 history 与 live 不一致时漏检）
        for rid in sorted(self._live):
            cur = self._live[rid]
            parts.append([rid + "\x00live",
                          json.dumps(cur.to_dict(), sort_keys=True,
                                     ensure_ascii=False,
                                     separators=(",", ":"))])
        # 纳入观测链（Mion 2026-11-24 回复4 §三）
        # ⇒ 否则「检查后改观测」不会被 stale_check 发现
        for rid in sorted(self._observed_chain):
            parts.append([rid + "\x00obs",
                          json.dumps(self._observed_chain[rid],
                                     sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":"))])
        blob = json.dumps(parts, sort_keys=True, ensure_ascii=False,
                          separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def write_log(self) -> List[Dict[str, Any]]:
        return list(self._write_log)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
