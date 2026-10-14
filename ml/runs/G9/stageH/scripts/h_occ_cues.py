"""Recompute Stage H occlusion cues (ml/eval/occlusion.cues) on the saved suite crops -> out/occ_cues.jsonl {key: cues}. Resumable.
Usage: h_occ_cues.py SECONDS"""
import json, os, sys, time, glob, cv2
sys.path.insert(0, "/workspace/work/nutrisole")
from ml.eval.occlusion import cues
from ml.grading.measure import object_mask
OUT = "/workspace/work/nutrisole/ml/runs/G9/stageH/out/occ_cues.jsonl"; done = set()
if os.path.exists(OUT):
    for l in open(OUT): done |= set(json.loads(l))
t0 = time.time(); buf = {}
for p in sorted(glob.glob("/workspace/work/g9h/occ/crops/*.png")):
    k = os.path.basename(p)[:-4]
    if k in done: continue
    if time.time() - t0 > float(sys.argv[1]): break
    im = cv2.imread(p); m, _ = object_mask(im[:, :, ::-1].copy()); buf[k] = cues(im, m)
    if len(buf) >= 200:
        open(OUT, "a").write(json.dumps(buf) + "\n"); buf = {}
if buf: open(OUT, "a").write(json.dumps(buf) + "\n")
print(len(done) + len(buf), "of", len(glob.glob("/workspace/work/g9h/occ/crops/*.png")))
