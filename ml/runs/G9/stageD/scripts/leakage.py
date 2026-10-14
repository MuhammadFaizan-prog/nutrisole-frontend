"""G9 Stage D leakage audit for the collected set S: 64-bit pHash of each candidate image vs (a) all keyframes of the 69 G7 stage-1 clips
(34 holdout + M-dev + M-train + excluded), (b) DEV val stills (det_v3 val, 402), (c) every 10th frame of the DEV det / neg / quality clips,
(d) det_v3 train (near-duplicates of training images add nothing), and within S. Also uploader checks (holdout + M-dev uploaders).
Usage: leakage.py IDS_JSON OUT.json   (IDS_JSON = list of S image file names)"""
import json, sys, glob, csv, cv2, imagehash
from PIL import Image
D = "/workspace/work/cv/g9d"; ids = json.load(open(sys.argv[1])); man = {m["file"]: m for m in json.load(open(f"{D}/commons/manifest.json")).values() if "file" in m}
role = {r["clip_id"]: r["stageB_role"] for r in csv.DictReader(open("/workspace/work/nutrisole/ml/runs/G9/stageB/mining_split.csv"))}
upl = {r["uploader"]: r["stageB_role"] for r in csv.DictReader(open("/workspace/work/nutrisole/ml/runs/G9/stageB/mining_split.csv"))}
def ph(p): return imagehash.phash(Image.open(p).convert("RGB"))
def phcv(fr): return imagehash.phash(Image.fromarray(fr[:, :, ::-1]))
ref = []
for p in glob.glob("/workspace/work/cv/g7al/stage1/*/keyframes/*.jpg"): ref.append(("clip:" + role.get(p.split("/")[-3], "?") + ":" + p.split("/")[-3], ph(p)))
for l in open("/workspace/work/cv/g3data/det_v3/val.txt"): ref.append(("dev_val", ph(l.strip())))
for c in ("det", "neg", "quality"):
    cap = cv2.VideoCapture(f"/workspace/work/cv/g3clips_dev/{c}_clip.mp4"); i = 0
    while True:
        ok, fr = cap.read()
        if not ok: break
        if i % 10 == 0: ref.append((f"dev_{c}_clip", phcv(fr)))
        i += 1
nref = len(ref)
for l in open("/workspace/work/cv/g3data/det_v3/train.txt"): ref.append(("det_v3_train", ph(l.strip())))
S = {k: ph(f"{D}/commons/img/{k}") for k in ids}; out = {}
for k, h in S.items():
    d = sorted(((h - r, n) for n, r in ref), key=lambda x: x[0])[:3]
    dup = [j for j in S if j < k and S[j] - h <= 6]
    out[k] = dict(min_dist=int(d[0][0]), nearest=[[int(a), b] for a, b in d], within_S_dup_of=dup, uploader=man[k]["uploader"], uploader_role=upl.get(man[k]["uploader"]))
res = dict(ref_hashes_eval=nref, ref_hashes_total=len(ref), candidates=len(S),
           drop_leak=[k for k, v in out.items() if v["min_dist"] <= 10], drop_dup=[k for k, v in out.items() if v["within_S_dup_of"]],
           drop_uploader=[k for k, v in out.items() if v["uploader_role"] in ("holdout_never_used", "excluded_uploader_overlaps_holdout", "M-dev")], per_image=out)
json.dump(res, open(sys.argv[2], "w"), indent=0); print({k: (len(v) if isinstance(v, list) else v) for k, v in res.items() if k != "per_image"})
