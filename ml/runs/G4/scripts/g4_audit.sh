#!/bin/bash
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole
python ml/data/sources/oiv7_audit.py --src /workspace/work/cv/g4data/oiv7c_src/oiv7c --out /workspace/work/cv/g4data/oiv7c \
  --existing "/workspace/work/cv/g1data/builds/v1/det/images/*/*.jpg" "/workspace/work/cv/g2data/coco_neg/images/*/*.jpg" "/workspace/work/cv/g3data/det_v3_oiv7/images/*/*.jpg" "/workspace/work/cv/g3data/hardneg/images/*/*.jpg" \
  --screen-model ml/runs/G3/kaggle/nutrisole-g3-det-yolo11n-640/runs/det_yolo11n_640/weights/best.pt --screen-imgsz 480 --screen-conf 0.5 \
  --test-split-name test_oiv7c --prefix oiv7c_ > /workspace/work/cv/g4logs/audit_oiv7c.log 2>&1 && touch /workspace/work/cv/g4logs/AUDIT_DONE
