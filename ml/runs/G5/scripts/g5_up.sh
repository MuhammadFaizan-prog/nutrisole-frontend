#!/bin/bash
# (re)start G5 background workers that are not running (session resets kill them). Each worker is idempotent.
cd /workspace/work/cv
start(){ n=$1; shift; [ -f g5logs/NO_$n ] && return; ps -eo args | grep -v grep | grep -qF "$*" || { setsid nohup "$@" >> g5logs/$n.out 2>&1 < /dev/null & echo "started $n"; }; }
start wait_v4 ./g5_wait_k.sh nutrisole-g4-det-v4 det4
start wait_v4h ./g5_wait_k.sh nutrisole-g4-det-v4hyg det4h
start q_temporal ./g5_q_temporal.sh
start mine ./g5_mine.sh
[ -f g5logs/G5_EXTRA_UP ] && source g5logs/G5_EXTRA_UP
