#!/bin/bash
cd /workspace/work/cv; ./g4_gaunt.sh cls4_r2 /workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx raw 480 /workspace/work/cv/g4models/cls_cls4/G4_E224_e25_b64_sgd01.onnx 1.7045885645587342 224 --max-same-class 0 && touch g4logs/NO_g4_cls4r2.sh
