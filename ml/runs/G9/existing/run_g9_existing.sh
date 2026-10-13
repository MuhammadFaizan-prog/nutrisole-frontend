#!/bin/bash
# G9 existing-models arm: G3 control vs snapml (veggies-and-fruits-balanced v1) vs calories (fruits-and-veg-2 v2), DEV only.
# Weights are cached outside the repo ($RF_WEIGHTS_DIR, default /workspace/work/cv/g9existing); no key or weights committed.
source /workspace/work/cvenv/bin/activate
cd /workspace/work/nutrisole
R=ml/runs/G9/existing; L=/workspace/work/cv/g9existing/logs; LK=/workspace/work/cv/g7logs/cpu.lock; P=/workspace/work/cv/g8logs/progress.md
mkdir -p $L $R/still $R/gauntlet_dev $R/vb8dev
log(){ echo "- $(date -u +%FT%TZ) [g9-existing] $*" >> $P; }
G3=/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx
log "chain start (pid $$)"
for m in g3 snapml calories; do
  [ -f $R/still/val_$m.json ] || { flock $LK python $R/still_val_map.py --model $m --out $R/still/val_$m.json > $L/still_$m.log 2>&1 && log "still val402 $m done" || log "still val402 $m FAILED (see $L/still_$m.log)"; }
done
# Synthetic DEV clips (g3clips_dev det + dev neg), fixed-frame stride 2 (7.5 fps processed) for ALL models, no classifier, guard as G8.
for m in g3 snapml calories; do
  if [ $m = g3 ]; then D=$G3; K=raw; S=480; else D=$m; K=roboflow; S=$([ $m = snapml ] && echo 416 || echo 640); fi
  for k in det neg; do  # split per clip kind so a sandbox restart loses at most one kind
    [ -f $R/gauntlet_dev/${m}_$k/gauntlet.json ] || { flock $LK python ml/eval/video_gauntlet.py --det $D --det-kind $K --imgsz $S --clips /workspace/work/cv/g3clips_dev --kinds $k --no-realtime --stride 2 --max-same-class 0 --out $R/gauntlet_dev/${m}_$k > $L/gaunt_${m}_$k.log 2>&1 && log "gauntlet dev $m $k done" || log "gauntlet dev $m $k FAILED (see $L/gaunt_${m}_$k.log)"; }
  done
done
for m in g3 snapml calories; do
  [ -f $R/vb8dev/vb8dev_$m.json ] || { flock $LK python $R/vb8dev_replay.py --model $m --out $R/vb8dev/vb8dev_$m.json > $L/vb8_$m.log 2>&1 && log "vb8 dev 2fps $m done" || log "vb8 dev 2fps $m FAILED (see $L/vb8_$m.log)"; }
done
log "chain end"
touch $L/CHAIN_DONE
