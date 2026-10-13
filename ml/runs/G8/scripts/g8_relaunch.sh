#!/bin/bash
# Relaunch all G8 background jobs after a sandbox restart (idempotent; markers in g8logs/). Safe to run every fire.
cd /workspace/work/cv; L=g8logs; mkdir -p $L
st(){ pgrep -f "$1" >/dev/null || (setsid nohup bash $1 ${2:-} > $L/$(basename $1 .sh).out 2>&1 < /dev/null &); }
[ -f $L/AL1_DONE ] || st g8_autolabel.sh
# G7 leftover: night classifier Kaggle kernel collector (writes ml/runs/G7/night/, G7 prereg s5 gate)
[ -f g7logs/NIGHT_DONE ] || st g7_night_post.sh
[ -f $L/TUNE_DONE ] || st g8_tune.sh
[ -f g8_alk.sh ] && { [ -f $L/ALK_DONE ] || st g8_alk.sh; }
[ -f g8_jobs_extra.sh ] && st g8_jobs_extra.sh
up=$(cut -d. -f1 /proc/uptime); [ $up -lt 1800 ] && echo "- $(date -u +%TZ) RELAUNCH (uptime ${up}s)" >> $L/progress.md
