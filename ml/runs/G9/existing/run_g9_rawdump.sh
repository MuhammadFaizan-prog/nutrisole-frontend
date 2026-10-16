#!/bin/bash
# G9 addendum: raw-detection dumps (same harness path, same frames: stride 2) for runs that started before the dump hook existed.
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole
R=ml/runs/G9/existing; L=/workspace/work/cv/g9existing/logs; LK=/workspace/work/cv/g7logs/cpu.lock; P=/workspace/work/cv/g8logs/progress.md
log(){ echo "- $(date -u +%FT%TZ) [g9-existing] $*" >> $P; }
G3=/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx
for m in g3 snapml; do
  if [ $m = g3 ]; then D=$G3; K=raw; S=480; else D=$m; K=roboflow; S=416; fi
  for k in det neg; do
    [ -f $R/gauntlet_dev/${m}_$k/raw_dets_$k.json.gz ] && continue
    [ -f $R/gauntlet_dev/raw_${m}_$k/raw_dets_$k.json.gz ] || { G9_RAW_DUMP=1 flock $LK python ml/eval/video_gauntlet.py --det $D --det-kind $K --imgsz $S --clips /workspace/work/cv/g3clips_dev --kinds $k --no-realtime --stride 2 --max-same-class 0 --out $R/gauntlet_dev/raw_${m}_$k > $L/raw_${m}_$k.log 2>&1 && log "raw dump $m $k done" || log "raw dump $m $k FAILED"; }
  done
done
touch $L/RAW_DONE
