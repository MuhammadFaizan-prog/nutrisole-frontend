#!/bin/bash
# G8 watchdog: keeps the pipeline moving without waiting for a scheduled run.
# Every 5 min: (1) relaunch dead jobs (g8_relaunch.sh); (2) retry OOM-killed stage-1 clips with 1 thread, max 3 tries/clip,
# then skip the clip (logged) so OWLv2 stage 2 is never blocked forever; (3) redo failed tracker-grid configs (max 3 tries)
# and re-run the pick. Stop: touch g8logs/STOP_WD. Started by g8_relaunch.sh, so it comes back after a sandbox restart
# as soon as anything calls g8_relaunch.sh.
cd /workspace/work/cv; L=g8logs; O=g7al/stage1; R=/workspace/work/nutrisole/ml/runs/G7/tracking/tune
log(){ echo "- $(date -u +%TZ) [watchdog] $*" >> $L/progress.md; }
mkdir -p $L/wd; log "started (pid $$)"
while [ ! -f $L/STOP_WD ]; do
  bash g8_relaunch.sh >/dev/null 2>&1

  # (2) stage-1 retries, only when the main pass is not running
  if [ ! -f $L/AL1_DONE ] && ! pgrep -f "^bash g8_autolabel.sh" >/dev/null && grep -q "stage1 pass done" $L/progress.md; then
    pending=0
    while read f; do id=$(basename $f); id=${id%.*}
      [ -f $O/$id/frames.json ] && continue
      [ -f $L/wd/skip_$id ] && continue
      n=$(cat $L/wd/try_$id 2>/dev/null || echo 0)
      if [ $n -ge 3 ]; then touch $L/wd/skip_$id; log "stage1 SKIP $id after 3 failed retries (OOM); excluded from auto-labels, listed in G8_failures"; continue; fi
      echo $((n+1)) > $L/wd/try_$id; pending=1
      rm -rf $O/$id
      (cd /workspace/work/nutrisole; source /workspace/work/cvenv/bin/activate; OMP_NUM_THREADS=1 ORT_NUM_THREADS=1 \
        flock /workspace/work/cv/g7logs/cpu.lock nice -n 5 python ml/autolabel/extract.py --clips-dir $(dirname $f) --out /workspace/work/cv/$O --ids $id >> /workspace/work/cv/$L/al_stage1.log 2>&1)
      rc=$?; echo "$(date -u +%T) $id rc=$rc retry$((n+1))" >> $L/al_stage1.log
    done < $L/al_order.txt
    done_n=$(ls $O/*/frames.json 2>/dev/null | wc -l); skip_n=$(ls $L/wd/skip_* 2>/dev/null | wc -l)
    if [ $pending -eq 0 ] && [ $((done_n+skip_n)) -ge 69 ]; then touch $L/AL1_DONE; log "stage1 complete: $done_n/69 labelled, $skip_n skipped -> OWLv2 stage 2 unblocked"; fi
  fi

  # (3) tracker grid: configs missing gauntlet.json -> clear markers and rerun g8_tune.sh (max 3 tries)
  missing=$(for nt in 0.25 0.35; do for mt in 0.8 0.9; do for mh in 1 2; do c=nt${nt}_mt${mt}_mh${mh}; [ -s $R/$c/gauntlet.json ] || echo $c; done; done; done)
  if [ -n "$missing" ] && ! pgrep -f "^bash g8_tune.sh" >/dev/null; then
    t=$(cat $L/wd/tune_try 2>/dev/null || echo 0)
    if [ $t -lt 3 ]; then echo $((t+1)) > $L/wd/tune_try
      for c in $missing; do rm -rf $R/$c; rm -f $L/T_tune_$c; done; rm -f $L/TUNE_DONE
      log "tracker grid retry $((t+1)): missing $(echo $missing | tr '\n' ' ')"
      (OMP_NUM_THREADS=1 ORT_NUM_THREADS=1 setsid nohup bash g8_tune.sh > $L/g8_tune.out 2>&1 < /dev/null &)
    elif [ ! -f $L/wd/tune_gaveup ]; then touch $L/wd/tune_gaveup; log "tracker grid: gave up after 3 retries, missing $(echo $missing | tr '\n' ' ')"; fi
  fi
  sleep 300
done
log "stopped (STOP_WD)"
