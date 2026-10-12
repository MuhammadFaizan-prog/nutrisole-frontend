#!/bin/bash
# usage: g5_dev.sh TAG DET IMGSZ [extra]: DEV-only tuning replay (G3 dev det+neg clips + G3 devneg clip), no classifier
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole
TAG=$1; DET=$2; S=$3; shift 3; R=ml/runs/G5/dev; L=/workspace/work/cv/g5logs
[ -f $L/D_$TAG ] && exit 0
python ml/eval/video_gauntlet.py --det $DET --det-kind raw --imgsz $S --clips /workspace/work/cv/g3clips_dev --kinds det,neg --no-realtime --out $R/dev_$TAG "$@" > $L/d_$TAG.log 2>&1 && \
python ml/eval/video_gauntlet.py --det $DET --det-kind raw --imgsz $S --clips /workspace/work/cv/g3clips_devneg --kinds neg --no-realtime --out $R/devneg_$TAG "$@" > $L/dn_$TAG.log 2>&1 && touch $L/D_$TAG
