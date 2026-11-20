import json,tempfile,unittest
from pathlib import Path
from ase import Atoms
from provenance import signature,validate_record,verify_frozen,sha
from compute_config import SETTINGS
from relax_one import metrics
from unittest.mock import patch
from ase.io import write
import run as runner

class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.p=Path(self.tmp.name);self.model=self.p/'model';self.model.write_bytes(b'model')
        self.cif=self.p/'input.cif';self.cif.write_bytes(b'input')
        (self.p/'worker.py').write_text('version=1')
        self.sig=signature(self.cif,self.model,self.p,SETTINGS)
        self.output=self.p/'relaxed.cif';self.output.write_bytes(b'result')
        self.record=self.p/'record.json'
        self.data=dict(status='completed',out=str(self.output),calculation_signature=self.sig,output_sha256=sha(self.output))
        self.save()
    def save(self):self.record.write_text(json.dumps(self.data))
    def test_unchanged_record_reused(self):validate_record(self.record,self.sig)
    def test_input_change_rejected(self):
        self.cif.write_bytes(b'changed')
        with self.assertRaises(RuntimeError):validate_record(self.record,signature(self.cif,self.model,self.p,SETTINGS))
    def test_model_change_rejected(self):
        self.model.write_bytes(b'changed')
        with self.assertRaises(RuntimeError):validate_record(self.record,signature(self.cif,self.model,self.p,SETTINGS))
    def test_script_change_rejected(self):
        (self.p/'worker.py').write_text('version=2')
        with self.assertRaises(RuntimeError):validate_record(self.record,signature(self.cif,self.model,self.p,SETTINGS))
    def test_parameter_change_rejected(self):
        with self.assertRaises(RuntimeError):validate_record(self.record,signature(self.cif,self.model,self.p,{**SETTINGS,'steps':151}))
    def test_unsigned_legacy_rejected(self):
        del self.data['calculation_signature'];self.save()
        with self.assertRaises(RuntimeError):validate_record(self.record,self.sig)
    def test_tampered_output_rejected(self):
        self.output.write_bytes(b'changed')
        with self.assertRaises(RuntimeError):validate_record(self.record,self.sig)
    def test_missing_output_rejected(self):
        self.output.unlink()
        with self.assertRaises(RuntimeError):validate_record(self.record,self.sig)
    def test_skin_not_counted_as_bond(self):
        # C-C threshold is 2*0.76*1.15=1.748 A; a 2.1 A pair must be separate.
        self.assertEqual(metrics(Atoms('CC',positions=[[0,0,0],[2.1,0,0]],cell=[20,20,20]))['fragments'],2)
    def test_short_pair_connected(self):
        self.assertEqual(metrics(Atoms('CC',positions=[[0,0,0],[1.5,0,0]],cell=[20,20,20]))['fragments'],1)
    def test_frozen_model_verified(self):
        (self.p/'support').mkdir();(self.p/'support/anchor_rules.py').write_text('support')
        f=dict(inputs={'input.cif':sha(self.cif)},scripts={'worker.py':sha(self.p/'worker.py')},support=sha(self.p/'support/anchor_rules.py'),model=sha(self.model))
        (self.p/'frozen.json').write_text(json.dumps(f));verify_frozen(self.p,self.model)
        self.model.write_bytes(b'changed')
        with self.assertRaises(RuntimeError):verify_frozen(self.p,self.model)
    def runner_fixture(self,signed):
        write(self.cif,Atoms('CC',positions=[[0,0,0],[1.5,0,0]],cell=[20,20,20],pbc=True))
        (self.p/'support').mkdir();support=self.p/'support/anchor_rules.py';support.write_text('support')
        builds=self.p/'build.json';builds.write_text(json.dumps([dict(name='U_X',status='built',cif=str(self.cif))]))
        frozen=dict(inputs={'build.json':sha(builds)},scripts={'worker.py':sha(self.p/'worker.py')},support=sha(support),model=sha(self.model))
        (self.p/'frozen.json').write_text(json.dumps(frozen));(self.p/'records').mkdir()
        self.data['calculation_signature']=signature(self.cif,self.model,self.p,SETTINGS)
        if not signed:del self.data['calculation_signature']
        (self.p/'records/U_X.json').write_text(json.dumps(self.data))
    def test_runner_rejects_unsigned_before_launch_or_manifest(self):
        self.runner_fixture(False)
        with patch.object(runner,'MODEL',str(self.model)),patch('sys.argv',['run.py',str(self.p)]),patch.object(runner.subprocess,'Popen') as launch:
            with self.assertRaises(RuntimeError):runner.main()
            launch.assert_not_called()
        self.assertFalse((self.p/'run.json').exists())
        self.assertFalse((self.p/'manifest.jsonl').exists())
    def test_runner_reuses_signed_without_launch(self):
        self.runner_fixture(True)
        with patch.object(runner,'MODEL',str(self.model)),patch('sys.argv',['run.py',str(self.p)]),patch.object(runner.subprocess,'Popen') as launch:
            runner.main();launch.assert_not_called()
        manifest=[json.loads(l) for l in (self.p/'manifest.jsonl').read_text().splitlines()]
        self.assertEqual(len(manifest),1)

if __name__=='__main__':unittest.main(verbosity=2)
