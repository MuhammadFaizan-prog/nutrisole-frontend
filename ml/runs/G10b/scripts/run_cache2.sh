#!/bin/bash
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole
G=/workspace/work/cv/g10; C=/workspace/work/cv/g10b/cache; L=/workspace/work/cv/g10b/logs
while [ ! -f $L/CACHE_DONE ]; do sleep 20; done
echo "g10b2 $$ $(date)" > /workspace/work/cv/g7logs/cpu.lock
[ -f $L/DONE_v8m_h ] || { python ml/runs/G10b/scripts/g10b_cache.py --model $G/ext/henning/yolo_fruits_and_vegetables_v1.pt --imgsz 640 --lists /workspace/work/cv/g10b/stageh_imgs.txt --out $C/v8m_640_stageh.pkl > $L/v8m_h.log 2>&1 && touch $L/DONE_v8m_h; }
rm -f /workspace/work/cv/g7logs/cpu.lock; touch $L/CACHE2_DONE
