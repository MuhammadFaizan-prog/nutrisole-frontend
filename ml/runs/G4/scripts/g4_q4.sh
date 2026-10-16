#!/bin/bash
# downloader for the CPU fallback kernels (ripeness-cpu, type-cpu)
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate
export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=${KAGGLE_API_TOKEN:-proxy-managed}
R=/workspace/work/nutrisole/ml/runs/G4/kaggle
while true; do
  n=0
  for k in nutrisole-g4-ripeness-cpu nutrisole-g4-type-cpu; do
    [ -f $R/$k/DL_DONE ] && { n=$((n+1)); continue; }
    s=$(timeout 40 kaggle kernels status mfaizannnn/$k 2>&1 | grep -oE 'COMPLETE|ERROR|CANCEL[A-Z]*' | head -1)
    if [ -n "$s" ]; then mkdir -p $R/$k; timeout 1500 kaggle kernels output mfaizannnn/$k -p $R/$k > $R/$k/dl.log 2>&1 && { echo $s > $R/$k/STATUS; touch $R/$k/DL_DONE; echo "$(date +%T) q4 downloaded $k $s" >> g4logs/orch.log; }; fi
  done
  [ $n = 2 ] && { touch g4logs/NO_g4_q4.sh; break; }
  sleep 120
done
