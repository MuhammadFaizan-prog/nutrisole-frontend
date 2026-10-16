#!/bin/bash
# usage: g5_cls_eval.sh TAG PT IMGSZ -- T fitted on val_lolo (G5, no held-out lighting family), test + robustness incl. night_sodium_hard, grading proxy, export+parity. Idempotent.
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole
TAG=$1; PT=$2; S=$3; R=ml/runs/G5; L=/workspace/work/cv/g5logs; D=/workspace/work/cv/g5data/quality2_g5ll; MD=/workspace/work/cv/g5models/cls_$TAG; mkdir -p $MD
st(){ [ -f $L/C_${TAG}_$1 ]; }; done_(){ touch $L/C_${TAG}_$1; }
st eval || { python ml/eval/eval_cls.py --model $PT --data $D --imgsz $S --robust --val-split val_lolo --out $R/eval_cls_$TAG > $L/ev_cls_$TAG.log 2>&1 && done_ eval; }
T=$(python -c "import json;print(json.load(open('$R/eval_cls_$TAG/eval_cls.json'))['temperature'])")
st proxy || { python ml/grading/eval_proxy.py --cls $PT --temp $T --imgsz $S --data $D --out $R/grading_proxy_$TAG/grading_proxy.json > $L/proxy_$TAG.log 2>&1 && done_ proxy; }
st export || { python ml/export/export_models.py --cls $PT:$S:$T:fresh,rotten --out $MD > $L/export_cls_$TAG.log 2>&1 && done_ export; }
ONNX=$(ls $MD/*.onnx | head -1)
st parity || { python ml/eval/onnx_parity.py --cls-pt $PT --cls-onnx $ONNX --cls-imgs "$D/test/*/*.jpg" --cls-imgsz $S --out $R/parity_cls_$TAG.json > $L/parity_cls_$TAG.log 2>&1 && done_ parity; }
echo "T=$T onnx=$ONNX" > $L/cls_$TAG.txt; touch $L/C_${TAG}_ALL
