"""Fixed commit a47970b: unchanged snapshot, environment-configured Python, raw output capture."""
import ctypes, hashlib, json, os, pathlib, re, shutil, subprocess, sys, time
sys.stdout.reconfigure(encoding='utf-8')
base=pathlib.Path(__file__).resolve().parent
snapshot=json.loads((base/'snapshot.json').read_text(encoding='utf-8-sig'))
repo=pathlib.Path(snapshot['root']);harness=repo/'afterglow_harness'
logs=base/'logs';logs.mkdir(exist_ok=True)
py=pathlib.Path('D:/Python/python.exe')
secret=os.environ.get('AFTERGLOW_WORKER_PASSWORD')
if not secret:raise RuntimeError('Credential not injected; requested credentialed replay cannot run')
before={str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in repo.rglob('*') if p.is_file() and p != harness/'q3_full_valid_result.json'}
(base/'source_hashes_before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf-8')
artifact=harness/'q3_full_valid_result.json'
results={'snapshot':snapshot,'python':str(py),'python_version':subprocess.check_output([str(py),'--version']).decode().strip(),
         'admin_token':bool(ctypes.windll.shell32.IsUserAnAdmin()),'source_edited':False,
         'public_python_env':str(py),'artifact_existed_before_run':artifact.exists(),'runs':[]}
env=dict(os.environ,AFTERGLOW_PUBLIC_PYTHON=str(py),PYTHONUTF8='1',PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1')
# Use the host's ordinary TEMP/TMP. Component source creates disposable fixtures.
for name,script,credentialed in [('binding','verify_manifest_binding.py',False),('with_credential','q3_qualify.py',True),('reset_detail','q3_reset_chain.py',True),('without_credential','q3_qualify.py',False)]:
    child_env=env.copy()
    if not credentialed:child_env.pop('AFTERGLOW_WORKER_PASSWORD',None)
    if name == 'reset_detail':
        import uuid
        child_env['AFTERGLOW_Q3_RUN_ID'] = uuid.uuid4().hex
    cmd=[str(py),script]
    print('RUN',name,flush=True);start=time.monotonic()
    proc=subprocess.run(cmd,cwd=harness,env=child_env,capture_output=True,timeout=600)
    if secret.encode() in proc.stdout or secret.encode() in proc.stderr:
        raise RuntimeError('Credential appeared in child output; raw output withheld')
    (logs/(name+'.stdout.log')).write_bytes(proc.stdout)
    (logs/(name+'.stderr.log')).write_bytes(proc.stderr)
    output=proc.stdout.decode('utf-8',errors='replace')
    run={'name':name,'command':cmd,'cwd':str(harness),'credential_present':credentialed,
         'exit_code':proc.returncode,'elapsed_s':round(time.monotonic()-start,2),
         'component_run_id':child_env.get('AFTERGLOW_Q3_RUN_ID') if name == 'reset_detail' else None,
         'q3_run_id':next(iter(re.findall(r'^Q3_RUN_ID = (\S+)',output,re.M)),None),
         'full_valid_line':next((s for s in output.splitlines() if 'FULL_VALID_SUCCESS_PATH' in s),None)}
    if name == 'with_credential' and artifact.exists():
        shutil.copy2(artifact,base/'full_valid_with_credential.json')
        data=json.loads(artifact.read_text(encoding='utf-8'))
        run['artifact_run_id_matches']=data.get('run_id')==run['q3_run_id']
    if name == 'reset_detail' and artifact.exists():
        shutil.copy2(artifact,base/'full_valid_reset_detail.json')
        data=json.loads(artifact.read_text(encoding='utf-8'))
        run['artifact_run_id_matches']=data.get('run_id')==run['component_run_id']
    results['runs'].append(run)
    (base/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print('\n'.join(line for line in output.splitlines() if any(tag in line for tag in ('V5-N','V4-B','B2:','selftest','[FAIL]'))) if name == 'reset_detail' else output,flush=True)
    if proc.stderr:print(proc.stderr.decode('utf-8',errors='replace'),flush=True)
    print('EXIT',proc.returncode,flush=True)
results['all_snapshot_files_unchanged']=all((repo/n).is_file() and hashlib.sha256((repo/n).read_bytes()).hexdigest()==digest for n,digest in before.items())
results['snapshot_generated_artifact_excluded_from_source_check']=True
results['new_files']=[str(p.relative_to(repo)) for p in repo.rglob('*') if p.is_file() and str(p.relative_to(repo)) not in before]
(base/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
assert results['all_snapshot_files_unchanged']
print('ALL SNAPSHOT FILES UNCHANGED',results['all_snapshot_files_unchanged'])
