import os
from pathlib import Path
from egmof import EGMOF

ROOT = Path(__file__).resolve().parent
CK = ROOT / "checkpoints"
N = int(os.environ.get("EGMOF_N", "1000"))
out = ROOT / os.environ.get("EGMOF_OUT", "scale1000")
out.mkdir(exist_ok=True)
acc = "cuda" if os.environ.get("EGMOF_ACCEL") == "cuda" else "cpu"
print("[init]", acc, N, out, flush=True)
eg = EGMOF(prop2desc_ckpt_path=str(CK / "prop2desc_best.ckpt"),
           prop2desc_config_path=str(CK / "prop2desc_ckpt/various_dataset/wilmer_CO2_uptake_2.5bar/hparams.yaml"),
           accelerator=acc, devices=1)
df = eg.generate(num_samples=N, target_value=5.0, build_cif=True,
                 cif_dir=str(out / "cif"), new_bb_dir=str(out / "bbs"))
df.to_csv(out / "samples.csv", index=False)
print(df.to_string())
print("saved", out / "samples.csv")
