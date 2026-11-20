"""Existing conditional sequence model plus the validated pcu/N16 assembly."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from ..common import write_json

class LinkerBackend:
    def __init__(self,task,request,runtime):
        import yaml
        self.task=Path(task);self.request=request
        self.assets=runtime['scenes'][request['scene']]['assets'];self.cfg=runtime['engines']['mofflow2_linker']
        self.repo=Path(self.cfg['repository']);out=self.task/'work'/'sequence';model=out/'seq_module_cond';model.mkdir(parents=True)
        (model/'ckpt.pt').symlink_to(Path(self.assets['checkpoint']).resolve());shutil.copy2(self.assets['checkpoint_config'],model/'config.yaml')
        env=os.environ.copy();env['PROJECT_ROOT']=str(self.repo);env['PYTHONPATH']=str(self.repo)
        env['LD_LIBRARY_PATH']=str(Path(self.cfg['sequence_python']).parent.parent/'lib')+os.pathsep+env.get('LD_LIBRARY_PATH','')
        cmd=[self.cfg['sequence_python'],'-m','experiments.predict_seq',f'inference.ckpt_path={model}/ckpt.pt',f"inference.seed={request['seed']}",f"inference.total_samples={request['sequence_samples']}",'inference.temperature=1.0',f"inference.target_property={request['target_value']}",'inference.batch_size=50',f'hydra.run.dir={out}/hydra']
        with (self.task/'logs'/'sequence.log').open('w',encoding='utf-8') as log:
            result=subprocess.run(cmd,cwd=self.repo,env=env,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:raise RuntimeError('sequence generation failed; see logs/sequence.log')
        directory=out/'inference'/f"temp_1.0_target-{request['target_value']}";source=directory/f"preds_samples-{request['sequence_samples']}.json"
        sequences=json.loads(source.read_text());effective=yaml.safe_load((directory/'config.yaml').read_text())['inference']
        for key,value in [('seed',request['seed']),('target_property',request['target_value']),('total_samples',request['sequence_samples'])]:
            if effective[key]!=value:raise RuntimeError('effective sequence config mismatch: '+key)
        if len(sequences)!=request['sequence_samples']:raise RuntimeError('sequence count mismatch')
        sys.path.insert(0,self.assets['support'])
        from filter_generated_sbus import split_seq,is_metal,has_carbon,check_sbu,NODE_ANIONS
        from anchor_rules import find_anchors
        from rdkit import Chem
        from rdkit import RDLogger
        RDLogger.DisableLog('rdApp.*')
        self.Chem=Chem;self.pool=[];seen=set();filters=[]
        for i,sequence in enumerate(sequences):
            try:
                organic=set();metals=[]
                for part in split_seq(sequence):
                    if is_metal(part):metals.append(part);continue
                    if not has_carbon(part):
                        if part not in NODE_ANIONS:raise ValueError('non_mof_guest')
                        continue
                    ok,why,_=check_sbu(part)
                    if not ok:raise ValueError('chemical_filter:'+','.join(why))
                    organic.add(Chem.MolToSmiles(Chem.MolFromSmiles(part)))
                if not metals or len(organic)!=1:raise ValueError('requires_metal_and_one_linker_type')
                smiles=next(iter(organic));mol=self.acid_molecule(smiles);anchors=find_anchors(mol)
                if mol.GetNumHeavyAtoms()>60 or len(anchors)!=2 or any(a.rule!='carboxylate' for a in anchors):raise ValueError('requires_two_carboxylates_and_max_60_heavy_atoms')
                key=Chem.MolToSmiles(Chem.RemoveHs(mol),isomericSmiles=False)
                if key in seen:raise ValueError('duplicate_linker_identity')
                seen.add(key);self.pool.append(dict(smiles=smiles,key=key,sequence_index=i))
                filters.append(dict(index=i,status='eligible',key=key))
            except Exception as exc:filters.append(dict(index=i,status='excluded',reason=str(exc)))
        write_json(out/'filter_records.json',filters);write_json(out/'eligible_linkers.json',self.pool)
        write_json(self.task/'backend_summary.json',dict(sequence_samples=len(sequences),eligible_unique=len(self.pool),embedding_seed=7,template='pcu/N16',no_resampling=True))

    def acid_molecule(self,smiles):
        from rdkit import Chem
        mol=Chem.MolFromSmiles(smiles)
        if mol is None:raise ValueError('invalid linker')
        for _,_,o in mol.GetSubstructMatches(Chem.MolFromSmarts('[CX3](=[OX1])[O-]')):
            atom=mol.GetAtomWithIdx(o);atom.SetFormalCharge(0);atom.SetNumExplicitHs(1);atom.SetNoImplicit(True)
        Chem.SanitizeMol(mol);return mol

    def next(self,ordinal):
        if ordinal>len(self.pool):raise StopIteration
        from anchor_rules import Config,find_anchors,apply_node,embed,place_x,to_pormake_xyz
        import numpy as np
        import random
        import pormake as pm
        row=self.pool[ordinal-1];root=self.task/'work'/f'attempt_{ordinal:04d}';root.mkdir(parents=True)
        try:
            cfg=Config(seed=7);mol=self.acid_molecule(row['smiles']);anchors=apply_node(find_anchors(mol,cfg),'Zn4O');mh=embed(mol,7)
            if mh is None:raise ValueError('embedding_failed')
            actual=self.Chem.MolToSmiles(self.Chem.RemoveHs(mh),isomericSmiles=False)
            if actual!=row['key']:raise ValueError('linker identity changed during embedding')
            place_x(mh,anchors,cfg);bb=root/'linker.xyz';bb.write_text(to_pormake_xyz(mh,anchors,cfg))
            np.random.seed(19);random.seed(19);db=pm.Database();topology=db.get_topo('pcu');nt=int(topology.unique_node_types[0])
            fw=pm.Builder().build_by_type(topology=topology,node_bbs={nt:db.get_bb('N16')},edge_bbs={(nt,nt):pm.BuildingBlock(str(bb))})
            dest=root/'framework.cif';fw.write_cif(str(dest))
            return dict(status='generated',cif=str(dest),source_key='pcu/N16|'+row['key'],source_topology='pcu',expected_linker=row['smiles'],upstream=row)
        except Exception as exc:return dict(status='assembly_failed',reason=str(exc),upstream=row)
