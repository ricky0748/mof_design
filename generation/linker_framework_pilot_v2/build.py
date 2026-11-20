import argparse,contextlib,hashlib,io,json,random,time
from pathlib import Path
import numpy as np
import pormake as pm


def build(id,arm,bbpath,template,out,kind='ligand'):
    start=time.monotonic()
    rec=dict(id=id,arm=arm,name=arm+'_'+id,status='failed',template=template,kind=kind)
    try:
        np.random.seed(7);random.seed(7)
        with contextlib.redirect_stdout(io.StringIO()):
            db=pm.Database();t=db.get_topo(template['topology']);nt=int(t.unique_node_types[0])
            bb=db.get_bb(template['edge']) if kind=='stock' else pm.BuildingBlock(bbpath)
            fw=pm.Builder().build_by_type(topology=t,node_bbs={nt:db.get_bb(template['node'])},edge_bbs={(nt,nt):bb})
            path=out/'raw'/(rec['name']+'.cif');fw.write_cif(str(path))
        rec.update(status='built',cif=str(path),natoms=len(fw.atoms),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    except Exception as exc:rec['reason']=type(exc).__name__+': '+str(exc)
    rec['seconds']=round(time.monotonic()-start,3)
    return rec


def main():
    ap=argparse.ArgumentParser();ap.add_argument('out');ap.add_argument('--controls-only',action='store_true');a=ap.parse_args()
    out=Path(a.out).resolve();(out/'raw').mkdir(exist_ok=True)
    f=json.loads((out/'frozen.json').read_text())
    for name,expected in f['inputs_sha256'].items():
        if hashlib.sha256((out/name).read_bytes()).hexdigest()!=expected:raise RuntimeError('Frozen decision changed: '+name)
    records=[]
    if a.controls_only:
        for c in json.loads((out/'controls.json').read_text()):
            records.append(build(c['id'],'control',c.get('bb'),c['template'],out,c['kind']))
    else:
        cal=json.loads((out/'calibration.json').read_text())
        if not cal['linear_positive_pass']:raise RuntimeError('Linear positive control failed')
        targets=json.loads((out/'targets.json').read_text())
        decisions={d['id']:d for d in json.loads((out/'decisions.json').read_text())}
        templates={t['name']:t for t in json.loads((out/'templates.json').read_text())}
        for row in targets:
            if hashlib.sha256(Path(row['bb']).read_bytes()).hexdigest()!=row['bb_sha256']:raise RuntimeError('Frozen BB changed')
            records.append(build(row['id'],'U',row['bb'],dict(topology='pcu',node='N16'),out))
            chosen=decisions[row['id']]['match']
            if chosen:
                records.append(build(row['id'],'M',row['bb'],templates[chosen['template']],out))
            else:records.append(dict(id=row['id'],arm='M',name='M_'+row['id'],status='no_match'))
            print(json.dumps(records[-2:],ensure_ascii=False),flush=True)
    (out/('controls_build.json' if a.controls_only else 'build.json')).write_text(json.dumps(records,ensure_ascii=False,indent=2))
    print('builds',len(records),flush=True)


if __name__=='__main__':main()
