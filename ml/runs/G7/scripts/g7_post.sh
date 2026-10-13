#!/bin/bash
# G7 post-training orchestrator (idempotent, crash-safe). For each detector arm as its Kaggle output lands:
# copy metrics/args/results to ml/runs/G7/kaggle/<slug>/ (weights stay out of git), CPU eval under cpu.lock,
# tables, then gauntlet r1/r2 only through g7_gaunt.sh's strict-image gate. Ripeness: copy report + fixture.
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate
L=g7logs; R=/workspace/work/nutrisole/ml/runs/G7; G3CLS=/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx
log(){ echo "- $(date -u +%TZ) [post] $*" >> $L/progress.md; }
while true; do
  [ -f $L/STOP_POST ] && exit 0
  pending=0
  for a in sB sA rfs; do
    [ -f $L/P_${a}_ALL ] && continue
    pending=1; [ -f $L/K_${a}_DONE ] || continue
    slug=nutrisole-g7-det-$(echo $a | tr A-Z a-z); K=g7models/k_$a; D=$R/kaggle/$slug; mkdir -p $D
    PT=$(ls $K/runs/det_yolo11n_g7_${a}/weights/best.pt 2>/dev/null)
    if [ ! -f $L/P_${a}_copy ]; then
      cp $K/STATUS $D/ 2>/dev/null; cp $K/*_metrics.json $D/ 2>/dev/null; mkdir -p $D/runs; cp $K/runs/det_yolo11n_g7_${a}/{args.yaml,results.csv} $D/runs/ 2>/dev/null
      cp $K/*.log $D/kernel.log 2>/dev/null; touch $L/P_${a}_copy; log "$a kaggle output copied (status $(cat $K/STATUS), best.pt ${PT:-MISSING})"
    fi
    if [ -z "$PT" ]; then log "$a has no best.pt -> no eval"; touch $L/P_${a}_ALL; continue; fi
    if [ ! -f $L/E_G7${a}_ALL ]; then flock $L/cpu.lock bash g7_eval_det.sh G7$a $PT 480; [ -f $L/E_G7${a}_ALL ] && { python g7_tables.py > /dev/null 2>&1; log "$a CPU eval done: $(python -c "import json;s=json.load(open('$R/tables.json'))['strict'];print({k[-8:]:(v['pooled'],v['image_pass'],v['per_class_fails']) for k,v in s.items() if 'G7$a]' in k})")"; }; fi
    ONNX=$(cat $L/onnx_G7$a.txt 2>/dev/null | cut -d= -f2)
    if [ -f $L/E_G7${a}_ALL ] && [ -n "$ONNX" ]; then
      for r in r1 r2; do flock $L/cpu.lock bash g7_gaunt.sh G7${a}_$r $ONNX raw 480 $G3CLS 0.25 224 --max-same-class 0; done
      python g7_tables.py > /dev/null 2>&1; touch $L/P_${a}_ALL; log "$a post done (gauntlet ran: $(ls $L/G_G7${a}_r* 2>/dev/null | wc -l) runs; skips: $(grep -c G7${a} $L/gaunt_skip.log 2>/dev/null))"
    fi
  done
  if [ -f $L/K_ripe_DONE ] && [ ! -f $L/P_ripe_ALL ]; then
    mkdir -p $R/ripeness; cp g7models/k_ripe/ripeness_g7*.json g7models/k_ripe/STATUS $R/ripeness/ 2>/dev/null; cp g7models/k_ripe/*.log $R/ripeness/kernel.log 2>/dev/null
    touch $L/P_ripe_ALL; log "ripeness output copied (status $(cat g7models/k_ripe/STATUS))"
  else [ -f $L/P_ripe_ALL ] || pending=1; fi
  [ $pending = 0 ] && { log "all post work done"; exit 0; }
  sleep 120
done
