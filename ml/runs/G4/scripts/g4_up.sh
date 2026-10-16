#!/bin/bash
# (re)start every G4 background worker that is not running (workers die when the sandbox session is reset)
cd /workspace/work/cv
for s in g4_gpuq2.sh g4_orch.sh g4_q3.sh g4_a1r2.sh g4_cls4r2.sh g4_q4.sh; do
  [ -f g4logs/NO_$s ] && continue
  ps -eo args | grep -v grep | grep -q "bash ./$s" || { setsid nohup ./$s >> g4logs/${s%.sh}.out 2>&1 < /dev/null & echo "started $s"; }
done
