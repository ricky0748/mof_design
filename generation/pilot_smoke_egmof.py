#!/usr/bin/env python3
"""EGMOF 10 样本 smoke test：下载检查点（如缺失）并生成带 CIF 的样本。"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CK = ROOT / "checkpoints"


def ensure():
    from egmof import download_desc2mof, download_mof2desc, download_prop2desc
    if not (CK / "desc2mof" / "desc2mof_best.ckpt").exists():
        print("[dl] desc2mof", flush=True)
        download_desc2mof()
    if not (CK / "mof2desc" / "mof2desc_best.ckpt").exists():
        print("[dl] mof2desc", flush=True)
        download_mof2desc()
    for p in [CK / "desc2mof" / "desc2mof_best.ckpt",
              CK / "mof2desc" / "mof2desc_best.ckpt",
              CK / "prop2desc_best.ckpt"]:
        assert p.exists(), p
        print("[ok]", p, round(p.stat().st_size / 1e6, 1), "MB", flush=True)


def main():
    ensure()
    from egmof import EGMOF
    out = ROOT / "smoke"
    out.mkdir(exist_ok=True)
    accelerator = "cuda" if os.environ.get("EGMOF_ACCEL") == "cuda" else "cpu"
    print("[init] accelerator", accelerator, flush=True)
    eg = EGMOF(
        prop2desc_ckpt_path=str(CK / "prop2desc_best.ckpt"),
        prop2desc_config_path=str(CK / "prop2desc_ckpt" / "various_dataset" / "wilmer_CO2_uptake_2.5bar" / "hparams.yaml"),
        accelerator=accelerator,
        devices=1,
    )
    df = eg.generate(
        num_samples=10,
        target_value=5.0,
        build_cif=True,
        cif_dir=str(out / "cif"),
        new_bb_dir=str(out / "bbs"),
    )
    df.to_csv(out / "samples.csv", index=False)
    print(df.to_string())
    print("saved", out / "samples.csv")


if __name__ == "__main__":
    main()
