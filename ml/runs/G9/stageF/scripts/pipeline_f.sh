#!/bin/bash
# Idempotent Stage F eval pipeline per arm: DEV detections (val stills, DEV det/neg clips, SYNTHETIC probe) -> stageD_eval g1 + none (fixed
# post-processing; no other guard/floor is evaluated) -> M-DEV v2 detections + eval_f. Usage: pipeline_f.sh ARM:ONNX [...]
S=/workspace/work/nutrisole/ml/runs/G9/stageD/scripts; F=/workspace/work/nutrisole/ml/runs/G9/stageF; PY=/workspace/work/cvenv/bin/python; L=/workspace/work/cv/g9f/pipe.log; LK=/workspace/work/cv/g7logs/cpu.lock
for spec in "$@"; do
  A=${spec%%:*}; M=${spec#*:}; C=/workspace/work/cv/g9f/cache_$A; mkdir -p $C $F/dev
  for i in $(seq 1 80); do out=$(flock $LK $PY /workspace/work/nutrisole/ml/runs/G9/stageB/scripts/cache_dets_any.py $M $C 100 2>&1 | tail -1); echo "$(date +%T) $A dets $out" >> $L; case "$out" in *"ALL DONE"*) break;; esac; done
  for i in $(seq 1 80); do out=$(flock $LK $PY $S/cache_probe_any.py $C 100 $M 2>&1 | tail -1); echo "$(date +%T) $A probe $out" >> $L; case "$out" in *"ALL DONE"*) break;; esac; done
  for g in g1 none; do [ -f $F/dev/${A}_${g}.json ] || (cd $S && flock $LK $PY stageD_eval.py $C $g $F/dev/${A}_${g}.json $C >> $L 2>&1); done
  (cd /workspace/work/cv/g9f && flock $LK $PY /workspace/work/nutrisole/ml/runs/G9/stageE/scripts/cache_m.py mdev_ids.json dets_$A.json $M >> $L 2>&1 && $PY $F/scripts/eval_f.py dets_$A.json $F/m_labels_v2.json $F/out/mdev_$A.json >> $L 2>&1)
  echo "$(date +%T) PIPEDONE $A" >> $L
done
