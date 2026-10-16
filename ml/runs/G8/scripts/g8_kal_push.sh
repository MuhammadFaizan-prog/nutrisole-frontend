#!/bin/bash
# G8: stage-1 + OWLv2 auto-label moved to ONE Kaggle kernel (mfaizannnn/nutrisole-g8-autolabel, free tier).
# Uploads kaggle/g8/up_kal as private dataset mfaizannnn/nutrisole-cv-g8-kal, waits until ready, pushes kaggle/g8/k_kal
# (GPU T4 if a free slot, else CPU; never paid). On push: touches STOP_AL/STOP_ALK so sandbox stage1/alk stop. Markers K_* in g8logs.
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=proxy-managed
L=g8logs; U=kaggle/g8/up_kal; K=kaggle/g8/k_kal; DS=mfaizannnn/nutrisole-cv-g8-kal; log(){ echo "- $(date -u +%TZ) [kal] $*" >> $L/progress.md; }
if [ ! -f $L/K_ds ]; then
  log "dataset upload start ($DS, $(du -sh $U | cut -f1), $(ls $U/*.webm | wc -l) clips)"
  timeout 5400 python3 kgl.py datasets create -p $U > $L/kal_ds.log 2>&1; rc=$?
  log "dataset create rc=$rc: $(tail -1 $L/kal_ds.log | cut -c1-160)"
  grep -qiE "success|created|ready|already" $L/kal_ds.log && touch $L/K_ds || exit 1
fi
for i in $(seq 1 40); do s=$(timeout 60 python3 kgl.py datasets status $DS 2>&1 | tail -1); echo "$s" | grep -qi ready && break; sleep 30; done
log "dataset status: $s"
if [ ! -f $L/K_push ]; then
  for i in 1 2 3 4 5 6; do
    if [ $i -le 3 ]; then sed -i 's/"enable_gpu": *false/"enable_gpu": true/' $K/kernel-metadata.json; out=$(timeout 100 python3 kgl.py kernels push -p $K --accelerator NvidiaTeslaT4 2>&1 | tail -2)
    else sed -i 's/"enable_gpu": *true/"enable_gpu": false/' $K/kernel-metadata.json; out=$(timeout 100 python3 kgl.py kernels push -p $K 2>&1 | tail -2); fi
    echo "$(date -u +%TZ) try$i $out" >> $L/kal_push.log
    echo "$out" | grep -qi "successfully pushed" && { touch $L/K_push $L/STOP_AL $L/STOP_ALK; log "kernel pushed try$i (gpu=$(grep -o '"enable_gpu": *[a-z]*' $K/kernel-metadata.json)): $(echo $out | cut -c1-160); STOP_AL+STOP_ALK touched"; break; }
    sleep 120
  done
  [ -f $L/K_push ] || { log "kernel push FAILED 6x: $(tail -1 $L/kal_push.log | cut -c1-200)"; exit 1; }
fi
