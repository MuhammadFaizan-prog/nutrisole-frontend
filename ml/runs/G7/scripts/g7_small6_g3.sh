#!/bin/bash
# G3 control on the test_small6 VIEW only (other G3 numbers are historical)
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole; L=/workspace/work/cv/g7logs
[ -f $L/E_G3_small6 ] && exit 0
python ml/eval/eval_det.py --model ml/runs/G3/kaggle/nutrisole-g3-det-yolo11n-640/runs/det_yolo11n_640/weights/best.pt --data /workspace/work/cv/g7data/test_small6.yaml --imgsz 480 --splits test_small6 --out ml/runs/G7/eval_small6_G3 > $L/small6_G3.log 2>&1 && touch $L/E_G3_small6
