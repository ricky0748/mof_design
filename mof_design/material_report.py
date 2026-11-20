"""Researcher-facing material dossiers from delivered CIFs and recorded evidence."""
import csv
import html
import io
import json
from pathlib import Path

from .common import inside, read_json, sha, write_json


def esc(value):
    return html.escape(str(value), quote=True)


def page(title, body):
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(title)}</title>
<style>body{{font:16px/1.7 system-ui,sans-serif;background:#f1f5f9;color:#233449;max-width:1160px;margin:auto;padding:28px}}
h1,h2{{color:#123d51}}h2{{margin-top:32px}}.card{{background:white;border:1px solid #d8e2e9;border-radius:14px;padding:22px;margin:18px 0}}
.scroll{{overflow:auto}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{border:1px solid #d8e2e9;text-align:left;padding:10px}}
th{{background:#eaf2f5}}a{{color:#086a91}}pre,code{{overflow-wrap:anywhere;white-space:pre-wrap}}img{{max-width:100%}}small{{color:#526878}}
@media print{{body{{background:white;padding:0}}.card{{break-inside:avoid}}}}</style><body>{body}</body></html>'''


def structure_svg(atoms):
    """Three orthographic projections; cell lines, no inferred chemical bonds."""
    import numpy as np
    from ase.data.colors import jmol_colors
    from ase.data import atomic_numbers
    from itertools import product
    corners = np.array(list(product([0, 1], repeat=3))) @ atoms.cell.array
    positions = atoms.get_positions(wrap=True)
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 380" role="img" aria-label="晶胞内原子三个笛卡尔方向的正投影">']
    for k, (axes, name) in enumerate([((0, 1), '沿 z 看 xy'), ((0, 2), '沿 y 看 xz'), ((1, 2), '沿 x 看 yz')]):
        data = np.vstack([positions, corners])[:, axes]
        lo, hi = data.min(axis=0), data.max(axis=0)
        scale = 280 / max(float((hi-lo).max()), 1)
        def xy(point):
            x, y = (point[list(axes)] - (hi+lo)/2) * scale
            return k*360+180+x, 190-y
        parts.append(f'<rect x="{k*360+5}" y="5" width="350" height="370" rx="12" fill="#fff" stroke="#d8e2e9"/><text x="{k*360+22}" y="32" font-family="sans-serif" font-size="16">{name}</text>')
        bits = list(product([0, 1], repeat=3))
        for i, a in enumerate(bits):
            for j, b in enumerate(bits[:i]):
                if sum(x!=y for x,y in zip(a,b)) == 1:
                    x,y=xy(corners[i]);u,v=xy(corners[j])
                    parts.append(f'<path d="M{x:.2f},{y:.2f} L{u:.2f},{v:.2f}" stroke="#8aa0ad" stroke-width="1.2" fill="none"/>')
        for point, symbol in zip(positions, atoms.get_chemical_symbols()):
            x,y=xy(point);rgb=jmol_colors[atomic_numbers[symbol]]
            color='#'+''.join(f'{int(c*255):02x}' for c in rgb)
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="{color}" stroke="#657885" stroke-width="0.5"><title>{symbol}</title></circle>')
    parts.append('</svg>')
    return ''.join(parts)


def describe(cif, record, request):
    from ase.io import read
    atoms = read(cif, store_tags=True)
    from .validation import METALS
    import numpy as np
    symbols = atoms.get_chemical_symbols()
    volume = float(atoms.get_volume())
    distances = atoms.get_all_distances(mic=True)
    np.fill_diagonal(distances, np.inf)
    validation = record.get('validation', {})
    identity = validation.get('mofid', {})
    data = dict(id=record['id'], cif_sha256=sha(cif), formula=atoms.get_chemical_formula(),
                formula_basis='导出 CIF 展开后的计算晶胞组成（含显式氢）', natoms=len(atoms),
                metals=sorted(set(symbols)&METALS), elements=sorted(set(symbols)),
                cell_lengths_angstrom=[float(v) for v in atoms.cell.lengths()],
                cell_angles_degree=[float(v) for v in atoms.cell.angles()], volume_angstrom3=volume,
                density_g_cm3=float(atoms.get_masses().sum()/volume*1.66053906660),
                density_method='ASE默认原子质量总和 / 晶胞体积；1 u/Å³ = 1.66053906660 g/cm³',
                minimum_distance_angstrom=float(distances.min()) if len(atoms)>1 else None,
                topology=identity.get('result', {}).get('topology'),
                topology_source='MOFid' if identity.get('status')=='identified' else '尚未确认',
                linkers=identity.get('linkers', []), mofid=identity.get('result', {}).get('mofid'),
                validation=validation, engine=request['engine'], scene=request['scene'],
                source_key=record.get('source_key'), spacegroup=dict(status='未计算'),
                pores=dict(status='待计算', method='需独立孔隙分析，记录原子半径、探针、可达性及采样参数'),
                performance=dict(status='未接入独立性能结果'), novelty=dict(status='未与指定训练集或数据库比对'))
    try:
        import spglib
        symmetry = spglib.get_symmetry_dataset((atoms.cell.array, atoms.get_scaled_positions(), atoms.numbers), symprec=0.01, angle_tolerance=-1)
        if symmetry is not None:
            data['spacegroup'] = dict(status='已计算', symbol=symmetry.international, number=int(symmetry.number),
                                     symprec_angstrom=0.01, angle_tolerance=-1, method='spglib', version=spglib.__version__)
        else:
            data['spacegroup']['reason']='容差下未识别'
    except (ImportError, RuntimeError, ValueError) as exc:
        data['spacegroup']['reason']=str(exc)
    return data, atoms


def render_material_reports(task):
    """Returns current generated file paths; missing analysis never becomes a value."""
    task=Path(task).resolve();root=task/'materials';root.mkdir(exist_ok=True)
    request=read_json(task/'request.json');records=read_json(task/'candidates.json')
    task_id=read_json(task/'status.json')['task_id'];files=[];materials=[];errors=[]
    for record in records:
        if record['status']!='accepted':continue
        try:
            cif=inside(task/record['cif'],task/'cifs')
            if sha(cif)!=record['sha256']:raise ValueError('CIF hash mismatch')
            data,atoms=describe(cif,record,request)
            # Filename follows a confined CIF stem, not unconstrained source text.
            stem=cif.stem;folder=inside(root/stem,root);folder.mkdir(exist_ok=True)
            write_json(folder/'material.json',data)
            (folder/'structure.svg').write_text(structure_svg(atoms),encoding='utf-8')
            linker_figures=[]
            try:
                from rdkit import Chem
                from rdkit.Chem import Draw
                for i,smiles in enumerate(data['linkers']):
                    mol=Chem.MolFromSmiles(smiles)
                    if mol is None:continue
                    drawer=Draw.rdMolDraw2D.MolDraw2DSVG(450,260);drawer.DrawMolecule(mol);drawer.FinishDrawing()
                    name=f'linker_{i+1}.svg';(folder/name).write_text(drawer.GetDrawingText(),encoding='utf-8')
                    linker_figures.append(f'<figure><img src="{name}" alt="连接体二维结构"><figcaption><code>{esc(smiles)}</code></figcaption></figure>')
            except ImportError:pass
            sg=data['spacegroup'];relax=data['validation'].get('relaxation',{})
            stages='；'.join(f"{s['stage']}：{s.get('steps','—')} 步，fmax 阈值 {s.get('fmax','—')} eV/Å，收敛 {s.get('converged')}" for s in relax.get('stages',[]))
            values=[('计算晶胞化学式',data['formula'],'CIF 展开组成'),('金属元素','、'.join(data['metals']),'CIF'),
                    ('拓扑',data['topology'] or '待确认',data['topology_source']),('原子数',data['natoms'],'CIF'),
                    ('a / b / c（Å）',' / '.join(f'{v:.4f}' for v in data['cell_lengths_angstrom']),'CIF'),
                    ('α / β / γ（°）',' / '.join(f'{v:.3f}' for v in data['cell_angles_degree']),'CIF'),
                    ('晶胞体积（Å³）',f'{data["volume_angstrom3"]:.3f}','几何计算'),
                    ('计算密度（g/cm³）',f'{data["density_g_cm3"]:.4f}','晶胞质量 / 体积'),
                    ('空间群',f'{sg.get("symbol","待识别")} {sg.get("number", "")}','spglib；symprec=0.01 Å' if sg['status']=='已计算' else sg.get('reason','未计算'))]
            table=''.join('<tr>'+''.join(f'<td>{esc(v)}</td>' for v in row)+'</tr>' for row in values)
            body=f'''<p><a href="../../MATERIALS.html">← 批次候选对比</a> · {esc(task_id)}</p><h1>{esc(data['id'])} · MOF 材料档案</h1>
<p>{esc(data['formula'])} · {esc(' / '.join(data['metals']))} · {esc(data['topology'] or '拓扑待确认')}</p>
<div class="card"><h2>结构概览</h2><img src="structure.svg" alt="晶胞三方向原子投影">
<p>导出晶胞内原子的笛卡尔正投影；边框为晶胞边线，未绘制化学键。投影中的空白区域需通过孔隙计算判断可达性。</p>
<p>元素：{esc('、'.join(data['elements']))}；原子颜色采用 Jmol 配色。</p></div>
<h2>材料基本信息</h2><table><tr><th>参数</th><th>结果</th><th>依据</th></tr>{table}</table>
<h2>连接体与节点</h2><p>以下连接体来自导出结构的 MOFid 分解，保留识别得到的电荷形式。</p>{''.join(linker_figures)}
<pre>{esc(json.dumps(data['linkers'],ensure_ascii=False,indent=2))}</pre>
<p>节点：<code>{esc(data['validation'].get('mofid',{}).get('result',{}).get('smiles_nodes',[]))}</code></p>
<h2>结构验证</h2><p>最终几何检查：{esc(data['validation'].get('final_geometry',{}).get('geometry_passed','未记录'))}；
最小原子距离：{data['minimum_distance_angstrom']} Å；优化收敛：{esc(relax.get('converged','未执行'))}。</p><p>{esc(stages)}</p>
<p>MOFid：<code>{esc(data['mofid'] or '未识别')}</code></p>
<h2>孔隙与应用性能</h2><table><tr><th>项目</th><th>状态</th></tr>
<tr><td>孔径、孔口、可达孔体积、表面积</td><td>待独立孔隙计算；计算时记录探针及原子半径参数</td></tr>
<tr><td>吸附量、选择性等应用性能</td><td>未接入该候选的独立性能结果</td></tr>
<tr><td>训练集 / 数据库新颖性</td><td>待指定参考集并进行身份与相似性比较</td></tr></table>
<h2>研究摘要与后续工作</h2><p>本候选为含 {esc('、'.join(data['metals']))} 的 {esc(data['topology'] or '待定拓扑')} 框架，
计算晶胞含 {data['natoms']} 个原子，密度 {data['density_g_cm3']:.4f} g/cm³。
优先补充孔隙可达性分析，再按研究气体与温压条件进行性能评价；合成路线和稳定性需进一步研究。</p>
<h2>来源与数据</h2><p>引擎 {esc(data['engine'])}；来源 {esc(data['source_key'])}。设计场景 {esc(data['scene'])} 的目标值仅作为生成条件。</p>
<p><a href="../../{esc(cif.relative_to(task).as_posix())}">下载 CIF</a> · <a href="material.json">机器可读材料数据</a> ·
<a href="../../REPORT.html">任务过程报告</a></p><small>CIF SHA256：{data['cif_sha256']}</small>'''
            (folder/'index.html').write_text(page(f'{task_id} / {data["id"]} 材料档案',body),encoding='utf-8')
            data['report']=f'materials/{stem}/index.html';materials.append(data)
            files.extend(p.relative_to(task).as_posix() for p in folder.iterdir() if p.is_file())
        except Exception as exc:
            errors.append(dict(id=record['id'],error=f'{type(exc).__name__}: {exc}'))
    write_json(task/'materials.json',dict(task_id=task_id,materials=materials,errors=errors))
    rows=''.join(f'<tr><td><a href="{esc(d["report"])}">{esc(d["id"])}</a></td><td>{esc(d["formula"])}</td><td>{esc(d["metals"])}</td><td>{esc(d["topology"] or "待确认")}</td><td>{d["natoms"]}</td><td>{d["density_g_cm3"]:.4f}</td><td>{d["volume_angstrom3"]:.2f}</td></tr>' for d in materials)
    body=f'<h1>MOF 候选材料对比</h1><p>任务 {esc(task_id)} · {len(materials)} 份材料档案</p><p>点击候选查看结构、晶体参数、连接体与验证依据。<a href="REPORT.html">任务过程报告</a></p><div class="scroll"><table><tr><th>候选</th><th>晶胞化学式</th><th>金属</th><th>拓扑</th><th>原子数</th><th>密度 g/cm³</th><th>体积 Å³</th></tr>{rows}</table></div><p>孔隙和性能结果待独立评价，当前对比不作性能排名。</p>'
    if errors:body+=f'<h2>未能生成的档案</h2><pre>{esc(json.dumps(errors,ensure_ascii=False,indent=2))}</pre>'
    if not materials and not errors:body+='<p>本任务无已交付候选。</p>'
    (task/'MATERIALS.html').write_text(page('MOF 候选材料对比',body),encoding='utf-8')
    stream=io.StringIO(newline='');writer=csv.writer(stream)
    writer.writerow(['task_id','candidate','formula','metals','topology','natoms','density_g_cm3','volume_angstrom3','cif_sha256'])
    for d in materials:writer.writerow([task_id,d['id'],d['formula'],' '.join(d['metals']),d['topology'],d['natoms'],d['density_g_cm3'],d['volume_angstrom3'],d['cif_sha256']])
    (task/'materials.csv').write_text(stream.getvalue(),encoding='utf-8-sig')
    return ['MATERIALS.html','materials.json','materials.csv']+files
