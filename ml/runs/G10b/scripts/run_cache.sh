#!/bin/bash
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole
G=/workspace/work/cv/g10; C=/workspace/work/cv/g10b/cache; L=/workspace/work/cv/g10b/logs
echo "g10b $$ $(date)" > /workspace/work/cv/g7logs/cpu.lock
[ -f $L/DONE_g3 ] || { python ml/runs/G10b/scripts/g10b_cache.py --model $G/models/G3_best_copy.pt --imgsz 480 --lists $G/val.txt $G/negdev.txt --out $C/g3_480.pkl > $L/g3.log 2>&1 && touch $L/DONE_g3; }
[ -f $L/DONE_v8m ] || { python ml/runs/G10b/scripts/g10b_cache.py --model $G/ext/henning/yolo_fruits_and_vegetables_v1.pt --imgsz 640 --lists $G/val.txt $G/negdev.txt --out $C/v8m_640.pkl > $L/v8m.log 2>&1 && touch $L/DONE_v8m; }
rm -f /workspace/work/cv/g7logs/cpu.lock; touch $L/CACHE_DONE
