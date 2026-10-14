"""H2 evidence on the occluder suite crops: full-crop H2 probs (does identity verification still pass on the occluded crop, with the wide
class = the item's class?) and the 4 half-crop agreements (partAgree at minP 0.3 / 0.5). Writes out/occ_h2.json. Usage: h_occ_h2.py SECONDS"""
import json, os, sys, time, glob, cv2
sys.path.insert(0, "/workspace/work/nutrisole"); sys.path.insert(0, "/workspace/work/nutrisole/ml/runs/G9/stageH/scripts")
from h_ident import h2_probs, halves
from ml.eval.verify import part_agreement, h2_decision
N = ["banana", "apple", "mango", "citrus", "guava", "pomegranate", "lemon_lime", "tomato", "potato", "cucumber", "carrot", "capsicum"]
B = "/workspace/work/nutrisole/ml/runs/G9/stageH/out"; OUT = f"{B}/occ_h2.json"
cls = {json.loads(l)["id"]: json.loads(l)["cls"] for l in open(f"{B}/occ_items.jsonl")}
D = json.load(open(OUT)) if os.path.exists(OUT) else {}; t0 = time.time()
for p in sorted(glob.glob("/workspace/work/g9h/occ/crops/*.png")):
    k = os.path.basename(p)[:-4]
    if k in D: continue
    if time.time() - t0 > float(sys.argv[1]): break
    c = cls[k.split("_")[0]]; ci = N.index(c); im = cv2.imread(p); pr, _ = h2_probs(im); hp = [h2_probs(x)[0] for x in halves(im)]
    D[k] = dict(probs=pr, partAgree=part_agreement(hp, ci, 0.3), partAgree5=part_agreement(hp, ci, 0.5), halves_top=[max(range(13), key=lambda i: h[i]) for h in hp])
json.dump(D, open(OUT, "w")); print(len(D), "of", len(glob.glob("/workspace/work/g9h/occ/crops/*.png")))
