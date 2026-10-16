#!/bin/bash
for i in $(seq 1 40); do
  out=$(flock /workspace/work/cv/g7logs/cpu.lock /workspace/work/cvenv/bin/python /workspace/work/nutrisole/ml/runs/G9/stageC/scripts/cache_probe.py /workspace/work/cv/g9c/probe 90)
  echo "$(date +%T) $out" >> /workspace/work/cv/g9c/cache.log
  case "$out" in *"ALL DONE"*) break;; esac
done
