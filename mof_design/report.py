"""Offline, evidence-based task reports; no model inference or remote assets."""
import html
import json
from collections import Counter
from pathlib import Path

from .common import read_json


def render_report(task, summary):
    task = Path(task)
    request = read_json(task / 'request.json')
    status = read_json(task / 'status.json')
    records = read_json(task / 'candidates.json')
    scene = read_json(task / 'scene.json')
    escape = lambda value: html.escape(str(value), quote=True)
    pretty = lambda value: escape(json.dumps(value, ensure_ascii=False, indent=2))
    rows = []
    for candidate in records:
        validation = candidate.get('validation', {})
        geometry = validation.get('final_geometry', {})
        relaxation = validation.get('relaxation', {})
        identity = validation.get('mofid', {})
        accepted = candidate['status'] == 'accepted'
        # Links are derived from IDs in the manifest, never arbitrary proposal paths.
        link = ''
        if accepted:
            from .common import inside
            cif = inside(task / candidate['cif'], task / 'cifs')
            relative = cif.relative_to(task.resolve()).as_posix()
            link = f'<a href="{escape(relative)}">下载 CIF</a>'
        cells = [candidate['id'], candidate['status'], geometry.get('natoms', '—'),
                 geometry.get('minimum_distance', '—'),
                 '已收敛' if relaxation.get('converged') else '未通过/未执行',
                 identity.get('result', {}).get('topology', '—'),
                 identity.get('status', '未执行'), candidate.get('reason', '—')]
        rows.append('<tr>' + ''.join(f'<td>{escape(v)}</td>' for v in cells)
                    + f'<td>{link}</td></tr>')
    reasons = Counter(c.get('reason', '未记录') for c in records if c['status'] != 'accepted')
    details = ''.join(f'<details><summary>{escape(c["id"])}：完整来源与验证记录</summary>'
                      f'<pre>{pretty(c)}</pre></details>' for c in records)
    cards = ''.join(f'<div class="card">{label}<strong>{escape(value)}</strong></div>' for label, value in [
        ('请求候选', summary['requested']), ('实际提案', summary['attempted']),
        ('交付候选', summary['accepted']), ('未填名额', summary['unfilled'])])
    body = f'''<h1>AI MOF 设计任务报告</h1>
<p>任务 {escape(summary['task_id'])} · 状态 {escape(summary['status'])}</p>
<div class="cards">{cards}</div>
<h2>设计目标与配置</h2>
<p>引擎：{escape(request['engine'])}；场景：{escape(request['scene'])}；
目标条件：{escape(request.get('target_value', '—'))}；随机种子：{escape(request.get('seed', '—'))}；
任务耗时：{escape(status.get('wall_seconds', '—'))} 秒。</p>
<p>目标值是模型输入条件。实际吸附性能需另行计算；单位与适用范围见场景配置。</p>
<details><summary>请求配置、预算与约束</summary><pre>{pretty(request)}</pre></details>
<details><summary>场景与单位声明</summary><pre>{pretty(scene)}</pre></details>
<h2>生成与验证流程</h2>
<p>条件生成 → 约束过滤 → 可选结构优化 → 最终几何检查 → 可选 MOFid 识别 → 去重 → CIF 交付。</p>
<p>约束在生成后检查。几何验收检查原子保持、最小距离、近似连通性和组成；
启用优化时要求两阶段收敛及体积变化在允许范围内。下表显示各候选实际记录。</p>
<h2>候选结果</h2><p><a href="MATERIALS.html">研究人员入口：材料档案与候选对比</a></p><div class="scroll"><table><thead><tr>
<th>候选</th><th>状态</th><th>原子数</th><th>最小距离 / Å</th><th>优化</th><th>拓扑</th><th>MOFid</th><th>拒绝原因</th><th>文件</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p>{'无候选提案记录。' if not records else ''}</p>
<h2>失败与未完成情况</h2><p>任务原因：{escape(status.get('reason') or '无')}；
拒绝原因统计：{escape(dict(reasons))}。</p>
<p>{escape(status.get('detail') or '')}</p>
<h2>验证范围</h2><p>本报告汇总本次任务的计算记录。实验可合成性、热力学稳定性和未配置的应用性能仍需独立评价。
MOFid 用于结构身份识别；训练集新颖性需与指定训练集额外比对。</p>
<h2>可追溯记录</h2><p><a href="request.json">请求</a> · <a href="manifest.json">候选文件与 SHA256</a> ·
<a href="provenance.json">模型和代码来源签名</a> · <a href="candidates.json">全部验证记录</a></p>{details}'''
    document = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI MOF 设计任务报告</title><style>
body{font:16px/1.7 system-ui,sans-serif;color:#183046;background:#f4f7fb;max-width:1200px;margin:auto;padding:32px}
h1,h2{color:#102e48}h2{margin-top:32px}.cards{display:flex;gap:16px;flex-wrap:wrap}
.card{background:white;border:1px solid #dce4ed;border-radius:12px;padding:16px;min-width:140px}
strong{display:block;font-size:30px}.scroll{overflow:auto}table{border-collapse:collapse;background:white;width:100%}
td,th{padding:10px;border:1px solid #dce4ed;text-align:left;white-space:nowrap}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:white;padding:16px}details{margin:12px 0}a{color:#0866ad}
@media print{body{background:white;padding:0}details{break-inside:avoid}.scroll{overflow:visible}td,th{white-space:normal}}
</style><body>''' + body + '</body></html>'
    (task / 'REPORT.html').write_text(document, encoding='utf-8')
    lines = ['# AI MOF 设计任务报告', '', f"任务：{summary['task_id']}",
             f"状态：{summary['status']}；引擎：{request['engine']}；场景：{request['scene']}",
             f"目标条件：{request.get('target_value')}；种子：{request.get('seed')}",
             f"请求 {summary['requested']}；提案 {summary['attempted']}；交付 {summary['accepted']}；未填 {summary['unfilled']}。", '',
             '完整候选表、优化与 MOFid 记录见 [可离线阅读的报告](REPORT.html)。',
             '来源与文件哈希见 provenance.json、manifest.json；逐候选验证与拒绝原因见 candidates.json。',
             '目标值为模型条件。实验可合成性、热力学稳定性、应用性能和训练集新颖性需独立评价。']
    (task / 'REPORT.md').write_text('\n\n'.join(lines) + '\n', encoding='utf-8')
