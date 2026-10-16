#!/bin/bash
# G6 rpx (reference) on the test_small6 VIEW
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole; L=/workspace/work/cv/g7logs
[ -f $L/E_G6rpx_small6 ] && exit 0
python ml/eval/eval_det.py --model ml/runs/G6/kaggle/nutrisole-g6-ft-rpx/runs/det_yolo11n_g6_rpx/weights/best.pt --data /workspace/work/cv/g7data/test_small6.yaml --imgsz 480 --splits test_small6 --out ml/runs/G7/eval_small6_G6rpx > $L/small6_G6rpx.log 2>&1 && touch $L/E_G6rpx_small6
