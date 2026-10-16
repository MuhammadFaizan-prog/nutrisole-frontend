#!/bin/bash
# after AUDIT_DONE: tar the audited oiv7c split and create the Kaggle dataset nutrisole-cv-g4-v4
cd /workspace/work/cv
while [ ! -f g4logs/AUDIT_DONE ]; do sleep 20; done
mkdir -p kaggle/g4/up_v4; rm -f kaggle/g4/up_v4/oiv7c_v4.tar
(cd g4data && tar -cf ../kaggle/g4/up_v4/oiv7c_v4.tar oiv7c/images oiv7c/labels) && \
cat > kaggle/g4/up_v4/dataset-metadata.json <<'J'
{"title": "nutrisole-cv-g4-v4", "id": "mfaizannnn/nutrisole-cv-g4-v4", "licenses": [{"name": "other"}], "description": "Private research data for NutriSole FYP CV gauntlet G4: audited Open Images V7 lemon/orange subset (images CC BY 2.0 per image, annotations CC BY 4.0) for det-v4. Not for redistribution; per-image licences in the repo."}
J
./g4_dscreate.sh kaggle/g4/up_v4
# Kaggle needs a few minutes to process a new dataset before a kernel can mount it
[ -f kaggle/g4/up_v4.DS_DONE ] && sleep 240 && echo ready > g4logs/V4_DS_READY
