#!/bin/bash
G=/workspace/work/cv/g10; L=$G/logs; R=$G/runs
while [ ! -f $L/ALL_DONE ]; do sleep 20; done
echo "g10b $$ $(date)" > /workspace/work/cv/g7logs/cpu.lock
cd /workspace/work/nutrisole
st(){ [ -f $L/DONE_$1 ]; }; ok(){ touch $L/DONE_$1; }
for s in 480 640; do st guard_$s || { /workspace/work/cvenv/bin/python ml/eval/g10_guard_whatif.py --model $G/models/G3_best_copy.pt --imgsz $s --list $G/val.txt --neg $G/negdev.txt --out $R/guard_whatif_G3_$s.json > $L/guard_$s.log 2>&1 && ok guard_$s; }; done
while ! grep -q done $L/tfenv.log; do sleep 20; done
st fbprobs || { $G/tfenv/bin/python ml/eval/g10_cls_bench.py --fruitbot-probs $R/fruitbot_probs_hval.json > $L/fb.log 2>&1 && ok fbprobs; }
st clsrep || { /workspace/work/cvenv/bin/python ml/eval/g10_cls_bench.py --report $R/fruitbot_probs_hval.json --out $R/cls_bench_hval.json > $L/clsrep.log 2>&1 && ok clsrep; }
rm -f /workspace/work/cv/g7logs/cpu.lock; touch $L/B_DONE
