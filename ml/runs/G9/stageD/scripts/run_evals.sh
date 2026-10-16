#!/bin/bash
# Usage: run_evals.sh ARM CACHE_DIR PROBE_CACHE_DIR
cd /workspace/work/nutrisole/ml/runs/G9/stageD/scripts; mkdir -p ../dev
for g in g1 none g05 g025 ssf50 ssf60; do
  [ -f ../dev/${1}_${g}.json ] && continue
  flock /workspace/work/cv/g7logs/cpu.lock /workspace/work/cvenv/bin/python stageD_eval.py $2 $g ../dev/${1}_${g}.json $3 >> /workspace/work/cv/g9d/eval.log 2>&1
done
echo "EVALDONE $1" >> /workspace/work/cv/g9d/eval.log
