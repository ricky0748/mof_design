import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from .common import read_json,state,event,TERMINAL
from .delivery import finalize

def terminate_tree(process):
    if process.poll() is not None:return
    if os.name=='nt':
        try:subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
        except (OSError,subprocess.TimeoutExpired):pass
        # A constrained Windows environment may deny taskkill while the parent
        # still owns a valid termination handle for its direct worker.
        if process.poll() is None:process.kill()
    else:
        # Include subprocesses that start their own sessions (e.g. official MOFid).
        pairs=[]
        for line in subprocess.check_output(['ps','-eo','pid=,ppid='],text=True).splitlines():
            try:p,pp=map(int,line.split());pairs.append((p,pp))
            except ValueError:pass
        family={process.pid}
        while True:
            children={p for p,pp in pairs if pp in family}
            if children<=family:break
            family|=children
        for pid in sorted(family,reverse=True):
            try:os.kill(pid,signal.SIGKILL)
            except ProcessLookupError:pass
    process.wait(timeout=15)

def supervise(task):
    task=Path(task).resolve();runtime=read_json(task/'runtime.json');request=read_json(task/'request.json');cfg=runtime['engines'][request['engine']]
    if read_json(task/'status.json')['status']!='queued':raise RuntimeError('Task already started; refusing concurrent run or overwrite')
    state(task,supervisor_pid=os.getpid(),stage='starting');process=None;started=time.monotonic()
    try:
        env=os.environ.copy();root=str(Path(__file__).resolve().parent.parent)
        env['PYTHONPATH']=root+os.pathsep+cfg['repository']+os.pathsep+env.get('PYTHONPATH','');env.update(OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2',MKL_NUM_THREADS='2')
        if cfg.get('cuda_visible_devices') is not None:env['CUDA_VISIBLE_DEVICES']=str(cfg['cuda_visible_devices'])
        kwargs={'start_new_session':True} if os.name!='nt' else {'creationflags':subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP}
        with (task/'logs'/'worker.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen([cfg['python'],'-m','mof_design.worker',str(task)],cwd=cfg['repository'],env=env,stdout=log,stderr=subprocess.STDOUT,**kwargs)
            state(task,worker_pid=process.pid)
            while process.poll() is None:
                if (task/'CANCEL').exists():
                    terminate_tree(process);state(task,status='cancelled',stage='finished',reason='cancel_requested');break
                if time.monotonic()-started>=request['walltime_seconds']:
                    terminate_tree(process);state(task,status='timed_out',stage='finished',reason='walltime_budget_exhausted');break
                time.sleep(.2)
        status=read_json(task/'status.json')
        if status['status'] not in TERMINAL:state(task,status='failed',stage='finished',reason='worker_exited_without_terminal_state',exit_code=process.returncode)
    except KeyboardInterrupt:
        if process is not None:terminate_tree(process)
        state(task,status='cancelled',stage='finished',reason='keyboard_interrupt')
    except Exception as exc:
        if process is not None:terminate_tree(process)
        state(task,status='failed',stage='finished',reason='supervisor_failed',detail=str(exc))
    finally:
        state(task,wall_seconds=round(time.monotonic()-started,3));event(task,'supervisor_finished')
    return finalize(task)

if __name__=='__main__':supervise(sys.argv[1])
