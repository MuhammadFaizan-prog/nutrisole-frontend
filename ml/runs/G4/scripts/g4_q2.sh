#!/bin/bash
# CPU queue 2: G3 champion on the new split test_oiv7c (control for G4.2)
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole
PT=ml/runs/G3/kaggle/nutrisole-g3-det-yolo11n-640/runs/det_yolo11n_640/weights/best.pt
[ -f /workspace/work/cv/g4logs/E_G3champ_oiv7c ] || { python ml/eval/eval_det.py --model $PT --data /workspace/work/cv/g4data/det_v4_eval.yaml --imgsz 480 --splits test_oiv7c --out ml/runs/G4/eval_det_G3champ_oiv7c > /workspace/work/cv/g4logs/evaldet_G3champ_oiv7c.log 2>&1 && touch /workspace/work/cv/g4logs/E_G3champ_oiv7c; }
