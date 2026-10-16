#!/bin/bash
cd /workspace/work/cv
rm -f kaggle/g4/up_cls/cls_g4ll.tar
(cd g4data && tar -cf ../kaggle/g4/up_cls/cls_g4ll.tar --exclude='quality2_g4ll/test' quality2_g4ll) && \
cat > kaggle/g4/up_cls/dataset-metadata.json <<'J'
{"title": "nutrisole-cv-g4-cls", "id": "mfaizannnn/nutrisole-cv-g4-cls", "licenses": [{"name": "other"}], "description": "Private research data for NutriSole FYP CV gauntlet G4: quality2-g4ll (Sultana fresh/rotten CC BY 4.0 + phone-camera augs + detector-style crops + strong low-light copies) and val_hard. TEST excluded. Not for redistribution."}
J
./g4_dscreate.sh kaggle/g4/up_cls
