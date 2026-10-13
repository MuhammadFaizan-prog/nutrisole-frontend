#!/bin/bash
# G8 P0-1 stage 2+3 (adapted from g7_al_kaggle.sh): wait AL1_DONE -> keyframes tar -> Kaggle dataset nutrisole-cv-g7-al -> kernel nutrisole-g7-autolabel (OWLv2; GPU) -> merge.py -> ml/runs/G8/autolabel. Markers A_* in g8logs.
# (GPU if a free slot among our det kernels, else CPU) -> wait -> download -> merge.py. Idempotent markers A_*.
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=proxy-managed
L=g8logs; K=kaggle/g7; log(){ echo "- $(date -u +%TZ) [al-k g8] $*" >> $L/progress.md; }
until [ -f $L/AL1_DONE ]; do [ -f $L/STOP_ALK ] && exit 0; sleep 120; done
if [ ! -f $L/A_tar ]; then
  (cd g7al/stage1 && tar -cf ../../$K/up_al/keyframes_all.tar */keyframes */keyframes.json) && touch $L/A_tar && log "keyframes tar $(du -h $K/up_al/keyframes_all.tar | cut -f1), $(ls g7al/stage1/*/keyframes/*.jpg | wc -l) kf"
fi
[ -f g7models/k_ripedup/ripe_test_neardup.json ] && cp g7models/k_ripedup/ripe_test_neardup.json $K/up_al/
if [ ! -f $L/A_ds ]; then
  timeout 3000 kaggle datasets create -p $K/up_al > $L/al_ds.log 2>&1; grep -qiE "success|created|ready|already" $L/al_ds.log && touch $L/A_ds; log "dataset create: $(tail -1 $L/al_ds.log | cut -c1-150)"
  sleep 180
fi
if [ ! -f $L/A_push ]; then
  run=0
  [ $run -lt 2 ] && sed -i 's/"enable_gpu":false/"enable_gpu":true/' $K/k_al/kernel-metadata.json
  for i in 1 2 3 4 5 6; do out=$(timeout 100 python3 kgl.py kernels push -p $K/k_al 2>&1 | tail -1); echo "$out" >> $L/al_push.log
    echo "$out" | grep -q "successfully pushed" && { touch $L/A_push; log "autolabel kernel pushed (gpu=$(grep -o '"enable_gpu":[a-z]*' $K/k_al/kernel-metadata.json))"; break; }; sed -i 's/"enable_gpu":true/"enable_gpu":false/' $K/k_al/kernel-metadata.json; sleep 120; done
  [ -f $L/A_push ] || { log "autolabel kernel push FAILED 6x"; exit 1; }
fi
O=g8models/k_al; mkdir -p $O
until [ -f $L/A_done ]; do
  s=$(timeout 60 python3 kgl.py kernels status mfaizannnn/nutrisole-g7-autolabel 2>&1 | grep -oE 'COMPLETE|ERROR|CANCEL[A-Z]*' | head -1)
  if [ -n "$s" ]; then timeout 1500 python3 kgl.py kernels output mfaizannnn/nutrisole-g7-autolabel -p $O > $O/dl.log 2>&1 && { echo $s > $O/STATUS; touch $L/A_done; log "autolabel kernel $s, output downloaded"; }; else sleep 300; fi
done
R=/workspace/work/nutrisole/ml/runs/G8; mkdir -p $R/autolabel $R/ripeness $R/hue_shift
cp $O/ripeness_hue_shift.json $R/hue_shift/ 2>/dev/null; mkdir -p $R/ripeness/overripe_audit; cp $O/audit_*.jpg $R/ripeness/overripe_audit/ 2>/dev/null
cp $O/*.log $R/autolabel/kernel.log 2>/dev/null
if [ -f $O/owlv2_keyframes.json ] && [ ! -f $L/A_merge ]; then
  cd /workspace/work/nutrisole
  flock /workspace/work/cv/g7logs/cpu.lock python ml/autolabel/merge.py --stage1 /workspace/work/cv/g7al/stage1 --owl /workspace/work/cv/$O/owlv2_keyframes.json --roles ml/runs/G7/video_v7/roles.json \
     --videos /workspace/work/cv/g6src/raw /workspace/work/cv/g7src/raw --out ml/runs/G8/autolabel > $L/al_merge.log 2>&1 && touch $L/A_merge
  log "merge rc=$? $(python -c "import json;d=json.load(open('ml/runs/G8/autolabel/summary.json'));print(d['clips'],'clips',d['keyframes'],'kf',d['boxes'],'boxes',d['status'],'queue',d['review_queue'])" 2>/dev/null)"
fi
touch $L/ALK_DONE
