#!/bin/bash
# resume of g4_mktype.sh after the crop build finished (processes were killed mid-way)
source /workspace/work/cvenv/bin/activate; cd /workspace/work/cv
mkdir -p kaggle/g4/up_type; (cd g4data && tar -cf ../kaggle/g4/up_type/typecrops.tar typecrops)
cat > kaggle/g4/up_type/dataset-metadata.json <<'J'
{"title": "nutrisole-cv-g4-type", "id": "mfaizannnn/nutrisole-cv-g4-type", "licenses": [{"name": "other"}], "description": "Private research data for NutriSole FYP CV gauntlet G4 two-stage experiment: produce type crops from det-v3 train/val (LVIS/COCO, OIV7 CC BY 2.0 images) + background 'other' crops. Not for redistribution."}
J
./g4_dscreate.sh kaggle/g4/up_type > g4logs/type_dscreate.log 2>&1 && sleep 240 && touch g4logs/TYPE_DS_READY
