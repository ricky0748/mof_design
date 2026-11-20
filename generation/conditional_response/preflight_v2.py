import hashlib,json,math,os,shutil,subprocess,time
from pathlib import Path
import numpy as np
from ase.io import read
from charge_transfer import preserve_geometry
ROOT=Path(__file__).resolve().parent/'performance_preflight_v2'
PROJECT=Path('/share/rickyswork/ai_mof')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    ROOT.mkdir(exist_ok=True);source=PROJECT/'generation/convergence_sensitivity_20261116/accepted_primary/S300_B01.cif';inp=ROOT/'control.cif'
    if (ROOT/'result.json').exists():raise RuntimeError('Refusing repeated control')
    shutil.copy2(source,inp);out=ROOT/'charged';out.mkdir(exist_ok=True);start=time.monotonic();rec=dict(source=str(source),input_sha256=sha(source),status='failed')
    try:
        import pacmof
        pacmof.get_charges_single_serial(str(inp),create_cif=True,path_to_output_dir=str(out))
        candidates=list(out.glob('*.cif'))
        if len(candidates)!=1:raise RuntimeError('expected one charged output')
        charged=candidates[0];rec['charge_transfer']=preserve_geometry(inp,charged);before=read(inp);after=read(charged,store_tags=True);charges=np.array(after.info['_atom_site_charge'],dtype=float)
        if len(after)!=len(before) or before.get_chemical_symbols()!=after.get_chemical_symbols() or not np.allclose(before.cell.array,after.cell.array,atol=1e-5) or not np.allclose(before.get_scaled_positions(),after.get_scaled_positions(),atol=1e-5):raise RuntimeError('charge assignment changed structure')
        if len(charges)!=len(after) or not np.isfinite(charges).all() or abs(charges.sum())>1e-3:raise RuntimeError('charge audit failed')
        height=after.get_volume()/np.linalg.norm(np.cross(after.cell.array[[1,2,0]],after.cell.array[[2,0,1]]),axis=1);uc=np.maximum(1,np.ceil(25.6/height)).astype(int).tolist();rec.update(charge_sum=float(charges.sum()),unit_cells=uc,charged_sha256=sha(charged),forcefield_sha256={str(p):sha(p) for sub in ['ff','molecules'] for p in (PROJECT/'widom_sih4'/sub).iterdir() if p.is_file()})
        for kind in ['widom','gcmc']:
            dest=ROOT/kind;dest.mkdir();shutil.copy2(charged,dest/'control.cif')
            for sub in ['ff','molecules']:
                for p in (PROJECT/'widom_sih4'/sub).iterdir():
                    if p.is_file():shutil.copy2(p,dest/p.name)
            lines=['SimulationType MonteCarlo','NumberOfCycles 100','NumberOfInitializationCycles 0','PrintEvery 100','RandomSeed 1701','Forcefield Local','CutOffVDW 12.8','CutOffChargeCharge 12.8','ChargeMethod Ewald','EwaldPrecision 1.0e-6','UseChargesFromCIFFile yes','Framework 0','FrameworkName control','RemoveAtomNumberCodeFromLabel yes','UnitCells '+' '.join(map(str,uc)),'ExternalTemperature 298.0']
            if kind=='gcmc':lines+=['ExternalPressure 100000.0']
            for i,(mol,fraction) in enumerate([('SiH4',.999),('CO2',.001)]):
                lines +=[f'Component {i} MoleculeName {mol}','MoleculeDefinition Local','CreateNumberOfMolecules 0']
                lines += ['WidomProbability 1.0'] if kind=='widom' else [f'MolFraction {fraction}','FugacityCoefficient 1.0','TranslationProbability 1.0','RotationProbability 1.0','ReinsertionProbability 1.0','SwapProbability 1.0']
            (dest/'simulation.input').write_text('\n'.join(lines)+'\n')
            with (dest/'raspa.log').open('w') as log:r=subprocess.run(['/usr/local/bin/simulate','simulation.input'],cwd=dest,stdout=log,stderr=subprocess.STDOUT,timeout=180)
            files=list((dest/'Output/System_0').glob('*.data'));finished=any('Simulation finished' in p.read_text(errors='replace') for p in files);rec[kind]=dict(returncode=r.returncode,finished=finished)
            if not finished:raise RuntimeError(kind+' control failed')
        rec['status']='passed'
    except Exception as exc:rec['reason']=repr(exc)
    rec['seconds']=time.monotonic()-start;(ROOT/'result.json').write_text(json.dumps(rec,indent=2));print(json.dumps(rec,indent=2))
if __name__=='__main__':main()
