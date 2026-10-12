#!/bin/bash
# G4 extra: det-v4 + hygiene-off combo kernel (test-informed, added after A1). Push with priority, download, eval, gauntlet r1/r2.
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate
export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=${KAGGLE_API_TOKEN:-proxy-managed}
L=g4logs; R=/workspace/work/nutrisole/ml/runs/G4/kaggle; k=nutrisole-g4-det-v4hyg; tag=det4h
C3=/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx
log(){ echo "$(date +%T) q3 $*" >> $L/orch.log; }
until [ -f $L/PUSHED_v4hyg ]; do
  out=$(cd kaggle/g4/k_det_v4hyg && timeout 100 kaggle kernels push -p . 2>&1 | tail -1)
  echo "$out" | grep -q "successfully pushed" && { touch $L/PUSHED_v4hyg; log "pushed v4hyg"; } || sleep 30
done
until [ -f $R/$k/DL_DONE ]; do
  sleep 120; s=$(timeout 40 kaggle kernels status mfaizannnn/$k 2>&1 | grep -oE 'COMPLETE|ERROR|CANCEL[A-Z]*' | head -1)
  if [ -n "$s" ]; then mkdir -p $R/$k; timeout 1500 kaggle kernels output mfaizannnn/$k -p $R/$k > $R/$k/dl.log 2>&1 && { echo $s > $R/$k/STATUS; touch $R/$k/DL_DONE; log "downloaded $k $s"; }; fi
done
pt=$(find $R/$k -name best.pt | head -1); [ -z "$pt" ] && { log "no best.pt $tag"; exit 1; }
# wait for the main orchestrator to be idle on CPU-heavy work is not needed (fixed-frame mode is deterministic)
log "eval $tag"; ./g4_eval_det.sh $tag $pt 480; onnx=$(ls /workspace/work/cv/g4models/$tag/*raw*.onnx | head -1)
log "gaunt $tag"; ./g4_gaunt.sh ${tag}_r1 $onnx raw 480 $C3 0.25 224 --max-same-class 0; ./g4_gaunt.sh ${tag}_r2 $onnx raw 480 $C3 0.25 224 --max-same-class 0
log "done $tag"
