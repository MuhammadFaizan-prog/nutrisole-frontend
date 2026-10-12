#!/bin/bash
# G5.4: package quality2_g5ll (train/val/val_lolo; NO test) -> Kaggle dataset nutrisole-cv-g5-cls -> push CPU cls kernel. Idempotent.
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=${KAGGLE_API_TOKEN:-proxy-managed}
L=g5logs; log(){ echo "$(date -u +%T) clsq $*" >> $L/gpuq.log; }
while [ ! -f $L/BUILDLL_DONE ]; do sleep 120; done
U=kaggle/g5/up_cls
if [ ! -f kaggle/g5/up_cls.DS_DONE ]; then mkdir -p $U
  (cd g5data && tar -cf ../$U/cls_g5ll.tar quality2_g5ll/train quality2_g5ll/val quality2_g5ll/val_lolo quality2_g5ll/manifest.json)
  echo '{"title": "nutrisole-cv-g5-cls", "id": "mfaizannnn/nutrisole-cv-g5-cls", "licenses": [{"name": "other"}], "description": "Private research data for NutriSole FYP CV G5.4: quality2-g5ll train/val/val_lolo (no test)."}' > $U/dataset-metadata.json
  timeout 3000 kaggle datasets create -p $U > kaggle/g5/up_cls_create.log 2>&1; grep -qiE "success|created|ready" kaggle/g5/up_cls_create.log && touch kaggle/g5/up_cls.DS_DONE && log "cls dataset created" && sleep 300
fi
[ -f kaggle/g5/up_cls.DS_DONE ] || { log "cls dataset create failed"; exit 1; }
for i in $(seq 1 20); do [ -f $L/PUSHED_cls ] && break
  out=$(timeout 120 python3 kgl.py kernels push -p kaggle/g5/k_cls 2>&1 | tail -1)
  echo "$out" | grep -q "successfully pushed" && { date -u +%T > $L/PUSHED_cls; log "pushed cls"; } || { log "wait cls: ${out:0:90}"; sleep 600; }
done
