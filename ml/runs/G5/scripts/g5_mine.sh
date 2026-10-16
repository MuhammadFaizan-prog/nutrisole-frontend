#!/bin/bash
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole
[ -f /workspace/work/cv/g5logs/MINE_DONE ] && exit 0
python ml/data/mine_video_hardneg.py --det /workspace/work/cv/g4models/A1hyg/det_yolo11n_640_hyg_off_raw.onnx --imgsz 480 --frames /workspace/work/cv/g5data/video/frames --sources /workspace/work/cv/g5data/video/sources.json --out /workspace/work/cv/g5data/hardneg_A1 > /workspace/work/cv/g5logs/mine.log 2>&1 && touch /workspace/work/cv/g5logs/MINE_DONE
