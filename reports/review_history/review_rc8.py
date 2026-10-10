"""Independent RC8 closure review. Mutations only in memory or copied trees."""
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

def run(tree,name,tag,args=()):
    boot='''import sys,pathlib,runpy,tempfile,shutil
root=pathlib.Path(sys.argv[1]).resolve();script=pathlib.Path(sys.argv[2]).resolve();tempfile.tempdir=str(root)
old=shutil.rmtree
def safe(p,*a,**kw):
 t=pathlib.Path(p).resolve()
 if not t.is_relative_to(root) or t==root:raise RuntimeError('Unsafe cleanup')
 return old(p,*a,**kw)
shutil.rmtree=safe
sys.path.insert(0,str(script.parent));sys.argv=[str(script)]+sys.argv[3:];runpy.run_path(str(script),run_name='__main__')
'''
    p=subprocess.run([sys.executable,'-c',boot,str(scratch),str(tree/'afterglow_harness'/name),*map(str,args)],capture_output=True,encoding='utf-8',env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1'),timeout=60)
    (out/(tag+'.log')).write_text(p.stdout+'\nSTDERR:\n'+p.stderr,encoding='utf-8')
    result={'exit':p.returncode,'tail':p.stdout.splitlines()[-7:],'log':tag+'.log'}
    print(tag,json.dumps(result,ensure_ascii=False));return result

d={'baseline':{},'closed_checks':{},'remaining':{}}
for name in ['smoke_components.py','smoke_evaluator.py','bd52_timing_witness_check.py','adversarial_regression.py','verify_manifest_binding.py','run_known_answer_suite.py']:
    d['baseline'][name]=run(repo,name,'baseline-'+Path(name).stem)
ledger_dir=repo/'afterglow_harness_artifacts/RC8_ledgers'
d['baseline']['recompute']=run(repo,'recompute_from_ledger.py','baseline-recompute',['--ledger',ledger_dir])

import copy
import fixtures as f
import gates as g
import evaluator as e
import qualification_binding as qb
import fixture_contracts as fc
import run_known_answer_suite as driver
import recompute_from_ledger as rec
from harness_constants import StateSnapshot,encode_substrate

def F(fid):return f.FIXTURES[fid]()
def desc(r):return {'actual':r.actual,'oracle':fc.FROZEN_ORACLES[r.fixture_id], 'oracle_match':driver._subset_eq(fc.FROZEN_ORACLES[r.fixture_id],r.actual),'ledger':dataclasses.asdict(r.ledger)}
def driver_in_memory(tag):
    target=out/tag;target.mkdir(exist_ok=True)
    s=io.StringIO()
    with patch.object(driver,'ARTIFACTS',target),patch.object(driver,'RAW_PATH',target/'raw.json'),patch.object(driver,'LEDGER_DIR',target/'ledgers'),contextlib.redirect_stdout(s):
        code=driver.main()
    (out/(tag+'.log')).write_text(s.getvalue(),encoding='utf-8')
    raw=json.loads((target/'raw.json').read_text(encoding='utf-8'))
    return {'exit':code,'preflight_ok':raw['preflight_ok'],'matches':raw['fixtures_oracle_match'],'total':raw['fixtures_total'],'suite':raw['known_answer_suite']}

with patch.object(f,'storage_write',lambda *a,**k:None):
    d['closed_checks']['V2_V3_noop']={fid:desc(F(fid)) for fid in ('V2','V3')}
    d['remaining']['V5a_noop_storage']=desc(F('V5a'))
real_extra=f.extra_write
with patch.object(f,'extra_write',lambda state,payload,mode:real_extra(state,payload,f.EXTRA_CONSTANT)):
    d['remaining']['V5b_constant_pre']=desc(F('V5b'))

real_wit=f._apply_j_witnessed
def bad_timing(arm,mode):
    sw,ja,hd=real_wit(arm,mode)
    return sw,ja,StateSnapshot(hd.literal,encode_substrate(hd.q+7))
with patch.object(f,'_apply_j_witnessed',bad_timing):d['closed_checks']['bad_timing']=desc(F('V5a'))
real_reset=f._reset_arm
calls=[]
def bad_first(arm,fault):
    h,r,ok,reason=real_reset(arm,fault);calls.append(arm.dir.name)
    return h,r,False if len(calls)==1 else ok,reason
with patch.object(f,'_reset_arm',bad_first):d['closed_checks']['first_reset_invalid']=desc(F('V5a'))
d['closed_checks']['reset_calls']=calls
def all_invalid(arm,fault):
    h,r,ok,reason=real_reset(arm,fault);return h,r,False,'review reset failure'
with patch.object(f,'_reset_arm',all_invalid):d['closed_checks']['V5f_reset_invalid']=desc(F('V5f'))

with patch.object(f,'affine_read',lambda path,u:Fraction(u)):
    d['remaining']['constant_reader']=driver_in_memory('constant-reader-suite')
with patch.object(f,'literal_consume',lambda path,u:0):
    d['remaining']['constant_literal_consumer']=driver_in_memory('constant-literal-suite')

# A state change after the J handoff witness but before reset's own handoff.
def drift_before_reset(arm,fault):
    if arm.dir.name.endswith('_C'):
        old=arm.snapshot()
        with arm.state.write_window():
            arm.state.substrate_path.write_bytes(encode_substrate(old.q*2))
    return real_reset(arm,fault)
with patch.object(f,'_reset_arm',drift_before_reset):
    d['remaining']['unlinked_reset_handoff']=desc(F('V5a'))

normal=F('V5a');d['normal_V5a']=desc(normal)
missing=copy.deepcopy(normal.ledger.observations);del missing['B2']
d['remaining']['missing_member_recompute']=rec.recompute_fixture('V5a',missing,{},'full')
stale=copy.deepcopy(normal.ledger.observations)
for o in stale.values():
    o['arms']['C']['J_after']['q_raw']=encode_substrate(123).hex()
    o['arms']['C']['reset_witness'].pop('reset_valid')
d['remaining']['stale_raw_and_missing_reset']=rec.recompute_fixture('V5a',stale,{},'full')

root=Path(tempfile.mkdtemp(prefix='wrapper-',dir=scratch))
on=f.CombinedOnlyWriter(root,'on');off=f.CombinedOnlyWriter(root,'off')
payload=f.EPISODE_PAYLOADS['A1'];on.write(payload);off.arm.store(payload,f.STORE_FULL)
d['remaining']['V4b_public_arm']={'surface':on.capability_surface(),'same_literal':on.arm.snapshot().literal==off.arm.snapshot().literal,'on_q':on.arm.snapshot().q,'off_q':off.arm.snapshot().q,'fixture':desc(F('V4b'))}

def ledger_case(tag,items):
    folder=out/tag;folder.mkdir(exist_ok=True)
    for i,item in enumerate(items):(folder/(str(i)+'.json')).write_text(json.dumps(item,ensure_ascii=False),encoding='utf-8')
    return run(repo,'recompute_from_ledger.py',tag,['--ledger',folder])
v0=json.loads((ledger_dir/'V0.json').read_text(encoding='utf-8'));v0['actual']['L1']='PASS'
d['remaining']['wrong_V0_only_ledger']=ledger_case('ledger-wrong-v0',[v0])
v5=json.loads((ledger_dir/'V5a.json').read_text(encoding='utf-8'));v5['actual']={}
d['remaining']['empty_actual_ledger']=ledger_case('ledger-empty-actual',[v5])
v5=json.loads((ledger_dir/'V5a.json').read_text(encoding='utf-8'));v5['ledger']['observations']=stale
d['remaining']['stale_digest_ledger']=ledger_case('ledger-stale-digest',[v5])

def copy_repo(tag):
    dest=Path(tempfile.mkdtemp(prefix=tag+'-',dir=scratch))/'repo'
    shutil.copytree(repo,dest,ignore=shutil.ignore_patterns('__pycache__','afterglow_harness_artifacts'));return dest
for name in ['adversarial_regression.py','recompute_from_ledger.py','qualification_binding.py','writers.py']:
    mut=copy_repo(Path(name).stem);p=mut/'afterglow_harness'/name;p.write_bytes(p.read_bytes()+b'\n# review: frozen component drift\n')
    d['remaining']['source_drift_'+name]=run(mut,'run_known_answer_suite.py','mut-'+Path(name).stem)

# Role set verification: report actual set, without changing frozen objects.
man=(repo/'reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md').read_text(encoding='utf-8')
roles=qb._parse_role_hash_map(man)
d['remaining']['role_sets']={'required_count':len(qb.REQUIRED_RUNTIME_ROLES),'bound_count':len(roles),'bound_but_unchecked':sorted(set(roles)-qb.REQUIRED_RUNTIME_ROLES),'exact_equal':set(roles)==qb.REQUIRED_RUNTIME_ROLES}
with patch.object(qb,'REQUIRED_RUNTIME_ROLES',frozenset()):d['closed_checks']['empty_roles']=driver.capture_frozen_binding()
d['closed_checks']['manifest_bind_imported']='manifest_bind' in sys.modules
d['hashes']={rel:{'bytes':(repo/rel).stat().st_size,'sha256':hashlib.sha256((repo/rel).read_bytes()).hexdigest()} for rel in ['reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md','spec/AFTERGLOW_IMPLEMENTATION_BINDING_v0.1.md','prereg/AFTERGLOW_MVP_PREREGISTRATION_v0.1.md']}
d['CRLF_py']=[p.name for p in (repo/'afterglow_harness').glob('*.py') if b'\r' in p.read_bytes()]
d['original_files_unchanged']=all(hashlib.sha256((repo/p).read_bytes()).hexdigest()==h for p,h in before.items());assert d['original_files_unchanged']
(out/'review-results.json').write_text(json.dumps(d,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
for k,v in d['remaining'].items():
    print(k,json.dumps({'actual':v['actual'],'oracle_match':v['oracle_match']} if 'actual' in v else v,ensure_ascii=False,default=str))

