"""Independent RC7 closure review. Mutations only in memory or copied trees."""
import argparse, contextlib, dataclasses, hashlib, io, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
from fractions import Fraction
from unittest.mock import patch

ap=argparse.ArgumentParser();ap.add_argument('--repo',required=True);ap.add_argument('--out',required=True)
args=ap.parse_args();repo=Path(args.repo).resolve();out=Path(args.out).resolve()
out.mkdir(parents=True,exist_ok=True);scratch=out/'scratch';scratch.mkdir(exist_ok=True)
tempfile.tempdir=str(scratch);sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0,str(repo/'afterglow_harness'))
before={str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in repo.rglob('*') if p.is_file() and '__pycache__' not in p.parts and 'afterglow_harness_artifacts' not in p.parts}
old_rm=shutil.rmtree
def safe_rm(p,*a,**kw):
    target=Path(p).resolve()
    if not target.is_relative_to(scratch) or target==scratch:raise RuntimeError('Unsafe cleanup')
    return old_rm(p,*a,**kw)
shutil.rmtree=safe_rm

def run(tree,name,tag):
    boot='''import sys,pathlib,runpy,tempfile,shutil
root=pathlib.Path(sys.argv[1]).resolve();script=pathlib.Path(sys.argv[2]).resolve();tempfile.tempdir=str(root)
old=shutil.rmtree
def safe(p,*a,**kw):
 t=pathlib.Path(p).resolve()
 if not t.is_relative_to(root) or t==root:raise RuntimeError('Unsafe cleanup')
 return old(p,*a,**kw)
shutil.rmtree=safe
sys.path.insert(0,str(script.parent));sys.argv=[str(script)];runpy.run_path(str(script),run_name='__main__')
'''
    p=subprocess.run([sys.executable,'-c',boot,str(scratch),str(tree/'afterglow_harness'/name)],capture_output=True,encoding='utf-8',env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1'),timeout=60)
    (out/(tag+'.log')).write_text(p.stdout+'\nSTDERR:\n'+p.stderr,encoding='utf-8')
    result={'exit':p.returncode,'tail':p.stdout.splitlines()[-7:],'log':tag+'.log'}
    print(tag,json.dumps(result,ensure_ascii=False));return result

d={'baseline':{},'closed_checks':{},'remaining':{}}
for name in ['smoke_components.py','smoke_evaluator.py','bd52_timing_witness_check.py','verify_counterexamples.py','verify_manifest_binding.py','run_known_answer_suite.py']:
    d['baseline'][name]=run(repo,name,'baseline-'+Path(name).stem)

import fixtures as f
import evaluator as e
import manifest_bind as mb
import run_known_answer_suite as driver
from harness_constants import StateSnapshot,encode_substrate

def desc(r):return {'actual':r.actual,'expected':r.expected,'oracle_match':r.oracle_match,'ledger':dataclasses.asdict(r.ledger)}
with patch.object(f,'storage_write',lambda *a,**k:None):
    d['closed_checks']['V2_V3_noop']={k:desc(fn()) for k,fn in [('V2',f.fixture_V2),('V3',f.fixture_V3)]}
    d['remaining']['V5a_noop_storage']=desc(f.fixture_V5a())

real_j=f.apply_j
for tag,fn,mode in [('V5b',f.fixture_V5b,'ERASE_EFFECT'),('V5d',f.fixture_V5d,'COLLAPSE_SIGN'),('V5e',f.fixture_V5e,'COLLAPSE_SIGN')]:
    with patch.object(f,'apply_j',lambda state,m,m2=mode:real_j(state,m2)):
        d['closed_checks']['wrong_J_'+tag]=desc(fn())

real_reset=f._reset_arm;calls=[]
def first_bad(arm,fault):
    h,r,ok,reason=real_reset(arm,fault);calls.append(arm.dir.name)
    return (h,r,False,'review first required reset failure') if len(calls)==1 else (h,r,ok,reason)
with patch.object(f,'_reset_arm',first_bad):d['closed_checks']['first_reset_invalid']=desc(f.fixture_V5a())
d['closed_checks']['reset_calls']=calls

def always_invalid(arm,fault):
    h,r,ok,reason=real_reset(arm,fault);return h,r,False,'review reset failure'
with patch.object(f,'_reset_arm',always_invalid):d['remaining']['V5f_reset_invalid']=desc(f.fixture_V5f())

real_witness=f._apply_j_witnessed
def bad_timing(arm,mode):
    sw,ja,hd=real_witness(arm,mode)
    return sw,ja,StateSnapshot(hd.literal,encode_substrate(hd.q+7))
with patch.object(f,'_apply_j_witnessed',bad_timing):
    rs=f.run_all()
    d['remaining']['invalid_J_timing']={'matches':sum(r.oracle_match for r in rs),'total':len(rs),'V5a':desc(next(r for r in rs if r.fixture_id=='V5a'))}

real_extra=f.extra_write
with patch.object(f,'extra_write',lambda state,payload,mode:real_extra(state,payload,f.EXTRA_CONSTANT)):
    d['remaining']['V5b_constant_pre']=desc(f.fixture_V5b())

normal=f.fixture_V5a();d['remaining']['normal_ledger']=desc(normal)
d['remaining']['normal_ledger_mismatches']={mid:{'j_after_equals_handoff':x['j_after_digest']==x['handoff_digest'],'reported_timing_valid':x['j_timing_valid']} for mid,x in normal.ledger.per_member.items()}
d['remaining']['frozen_oracle_vs_executed']={r.fixture_id:{'frozen':mb.FIXTURE_BUNDLES[r.fixture_id]['oracle'],'executed':r.expected} for r in f.run_all() if mb.FIXTURE_BUNDLES[r.fixture_id]['oracle']!=r.expected}

# Public combined interface permits ON/OFF with identical literal storage.
root=Path(tempfile.mkdtemp(prefix='wrapper-',dir=scratch))
w_off=f.CombinedStorageWrapper(root,'off');w_on=f.CombinedStorageWrapper(root,'on')
w_off.combined_write(f.EPISODE_PAYLOADS['A1'],f.STORE_FULL,f.EXTRA_OFF)
w_on.combined_write(f.EPISODE_PAYLOADS['A1'],f.STORE_FULL,f.EXTRA_CONTENT)
d['remaining']['V4b_separable']={'off_q':w_off.arm.snapshot().q,'on_q':w_on.arm.snapshot().q,'same_literal':w_off.arm.snapshot().literal==w_on.arm.snapshot().literal,'fixture':desc(f.fixture_V4b())}

# Post-reset reader currently uses only B (q=0); substituting constant-q reader
# is not detected by these fixture oracles, while component smoke is separate.
with patch.object(f,'affine_read',lambda path,u:Fraction(u)):
    rs=f.run_all();d['remaining']['constant_reader']={'matches':sum(r.oracle_match for r in rs),'total':len(rs)}

# Integration calls now exist: fail-loud replacement must be reached.
for name in ['affine_read','literal_consume']:
    try:
        with patch.object(f,name,side_effect=RuntimeError('review reached '+name)):f.fixture_V5a()
    except RuntimeError as err:d['closed_checks'][name+'_invoked']=str(err)

def copy_repo(tag):
    dest=Path(tempfile.mkdtemp(prefix=tag+'-',dir=scratch))/'repo'
    shutil.copytree(repo,dest,ignore=shutil.ignore_patterns('__pycache__','afterglow_harness_artifacts'));return dest

mut=copy_repo('driver');p=mut/'afterglow_harness/run_known_answer_suite.py'
p.write_bytes(p.read_bytes().replace(b'results = run_all()',b'results = run_all()[:1]'))
d['closed_checks']['driver_drift_rejected']=run(mut,'run_known_answer_suite.py','mut-driver')
mut=copy_repo('spec');p=mut/'spec/AFTERGLOW_IMPLEMENTATION_BINDING_v0.1.md';p.write_bytes(p.read_bytes()+b'\nreview alteration\n')
d['closed_checks']['spec_drift_rejected']=run(mut,'run_known_answer_suite.py','mut-spec')

# manifest_bind is executed at runtime but still excluded from binding checks.
mut=copy_repo('runtime-binding-helper')
p=mut/'afterglow_harness/manifest_bind.py';p.write_bytes(p.read_bytes()+b'\nCOMPONENT_FILES = {}  # review: missing component inventory\n')
p=mut/'afterglow_harness/writers.py';p.write_bytes(p.read_bytes()+b'\n# review: bound source drift\n')
d['remaining']['unbound_runtime_helper']=run(mut,'run_known_answer_suite.py','mut-runtime-helper')

# Exact bytes and non-modification record.
d['hashes']={rel:{'bytes':(repo/rel).stat().st_size,'sha256':hashlib.sha256((repo/rel).read_bytes()).hexdigest()} for rel in ['reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md','spec/AFTERGLOW_IMPLEMENTATION_BINDING_v0.1.md','prereg/AFTERGLOW_MVP_PREREGISTRATION_v0.1.md','afterglow_harness/fixtures.py']}
d['CRLF_py']=[p.name for p in (repo/'afterglow_harness').glob('*.py') if b'\r' in p.read_bytes()]
d['original_files_unchanged']=all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==h for p,h in before.items());assert d['original_files_unchanged']
(out/'review-results.json').write_text(json.dumps(d,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
for k,v in d['remaining'].items():
    print(k,json.dumps({'actual':v['actual'],'oracle_match':v['oracle_match']} if 'actual' in v else v,ensure_ascii=False,default=str))
