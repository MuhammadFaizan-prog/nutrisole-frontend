#!/bin/bash
G=/workspace/work/cv/g10; L=$G/logs; R=$G/runs
while [ ! -f $L/B_DONE ]; do sleep 20; done
echo "g10c $$ $(date)" > /workspace/work/cv/g7logs/cpu.lock
cd /workspace/work/nutrisole; P=/workspace/work/cvenv/bin/python
st(){ [ -f $L/DONE_$1 ]; }; ok(){ touch $L/DONE_$1; }
for s in 480 640; do st oiv_g3_$s || { $P ml/eval/g10_ext_bench.py --model $G/models/G3_best_copy.pt --map g3 --imgsz $s --list $G/val_oiv7.txt --out $R/bench_G3_${s}_valoiv7.json > $L/oiv_g3_$s.log 2>&1 && ok oiv_g3_$s; }; done
st oiv_hv1 || { $P ml/eval/g10_ext_bench.py --model $G/ext/henning/yolo_fruits_and_vegetables_v1.pt --map lvis63 --imgsz 640 --list $G/val_oiv7.txt --out $R/bench_henning_v1m_640_valoiv7.json > $L/oiv_hv1.log 2>&1 && ok oiv_hv1; }
rm -f /workspace/work/cv/g7logs/cpu.lock; touch $L/C_DONE
