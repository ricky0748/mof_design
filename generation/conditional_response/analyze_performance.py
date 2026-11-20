import csv,hashlib,json,math,statistics,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'performance';PROJECT=Path('/share/rickyswork/ai_mof')
sys.path.insert(0,str(PROJECT/'widom_sih4'));from parse_widom import parse_dir
sys.path.insert(0,str(PROJECT/'generation'));from parse_gcmc import one as parse_gcmc
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def finite(v):return isinstance(v,(int,float)) and math.isfinite(v)
def clean(x):
    if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
    if isinstance(x,list):return [clean(v) for v in x]
    return None if isinstance(x,float) and not math.isfinite(x) else x
def dist(values):
    v=[x for x in values if finite(x)];return dict(n=len(v),median=statistics.median(v),min=min(v),max=max(v)) if v else dict(n=0)
def main():
    frozen=json.loads((OUT/'frozen.json').read_text());jobs=json.loads((OUT/'jobs_frozen.json').read_text());errors=[];parsed=[]
    for n,h in {**frozen['inputs'],**frozen['forcefield']}.items():
        if sha(n)!=h:errors.append('frozen source changed '+n)
    if sha('/usr/local/bin/simulate')!=frozen['simulator_sha256']:errors.append('simulator changed')
    for job in jobs:
        dest=Path(job['directory']);rec=json.loads((dest/'record.json').read_text());row=dict(id=job['id'],seed=job['seed'],kind=job['kind'],status=rec['status'])
        if sha(dest/'simulation.input')!=job['input_sha256'] or sha(dest/(job['id']+'.cif'))!=job['cif_sha256']:errors.append('gas input changed '+str(dest))
        if min(job['supercell_heights'])<25.6:errors.append('supercell too small '+str(dest))
        for n,h in rec['output_sha256'].items():
            if sha(n)!=h:errors.append('gas output changed '+n)
        if rec['status']=='completed':
            if job['kind']=='widom':
                status,data=parse_dir(str(dest));row['parse_status']=status
                for mol in ['SiH4','CO2']:
                    row['K_'+mol]=data.get(mol,{}).get('K');row['Kerr_'+mol]=data.get(mol,{}).get('K_err')
                a,b=row['K_SiH4'],row['K_CO2'];row['S_CO2']=b/a if finite(a) and finite(b) and a>0 and b>=0 else None
                row['relative_error_above_50pct']=any(finite(row['K_'+m]) and finite(row['Kerr_'+m]) and row['K_'+m]>0 and row['Kerr_'+m]/row['K_'+m]>.5 for m in ['SiH4','CO2'])
            else:
                data=parse_gcmc(str(dest));row.update({k:v for k,v in data.items() if k not in ['mof','status']});row['parse_status']=data['status'];row['zero_co2']=finite(row.get('q_CO2')) and row['q_CO2']==0
                row['relative_error_above_50pct']=any(finite(row.get('q_'+m)) and finite(row.get('q_'+m+'_err')) and row['q_'+m]>0 and row['q_'+m+'_err']/row['q_'+m]>.5 for m in ['SiH4','CO2'])
        parsed.append(row)
    structures=json.loads((ROOT/'structure_results.json').read_text());charge={r['id']:r for r in json.loads((OUT/'charge_results.json').read_text())};per=[]
    for s in structures:
        r=dict(id=s['id'],memberships=s['memberships'],structure_accepted=bool(s['strict'] and s['converged']),charge_status=charge.get(s['id'],{}).get('status','not_run'),replicates=[p for p in parsed if p['id']==s['id']])
        for kind,fields in [('widom',['K_SiH4','K_CO2','S_CO2']),('gcmc',['q_SiH4','q_CO2','S_CO2'])]:
            ps=[p for p in r['replicates'] if p['kind']==kind and p.get('parse_status')=='ok'];valid=[p for p in ps if all(finite(p.get(f)) for f in fields)]
            r[kind+'_valid_replicates']=len(valid)
            if len(valid)==2:
                for field in fields:r[kind+'_'+field]=statistics.mean(p[field] for p in valid)
                r[kind+'_S_CO2_replicate_min']=min(p['S_CO2'] for p in valid);r[kind+'_S_CO2_replicate_max']=max(p['S_CO2'] for p in valid)
                r[kind+'_uncertain']=any(p.get('relative_error_above_50pct',False) or p.get('zero_co2',False) for p in valid)
        per.append(r)
    groupnames=list(json.loads((ROOT/'groups.json').read_text()));summary={}
    for label in groupnames+['target2_unique','target5_unique']:
        rs=[r for r in per if any(m['group']==label if label in groupnames else m['group'].endswith('_t'+('2' if label=='target2_unique' else '5')) for m in r['memberships'])]
        g=dict(selected_unique=len(rs),structure_accepted=sum(r['structure_accepted'] for r in rs),charge_passed=sum(r['charge_status']=='passed' for r in rs))
        for kind in ['widom','gcmc']:
            g[kind+'_both_replicates']=sum(r[kind+'_valid_replicates']==2 for r in rs);g[kind+'_uncertain']=[r['id'] for r in rs if r.get(kind+'_uncertain')]
            for field in (['K_SiH4','K_CO2','S_CO2'] if kind=='widom' else ['q_SiH4','q_CO2','S_CO2']):g[kind+'_'+field]=dist([r.get(kind+'_'+field) for r in rs])
        summary[label]=g
    audit=dict(passed=not errors,errors=errors,total_jobs=len(jobs),completed=sum(r['status']=='completed' for r in parsed),scope='frozen performance sources, input/output hashes and box widths; simulator numerical convergence not independently established')
    for name,data in [('parsed_runs.json',parsed),('per_candidate.json',per),('summary.json',summary),('AUDIT.json',audit)]: (OUT/name).write_text(json.dumps(clean(data),indent=2,allow_nan=False))
    flat=[{k:v for k,v in r.items() if k not in ['memberships','replicates']} for r in per];fields=sorted(set().union(*(r.keys() for r in flat)))
    with (OUT/'per_candidate.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(clean(flat))
    print(json.dumps(clean(summary),indent=2,allow_nan=False))
    if errors:raise RuntimeError(errors)
    (ROOT/'PERFORMANCE_ANALYSIS_DONE').write_text('complete')
if __name__=='__main__':main()
