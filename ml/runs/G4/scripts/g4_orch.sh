#!/bin/bash
# G4 post-processing orchestrator: as Kaggle outputs land, run CPU evals + fixed-frame gauntlets (sequential). Idempotent.
cd /workspace/work/cv; L=g4logs; K=/workspace/work/nutrisole/ml/runs/G4/kaggle
D3=/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx; C3=/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx
log(){ echo "$(date +%T) $*" >> $L/orch.log; }
for it in $(seq 1 200); do
  for pair in hyg-off:A1hyg bg15:A2bg15 v4:det4; do k=${pair%%:*}; tag=${pair#*:}; d=$K/nutrisole-g4-det-$k
    [ -f $d/DL_DONE ] || continue; [ -f $L/G_${tag}_r1 ] && continue
    pt=$(find $d -name best.pt | head -1); [ -z "$pt" ] && { [ -f $L/NOPT_$tag ] || { log "no best.pt $tag"; touch $L/NOPT_$tag; }; continue; }
    log "eval $tag"; ./g4_eval_det.sh $tag $pt 480; onnx=$(ls /workspace/work/cv/g4models/$tag/*raw*.onnx | head -1)
    log "gaunt $tag r1"; ./g4_gaunt.sh ${tag}_r1 $onnx raw 480 $C3 0.25 224 --max-same-class 0
    [ $tag = det4 ] && { log "gaunt $tag r2"; ./g4_gaunt.sh ${tag}_r2 $onnx raw 480 $C3 0.25 224 --max-same-class 0; }
    log "done $tag"
  done
  d=$K/nutrisole-g4-cls
  if [ -f $d/DL_DONE ] && [ ! -f $L/G_cls4_r1 ]; then
    sel=$(python3 -c "import json;print(json.load(open('$(find $d -name cls_g4_meta.json|head -1)')).get('selected',''))")
    pt=$(find $d -path "*/$sel/weights/best.pt" | head -1)
    if [ -n "$pt" ]; then sz=$(python3 -c "import json;print(json.load(open('$(find $d -name cls_g4_meta.json|head -1)'))['runs']['$sel']['imgsz'])")
      log "cls eval $sel $sz"; ./g4_cls_eval.sh cls4 $pt $sz; T=$(python3 -c "import json;print(json.load(open('/workspace/work/nutrisole/ml/runs/G4/eval_cls_cls4/eval_cls.json'))['temperature'])")
      onnx=$(ls /workspace/work/cv/g4models/cls_cls4/*.onnx | head -1)
      log "gaunt cls4"; ./g4_gaunt.sh cls4_r1 $D3 raw 480 $onnx $T $sz --max-same-class 0; ./g4_gaunt.sh cls4_r2 $D3 raw 480 $onnx $T $sz --max-same-class 0
      log "done cls4"
    else [ -f $L/NOPT_cls ] || { log "cls no selected pt ($sel)"; touch $L/NOPT_cls; }; fi
  fi
  [ -f $L/G_det4_r2 ] && [ -f $L/G_cls4_r2 ] && [ -f $L/G_A1hyg_r1 ] && [ -f $L/G_A2bg15_r1 ] && break
  [ -f $L/ORCH_STOP ] && break
  sleep 120
done
log "orch exit"
