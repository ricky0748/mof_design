import csv,json,sys,shutil,hashlib
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
BASE=Path('/share/rickyswork/ai_mof/generation/budget_confirmation_20261113')
sys.path.insert(0,str(BASE))
from identity_checks import check_identity

def main():
    frozen=json.loads((ROOT/'frozen.json').read_text());ident={r['id']:r for p in (ROOT/'mofid'/'records').glob('*.json') for r in [json.loads(p.read_text())]}
    oldident={r['id']:r for p in (BASE/'mofid'/'records').glob('*.json') for r in [json.loads(p.read_text())]}
    aliases=json.loads((BASE/'mofid_aliases.json').read_text());rows=[]
    fig,axes=plt.subplots(2,3,figsize=(15,8));histories={}
    for job in frozen['jobs']:
        name=job['name'];rec=json.loads((ROOT/'records'/f'{name}.json').read_text());r=dict(name=name,baseline_strict=job['baseline_strict'],primary=job['arm']=='S300' and job['baseline_strict'],status=rec['status'],converged=rec.get('converged',False),strict=False,seconds=rec['seconds'])
        if rec['status']=='completed':
            mi=ident.get(name,{});ci=check_identity(job['smiles'],mi,'pcu');hist=[json.loads(s) for s in (ROOT/'records'/f'{name}.history.jsonl').read_text().splitlines()];histories[name]=hist
            baseline=json.loads((BASE/'records'/f'{name}.json').read_text());original_natoms=baseline['raw_declared_natoms'];geometry=bool(rec['geometry_valid'] and rec['after']['natoms']==original_natoms)
            r.update(ci,steps=rec['steps'],geometry=geometry,original_natoms=original_natoms,final_natoms=rec['after']['natoms'],strict=bool(geometry and ci['strict_identity']),energy_change_per_atom=(hist[-1]['energy']-hist[0]['energy'])/rec['before']['natoms'],initial_atomic_fmax=hist[0]['atomic_fmax'],final_atomic_fmax=hist[-1]['atomic_fmax'],initial_filter_fmax=hist[0]['filter_fmax'],final_filter_fmax=hist[-1]['filter_fmax'],volume_change_percent=100*(rec['volume_ratio_to_start']-1),displacement_rms=rec['displacement_rms'],displacement_max=rec['displacement_max'],framework_identity_unchanged=bool(mi.get('framework_key') and mi.get('framework_key')==oldident.get(aliases.get(name,name),{}).get('framework_key')))
            for c in ['2.3','2.5','2.7']:
                before=rec['before']['coord_'+c];after=rec['after']['coord_'+c];r['cn_changed_'+c]=sum(a!=b for a,b in zip(before['cn'],after['cn']));r['angle_rms_before_'+c]=before['angle_rms'];r['angle_rms_after_'+c]=after['angle_rms']
            x=[v['step'] for v in hist]
            for ax,key in [(axes[0,1],'atomic_fmax'),(axes[0,2],'filter_fmax')]:ax.plot(x,[v[key] for v in hist],alpha=.45,lw=.8)
            if r['primary']:axes[0,0].plot(x,[(v['energy']-hist[0]['energy'])/rec['before']['natoms'] for v in hist],alpha=.45,lw=.8)
        rows.append(r)
    groups={}
    for label,predicate in [('primary_26',lambda r:r['primary']),('diagnostic_8',lambda r:not r['primary']),('all_34',lambda r:True)]:
        rs=[r for r in rows if predicate(r)];complete=[r for r in rs if r['status']=='completed'];g=dict(n=len(rs),completed=len(complete),converged=sum(r['converged'] for r in rs),strict=sum(r['strict'] for r in rs),converged_and_strict=sum(r['converged'] and r['strict'] for r in rs),lost_strict=[r['name'] for r in rs if r['baseline_strict'] and not r['strict']],rescued=[r['name'] for r in rs if not r['baseline_strict'] and r['strict']],identity_changed=[r['name'] for r in complete if not r['framework_identity_unchanged']])
        for key in ['energy_change_per_atom','volume_change_percent','displacement_rms','final_atomic_fmax','final_filter_fmax','steps']:
            vals=[r[key] for r in complete];g[key]=dict(median=float(np.median(vals)),min=float(min(vals)),max=float(max(vals))) if vals else None
        g['cn_changed_structures_2.5']=[r['name'] for r in complete if r['cn_changed_2.5']];g['atomic_fmax_above_0.05']=[r['name'] for r in complete if r['final_atomic_fmax']>=.05];groups[label]=g
    for ax,key,title in [(axes[1,0],'energy_change_per_atom','Additional energy change (eV/atom)'),(axes[1,1],'volume_change_percent','Volume change (%)'),(axes[1,2],'displacement_rms','Atomic displacement RMS (Angstrom)')]:
        for i,r in enumerate(rows):
            if key in r:ax.scatter(i,r[key],marker='o' if r['primary'] else 'x',color='tab:blue' if r['primary'] else 'tab:orange',s=22)
        ax.set(title=title,xlabel='Fixed sample order');ax.axhline(0,color='gray',lw=.5)
    for ax,title in zip(axes[0],['Energy change: primary 26 (eV/atom)','Maximum atomic force (eV/Angstrom)','Maximum filter force']):ax.set(title=title,xlabel='Additional BFGS steps');ax.grid(alpha=.15)
    for ax in axes[0,1:]:ax.set_yscale('log');ax.axhline(.05,color='black',ls='--',lw=.8)
    fig.tight_layout();fig.savefig(ROOT/'comparison.png',dpi=170);plt.close(fig)
    (ROOT/'summary.json').write_text(json.dumps(groups,indent=2));(ROOT/'per_structure.json').write_text(json.dumps(rows,indent=2));(ROOT/'histories.json').write_text(json.dumps(histories))
    accepted=ROOT/'accepted_primary';accepted.mkdir(exist_ok=True);manifest=[]
    for r in rows:
        if r['primary'] and r['strict'] and r['converged']:
            source=ROOT/'relaxed'/(r['name']+'.cif');dest=accepted/source.name;shutil.copy2(source,dest);manifest.append(dict(name=r['name'],sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),cif=str(dest),source_input_sha256=next(j['input_sha256'] for j in frozen['jobs'] if j['name']==r['name'])))
    (ROOT/'accepted_primary_manifest.json').write_text(json.dumps(manifest,indent=2))
    fields=sorted(set().union(*(r.keys() for r in rows)))
    with (ROOT/'per_structure.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    print(json.dumps(groups,indent=2))
if __name__=='__main__':main()
