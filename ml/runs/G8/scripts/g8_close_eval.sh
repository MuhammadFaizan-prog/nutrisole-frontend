#!/bin/bash
# G8 closeout CPU jobs (idempotent, markers CL_* in g8logs, all behind cpu.lock): showcase strict per-split eval (non-gating S3
# report item), neg_test image FA for show_s0, repo tests, locked-split hashes. Waits for the showcase collector (SH_DONE) first.
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate; L=/workspace/work/cv/g8logs; LK=/workspace/work/cv/g7logs/cpu.lock
log(){ echo "- $(date -u +%TZ) [close] $*" >> $L/progress.md; }
n=0; while [ ! -f $L/SH_DONE ] && [ $n -lt 3 ]; do pgrep -f g8_show_collect.sh >/dev/null && n=0 || n=$((n+1)); sleep 60; done
cd /workspace/work/nutrisole; R=ml/runs/G8/showcase; W=/workspace/work/cv/g8show; D3=/workspace/work/cv/g3data/det_v3
for s in 0 1; do
  [ -f $L/CL_split$s ] || { flock $LK nice -n 5 python ml/eval/eval_det.py --model $W/show5_s${s}_12row.pt --data /workspace/work/cv/g4data/det_v4_eval.yaml --imgsz 480 --splits test test_rf test_oiv7 test_oiv7c --out $R/eval_splits_show_s$s > $W/splits_s$s.log 2>&1 && touch $L/CL_split$s && log "showcase s$s strict per-split eval done"; }
done
[ -f $L/CL_negfa ] || { flock $LK python ml/eval/neg_fa.py --model $W/show5_s0_12row.pt --imgsz 480 --images $D3/neg/images/neg_test --out $R/neg_fa_show_s0.json > $W/negfa.log 2>&1 && touch $L/CL_negfa && log "showcase s0 neg_test FA done"; }
mkdir -p /workspace/work/cv/g8logs/tests
[ -f $L/CL_tests ] || { flock $LK bash /workspace/work/cv/g7_tests.sh /workspace/work/cv/g8logs/tests > /dev/null 2>&1; cp /workspace/work/cv/g8logs/tests/summary.txt ml/runs/G8/tests_summary.txt 2>/dev/null; touch $L/CL_tests; log "tests: $(tr '\n' ' ' < /workspace/work/cv/g8logs/tests/summary.txt)"; }
[ -f $L/CL_hash ] || { flock $LK python /workspace/work/cv/g7_hashes.py g8_end > /workspace/work/cv/g8logs/hashes.out 2>&1; cp ml/runs/G7/locked_hashes_g8_end.json ml/runs/G8/locked_hashes_end.json; touch $L/CL_hash; log "locked hashes: $(tail -2 /workspace/work/cv/g8logs/hashes.out | tr '\n' ' ' | cut -c1-300)"; }
touch $L/CL_EVAL_DONE
