#!/bin/bash
# G6.4 (budget-cut version, see G6_prereg.md deviation 03:35 PKT): DEV grid on the det clip only; TEST r1 for control + ByteTrack pick; r2 only if ByteTrack passes on r1.
cd /workspace/work/nutrisole; source /workspace/work/cvenv/bin/activate
L=/workspace/work/cv/g6logs; R=ml/runs/G6/tracking; mkdir -p $R
DET=/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx; CLS=/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx
exec 9>$L/cpu.lock
run(){ [ -f $L/T_$1 ] && return; flock 9
  python ml/eval/video_gauntlet.py --det $DET --det-kind raw --imgsz 480 --clips $2 --kinds $3 --cls $CLS --temp 0.25 --cls-imgsz 224 --no-realtime --max-same-class 0 \
    --tracker-kind $4 ${5:+--tracker "$5"} --out $R/$1 > $L/t_$1.log 2>&1 && touch $L/T_$1; echo "$(date -u +%T) T_$1 rc=$?" >> $L/track.log; flock -u 9; }
for b in 8 15 30; do run devdet_bt_b$b /workspace/work/cv/g3clips_dev det bytetrack "{\"track_buffer\":$b}"; done
python /workspace/work/cv/g6_track_pick.py > $L/bt_pick.json || exit 1
P=$(python -c "import json;print(json.dumps(json.load(open('$L/bt_pick.json'))['params']))")
run test_iou_r1 /workspace/work/cv/g1clips det,quality,neg iou
run test_bt_r1 /workspace/work/cv/g1clips det,quality,neg bytetrack "$P"
run negtest_iou_r1 /workspace/work/cv/g2clips_negtest neg iou
run negtest_bt_r1 /workspace/work/cv/g2clips_negtest neg bytetrack "$P"
touch $L/TRACK_R1_DONE
