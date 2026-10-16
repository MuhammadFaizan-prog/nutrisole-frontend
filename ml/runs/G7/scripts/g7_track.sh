#!/bin/bash
# G7 (GPT review items 2-3): re-run TEST IouTracker vs ByteTrack b15 with missed-duration/fragmentation metrics; BoT-SORT on DEV once,
# TEST only if it passes the addendum-A gate. Idempotent markers g7logs/T_*; serialised with cpu.lock per run.
cd /workspace/work/nutrisole; source /workspace/work/cvenv/bin/activate
L=/workspace/work/cv/g7logs; R=ml/runs/G7/tracking; mkdir -p $R
DET=/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx; CLS=/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx
P=$(python -c "import json;print(json.dumps(json.load(open('/workspace/work/cv/g6logs/bt_pick.json'))['params']))")
run(){ [ -f $L/T_$1 ] && return; flock $L/cpu.lock python ml/eval/video_gauntlet.py --det $DET --det-kind raw --imgsz 480 --clips $2 --kinds $3 --cls $CLS --temp 0.25 --cls-imgsz 224 --no-realtime --max-same-class 0 \
    --tracker-kind $4 ${5:+--tracker "$5"} --out $R/$1 > $L/t_$1.log 2>&1 && touch $L/T_$1; echo "- $(date -u +%TZ) [track] $1 rc=$?" >> $L/progress.md; }
run devdet_botsort /workspace/work/cv/g3clips_dev det botsort "$P"
run test_iou_r1 /workspace/work/cv/g1clips det,quality,neg iou
run test_bt_r1 /workspace/work/cv/g1clips det,quality,neg bytetrack "$P"
run negtest_iou_r1 /workspace/work/cv/g2clips_negtest neg iou
run negtest_bt_r1 /workspace/work/cv/g2clips_negtest neg bytetrack "$P"
ok=$(python -c "import json;d=json.load(open('$R/devdet_botsort/gauntlet.json'))['clips']['det'];print(d['segment_acc']>=0.625 and d['label_flicker_per_10s_static']<=0.625)" 2>/dev/null)
echo "- $(date -u +%TZ) [track] botsort DEV gate pass=$ok" >> $L/progress.md
if [ "$ok" = "True" ]; then run test_botsort_r1 /workspace/work/cv/g1clips det,quality,neg botsort "$P"; run negtest_botsort_r1 /workspace/work/cv/g2clips_negtest neg botsort "$P"; fi
touch $L/TRACK7_DONE
