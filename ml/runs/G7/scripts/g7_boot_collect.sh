#!/bin/bash
# usage: g7_boot_collect.sh TAG PT  (idempotent, cpu.lock)
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole; L=/workspace/work/cv/g7logs
[ -f $L/B_$1 ] && exit 0
flock $L/cpu.lock python ml/eval/bootstrap_det.py collect --model $2 --tag $1 --out /workspace/work/cv/g7models/boot > $L/boot_$1.log 2>&1 && touch $L/B_$1
echo "- $(date -u +%TZ) [boot] collect $1 rc=$?" >> $L/progress.md
