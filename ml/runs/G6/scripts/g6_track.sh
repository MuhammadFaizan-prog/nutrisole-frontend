#!/bin/bash
# G6.4 tracking experiment on the G3 control (det G3 640->480 raw, cls G3 E224 T=0.25, guard rule 2 off). Idempotent markers g6logs/T_*.
# DEV (g3clips_dev + g3clips_devneg): IouTracker baseline + ByteTrack grid on track_buffer; pick on DEV; then TEST (g1clips + g2clips_negtest) r1/r2.
cd /workspace/work/nutrisole; source /workspace/work/cvenv/bin/activate
L=/workspace/work/cv/g6logs; R=ml/runs/G6/tracking; mkdir -p $R
DET=/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx; CLS=/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx
exec 9>$L/cpu.lock
run(){ # TAG CLIPS KINDS TRACKERKIND TRACKERJSON
  [ -f $L/T_$1 ] && return; flock 9
  python ml/eval/video_gauntlet.py --det $DET --det-kind raw --imgsz 480 --clips $2 --kinds $3 --cls $CLS --temp 0.25 --cls-imgsz 224 --no-realtime --max-same-class 0 \
    --tracker-kind $4 ${5:+--tracker "$5"} --out $R/$1 > $L/t_$1.log 2>&1 && touch $L/T_$1; flock -u 9; echo "$(date -u +%T) T_$1 rc=$?" >> $L/track.log; }
run dev_iou /workspace/work/cv/g3clips_dev det,quality,neg iou
run devneg_iou /workspace/work/cv/g3clips_devneg neg iou
for b in 8 15 30; do
  run dev_bt_b$b /workspace/work/cv/g3clips_dev det,quality,neg bytetrack "{\"track_buffer\":$b}"
  run devneg_bt_b$b /workspace/work/cv/g3clips_devneg neg bytetrack "{\"track_buffer\":$b}"
done
# TEST: control replay + ByteTrack with the DEV pick (written by g6_track_pick.py into $L/bt_pick.json)
run test_iou_r1 /workspace/work/cv/g1clips det,quality,neg iou
run negtest_iou_r1 /workspace/work/cv/g2clips_negtest neg iou
python /workspace/work/cv/g6_track_pick.py > $L/bt_pick.json || exit 1
P=$(python -c "import json;print(json.dumps(json.load(open('$L/bt_pick.json'))['params']))")
for r in r1 r2; do
  run test_bt_$r /workspace/work/cv/g1clips det,quality,neg bytetrack "$P"
  run negtest_bt_$r /workspace/work/cv/g2clips_negtest neg bytetrack "$P"
done
touch $L/TRACK_ALL_DONE
