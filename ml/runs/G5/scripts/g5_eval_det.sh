#!/bin/bash
# usage: g5_eval_det.sh TAG PT IMGSZ -- local CPU eval of a raw+NMS yolo11n: export ONNX, parity, eval test/test_rf/test_oiv7/test_oiv7c, pooled, neg FA. Idempotent.
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole
TAG=$1; PT=$2; S=$3; K=raw; R=ml/runs/G5; L=/workspace/work/cv/g5logs; MD=/workspace/work/cv/g5models/$TAG; mkdir -p $MD
st(){ [ -f $L/E_${TAG}_$1 ]; }; done_(){ touch $L/E_${TAG}_$1; }
D3=/workspace/work/cv/g3data/det_v3
st export || { python ml/export/export_models.py --det $PT:$K:$S --out $MD > $L/export_$TAG.log 2>&1 && done_ export; }
ONNX=$(ls $MD/*${K}*.onnx 2>/dev/null | head -1); echo "onnx=$ONNX" > $L/onnx_$TAG.txt
st parity || { python ml/eval/onnx_parity.py --det-pt $PT --det-onnx $ONNX --det-kind $K --imgsz $S --det-imgs "$D3/det/images/test/*.jpg" --out $R/parity_det_$TAG.json > $L/parity_$TAG.log 2>&1 && done_ parity; }
st eval || { python ml/eval/eval_det.py --model $PT --data /workspace/work/cv/g4data/det_v4_eval.yaml --imgsz $S --splits test test_rf test_oiv7 test_oiv7c --out $R/eval_det_$TAG > $L/evaldet_$TAG.log 2>&1 && done_ eval; }
st pooled || { python ml/eval/eval_det.py --model $PT --data $D3/det_v3_pooled.yaml --imgsz $S --splits pooled --out $R/eval_pooled_$TAG > $L/pooled_$TAG.log 2>&1 && done_ pooled; }
st negfa || { python ml/eval/neg_fa.py --model $PT --imgsz $S --images $D3/neg/images/neg_test --out $R/neg_fa_$TAG.json > $L/negfa_$TAG.log 2>&1 && done_ negfa; }
st nostrips || { python ml/eval/eval_det.py --model $PT --data /workspace/work/cv/g5data/test_rf_nostrips.yaml --imgsz $S --splits test_rf_nostrips --out $R/eval_nostrips_$TAG > $L/nostrips_$TAG.log 2>&1 && done_ nostrips; }
touch $L/E_${TAG}_ALL
