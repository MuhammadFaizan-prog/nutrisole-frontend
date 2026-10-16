#!/bin/bash
# G8 P0-1 stage 1: ml/autolabel/extract.py per clip in prereg priority order (g8logs/al_order.txt), output shared with G7 (g7al/stage1).
# Idempotent: skips clips with frames.json. One clip per cpu.lock hold. Stop: touch g8logs/STOP_AL.
cd /workspace/work/nutrisole; source /workspace/work/cvenv/bin/activate
L=/workspace/work/cv/g8logs; O=/workspace/work/cv/g7al/stage1; mkdir -p $O
while read f; do id=$(basename $f); id=${id%.*}; [ -f $O/$id/frames.json ] && continue; [ -f $L/STOP_AL ] && exit 0
  flock /workspace/work/cv/g7logs/cpu.lock nice -n 5 python ml/autolabel/extract.py --clips-dir $(dirname $f) --out $O --ids $id >> $L/al_stage1.log 2>&1; rc=$?
  echo "$(date -u +%T) $id rc=$rc $(python -c "import json;print(len(json.load(open('$O/$id/keyframes.json'))['keyframes']))" 2>/dev/null) kf" >> $L/al_stage1.log
done < $L/al_order.txt
n=$(ls $O/*/frames.json | wc -l); echo "- $(date -u +%TZ) [al] stage1 pass done: $n/69 clips" >> $L/progress.md; [ $n -ge 69 ] && touch $L/AL1_DONE
