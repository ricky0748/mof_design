#!/bin/bash
cd /share/rickyswork/ai_mof/generation/pilots/MOFFlow-2/assets_dl
B=https://huggingface.co/nayoung10/mofflow2-ckpt/resolve/main
D=https://huggingface.co/datasets/nayoung10/mofflow2-data/resolve/main
for f in csp/sp_module_ckpt.tar.gz csp/config.yaml \
         gen/seq_module_conditional/seq_module_conditional_ckpt.tar.gz \
         gen/seq_module_conditional/config.yaml \
         gen/seq_module_unconditional/seq_module_unconditional_ckpt.tar.gz \
         gen/seq_module_unconditional/config.yaml \
         gen/sp_module/sp_module_ckpt.tar.gz gen/sp_module/config.yaml; do
  mkdir -p "ckpt/$(dirname $f)"
  wget -c -q "$B/$f" -O "ckpt/$f"
done
for f in lmdb/csp/train.tar.gz lmdb/csp/val.tar.gz lmdb/csp/test.tar.gz \
         lmdb/gen/train.tar.gz lmdb/gen/val.tar.gz \
         metals/metal_lib_train.pkl seqs/seqs_data.tar.gz seqs/vocab.json splits.tar.gz; do
  mkdir -p "data/$(dirname $f)"
  wget -c -q "$D/$f" -O "data/$f"
done
echo DONE > hf_dl.done
