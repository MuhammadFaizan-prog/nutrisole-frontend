#!/bin/bash
# usage: g6_wait_k.sh KERNEL TAG : wait for a G6 Kaggle detector kernel (poll 600 s), download, then (serialised by flock) CPU eval + fixed-frame gauntlet r1/r2. Idempotent.
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate
export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=proxy-managed
k=$1; tag=$2; L=g6logs; R=/workspace/work/nutrisole/ml/runs/G6/kaggle; C3=/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx
log(){ echo "$(date -u +%T) $k $*" >> $L/wait.log; }
until [ -f $R/$k/DL_DONE ]; do
  [ -f $L/STOP_WAIT ] && exit 0
  s=$(timeout 60 python3 kgl.py kernels status mfaizannnn/$k 2>&1 | grep -oE 'COMPLETE|ERROR|CANCEL[A-Z]*' | head -1)
  if [ -n "$s" ]; then mkdir -p $R/$k; timeout 1500 python3 kgl.py kernels output mfaizannnn/$k -p $R/$k > $R/$k/dl.log 2>&1 && { echo $s > $R/$k/STATUS; touch $R/$k/DL_DONE; log "downloaded $s"; }; else sleep 600; fi
done
pt=$(find $R/$k -name best.pt | head -1); [ -z "$pt" ] && { log "no best.pt"; exit 1; }
exec 9>$L/cpu.lock; flock 9
log "eval"; ./g6_eval_det.sh $tag $pt 480; onnx=$(ls /workspace/work/cv/g6models/$tag/*raw*.onnx | head -1)
log "gaunt"; ./g6_gaunt.sh ${tag}_r1 $onnx raw 480 $C3 0.25 224 --max-same-class 0; ./g6_gaunt.sh ${tag}_r2 $onnx raw 480 $C3 0.25 224 --max-same-class 0
touch $L/K_${tag}_DONE; log "done"
