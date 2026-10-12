#!/bin/bash
# G5.1b: DEV sweep of temporal window for champion (G3 control) and A1, then nothing else (TEST runs launched by g5_orch after selection)
cd /workspace/work/cv
C=/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx; A=/workspace/work/cv/g4models/A1hyg/det_yolo11n_640_hyg_off_raw.onnx
for m in C:$C A:$A; do t=${m%%:*}; d=${m#*:}
  ./g5_dev.sh ${t}_base $d 480
  for w in 3 5 7; do ./g5_dev.sh ${t}_w$w $d 480 --temporal "{\"window\":$w}"; done
done
touch g5logs/TEMPORAL_DEV_DONE
