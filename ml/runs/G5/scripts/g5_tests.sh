#!/bin/bash
# G5 repo checks: g1_tests.sh suite + ml/prices pytest; logs in $1
D=$1; mkdir -p $D; rm -f $D/TESTS_DONE
TL=$D bash /workspace/work/cv/g1_tests.sh
( source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole && python -m pytest -q ml/prices; echo EXIT=$? ) > $D/t_prices.log 2>&1
grep -h "EXIT=" $D/t_*.log > $D/summary.txt; touch $D/ALL_DONE
