"""用理想 sql / kgm / pcu 网格检验 analyze_cg 的环统计与周期假环过滤（不需要 hoomd）。"""
import numpy as np
from analyze_cg import analyze_frame
TYPES = ["M", "A", "E", "B", "R", "C"]


def lattice(nodes, edges, L, d=0.7):
    pos, typ, own, kind = [], [], [], []
    def add(t, p, o, k): pos.append(p); typ.append(TYPES.index(t)); own.append(o); kind.append(k)
    for i, p in enumerate(nodes):
        add("M", p, i, 0)
    n = len(nodes)
    for l, (i, j) in enumerate(edges):
        v = nodes[j] - nodes[i]; v -= L * np.round(v / L); u = v / np.linalg.norm(v)
        add("E", nodes[i] + d * u, i, 0); add("E", nodes[j] - d * u, j, 0)
        add("R", nodes[i] + v / 2, n + l, 1); add("C", nodes[i] + (d + .45) * u, n + l, 1); add("C", nodes[j] - (d + .45) * u, n + l, 1)
    P = np.array(pos); P -= L * np.round(P / L)
    return P, np.array(typ), TYPES, np.array(own), np.array(kind)


a = 3.0
# sql 6x6（周期假环长 6 > 4，最小环基里不会和真实 4 元环打平）
N = 6; L = N * a
nodes = [np.array([x * a, y * a, 0.0]) for x in range(N) for y in range(N)]
idx = lambda x, y: (x % N) * N + (y % N)
edges = [(idx(x, y), idx(x + 1, y)) for x in range(N) for y in range(N)] + [(idx(x, y), idx(x, y + 1)) for x in range(N) for y in range(N)]
r = analyze_frame(*lattice(nodes, edges, L), L, 2); print("sql", r["rings"], "periodic", r["n_periodic_loops"], "bridging", r["frac_bridging"])
assert r["rings"] == {4: 35} and r["n_periodic_loops"] == 2

# kgm 3x3（三角形 + 六边形）
N = 4; L = N * 2 * a
a1, a2 = np.array([2 * a, 0, 0]), np.array([a, np.sqrt(3) * a, 0])
# 用正交盒：kgm 的正交超胞 = 2 个原胞，这里改用斜坐标近似不方便，换成正交化的长方超胞
# 直接构造：kgm 原胞 3 个位点；为配合立方盒，用 N×N 斜格并要求 L 方向周期，取 a2 投影不整除会出错 → 仅检验非周期有限片
sites = []
M = 3
for i in range(M):
    for j in range(M):
        o = i * a1 + j * a2
        sites += [o, o + a1 / 2, o + a2 / 2]
sites = [s + 20 for s in sites]
Lb = 200.0
P = np.array(sites); E = []
for i in range(len(P)):
    for j in range(i + 1, len(P)):
        if abs(np.linalg.norm(P[i] - P[j]) - a) < 1e-6:
            E.append((i, j))
r = analyze_frame(*lattice([np.array(p) for p in P], E, Lb), Lb, 2); print("kgm(有限片)", r["rings"], "frac3", r["frac3"])
assert set(r["rings"]) <= {3, 6} and r["rings"].get(3, 0) > 0 and r["rings"].get(6, 0) > 0

# pcu 5x5x5
N = 5; L = N * a
nodes = [np.array([x * a, y * a, z * a]) for x in range(N) for y in range(N) for z in range(N)]
idx = lambda x, y, z: (x % N) * N * N + (y % N) * N + (z % N)
edges = []
for x in range(N):
    for y in range(N):
        for z in range(N):
            edges += [(idx(x, y, z), idx(x + 1, y, z)), (idx(x, y, z), idx(x, y + 1, z)), (idx(x, y, z), idx(x, y, z + 1))]
r = analyze_frame(*lattice(nodes, edges, L), L, 2); print("pcu", r["rings"], "periodic", r["n_periodic_loops"])
assert set(r["rings"]) == {4}
print("OK")
