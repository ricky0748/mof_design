import json,shutil,subprocess
from pathlib import Path
import yaml
from provenance import sha

p=Path(__file__).resolve().parent
if (p/'generation_frozen.json').exists():raise RuntimeError('Already initialized')
m=Path('/share/rickyswork/ai_mof/generation/pilots/MOFFlow-2');old=m/'scale1000'
for name in ['seq_module_cond','sp_module']:
    d=p/name;d.mkdir();(d/'ckpt.pt').symlink_to(old/name/'ckpt.pt')
    cfg=yaml.safe_load((old/name/'config.yaml').read_text())
    if name=='sp_module':
        cfg['data']['loader']['batch_size']['predict']=8
        cfg['data']['loader']['num_workers']=4
    (d/'config.yaml').write_text(yaml.safe_dump(cfg,sort_keys=False))
sources=[old/n/x for n in ['seq_module_cond','sp_module'] for x in ['ckpt.pt','config.yaml']]+[m/x for x in ['experiments/predict_seq.py','experiments/predict.py','data/dataset_gen.py','data/metals/metal_lib_train.pkl','data/seqs/vocab.json']]+[p/'support/filter_generated_sbus.py',p/'support/anchor_rules.py']
f=dict(protocol=sha(p/'PROTOCOL.md'),scripts={q.name:sha(q) for q in p.glob('*.py')},pipeline=sha(p/'pipeline.sh'),sources={str(q):sha(q) for q in sources},local_configs={str(q.relative_to(p)):sha(q) for q in p.glob('*/config.yaml')},seed=1301,samples=600,temperature=1.,target=5.)
(p/'generation_frozen.json').write_text(json.dumps(f,indent=2))
(p/'gpu_inventory.txt').write_text(subprocess.check_output(['nvidia-smi','--query-gpu=index,name,memory.total','--format=csv,noheader'],text=True))
print('Generation protocol frozen: 600 sequences, seed1301',flush=True)
