"""patchy 自组装轨迹分析：配位饱和、桥连、网络连通、环大小分布（拓扑指纹）。

判定:
  C bead 与某个 E 位点距离 < BIND_CUT → 该连接点配位到该 E 所属节点
  配体连到 ≥2 个不同节点 → 桥连；两端连同一节点 → 同节点螯合（浪费）
  rod 节点额外用 A–A 距离 < A_CUT 判断链内相邻
环: 节点–配体二部图（ditopic 配体收缩为节点–节点边）上的最小环基；
    沿环累加最小像位移，|Σ| > L/2 的是绕周期边界的"假环"，单独计数、不进环分布。
    ditopic 配体时环大小 = 环上节点数（sql/pcu → 4，kgm → 3 和 6，MOP 立方八面体 → 3 和 4）。

用法: python analyze_cg.py cases/<name>.npz runs/<name>.gsd [--last 10] [--json out.json]
"""
import sys, json, argparse, collections
import numpy as np
import networkx as nx

BIND_CUT, A_CUT = 0.8, 0.7


def _mic(d, L):
    return d - L * np.round(d / L)


def _nearest(P, Q, L):
    """P 中每点到 Q 的最近点（索引, 距离），周期边界。"""
    D = _mic(P[:, None, :] - Q[None, :, :], L)
    r = np.sqrt((D * D).sum(-1))
    j = r.argmin(1)
    return j, r[np.arange(len(P)), j]


def analyze_frame(pos, typeid, types, owner, kind, L, linker_conn):
    t = np.array(types)[typeid]
    owner = np.asarray(owner).astype(int); kind = np.asarray(kind)
    Eidx = np.where(t == "E")[0]; Cidx = np.where(t == "C")[0]; Midx = np.where(t == "M")[0]
    n_nodes = len(Midx)
    center = {int(owner[i]): pos[i] for i in Midx}
    lig_ids = [int(l) for l in sorted(set(owner[kind == 1]))]
    for l in lig_ids:                                  # 配体中心：其 bead 的最小像平均
        b = pos[owner == l]; center[l] = b[0] + _mic(b - b[0], L).mean(0)
    j, r = _nearest(pos[Cidx], pos[Eidx], L)
    bound = r < BIND_CUT
    e_owner = owner[Eidx[j]]
    att = collections.defaultdict(list)
    for c, ok, n in zip(Cidx, bound, e_owner):
        if ok:
            att[int(owner[c])].append(int(n))
    E_used = len(set(Eidx[j][bound]))
    occ = collections.Counter(collections.Counter(Eidx[j][bound].tolist()).get(e, 0) for e in Eidx)
    n_bridge = sum(1 for l in lig_ids if len(set(att[l])) >= 2)
    n_intra = sum(1 for l in lig_ids if len(att[l]) >= 2 and len(set(att[l])) == 1)
    # 网络
    G = nx.Graph(); G.add_nodes_from(int(m) for m in sorted(set(owner[Midx])))
    multi = collections.Counter()
    if linker_conn == 2:
        for l in lig_ids:
            s = sorted(set(att[l]))
            if len(s) == 2:
                multi[tuple(s)] += 1; G.add_edge(*s)
        ring_unit = 1
    else:
        for l in lig_ids:
            for n in set(att[l]):
                G.add_edge(("L", l), n)
        ring_unit = 2
    Gr = G.copy()                                       # 环统计只用配体桥连边（不含 A–A 链内边）
    chains, inter_chain, intra_chain = 0, None, None
    if "A" in types and (t == "A").any():
        Aidx = np.where(t == "A")[0]
        D = _mic(pos[Aidx][:, None] - pos[Aidx][None], L); rr = np.sqrt((D * D).sum(-1))
        CH = nx.Graph(); CH.add_nodes_from(int(m) for m in sorted(set(owner[Midx])))
        for a, b in zip(*np.where((rr < A_CUT) & (rr > 0))):
            if owner[Aidx[a]] != owner[Aidx[b]]:
                u, v = int(owner[Aidx[a]]), int(owner[Aidx[b]]); CH.add_edge(u, v); G.add_edge(u, v, chain=True)
        chains = nx.number_connected_components(CH)
        cid = {n: k for k, c in enumerate(nx.connected_components(CH)) for n in c}
        br = [l for l in lig_ids if len(set(att[l])) >= 2]
        inter_chain = round(sum(1 for l in br if len({cid[n] for n in att[l]}) >= 2) / max(len(lig_ids), 1), 3)
        intra_chain = round(sum(1 for l in br if len({cid[n] for n in att[l]}) == 1) / max(len(lig_ids), 1), 3)
    node_set = {int(m) for m in owner[Midx]}
    comps = sorted((len(c & node_set) for c in nx.connected_components(G)), reverse=True)

    def cpos(v):
        return center[v[1]] if isinstance(v, tuple) else center[v]
    rings, periodic, nonsimple = collections.Counter(), 0, 0
    try:
        basis = nx.minimum_cycle_basis(Gr)
    except Exception as e:
        print("cycle basis failed:", e); basis = []
    for cyc in basis:
        H = Gr.subgraph(cyc)
        if any(d != 2 for _, d in H.degree()):
            nonsimple += 1; continue
        order = [u for u, _ in nx.find_cycle(H)]
        disp = sum(_mic(cpos(order[(i + 1) % len(order)]) - cpos(order[i]), L) for i in range(len(order)))
        if np.linalg.norm(disp) > L / 2:
            periodic += 1
        else:
            rings[len(order) // ring_unit] += 1
    nr = sum(rings.values())
    return dict(frac_E_bound=round(E_used / max(len(Eidx), 1), 3), frac_C_bound=round(float(bound.mean()), 3),
                C_per_node=round(float(bound.sum()) / n_nodes, 3),
                E_occupancy={int(k): int(v) for k, v in sorted(occ.items())},
                frac_bridge_inter_chain=inter_chain, frac_bridge_intra_chain=intra_chain,
                frac_bridging=round(n_bridge / max(len(lig_ids), 1), 3), frac_intra_node=round(n_intra / max(len(lig_ids), 1), 3),
                n_double_bridge=int(sum(v - 1 for v in multi.values() if v > 1)),
                largest_component_frac=round(comps[0] / n_nodes, 3) if comps else 0.0, n_components=len(comps),
                n_chains=chains, rings={int(k): int(v) for k, v in sorted(rings.items())}, n_rings=nr,
                frac3=round(rings[3] / nr, 3) if nr else None, frac4=round(rings[4] / nr, 3) if nr else None,
                frac6=round(rings[6] / nr, 3) if nr else None, n_periodic_loops=periodic, n_nonsimple=nonsimple)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("spec"); ap.add_argument("gsd")
    ap.add_argument("--last", type=int, default=10); ap.add_argument("--json")
    a = ap.parse_args()
    import gsd.hoomd
    S = np.load(a.spec, allow_pickle=False); meta = json.loads(str(S["meta"]))
    types = [str(x) for x in S["types"]]
    with gsd.hoomd.open(a.gsd, "r") as tr:
        frames = [tr[i] for i in range(max(0, len(tr) - a.last), len(tr))]
    res = [analyze_frame(np.asarray(f.particles.position, float), np.asarray(f.particles.typeid), list(f.particles.types),
                         S["owner"], S["kind"], meta["L"], meta["linker_conn"]) for f in frames]
    scal = [k for k, v in res[-1].items() if isinstance(v, (int, float)) and v is not None]
    out = dict(case=meta["case"], seed=meta["seed"], n_frames=len(res), final=res[-1],
               mean_last={k: round(float(np.mean([r[k] for r in res if r[k] is not None])), 3) for k in scal
                          if any(r[k] is not None for r in res)})
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if a.json:
        json.dump(out, open(a.json, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
