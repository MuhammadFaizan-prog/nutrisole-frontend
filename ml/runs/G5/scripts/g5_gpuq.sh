#!/bin/bash
# G5.1a/G5.2: package mined hard negatives -> Kaggle dataset nutrisole-cv-g5 -> push det kernels g5hn, g5hnc when a GPU slot frees (retry every 10 min). Idempotent.
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=${KAGGLE_API_TOKEN:-proxy-managed}
L=g5logs; log(){ echo "$(date -u +%T) gpuq $*" >> $L/gpuq.log; }
while [ ! -f $L/MINE_DONE ]; do sleep 120; done
U=kaggle/g5/up_hn
if [ ! -f kaggle/g5/up_hn.DS_DONE ]; then
  rm -rf g5data/g5hn; mkdir -p g5data/g5hn/images/train $U
  python3 - <<'P'
import json, random, shutil, os
r = json.load(open('/workspace/work/cv/g5data/hardneg_A1/mining.json'))
c = json.load(open('/workspace/work/cv/g5data/hardneg_A1/filter.json'))['agent_review']['final']
random.Random(0).shuffle(c); keep = sorted(c[:600])
for f in keep: shutil.copy(f'/workspace/work/cv/g5data/hardneg_A1/crops/{f}', f'/workspace/work/cv/g5data/g5hn/images/train/{f}')
json.dump(dict(available=len(c), kept=len(keep), files=keep), open('/workspace/work/cv/g5data/g5hn/manifest.json', 'w'), indent=1)
print(len(c), len(keep))
P
  (cd g5data && tar -cf ../$U/g5hn.tar g5hn)
  cat > $U/dataset-metadata.json <<'J'
{"title": "nutrisole-cv-g5", "id": "mfaizannnn/nutrisole-cv-g5", "licenses": [{"name": "other"}], "description": "Private research data for NutriSole FYP CV gauntlet G5: hard-negative background crops mined from CC0 / US-public-domain Wikimedia Commons market videos (per-video licences in the repo docs/cv/licences.md)."}
J
  timeout 3000 kaggle datasets create -p $U > kaggle/g5/up_hn_create.log 2>&1; grep -qiE "success|created|ready" kaggle/g5/up_hn_create.log && touch kaggle/g5/up_hn.DS_DONE && log "dataset created" && sleep 300
fi
[ -f kaggle/g5/up_hn.DS_DONE ] || { log "dataset create failed"; exit 1; }
while [ ! -f $L/HNVER_DONE ]; do sleep 60; done
for v in g5hn g5hnc; do d=kaggle/g5/k_det_$v; mkdir -p $d
  sed "s/__VARIANT__/$v/" kaggle/g5/det_run_g5.py > $d/run.py
  ds='"mfaizannnn/nutrisole-cv-g3", "mfaizannnn/nutrisole-cv-g4-abl", "mfaizannnn/nutrisole-cv-g5"'
  [ $v = g5hnc ] && ds="$ds, \"hosythao/guava-fruit-dataset-yolo8\", \"enddl22/deepnir-11fruits\""
  echo "{\"id\": \"mfaizannnn/nutrisole-g5-det-$v\", \"title\": \"nutrisole-g5-det-$v\", \"code_file\": \"run.py\", \"language\": \"python\", \"kernel_type\": \"script\", \"is_private\": true, \"enable_gpu\": true, \"enable_internet\": true, \"dataset_sources\": [$ds], \"competition_sources\": [], \"kernel_sources\": []}" > $d/kernel-metadata.json
done
for i in $(seq 1 60); do
  for v in g5hn g5hnc; do [ -f $L/PUSHED_$v ] && continue; [ -f $L/NOPUSH_$v ] && continue
    out=$(timeout 120 python3 kgl.py kernels push -p kaggle/g5/k_det_$v 2>&1 | tail -1)
    if echo "$out" | grep -q "successfully pushed"; then touch $L/PUSHED_$v; date -u +%T > $L/PUSHED_$v; log "pushed $v"; else log "wait $v: ${out:0:90}"; fi
  done
  [ -f $L/PUSHED_g5hn ] && [ -f $L/PUSHED_g5hnc ] && break
  sleep 600
done
