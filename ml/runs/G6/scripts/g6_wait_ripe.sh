#!/bin/bash
# G6: wait for Kaggle nutrisole-g5-ripeness (CPU kernel), download output once finished. Idempotent (marker RIPE_DL_DONE).
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate
export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=proxy-managed
O=/workspace/work/cv/g6models/ripe; mkdir -p $O; L=g6logs/ripe_wait.log
until [ -f $O/RIPE_DL_DONE ]; do
  [ -f g6logs/STOP_WAIT ] && exit 0
  s=$(timeout 60 python3 kgl.py kernels status mfaizannnn/nutrisole-g5-ripeness 2>&1 | grep -oE 'COMPLETE|ERROR|CANCEL[A-Z]*' | head -1)
  echo "$(date -u +%T) status=${s:-RUNNING}" >> $L
  if [ -n "$s" ]; then timeout 1500 python3 kgl.py kernels output mfaizannnn/nutrisole-g5-ripeness -p $O > $O/dl.log 2>&1 && { echo $s > $O/STATUS; touch $O/RIPE_DL_DONE; echo "$(date -u +%T) downloaded $s" >> $L; }; else sleep 900; fi
done
