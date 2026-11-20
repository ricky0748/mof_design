"""Execute proposals in the configured backend environment, with shared checks."""
import os
from pathlib import Path
import random
import shutil
import sys
from .common import event,inside,read_json,sha,state,write_json
from .config import preflight
from .validation import geometry,check_constraints,relax,mofid,normalized_linker
from .backends import create

def execute(task,backend_factory=create):
    task=Path(task).resolve();request=read_json(task/'request.json');runtime=read_json(task/'runtime.json');records=[];source_seen={};hash_seen={};identity_seen={};accepted=0
    def persist(stage):
        write_json(task/'candidates.json',records)
        state(task,stage=stage,attempted=len(records),accepted=accepted,rejected=len(records)-accepted)
    try:
        preflight(request,runtime)
        state(task,status='running',stage='loading_backend',worker_pid=os.getpid());event(task,'loading_backend')
        import numpy as np
        random.seed(request['seed']);np.random.seed(request['seed'])
        backend=backend_factory(request['engine'],task,request,runtime)
        for ordinal in range(1,request['max_attempts']+1):
            if accepted>=request['num_candidates']:break
            if (task/'CANCEL').exists():
                state(task,status='cancelled',stage='finished');break
            candidate_id=f'C{ordinal:04d}';record=dict(id=candidate_id,attempt=ordinal,engine=request['engine'],status='rejected',validation={})
            state(task,stage='generating',current_candidate=candidate_id);event(task,'generating',candidate_id=candidate_id)
            try:proposal=backend.next(ordinal)
            except StopIteration:
                event(task,'proposal_pool_exhausted');break
            except Exception as exc:
                records.append({**record,'reason':'generation_failed','detail':str(exc)});persist('generating');continue
            record['proposal']=proposal
            if proposal.get('status')!='generated':
                records.append({**record,'reason':proposal.get('status','generation_failed'),'detail':proposal.get('reason')});persist('generating');continue
            try:
                source=inside(proposal['cif'],task/'work');source_hash=sha(source);source_key=proposal['source_key']
                record.update(source_key=source_key,raw_sha256=source_hash)
                duplicate=source_seen.get(source_key) or hash_seen.get(source_hash)
                if duplicate:
                    record.update(reason='duplicate_source_or_bytes',duplicate_of=duplicate);records.append(record);persist('generating');continue
                source_seen[source_key]=candidate_id;hash_seen[source_hash]=candidate_id
                state(task,stage='checking_constraints');before=geometry(source,request['constraints']['max_atoms']);record['validation']['raw_geometry']=before
                problems=check_constraints(before,proposal['source_topology'],request['constraints'])
                if problems:raise ValueError(','.join(problems))
                raw=task/'raw'/(candidate_id+'.cif');shutil.copy2(source,raw);output=raw
                if request['validation']['relax']:
                    state(task,stage='relaxing');event(task,'relaxing',candidate_id=candidate_id)
                    output=task/'optimized'/(candidate_id+'.cif');relaxation=relax(raw,output,task,candidate_id,runtime);record['validation']['relaxation']=relaxation
                    if not relaxation['converged']:raise ValueError('relaxation_not_converged')
                    if not relaxation['atoms_preserved'] or not .75<=relaxation['volume_ratio']<=1.25:raise ValueError('relaxation_changed_atoms_or_volume_outside_range')
                after=geometry(output,request['constraints']['max_atoms']);record['validation']['final_geometry']=after
                if before['symbols']!=after['symbols'] or before['declared_natoms']!=after['natoms']:raise ValueError('atom_count_or_order_changed')
                if not after['geometry_passed']:raise ValueError('geometry_failed')
                problems=check_constraints(after,proposal['source_topology'],request['constraints'])
                if problems:raise ValueError(','.join(problems))
                if request['validation']['mofid']:
                    state(task,stage='identifying');identity=mofid(output,task,candidate_id,runtime);record['validation']['mofid']=identity
                    if identity.get('status')!='identified' or not identity.get('framework_key'):raise ValueError('mofid_not_fully_identified')
                    topology=identity.get('result',{}).get('topology')
                    if request['constraints'].get('topologies') and topology not in request['constraints']['topologies']:raise ValueError('final_topology_not_allowed')
                    if proposal.get('expected_linker'):
                        target=normalized_linker(proposal['expected_linker']);actual=[normalized_linker(s) for s in identity.get('linkers',[])]
                        if not target or not actual or any(k is None for k in actual) or set(actual)!={target} or topology!='pcu':raise ValueError('linker_or_expected_pcu_not_preserved')
                    key=identity['framework_key']
                    if key in identity_seen:
                        record.update(reason='duplicate_framework_identity',duplicate_of=identity_seen[key]);records.append(record);persist('generating');continue
                    identity_seen[key]=candidate_id
                delivered=task/'cifs'/(candidate_id+'.cif');shutil.copy2(output,delivered)
                record.update(status='accepted',cif='cifs/'+delivered.name,sha256=sha(delivered),validation_level='relaxed_geometry' if request['validation']['relax'] else 'raw_geometry',identity_verified=request['validation']['mofid'])
                accepted+=1
            except Exception as exc:record.update(reason=str(exc))
            records.append(record);persist('generating')
        current=read_json(task/'status.json')
        if current['status']!='cancelled':
            terminal='completed' if accepted==request['num_candidates'] else 'partial' if accepted else 'failed'
            state(task,status=terminal,stage='finished',reason=None if terminal=='completed' else 'proposal_budget_exhausted_or_no_acceptable_candidates',current_candidate=None)
        persist('finished');event(task,'finished',status=read_json(task/'status.json')['status'])
    except Exception as exc:
        persist('finished');state(task,status='failed',stage='finished',reason='backend_initialization_or_execution_failed',detail=str(exc));event(task,'failed',detail=str(exc));raise

if __name__=='__main__':execute(sys.argv[1])
