import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from ase import Atoms
from ase.io import write
import run as runner
from provenance import sha,signature,validate_record
from compute_config import settings_for

class RunnerTests(unittest.TestCase):
    def fixture(self,steps):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);p=Path(t.name)
        model=p/'model';model.write_bytes(b'model');(p/'worker.py').write_text('version=1');(p/'support').mkdir();(p/'support/anchor_rules.py').write_text('support')
        source=p/'raw.cif';write(source,Atoms('CC',positions=[[0,0,0],[1.5,0,0]],cell=[10,10,10],pbc=True));output=p/'result.cif';output.write_bytes(b'result')
        source_row=dict(name='S300_B01',status='built',cif=str(source),max_steps=300,timeout=1200);dest_row={**source_row,'name':'D7_B01','max_steps':150,'timeout':600}
        (p/'build.json').write_text(json.dumps([source_row,dest_row]));(p/'records').mkdir()
        record=dict(status='completed',out=str(output),output_sha256=sha(output),calculation_signature=signature(source,model,p,settings_for(source_row)),steps=steps,converged=True,wall_seconds=40.,physical_seconds=40.)
        (p/'records/S300_B01.json').write_text(json.dumps(record));(p/'frozen.json').write_text(json.dumps(dict(inputs={'build.json':sha(p/'build.json')},scripts={'worker.py':sha(p/'worker.py')},support=sha(p/'support/anchor_rules.py'),model=sha(model))))
        return p,model,dest_row
    def test_early_result_materialized_without_process(self):
        p,model,dest=self.fixture(100)
        with patch.object(runner,'MODEL',str(model)),patch('sys.argv',['run.py',str(p),'--phase','secondary']),patch.object(runner.subprocess,'Popen') as launch:
            runner.main();launch.assert_not_called()
        r=validate_record(p/'records/D7_B01.json',signature(dest['cif'],model,p,settings_for(dest)))
        self.assertEqual(r['derived_from'],'S300_B01');self.assertEqual(r['max_steps'],150);self.assertEqual(r['steps'],100)
    def test_longer_source_runs_separate_short_budget(self):
        p,model,dest=self.fixture(200)
        with patch.object(runner,'MODEL',str(model)),patch('sys.argv',['run.py',str(p),'--phase','secondary']),patch.object(runner.subprocess,'Popen') as launch:
            launch.return_value.returncode=1;launch.return_value.wait.return_value=1;runner.main();self.assertEqual(launch.call_count,1)
        r=json.loads((p/'records/D7_B01.json').read_text());self.assertEqual(r['status'],'failed');self.assertNotIn('derived_from',r)

if __name__=='__main__':unittest.main(verbosity=2)
