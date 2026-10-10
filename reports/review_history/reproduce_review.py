"""Independent review checks, not a qualifying run. Never edits the supplied repo.

Usage: python reproduce_review.py --repo PATH --out OUTPUT_DIRECTORY
Mutations are restricted to in-memory patches or separately copied repositories.
"""
from pathlib import Path
import argparse
import contextlib
import dataclasses
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

ap = argparse.ArgumentParser()
ap.add_argument('--repo', required=True)
ap.add_argument('--out', required=True)
args = ap.parse_args()
repo = Path(args.repo).resolve()
out = Path(args.out).resolve()
out.mkdir(parents=True, exist_ok=True)
scratch = out / 'scratch'
scratch.mkdir(exist_ok=True)
tempfile.tempdir = str(scratch)
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, str(repo / 'afterglow_harness'))

# Reviewed harness cleanup must remain inside the dedicated scratch directory.
original_rmtree = shutil.rmtree
def guarded_rmtree(path, *a, **kw):
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(scratch) or resolved == scratch:
        raise RuntimeError('Cleanup outside per-test scratch: ' + str(resolved))
    return original_rmtree(path, *a, **kw)
shutil.rmtree = guarded_rmtree

source_hashes = {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in repo.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
summary = {'repo': str(repo), 'baseline': [], 'counterexamples': {}}

def execute_script(tree, name, tag):
    child_out = out / (tag + '.log')
    bootstrap = '''import pathlib,sys,runpy,tempfile,shutil
root=pathlib.Path(sys.argv[1]).resolve()
script=pathlib.Path(sys.argv[2]).resolve()
tempfile.tempdir=str(root)
old=shutil.rmtree
def safe(p,*a,**kw):
    target=pathlib.Path(p).resolve()
    if not target.is_relative_to(root) or target==root: raise RuntimeError('Unsafe cleanup')
    return old(p,*a,**kw)
shutil.rmtree=safe
sys.path.insert(0,str(script.parent))
sys.argv=[str(script)]
runpy.run_path(str(script),run_name='__main__')
'''
    env = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    r = subprocess.run([sys.executable, '-c', bootstrap, str(scratch),
                        str(tree / 'afterglow_harness' / name)],
                       capture_output=True, encoding='utf-8', env=env, timeout=60)
    child_out.write_text(r.stdout + '\nSTDERR:\n' + r.stderr, encoding='utf-8')
    return {'script': name, 'exit': r.returncode,
            'tail': r.stdout.splitlines()[-7:], 'log': child_out.name}

for name in ['smoke_components.py', 'smoke_evaluator.py',
             'bd52_timing_witness_check.py', 'verify_manifest_binding.py',
             'run_known_answer_suite.py']:
    entry = execute_script(repo, name, 'baseline-' + Path(name).stem)
    summary['baseline'].append(entry)
    print(json.dumps(entry, ensure_ascii=False))

import fixtures as f
import evaluator as e
import reset
import observer
import readers

def describe(result):
    return {'actual': result.actual, 'expected': result.expected,
            'oracle_match': result.oracle_match,
            'ledger': dataclasses.asdict(result.ledger)}

# CE1: no literal write happens, yet V2/V3 claim L1 PASS and match their oracles.
with patch.object(f, 'storage_write', lambda *a, **kw: None):
    summary['counterexamples']['no_storage_write'] = {
        k: describe(fn()) for k, fn in [('V2', f.fixture_V2), ('V3', f.fixture_V3)]}

# CE2: use the wrong J function; the state no longer supports the canned class.
real_j = f.apply_j
for tag, fn, substituted_mode in [
    ('V5b_erased_instead_of_collapsed', f.fixture_V5b, 'ERASE_EFFECT'),
    ('V5d_collapsed_instead_of_erased', f.fixture_V5d, 'COLLAPSE_SIGN'),
    ('V5e_collapsed_instead_of_halved', f.fixture_V5e, 'COLLAPSE_SIGN'),
]:
    with patch.object(f, 'apply_j', lambda state, mode, m=substituted_mode: real_j(state, m)):
        summary['counterexamples'][tag] = describe(fn())

# CE3: first member fails reset, but only the last member's outcome survives.
real_reset = f._reset_arm
reset_calls = []
def first_reset_invalid(arm, restore_digest=None):
    reset_calls.append(arm.dir.name)
    h, r, outcome = real_reset(arm, restore_digest)
    if len(reset_calls) == 1:
        outcome = dataclasses.replace(outcome, reset_valid=False,
                                      reason='review: first member reset failed')
    return h, r, outcome
with patch.object(f, '_reset_arm', first_reset_invalid):
    summary['counterexamples']['first_reset_invalid'] = describe(f.fixture_V5a())
summary['counterexamples']['first_reset_invalid']['reset_arms_called'] = reset_calls

# CE4: state changes during reset; reported post class still uses pre-reset T.
def changed_during_reset(arm, restore_digest=None):
    h, r, outcome = real_reset(arm, restore_digest)
    with arm.state.write_window():
        arm.state.write_substrate(0)
    r = arm.snapshot()
    # Model an independently supplied valid-reset outcome; check whether post
    # measurement is consumed at all, separate from reset validity enforcement.
    return h, r, outcome
with patch.object(f, '_reset_arm', changed_during_reset):
    summary['counterexamples']['post_reset_state_not_consumed'] = describe(f.fixture_V5a())

# CE5: required actual read paths and independent observer are never invoked.
def forbidden(*a, **kw):
    raise AssertionError('review: required component invoked')
with contextlib.ExitStack() as stack:
    for obj, name in [(f, 'affine_read'), (f, 'literal_consume'),
                      (readers, 'affine_read'), (readers, 'literal_consume'),
                      (observer.StateObserver, 'snapshot'), (observer, 'snapshot_paths'),
                      (reset.ResetController, 'restart_worker'),
                      (reset.ResetController, 'access_probe')]:
        stack.enter_context(patch.object(obj, name, forbidden))
    results = f.run_all()
    summary['counterexamples']['required_components_unused'] = {
        'fixtures': len(results), 'oracle_matches': sum(r.oracle_match for r in results)}

# CE6: helper-level input validation does not enforce frozen member completeness.
summary['counterexamples']['empty_C3'] = dataclasses.asdict(e.evaluate_c3([], [], []))
summary['counterexamples']['invalid_L2_collapsed'] = {
    'all_invalid': e.l2_aggregate(e.INVALID, e.NOT_ASSESSED, e.NOT_ASSESSED)}

def make_mutation_copy(name):
    dest = Path(tempfile.mkdtemp(prefix=name+'-', dir=scratch)) / 'repo'
    shutil.copytree(repo, dest, ignore=shutil.ignore_patterns('__pycache__', 'afterglow_harness_artifacts'))
    return dest

# CE7: bound driver is changed to execute only one fixture. The standalone
# verifier rejects drift, but the suite's own qualification gate accepts it.
mut = make_mutation_copy('driver-coverage-mutant')
path = mut / 'afterglow_harness' / 'run_known_answer_suite.py'
raw = path.read_bytes()
assert raw.count(b'results = run_all()') == 1
path.write_bytes(raw.replace(b'results = run_all()', b'results = run_all()[:1]'))
summary['counterexamples']['driver_drift'] = {
    'verifier': execute_script(mut, 'verify_manifest_binding.py', 'mutant-driver-verifier'),
    'suite': execute_script(mut, 'run_known_answer_suite.py', 'mutant-driver-suite')}

# CE8: actual SPEC object changes, while constant hash strings stay unchanged.
mut = make_mutation_copy('spec-drift-mutant')
spec = mut / 'spec' / 'AFTERGLOW_IMPLEMENTATION_BINDING_v0.1.md'
spec.write_bytes(spec.read_bytes() + b'\nreview-only alteration\n')
summary['counterexamples']['spec_drift'] = {
    'verifier': execute_script(mut, 'verify_manifest_binding.py', 'mutant-spec-verifier'),
    'suite': execute_script(mut, 'run_known_answer_suite.py', 'mutant-spec-suite')}

# The GitHub tree is LF while 11 frozen source hashes are CRLF. Reconstruct
# exact hash-matching component bytes ONLY in a separate diagnostic copy.
# This is not a qualification of the published GitHub snapshot.
reconstructed = make_mutation_copy('crlf-diagnostic')
manifest_text = (reconstructed/'reports/AFTERGLOW_IMPLEMENTATION_BINDING_MANIFEST_v0.1.md').read_text(encoding='utf-8')
restored_files = []
for path in (reconstructed/'afterglow_harness').glob('*.py'):
    raw = path.read_bytes()
    candidate = raw.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
    if hashlib.sha256(raw).hexdigest() not in manifest_text and hashlib.sha256(candidate).hexdigest() in manifest_text:
        path.write_bytes(candidate)
        restored_files.append(path.name)
summary['crlf_diagnostic_only'] = {
    'restored_files': restored_files,
    'verifier': execute_script(reconstructed,'verify_manifest_binding.py','reconstructed-verifier'),
    'suite': execute_script(reconstructed,'run_known_answer_suite.py','reconstructed-suite'),
}
driver = reconstructed/'afterglow_harness/run_known_answer_suite.py'
original_driver = driver.read_bytes()
driver.write_bytes(original_driver.replace(b'results = run_all()',b'results = run_all()[:1]'))
summary['crlf_diagnostic_only']['one_fixture_driver_drift'] = {
    'verifier':execute_script(reconstructed,'verify_manifest_binding.py','reconstructed-one-fixture-verifier'),
    'suite':execute_script(reconstructed,'run_known_answer_suite.py','reconstructed-one-fixture-suite'),
}
driver.write_bytes(original_driver)
spec = reconstructed/'spec/AFTERGLOW_IMPLEMENTATION_BINDING_v0.1.md'
spec.write_bytes(spec.read_bytes()+b'\nreview-only alteration\n')
summary['crlf_diagnostic_only']['changed_spec'] = {
    'verifier':execute_script(reconstructed,'verify_manifest_binding.py','reconstructed-changed-spec-verifier'),
    'suite':execute_script(reconstructed,'run_known_answer_suite.py','reconstructed-changed-spec-suite'),
}

# Existing RC6 artifact consistency is checked separately from re-running.
raw = json.loads((repo/'artifacts/RC6/RC6_qualifying_run_raw.json').read_text(encoding='utf-8'))
summary['published_artifacts'] = {
    'total': len(raw['per_fixture']),
    'all_ledgers_equal_raw': all(
        item == json.loads((repo/'artifacts/RC6/ledgers'/(item['fixture_id']+'.json')).read_text(encoding='utf-8'))
        for item in raw['per_fixture']),
    'missing_V5_timing_records': 'timing_records' not in raw['per_fixture'][7]['ledger'],
}
summary['original_files_unchanged'] = all(
    hashlib.sha256((repo/p).read_bytes()).hexdigest() == h for p,h in source_hashes.items())
assert summary['original_files_unchanged']
(out/'review-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
for k,v in summary['counterexamples'].items():
    if 'actual' in v: print(k, json.dumps({'actual':v['actual'],'oracle_match':v['oracle_match']},ensure_ascii=False))
    elif k=='no_storage_write': print(k,[(n,x['actual'],x['ledger']['l1'],x['oracle_match']) for n,x in v.items()])
    else: print(k,json.dumps(v,ensure_ascii=False,default=str))
print('original_files_unchanged',summary['original_files_unchanged'])
print('crlf_diagnostic_only',json.dumps(summary['crlf_diagnostic_only'],ensure_ascii=False))
