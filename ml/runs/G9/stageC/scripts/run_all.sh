#!/bin/bash
cd /workspace/work/nutrisole/ml/runs/G9/stageC/scripts; mkdir -p ../dev
while ! grep -q "ALL DONE" /workspace/work/cv/g9c/cache.log; do sleep 10; done
for trk in iou0.3 iou0.2 ctr; do for maf in 0.01 0.005 0.0025 0.0; do
  [ -f ../dev/arm_${maf}_${trk}.json ] && continue
  flock /workspace/work/cv/g7logs/cpu.lock /workspace/work/cvenv/bin/python stagec_eval.py $maf $trk ../dev/arm_${maf}_${trk}.json >> /workspace/work/cv/g9c/eval.log 2>&1
done; done
flock /workspace/work/cv/g7logs/cpu.lock /workspace/work/cvenv/bin/python raw_vs_guard.py /workspace/work/cv/g9fp ../out/raw_vs_guard_dev.json /workspace/work/cv/g9c/probe > /workspace/work/cv/g9c/rawvs.log 2>&1
echo ALLEVAL >> /workspace/work/cv/g9c/eval.log
