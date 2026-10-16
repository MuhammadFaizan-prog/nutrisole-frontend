#!/bin/bash
# G4 GPU queue + downloader. Pushes queued kernels when a Kaggle GPU slot frees (max 2), downloads finished outputs.
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate
export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=${KAGGLE_API_TOKEN:-proxy-managed}
L=g4logs; R=/workspace/work/nutrisole/ml/runs/G4/kaggle; mkdir -p $R
Q="det_v4:g4logs/V4_DS_READY cls:kaggle/g4/up_cls.DS_DONE ripe:none type:g4logs/TYPE_DS_READY"
ALL="nutrisole-g4-det-hyg-off nutrisole-g4-det-bg15 nutrisole-g4-owlv2 nutrisole-g4-det-v4 nutrisole-g4-cls nutrisole-g4-ripeness nutrisole-g4-type"
log(){ echo "$(date +%T) $*" >> $L/gpuq.log; }
for it in $(seq 1 400); do
  for q in $Q; do k=${q%%:*}; pre=${q#*:}; dir=kaggle/g4/k_${k/_/_}; [ $k = det_v4 ] && dir=kaggle/g4/k_det_v4; [ $k = ripe ] && dir=kaggle/g4/k_ripe; [ $k = type ] && dir=kaggle/g4/k_type
    [ -f $L/PUSHED_$k ] && continue
    [ "$pre" != none ] && [ ! -f "$pre" ] && continue
    out=$(cd $dir && timeout 100 kaggle kernels push -p . 2>&1 | tail -1)
    if echo "$out" | grep -q "successfully pushed"; then touch $L/PUSHED_$k; log "pushed $k"; else log "wait $k: ${out:0:80}"; fi
    break
  done
  for k in $ALL; do
    [ -f $R/$k/DL_DONE ] && continue
    s=$(timeout 40 kaggle kernels status mfaizannnn/$k 2>&1 | grep -oE 'COMPLETE|ERROR|CANCEL[A-Z]*' | head -1)
    if [ -n "$s" ]; then mkdir -p $R/$k; timeout 1500 kaggle kernels output mfaizannnn/$k -p $R/$k > $R/$k/dl.log 2>&1 && { echo $s > $R/$k/STATUS; touch $R/$k/DL_DONE; log "downloaded $k $s"; }; fi
  done
  [ -f $R/nutrisole-g4-type/DL_DONE ] && [ -f $R/nutrisole-g4-ripeness/DL_DONE ] && [ -f $R/nutrisole-g4-cls/DL_DONE ] && [ -f $R/nutrisole-g4-det-v4/DL_DONE ] && break
  sleep 90
done
log "gpuq exit"
