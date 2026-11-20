import csv,hashlib,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PROJECT=Path('/share/rickyswork/ai_mof')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    for _ in range(720):
        if (ROOT/'STRUCTURE_ANALYSIS_DONE').exists():break
        time.sleep(10)
    rows=[r for r in json.loads((ROOT/'structure_results.json').read_text()) if r['strict'] and r['converged']];out=ROOT/'zeo';out.mkdir();listfile=out/'inputs.csv'
    with listfile.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=['name','cif']);w.writeheader();w.writerows(dict(name=r['id'],cif=r['accepted_cif']) for r in rows)
    script=PROJECT/'widom_sih4/zeo_features.py';binary=PROJECT/'zeoplusplus/network';frozen=dict(script_sha256=sha(script),binary_sha256=sha(binary),inputs={r['accepted_cif']:sha(r['accepted_cif']) for r in rows},settings=dict(probe=1.4,samples=20000,ha=True,workers=4,role='descriptive; no additional filtering'))
    (out/'frozen.json').write_text(json.dumps(frozen,indent=2))
    with (out/'runtime.log').open('w') as log:r=subprocess.run([sys.executable,str(script),'--list',str(listfile),'--out',str(out/'features.csv'),'--network',str(binary),'--workers','4'],stdout=log,stderr=subprocess.STDOUT)
    (out/'status.json').write_text(json.dumps(dict(returncode=r.returncode,rows=len(rows)),indent=2))
    if r.returncode:raise SystemExit(r.returncode)
if __name__=='__main__':main()
