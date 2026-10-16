#!/bin/bash
# G8 closeout: poll Kaggle mfaizannnn/nutrisole-g8-holdout, download replay JSONs to g8hold/out, score per prereg addendum 2026-10-14.
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=proxy-managed
L=g8logs; O=/workspace/work/cv/g8hold/out; mkdir -p $O; log(){ echo "- $(date -u +%TZ) [holdout] $*" >> $L/progress.md; }
K=mfaizannnn/nutrisole-g8-holdout
while [ ! -f $L/HO_DL ]; do
  st=$(timeout 60 python3 kgl.py kernels status $K 2>&1 | tail -1); echo "$(date -u +%TZ) $st" >> g8hold/status.log
  case "$st" in
    *COMPLETE*) timeout 1200 python3 kgl.py kernels output $K -p $O > g8hold/dl.log 2>&1; [ -f $O/hold_meta.json ] && { touch $L/HO_DL; log "kernel COMPLETE, $(ls $O/hold/*.json | wc -l) clip replays downloaded"; } ;;
    *ERROR*|*CANCEL*) timeout 600 python3 kgl.py kernels output $K -p $O > g8hold/dl.log 2>&1; log "kernel FAILED: $st"; touch $L/HO_FAIL; exit 1 ;;
  esac
  [ -f $L/HO_DL ] || sleep 240
done
cd /workspace/work/nutrisole
[ -f $L/HO_SCORE ] || { python ml/runs/G8/scripts/g8_holdout_score.py $O/hold ml/runs/G8/holdout > /workspace/work/cv/g8hold/score.log 2>&1 && cp $O/hold_meta.json ml/runs/G8/holdout/ && touch $L/HO_SCORE && log "scored: $(python3 -c "import json;d=json.load(open('ml/runs/G8/holdout/holdout_scores.json'));print({c:(d['all12'][c]['clip_presence_recall'],d['all12'][c]['fa_per_min']) for c in d['all12']})")"; }
touch $L/HO_DONE
