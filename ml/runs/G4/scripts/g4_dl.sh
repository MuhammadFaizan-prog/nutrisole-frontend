#!/bin/bash
# g4_dl.sh KERNEL OUTDIR : download kernel output in background, touch OUTDIR/DL_DONE when done
source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=${KAGGLE_API_TOKEN:-proxy-managed}
mkdir -p $2; timeout 1800 kaggle kernels output mfaizannnn/$1 -p $2 > $2/dl.log 2>&1 && touch $2/DL_DONE
