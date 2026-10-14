"""G9 Stage E leakage audit for market set M (all downloaded M-DEV + M-TEST candidates): 64-bit pHash vs (a) all keyframes of the G7 stage-1
clips (holdout + M-dev + M-train + excluded), (b) DEV val stills, (c) every 10th frame of DEV det/neg/quality clips, (d) det_v3 train (G3
training images), (e) Stage D set S and all 586 Stage D Commons candidates; plus M-DEV vs M-TEST and within-split near-duplicates.
Reference hashes are cached. Usage: leakage_e.py OUT.json"""
import json, sys, glob, os, cv2, imagehash
from PIL import Image
D = "/workspace/work/cv/g9e"; CACHE = f"{D}/ref_hashes.json"
def ph(p): return str(imagehash.phash(Image.open(p).convert("RGB")))
if os.path.exists(CACHE): ref = json.load(open(CACHE))
else:
    ref = []
    for p in glob.glob("/workspace/work/cv/g7al/stage1/*/keyframes/*.jpg"): ref.append(["g7_clip_keyframe:" + p.split("/")[-3], ph(p)])
    for l in open("/workspace/work/cv/g3data/det_v3/val.txt"): ref.append(["dev_val", ph(l.strip())])
    for c in ("det", "neg", "quality"):
        cap = cv2.VideoCapture(f"/workspace/work/cv/g3clips_dev/{c}_clip.mp4"); i = 0
        while True:
            ok, fr = cap.read()
            if not ok: break
            if i % 10 == 0: ref.append([f"dev_{c}_clip", str(imagehash.phash(Image.fromarray(fr[:, :, ::-1])))])
            i += 1
    for l in open("/workspace/work/cv/g3data/det_v3/train.txt"): ref.append(["det_v3_train(G3 train)", ph(l.strip())])
    for p in glob.glob("/workspace/work/cv/g9d/commons/img/*.jpg"): ref.append(["stageD_candidate_or_S:" + os.path.basename(p), ph(p)])
    json.dump(ref, open(CACHE, "w"))
R = [(n, imagehash.hex_to_hash(h)) for n, h in ref]
man = {v["file"]: v for v in json.load(open(f"{D}/commons/manifest.json")).values() if "file" in v and os.path.exists(f"{D}/commons/img/{v['file']}")}
H = {f: imagehash.phash(Image.open(f"{D}/commons/img/{f}").convert("RGB")) for f in man}
out = {}
for f, h in H.items():
    d = sorted(((h - r, n) for n, r in R), key=lambda x: x[0])[:3]
    cross = sorted((int(h - H[g]), g) for g in H if g != f)[:1]
    out[f] = dict(split=man[f]["split"], min_dist_ref=int(d[0][0]), nearest_ref=[[int(a), b] for a, b in d],
                  nearest_in_M=cross[0] if cross else None, nearest_in_M_split=man[cross[0][1]]["split"] if cross else None)
res = dict(ref_hashes=len(R), ref_counts={k: sum(1 for n, _ in ref if n.split(":")[0] == k) for k in set(n.split(":")[0] for n, _ in ref)},
           candidates=len(H), leak_vs_ref=[f for f, v in out.items() if v["min_dist_ref"] <= 10],
           near_dup_cross_split=[f for f, v in out.items() if v["nearest_in_M"] and v["nearest_in_M"][0] <= 10 and v["nearest_in_M_split"] != v["split"]],
           near_dup_same_split=[f for f, v in out.items() if v["nearest_in_M"] and v["nearest_in_M"][0] <= 10 and v["nearest_in_M_split"] == v["split"]], per_image=out)
json.dump(res, open(sys.argv[1], "w"), indent=0); print({k: (len(v) if isinstance(v, list) else v) for k, v in res.items() if k != "per_image"})
