#!/bin/bash
# Idempotent: cache DEV detections (val stills, DEV det/neg clips, SYNTHETIC probe) for each arm, then run the guard evals.
# Usage: pipeline.sh ARM:ONNX [ARM:ONNX ...]   (safe to relaunch after a sandbox restart)
S=/workspace/work/nutrisole/ml/runs/G9/stageD/scripts; PY=/workspace/work/cvenv/bin/python; L=/workspace/work/cv/g9d/pipe.log
for spec in "$@"; do
  A=${spec%%:*}; M=${spec#*:}; C=/workspace/work/cv/g9d/cache_$A; mkdir -p $C
  for i in $(seq 1 80); do out=$(flock /workspace/work/cv/g7logs/cpu.lock $PY /workspace/work/nutrisole/ml/runs/G9/stageB/scripts/cache_dets_any.py $M $C 100 2>&1 | tail -1); echo "$(date +%T) $A dets $out" >> $L; case "$out" in *"ALL DONE"*) break;; esac; done
  for i in $(seq 1 80); do out=$(flock /workspace/work/cv/g7logs/cpu.lock $PY $S/cache_probe_any.py $C 100 $M 2>&1 | tail -1); echo "$(date +%T) $A probe $out" >> $L; case "$out" in *"ALL DONE"*) break;; esac; done
  $S/run_evals.sh $A $C $C
  echo "$(date +%T) PIPEDONE $A" >> $L
done
