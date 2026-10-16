#!/bin/bash
# poll Kaggle merge kernel, download output into g8models/k_merge on finish
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=proxy-managed
KS=mfaizannnn/nutrisole-g8-merge; O=g8models/k_merge; mkdir -p $O; rm -f $O/STATUS
while true; do raw=$(timeout 60 python3 kgl.py kernels status $KS 2>&1 | tail -1); echo "$(date -u +%TZ) $raw" >> $O/poll.log
 case "$raw" in *COMPLETE*|*ERROR*|*CANCEL*) timeout 1800 python3 kgl.py kernels output $KS -p $O > $O/dl.log 2>&1; echo "$raw" > $O/STATUS; exit 0;; esac; sleep 30; done
