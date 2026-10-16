#!/bin/bash
# Stage E DEV continuity: G3 (D0 cache) x {g1, none, ssf50, ssf525, ssf55, ssf575, ssf60}
cd /workspace/work/nutrisole/ml/runs/G9/stageE/scripts
for g in g1 ssf50 ssf525 ssf55 ssf575 ssf60 none; do
  [ -f ../dev/G3_${g}.json ] && continue
  flock /workspace/work/cv/g7logs/cpu.lock /workspace/work/cvenv/bin/python stageE_eval.py /workspace/work/cv/g9fp $g ../dev/G3_${g}.json /workspace/work/cv/g9c/probe >> /workspace/work/cv/g9e/dev.log 2>&1
done
echo DEVDONE >> /workspace/work/cv/g9e/dev.log
