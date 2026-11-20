import concurrent.futures,contextlib,hashlib,json,os,shutil,signal,subprocess,time
from pathlib import Path
import numpy as np
from ase.io import read
from charge_transfer import preserve_geometry
from raspa_cif import adapt
ROOT=Path(__file__).resolve().parent;PROJECT=Path('/share/rickyswork/ai_mof');OUT=ROOT/'performance'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def charge(row):
    dest=OUT/'charges'/row['id'];dest.mkdir(parents=True);rec=dict(id=row['id'],source=row['accepted_cif'],input_sha256=sha(row['accepted_cif']),status='failed');start=time.monotonic()
    try:
        import pacmof
        with (dest/'pacmof.log').open('w') as log,contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):pacmof.get_charges_single_serial(row['accepted_cif'],create_cif=True,path_to_output_dir=str(dest))
        files=list(dest.glob('*.cif'))
        if len(files)!=1:raise ValueError('expected one charged CIF')
        file=files[0];rec['transfer']=preserve_geometry(row['accepted_cif'],file);adapt(file);rec.update(status='passed',cif=str(file),sha256=sha(file))
    except Exception as exc:rec['reason']=repr(exc)
    rec['seconds']=time.monotonic()-start;(dest/'record.json').write_text(json.dumps(rec,indent=2));return rec
def input_text(name,uc,seed,kind):
    lines=['SimulationType MonteCarlo',f"NumberOfCycles {5000 if kind=='widom' else 30000}",f"NumberOfInitializationCycles {0 if kind=='widom' else 5000}",'PrintEvery 1000',f'RandomSeed {seed}','Forcefield Local','CutOffVDW 12.8','CutOffChargeCharge 12.8','ChargeMethod Ewald','EwaldPrecision 1.0e-6','UseChargesFromCIFFile yes','Framework 0',f'FrameworkName {name}','RemoveAtomNumberCodeFromLabel yes','UnitCells '+' '.join(map(str,uc)),'ExternalTemperature 298.0']
    if kind=='gcmc':lines+=['ExternalPressure 100000.0']
    for i,(mol,fraction) in enumerate([('SiH4',.999),('CO2',.001)]):
        lines +=[f'Component {i} MoleculeName {mol}','MoleculeDefinition Local','CreateNumberOfMolecules 0']
        lines += ['WidomProbability 1.0'] if kind=='widom' else [f'MolFraction {fraction}','FugacityCoefficient 1.0','TranslationProbability 1.0','RotationProbability 1.0','ReinsertionProbability 1.0','SwapProbability 1.0']
    return '\n'.join(lines)+'\n'
def main():
    import sklearn,pacmof
    if sklearn.__version__!='1.7.2':raise RuntimeError('PACMOF environment must use sklearn1.7.2')
    if OUT.exists():raise RuntimeError('Refusing overwrite performance campaign')
    if json.loads((ROOT/'performance_preflight_v3/result.json').read_text())['status']!='passed':raise RuntimeError('Control failed')
    if not json.loads((ROOT/'STRUCTURE_AUDIT.json').read_text())['passed']:raise RuntimeError('Structure audit failed')
    OUT.mkdir();(OUT/'charges').mkdir();selected={r['id']:r for r in json.loads((ROOT/'selected.json').read_text())};rows=json.loads((ROOT/'structure_results.json').read_text());eligible=[];excluded=[]
    for r in rows:
        if not (r['strict'] and r['converged']):excluded.append(dict(id=r['id'],reason='structure_not_accepted'));continue
        if selected[r['id']]['formal_charge']!=0:excluded.append(dict(id=r['id'],reason='charge_compensation_unmodeled'));continue
        if sha(r['accepted_cif'])!=r['sha256']:raise RuntimeError('Source hash mismatch '+r['id'])
        eligible.append(r)
    pkg=Path(pacmof.__file__).parent
    files=[ROOT/'PERFORMANCE_PROTOCOL.md',ROOT/'structure_results.json',ROOT/'STRUCTURE_AUDIT.json',ROOT/'selected.json',ROOT/'performance_preflight_v3/result.json',ROOT/'performance.py',ROOT/'charge_transfer.py',ROOT/'raspa_cif.py']+[p for p in pkg.rglob('*') if p.is_file() and '__pycache__' not in str(p) and (p.suffix in ['.py','.pkl','.joblib','.pickle'] or 'model' in p.name.lower())]
    frozen=dict(inputs={str(p):sha(p) for p in files},forcefield={str(p):sha(p) for sub in ['ff','molecules'] for p in (PROJECT/'widom_sih4'/sub).iterdir() if p.is_file()},simulator_sha256=sha('/usr/local/bin/simulate'),eligible=[dict(id=r['id'],cif=r['accepted_cif'],sha256=r['sha256']) for r in eligible],excluded=excluded,sklearn=sklearn.__version__,settings=dict(seeds=[1701,1702],temperature=298,pressure=100000,mol_fraction_co2=.001,widom_cycles=5000,gcmc_cycles=30000,gcmc_initialization=5000,workers=16,timeout_seconds=14400))
    (OUT/'frozen.json').write_text(json.dumps(frozen,indent=2))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:charged=list(pool.map(charge,eligible))
    (OUT/'charge_results.json').write_text(json.dumps(charged,indent=2));jobs=[]
    for r in charged:
        if r['status']!='passed':continue
        atoms=read(r['cif']);height=atoms.get_volume()/np.linalg.norm(np.cross(atoms.cell.array[[1,2,0]],atoms.cell.array[[2,0,1]]),axis=1);uc=np.maximum(1,np.ceil(25.6/height)).astype(int).tolist()
        for seed in [1701,1702]:
            for kind in ['widom','gcmc']:
                dest=OUT/'runs'/r['id']/str(seed)/kind;dest.mkdir(parents=True);shutil.copy2(r['cif'],dest/(r['id']+'.cif'))
                for sub in ['ff','molecules']:
                    for p in (PROJECT/'widom_sih4'/sub).iterdir():
                        if p.is_file():shutil.copy2(p,dest/p.name)
                inp=dest/'simulation.input';inp.write_text(input_text(r['id'],uc,seed,kind));jobs.append(dict(id=r['id'],seed=seed,kind=kind,directory=str(dest),unit_cells=uc,supercell_heights=(height*np.array(uc)).tolist(),input_sha256=sha(inp),cif_sha256=sha(dest/(r['id']+'.cif'))))
    (OUT/'jobs_frozen.json').write_text(json.dumps(jobs,indent=2))
    def run(job):
        dest=Path(job['directory']);start=time.monotonic();rec={**job,'status':'failed'};env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
        with (dest/'raspa.log').open('w') as log:
            p=subprocess.Popen(['/usr/local/bin/simulate','simulation.input'],cwd=dest,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            try:p.wait(timeout=14400)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait();rec['reason']='timeout'
        files=list((dest/'Output/System_0').glob('*.data'));finished=any('Simulation finished' in f.read_text(errors='replace') for f in files)
        rec.update(returncode=p.returncode,status='completed' if finished else 'failed',seconds=time.monotonic()-start,output_sha256={str(f):sha(f) for f in files});(dest/'record.json').write_text(json.dumps(rec,indent=2));print(job['id'],job['seed'],job['kind'],rec['status'],flush=True);return rec
    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:results=list(pool.map(run,jobs))
    (OUT/'run_results.json').write_text(json.dumps(results,indent=2));(ROOT/'PERFORMANCE_RUNS_DONE').write_text(str(len(results)))
if __name__=='__main__':main()
