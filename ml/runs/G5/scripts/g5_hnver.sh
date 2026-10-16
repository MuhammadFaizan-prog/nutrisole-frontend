#!/bin/bash
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=${KAGGLE_API_TOKEN:-proxy-managed}
[ -f g5logs/HNVER_DONE ] && exit 0
timeout 1500 kaggle datasets version -p kaggle/g5/up_hn -m "G5 filtered hard negatives: two-model filter + agent visual review, 53 crops x4" > g5logs/hnver.log 2>&1 && grep -qiE "success|created|ready|updated" g5logs/hnver.log && sleep 300 && touch g5logs/HNVER_DONE
