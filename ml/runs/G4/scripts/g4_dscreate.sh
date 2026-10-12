#!/bin/bash
# g4_dscreate.sh DIR : create Kaggle dataset in background; log to DIR/create.log, marker DIR/DS_DONE
source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=${KAGGLE_API_TOKEN:-proxy-managed}
timeout 3000 kaggle datasets create -p $1 > $1/../$(basename $1)_create.log 2>&1; grep -qiE "success|created|ready" $1/../$(basename $1)_create.log && touch $1/../$(basename $1).DS_DONE
