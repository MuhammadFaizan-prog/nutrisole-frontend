#!/bin/bash
# G7 night classifier: wait for Kaggle nutrisole-g7-night, download, eval both arms + G3 E224 control with the SAME script
# (eval_cls.py --robust on the locked q2g3crop test, n=270, CPU, imgsz 224), apply the prereg section-5 gate. Markers N_*.
cd /workspace/work/cv; source /workspace/work/cvenv/bin/activate; export KAGGLE_USERNAME_OVERRIDE=mfaizannnn KAGGLE_API_TOKEN=proxy-managed
L=/workspace/work/cv/g7logs; O=g7models/k_night; mkdir -p $O; log(){ echo "- $(date -u +%TZ) [night] $*" >> $L/progress.md; }
until [ -f $L/N_dl ]; do
  s=$(timeout 60 python3 kgl.py kernels status mfaizannnn/nutrisole-g7-night 2>&1 | grep -oE 'COMPLETE' | head -1)  # fix 2026-10-13: wait for COMPLETE only (v1 ERRORed: no cls_g3.tar; re-pushed v2)
  if [ -n "$s" ]; then timeout 1500 python3 kgl.py kernels output mfaizannnn/nutrisole-g7-night -p $O > $O/dl.log 2>&1 && { echo $s > $O/STATUS; touch $L/N_dl; log "kernel $s downloaded"; }; else sleep 240; fi
done
cd /workspace/work/nutrisole; R=ml/runs/G7/night; mkdir -p $R; cp /workspace/work/cv/$O/night_g7_meta.json $R/ 2>/dev/null
D=/workspace/work/cv/g3data/quality2_g3crop
G3PT=ml/runs/G3/kaggle/nutrisole-g3-cls/runs/E_224_e15_b64_sgd01/weights/best.pt
for spec in "G3E224=$G3PT" "N1=/workspace/work/cv/$O/runs/N1_light_aug/weights/best.pt" "N2=/workspace/work/cv/$O/runs/N2_light_aug_reduced_hue/weights/best.pt"; do
  t=${spec%%=*}; pt=${spec#*=}; [ -f $pt ] || { log "$t missing best.pt"; continue; }
  [ -f $L/N_ev_$t ] || { flock $L/cpu.lock python ml/eval/eval_cls.py --model $pt --data $D --imgsz 224 --robust --out $R/eval_$t > $L/night_ev_$t.log 2>&1 && touch $L/N_ev_$t; }
done
python - <<'PY' > $R/night_gate.json
import json, os
R = "ml/runs/G7/night"; out = {"gate": "prereg s5: night_sodium_hard rotten recall >= 0.983 AND low_light rotten recall >= 0.941 AND test (item-crop) rotten recall >= 0.983", "models": {}}
for t in ["G3E224", "N1", "N2"]:
    p = f"{R}/eval_{t}/eval_cls.json"
    if not os.path.exists(p): continue
    d = json.load(open(p)); rb = d["robustness"]
    row = dict(test_acc=round(d["test"]["acc"], 4), test_rotten_recall=round(d["test"]["recall"]["rotten"], 4),
               night_sodium_hard_rr=round(rb["night_sodium_hard"]["rotten_recall"], 4), low_light_rr=round(rb["low_light"]["rotten_recall"], 4),
               low_light_hard_rr=round(rb["low_light_hard"]["rotten_recall"], 4), tube_light_hard_rr=round(rb["tube_light_hard"]["rotten_recall"], 4), n_test=d["n_test"])
    row["passes_gate"] = row["night_sodium_hard_rr"] >= 0.983 and row["low_light_rr"] >= 0.941 and row["test_rotten_recall"] >= 0.983
    out["models"][t] = row
print(json.dumps(out, indent=1))
PY
log "gate: $(python -c "import json;d=json.load(open('$R/night_gate.json'))['models'];print({k:(v['night_sodium_hard_rr'],v['low_light_rr'],v['test_rotten_recall'],v['passes_gate']) for k,v in d.items()})")"
touch $L/NIGHT_DONE
