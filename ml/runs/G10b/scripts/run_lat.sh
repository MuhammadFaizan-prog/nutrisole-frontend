#!/bin/bash
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole/ml/runs/G10b/scripts
echo "g10b-lat $$ $(date)" > /workspace/work/cv/g7logs/cpu.lock
for c in G3 v8m G3+v8m; do python g10b_latmem.py $c 40 /workspace/work/cv/g10b/runs/latmem_${c/+/_}.json >> /workspace/work/cv/g10b/logs/lat.log 2>&1; done
uptime >> /workspace/work/cv/g10b/logs/lat.log
rm -f /workspace/work/cv/g7logs/cpu.lock; touch /workspace/work/cv/g10b/logs/DONE_lat
