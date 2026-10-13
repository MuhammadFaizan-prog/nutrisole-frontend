#!/bin/bash
# G8: collector for Kaggle kernel mfaizannnn/nutrisole-g8-autolabel. Polls status; on COMPLETE/ERROR downloads output into
# g8models/k_al, unpacks stage1_new.tar into g7al/stage1, then runs the g8_alk.sh merge step (merge.py -> ml/runs/G8/autolabel).
# Idempotent markers KC_* in g8logs. Outputs are PROPOSALS, never ground truth.
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=proxy-managed
L=g8logs; KS=mfaizannnn/nutrisole-g8-autolabel; O=g8models/k_al; mkdir -p $O; log(){ echo "- $(date -u +%TZ) [kal-collect] $*" >> $L/progress.md; }
until [ -f $L/K_push ]; do [ -f $L/STOP_KAL ] && exit 0; sleep 120; done
last=""
until [ -f $L/KC_dl ]; do
  [ -f $L/STOP_KAL ] && exit 0
  raw=$(timeout 60 python3 kgl.py kernels status $KS 2>&1 | tail -1); s=$(echo "$raw" | grep -oE 'COMPLETE|ERROR|CANCEL[A-Z]*|RUNNING|QUEUED' | head -1)
  [ "$s" != "$last" ] && { log "status: $raw"; last=$s; }
  case "$s" in COMPLETE|ERROR|CANCEL*)
    timeout 1800 python3 kgl.py kernels output $KS -p $O > $O/dl.log 2>&1 && { echo $s > $O/STATUS; touch $L/KC_dl; log "kernel $s, output downloaded ($(ls $O | wc -l) files)"; } ;;
  *) sleep 240 ;; esac
done
if [ -f $O/stage1_new.tar ] && [ ! -f $L/KC_s1 ]; then
  for c in $(tar -tf $O/stage1_new.tar | cut -d/ -f1 | sort -u); do
    k=$(tar -xOf $O/stage1_new.tar $c/keyframes.json 2>/dev/null | python3 -c "import json,sys;print(len(json.load(sys.stdin)['keyframes']))" 2>/dev/null)
    [ "${k:-0}" -gt 0 ] || [ ! -f g7al/stage1/$c/frames.json ] && { rm -rf g7al/stage1/$c; tar -xf $O/stage1_new.tar -C g7al/stage1 $c; }
  done
  n=$(ls g7al/stage1/*/frames.json | wc -l); touch $L/KC_s1; log "stage1 unpacked from Kaggle: $n/69 clips with frames.json ($(cat $O/stage1_summary.json 2>/dev/null | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['n_ok'],'/',d['n'],'ok, transcoded',d['transcoded_h264'])" 2>/dev/null))"
  [ $n -ge 69 ] && touch $L/AL1_DONE
fi
[ -f $O/owlv2_keyframes.json ] && log "owlv2: $(python3 -c "import json;d=json.load(open('$O/owlv2_keyframes.json'));print(d['n_done'],'/',d['n'],'kf,',len(d['clips']),'clips,',sum(len(v) for c in d['clips'].values() for v in c.values()),'proposals, device',d['device'])")"
# merge step (as in g8_alk.sh)
R=/workspace/work/nutrisole/ml/runs/G8; mkdir -p $R/autolabel $R/ripeness $R/hue_shift
cp $O/ripeness_hue_shift.json $R/hue_shift/ 2>/dev/null; mkdir -p $R/ripeness/overripe_audit; cp $O/audit_*.jpg $R/ripeness/overripe_audit/ 2>/dev/null
cat $O/*.log > $R/autolabel/kernel.log 2>/dev/null; cp $O/stage1_summary.json $R/autolabel/ 2>/dev/null
if [ -f $O/owlv2_keyframes.json ] && [ ! -f $L/A_merge ]; then
  cd /workspace/work/nutrisole
  flock /workspace/work/cv/g7logs/cpu.lock python ml/autolabel/merge.py --stage1 /workspace/work/cv/g7al/stage1 --owl /workspace/work/cv/$O/owlv2_keyframes.json --roles ml/runs/G7/video_v7/roles.json \
     --videos /workspace/work/cv/g6src/raw /workspace/work/cv/g7src/raw --out ml/runs/G8/autolabel > /workspace/work/cv/$L/al_merge.log 2>&1 && touch /workspace/work/cv/$L/A_merge
  log "merge rc=$? $(python -c "import json;d=json.load(open('ml/runs/G8/autolabel/summary.json'));print(d['clips'],'clips',d['keyframes'],'kf',d['boxes'],'boxes',d['status'],'queue',d['review_queue'])" 2>/dev/null)"
  cd /workspace/work/cv
fi
[ -f $L/A_merge ] && touch $L/ALK_DONE $L/KAL_DONE
