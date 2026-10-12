#!/bin/bash
cd /workspace/work/cv
C=/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx
for t in fthnc fthn; do nice -n 5 ./g5_gaunt.sh ${t}_r1 /workspace/work/cv/g5models/$t/det_yolo11n_ft480_${t}_raw.onnx raw 480 $C 0.25 224 --max-same-class 0; done
echo done > g5logs/FTG_DONE
