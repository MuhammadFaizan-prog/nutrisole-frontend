#!/bin/bash
# G8 H4 step 1: complete the G7 addendum-C DEV tracker grid (4/8 configs missing after a G7 restart), apply the pre-registered pick rule unchanged,
# and if the pick differs from b15 run TEST once. Idempotent (skips configs with gauntlet.json; T_* markers in g8logs).
cd /workspace/work/nutrisole; source /workspace/work/cvenv/bin/activate
L=/workspace/work/cv/g8logs; R=ml/runs/G7/tracking/tune; G8R=ml/runs/G8/tracking; mkdir -p $R $G8R; LK=/workspace/work/cv/g7logs/cpu.lock
DET=/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx; CLS=/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx
for nt in 0.25 0.35; do for mt in 0.8 0.9; do for mh in 1 2; do
  n=nt${nt}_mt${mt}_mh${mh}; [ -f $R/$n/gauntlet.json ] && continue
  P="{\"track_buffer\": 15, \"new_track_thresh\": $nt, \"match_thresh\": $mt, \"minHits\": $mh}"
  flock $LK python ml/eval/video_gauntlet.py --det $DET --det-kind raw --imgsz 480 --clips /workspace/work/cv/g3clips_dev --kinds det,neg --cls $CLS --temp 0.25 --cls-imgsz 224 --no-realtime --max-same-class 0 --tracker-kind bytetrack --tracker "$P" --out $R/$n > $L/tune_$n.log 2>&1 && touch $L/T_tune_$n
done; done; done
python - <<'PY' > $G8R/pick_g7grid.json
import json,glob,os
rows=[]
for d in sorted(glob.glob("ml/runs/G7/tracking/tune/nt*")):
    g=json.load(open(d+"/gauntlet.json"))["clips"]; c=g["det"]; ng=g.get("neg",{})
    rows.append(dict(cfg=os.path.basename(d),seg=c["segment_acc"],frame=c["frame_acc"],ttfc_p90=c["ttfc_ms"]["p90"],flick=c["label_flicker_per_10s_static"],ids=c["id_switches"],frag=c.get("fragmentations"),missed_s=c.get("missed_s_total"),fa_min=ng.get("false_alarms_per_min")))
ref=[r for r in rows if r["cfg"]=="nt0.35_mt0.8_mh2"][0]
ok=[r for r in rows if r["flick"]<=0.625 and (r["fa_min"] or 0)<=(ref["fa_min"] or 0)]
pick=sorted(ok,key=lambda r:(-r["seg"],r["ttfc_p90"] or 1e9))[0] if ok else ref
print(json.dumps(dict(rule="prereg addendum C",rows=rows,ref=ref["cfg"],pick=pick["cfg"]),indent=1))
PY
pick=$(python -c "import json;print(json.load(open('$G8R/pick_g7grid.json'))['pick'])")
echo "- $(date -u +%TZ) [tune-g7grid] DEV grid done, pick=$pick" >> $L/progress.md
if [ "$pick" != "nt0.35_mt0.8_mh2" ]; then
  nt=$(echo $pick | sed 's/nt\([0-9.]*\)_.*/\1/'); mt=$(echo $pick | sed 's/.*_mt\([0-9.]*\)_.*/\1/'); mh=${pick##*_mh}
  P="{\"track_buffer\": 15, \"new_track_thresh\": $nt, \"match_thresh\": $mt, \"minHits\": $mh}"
  for spec in "test_tuned_r1 /workspace/work/cv/g1clips det,quality,neg" "negtest_tuned_r1 /workspace/work/cv/g2clips_negtest neg"; do set -- $spec
    [ -f $L/T_$1 ] || { flock $LK python ml/eval/video_gauntlet.py --det $DET --det-kind raw --imgsz 480 --clips $2 --kinds $3 --cls $CLS --temp 0.25 --cls-imgsz 224 --no-realtime --max-same-class 0 --tracker-kind bytetrack --tracker "$P" --out $G8R/$1 > $L/t_$1.log 2>&1 && touch $L/T_$1; }
  done
fi
touch $L/TUNE_DONE; echo "- $(date -u +%TZ) [tune-g7grid] done" >> $L/progress.md
