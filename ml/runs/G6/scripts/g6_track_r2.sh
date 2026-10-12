#!/bin/bash
# G6.4 r2 replay for the ByteTrack pick (prereg: r2 only if ByteTrack passes the adoption rule on r1; it did at 23:12Z: det seg 0.667=0.667, FA 1.25/0.00 = control, static flicker 0=0, q_acc 0.929=0.929, rot_rec 0.875=0.875).
cd /workspace/work/nutrisole; source /workspace/work/cvenv/bin/activate
L=/workspace/work/cv/g6logs; R=ml/runs/G6/tracking
DET=/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx; CLS=/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx
P=$(python -c "import json;print(json.dumps(json.load(open('$L/bt_pick.json'))['params']))")
exec 9>$L/cpu.lock
run(){ [ -f $L/T_$1 ] && return; flock 9
  python ml/eval/video_gauntlet.py --det $DET --det-kind raw --imgsz 480 --clips $2 --kinds $3 --cls $CLS --temp 0.25 --cls-imgsz 224 --no-realtime --max-same-class 0 \
    --tracker-kind $4 ${5:+--tracker "$5"} --out $R/$1 > $L/t_$1.log 2>&1 && touch $L/T_$1; echo "$(date -u +%T) T_$1 rc=$?" >> $L/track.log; flock -u 9; }
run test_bt_r2 /workspace/work/cv/g1clips det,quality,neg bytetrack "$P"
run negtest_bt_r2 /workspace/work/cv/g2clips_negtest neg bytetrack "$P"
touch $L/TRACK_R2_DONE
