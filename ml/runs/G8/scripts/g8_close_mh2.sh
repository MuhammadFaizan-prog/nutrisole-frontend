#!/bin/bash
# G8 closeout: single final attempt at the last missing DEV tracker-grid config (watchdog gave up after 3 tries), then re-apply the
# unchanged addendum-C pick rule (same code as g8_tune.sh). Marker CL_MH2 in g8logs.
cd /workspace/work/nutrisole; source /workspace/work/cvenv/bin/activate
L=/workspace/work/cv/g8logs; R=ml/runs/G7/tracking/tune; n=nt0.35_mt0.9_mh2
log(){ echo "- $(date -u +%TZ) [close] $*" >> $L/progress.md; }
[ -f $L/CL_MH2 ] && exit 0
t=$(cat $L/cl_mh2_try 2>/dev/null || echo 0); [ $t -ge 2 ] && { log "tracker grid $n: gave up (killed twice by sandbox restarts); grid stays 7/8"; python /workspace/work/cv/g8_pick_rule.py > ml/runs/G8/tracking/pick_g7grid.json; touch $L/CL_MH2; exit 0; }; echo $((t+1)) > $L/cl_mh2_try
DET=/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx; CLS=/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx
log "tracker grid: final attempt $n (no cpu.lock wait, 1 thread; latency fields of this run are contaminated by a concurrent job and are not used)"
OMP_NUM_THREADS=1 nice -n 5 python ml/eval/video_gauntlet.py --det $DET --det-kind raw --imgsz 480 --clips /workspace/work/cv/g3clips_dev --kinds det,neg --cls $CLS --temp 0.25 --cls-imgsz 224 --no-realtime --max-same-class 0 --tracker-kind bytetrack --tracker "{\"track_buffer\": 15, \"new_track_thresh\": 0.35, \"match_thresh\": 0.9, \"minHits\": 2}" --out $R/$n > $L/tune_$n.log 2>&1
rc=$?; log "tracker grid $n rc=$rc"
[ -s $R/$n/gauntlet.json ] && touch $L/T_tune_$n
python /workspace/work/cv/g8_pick_rule.py > ml/runs/G8/tracking/pick_g7grid.json
log "tracker grid pick (addendum-C rule, $(python -c "import json;print(len(json.load(open('ml/runs/G8/tracking/pick_g7grid.json'))['rows']))")/8 configs): $(python -c "import json;print(json.load(open('ml/runs/G8/tracking/pick_g7grid.json'))['pick'])")"
touch $L/CL_MH2
