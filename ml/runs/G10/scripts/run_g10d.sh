#!/bin/bash
G=/workspace/work/cv/g10; L=$G/logs; R=$G/runs
while [ ! -f $L/C_DONE ]; do sleep 20; done
cd /workspace/work/nutrisole; P=/workspace/work/cvenv/bin/python
st(){ [ -f $L/DONE_$1 ]; }; ok(){ touch $L/DONE_$1; }
for s in 480 640; do st guard_$s || { $P ml/eval/g10_guard_whatif.py --model $G/models/G3_best_copy.pt --imgsz $s --list $G/val.txt --neg $G/negdev.txt --out $R/guard_whatif_G3_$s.json > $L/guard_$s.log 2>&1 && ok guard_$s; }; done
st fbprobs || { $G/tfenv/bin/python ml/eval/g10_cls_bench.py --fruitbot-probs $R/fruitbot_probs_hval.json > $L/fb.log 2>&1 && ok fbprobs; }
st clsrep || { $P ml/eval/g10_cls_bench.py --report $R/fruitbot_probs_hval.json --out $R/cls_bench_hval.json > $L/clsrep.log 2>&1 && ok clsrep; }
touch $L/D_DONE
