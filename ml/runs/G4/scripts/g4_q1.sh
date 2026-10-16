#!/bin/bash
# G4.1 queue: reproducibility (each config twice) + tracker tune check on TEST clips. Sequential.
cd /workspace/work/cv
G1D=/workspace/work/cv/g1models/det_yolo26n_320_e2e.onnx; G1C=/workspace/work/cv/g1models/cls_q2_yolo26n_192.onnx
D3=/workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx; C3=/workspace/work/cv/g3models/cls/E_224_e15_b64_sgd01.onnx
TUNE='{"scoreAlpha":0.5,"switchMargin":0.1,"minHits":3}'
./g4_gaunt.sh G3champ_r1 $D3 raw 480 $C3 0.25 224
./g4_gaunt.sh G3champ_r2 $D3 raw 480 $C3 0.25 224
./g4_gaunt.sh G3champ_tune_r1 $D3 raw 480 $C3 0.25 224 --tracker "$TUNE"
./g4_gaunt.sh G1champ_r1 $G1D e2e 320 $G1C 0.889 192
./g4_gaunt.sh G1champ_r2 $G1D e2e 320 $G1C 0.889 192
./g4_gaunt.sh G3champ_msc0_r1 $D3 raw 480 $C3 0.25 224 --max-same-class 0
touch g4logs/Q1_DONE
