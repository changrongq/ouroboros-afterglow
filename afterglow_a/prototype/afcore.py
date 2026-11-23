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

MATCH_KINDS = {"exact", "superset", "subset", "disjoint", "not_run"}

UNKNOWN_REASONS = {
    "field_absent",
    "value_conflict",
    "ref_dangling",
    "never_observed",
    "not_applicable",
}


class SchemaError(Exception):
    """任何枚举字段取值不在闭集内 ⇒ 报错，不落缺省。"""


# ---------------------------------------------------------------- 摘要

DIGEST_FIELDS_EXCLUDED = {"this_digest"}


def canonical_digest(record: Dict[str, Any]) -> str:
    """对记录做规范化摘要（排除摘要字段自身）。"""
    payload = {k: v for k, v in record.items() if k not in DIGEST_FIELDS_EXCLUDED}
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


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
        probs = rec.validate()
        if probs:
            raise SchemaError("; ".join(probs))
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

    # ---- 修订（不覆盖：旧版保留）
    def revise(self, record_id: str, changes: Dict[str, Any],
               reason: str = "", authority: Optional[str] = None) -> str:
        cur = self._live.get(record_id)
        if cur is None:
            raise KeyError(record_id)

        illegal = set(changes) - self._REVISABLE
        if illegal:
            raise SchemaError(
                "revise 不允许变更字段 %s（允许：%s）。"
                "record_id 等身份字段不得经普通 revise 变更。"
                % (sorted(illegal), sorted(self._REVISABLE)))

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
                "source_kind": basis.source_kind,
                "source_ref": basis.source_ref,
                "participant_id": basis.participant_id,
                "participation_basis": basis.participation_basis,
                "basis_ref": basis.basis_ref,
            },
            reason="correction: " + reason)

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

    def write_log(self) -> List[Dict[str, Any]]:
        return list(self._write_log)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
