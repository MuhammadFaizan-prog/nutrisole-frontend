#!/bin/bash
# G10 inference-only benchmark chain (dev/val splits only; no training; production weights only READ).
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole
G=/workspace/work/cv/g10; L=$G/logs; R=$G/runs; D=/workspace/work/cv/g3data/det_v3
echo "g10 $$ $(date)" > /workspace/work/cv/g7logs/cpu.lock
st(){ [ -f $L/DONE_$1 ]; }; ok(){ touch $L/DONE_$1; }
G3=$G/models/G3_best_copy.pt
st evaldet || { python ml/eval/eval_det.py --model $G3 --data $D/det_v3.yaml --imgsz 480 640 --splits val --out $R/eval_det_G3_val > $L/evaldet.log 2>&1 && ok evaldet; }
for s in 480 640; do st g3_$s || { python ml/eval/g10_ext_bench.py --model $G3 --map g3 --imgsz $s --list $G/val.txt --neg $G/negdev.txt --out $R/bench_G3_$s.json > $L/g3_$s.log 2>&1 && ok g3_$s; }; done
for m in Yolo11 Yolo26; do for s in 640 480; do st m_${m}_$s || { python ml/eval/g10_ext_bench.py --model $G/ext/mark360/$m.pt --map mark360 --imgsz $s --list $G/val.txt --neg $G/negdev.txt --out $R/bench_mark360_${m}_$s.json > $L/m_${m}_$s.log 2>&1 && ok m_${m}_$s; }; done; done
st hv1_640 || { python ml/eval/g10_ext_bench.py --model $G/ext/henning/yolo_fruits_and_vegetables_v1.pt --map lvis63 --imgsz 640 --list $G/val.txt --neg $G/negdev.txt --out $R/bench_henning_v1m_640.json > $L/hv1_640.log 2>&1 && ok hv1_640; }
st export || { python - > $L/export.log 2>&1 <<'P'
from ultralytics import YOLO
import shutil
G="/workspace/work/cv/g10"
for pt,tag,sz in [(f"{G}/models/G3_best_copy.pt","G3_k11_640",640),(f"{G}/ext/mark360/Yolo11.pt","mark360_y11",640),(f"{G}/ext/mark360/Yolo26.pt","mark360_y26",640),(f"{G}/ext/henning/yolo_fruits_and_vegetables_v1.pt","henning_v8m",640)]:
    try:
        p=YOLO(pt).export(format="onnx",imgsz=sz,device="cpu",dynamic=False,simplify=True); shutil.copyfile(p,f"{G}/models/{tag}_{sz}.onnx"); print("OK",tag,p)
    except Exception as e: print("FAIL",tag,e)
P
ok export; }
st lat || { python /workspace/work/cv/g2_bench.py $R/latency_onnx.json /workspace/work/cv/g3models/k11_480/det_yolo11n_640_raw.onnx:G3_prod:480 $G/models/G3_k11_640_640.onnx:G3_k11:640 $G/models/mark360_y11_640.onnx:mark360_y11:640 $G/models/mark360_y26_640.onnx:mark360_y26:640 $G/models/henning_v8m_640.onnx:henning_v8m:640 > $L/lat.log 2>&1 && ok lat; }
rm -f /workspace/work/cv/g7logs/cpu.lock; touch $L/ALL_DONE
