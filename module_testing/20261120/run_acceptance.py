"""Bounded, real-user acceptance run of the published module (no training)."""
import argparse
import copy
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

def write(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8');os.replace(tmp,p)

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def timestamp():return datetime.now(timezone.utc).isoformat()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--module',required=True);parser.add_argument('--out',required=True);args=parser.parse_args()
    module=Path(args.module).resolve();out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=False)
    sys.path.insert(0,str(module))
    from mof_design import submit_design,get_status,cancel_design
    from mof_design.audit import audit
    base=read(module/'mof_design/examples/runtime.server.json')
    default=read(module/'mof_design/examples/egmof.json');linker=read(module/'mof_design/examples/linker.json')
    cases={
        'egmof_user':{**default,'seed':20261120,'max_attempts':6,'walltime_seconds':1800,'constraints':{'max_atoms':1000,'forbidden_elements':['Cd','Hg','Pb']}},
        'linker_user':{**linker,'seed':20261121,'max_attempts':4,'walltime_seconds':1200},
        'timeout_control':{**default,'seed':20261122,'num_candidates':1,'max_attempts':1,'walltime_seconds':1,'validation':{'relax':False,'mofid':False}},
        'cancel_control':{**linker,'seed':20261123,'num_candidates':1,'max_attempts':1,'sequence_samples':200,'walltime_seconds':300,'validation':{'relax':False,'mofid':False},'constraints':{'max_atoms':1000}},
        'constraint_control':{**linker,'seed':20261124,'num_candidates':1,'max_attempts':1,'sequence_samples':50,'walltime_seconds':300,'validation':{'relax':False,'mofid':False},'constraints':{'max_atoms':1000,'forbidden_elements':['Zn']}}
    }
    gpu={'egmof_user':'0','linker_user':'1','timeout_control':'3','cancel_control':'2','constraint_control':'3'}
    protocol=dict(created_at=timestamp(),purpose='module functionality, constraints and delivery; no performance research or training',module_directory=str(module),module_sha256={str(p.relative_to(module)):sha(p) for p in (module/'mof_design').rglob('*.py')},cases=cases,expected=dict(egmof_user='completed with 2 accepted CIFs',linker_user='completed with 2 accepted CIFs',timeout_control='timed_out, no surviving task process',cancel_control='cancelled, no surviving task process',constraint_control='failed, forbidden Zn rejected, no delivered CIF'),gpu=gpu)
    write(out/'PROTOCOL.json',protocol)
    env=os.environ.copy();env['PYTHONPATH']=str(module)+os.pathsep+env.get('PYTHONPATH','')
    invalid=[]
    for name,changes,phrase in [
        ('unknown_scene',{'scene':'unknown.scene'},'scene'),
        ('cross_engine_scene',{'scene':'mofflow2.co2_working_capacity'},'scene'),
        ('unsupported_constraint',{'constraints':{'pore_size':10}},'constraint'),
        ('invalid_budget',{'num_candidates':3,'max_attempts':1},'max_attempts')]:
        root=out/'invalid'/name;root.mkdir(parents=True)
        write(root/'request.json',{**default,**changes});write(root/'runtime.json',base)
        r=subprocess.run([sys.executable,'-m','mof_design','validate','--runtime',str(root/'runtime.json'),'--request',str(root/'request.json'),'--out',str(root/'should_not_exist')],cwd=module,env=env,capture_output=True,text=True)
        (root/'stdout.log').write_text(r.stdout,encoding='utf-8');(root/'stderr.log').write_text(r.stderr,encoding='utf-8')
        invalid.append(dict(case=name,passed=r.returncode!=0 and phrase in r.stderr and not (root/'should_not_exist').exists(),returncode=r.returncode,error=r.stderr.strip()))
    write(out/'invalid_results.json',invalid)
    tasks={};histories={};completed={};case_started={}
    def launch(name):
        root=out/name;root.mkdir();runtime=copy.deepcopy(base)
        runtime['engines'][cases[name]['engine']]['cuda_visible_devices']=gpu[name]
        write(root/'request.json',cases[name]);write(root/'runtime.json',runtime)
        r=submit_design(cases[name],runtime,root/'runs');tasks[name]=r['task_directory'];case_started[name]=time.monotonic();histories[name]=None
        write(out/'tasks.json',tasks);print('launched',name,r['task_id'],flush=True)
    def observe(name):
        s=get_status(tasks[name]);key=(s['status'],s['stage'],s.get('attempted'),s.get('accepted'))
        if key!=histories[name]:
            with (out/name/'observations.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(dict(time=timestamp(),status=s),ensure_ascii=False)+'\n')
            histories[name]=key;print(name,*key,flush=True)
        return s
    def live_pids(task):
        result=[];task=str(Path(task).resolve())
        for proc in Path('/proc').glob('[0-9]*'):
            try:
                cmd=(proc/'cmdline').read_bytes().decode(errors='replace').replace('\0',' ')
                cwd=os.readlink(proc/'cwd')
                if task in cmd or cwd.startswith(task+os.sep):result.append(int(proc.name))
            except (OSError,PermissionError):pass
        return sorted(result)
    def finish(name,s):
        task=Path(tasks[name]);result=dict(case=name,task_directory=str(task),status=s,audit=audit(task),remaining_processes=live_pids(task))
        records=read(task/'candidates.json');accepted=[r for r in records if r['status']=='accepted'];result['rejections']=[dict(id=r['id'],reason=r.get('reason')) for r in records if r['status']!='accepted']
        if name.endswith('_user'):
            result['passed']=s['status']=='completed' and len(accepted)==2 and result['audit']['passed']
            # Independently reread exported CIF bytes, not the stored geometry flags.
            import numpy as np
            from ase.io import read as read_cif
            details=[]
            for entry in read(task/'manifest.json'):
                cif=task/entry['cif'];atoms=read_cif(cif,store_tags=True);d=atoms.get_all_distances(mic=True);np.fill_diagonal(d,np.inf)
                detail=dict(id=entry['id'],natoms=len(atoms),declared_natoms=len(atoms.info['_atom_site_label']),elements=sorted(set(atoms.get_chemical_symbols())),volume=float(atoms.get_volume()),minimum_distance=float(d.min()),hash_matches=sha(cif)==entry['sha256'])
                if name=='egmof_user':detail['forbidden_elements_absent']=not set(detail['elements'])&{'Cd','Hg','Pb'}
                details.append(detail)
                result['passed'] &= detail['hash_matches'] and detail['natoms']==detail['declared_natoms'] and detail['minimum_distance']>=.9 and detail.get('forbidden_elements_absent',True)
            result['independent_cif_checks']=details
        elif name=='constraint_control':
            result['passed']=s['status']=='failed' and not accepted and any('forbidden_elements' in r.get('reason','') for r in records) and result['audit']['passed']
        else:
            wanted='cancelled' if name=='cancel_control' else 'timed_out'
            result['passed']=s['status']==wanted and result['audit']['passed'] and not result['remaining_processes']
        write(out/name/'RESULT.json',result);completed[name]=result
        write(out/'RESULTS.json',dict(updated_at=timestamp(),invalid=invalid,cases=completed));print('finished',name,'passed',result['passed'],flush=True)
    launch('egmof_user');launch('linker_user');launch('timeout_control');launch('cancel_control')
    cancel_sent=False;constraint_started=False;deadline=time.monotonic()+2100
    while len(completed)<len(cases) and time.monotonic()<deadline:
        for name in list(tasks):
            if name in completed:continue
            s=observe(name)
            if name=='cancel_control' and not cancel_sent:
                sequence=Path(tasks[name])/'logs/sequence.log'
                if sequence.exists() or time.monotonic()-case_started[name]>90:
                    before=live_pids(tasks[name]);cancel_design(tasks[name]);write(out/name/'cancellation.json',dict(sent_at=timestamp(),stage=s['stage'],live_pids_before=before,sequence_log_existed=sequence.exists()));cancel_sent=True
            if s['status'] in ['completed','partial','failed','cancelled','timed_out'] and s.get('package'):
                # Supervisor exits shortly after atomic ZIP publication.
                if name in ['cancel_control','timeout_control'] and live_pids(tasks[name]):continue
                finish(name,s)
        if 'timeout_control' in completed and not constraint_started:launch('constraint_control');constraint_started=True
        time.sleep(1)
    if len(completed)<len(cases):
        for name in tasks:
            if name not in completed:cancel_design(tasks[name])
        write(out/'INCOMPLETE.json',dict(reason='test_driver_deadline',pending=[n for n in cases if n not in completed]));raise SystemExit(1)
    result=dict(updated_at=timestamp(),passed=all(r['passed'] for r in invalid) and all(r['passed'] for r in completed.values()),invalid=invalid,cases=completed)
    write(out/'RESULTS.json',result);(out/'ALL_DONE').write_text(timestamp());print('ALL_DONE',result['passed'],flush=True)
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
