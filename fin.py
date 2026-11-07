import subprocess, os, shutil, hashlib

REPO = r'd:\qcr\ouroboros-afterglow'
BASE = os.path.join(REPO, 'reports', 'review_history')
SRC = r'd:\qcr\EntropyDrivenAI\selective_forgetting\reports\review_history'
PRE = 'reports/review_history/'

DOCS = {
    '§0': '原型实施授权申请_§0_未证明事项_草案_20261104.md',
    '§1': '原型实施授权申请_§1_范围与信任边界_草案_20261104.md',
    '§2': '原型实施授权申请_§2_P1引用完整性编码_草案_20261104.md',
    '§3': '原型实施授权申请_§3_P2身份凭证与可信消费_草案_20261105.md',
    '§4': '原型实施授权申请_§4_P5本机独占执行机制_草案_20261105.md',
    '§5': '原型实施授权申请_§5_epoch身份与持久化提交_草案_20261106.md',
    '§6': '原型实施授权申请_§6_故障矩阵_草案_20261106.md',
    '§7': '原型实施授权申请_§7_验收判定器_草案_20261106.md',
    '绑定表': '六格逐分支断言绑定表_20261107.md',
    'CHECK': 'CHECK_ALIGNMENT_WITH_S0_执行结果_20261106.md',
    '送审说明': '给凌翼_§0至§7与绑定表送审说明_Coder_20261107.md',
    '逐条应答': '给凌翼_预审意见逐条应答_Coder_20261107.md',
}

def blob(c, p):
    r = subprocess.run(['git', 'rev-parse', f'{c}:{p}'], cwd=REPO, capture_output=True)
    return r.stdout.decode().strip() if r.returncode == 0 else 'ABSENT'

out = []
for k, n in DOCS.items():
    out.append(f'| {k} | `{blob("99b7481", PRE+n)[:12]}` | `{blob("HEAD", PRE+n)[:12]}` |')
print('\n'.join(out))

# sync all to source tree
for n in DOCS.values():
    shutil.copy2(os.path.join(BASE, n), os.path.join(SRC, n))
bad = 0
for n in DOCS.values():
    a = hashlib.sha256(open(os.path.join(BASE, n), 'rb').read()).hexdigest()
    b = hashlib.sha256(open(os.path.join(SRC, n), 'rb').read()).hexdigest()
    if a != b:
        bad += 1
print('\nsync diffs =', bad)
