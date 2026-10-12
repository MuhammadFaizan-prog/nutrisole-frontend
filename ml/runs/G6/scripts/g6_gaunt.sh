#!/bin/bash
# usage: g5_gaunt.sh TAG DET KIND IMGSZ CLS TEMP CLSIMGSZ [extra args...]
# G5 fixed-frame (deterministic) TEST gauntlet: G1 clips + G2 negtest clip (same protocol as G4). Idempotent via g6logs/G_TAG.
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole
TAG=$1; DET=$2; K=$3; S=$4; CLS=$5; T=$6; CS=$7; shift 7
R=ml/runs/G6; L=/workspace/work/cv/g6logs
[ -f $L/G_$TAG ] && exit 0
# G6 budget gate (G6_prereg deviation): fine-tune candidates get the gauntlet only if they pass the strict image gates; r2 only if r1 is non-inferior.
case $TAG in G6rp_r*|G6rpx_r*)
  M=${TAG%_r*}; python /workspace/work/cv/g6_tables.py > /dev/null 2>&1
  ok=$(python -c "import json;s=json.load(open('ml/runs/G6/tables.json'))['strict'];print(any(v['image_pass'] for k,v in s.items() if k.endswith('[$M]')))")
  if [ "$ok" != "True" ]; then echo "$(date -u +%T) $TAG skipped: image gates fail" >> $L/gaunt_skip.log; exit 0; fi
  if [ "${TAG##*_}" = "r2" ]; then
    g=$(python -c "import json;d=json.load(open('ml/runs/G6/gauntlet_ff_${M}_r1/gauntlet.json'))['clips'];print(d['det']['segment_acc']>=0.6667 and d['neg']['false_alarms_per_min']<=1.25)" 2>/dev/null)
    [ "$g" != "True" ] && { echo "$(date -u +%T) $TAG skipped: r1 fails gauntlet gates" >> $L/gaunt_skip.log; exit 0; }
  fi;;
esac
python ml/eval/video_gauntlet.py --det $DET --det-kind $K --imgsz $S --clips /workspace/work/cv/g1clips --cls $CLS --temp $T --cls-imgsz $CS --no-realtime --out $R/gauntlet_ff_$TAG "$@" > $L/g_$TAG.log 2>&1 && \
python ml/eval/video_gauntlet.py --det $DET --det-kind $K --imgsz $S --clips /workspace/work/cv/g2clips_negtest --kinds neg --no-realtime --out $R/gauntlet_ff_negtest_$TAG "$@" > $L/gn_$TAG.log 2>&1 && touch $L/G_$TAG
