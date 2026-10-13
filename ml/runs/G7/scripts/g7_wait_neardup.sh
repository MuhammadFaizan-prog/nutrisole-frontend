#!/bin/bash
# wait for the CPU near-dup helper kernel and download its output (idempotent)
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=proxy-managed
O=g7models/k_ripedup; mkdir -p $O
until [ -f g7logs/NEARDUP_DONE ]; do
  s=$(timeout 60 python3 kgl.py kernels status mfaizannnn/nutrisole-g7-ripe-neardup 2>&1 | grep -oE 'COMPLETE|ERROR|CANCEL' | head -1)
  if [ -n "$s" ]; then timeout 600 python3 kgl.py kernels output mfaizannnn/nutrisole-g7-ripe-neardup -p $O > $O/dl.log 2>&1 && echo $s > $O/STATUS && touch g7logs/NEARDUP_DONE; else sleep 60; fi
done
