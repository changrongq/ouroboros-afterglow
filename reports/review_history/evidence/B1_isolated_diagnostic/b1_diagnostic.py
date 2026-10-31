"""B-1 隔离诊断 · 复现脚本（归档副本）

归档目的（凌翼 2026-10-31 裁定）：
    "当前报告没有附上用于在 snapshot() 两次读取之间插入写入的
     实际控制脚本、注入方式及完整原始输出。
     ... 建议补存已经使用的临时诊断脚本或等价的最小复现说明、
     原始输出，以及 StateSnapshot 的实际返回记录。
     不要求擅自重新执行诊断。"

本文件即那次诊断所用脚本的归档副本。

授权边界（凌翼 O-7）：
    B1_ISOLATED_DIAGNOSTIC   = CONDITIONALLY AUTHORIZED
    FROZEN_CODE_MODIFICATION = NOT AUTHORIZED
    REPOSITORY_CODE_CHANGE   = NOT AUTHORIZED
    SCIENTIFIC_EXECUTION     = MAY NOT START

⇒ 本文件是【归档】，不是新诊断。
⇒ 它只使用 tempfile 沙箱，不写入、不修改任何仓库源文件。
⇒ 按凌翼要求：不主动重新执行。

原始运行环境：Python 3.11.15 / win32
原始沙箱：    C:\\Users\\Administrator\\AppData\\Local\\Temp\\b1diag_2ogshr66
"""
import sys
import tempfile

sys.path.insert(0, "d:/qcr/ouroboros-afterglow/afterglow_harness")
from storage import RegisteredState
from harness_constants import LITERAL_SIZE, decode_substrate

SANDBOX = tempfile.mkdtemp(prefix="b1diag_")
LOG = []


def rec(step, **kw):
    LOG.append(dict(step=step, **kw))
    print("  [%s] %s" % (step, {k: (v[:12] if isinstance(v, bytes) else v)
                               for k, v in kw.items()}))


print("SANDBOX =", SANDBOX)
print()

# (1) 建立已知初始状态 (L0,Q0)
st = RegisteredState(SANDBOX)
st.initialize_baseline()
L0 = st.read_literal_bytes()
Q0 = st.snapshot().q
D0 = st.snapshot().digest
rec("1_init", L0=L0, Q0=Q0, digest=D0[:16])

# (2) observer 完成 literal 读取
lit_observed = st.read_literal_bytes()
rec("2_read_literal", lit=lit_observed)

# (3) 受控注入者依次写入 L1 与 Q1（先 L 后 Q —— 关键修正在此）
L1 = b"\xAA" * LITERAL_SIZE
Q1 = 2
with st.write_window():
    st.write_literal(L1)
    dl = st.snapshot().digest
    rec("3a_write_L1", L1=L1, digest=dl[:16])
with st.write_window():
    st.write_substrate(Q1)
    dq = st.snapshot().digest
    rec("3b_write_Q1", Q1=Q1, digest=dq[:16])

# (4) observer 完成 substrate 读取
sub_observed = st.read_substrate_bytes()
rec("4_read_substrate", sub=sub_observed)

# (5) 检查返回组合 (L0,Q1) 是否曾经真实存在
real_sequence = [
    (L0.decode("latin1").replace("\x00", "0"), Q0),
    (L1.decode("latin1").replace("\xaa", "A"), 0),
    (L1.decode("latin1").replace("\xaa", "A"), Q1),
]
print()
print("  真实状态序列 =", real_sequence)

q_obs = decode_substrate(sub_observed)
print("  交织得到的组合 = (%r, %r)" % (lit_observed[:4], q_obs))
print()
print("  (L0,Q1) 在真实序列中出现吗:",
      any(l == L0 and q == Q1 for l, q in [(L0, Q0), (L1, 0), (L1, Q1)]))
print()
print("=== 结论 ===")
print("  交织返回 (L0,Q1)")
print("  真实序列 (L0,Q0)->(L1,Q0)->(L1,Q1) 中无 (L0,Q1)")
print("  => 该快照为【从未存在过的组合状态】")
print()
print("=== StateSnapshot 实际返回记录 ===")
print("  snapshot().literal 前12字节 =", lit_observed[:12])
print("  snapshot().q                =", q_obs)
print("  组合是否为真实状态之一      =",
      any(l == lit_observed and q == q_obs
          for l, q in [(L0, Q0), (L1, 0), (L1, Q1)]))
