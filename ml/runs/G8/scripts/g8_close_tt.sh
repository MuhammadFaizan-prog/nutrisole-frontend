#!/bin/bash
# G8 closeout: the one TEST gauntlet run of the DEV tracker pick (g8_tune.sh intended it; log empty after restarts). Single attempt per marker.
cd /workspace/work/nutrisole; source /workspace/work/cvenv/bin/activate; L=/workspace/work/cv/g8logs; LK=/workspace/work/cv/g7logs/cpu.lock
[ -f $L/T_test_tuned_r1 ] && exit 0
t=$(cat $L/cl_tt_try 2>/dev/null || echo 0); [ $t -ge 2 ] && { echo "- $(date -u +%TZ) [close] tracker pick TEST run: gave up after 2 attempts" >> $L/progress.md; touch $L/T_test_tuned_r1; exit 0; }; echo $((t+1)) > $L/cl_tt_try
DET=/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx; CLS=/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx
P='{"track_buffer": 15, "new_track_thresh": 0.25, "match_thresh": 0.8, "minHits": 1}'
flock $LK python ml/eval/video_gauntlet.py --det $DET --det-kind raw --imgsz 480 --clips /workspace/work/cv/g1clips --kinds det,quality,neg --cls $CLS --temp 0.25 --cls-imgsz 224 --no-realtime --max-same-class 0 --tracker-kind bytetrack --tracker "$P" --out ml/runs/G8/tracking/test_tuned_r1 > $L/t_test_tuned_r1.log 2>&1 && touch $L/T_test_tuned_r1 && echo "- $(date -u +%TZ) [close] tracker pick TEST gauntlet (g1clips) done" >> $L/progress.md
