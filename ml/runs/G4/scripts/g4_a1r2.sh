#!/bin/bash
cd /workspace/work/cv; until [ -f g4logs/G_A1hyg_r1 ]; do sleep 60; done
./g4_gaunt.sh A1hyg_r2 /workspace/work/cv/g4models/A1hyg/$(ls g4models/A1hyg | grep raw.onnx | head -1) raw 480 /workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx 0.25 224 --max-same-class 0
echo "$(date +%T) A1hyg r2 done" >> g4logs/orch.log
