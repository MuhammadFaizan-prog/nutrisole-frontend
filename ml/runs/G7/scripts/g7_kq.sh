#!/bin/bash
# G7 Kaggle queue: free tier allows 2 concurrent GPU batch sessions. Polls kernels, downloads finished outputs,
# pushes queued kernels (order: sB, ripe) when a slot frees. Idempotent: markers in g7logs/ (K_<arm>_PUSHED, K_<arm>_DONE).
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate
export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=proxy-managed
L=g7logs/kq.log; M=g7logs
# sA, rfs v1 ERRORed at start (empty log) -> re-queued after sB, ripe
slug() { case $1 in ripe) echo nutrisole-g7-ripeness;; *) echo nutrisole-g7-det-$(echo $1 | tr A-Z a-z);; esac; }
QUEUE="sB ripe sA rfs"; ALL="sA rfs sB ripe"
while true; do
  [ -f $M/STOP_KQ ] && exit 0
  running=0; alldone=1
  for a in $ALL; do
    [ -f $M/K_${a}_DONE ] && continue
    alldone=0
    [ -f $M/K_${a}_PUSHED ] || continue
    s=$(timeout 60 python3 kgl.py kernels status mfaizannnn/$(slug $a) 2>&1 | grep -oE 'COMPLETE|ERROR|CANCEL[A-Z]*|RUNNING|QUEUED' | head -1)
    echo "$(date -u +%T) $a status=${s:-?}" >> $L
    if [[ "$s" =~ ^(COMPLETE|ERROR|CANCEL) ]]; then
      O=/workspace/work/cv/g7models/k_$a; mkdir -p $O
      timeout 1500 python3 kgl.py kernels output mfaizannnn/$(slug $a) -p $O > $O/dl.log 2>&1 && { echo $s > $O/STATUS; touch $M/K_${a}_DONE; echo "$(date -u +%T) $a downloaded ($s)" >> $L; }
    else running=$((running+1)); fi
  done
  [ $alldone = 1 ] && { echo "$(date -u +%T) all done" >> $L; exit 0; }
  for a in $QUEUE; do
    [ -f $M/K_${a}_PUSHED ] && continue
    [ $running -ge 2 ] && break
    [ -f $M/NO_NEW_PUSH ] && break
    d=kaggle/g7/k_$a
    out=$(timeout 100 python3 kgl.py kernels push -p $d 2>&1 | tail -1); echo "$(date -u +%T) push $a: $out" >> $L
    if echo "$out" | grep -q "successfully pushed"; then touch $M/K_${a}_PUSHED; running=$((running+1)); else break; fi
  done
  sleep 300
done
