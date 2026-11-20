import os
from pathlib import Path
import subprocess
import sys
import uuid
import threading
from .common import now,read_json,write_json,sha,event,TERMINAL
from .config import load_runtime,normalize_request,preflight

def prepare(request,runtime,output_root):
    runtime=load_runtime(runtime);request=normalize_request(request,runtime);paths=preflight(request,runtime)
    root=Path(output_root).resolve();root.mkdir(parents=True,exist_ok=True);task=root/('design_'+uuid.uuid4().hex[:16]);task.mkdir()
    for name in ['logs','work','raw','optimized','validation','cifs']:(task/name).mkdir()
    write_json(task/'request.json',request);write_json(task/'runtime.json',runtime);write_json(task/'scene.json',runtime['scenes'][request['scene']]);write_json(task/'candidates.json',[])
    write_json(task/'status.json',dict(task_id=task.name,status='queued',stage='queued',created_at=now(),updated_at=now(),requested=request['num_candidates'],attempted=0,accepted=0,rejected=0))
    package=Path(__file__).resolve().parent
    files={str(Path(p).resolve()):sha(p) for p in paths.values() if Path(p).is_file() and not str(p).lower().endswith(('.exe',))}
    # Include upstream source/config assets that determine generation and support.
    engine=runtime['engines'][request['engine']];repo=Path(engine['repository']);additional=[]
    if request['engine']=='egmof':
        additional=list((repo/'src/egmof').rglob('*.py'))+[repo/'config/desc2mof_training_config.yaml',repo/'config/mof2desc_training_config.yaml']+list((repo/'src/egmof/desc2mof/data').glob('*.csv'))+list((repo/'src/egmof/desc2mof/data').glob('*.txt'))
    else:
        support=Path(runtime['scenes'][request['scene']]['assets']['support']);additional=list(support.glob('*.py'))+[repo/'experiments/predict_seq.py',repo/'data/seqs/vocab.json']
    for p in additional:
        if p.is_file():files[str(p.resolve())]=sha(p)
    commit=subprocess.run(['git','-C',str(repo),'rev-parse','HEAD'],capture_output=True,text=True).stdout.strip() if (repo/'.git').exists() else None
    write_json(task/'provenance.json',dict(module_version='0.1.0',upstream_commit=commit,asset_sha256=files,module_sha256={p.relative_to(package).as_posix():sha(p) for p in package.rglob('*.py')},request_sha256=sha(task/'request.json'),scene_sha256=sha(task/'scene.json'),constraint_application='post_generation_filter',seed=request['seed'],bitwise_gpu_reproducibility_guaranteed=False))
    event(task,'queued');return task

def run_design(request,runtime,output_root='design_runs'):
    from .supervisor import supervise
    task=prepare(request,runtime,output_root);supervise(task);return get_status(task)

def submit_design(request,runtime,output_root='design_runs'):
    task=prepare(request,runtime,output_root);env=os.environ.copy();env['PYTHONPATH']=str(Path(__file__).resolve().parent.parent)+os.pathsep+env.get('PYTHONPATH','')
    kwargs={'start_new_session':True} if os.name!='nt' else {'creationflags':subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP}
    with (task/'logs'/'supervisor.log').open('w',encoding='utf-8') as log:
        process=subprocess.Popen([sys.executable,'-m','mof_design.supervisor',str(task)],env=env,stdout=log,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,**kwargs)
    threading.Thread(target=process.wait,daemon=True).start()
    return get_status(task)

def get_status(task):
    p=Path(task).resolve();status=read_json(p/'status.json');status['task_directory']=str(p)
    if (p/'summary.json').exists():status['summary']=read_json(p/'summary.json')
    if (p/'manifest.json').exists():status['candidates']=read_json(p/'manifest.json')
    if (p/'candidates.zip').exists():status['package']=str(p/'candidates.zip')
    return status

def cancel_design(task):
    p=Path(task).resolve();status=get_status(p)
    if status['status'] not in TERMINAL:(p/'CANCEL').write_text('cancel requested\n',encoding='utf-8')
    return get_status(p)
