"""Additional targeted RC8 checks. No baseline rerun, no source mutations."""
import argparse, contextlib, dataclasses, hashlib, io, json, shutil, sys, tempfile
from pathlib import Path
from unittest.mock import patch

ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
args=ap.parse_args();repo=Path(args.repo).resolve();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
scratch=out/'scratch';scratch.mkdir(exist_ok=True);tempfile.tempdir=str(scratch)
sys.stdout.reconfigure(encoding='utf-8');sys.dont_write_bytecode=True;sys.path.insert(0,str(repo/'afterglow_harness'))
old_rm=shutil.rmtree
def safe_rm(p,*a,**kw):
    target=Path(p).resolve()
    if not target.is_relative_to(scratch) or target==scratch:raise RuntimeError('unsafe cleanup')
    return old_rm(p,*a,**kw)
shutil.rmtree=safe_rm
import fixtures as f
import qualification_binding as qb
import run_known_answer_suite as driver
import gates as g

before={str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in repo.rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'afterglow_harness_artifacts' not in p.parts}
d={}
real=f.FIXTURES['V5b'];real_extra=f.extra_write
def constant_v5b():
    with patch.object(f,'extra_write',lambda s,p,m:real_extra(s,p,f.EXTRA_CONSTANT)):
        return real()
target=out/'constant-pre-suite';target.mkdir(exist_ok=True);s=io.StringIO()
with patch.dict(f.FIXTURES,{'V5b':constant_v5b}),patch.object(driver,'ARTIFACTS',target),patch.object(driver,'RAW_PATH',target/'raw.json'),patch.object(driver,'LEDGER_DIR',target/'ledgers'),contextlib.redirect_stdout(s):
    code=driver.main()
(out/'constant-pre-suite.log').write_text(s.getvalue(),encoding='utf-8')
raw=json.loads((target/'raw.json').read_text(encoding='utf-8'))
d['constant_pre_suite']={'exit':code,'preflight_ok':raw['preflight_ok'],'suite':raw['known_answer_suite'],'matches':raw['fixtures_oracle_match'],'V5b':next(x['actual'] for x in raw['per_fixture'] if x['fixture_id']=='V5b')}

with patch.object(f,'_MEMBERS',('A1','A2','B1')):
    r=f.FIXTURES['V5b']()
    d['missing_member_V5b']={'actual':r.actual,'oracle_match':driver._subset_eq(driver.FROZEN_ORACLES['V5b'],r.actual)}

text=(repo/'reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md').read_text(encoding='utf-8')
section=text.split('# 十三 ·')[1].split('# 十四 ·')[0]
roles=qb._parse_role_hash_map(section)
d['section13_roles']={'count':len(roles),'required_count':len(qb.REQUIRED_RUNTIME_ROLES),'unchecked':sorted(set(roles)-qb.REQUIRED_RUNTIME_ROLES)}
d['original_files_unchanged']=all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==h for p,h in before.items());assert d['original_files_unchanged']
(out/'followup-results.json').write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8');print(json.dumps(d,indent=2,ensure_ascii=False))
