#!/bin/bash
# G8 showcase: poll Kaggle kernel mfaizannnn/nutrisole-g8-showcase, download outputs, run the pre-registered evaluation (Addendum 2026-10-13 S3)
# on sandbox CPU, decide, commit + sync to cv-gauntlet. Idempotent: markers SH_* in g8logs/. Started by g8_relaunch.sh.
L=/workspace/work/cv/g8logs; W=/workspace/work/cv/g8show; REPO=/workspace/work/nutrisole; R=$REPO/ml/runs/G8/showcase; LK=/workspace/work/cv/g7logs/cpu.lock
log(){ echo "- $(date -u +%TZ) [showcase] $*" >> $L/progress.md; }
source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=proxy-managed
mkdir -p $W/out $W/boot $R
KS=mfaizannnn/nutrisole-g8-showcase
while [ ! -f $L/SH_KDONE ]; do
  st=$(cd $W && timeout 100 python3 /workspace/work/cv/kgl.py kernels status $KS 2>&1 | tail -1)
  echo "$(date -u +%TZ) $st" >> $W/status.log
  case "$st" in
    *COMPLETE*) (cd $W && timeout 600 python3 /workspace/work/cv/kgl.py kernels output $KS -p $W/out > $W/dl.log 2>&1) && [ -f $W/out/show_metrics.json ] && { touch $L/SH_KDONE; log "kernel COMPLETE, outputs in $W/out"; } ;;
    *ERROR*|*CANCEL*) (cd $W && timeout 600 python3 /workspace/work/cv/kgl.py kernels output $KS -p $W/out > $W/dl.log 2>&1); log "kernel FAILED: $st (log in $W/out)"; touch $L/SH_KFAIL; exit 1 ;;
  esac
  [ -f $L/SH_KDONE ] || sleep 180
done
cd $REPO
if [ ! -f $L/SH_COPY ]; then
  mkdir -p $R/kaggle; cp $W/out/show_metrics.json $R/kaggle/; cp $W/out/*.log $R/kaggle/ 2>/dev/null
  for s in 0 1; do cp $W/out/show5_s${s}_12row.pt $W/ 2>/dev/null; cp $W/out/show5_s${s}_12row_raw.onnx $W/ 2>/dev/null; cp $W/out/runs/show5_s${s}/results.csv $R/kaggle/results_s${s}.csv 2>/dev/null; done
  touch $L/SH_COPY; log "copied kaggle metrics: $(python3 -c "import json;d=json.load(open('$R/kaggle/show_metrics.json'));print({k:(v.get('val480',{}).get('mAP50'),v.get('train_wall_s')) for k,v in d['runs'].items()}, 'init', d['init_sliced_val480']['mAP50'])")"
fi
# ONNX for seeds if the kernel export failed
for s in 0 1; do [ -f $W/show5_s${s}_12row_raw.onnx ] || python $W/exp.py $W/show5_s${s}_12row.pt $W/show5_s${s}_12row_raw.onnx >> $W/exp.log 2>&1; done
[ -f $W/G3r5_12row_raw.onnx ] || python $W/exp.py $W/G3r5_12row.pt $W/G3r5_12row_raw.onnx >> $W/exp.log 2>&1
Y=/workspace/work/cv/g3data/det_v3/det_v3_pooled.yaml
for s in 0 1; do
  [ -f $L/SH_P$s ] || { flock $LK nice -n 5 python ml/eval/eval_det.py --model $W/show5_s${s}_12row.pt --data $Y --imgsz 480 --splits pooled --out $R/eval_pooled_show_s$s > $W/pooled_s$s.log 2>&1 && touch $L/SH_P$s && log "pooled eval s$s done"; }
done
python $W/decide.py > $W/decide1.log 2>&1; log "per-class gate (pooled only so far): $(python3 -c "import json;d=json.load(open('$R/decision.json'));print({k:(v and v['n_pass']) for k,v in d['seeds'].items()}, {c:(r['g3'],r['cand']) for c,r in d['seeds']['show_s0']['per_class'].items()})" 2>&1)"
DET3=/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx; CLS=/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx
for spec in "G3 $DET3" "G3r5 $W/G3r5_12row_raw.onnx" "show_s0 $W/show5_s0_12row_raw.onnx"; do set -- $spec
  [ -f $L/SH_V_$1 ] || { flock $LK python ml/eval/video_gauntlet.py --det $2 --det-kind raw --imgsz 480 --clips /workspace/work/cv/g3clips_dev --kinds det,neg --cls $CLS --temp 0.25 --cls-imgsz 224 --no-realtime --max-same-class 0 --out $R/video_dev_$1 > $W/v_$1.log 2>&1 && touch $L/SH_V_$1 && log "dev video $1 done"; }
done
[ -f $L/SH_LAT ] || { flock $LK python $W/lat.py $R/latency.json G3=$DET3 G3r5=$W/G3r5_12row_raw.onnx show_s0=$W/show5_s0_12row_raw.onnx > $W/lat.log 2>&1 && touch $L/SH_LAT && log "latency done: $(cat $R/latency.json | tr -d '\n ' | cut -c1-200)"; }
[ -f $L/SH_PAR ] || { flock $LK python ml/eval/onnx_parity.py --det-pt $W/show5_s0_12row.pt --det-onnx $W/show5_s0_12row_raw.onnx --det-kind raw --imgsz 480 --det-imgs "/workspace/work/cv/g3data/det_v3/det/images/val/*.jpg" --n 40 --out $R/parity_show_s0.json > $W/par.log 2>&1; touch $L/SH_PAR; log "parity rc done"; }
[ -f $L/SH_BOOT ] || { flock $LK nice -n 5 python ml/eval/bootstrap_det.py collect --model $W/show5_s0_12row.pt --tag show_s0 --out $W/boot > $W/boot.log 2>&1 && python ml/eval/bootstrap_perclass.py --ref G3 --cand show_s0 --classes 3 1 0 7 10 --out $R/perclass_bootstrap_s0.json > $W/bpc.log 2>&1 && touch $L/SH_BOOT && log "per-class bootstrap done"; }
python $W/decide.py > $W/decide2.log 2>&1
P=$(python3 -c "import json;print(json.load(open('$R/decision.json'))['PASS'])")
log "DECISION PASS=$P criteria=$(python3 -c "import json;print(json.load(open('$R/decision.json'))['criteria'])")"
if [ "$P" = "True" ]; then cp $W/show5_s0_12row_raw.onnx $R/showcase_s0_12row_raw.onnx; fi
cp $W/g8_show_collect.sh $W/decide.py $W/lat.py $W/exp.py $R/ 2>/dev/null; cp /workspace/work/cv/g8_show_collect.sh $R/
git add ml/runs/G8/showcase ml/eval/bootstrap_perclass.py
git commit -q -m "G8 showcase: Kaggle nutrisole-g8-showcase outputs, pooled per-class eval, dev video, latency, parity, per-class bootstrap; decision PASS=$P (Addendum 2026-10-13 S3, unchanged)" && {
  last=$(python3 -c "import json;print(json.load(open('/workspace/work/cv/gh_sync_state.json'))['last_synced'])")
  python3 /workspace/work/cv/gh_sync.py $last $(git rev-parse HEAD) cv-gauntlet >> $W/sync.log 2>&1 && log "committed $(git rev-parse --short HEAD), synced to cv-gauntlet" || log "commit $(git rev-parse --short HEAD) local; gh sync failed (needs github credentials; run gh_sync.py)"; }
touch $L/SH_DONE
