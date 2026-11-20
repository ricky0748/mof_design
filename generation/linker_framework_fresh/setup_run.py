import json,shutil,os
from pathlib import Path
from provenance import sha

p=Path(__file__).resolve().parent
if (p/'generation_frozen.json').exists():raise RuntimeError('Already initialized')
m=Path('/share/rickyswork/ai_mof/generation/pilots/MOFFlow-2');old=m/'scale1000'
for name in ['seq_module_cond','sp_module']:
    d=p/name;d.mkdir()
    (d/'ckpt.pt').symlink_to(old/name/'ckpt.pt')
    shutil.copyfile(old/name/'config.yaml',d/'config.yaml')
sources=[old/'seq_module_cond/ckpt.pt',old/'seq_module_cond/config.yaml',old/'sp_module/ckpt.pt',old/'sp_module/config.yaml',m/'experiments/predict_seq.py',m/'experiments/predict.py',m/'data/dataset_gen.py',p/'support/filter_generated_sbus.py',p/'support/anchor_rules.py']
(p/'generation_frozen.json').write_text(json.dumps(dict(protocol=sha(p/'PROTOCOL.md'),scripts={q.name:sha(q) for q in p.glob('*.py')},pipeline=sha(p/'pipeline.sh'),sources={str(q):sha(q) for q in sources},seed=719,samples=200,temperature=1.0,target=5.0),indent=2))
print('Generation protocol frozen',flush=True)
