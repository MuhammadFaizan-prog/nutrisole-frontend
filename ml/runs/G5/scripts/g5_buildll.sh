#!/bin/bash
source /workspace/work/cvenv/bin/activate; cd /workspace/work/nutrisole
[ -f /workspace/work/cv/g5logs/BUILDLL_DONE ] && exit 0
python ml/data/build_quality_g5ll.py --g3crop /workspace/work/cv/g3data/quality2_g3crop --dst /workspace/work/cv/g5data/quality2_g5ll > /workspace/work/cv/g5logs/build_g5ll.log 2>&1 && touch /workspace/work/cv/g5logs/BUILDLL_DONE
