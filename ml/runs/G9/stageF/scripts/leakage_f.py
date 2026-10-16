"""G9 Stage F leakage audit for the MT pool: 64-bit pHash vs G3 train (det_v3 train), DEV val stills, DEV det/neg/quality clip frames,
G7 stage-1 keyframes (holdout + M-dev + M-train), Stage D set S, and ALL Stage E market candidates (M-DEV + M-TEST + unused).
Distance <= 10 -> drop. Within-pool near-duplicates (<= 10) -> keep the first. Usage: leakage_f.py OUT.json"""
import json, sys, os, glob, imagehash
from PIL import Image
ref = json.load(open("/workspace/work/cv/g9e/ref_hashes.json"))
S = {i["file"] for i in json.load(open("/workspace/work/nutrisole/ml/runs/G9/stageD/s_labels.json"))["items"]}
R = []
for n, h in ref:
    if n.startswith("stageD_candidate_or_S:"):
        if n.split(":", 1)[1] not in S: continue
        n = "stageD_S:" + n.split(":", 1)[1]
    R.append((n, imagehash.hex_to_hash(h)))
MC = "/workspace/work/cv/g9f/m_hashes.json"
if os.path.exists(MC): mh = json.load(open(MC))
else:
    mh = {os.path.basename(p): str(imagehash.phash(Image.open(p).convert("RGB"))) for p in glob.glob("/workspace/work/cv/g9e/commons/img/*.jpg")}; json.dump(mh, open(MC, "w"))
R += [("stageE_M_candidate:" + f, imagehash.hex_to_hash(h)) for f, h in mh.items()]
pool = json.load(open("/workspace/work/cv/g9f/pool.json"))
H = {t: imagehash.phash(Image.open(v["path"]).convert("RGB")) for t, v in pool.items()}
out = {}; kept = []
for t, h in H.items():
    d = min(((h - r, n) for n, r in R), key=lambda x: x[0])
    dup = min(((h - H[k], k) for k in kept), key=lambda x: x[0], default=(99, None))
    out[t] = dict(min_dist_ref=int(d[0]), nearest_ref=d[1], dup_of=dup[1] if dup[0] <= 10 else None, phash=str(h))
    if d[0] > 10 and dup[0] > 10: kept.append(t)
res = dict(ref_hashes=len(R), pool=len(H), leak=[t for t, v in out.items() if v["min_dist_ref"] <= 10], dup=[t for t, v in out.items() if v["dup_of"]], kept=len(kept), per_image=out)
json.dump(res, open(sys.argv[1], "w"), indent=0); print({k: (len(v) if isinstance(v, list) else v) for k, v in res.items() if k != "per_image"}, [(t, out[t]["nearest_ref"]) for t in res["leak"]][:10])
