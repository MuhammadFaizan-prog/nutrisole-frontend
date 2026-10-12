#!/bin/bash
source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=${KAGGLE_API_TOKEN:-proxy-managed}
cd /workspace/work/cv; mkdir -p g5data/raw
for d in hosythao/guava-fruit-dataset-yolo8 afsananadia/fruits-images-dataset-object-detection enddl22/deepnir-11fruits; do n=$(echo $d|tr / _)
  [ -f g5data/raw/$n.DONE ] && continue
  timeout 2400 python3 kgl.py datasets download $d -p g5data/raw/$n --unzip > g5logs/dl_$n.log 2>&1 && touch g5data/raw/$n.DONE
done
