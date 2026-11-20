import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch
import zipfile

from mof_design.api import prepare,submit_design,get_status,cancel_design
from mof_design.common import read_json,write_json
from mof_design.config import load_runtime,normalize_request
from mof_design.delivery import finalize
from mof_design.supervisor import supervise
from mof_design.worker import execute

ROOT=Path(__file__).resolve().parents[1]
FIXTURE=ROOT/'tests/fixtures/valid_pcu.cif'

class RequestTests(unittest.TestCase):
    def setUp(self):
        self.runtime=load_runtime(ROOT/'mof_design/examples/runtime.server.json')
        self.request=read_json(ROOT/'mof_design/examples/egmof.json')
    def test_normalization_is_idempotent(self):
        a=normalize_request(self.request,self.runtime);self.assertEqual(a,normalize_request(a,self.runtime))
    def test_unknown_scene_is_rejected(self):
        self.request['scene']='sih4.co2.selectivity'
        with self.assertRaises(ValueError):normalize_request(self.request,self.runtime)
    def test_cross_engine_scene_is_rejected(self):
        self.request['engine']='mofflow2_linker'
        with self.assertRaises(ValueError):normalize_request(self.request,self.runtime)
    def test_unknown_constraints_not_silently_ignored(self):
        self.request['constraints']['pore_size']=10
        with self.assertRaises(ValueError):normalize_request(self.request,self.runtime)
    def test_unknown_request_fields_not_silently_ignored(self):
        self.request['gas']='SiH4'
        with self.assertRaises(ValueError):normalize_request(self.request,self.runtime)
    def test_nonfinite_target_rejected(self):
        for value in [float('nan'),float('inf'),True]:
            with self.subTest(value=value),self.assertRaises(ValueError):normalize_request({**self.request,'target_value':value},self.runtime)
    def test_boolean_count_rejected(self):
        with self.assertRaises(ValueError):normalize_request({**self.request,'num_candidates':True},self.runtime)
    def test_attempt_budget_must_cover_requested_count(self):
        with self.assertRaises(ValueError):normalize_request({**self.request,'max_attempts':1},self.runtime)
    def test_contradictory_elements_rejected(self):
        self.request['constraints']={'allowed_elements':['Zn'],'forbidden_elements':['Zn']}
        with self.assertRaises(ValueError):normalize_request(self.request,self.runtime)
    def test_final_topology_needs_identity_validation(self):
        self.request['constraints']={'topologies':['pcu']};self.request['validation']['mofid']=False
        with self.assertRaises(ValueError):normalize_request(self.request,self.runtime)
    def test_linker_scene_range_and_fixed_template(self):
        r=read_json(ROOT/'mof_design/examples/linker.json');r['target_value']=100
        with self.assertRaises(ValueError):normalize_request(r,self.runtime)
        r['target_value']=5;r['constraints']['topologies']=['fcu']
        with self.assertRaises(ValueError):normalize_request(r,self.runtime)

class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.assertTrue(self.root.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()))
        repo=self.root/'repo';repo.mkdir()
        for rel in ['checkpoints/desc2mof/desc2mof_best.ckpt','checkpoints/mof2desc/mof2desc_best.ckpt','prop.ckpt','prop.yaml']:
            p=repo/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('test fixture, not model weights')
        self.runtime={'version':1,'engines':{'egmof':{'python':sys.executable,'repository':str(repo),'default_scene':'test'}},'scenes':{'test':{'engine':'egmof','assets':{'prop2desc_checkpoint':str(repo/'prop.ckpt'),'prop2desc_config':str(repo/'prop.yaml')}}}}
        self.request=dict(engine='egmof',scene='test',target_value=5,num_candidates=2,max_attempts=3,validation={'relax':False,'mofid':False},walltime_seconds=30)
    def tearDown(self):
        deadline=time.monotonic()+3
        while True:
            try:self.temp.cleanup();break
            except PermissionError:
                if time.monotonic()>deadline:raise
                time.sleep(.05)
    def task(self,**changes):return prepare({**self.request,**changes},self.runtime,self.root/'runs')
    def run_fake(self,task,proposals):
        fixture=FIXTURE
        class Backend:
            def next(self,ordinal):
                if ordinal>len(proposals):raise StopIteration
                info=dict(proposals[ordinal-1]);info.setdefault('status','generated')
                if info['status']=='generated' and 'cif' not in info:
                    p=task/'work'/f'proposal{ordinal}.cif';shutil.copy2(fixture,p);info['cif']=str(p);info.setdefault('source_topology','pcu')
                return info
        execute(task,lambda *args:Backend())
        return finalize(task)
    def test_duplicate_and_failed_proposals_preserve_denominator(self):
        task=self.task();summary=self.run_fake(task,[{'source_key':'a'},{'source_key':'a'},{'status':'assembly_failed'}])
        self.assertEqual(summary['attempted'],3) if 'attempted' in summary else self.assertEqual(read_json(task/'status.json')['attempted'],3)
        self.assertEqual(summary['status'],'partial');self.assertEqual(len(read_json(task/'manifest.json')),1)
        records=read_json(task/'candidates.json');self.assertEqual(records[1]['duplicate_of'],'C0001')
        with zipfile.ZipFile(task/'candidates.zip') as z:
            self.assertEqual(len([n for n in z.namelist() if n.endswith('.cif')]),1)
            self.assertNotIn('runtime.json',z.namelist())
    def test_unsupported_elements_reject_real_structure(self):
        task=self.task(constraints={'forbidden_elements':['Zn']});summary=self.run_fake(task,[{'source_key':'a'}])
        self.assertEqual(summary['status'],'failed');self.assertFalse(read_json(task/'manifest.json'))
        self.assertIn('forbidden_elements',read_json(task/'candidates.json')[0]['reason'])
    def test_proposal_cannot_escape_task_workspace(self):
        task=self.task();summary=self.run_fake(task,[{'source_key':'a','cif':str(FIXTURE),'source_topology':'pcu'}])
        self.assertEqual(summary['status'],'failed');self.assertFalse(read_json(task/'manifest.json'))
    def test_delivery_detects_changed_cif(self):
        task=self.task(num_candidates=1);self.run_fake(task,[{'source_key':'a'}]);p=task/'cifs/C0001.cif';p.write_text(p.read_text()+'\n# changed\n')
        with self.assertRaises(ValueError):finalize(task)
    def test_portable_audit_keeps_original_task_identity(self):
        from mof_design.audit import audit
        task=self.task(num_candidates=1);self.run_fake(task,[{'source_key':'a'}]);copy=self.root/'renamed_portable_copy';shutil.copytree(task,copy)
        result=audit(copy,check_assets=False)
        self.assertTrue(result['passed']);self.assertEqual(result['task_id'],task.name)
    def test_tasks_never_overwrite_previous_run(self):
        a=self.task();b=self.task();self.assertNotEqual(a,b);self.assertTrue((a/'request.json').exists())
    def test_finished_task_refuses_second_supervisor(self):
        task=self.task(num_candidates=1);self.run_fake(task,[{'source_key':'a'}])
        with self.assertRaises(RuntimeError):supervise(task)
    def test_real_process_deadline_produces_a_package(self):
        task=self.task(walltime_seconds=1);original=subprocess.Popen
        def launch(command,*args,**kwargs):
            if isinstance(command,list) and command[1:3]==['-m','mof_design.worker']:
                command=[sys.executable,'-c','import time; time.sleep(30)']
            return original(command,*args,**kwargs)
        with patch('mof_design.supervisor.subprocess.Popen',side_effect=launch):result=supervise(task)
        self.assertEqual(result['status'],'timed_out',msg=read_json(task/'status.json'))
        self.assertTrue((task/'candidates.zip').exists());self.assertFalse(read_json(task/'manifest.json'))
    def test_async_cancellation(self):
        result=submit_design({**self.request,'walltime_seconds':15},self.runtime,self.root/'runs');task=Path(result['task_directory']);cancel_design(task)
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            result=get_status(task)
            if result['status'] in ['cancelled','failed'] and 'package' in result:break
            time.sleep(.1)
        self.assertEqual(result['status'],'cancelled');self.assertTrue((task/'candidates.zip').exists())

if __name__=='__main__':unittest.main()
