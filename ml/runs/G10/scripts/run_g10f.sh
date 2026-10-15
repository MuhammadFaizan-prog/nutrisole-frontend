#!/bin/bash
G=/workspace/work/cv/g10; L=$G/logs; R=$G/runs; cd /workspace/work/nutrisole
$G/tfenv/bin/python ml/eval/g10_cls_bench.py --fruitbot-probs $R/fruitbot_probs_hval.json > $L/fb.log 2>&1 && touch $L/DONE_fbprobs
/workspace/work/cvenv/bin/python ml/eval/g10_cls_bench.py --report $R/fruitbot_probs_hval.json --out $R/cls_bench_hval.json > $L/clsrep.log 2>&1 && touch $L/DONE_clsrep
touch $L/F_DONE
