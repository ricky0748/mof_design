from pathlib import Path
from ..common import inside, plain

class EGMOFBackend:
    def __init__(self,task,request,runtime):
        import torch
        torch.manual_seed(request['seed'])
        if torch.cuda.is_available():torch.cuda.manual_seed_all(request['seed'])
        from egmof import EGMOF
        self.task=Path(task);self.request=request
        assets=runtime['scenes'][request['scene']]['assets']
        cfg=runtime['engines']['egmof']
        self.model=EGMOF(prop2desc_ckpt_path=assets['prop2desc_checkpoint'],prop2desc_config_path=assets['prop2desc_config'],accelerator=cfg.get('accelerator','cpu'),devices=1)

    def next(self,ordinal):
        root=self.task/'work'/f'attempt_{ordinal:04d}';root.mkdir(parents=True)
        cif_dir=root/'cif';bbs=root/'bbs'
        df=self.model.generate(num_samples=1,target_value=self.request['target_value'],build_cif=True,cif_dir=str(cif_dir),new_bb_dir=str(bbs),num_workers=0)
        rows=[{str(k):plain(v) for k,v in row.items()} for row in df.to_dict(orient='records')]
        from ..common import write_json
        write_json(root/'upstream.json',rows)
        if not rows:return dict(status='generation_filtered',reason='upstream returned no rows')
        row=rows[0];name=row.get('filename');cif=row.get('cif')
        if len(rows)!=1:return dict(status='upstream_contract_error',reason='expected one proposal per bounded attempt',upstream=rows)
        if not isinstance(cif,str) or not cif:return dict(status='assembly_failed',reason='upstream did not produce a CIF',upstream=row)
        source=inside(cif_dir/cif,cif_dir)
        if not source.is_file():return dict(status='assembly_failed',reason='reported CIF missing',upstream=row)
        return dict(status='generated',cif=str(source),source_key=str(name),source_topology=str(name).split('+')[0],upstream=row)
