"""读取 cg_build 生成的 spec.npz，用 HOOMD 5 跑 patchy 自组装。

写法刻意与 mof303/cg_patchy3.py 保持一致（同一套 hoomd 5.2.0 API，已在服务器 hoomd5 环境验证过）：
  Snapshot → LJ(全部 WCA，A-A / E-C 吸引) + Harmonic bond + Harmonic angle → Langevin + Ramp 退火

用法:  python run_cg.py cases/<name>.npz [out_dir] [n_steps 覆盖，冒烟测试用，如 2000]
输出:  <out_dir>/<name>.gsd（每 2000 步一帧）、<name>_run.log
"""
import sys, os, json
import numpy as np
import hoomd

spec = np.load(sys.argv[1], allow_pickle=False)
out_dir = sys.argv[2] if len(sys.argv) > 2 else "runs"
os.makedirs(out_dir, exist_ok=True)
meta = json.loads(str(spec["meta"]))
name = os.path.splitext(os.path.basename(sys.argv[1]))[0]
OUT = os.path.join(out_dir, name + ".gsd")
types = [str(t) for t in spec["types"]]
L = meta["L"]

snap = hoomd.Snapshot()
snap.configuration.box = [L, L, L, 0, 0, 0]
snap.particles.N = len(spec["position"])
snap.particles.types = types
snap.particles.position[:] = spec["position"]
snap.particles.typeid[:] = spec["typeid"]
snap.bonds.N = len(spec["bond_group"])
snap.bonds.types = meta["bond_types"]
snap.bonds.group[:] = spec["bond_group"]
snap.bonds.typeid[:] = spec["bond_typeid"]
snap.angles.N = len(spec["angle_group"])
snap.angles.types = meta["angle_types"]
snap.angles.group[:] = spec["angle_group"]
snap.angles.typeid[:] = spec["angle_typeid"]

sim = hoomd.Simulation(device=hoomd.device.CPU(), seed=int(meta["seed"]))
sim.create_state_from_snapshot(snap)

nl = hoomd.md.nlist.Cell(buffer=0.4)
lj = hoomd.md.pair.LJ(nlist=nl, default_r_cut=2.5)
SIG = meta["pair"]["sigma"]
for t1 in types:
    for t2 in types:
        s = 0.5 * (SIG[t1] + SIG[t2])
        lj.params[(t1, t2)] = dict(epsilon=1.0, sigma=s)
        lj.r_cut[(t1, t2)] = 2 ** (1 / 6) * s
for a, b, sig in meta["pair"].get("repulse", []):      # 单占位模式：加大 C–C 体积排除
    lj.params[(a, b)] = dict(epsilon=1.0, sigma=sig)
    lj.r_cut[(a, b)] = 2 ** (1 / 6) * sig
for a, b, eps, sig, rc in meta["pair"]["attract"]:
    lj.params[(a, b)] = dict(epsilon=eps, sigma=sig)
    lj.r_cut[(a, b)] = rc

bond_h = hoomd.md.bond.Harmonic()
for t, p in meta["bond_par"].items():
    bond_h.params[t] = dict(k=p["k"], r0=p["r0"])
angle_h = hoomd.md.angle.Harmonic()
for t, p in meta["angle_par"].items():
    angle_h.params[t] = dict(k=p["k"], t0=p["t0"])

R = dict(meta["run"])
if len(sys.argv) > 3:
    R["n_steps"] = int(sys.argv[3]); R["n_anneal"] = min(R["n_anneal"], R["n_steps"])
n_anneal = min(R["n_anneal"], R["n_steps"])
kT = hoomd.variant.Ramp(R["t_high"], R["t_low"], n_anneal // 2, n_anneal // 2)
langevin = hoomd.md.methods.Langevin(filter=hoomd.filter.All(), kT=kT)
sim.operations.integrator = hoomd.md.Integrator(dt=R["dt"], methods=[langevin], forces=[lj, bond_h, angle_h])

thermo = hoomd.md.compute.ThermodynamicQuantities(filter=hoomd.filter.All())
sim.operations.computes.append(thermo)
sim.operations.writers.append(hoomd.write.GSD(filename=OUT, trigger=hoomd.trigger.Periodic(2000),
                                              filter=hoomd.filter.All(), mode="wb"))
logger = hoomd.logging.Logger(categories=["scalar", "string"])
logger.add(sim, quantities=["timestep", "tps"])
logger.add(thermo, quantities=["potential_energy", "kinetic_temperature"])
sim.operations.writers.append(hoomd.write.Table(trigger=hoomd.trigger.Periodic(5000), logger=logger,
                                                output=open(OUT.replace(".gsd", "_run.log"), "w")))
print(f"{name}: {snap.particles.N} beads, L={L:.2f}, {R['n_steps']} 步", flush=True)
sim.run(R["n_steps"])
print("完成。势能:", thermo.potential_energy)
