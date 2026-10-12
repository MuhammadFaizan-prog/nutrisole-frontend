#!/bin/bash
# G5: wait for ripeness + cls kernels (sleep 1200 between polls), download; then CPU eval of the cls candidate. Idempotent.
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=${KAGGLE_API_TOKEN:-proxy-managed}
L=g5logs; R=/workspace/work/nutrisole/ml/runs/G5/kaggle; log(){ echo "$(date -u +%T) misc $*" >> $L/wait.log; }
for i in $(seq 1 40); do
  for k in nutrisole-g5-ripeness nutrisole-g5-cls; do [ -f $R/$k/DL_DONE ] && continue
    s=$(timeout 60 python3 kgl.py kernels status mfaizannnn/$k 2>&1 | grep -oE 'COMPLETE|ERROR|CANCEL[A-Z]*' | head -1)
    [ -n "$s" ] && { mkdir -p $R/$k; timeout 1500 python3 kgl.py kernels output mfaizannnn/$k -p $R/$k > $R/$k/dl.log 2>&1 && { echo $s > $R/$k/STATUS; touch $R/$k/DL_DONE; log "downloaded $k $s"; }; }
  done
  d=$R/nutrisole-g5-cls
  if [ -f $d/DL_DONE ] && [ ! -f $L/C_cls5_ALL ]; then m=$(find $d -name cls_g5_meta.json | head -1)
    sel=$(python3 -c "import json;print(json.load(open('$m')).get('selected',''))"); pt=$(find $d -path "*/$sel/weights/best.pt" | head -1)
    [ -n "$pt" ] && { log "cls eval $sel"; ./g5_cls_eval.sh cls5 $pt 224; } || { log "cls: no selected pt"; touch $L/C_cls5_ALL; }
  fi
  [ -f $R/nutrisole-g5-ripeness/DL_DONE ] && [ -f $L/C_cls5_ALL ] && break
  sleep 1200
done
