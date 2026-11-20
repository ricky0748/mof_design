"""不需要 hoomd 的输入自检：键长与 r0 一致、无严重重叠、索引合法，并用初始构型试跑分析脚本。"""
import glob, json, sys
import numpy as np
from analyze_cg import analyze_frame, _mic

bad = 0
for f in sorted(glob.glob("cases/*.npz")):
    S = np.load(f, allow_pickle=False); m = json.loads(str(S["meta"])); P = S["position"]; L = m["L"]
    assert np.all(np.abs(P) <= L / 2 + 1e-6), f
    bt = m["bond_types"]; g = S["bond_group"]
    r = np.linalg.norm(_mic(P[g[:, 0]] - P[g[:, 1]], L), axis=1)
    r0 = np.array([m["bond_par"][bt[t]]["r0"] for t in S["bond_typeid"]])
    at = m["angle_types"]; a = S["angle_group"]
    v1 = _mic(P[a[:, 0]] - P[a[:, 1]], L); v2 = _mic(P[a[:, 2]] - P[a[:, 1]], L)
    th = np.arccos(np.clip((v1 * v2).sum(1) / np.linalg.norm(v1, axis=1) / np.linalg.norm(v2, axis=1), -1, 1))
    t0 = np.array([m["angle_par"][at[t]]["t0"] for t in S["angle_typeid"]])
    D = _mic(P[:, None] - P[None], L); dd = np.sqrt((D * D).sum(-1)); np.fill_diagonal(dd, 99)
    own = S["owner"]; inter = own[:, None] != own[None]
    dmin = dd[inter].min()
    tt = np.array([str(x) for x in S["types"]])[S["typeid"]]; Ci = np.where(tt == "C")[0]
    dcc = dd[np.ix_(Ci, Ci)][inter[np.ix_(Ci, Ci)]].min()
    need_cc = 2 ** (1 / 6) * 1.45 * 0.85 if m["patch"] == "single" else 0.3
    res = analyze_frame(P, S["typeid"], [str(t) for t in S["types"]], own, S["kind"], L, m["linker_conn"])
    ok = np.abs(r - r0).max() < 1e-3 and np.abs(th - t0).max() < 1e-3 and dmin > 0.3 and dcc > need_cc
    bad += not ok
    print(f"{f:32s} N={len(P):4d} L={L:6.2f} |Δr|max={np.abs(r-r0).max():.1e} |Δθ|max={np.degrees(np.abs(th-t0).max()):.1e}° "
          f"分子间最近={dmin:.2f} C–C最近={dcc:.2f}  初始 E 配位={res['frac_E_bound']}  {'OK' if ok else 'FAIL'}")
sys.exit(bad)
