#!/bin/bash
# G5.2 capsicum view: test_rf excluding the 110 sliced-strip capsicum boxes, for the G3 control and A1 (new models get it in g5_eval_det.sh)
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole; L=/workspace/work/cv/g5logs
for p in G3champ:ml/runs/G3/kaggle/nutrisole-g3-det-yolo11n-640/runs/det_yolo11n_640/weights/best.pt A1hyg:ml/runs/G4/kaggle/nutrisole-g4-det-hyg-off/runs/det_yolo11n_640_hyg_off/weights/best.pt; do t=${p%%:*}; pt=${p#*:}
  [ -f $L/E_${t}_nostrips ] || { python ml/eval/eval_det.py --model $pt --data /workspace/work/cv/g5data/test_rf_nostrips.yaml --imgsz 480 --splits test_rf_nostrips --out ml/runs/G5/eval_nostrips_$t > $L/nostrips_$t.log 2>&1 && touch $L/E_${t}_nostrips; }
done
