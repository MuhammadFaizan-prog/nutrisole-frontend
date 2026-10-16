#!/bin/bash
# usage: g5_gaunt.sh TAG DET KIND IMGSZ CLS TEMP CLSIMGSZ [extra args...]
# G5 fixed-frame (deterministic) TEST gauntlet: G1 clips + G2 negtest clip (same protocol as G4). Idempotent via g5logs/G_TAG.
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole
TAG=$1; DET=$2; K=$3; S=$4; CLS=$5; T=$6; CS=$7; shift 7
R=ml/runs/G5; L=/workspace/work/cv/g5logs
[ -f $L/G_$TAG ] && exit 0
python ml/eval/video_gauntlet.py --det $DET --det-kind $K --imgsz $S --clips /workspace/work/cv/g1clips --cls $CLS --temp $T --cls-imgsz $CS --no-realtime --out $R/gauntlet_ff_$TAG "$@" > $L/g_$TAG.log 2>&1 && \
python ml/eval/video_gauntlet.py --det $DET --det-kind $K --imgsz $S --clips /workspace/work/cv/g2clips_negtest --kinds neg --no-realtime --out $R/gauntlet_ff_negtest_$TAG "$@" > $L/gn_$TAG.log 2>&1 && touch $L/G_$TAG
