#!/bin/bash
G=/workspace/work/cv/g10; L=$G/logs; R=$G/runs
while [ ! -f $L/D_DONE ]; do sleep 20; done
cd /workspace/work/nutrisole; P=/workspace/work/cvenv/bin/python
st(){ [ -f $L/DONE_$1 ]; }; ok(){ touch $L/DONE_$1; }
st oiv_g3_480 || { $P ml/eval/g10_ext_bench.py --model $G/models/G3_best_copy.pt --map g3 --imgsz 480 --list $G/val_oiv7.txt --out $R/bench_G3_480_valoiv7.json > $L/oiv_g3_480.log 2>&1 && ok oiv_g3_480; }
touch $L/E_DONE
